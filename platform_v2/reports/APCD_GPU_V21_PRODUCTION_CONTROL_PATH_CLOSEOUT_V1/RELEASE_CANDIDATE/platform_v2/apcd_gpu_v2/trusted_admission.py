"""ACL-backed issuance adapter for the existing Coupling batch ledger protocol.

No keys, signing root, budget authority, scheduler or solver is created here.
Production uses the installer-pinned Windows identity/DACL boundary. Fixtures
are explicitly scoped to PRODUCTION_EQUIVALENT and cannot authorize production.
"""
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field

from .config import StrictModel, digest
from .artifacts import sha256
from .ledger import Refused
from .general import (Admission, Manifest, Pin, checked, read_json, under, verify_acl,
                      validate_batch_inputs, load_platform)
from .serial import exclusive


class Provenance(StrictModel):
    case_id: str
    attempt_id: Literal['attempt_001']
    source_run_truth: Pin
    setup_input: Pin
    candidate_setup: Pin
    source_manifest: Pin
    auxiliary: list[Pin] = Field(default_factory=list)


class OwnerIntent(StrictModel):
    schema_version: Literal['APCD_GPU_V21_SCIENCE_OWNER_ISSUANCE_INTENT_V1']
    intent_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$')
    science_owner: str
    science_owner_sid: str
    batch_id: str
    manifest_file_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    approved_case_set: list[str]
    approved_entry_budget: int = Field(gt=0)
    per_case_entry_limit: Literal[1]
    no_replay: Literal[True]
    profile_id: Literal['coupling_609d_v1']
    profile_certification_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    release_inventory: Pin
    scientific_evidence: dict[str, Pin]
    case_provenance: list[Provenance]
    scope: Literal['SCIENCE_ADMISSION_AND_LEDGER_GENESIS_ONLY']
    solver_entry_authorized: Literal[False]
    fixture_only: bool = False


@dataclass(frozen=True)
class FixturePrincipal:
    sid: str
    root: str


def authority_policy(platform):
    """Verifier may run as GPU Owner; only issuance requires the Science token."""
    if platform.mode == 'PRODUCTION_EQUIVALENT':
        if 'zero_solver' not in str(Path(platform.runtime_root)).lower():
            raise Refused('FIXTURE_AUTHORITY_ROOT_REQUIRED')
        canonical=Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1').resolve()
        root=Path(platform.runtime_root).resolve()
        if root==canonical or canonical in root.parents or root in canonical.parents:
            raise Refused('FIXTURE_OUTSIDE_PRODUCTION_REQUIRED')
        for path in [platform.science_root,platform.source_root,platform.coupling_root]:
            under(path,root)
        return
    canonical = Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1/platform_config.json')
    installed = load_platform(Pin(path=str(canonical), sha256=sha256(canonical)))
    if installed.model_dump() != platform.model_dump():
        raise Refused('ISSUER_PLATFORM_NOT_INSTALLER_BOUND')
    if platform.science_owner_sid == platform.consumer_sid or platform.science_owner_sid in platform.operator_sids:
        raise Refused('SCIENCE_GPU_PRINCIPAL_SEPARATION_REQUIRED')
    for root in [platform.science_root, platform.source_root]:
        verify_acl(platform, root, authority_root=root)


def require_science_owner(platform, fixture_principal=None):
    if platform.mode == 'PRODUCTION_GPU' and fixture_principal is not None:
        raise Refused('FIXTURE_CREDENTIAL_FORBIDDEN_IN_PRODUCTION')
    authority_policy(platform)
    if platform.mode == 'PRODUCTION_EQUIVALENT':
        if (not isinstance(fixture_principal, FixturePrincipal)
            or Path(fixture_principal.root).resolve() != Path(platform.runtime_root).resolve()
            or fixture_principal.sid != platform.science_owner_sid):
            raise Refused('FIXTURE_SCIENCE_OWNER_IDENTITY_REQUIRED')
        return fixture_principal.sid
    if fixture_principal is not None:
        raise Refused('FIXTURE_CREDENTIAL_FORBIDDEN_IN_PRODUCTION')
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
        '[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],
        capture_output=True, text=True, timeout=15)
    if result.returncode or result.stdout.strip() != platform.science_owner_sid:
        raise Refused('AUTHENTICATED_SCIENCE_OWNER_REQUIRED')
    return result.stdout.strip()


def _release_binding(platform, pin):
    inventory = checked(pin)
    if platform.mode == 'PRODUCTION_EQUIVALENT':
        under(pin.path, platform.runtime_root)
        return
    root = Path(__file__).resolve().parents[2]
    if (Path(pin.path).resolve() != root/'CODE_SHA256.json'
        or root.parent != Path(platform.runtime_root).resolve()/'releases'):
        raise Refused('ISSUER_MUST_RUN_FROM_PINNED_INSTALLED_RELEASE')
    verify_acl(platform, pin.path, authority_root=root)
    files = inventory.get('files', {})
    for name in ['trusted_admission.py', 'general.py']:
        p = Path(__file__).parent/name
        row = files.get('platform_v2/apcd_gpu_v2/'+name, {})
        if row.get('sha256') != sha256(p):
            raise Refused('TRUSTED_ISSUER_CODE_NOT_IN_RELEASE_INVENTORY')


def _paths(platform, batch_id):
    base = Path(platform.science_root)/'_admissions'/batch_id
    return {name:under(base/(name+'.json'),platform.science_root) for name in ['reservation', 'genesis', 'admission', 'activation']}


def _plan(platform, manifest_pin, intent_pin, *, issuing=False):
    authority_policy(platform)
    verify_acl(platform, intent_pin.path)
    intent = OwnerIntent.model_validate(checked(intent_pin))
    if intent.fixture_only != (platform.mode == 'PRODUCTION_EQUIVALENT'):
        raise Refused('ISSUANCE_FIXTURE_PRODUCTION_SCOPE_MISMATCH')
    m, profile = validate_batch_inputs(platform, manifest_pin, ledger_required=False)
    if (intent.science_owner != platform.science_owner_id or intent.science_owner_sid != platform.science_owner_sid
        or intent.batch_id != m.batch_id or intent.manifest_file_sha256 != manifest_pin.sha256
        or intent.manifest_sha256 != m.manifest_sha or intent.approved_case_set != m.approved_case_set
        or intent.approved_entry_budget != m.approved_entry_budget
        or intent.profile_id != profile.profile_id or intent.profile_certification_sha256 != profile.certification.sha256):
        raise Refused('SCIENCE_OWNER_INTENT_BINDING_CONFLICT')
    expected_ledger = Path(platform.source_root)/m.batch_id/'science_ledger.json'
    if Path(m.science_ledger).resolve() != expected_ledger.resolve():
        raise Refused('ONE_CANONICAL_BATCH_LEDGER_REQUIRED')
    control = read_json(m.science_control.path)
    if (m.batch_science_hold or control.get('batch_id') != m.batch_id or control.get('manifest_sha') != m.manifest_sha
        or (issuing and (control.get('hold') is not False or control.get('admission_pass') is not True))):
        raise Refused('BATCH_SCIENCE_HOLD')
    if [r.case_id for r in intent.case_provenance] != m.approved_case_set:
        raise Refused('EXACT_CASE_PROVENANCE_REQUIRED')
    for case, provenance in zip(m.cases, intent.case_provenance):
        if provenance.attempt_id != case.attempt_id or provenance.candidate_setup.sha256 != case.source_fsp.sha256:
            raise Refused('CASE_SOURCE_SETUP_BINDING_CONFLICT')
        if issuing:
            for pin in [provenance.source_run_truth, provenance.setup_input, provenance.candidate_setup,
                        provenance.source_manifest]+provenance.auxiliary:
                if sha256(pin.path) != pin.sha256: raise Refused('SOURCE_SETUP_SHA_MISMATCH')
    for pin in intent.scientific_evidence.values():
        if sha256(pin.path) != pin.sha256: raise Refused('SCIENTIFIC_EVIDENCE_SHA_MISMATCH')
    if not intent.scientific_evidence: raise Refused('SCIENTIFIC_EVIDENCE_REQUIRED')
    _release_binding(platform, intent.release_inventory)
    paths = _paths(platform, m.batch_id)
    genesis = dict(schema='APCD_GPU_V21_COUPLING_LEDGER_GENESIS_V1', batch_id=m.batch_id,
        manifest=manifest_pin.model_dump(), intent=intent_pin.model_dump(),
        profile_id=profile.profile_id, certification_sha256=profile.certification.sha256,
        release_inventory=intent.release_inventory.model_dump(), platform_sha256=platform.sha256,
        case_attempts=[dict(case_id=r.case_id,attempt_id=r.attempt_id,case_request_sha256=r.case_request_sha256,
            physics_contract_sha256=r.physics_contract_sha,physics_contract_file_sha256=r.physics_contract.sha256,
            source_fsp_sha256=r.source_fsp.sha256,source_manifest_sha256=r.source_manifest.sha256) for r in m.cases],
        approved_entry_budget=m.approved_entry_budget,per_case_entry_limit=1,no_replay=True,
        science_ledger=str(expected_ledger),fixture_only=intent.fixture_only)
    genesis_sha = digest(genesis)
    issuance = dict(schema='APCD_GPU_V21_ACL_ISSUANCE_V1',genesis_sha256=genesis_sha,
        intent=intent_pin.model_dump(),release_inventory=intent.release_inventory.model_dump(),
        issuer_sid=platform.science_owner_sid,fixture_only=intent.fixture_only)
    admission = Admission(schema_version='APCD_GPU_V21_SCIENCE_ADMISSION_V1',batch_id=m.batch_id,
        science_owner=platform.science_owner_id,manifest_sha=m.manifest_sha,manifest_file_sha=manifest_pin.sha256,
        approved_case_set=m.approved_case_set,approved_entry_budget=m.approved_entry_budget,
        scientific_admission='PASS',engineering_admission='PASS',revoked=False,no_replay=True,
        label_validation_profile=profile.profile_id,profile_certification_sha=profile.certification.sha256,
        science_ledger=str(expected_ledger),issuance=issuance).model_dump(mode='json')
    admission_sha = digest(admission)
    ledger = dict(schema='APCD_COUPLING_BATCH_ENTRY_LEDGER_V1',batch_id=m.batch_id,no_replay=True,replay_count=0,
        admission_sha256=admission_sha,genesis_sha256=genesis_sha,authorized_entry_budget=m.approved_entry_budget,
        entered_case_ids=[],entered_count=0,remaining_unentered_case_ids=m.approved_case_set,
        remaining_unentered_count=m.approved_entry_budget,truth_valid_case_ids=[],truth_valid_count=0,
        labels_valid_case_ids=[],labels_valid_count=0,case_records={})
    reservation = dict(schema='APCD_GPU_V21_BATCH_RESERVATION_V1',batch_id=m.batch_id,
        genesis_sha256=genesis_sha,admission_sha256=admission_sha,science_ledger=str(expected_ledger),
        case_attempts=[dict(case_id=r.case_id,attempt_id=r.attempt_id) for r in m.cases])
    activation = dict(reservation,
        manifest_file_sha256=manifest_pin.sha256,fixture_only=intent.fixture_only,
        status='SCIENCE_READY_NOT_SOLVER_AUTHORIZATION',solver_entry_authorized=False)
    activation['schema']='APCD_GPU_V21_SCIENCE_ACTIVATION_V1'
    return m, paths, genesis, admission, ledger, reservation, activation


def atomic_new_json(path, value, fault=lambda step:None):
    """No-overwrite atomic publication on NTFS; incomplete temp files are inert."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')
    if path.exists():
        if path.read_bytes()!=payload:raise Refused('IMMUTABLE_ISSUANCE_ARTIFACT_CONFLICT')
        return
    temporary=path.parent/('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(payload[:len(payload)//2]);stream.flush();fault('partial_temporary_write')
            stream.write(payload[len(payload)//2:]);stream.flush();os.fsync(stream.fileno())
        try:os.link(temporary,path)
        except FileExistsError:
            if path.read_bytes()!=payload:raise Refused('CONCURRENT_ISSUANCE_ARTIFACT_CONFLICT')
    finally:
        if temporary.exists():temporary.unlink()


def issue_and_initialize(platform, manifest_pin, intent_pin, *, fixture_principal=None,
                         recover=False, fault=lambda step:None):
    """Science Owner only. Does not touch V2 SQLite, PAUSE, Scheduler or a solver."""
    issuer=require_science_owner(platform,fixture_principal)
    with exclusive(Path(platform.science_root)/'.v21_admission.lock'):
        raw_manifest=Manifest.model_validate_json(json.dumps(checked(manifest_pin)))
        already_active=_paths(platform,raw_manifest.batch_id)['activation'].exists()
        m,paths,genesis,admission,ledger,reservation,activation=_plan(platform,manifest_pin,intent_pin,issuing=not already_active)
        identities={(r.case_id.casefold(),r.attempt_id) for r in m.cases}
        for prior in (Path(platform.science_root)/'_admissions').glob('*/reservation.json'):
            old=read_json(prior)
            if prior.resolve()!=paths['reservation'].resolve() and identities & {
                (r['case_id'].casefold(),r['attempt_id']) for r in old['case_attempts']}:
                raise Refused('CROSS_BATCH_ATTEMPT_ALREADY_RESERVED')
        if paths['activation'].exists():
            verify_issued_admission(platform,m,manifest_pin,Admission.model_validate(admission),
                Pin(path=str(paths['admission']),sha256=digest(admission)))
            if not recover:raise Refused('ALREADY_ISSUED_NO_NEW_AUTHORITY')
            return dict(status='ALREADY_ACTIVE_NO_MUTATION',admission=Pin(path=str(paths['admission']),sha256=digest(admission)).model_dump(),genesis_sha256=digest(genesis))
        if paths['reservation'].exists() and not recover:raise Refused('ISSUANCE_RECOVERY_REQUIRED')
        atomic_new_json(paths['reservation'],reservation,fault);fault('reservation_committed')
        atomic_new_json(paths['genesis'],genesis,fault);fault('genesis_committed')
        atomic_new_json(paths['admission'],admission,fault);fault('admission_committed')
        atomic_new_json(Path(m.science_ledger),ledger,fault);fault('ledger_committed')
        # Revalidate pins while holding the issuer lock, before the only activation point.
        if require_science_owner(platform,fixture_principal)!=issuer or _plan(platform,manifest_pin,intent_pin,issuing=True)[2]!=genesis:
            raise Refused('ISSUANCE_INPUT_CHANGED_BEFORE_ACTIVATION')
        atomic_new_json(paths['activation'],activation,fault);fault('activation_committed')
        return dict(status='SCIENCE_READY_NOT_SOLVER_AUTHORIZATION',
            admission=Pin(path=str(paths['admission']),sha256=sha256(paths['admission'])).model_dump(),
            science_ledger=str(m.science_ledger),genesis_sha256=digest(genesis),fixture_only=platform.mode!='PRODUCTION_GPU')


def verify_issued_admission(platform, manifest, manifest_pin, admission, admission_pin):
    if not admission.issuance:raise Refused('TRUSTED_ISSUANCE_REQUIRED')
    issuance=admission.issuance
    if set(issuance)!=set(['schema','genesis_sha256','intent','release_inventory','issuer_sid','fixture_only']):
        raise Refused('UNSUPPORTED_ISSUANCE_BINDING')
    if issuance['schema']!='APCD_GPU_V21_ACL_ISSUANCE_V1':raise Refused('UNSUPPORTED_ISSUANCE_PROTOCOL')
    if issuance['fixture_only']!=(platform.mode=='PRODUCTION_EQUIVALENT'):
        raise Refused('FIXTURE_CREDENTIAL_FORBIDDEN_IN_PRODUCTION')
    result=_plan(platform,manifest_pin,Pin.model_validate(issuance['intent']))
    m,paths,genesis,expected,ledger,reservation,activation=result
    if admission.model_dump(mode='json')!=expected or admission_pin.sha256!=digest(expected):
        raise Refused('ISSUED_ADMISSION_BINDING_CONFLICT')
    if Path(admission_pin.path).resolve()!=paths['admission'].resolve():raise Refused('NONCANONICAL_ISSUED_ADMISSION')
    if sha256(admission_pin.path)!=admission_pin.sha256:raise Refused('ISSUED_ADMISSION_SHA_MISMATCH')
    for name,value in [('reservation',reservation),('genesis',genesis),('admission',expected),('activation',activation)]:
        verify_acl(platform,paths[name])
        if not paths[name].is_file():raise Refused('ISSUANCE_NOT_ATOMICALLY_ACTIVE')
        if read_json(paths[name])!=value:raise Refused('ISSUANCE_COMMIT_EVIDENCE_CONFLICT')
    actual=read_json(m.science_ledger)
    if any(actual.get(key)!=ledger[key] for key in ['schema','batch_id','no_replay','replay_count','admission_sha256','genesis_sha256','authorized_entry_budget']):
        raise Refused('LEDGER_GENESIS_IDENTITY_CONFLICT')
    return dict(verdict='PASS',genesis_sha256=digest(genesis),fixture_only=platform.mode!='PRODUCTION_GPU',solver_entry_authorized=False)


def main(argv=None):
    """Production-only CLI: there is deliberately no fixture credential option."""
    import argparse
    parser=argparse.ArgumentParser(description='Protected Science Owner Admission/genesis transaction; never starts a solver')
    parser.add_argument('operation',choices=['check','issue','recover','verify'])
    for name in ['platform','manifest','intent']:
        parser.add_argument('--'+name,required=True)
        parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args(argv)
    try:
        platform=load_platform(Pin(path=args.platform,sha256=args.platform_sha256))
        if platform.mode!='PRODUCTION_GPU':raise Refused('FIXTURE_CREDENTIALS_HAVE_NO_PRODUCTION_CLI')
        manifest=Pin(path=args.manifest,sha256=args.manifest_sha256)
        intent=Pin(path=args.intent,sha256=args.intent_sha256)
        if args.operation=='check':
            require_science_owner(platform);m,paths,*_=_plan(platform,manifest,intent,issuing=True)
            result=dict(status='INPUTS_VERIFIED_NO_ISSUANCE',batch_id=m.batch_id,solver_entry_authorized=False)
        elif args.operation=='verify':
            m,paths,genesis,admission,*_=_plan(platform,manifest,intent)
            result=verify_issued_admission(platform,m,manifest,Admission.model_validate(admission),
                Pin(path=str(paths['admission']),sha256=digest(admission)))
        else:
            result=issue_and_initialize(platform,manifest,intent,recover=args.operation=='recover')
        print(json.dumps(result,sort_keys=True));return 0
    except Refused as exc:
        print(json.dumps(dict(status='REFUSED',reason=str(exc),solver_entry_authorized=False)));return 2
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps(dict(status='REFUSED',reason='ISSUANCE_INPUT_OR_STORAGE_UNAVAILABLE',error_type=type(exc).__name__,solver_entry_authorized=False)));return 2


if __name__=='__main__':
    raise SystemExit(main())
