"""Explicit V3 batch adapters for the existing serial core, never another allocator."""
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import Field, model_validator

from .artifacts import durable_json, sha256
from .config import CONTRACT_SHA, StrictModel, digest
from .ledger import Refused
from .serial import Pin, SerialConfig, SerialRequest, CouplingBudget, exclusive, replace_json

DATASET = 'APCD_COUPLING_V3_DOE56'
FROZEN_MANIFEST_SHA = 'f0231e22b169f82f9239d7e89c3455f877ea85d493c422274f664c9dd91ba667'
MESH4_SHA = 'f8a59ebd65b168e52f76bde1f4bb7f91d545dfd5fd1838a32ab79e0548967d92'
ROLES = dict(DIAGNOSTIC_REPEAT='DIAGNOSTIC_5NM', DIAGNOSTIC_MESH='DIAGNOSTIC_4NM',
             DEVELOPMENT_LOCAL='DEVELOPMENT', DEVELOPMENT_GLOBAL='DEVELOPMENT',
             SEALED_LOCAL='SEALED_EVALUATION', SEALED_GLOBAL='SEALED_EVALUATION')


class Window(StrictModel):
    deadline_unix: float
    report_buffer_seconds: Literal[1800] = 1800
    postprocessing_margin_seconds: Literal[300] = 300
    historical_5nm_q95_seconds: float = Field(ge=716.230)
    unmeasured_4nm_factor: Literal[2.5] = 2.5


class V3Config(SerialConfig):
    schema_version: Literal['APCD_V2_REGISTERED_V3_SERIAL_V1']
    dataset_id: Literal['APCD_COUPLING_V3_DOE56']
    registry: Pin
    budget_authority: Pin
    engineering_acceptance: Pin
    science_acceptance: Pin
    sealed_identity_acceptance: Pin
    identity_authority: Pin
    diagnostic_gate: Pin | None = None
    v3_data_root: str
    window: Window
    importer_module: Literal['k6_v2_pipeline.v3_ingest'] = 'k6_v2_pipeline.v3_ingest'

    @model_validator(mode='after')
    def paths(self):
        # Override only the legacy fixed128 budget path; leave SerialConfig itself strict.
        all_paths = [self.runtime_root, self.coupling_ledger, self.fdtd_executable,
                     self.v3_data_root, self.coupling_root, self.queue.path, self.release.path]
        if not all(Path(p).is_absolute() for p in all_paths):
            raise ValueError('ABSOLUTE_REGISTERED_PATHS_REQUIRED')
        root = Path(self.runtime_root).resolve(); data = Path(self.v3_data_root).resolve()
        if self.mode == 'PRODUCTION_EQUIVALENT':
            if 'zero_solver' not in str(root).lower(): raise ValueError('FIXTURE_ROOT_REQUIRED')
            for p in [self.coupling_ledger, self.v3_data_root, self.registry.path,
                      self.budget_authority.path, self.queue.path, self.release.path]:
                if root not in Path(p).resolve().parents: raise ValueError('FIXTURE_BOUNDARY')
        else:
            if root != Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1').resolve():
                raise ValueError('ONE_CANONICAL_V2_EXECUTION_LEDGER_REQUIRED')
            if data != root/'v3_data': raise ValueError('V3_CUSTODY_ROOT_REQUIRED')
            old = Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json').resolve()
            if Path(self.coupling_ledger).resolve() == old: raise ValueError('OLD128_AUTHORITY_FORBIDDEN')
            canonical_coupling=Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1').resolve()
            authority_root=canonical_coupling/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1'
            if Path(self.coupling_root).resolve()!=canonical_coupling or Path(self.coupling_ledger).resolve()!=authority_root/'V3_EXECUTION_LEDGER_V1.json':
                raise ValueError('SINGLE_CANONICAL_COUPLING_V3_BUDGET_REQUIRED')
            if Path(self.budget_authority.path).resolve()!=authority_root/'interface_amendment_01/V3_BUDGET_AUTHORITY_V1.json':
                raise ValueError('FORMAL_STATIC_V3_BUDGET_AUTHORITY_REQUIRED')

            if not {'lumapi','postprocessor','decoder','importer','incident_power_helper'} <= self.truth_toolchain.keys():
                raise ValueError('PINNED_NATIVE_TOOLCHAIN_REQUIRED')
        return self


class V3Request(SerialRequest):
    # Membership, not a broader legacy regex, decides every new scientific identity.
    case_id: str
    dataset_id: Literal['APCD_COUPLING_V3_DOE56']
    role: Literal['DIAGNOSTIC_REPEAT','DIAGNOSTIC_MESH','DEVELOPMENT_LOCAL',
                  'DEVELOPMENT_GLOBAL','SEALED_LOCAL','SEALED_GLOBAL']
    physical_contract_sha256: Literal[CONTRACT_SHA, MESH4_SHA]
    registry_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    frozen_case_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


def registry_cases(config):
    reg = config.registry.read()
    if reg.get('schema') != 'V3_REGISTERED_BATCH_V1' or reg.get('dataset_id') != DATASET:
        raise Refused('REGISTERED_BATCH_SCHEMA_REQUIRED')
    if reg.get('frozen_manifest_sha256') != FROZEN_MANIFEST_SHA:
        raise Refused('FROZEN_DOE_PIN_MISMATCH')
    rows = reg.get('cases', [])
    if len(rows) != 56 or len({x['case_id'] for x in rows}) != 56:
        raise Refused('EXACT56_IDENTITIES_REQUIRED')
    counts = {r:sum(ROLES.get(x['role']) == r for x in rows) for r in set(ROLES.values())}
    if counts != dict(DIAGNOSTIC_5NM=2,DIAGNOSTIC_4NM=2,DEVELOPMENT=44,SEALED_EVALUATION=8):
        raise Refused('FROZEN_ROLE_COUNTS_MISMATCH')
    for x in rows:
        if x['attempt_id'] != 'attempt_001': raise Refused('ATTEMPT001_ONLY')
        expected = MESH4_SHA if x['role'] == 'DIAGNOSTIC_MESH' else CONTRACT_SHA
        if x['physical_contract_sha256'] != expected: raise Refused('REGISTERED_CONTRACT_ROLE_CONFLICT')
        if x['frozen_case_sha256'] != digest(x['frozen_case']): raise Refused('FROZEN_CASE_DIGEST_CHANGED')
        f = x['frozen_case']
        if any(x[k] != f[k] for k in ['case_id','role','ordered_D_nm']):
            raise Refused('FROZEN_REGISTRATION_CONFLICT')
    return {x['case_id']:x for x in rows}


def validate_registered(config, request):
    if not isinstance(config,V3Config) or not isinstance(request,V3Request):
        raise Refused('EXPLICIT_REGISTERED_TYPES_REQUIRED')
    if request.config_sha256 != config.sha256 or request.registry_sha256 != config.registry.sha256:
        raise Refused('REGISTERED_CONFIG_OR_REGISTRY_BINDING_MISMATCH')
    row = registry_cases(config).get(request.case_id)
    if row is None: raise Refused('UNREGISTERED_CASE')
    for k in ['attempt_id','role','physical_contract_sha256','pre_fsp_sha256','frozen_case_sha256']:
        if getattr(request,k) != row[k]: raise Refused('REGISTERED_CASE_BINDING_MISMATCH:'+k)
    if list(request.ordered_D_nm) != row['ordered_D_nm']: raise Refused('REGISTERED_GEOMETRY_MISMATCH')
    for k in ['source_manifest','physical_contract']:
        if getattr(request,k).model_dump() != row[k]: raise Refused('REGISTERED_SOURCE_LOCATION_MISMATCH')
    if request.pre_fsp != row['pre_fsp'] or sha256(request.pre_fsp) != row['pre_fsp_sha256']:
        raise Refused('REGISTERED_FSP_CHANGED')
    manifest=request.source_manifest.read(); request.physical_contract.read()
    if request.physical_contract.sha256 != request.physical_contract_sha256:
        raise Refused('ACTUAL_CONTRACT_PIN_MISMATCH')
    if manifest.get('case_id') != request.case_id or manifest.get('attempt_id') != request.attempt_id:
        raise Refused('SOURCE_MANIFEST_IDENTITY_MISMATCH')
    if manifest.get('physical_contract_sha256') != request.physical_contract_sha256:
        raise Refused('SOURCE_MANIFEST_CONTRACT_MISMATCH')
    for desc in manifest['artifacts'].values():
        if sha256(Path(request.source_manifest.path).parent/desc['path']) != desc['sha256']:
            raise Refused('SOURCE_ARTIFACT_PIN_CHANGED')
    if request.role == 'DIAGNOSTIC_MESH':
        binding=Pin.model_validate(row['actual_contract_binding']).read()
        if binding['actual_pre_fsp']['sha256'] != request.pre_fsp_sha256 or binding['actual_physical_contract']['sha256'] != MESH4_SHA or binding['core_step_nm'] != [4,4,4]:
            raise Refused('ACTUAL_MESH4_LOAD_BINDING_REQUIRED')
    release=config.release.read()
    if release.get('schema') != 'APCD_V3_FINITE_SERIAL_RELEASE_V1' or release.get('dataset_id') != DATASET:
        raise Refused('REGISTERED_FINITE_RELEASE_REQUIRED')
    if release.get('queue_sha256') != config.queue.sha256 or release.get('registry_sha256') != config.registry.sha256 or request.admission_sha256 not in release.get('requests',[]):
        raise Refused('REGISTERED_RELEASE_BINDING_MISMATCH')
    if release.get('expires_unix',0) <= time.time(): raise Refused('RELEASE_EXPIRED')
    queue=config.queue.read()
    if queue.get('registry_sha256') != config.registry.sha256 or queue.get('ordered_cases') != list(registry_cases(config).values()):
        raise Refused('QUEUE_REGISTRY_CONFLICT')
    if sha256(config.fdtd_executable) != config.executable_sha256: raise Refused('EXECUTABLE_PIN_CHANGED')
    if config.mode == 'PRODUCTION_GPU':
        for p in [config.engineering_acceptance,config.science_acceptance,config.sealed_identity_acceptance]:
            accepted=p.read()
            if accepted.get('verdict') != 'PASS' or accepted.get('registry_sha256') != config.registry.sha256:
                raise Refused('INDEPENDENT_INSTALL_ADMISSION_NOT_PASS')
        if release.get('science_authorized') is not True: raise Refused('SCIENCE_RELEASE_DENY')
        from .v3_identity import current_token_evidence
        token=current_token_evidence()
        if token['user_sid'] != 'S-1-5-21-2958591235-2706656562-1210676212-1001' or not token['elevated']:
            raise Refused('CONTROLLED_PRODUCTION_CUSTODIAN_REQUIRED')
    if ROLES[request.role] not in ['DIAGNOSTIC_5NM','DIAGNOSTIC_4NM']:
        if config.diagnostic_gate is None: raise Refused('PREREGISTERED_DIAGNOSTIC_GATE_REQUIRED')
        gate=config.diagnostic_gate.read()
        if gate.get('schema') != 'V3_COUPLING_NUMERICAL_GATE_RECEIPT_V1' or gate.get('advance_to_development') is not True or gate.get('inputs',{}).get('registry',{}).get('sha256') != config.registry.sha256:
            raise Refused('DIAGNOSTIC_ADVANCEMENT_NOT_PASS')
    return release


def storage_root(config, request):
    role=ROLES[request.role]
    name='V3_DIAGNOSTIC' if role.startswith('DIAGNOSTIC') else 'V3_'+role
    return Path(config.v3_data_root)/name/'production'


def time_gate(config, request, *, now=None):
    now=time.time() if now is None else now
    data=json.loads(Path(config.coupling_ledger).read_text())
    history=[r['end_to_end_seconds'] for r in data.get('case_records',{}).values()
             if r.get('phase')=='V2_TRUTH_VALID' and r.get('physical_contract_sha256')==request.physical_contract_sha256 and r.get('end_to_end_seconds',0)>0]
    factor=config.window.unmeasured_4nm_factor if request.role=='DIAGNOSTIC_MESH' else 1
    bound=max(config.window.historical_5nm_q95_seconds*factor, max(history,default=0))
    estimate=bound+config.window.postprocessing_margin_seconds
    if request.role=='DIAGNOSTIC_MESH':estimate=max(2091,estimate)
    end=min(config.window.deadline_unix,config.release.read()['expires_unix'])
    result=dict(now_unix=now,deadline_unix=end,remaining_seconds=end-now,
                contract_sha256=request.physical_contract_sha256,estimated_case_seconds=estimate,
                report_buffer_seconds=config.window.report_buffer_seconds,
                allow_new_entry=now+estimate+config.window.report_buffer_seconds<=end,
                stop_policy='NO_NEW_ENTRY; NEVER_KILL_ADMITTED_SOLVER')
    if not result['allow_new_entry']: raise Refused('WINDOW_INSUFFICIENT_NO_NEW_ENTRY')
    return result


class V3Budget(CouplingBudget):
    def __init__(self,config):
        super().__init__(config)
        self.receipts=self.path.parent/'V3_ENTRY_EVIDENCE_V1'

    def validate(self,request):
        rows=registry_cases(self.config);data=json.loads(self.path.read_text())
        authority=self.config.budget_authority.read()
        if authority.get('dataset_id') != DATASET or authority.get('max_new_entries') != 56 or authority.get('scientific_budget_approved') is not True:
            raise Refused('INDEPENDENT_COUPLING_BUDGET_NOT_APPROVED')
        if data.get('dataset_id') != DATASET or data.get('authorized_case_count') != 56:
            raise Refused('INDEPENDENT_V3_LEDGER_REQUIRED')
        keys=['entered_case_ids','remaining_unentered_case_ids','truth_valid_case_ids','labels_valid_case_ids']
        counts=['entered_count','remaining_unentered_count','truth_valid_count','labels_valid_count']
        for key,count in zip(keys,counts):
            if len(set(data[key])) != len(data[key]) or len(data[key]) != data[count]: raise Refused('BUDGET_COUNT_CONFLICT')
        e,u,t,l=map(lambda k:set(data[k]),keys)
        if e & u or e|u != set(rows) or not l<=t<=e: raise Refused('BUDGET_SET_CONFLICT')
        if e-t:raise Refused('PRIOR_UNCERTAIN_ENTRY_BLOCKS_NEW_CASE_NO_REPLAY')
        for receipt in self.receipts.glob('*__attempt_001.json'):
            prior=json.loads(receipt.read_text())
            if prior.get('case_id') not in t:raise Refused('DURABLE_RECEIPT_UNCERTAIN_BLOCKS_NEW_CASE_NO_REPLAY')
        if request.case_id not in rows or request.case_id not in u or self.receipt_path(request).exists():
            raise Refused('ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY')
        record=data.get('case_records',{}).get(request.case_id,{})
        if record.get('entry_consumed') or record.get('solver_entered') or (record and record.get('phase') != 'FAILED_PREENTRY_NO_ENTRY'): raise Refused('PRIOR_ENTRY_RECORD_NO_REPLAY')
        return data

    def prepare_entry(self,request,token,fault=lambda step:None):
        validate_registered(self.config,request)
        time_gate(self.config,request)
        # Reuse the receipt-first conservative cross-ledger write protocol.
        return super().prepare_entry(request,token,fault)

    def finish_truth(self,request,evidence):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data=json.loads(self.path.read_text());rec=data['case_records'][request.case_id]
            if rec.get('request_sha256') != request.request_sha256 or rec['phase'] != 'V2_ENTRY_UNCERTAIN':
                raise Refused('TERMINAL_BINDING_CONFLICT')
            label=evidence['validation']['labels_artifact']
            if sha256(label['path']) != label['sha256']: raise Refused('LABEL_ARTIFACT_CHANGED')
            # Only development labels are published to an ordinary-consumer-readable view.
            published=None
            if ROLES[request.role]=='DEVELOPMENT':
                target=Path(self.config.v3_data_root)/'V3_DEVELOPMENT/published'/request.case_id/'labels.npz'
                target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists():
                    with np.load(target,allow_pickle=False) as old,np.load(label['path'],allow_pickle=False) as new:
                        if set(old.files)!=set(new.files) or any(not np.array_equal(old[k],new[k]) for k in old.files):
                            raise Refused('PUBLICATION_CONFLICT')
                else:
                    stage=target.with_name('labels.partial.'+uuid.uuid4().hex)
                    with stage.open('xb') as f:
                        f.write(Path(label['path']).read_bytes());f.flush();os.fsync(f.fileno())
                    if sha256(stage)!=label['sha256']:raise Refused('PUBLICATION_COPY_CHANGED')
                    os.link(stage,target)
                receipt_path=target.parent/'PUBLICATION_RECEIPT.json'
                provenance=evidence['validation'].get('registered_provenance')
                if provenance is None and self.config.mode=='PRODUCTION_GPU':
                    raise Refused('VERIFIED_IMPORTER_PROVENANCE_REQUIRED')
                body=dict(schema='V3_DEVELOPMENT_LABEL_PUBLICATION_V1',status='PASS',training_label_eligible=True,
                    case_id=request.case_id,attempt_id=request.attempt_id,role=request.role,
                    ordered_D_nm=list(request.ordered_D_nm),physical_contract_sha256=request.physical_contract_sha256,
                    registry_sha256=self.config.registry.sha256,label_sha256=sha256(target),
                    h2_validation=dict(status='PASS',authority='verified original Coupling CaseTruth importer'),
                    provenance=provenance if provenance is not None else {'fixture_only':True})
                if receipt_path.exists():
                    if json.loads(receipt_path.read_text())!=body:raise Refused('PUBLICATION_RECEIPT_CONFLICT')
                else:durable_json(receipt_path,body)
                published=dict(case_id=request.case_id,attempt_id=request.attempt_id,role=request.role,
                    ordered_D_nm=list(request.ordered_D_nm),physical_contract_sha256=request.physical_contract_sha256,
                    label=dict(path=str(target),sha256=sha256(target)),
                    receipt=dict(path=str(receipt_path),sha256=sha256(receipt_path)))
            for key,count in [('truth_valid_case_ids','truth_valid_count'),('labels_valid_case_ids','labels_valid_count')]:
                if request.case_id not in data[key]:data[key].append(request.case_id);data[count]+=1
            receipt=self.reconcile(request)['receipt']
            rec.update(phase='V2_TRUTH_VALID',truth_valid=True,labels_valid=True,role=request.role,
                       physical_contract_sha256=request.physical_contract_sha256,evidence=evidence,
                       end_to_end_seconds=time.time()-receipt['entered_at'],published_development=published)
            replace_json(self.path,data)


def import_truth(config,request,record,importer):
    registry=importer.load_registry(config.registry.path,config.registry.sha256,root=Path(config.coupling_root),identity_authority=config.identity_authority.model_dump())
    imported=importer.load_verified_runner_case(record,expected_role=request.role,
        root=Path(config.coupling_root),registry=registry,access_role='PRODUCTION_CUSTODIAN')
    c=np.asarray(imported.c_hat);p=np.asarray(imported.p_scale)
    if c.shape!=(21,7,2) or not np.iscomplexobj(c) or p.shape!=(21,) or not np.isfinite(c).all() or not np.isfinite(p).all() or (p<=0).any():
        raise Refused('REGISTERED_LABEL_DIMENSION_OR_FINITE_CONFLICT')
    return imported,dict(outputs=609,provenance=imported.provenance)



def public_control_metadata(kind,body):
    """Reject extensible payloads: only explicit typed metadata may leave custody."""
    import math,re
    if not isinstance(body,dict):raise Refused('PUBLIC_METADATA_TYPE_REJECTED')
    if kind=='controller':
        if set(body)-{'enabled','state','demand_start','last_task_result'}:raise Refused('PUBLIC_METADATA_FIELDS_REJECTED')
        for key,value in body.items():
            good=(type(value) is bool) if key in ['enabled','demand_start'] else (type(value) is int and 0<=value<2**32 and (key!='state' or value<=4))
            if not good:raise Refused('PUBLIC_METADATA_VALUE_REJECTED')
    elif kind=='production_state':
        hashes={'code_inventory_sha256','registry_sha256','config_sha256','release_sha256'}
        allowed=hashes|{'status','dataset_id','phase','expires_unix','release_expires_unix','science_authorized'}
        if set(body)-allowed:raise Refused('PUBLIC_METADATA_FIELDS_REJECTED')
        for key,value in body.items():
            if key in hashes:good=isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value) is not None
            elif key=='status':good=value in ['CONTROLLER_STARTED','RUNNING','PARTIAL','HOLD','WINDOW_STOP','COMPLETE','DISABLED_NOT_STARTED'] if isinstance(value,str) else False
            elif key=='dataset_id':good=value==DATASET if isinstance(value,str) else False
            elif key=='phase':good=value in ['DIAGNOSTIC','DEVELOPMENT','SEALED_EVALUATION'] if isinstance(value,str) else False
            elif key=='science_authorized':good=type(value) is bool
            else:good=type(value) in [int,float] and math.isfinite(value) and value>=0
            if not good:raise Refused('PUBLIC_METADATA_VALUE_REJECTED')
    else:raise Refused('UNKNOWN_PUBLIC_METADATA_KIND')
    return dict(body)


def public_or_rejected(kind,body):
    try:return public_control_metadata(kind,body)
    except Refused:return dict(status='METADATA_REJECTED',failure_code='PUBLIC_METADATA_ALLOWLIST_REJECTION')

def morning_report(config,ledger_snapshot,*,now=None):
    """Allowlist construction: never serialize records, raw payloads or response arrays."""
    data=json.loads(Path(config.coupling_ledger).read_text());rows=registry_cases(config);records=data.get('case_records',{})
    tasks={x['case_id']:x for x in ledger_snapshot['tasks']}
    result=dict(schema='V3_PUBLIC_MORNING_REPORT_V1',dataset_id=DATASET,
        generated_unix=time.time() if now is None else now,entered=data['entered_count'],
        truth_valid=data['truth_valid_count'],labels_valid=data['labels_valid_count'],
        unentered=data['remaining_unentered_count'],replay=0,
        remaining_case_ids=data['remaining_unentered_case_ids'],
        postentry_not_truth_valid=data['entered_count']-data['truth_valid_count'],
        slot_empty=ledger_snapshot['slot']['token'] is None,release_expires=config.release.read()['expires_unix'],cases=[])
    for cid,row in rows.items():
        rec=records.get(cid,{});evidence=rec.get('evidence',{});label=evidence.get('validation',{}).get('labels_artifact')
        result['cases'].append(dict(case_id=cid,role=row['role'],entered=cid in data['entered_case_ids'],
            truth_valid=cid in data['truth_valid_case_ids'],labels_valid=cid in data['labels_valid_case_ids'],
            state=tasks.get(cid,{}).get('state','UNENTERED'),
            elapsed_seconds=rec.get('end_to_end_seconds'),native_wall_seconds=evidence.get('execution',{}).get('native_wall_seconds'),label_sha256=label.get('sha256') if label else None,
            native_files={name:{key:desc[key] for key in ['sha256','bytes'] if key in desc} for name,desc in evidence.get('bundle',{}).get('files',{}).items()},
            published_development=rec.get('published_development') if ROLES[row['role']]=='DEVELOPMENT' else None))
    result['role_counts']={role:dict(total=sum(ROLES[x['role']]==role for x in rows.values()),
        valid=sum(ROLES[rows[cid]['role']]==role for cid in data['labels_valid_case_ids'])) for role in set(ROLES.values())}
    result['failed_or_uncertain']=data['entered_count']-data['truth_valid_count']
    result['development_new_valid_geometry_count']=result['role_counts']['DEVELOPMENT']['valid']
    result['development_pool_geometry_count']=156+result['development_new_valid_geometry_count']
    result['diagnostic_progress']={key:result['role_counts'][key] for key in ['DIAGNOSTIC_5NM','DIAGNOSTIC_4NM']}
    result['sealed_integrity_status']='VALIDATED_AT_INGEST' if result['role_counts']['SEALED_EVALUATION']['valid']==8 else 'PARTIAL_OR_UNENTERED'
    result['configured_release']=dict(sha256=config.release.sha256,science_authorized=config.release.read().get('science_authorized') is True,expires_unix=config.release.read()['expires_unix'])
    state=Path(config.v3_data_root)/'V3_AUDIT_METADATA/PRODUCTION_STATE.json'
    result['production_state']=public_or_rejected('production_state',json.loads(state.read_text()) if state.exists() else dict(status='DISABLED_NOT_STARTED'))
    result['controller']=public_or_rejected('controller',ledger_snapshot['controller']) if 'controller' in ledger_snapshot else dict(status='NOT_OBSERVED')
    return result


def close_proven_window_preentry(config,request,ledger,token):
    """Only current owner may close its own proven no-entry time-window stop."""
    V3Budget(config).validate(request)
    folder=storage_root(config,request)/'attempts'/request.request_sha256
    if folder.exists() and (sorted(x.name for x in folder.iterdir())!=['run.fsp'] or sha256(folder/'run.fsp')!=request.pre_fsp_sha256):
        raise Refused('WINDOW_PREENTRY_NATIVE_EVIDENCE_UNKNOWN')
    from .processes import identity
    with ledger.transaction() as db:
        ledger.fence(db,request.request_sha256,token)
        slot=db.execute('select * from slot where id=1').fetchone()
        if json.loads(slot['owner'])!=identity():raise Refused('WINDOW_PREENTRY_NOT_CURRENT_OWNER')
        row=db.execute('select * from tasks where request_sha=?',(request.request_sha256,)).fetchone()
        if row['entered'] or row['entry_at'] is not None or row['state']!='HOLD_NO_REPLAY':raise Refused('WINDOW_STOP_ENTRY_NOT_EXCLUDED')
        forbidden=['COUPLING_ENTRY_MIRRORED','LAUNCH_REQUESTED','LAUNCHER_PROCESS','ENGINE_PROCESS','PROCESS_RETURNED']
        kinds=[x[0] for x in db.execute('select kind from events where request_sha=?',(request.request_sha256,))]
        if any(k in forbidden for k in kinds):raise Refused('WINDOW_STOP_LAUNCH_NOT_EXCLUDED')
        ledger.event(db,request.request_sha256,'WINDOW_STOP_UNENTERED',dict(entry_consumed=False,solver_invocations=0,owner=dict(slot),old_task=dict(row),admission_sha256=request.admission_sha256,staging_sha256=request.pre_fsp_sha256 if folder.exists() else None))
        db.execute("update tasks set state='WINDOW_STOP_UNENTERED' where request_sha=?",(request.request_sha256,))
        db.execute('update slot set token=NULL,owner=NULL,request_sha=NULL where id=1')


def rebind_proven_window(config,request,ledger):
    """Preserve no-entry lineage under a new finite release; no attempt increment."""
    validate_registered(config,request)
    with ledger.transaction() as db:
        row=db.execute('select * from tasks where case_id=? and attempt_id=?',(request.case_id,request.attempt_id)).fetchone()
        if not row or row['state']!='WINDOW_STOP_UNENTERED':return False
        V3Budget(config).validate(request)
        old=V3Request.model_validate_json(row['payload'])
        if row['entered'] or row['entry_at'] is not None or old.admission_sha256!=request.admission_sha256:
            raise Refused('WINDOW_REBIND_ENTRY_OR_IDENTITY_CONFLICT')
        slot=db.execute('select * from slot where id=1').fetchone()
        if slot['token']:raise Refused('WINDOW_REBIND_ACTIVE_OWNER_PRESENT')
        events=[dict(x) for x in db.execute('select * from events where request_sha=? and kind=?',(row['request_sha'],'WINDOW_STOP_UNENTERED'))]
        if len(events)!=1:raise Refused('WINDOW_REBIND_PROOF_REQUIRED')
        proof=dict(old_task=dict(row),window_stop_event=events[0],new_request_sha256=request.request_sha256,entry_consumed=False,solver_invocations=0,automatic_replays=0)
        ledger.event(db,row['request_sha'],'WINDOW_PREENTRY_REBOUND',proof)
        ledger.event(db,request.request_sha256,'PREENTRY_REBOUND_READY',proof)
        db.execute("update tasks set request_sha=?,config_sha=?,payload=?,state='REGISTERED',error=NULL,bundle=NULL where case_id=? and attempt_id=?",(request.request_sha256,config.sha256,request.model_dump_json(),request.case_id,request.attempt_id))
        return True
