"""Data-driven admission and queue for the existing V2 serial execution core.

No science signing, no budget creation, no scheduler, no native backend replacement.
"""
import json
import os
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from .config import StrictModel, digest
from .artifacts import sha256, bundle_inventory
from .ledger import Refused
from .serial import (Pin, SerialConfig, SerialRequest, SerialLedger, CouplingBudget,
                     exclusive, ProductionNativeBackend, NativeTruthValidator,
                     run_serial_case, recover_load_only, replace_json)
from .artifacts import durable_json

SHA = r'^[a-f0-9]{64}$'
ID = r'^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$'
PROFILES = {
    'COUPLING_609D_V1': ('k6_v2_pipeline.ingest', 'load_verified_runner_case', None),
    'COUPLING_DIAG2_TIME_V1': ('k6_v2_pipeline.ingest', 'load_diag2_runner_case', 'validate_diag2_labels'),
}


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise Refused('DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def checked(pin):
    if sha256(pin.path) != pin.sha256: raise Refused('PIN_CHANGED:' + pin.path)
    return read_json(pin.path)


def under(path, root):
    p, r = Path(path).resolve(), Path(root).resolve()
    if p != r and r not in p.parents: raise Refused('AUTHORITY_PATH_ESCAPE')
    return p


class Profile(StrictModel):
    profile_id: Literal['COUPLING_609D_V1', 'COUPLING_DIAG2_TIME_V1']
    truth_toolchain: dict[str, Pin]
    certification: Pin


class Platform(StrictModel):
    schema_version: Literal['APCD_GPU_V21_PLATFORM_V1']
    mode: Literal['PRODUCTION_GPU', 'PRODUCTION_EQUIVALENT']
    runtime_root: str
    science_root: str
    source_root: str
    coupling_root: str
    science_owner_sid: str
    consumer_sid: str
    operator_sids: list[str]
    fdtd_executable: str
    executable_sha256: str = Field(pattern=SHA)
    gpu_resource: Literal['GPU license audit']
    native_h5_name: Literal['run_output.h5']
    heartbeat_seconds: float = Field(gt=0, le=30)
    slots: Literal[1] = 1
    automatic_replays: Literal[0] = 0
    run_policy: Literal['RUN_UNTIL_APPROVED_BATCH_COMPLETE'] = 'RUN_UNTIL_APPROVED_BATCH_COMPLETE'
    profiles: list[Profile]

    @model_validator(mode='after')
    def validate_paths(self):
        for p in [self.runtime_root, self.science_root, self.source_root, self.coupling_root, self.fdtd_executable]:
            if not Path(p).is_absolute(): raise ValueError('ABSOLUTE_PLATFORM_PATH_REQUIRED')
        if self.science_owner_sid == self.consumer_sid: raise ValueError('SCIENCE_OWNER_CONSUMER_MUST_DIFFER')
        if self.mode == 'PRODUCTION_EQUIVALENT':
            if 'zero_solver' not in str(Path(self.runtime_root)).lower(): raise ValueError('FIXTURE_ROOT_REQUIRED')
            for p in [self.science_root, self.source_root, self.coupling_root]: under(p, self.runtime_root)
        elif Path(self.runtime_root).resolve() != Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1').resolve():
            raise ValueError('ONE_CANONICAL_RUNTIME_REQUIRED')
        if len({p.profile_id for p in self.profiles}) != len(self.profiles): raise ValueError('DUPLICATE_PROFILE')
        return self

    @property
    def sha256(self): return digest(self.model_dump())


class Case(StrictModel):
    case_id: str = Field(pattern=ID)
    attempt_id: Literal['attempt_001']
    role: Literal['DEVELOPMENT_GLOBAL', 'DEVELOPMENT_LOCAL_AXIS', 'TIME_CONVERGENCE_DIAGNOSTIC_ONLY']
    ordered_D_nm: tuple[int, int, int, int, int, int]
    source_fsp: Pin
    source_manifest: Pin
    source_acceptance: Pin
    physics_contract: Pin
    physics_contract_sha: str = Field(pattern=SHA)
    simulation_time_s: float = Field(gt=0)
    mesh_nm: float = Field(gt=0)
    auto_shutoff_min: float = Field(gt=0, lt=1)


class Manifest(StrictModel):
    schema_version: Literal['APCD_GPU_V21_BATCH_V1']
    batch_id: str = Field(pattern=ID)
    science_owner: str
    case_count: int = Field(gt=0)
    approved_entry_budget: int = Field(gt=0)
    solver_backend: Literal['LUMERICAL_2025R1_GPU']
    required_truth_artifacts: tuple[Literal['FSP'], Literal['SIBLING_H5'], Literal['FRESH_LOAD']]
    label_validation_profile: Literal['COUPLING_609D_V1', 'COUPLING_DIAG2_TIME_V1']
    approved_case_set: list[str]
    batch_science_hold: bool
    science_control: Pin
    science_ledger: str
    cases: list[Case]
    manifest_sha: str = Field(pattern=SHA)

    @model_validator(mode='after')
    def exact_set(self):
        ids = [c.case_id for c in self.cases]
        if ids != self.approved_case_set or len({cid.casefold() for cid in ids}) != self.case_count or len(ids) != self.case_count:
            raise ValueError('EXACT_APPROVED_CASE_SET_REQUIRED')
        if self.batch_id.upper() in {'CON','PRN','AUX','NUL'} | {'COM'+str(i) for i in range(1,10)} | {'LPT'+str(i) for i in range(1,10)}:
            raise ValueError('WINDOWS_RESERVED_BATCH_NAMESPACE')
        if self.approved_entry_budget != self.case_count: raise ValueError('FINITE_APPROVED_CASE_SET_BUDGET_REQUIRED')
        if self.manifest_sha != digest(self.model_dump(exclude={'manifest_sha'})):
            raise ValueError('MANIFEST_DIGEST_MISMATCH')
        if any(c.physics_contract.sha256 != c.physics_contract_sha for c in self.cases):
            raise ValueError('PHYSICS_PIN_MISMATCH')
        return self


class Admission(StrictModel):
    schema_version: Literal['APCD_GPU_V21_SCIENCE_ADMISSION_V1']
    batch_id: str
    science_owner: str
    manifest_sha: str = Field(pattern=SHA)
    manifest_file_sha: str = Field(pattern=SHA)
    approved_case_set: list[str]
    approved_entry_budget: int
    scientific_admission: Literal['PASS']
    engineering_admission: Literal['PASS']
    revoked: bool
    no_replay: Literal[True]
    label_validation_profile: str
    profile_certification_sha: str = Field(pattern=SHA)
    science_ledger: str


def acl_evidence(path):
    """Read SID DACL, never change it. Unknown ACL is a hard refusal."""
    env = dict(os.environ, APCD_V21_ACL_PATH=str(Path(path).resolve()))
    cmd = "$a=Get-Acl -LiteralPath $env:APCD_V21_ACL_PATH; [pscustomobject]@{owner=$a.GetOwner([System.Security.Principal.SecurityIdentifier]).Value; rules=@($a.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) | ForEach-Object {[pscustomobject]@{sid=$_.IdentityReference.Value;rights=[int]$_.FileSystemRights;allow=($_.AccessControlType -eq 'Allow')}})} | ConvertTo-Json -Depth 4 -Compress"
    p = subprocess.run(['powershell', '-NoProfile', '-Command', cmd], env=env, capture_output=True, text=True)
    if p.returncode: raise Refused('ACL_EVIDENCE_UNAVAILABLE:' + str(path))
    try: return json.loads(p.stdout)
    except Exception as e: raise Refused('ACL_EVIDENCE_INVALID') from e


def verify_acl(platform, path, *, reader=acl_evidence):
    if platform.mode == 'PRODUCTION_EQUIVALENT': under(path, platform.runtime_root); return
    allowed = {platform.science_owner_sid, 'S-1-5-18', 'S-1-5-32-544'}
    # Write data/append/attributes/delete/change DACL/take ownership, including delete-child.
    write = 2 | 4 | 16 | 64 | 256 | 65536 | 262144 | 524288
    root = Path(platform.science_root).resolve(); p = under(path, root)
    for target in [p] + list(p.parents)[:len(p.parents) - len(root.parents)]:
        data = reader(target)
        if data.get('owner') not in allowed: raise Refused('UNTRUSTED_AUTHORITY_OWNER')
        for rule in data.get('rules', []):
            if rule['allow'] and rule['rights'] & write and rule['sid'] not in allowed:
                raise Refused('CONSUMER_OR_FOREIGN_AUTHORITY_WRITE_ALLOWED')


class GeneralConfig(SerialConfig):
    schema_version: Literal['APCD_GPU_V21_SERIAL_V1']
    physical_contract_sha256: str = Field(pattern=SHA)
    batch_id: str
    batch_manifest: Pin
    science_admission: Pin
    science_control: Pin
    platform: Platform
    importer_module: str
    importer_entrypoint: str
    label_validator_entrypoint: str | None
    validation_profile: str

    @model_validator(mode='after')
    def paths(self):
        if self.runtime_root != self.platform.runtime_root or self.mode != self.platform.mode:
            raise ValueError('PLATFORM_AUTHORITY_MISMATCH')
        for p in [self.coupling_ledger, self.queue.path, self.release.path]:
            if not Path(p).is_absolute(): raise ValueError('ABSOLUTE_BATCH_PATH_REQUIRED')
        under(self.coupling_ledger, self.platform.source_root)
        if (self.importer_module, self.importer_entrypoint, self.label_validator_entrypoint) != PROFILES.get(self.validation_profile):
            raise ValueError('UNCERTIFIED_PROFILE_IMPLEMENTATION')
        return self


class GeneralRequest(SerialRequest):
    case_id: str = Field(pattern=ID)
    role: Literal['DEVELOPMENT_GLOBAL', 'DEVELOPMENT_LOCAL_AXIS', 'TIME_CONVERGENCE_DIAGNOSTIC_ONLY']
    physical_contract_sha256: str = Field(pattern=SHA)
    batch_id: str
    simulation_time_s: float
    mesh_nm: float
    auto_shutoff_min: float

    @property
    def dataset_id(self):
        return 'APCD_COUPLING_V3_TIME_DIAG2_V1' if self.role=='TIME_CONVERGENCE_DIAGNOSTIC_ONLY' else self.batch_id


def is_general(config): return isinstance(config, GeneralConfig)


def load_batch(platform, manifest_pin, admission_pin):
    for pin in [manifest_pin, admission_pin]: verify_acl(platform, pin.path)
    m = Manifest.model_validate_json(json.dumps(checked(manifest_pin))); a = Admission.model_validate(checked(admission_pin))
    if (a.batch_id != m.batch_id or a.science_owner != m.science_owner or a.science_owner != platform.science_owner_sid
        or a.manifest_sha != m.manifest_sha or a.manifest_file_sha != manifest_pin.sha256
        or a.approved_case_set != m.approved_case_set or a.approved_entry_budget != m.approved_entry_budget
        or a.label_validation_profile != m.label_validation_profile or a.science_ledger != m.science_ledger
        or a.revoked): raise Refused('SCIENCE_ADMISSION_UNBOUND_OR_REVOKED')
    profiles = [p for p in platform.profiles if p.profile_id == m.label_validation_profile]
    if len(profiles) != 1: raise Refused('UNSUPPORTED_SCIENCE_PROFILE')
    profile = profiles[0]; verify_acl(platform, profile.certification.path)
    certification = checked(profile.certification)
    if (a.profile_certification_sha != profile.certification.sha256 or certification.get('verdict') != 'PASS'
        or certification.get('profile_id') != profile.profile_id
        or certification.get('toolchain') != {k: p.sha256 for k,p in profile.truth_toolchain.items()}):
        raise Refused('SCIENCE_PROFILE_CERTIFICATION_REQUIRED')
    verify_acl(platform, m.science_control.path)
    for case in m.cases:
        if Path(case.source_fsp.path).suffix.lower()!='.fsp':raise Refused('ONLY_NATIVE_FSP_SOURCE_ALLOWED')
        for pin in [case.source_fsp, case.source_manifest, case.physics_contract]:
            under(pin.path, platform.source_root)
            if sha256(pin.path) != pin.sha256: raise Refused('BATCH_SOURCE_SHA_MISMATCH')
        contract = checked(case.physics_contract)
        # A certified native LOAD receipt handles scientific contract-specific nesting.
        # If these common fields are present, additionally cross-check them without rewriting science.
        if any(key in contract and contract[key] != expected for key,expected in
               [('simulation_time_s',case.simulation_time_s),('mesh_nm',case.mesh_nm),('auto_shutoff_min',case.auto_shutoff_min)]):
            raise Refused('PHYSICAL_TIME_MESH_STOP_CONTRACT_MISMATCH')
        verify_acl(platform,case.source_acceptance.path)
        proof=checked(case.source_acceptance)
        if (proof.get('verdict')!='PASS' or proof.get('fresh_load_verified') is not True
            or proof.get('case_id')!=case.case_id or proof.get('source_fsp_sha')!=case.source_fsp.sha256
            or proof.get('attempt_id')!=case.attempt_id or proof.get('ordered_D_nm')!=list(case.ordered_D_nm)
            or proof.get('physics_contract_sha')!=case.physics_contract_sha
            or proof.get('simulation_time_s')!=case.simulation_time_s or proof.get('mesh_nm')!=case.mesh_nm
            or proof.get('auto_shutoff_min')!=case.auto_shutoff_min):
            raise Refused('SCIENTIFIC_SOURCE_LOAD_ACCEPTANCE_REQUIRED')
    under(m.science_ledger, platform.source_root)
    return m, a, profile


def build_requests(platform, manifest_pin, admission_pin):
    m, a, p = load_batch(platform, manifest_pin, admission_pin)
    module, entry, labels = PROFILES[m.label_validation_profile]
    result = []
    for row in m.cases:
        cfg = GeneralConfig(schema_version='APCD_GPU_V21_SERIAL_V1', mode=platform.mode,
            runtime_root=platform.runtime_root, coupling_ledger=m.science_ledger, queue=manifest_pin,
            release=admission_pin, fdtd_executable=platform.fdtd_executable, executable_sha256=platform.executable_sha256,
            gpu_resource=platform.gpu_resource, native_h5_name=platform.native_h5_name,
            heartbeat_seconds=platform.heartbeat_seconds, physical_contract_sha256=row.physics_contract_sha,
            truth_toolchain=p.truth_toolchain, coupling_root=platform.coupling_root, batch_id=m.batch_id,
            batch_manifest=manifest_pin, science_admission=admission_pin, science_control=m.science_control,
            platform=platform, importer_module=module, importer_entrypoint=entry,
            label_validator_entrypoint=labels, validation_profile=m.label_validation_profile)
        req = GeneralRequest(case_id=row.case_id, attempt_id=row.attempt_id, role=row.role,
            ordered_D_nm=row.ordered_D_nm, pre_fsp=row.source_fsp.path, pre_fsp_sha256=row.source_fsp.sha256,
            source_manifest=row.source_manifest, physical_contract=row.physics_contract,
            physical_contract_sha256=row.physics_contract_sha, config_sha256=cfg.sha256, batch_id=m.batch_id,
            simulation_time_s=row.simulation_time_s, mesh_nm=row.mesh_nm, auto_shutoff_min=row.auto_shutoff_min)
        result.append((cfg, req))
    return m, result


def science_gate(config):
    m, a, p = load_batch(config.platform, config.batch_manifest, config.science_admission)
    # control is mutable, owner-only: SHA is registration evidence, live HOLD must always be read.
    verify_acl(config.platform, m.science_control.path)
    control = read_json(m.science_control.path)
    if control.get('batch_id') != m.batch_id or control.get('manifest_sha') != m.manifest_sha:
        raise Refused('SCIENCE_CONTROL_BINDING_MISMATCH')
    if m.batch_science_hold or control.get('hold') is not False or control.get('admission_pass') is not True:
        raise Refused('BATCH_SCIENCE_HOLD')
    return m


def validate_general(config, request):
    m = science_gate(config)
    _, pairs = build_requests(config.platform, config.batch_manifest, config.science_admission)
    expected = [r for c,r in pairs if r.case_id == request.case_id]
    if len(expected) != 1 or expected[0].request_sha256 != request.request_sha256:
        raise Refused('UNREGISTERED_OR_CROSS_BATCH_REQUEST')
    if sha256(config.fdtd_executable) != config.executable_sha256: raise Refused('EXECUTABLE_PIN_CHANGED')
    with sqlite3.connect(Path(config.runtime_root)/'ledger.sqlite3') as db:
        row = db.execute('SELECT paused,manifest_sha,admission_sha FROM v21_batches WHERE batch_id=?', (m.batch_id,)).fetchone()
        if not row or row[1:] != (config.batch_manifest.sha256,config.science_admission.sha256): raise Refused('BATCH_NOT_REGISTERED')
        if row[0]: raise Refused('OPERATOR_PAUSED_NEW_ENTRIES')
    return checked(config.science_admission)


class GeneralBudget(CouplingBudget):
    def __init__(self, config):
        super().__init__(config)
        self.receipts = self.path.parent / ('V21_ENTRY_EVIDENCE_' + config.batch_id)

    def uncertainty(self):
        data=read_json(self.path)
        pending=set(data['entered_case_ids'])-set(data['labels_valid_case_ids'])
        for path in self.receipts.glob('*__attempt_001.json'):
            row=read_json(path)
            if row.get('case_id') not in data['labels_valid_case_ids']:pending.add(row.get('case_id','UNKNOWN'))
        return sorted(pending)

    def validate(self, request):
        validate_general(self.config, request)
        m = Manifest.model_validate_json(json.dumps(checked(self.config.batch_manifest)))
        data = super().validate(request)
        if (data.get('batch_id') != m.batch_id or data.get('admission_sha256') != self.config.science_admission.sha256
            or data['authorized_development_case_count'] != m.approved_entry_budget
            or set(data['entered_case_ids']) | set(data['remaining_unentered_case_ids']) != set(m.approved_case_set)):
            raise Refused('SCIENCE_LEDGER_AUTHORITY_OR_CASE_SET_CONFLICT')
        if data['entered_count'] >= m.approved_entry_budget: raise Refused('BATCH_BUDGET_EXHAUSTED')
        if self.uncertainty(): raise Refused('UNCERTAIN_SCIENCE_ENTRY_HOLD')
        return data

    def mark_launch_request(self, request, token):
        # Recheck HOLD/pause and immutable admission immediately before the original launch fence.
        validate_general(self.config, request)
        return super().mark_launch_request(request, token)

    def finish_truth(self, request, evidence):
        # Batch-specific scientific publication; never label diagnostics as legacy development.
        validation=evidence.get('validation',{})
        if (validation.get('verdict')!='PASS' or validation.get('outputs')!=609
            or validation.get('fresh_load_verified') is not True
            or validation.get('actual_importer')!=self.config.importer_entrypoint):
            raise Refused('CERTIFIED_PROFILE_TRUTH_REQUIRED')
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data=read_json(self.path);record=data['case_records'][request.case_id]
            if record.get('request_sha256')!=request.request_sha256 or record.get('phase') not in ['V2_ENTRY_UNCERTAIN','V2_TRUTH_VALID']:
                raise Refused('BATCH_TERMINAL_BINDING_CONFLICT')
            if self.config.mode=='PRODUCTION_GPU':
                labels=validation.get('labels_artifact',{})
                if sha256(labels.get('path',''))!=labels.get('sha256'):raise Refused('LABEL_ARTIFACT_SHA_MISMATCH')
            receipt=dict(schema='APCD_GPU_V21_SCIENCE_TERMINAL_V1',batch_id=request.batch_id,
                case_id=request.case_id,attempt_id=request.attempt_id,role=request.role,
                request_sha256=request.request_sha256,admission_sha256=self.config.science_admission.sha256,
                profile_id=self.config.validation_profile,entry_count=1,replay_count=0,
                truth_valid=True,labels_valid=True,evidence=evidence)
            target=self.path.parent/('V21_TERMINAL_'+request.case_id+'__attempt_001.json')
            if target.exists():
                if read_json(target)!=receipt:raise Refused('IMMUTABLE_SCIENCE_TERMINAL_CONFLICT')
            else:durable_json(target,receipt)
            for key,count in [('truth_valid_case_ids','truth_valid_count'),('labels_valid_case_ids','labels_valid_count')]:
                if request.case_id not in data[key]:data[key].append(request.case_id);data[count]+=1
            record.update(phase='V2_TRUTH_VALID',truth_valid=True,labels_valid=True,evidence=evidence,
                terminal_receipt=str(target),terminal_receipt_sha256=sha256(target))
            replace_json(self.path,data)


class GeneralLedger(SerialLedger):
    def register(self, request, config):
        if request.config_sha256 != config.sha256: raise Refused('CONFIG_REQUEST_MISMATCH')
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM tasks WHERE state NOT IN ('TRUTH_VALID','REGISTERED') LIMIT 1").fetchone():
                raise Refused('UNRESOLVED_OLD_EXECUTION_HOLD')
            try:
                db.execute('INSERT INTO tasks(case_id,attempt_id,request_sha,config_sha,payload,state) VALUES(?,?,?,?,?,?)',
                    (request.case_id, request.attempt_id, request.request_sha256, config.sha256, request.model_dump_json(),'REGISTERED'))
            except sqlite3.IntegrityError as e: raise Refused('DUPLICATE_CASE_ATTEMPT_OR_REQUEST') from e
            self.event(db,request.request_sha256,'REGISTERED',request.model_dump())


class Registry:
    def __init__(self, platform):
        self.platform = platform
        self.ledger = GeneralLedger(Path(platform.runtime_root)/'ledger.sqlite3')
        with self.ledger.transaction() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS v21_platform(id INTEGER PRIMARY KEY CHECK(id=1),sha TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v21_batches(seq INTEGER PRIMARY KEY AUTOINCREMENT,batch_id TEXT COLLATE NOCASE UNIQUE NOT NULL,
manifest_path TEXT NOT NULL,manifest_sha TEXT NOT NULL,admission_path TEXT NOT NULL,admission_sha TEXT NOT NULL,
paused INTEGER NOT NULL CHECK(paused IN (0,1)),started INTEGER NOT NULL CHECK(started IN (0,1)),status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS v21_case_ids(case_id TEXT COLLATE NOCASE PRIMARY KEY,batch_id TEXT NOT NULL);''')
            old = db.execute('SELECT sha FROM v21_platform WHERE id=1').fetchone()
            if old and old['sha'] != platform.sha256: raise Refused('PLATFORM_CONFIG_MISMATCH')
            db.execute('INSERT OR IGNORE INTO v21_platform VALUES(1,?)',(platform.sha256,))

    def submit(self, manifest_pin, admission_pin):
        m, pairs = build_requests(self.platform,manifest_pin,admission_pin)
        with self.ledger.transaction() as db:
            old = db.execute('SELECT * FROM v21_batches WHERE batch_id=?',(m.batch_id,)).fetchone()
            if old:
                if old['manifest_sha'] != manifest_pin.sha256 or old['admission_sha'] != admission_pin.sha256: raise Refused('BATCH_IMMUTABLE_BINDING_CONFLICT')
                return 'ALREADY_SUBMITTED'
            for cfg,req in pairs:
                if db.execute('SELECT 1 FROM tasks WHERE case_id=? COLLATE NOCASE',(req.case_id,)).fetchone(): raise Refused('HISTORICAL_CASE_ID_REUSE')
                try: db.execute('INSERT INTO v21_case_ids VALUES(?,?)',(req.case_id,m.batch_id))
                except sqlite3.IntegrityError as e: raise Refused('CROSS_BATCH_CASE_ID_REUSE') from e
            registration=Path(self.platform.runtime_root)/'submission_receipts'/(m.batch_id+'.json')
            registration.parent.mkdir(exist_ok=True)
            proof=dict(batch_id=m.batch_id,manifest=manifest_pin.model_dump(),admission=admission_pin.model_dump())
            if registration.exists():
                if read_json(registration)!=proof:raise Refused('IMMUTABLE_SUBMISSION_CONFLICT')
            else:durable_json(registration,proof)
            db.execute('INSERT INTO v21_batches(batch_id,manifest_path,manifest_sha,admission_path,admission_sha,paused,started,status) VALUES(?,?,?,?,?,1,0,?)',
                (m.batch_id,manifest_pin.path,manifest_pin.sha256,admission_pin.path,admission_pin.sha256,'SUBMITTED_PAUSED'))
        return 'SUBMITTED_PAUSED'

    def global_entry_gate(self):
        rows={r['batch_id']:r for r in self.status()['batches']}
        for path in (Path(self.platform.runtime_root)/'submission_receipts').glob('*.json'):
            proof=read_json(path);row=rows.get(proof.get('batch_id'))
            if not row or proof.get('manifest')!={'path':row['manifest_path'],'sha256':row['manifest_sha']} or proof.get('admission')!={'path':row['admission_path'],'sha256':row['admission_sha']}:
                raise Refused('LOCAL_REGISTRY_LOST_OR_SUBMISSION_UNCERTAIN')
        for row in rows.values():
            _,pairs=build_requests(self.platform,Pin(path=row['manifest_path'],sha256=row['manifest_sha']),Pin(path=row['admission_path'],sha256=row['admission_sha']))
            if GeneralBudget(pairs[0][0]).uncertainty():raise Refused('CROSS_BATCH_UNCERTAIN_ENTRY_HOLD')

    def operate(self, batch_id, paused):
        with self.ledger.transaction() as db:
            row=db.execute('SELECT * FROM v21_batches WHERE batch_id=?',(batch_id,)).fetchone()
            if not row: raise Refused('UNKNOWN_BATCH')
            if not paused:
                _, pairs=build_requests(self.platform,Pin(path=row['manifest_path'],sha256=row['manifest_sha']),Pin(path=row['admission_path'],sha256=row['admission_sha']))
                science_gate(pairs[0][0])
            db.execute('UPDATE v21_batches SET paused=?,started=1 WHERE batch_id=?',(int(paused),batch_id))
            self.ledger.event(db,None,'OPERATOR_PAUSE' if paused else 'OPERATOR_RESUME',{'batch_id':batch_id})

    def status(self):
        with self.ledger.connect() as db:
            batches=[dict(r) for r in db.execute('SELECT * FROM v21_batches ORDER BY seq')]
        return dict(platform_sha=self.platform.sha256,batches=batches,execution=self.ledger.audit())

    def public_status(self):
        # Status is metadata only: never expose historical response, owner tokens or private paths.
        snapshot=self.status()
        return dict(platform_sha=snapshot['platform_sha'],gpu_slots=1,
            batches=[{k:r[k] for k in ['batch_id','paused','started','status','manifest_sha','admission_sha']} for r in snapshot['batches']],
            slot_occupied=bool(snapshot['execution']['slot']['token']),
            task_counts={state:sum(r['state']==state for r in snapshot['execution']['tasks'])
                         for state in sorted({r['state'] for r in snapshot['execution']['tasks']})})

    def drain(self, *, backend=None, validator_factory=None, fault=lambda step:None):
        if self.platform.mode=='PRODUCTION_GPU' and (backend is not None or validator_factory is not None):
            raise Refused('PRODUCTION_IMPLEMENTATION_OVERRIDE_FORBIDDEN')
        impl = backend if backend is not None else ProductionNativeBackend()
        with exclusive(Path(self.platform.runtime_root)/'.v2_controller.lock'):
            slot=self.ledger.audit()['slot']
            if slot['token']:
                candidates=[]
                for row in self.status()['batches']:
                    _, pairs=build_requests(self.platform,Pin(path=row['manifest_path'],sha256=row['manifest_sha']),Pin(path=row['admission_path'],sha256=row['admission_sha']))
                    candidates.extend((cfg,req) for cfg,req in pairs if req.request_sha256==slot['request_sha'])
                if len(candidates)!=1: raise Refused('PERSISTED_OWNER_LOAD_ONLY_REVIEW_REQUIRED')
                cfg,req=candidates[0]
                validator=validator_factory(cfg) if validator_factory else NativeTruthValidator(cfg)
                # Existing fresh LOAD recovery checks PID+creation-time and returned engine evidence.
                # It has no backend/solver argument, cannot replay, and preserves science HOLD/pause.
                recover_load_only(cfg,req,self.ledger,validator)
            self.global_entry_gate()
            for row in self.status()['batches']:
                if row['paused'] or not row['started']: continue
                manifest=Pin(path=row['manifest_path'],sha256=row['manifest_sha']); admission=Pin(path=row['admission_path'],sha256=row['admission_sha'])
                m,pairs=build_requests(self.platform,manifest,admission)
                try: science_gate(pairs[0][0])
                except Refused as e:
                    with self.ledger.transaction() as db: db.execute('UPDATE v21_batches SET status=? WHERE batch_id=?',('SCIENCE_HOLD:'+str(e),m.batch_id))
                    continue
                with exclusive(Path(m.science_ledger).with_suffix('.v2_controller.lock')):
                    for cfg,req in pairs:
                        with self.ledger.connect() as db:
                            paused=db.execute('SELECT paused FROM v21_batches WHERE batch_id=?',(m.batch_id,)).fetchone()[0]
                        if paused: break
                        old=[t for t in self.ledger.audit()['tasks'] if t['case_id']==req.case_id]
                        if old:
                            external=read_json(cfg.coupling_ledger)
                            if (old[0]['request_sha']!=req.request_sha256 or old[0]['state']!='TRUTH_VALID'
                                or external['case_records'].get(req.case_id,{}).get('phase')!='V2_TRUTH_VALID'):
                                raise Refused('PREVIOUS_ATTEMPT_NO_REPLAY')
                            bundle=json.loads(old[0]['bundle'])['bundle']
                            if bundle_inventory(Path(bundle['path'])/'run.fsp',cfg.native_h5_name)!=bundle['files']:
                                raise Refused('PERSISTED_TRUTH_INTEGRITY_CONFLICT')
                            continue
                        self.global_entry_gate()
                        validate_general(cfg,req)
                        validator=validator_factory(cfg) if validator_factory else NativeTruthValidator(cfg)
                        self.ledger.register(req,cfg)
                        run_serial_case(cfg,req,self.ledger,impl,validator,fault=fault)
                        if self.ledger.audit()['slot']['token']: raise Refused('TRUTH_BEFORE_NEXT_REQUIRED')
                    with self.ledger.transaction() as db:
                        done=db.execute("SELECT COUNT(*) FROM tasks WHERE state='TRUTH_VALID' AND case_id IN (SELECT case_id FROM v21_case_ids WHERE batch_id=?)",(m.batch_id,)).fetchone()[0]
                        db.execute('UPDATE v21_batches SET status=? WHERE batch_id=?',('COMPLETE' if done==m.case_count else 'PAUSED',m.batch_id))
        return self.status()


def load_platform(pin):
    platform = Platform.model_validate(checked(pin))
    if platform.mode == 'PRODUCTION_GPU':
        canonical = Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1/platform_config.json').resolve()
        if Path(pin.path).resolve() != canonical: raise Refused('CANONICAL_PLATFORM_CONFIG_REQUIRED')
        allowed = {'S-1-5-18','S-1-5-32-544'}
        write = 2 | 4 | 16 | 64 | 256 | 65536 | 262144 | 524288
        for target in [canonical, canonical.parent]:
            acl = acl_evidence(target)
            if acl.get('owner') not in allowed or any(r['allow'] and r['rights'] & write and r['sid'] not in allowed for r in acl.get('rules',[])):
                raise Refused('PLATFORM_INSTALLER_ACL_REQUIRED')
    return platform


def require_operator(platform):
    if platform.mode == 'PRODUCTION_EQUIVALENT': return
    r=subprocess.run(['powershell','-NoProfile','-Command','[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value'],capture_output=True,text=True)
    if r.returncode or r.stdout.strip() not in platform.operator_sids: raise Refused('OPERATOR_IDENTITY_NOT_AUTHORIZED')

