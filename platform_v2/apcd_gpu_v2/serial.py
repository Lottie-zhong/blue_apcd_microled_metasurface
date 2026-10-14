"""Single server-owned V2 worker. Coupling owns budget; uncertainty never replays."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import psutil
from pydantic import Field, model_validator

from .artifacts import archive_pair, bundle_inventory, durable_json, load_only, sha256
from .config import StrictModel, CONTRACT_SHA, digest
from .ledger import Ledger, Refused
from .native import launch_spec
from .processes import identity, identity_state


class Pin(StrictModel):
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    def read(self):
        if sha256(self.path) != self.sha256:
            raise Refused('PIN_CHANGED:' + self.path)
        return json.loads(Path(self.path).read_text(encoding='utf-8'))


def registered_config(config):
    if config.schema_version != 'APCD_V2_REGISTERED_V3_SERIAL_V1':return False
    from .v3 import V3Config
    if not isinstance(config,V3Config):raise Refused('EXPLICIT_REGISTERED_CONFIG_REQUIRED')
    return True


def diag2_config(config):
    from .diag2 import is_diag2_config
    return is_diag2_config(config)


def budget_for(config):
    from .general import is_general, GeneralBudget
    if is_general(config): return GeneralBudget(config)
    if diag2_config(config):
        return Diag2Budget(config)
    if registered_config(config):
        from .v3 import V3Budget
        return V3Budget(config)
    return CouplingBudget(config)


def case_storage(config,request):
    from .general import is_general
    if is_general(config): return Path(config.runtime_root)/'batches'/config.batch_id
    if diag2_config(config):
        from .diag2 import case_storage as diag2_case_storage
        return diag2_case_storage(config,request)
    if registered_config(config):
        from .v3 import storage_root
        return storage_root(config,request)
    return Path(config.runtime_root)


def window_admission(config,request):
    if diag2_config(config):
        return None
    if registered_config(config):
        from .v3 import time_gate
        return time_gate(config,request)
    return None


class SerialConfig(StrictModel):
    schema_version: Literal['APCD_V2_SERIAL_V1']
    mode: Literal['PRODUCTION_GPU', 'PRODUCTION_EQUIVALENT']
    runtime_root: str
    coupling_ledger: str
    queue: Pin
    release: Pin
    fdtd_executable: str
    executable_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    gpu_resource: Literal['GPU license audit']
    lumerical_version: Literal['2025 R1'] = '2025 R1'
    gpu_device: Literal['NVIDIA GeForce RTX 3080'] = 'NVIDIA GeForce RTX 3080'
    native_h5_name: Literal['run_output.h5']
    physical_contract_sha256: Literal[CONTRACT_SHA]
    slots: Literal[1] = 1
    automatic_replays: Literal[0] = 0
    heartbeat_seconds: float = Field(gt=0, le=30)
    truth_toolchain: dict[str, Pin] = Field(default_factory=dict)
    coupling_root: str = ''

    @model_validator(mode='after')
    def paths(self):
        for s in [self.runtime_root, self.coupling_ledger, self.fdtd_executable, self.queue.path, self.release.path]:
            if not Path(s).is_absolute():
                raise ValueError('absolute paths required')
        if self.mode == 'PRODUCTION_EQUIVALENT':
            root = Path(self.runtime_root).resolve()
            if 'zero_solver' not in str(root).lower():
                raise ValueError('explicit zero_solver fixture root required')
            for p in [self.coupling_ledger, self.queue.path, self.release.path]:
                if root not in Path(p).resolve().parents:
                    raise ValueError('fixture may not write/read production authority')
        elif not {'lumapi','postprocessor','decoder','importer'} <= set(self.truth_toolchain) or not Path(self.coupling_root).is_absolute():
            raise ValueError('pinned native truth toolchain required')
        if self.mode=='PRODUCTION_GPU':
            canonical=Path('D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1/reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json').resolve()
            if Path(self.coupling_ledger).resolve()!=canonical or Path(self.runtime_root).resolve()!=Path('D:/apcd_runtime/gpu_platform_v2_serial_production_v1').resolve():
                raise ValueError('single canonical production authority and runtime required')
        return self

    @property
    def sha256(self):
        return digest(self.model_dump())


class SerialRequest(StrictModel):
    case_id: str = Field(pattern=r'^K6(GDP2|LDA1)_DEV_[A-Za-z0-9_]+$')
    attempt_id: Literal['attempt_001']
    role: Literal['DEVELOPMENT_GLOBAL', 'DEVELOPMENT_LOCAL_AXIS']
    ordered_D_nm: tuple[int, int, int, int, int, int]
    pre_fsp: str
    pre_fsp_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_manifest: Pin
    physical_contract: Pin
    physical_contract_sha256: Literal[CONTRACT_SHA]
    config_sha256: str

    @property
    def request_sha256(self):
        return digest(self.model_dump())

    @property
    def admission_sha256(self):
        # Excludes config release SHA to avoid a circular request/release hash dependency.
        return digest(self.model_dump(exclude={'config_sha256'}))


@contextmanager
def exclusive(path):
    """OS byte lock survives stale file names; never delete an owner marker."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = path.open('a+b')
    f.seek(0,os.SEEK_END)
    if f.tell() == 0:
        f.write(b'0'); f.flush()
    f.seek(0)
    locked = False
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        f.close()
        raise Refused('OS_OWNER_LOCK_OR_IO_FAILURE') from exc
    locked = True
    try:
        yield
    finally:
        if locked:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def replace_json(path, data):
    path = Path(path)
    stage = path.with_name(path.name + '.partial.' + uuid.uuid4().hex)
    durable_json(stage, data)
    os.replace(stage, path)


class CouplingBudget:
    """Writes the existing Coupling ledger, never creates a budget authority.

    Its adjacent immutable entry receipt is the Coupling-side write-ahead evidence.
    A receipt left before ledger replacement conservatively blocks, never refunds.
    """
    def __init__(self, config):
        self.config = config
        self.path = Path(config.coupling_ledger)
        self.receipts = self.path.parent / 'V2_ENTRY_EVIDENCE_V1'

    def receipt_path(self, request):
        return self.receipts / (request.case_id + '__' + request.attempt_id + '.json')

    def validate(self, request):
        data = json.loads(self.path.read_text(encoding='utf-8'))
        entered = data['entered_case_ids']; remaining = data['remaining_unentered_case_ids']
        valid = data['truth_valid_case_ids']; labels = data['labels_valid_case_ids']
        if len(set(entered)) != len(entered) or set(entered) & set(remaining):
            raise Refused('COUPLING_LEDGER_SET_CONFLICT')
        for items, count in [(entered,'entered_count'),(remaining,'remaining_unentered_count'),(valid,'truth_valid_count'),(labels,'labels_valid_count')]:
            if len(set(items)) != data[count]:
                raise Refused('COUPLING_COUNT_CONFLICT')
        if not set(labels) <= set(valid) <= set(entered):
            raise Refused('COUPLING_TRUTH_ENTRY_CONFLICT')
        if len(entered) + len(remaining) != data['authorized_development_case_count']:
            raise Refused('COUPLING_AUTHORIZED_TOTAL_CONFLICT')
        if request.case_id not in remaining or request.case_id in entered or self.receipt_path(request).exists():
            raise Refused('COUPLING_ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY')
        old = data.get('case_records',{}).get(request.case_id,{})
        if old.get('entry_consumed') or old.get('solver_entered'):
            raise Refused('COUPLING_PRIOR_ENTRY_PRESENT')
        if old and old.get('phase') != 'FAILED_PREENTRY_NO_ENTRY':
            raise Refused('COUPLING_NONTERMINAL_RECORD')
        return data

    def prepare_entry(self, request, token, fault=lambda step: None):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data = self.validate(request)
            self.receipts.mkdir(exist_ok=True)
            record = dict(schema='APCD_V2_COUPLING_CONSERVATIVE_ENTRY_V1',case_id=request.case_id,
                          attempt_id=request.attempt_id,request_sha=request.request_sha256,
                          owner_token=token,pre_fsp_sha256=request.pre_fsp_sha256,
                          physical_contract_sha256=request.physical_contract_sha256,entered_at=time.time(),
                          ledger_before_sha256=sha256(self.path),mode=self.config.mode,
                          config_sha256=self.config.sha256,release_sha256=self.config.release.sha256,
                          solver_entered=True,physical_process_confirmed=False,automatic_replay=0)
            durable_json(self.receipt_path(request), record)
            fault('coupling_receipt_committed')
            data['entered_case_ids'].append(request.case_id)
            data['remaining_unentered_case_ids'].remove(request.case_id)
            data['entered_count'] += 1; data['remaining_unentered_count'] -= 1
            previous = data.setdefault('case_records',{}).get(request.case_id)
            data['case_records'][request.case_id] = dict(attempt_id=request.attempt_id,
                phase='V2_ENTRY_UNCERTAIN',entry_consumed=True,solver_entered=True,
                v2_entry_receipt=str(self.receipt_path(request)),v2_entry_receipt_sha256=sha256(self.receipt_path(request)),
                previous_preentry_record=previous,request_sha256=request.request_sha256)
            replace_json(self.path, data)
            fault('coupling_ledger_committed')
            return record

    def reconcile(self, request):
        """Return evidence for review; never dispatch, decrement or delete."""
        p = self.receipt_path(request)
        data = json.loads(self.path.read_text(encoding='utf-8'))
        return dict(replay_allowed=False,entered_in_ledger=request.case_id in data['entered_case_ids'],
                    receipt=json.loads(p.read_text(encoding='utf-8')) if p.exists() else None)

    def mark_launch_request(self,request,token):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            proof=self.reconcile(request)
            if not proof['entered_in_ledger'] or not proof['receipt'] or proof['receipt']['owner_token']!=token or proof['receipt']['request_sha']!=request.request_sha256:
                raise Refused('COUPLING_LAUNCH_BINDING_NOT_PROVEN')
            target=self.receipt_path(request).with_suffix('.launch_requested.json')
            if target.exists():raise Refused('COUPLING_LAUNCH_ALREADY_REQUESTED_NO_REPLAY')
            durable_json(target,dict(schema='APCD_V2_NONREPEATABLE_LAUNCH_V1',request_sha=request.request_sha256,
                owner_token=token,entry_receipt_sha256=sha256(self.receipt_path(request)),requested_at=time.time(),
                mode=self.config.mode,automatic_replay=0))

    def reconcile_entry_evidence(self,request):
        """Conservative Coupling count repair only, never a solver permission or refund."""
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            proof=self.reconcile(request);receipt=proof['receipt']
            if not receipt or receipt['request_sha']!=request.request_sha256 or receipt['config_sha256']!=self.config.sha256:
                raise Refused('ENTRY_RECONCILIATION_BINDING_UNKNOWN')
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if proof['entered_in_ledger']:
                if data['case_records'].get(request.case_id,{}).get('request_sha256')!=request.request_sha256:
                    raise Refused('ENTRY_RECONCILIATION_RECORD_CONFLICT')
                return dict(entered=True,replay_allowed=False,repaired=False)
            if sha256(self.path)!=receipt['ledger_before_sha256'] or request.case_id not in data['remaining_unentered_case_ids']:
                raise Refused('ENTRY_RECONCILIATION_CONCURRENT_CHANGE')
            data['entered_case_ids'].append(request.case_id);data['entered_count']+=1
            data['remaining_unentered_case_ids'].remove(request.case_id);data['remaining_unentered_count']-=1
            previous=data.setdefault('case_records',{}).get(request.case_id)
            data['case_records'][request.case_id]=dict(attempt_id=request.attempt_id,
                phase='V2_ENTRY_UNCERTAIN',entry_consumed=True,solver_entered=True,
                v2_entry_receipt=str(self.receipt_path(request)),v2_entry_receipt_sha256=sha256(self.receipt_path(request)),
                previous_preentry_record=previous,request_sha256=request.request_sha256)
            replace_json(self.path,data)
            return dict(entered=True,replay_allowed=False,repaired=True)

    def finish_truth(self, request, evidence):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data = json.loads(self.path.read_text(encoding='utf-8'))
            rec = data['case_records'][request.case_id]
            if rec.get('request_sha256') != request.request_sha256 or rec.get('phase') != 'V2_ENTRY_UNCERTAIN':
                raise Refused('COUPLING_TERMINAL_BINDING_CONFLICT')
            if self.config.mode=='PRODUCTION_GPU':
                validation=evidence['validation']; label=validation['labels_artifact']
                if sha256(label['path'])!=label['sha256']:raise Refused('LABEL_ARTIFACT_SHA_MISMATCH')
                target=self.path.parent/('INGESTED_TRUTH_'+request.case_id+'_V1.npz')
                if target.exists():
                    import numpy as np
                    with np.load(target,allow_pickle=False) as old,np.load(label['path'],allow_pickle=False) as fresh:
                        if set(old.files)!=set(fresh.files) or any(not np.array_equal(old[k],fresh[k]) for k in old.files):
                            raise Refused('COUPLING_LABEL_PUBLICATION_CONFLICT')
                else:
                    stage=target.with_name(target.name+'.partial.'+uuid.uuid4().hex)
                    with stage.open('xb') as stream:
                        stream.write(Path(label['path']).read_bytes());stream.flush();os.fsync(stream.fileno())
                    if sha256(stage)!=label['sha256']:raise Refused('LABEL_COPY_SHA_MISMATCH')
                    os.link(stage,target)  # atomic exclusive publish; never replace existing truth
                result=self.path.parent/('INGEST_RESULT_'+request.case_id+'_V1.json')
                body=dict(schema='COUPLING_K6_V2_DEVELOPMENT_CASE_INGEST_RESULT_V1',status='PASS',decision='INGESTED_FOR_DEVELOPMENT_ONLY; NOT_MODEL_ADMISSION',case_id=request.case_id,attempt_id=request.attempt_id,role=request.role,ordered_D_nm=list(request.ordered_D_nm),solver_entered=True,solver_invocations=1,replay_count=0,input_artifacts=validation['record'],truth_artifact=dict(path=str(target),sha256=sha256(target),shapes={'C_hat':[21,7,2],'P_scale':[21],'eta':[21,7],'absolute_order':[21,7]}),access_counts={'solver_entries_this_case':1,'automatic_replay':0,'training_fit_count':0,'p_scale_fit_count':0,'confirmation_response_opened':False,'diagnostic_data_accessed':False})
                if result.exists():
                    old=json.loads(result.read_text(encoding='utf-8'))
                    if old.get('status')!='PASS' or old.get('truth_artifact')!=body['truth_artifact']:
                        raise Refused('COUPLING_INGEST_RECEIPT_CONFLICT')
                else:
                    stage=result.with_name(result.name+'.partial.'+uuid.uuid4().hex)
                    durable_json(stage,body);os.link(stage,result)
            for key,count in [('truth_valid_case_ids','truth_valid_count'),('labels_valid_case_ids','labels_valid_count')]:
                if request.case_id not in data[key]: data[key].append(request.case_id);data[count]+=1
            rec.update(phase='V2_TRUTH_VALID',truth_valid=True,labels_valid=True,evidence=evidence)
            replace_json(self.path,data)


class Diag2Budget(CouplingBudget):
    """Finite Coupling-owned DIAG2 ledger; isolated from DOE56 and the historical 128-case ledger."""
    schema = 'APCD_COUPLING_DIAG2_ENTRY_LEDGER_V1'

    def __init__(self, config):
        super().__init__(config)
        self.receipts = self.path.parent / 'V2_DIAG2_ENTRY_EVIDENCE_V1'

    def receipt_path(self, request):
        return self.receipts / (request.case_id + '__' + request.attempt_id + '.json')

    def validate(self, request):
        from .diag2 import DATASET_ID, BATCH_ID, DIAG2_CASES
        resolved = self.path.resolve()
        forbidden = ('DOE56', 'REMAINING127', 'V3_EXECUTION_LEDGER', 'QUEUE_EXECUTION_LEDGER')
        if any(mark in str(resolved).upper() for mark in forbidden):
            raise Refused('DIAG2_FORBIDDEN_COUPLING_LEDGER_PATH')
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('schema') != self.schema or data.get('status') not in {'OPEN', 'SCIENTIFIC_ADMISSION_PASS'}:
            raise Refused('DIAG2_COUPLING_LEDGER_SCHEMA_OR_STATUS')
        if data.get('dataset_id') != DATASET_ID or data.get('batch_id') != BATCH_ID:
            raise Refused('DIAG2_COUPLING_LEDGER_IDENTITY_MISMATCH')
        if data.get('case_ids') != list(DIAG2_CASES):
            raise Refused('DIAG2_COUPLING_LEDGER_CASE_SET_MISMATCH')
        if (data.get('max_new_entries') != 2 or data.get('per_case_entry_limit') != 1
                or data.get('automatic_replays') != 0):
            raise Refused('DIAG2_COUPLING_LEDGER_BUDGET_MISMATCH')
        if (data.get('registry_sha256') != self.config.registry.sha256
                or data.get('scientific_admission_sha256') != self.config.scientific_admission.sha256
                or data.get('physical_contract_sha256') != self.config.physical_contract_sha256):
            raise Refused('DIAG2_COUPLING_LEDGER_AUTHORITY_PIN_MISMATCH')
        entered = data.get('entered_case_ids'); remaining = data.get('remaining_case_ids')
        truth = data.get('truth_valid_case_ids'); labels = data.get('labels_valid_case_ids')
        if not all(isinstance(x, list) for x in (entered, remaining, truth, labels)):
            raise Refused('DIAG2_COUPLING_LEDGER_LIST_SCHEMA')
        if len(set(entered)) != len(entered) or len(set(remaining)) != len(remaining):
            raise Refused('DIAG2_COUPLING_LEDGER_DUPLICATE_IDS')
        if set(entered) & set(remaining) or set(entered) | set(remaining) != set(DIAG2_CASES):
            raise Refused('DIAG2_COUPLING_LEDGER_PARTITION_CONFLICT')
        if len(set(truth)) != len(truth) or len(set(labels)) != len(labels):
            raise Refused('DIAG2_COUPLING_LEDGER_DUPLICATE_TERMINALS')
        if not set(labels) <= set(truth) <= set(entered):
            raise Refused('DIAG2_COUPLING_LEDGER_TRUTH_LABEL_CONFLICT')
        for key, expected in [('entry_count', len(entered)), ('remaining_count', len(remaining)),
                              ('truth_valid_count', len(truth)), ('labels_valid_count', len(labels))]:
            if data.get(key) != expected:
                raise Refused('DIAG2_COUPLING_LEDGER_COUNT_CONFLICT:' + key)
        if data.get('entry_count', 0) > 2:
            raise Refused('DIAG2_TOTAL_BUDGET_EXHAUSTED')
        records = data.get('case_records')
        if not isinstance(records, dict) or set(records) != set(DIAG2_CASES):
            raise Refused('DIAG2_CASE_RECORD_SET_CONFLICT')
        for cid in DIAG2_CASES:
            row = records[cid]
            if (row.get('attempt_id') != 'attempt_001' or row.get('max_entry_count') != 1
                    or row.get('entry_count') not in (0, 1) or row.get('replay_count') != 0):
                raise Refused('DIAG2_CASE_RECORD_BUDGET_CONFLICT:' + cid)
            if (row.get('entry_count') == 1) != (cid in entered):
                raise Refused('DIAG2_CASE_RECORD_ENTRY_CONFLICT:' + cid)
        row = records.get(request.case_id)
        if request.case_id not in remaining or request.case_id in entered or self.receipt_path(request).exists():
            raise Refused('DIAG2_ENTRY_CONSUMED_OR_UNCERTAIN_NO_REPLAY')
        if row.get('phase') not in {'UNENTERED', 'FAILED_PREENTRY_NO_ENTRY'} or row.get('entry_count') != 0:
            raise Refused('DIAG2_CASE_NOT_PREENTRY')
        if row.get('request_sha256') not in (None, request.request_sha256):
            raise Refused('DIAG2_CASE_REQUEST_SHA_CONFLICT')
        return data

    def prepare_entry(self, request, token, fault=lambda step: None):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data = self.validate(request)
            self.receipts.mkdir(parents=True, exist_ok=True)
            target = self.receipt_path(request)
            if target.exists():
                raise Refused('DIAG2_ENTRY_RECEIPT_ALREADY_EXISTS_NO_REPLAY')
            receipt = dict(schema='APCD_V2_DIAG2_CONSERVATIVE_ENTRY_V1',
                dataset_id=request.dataset_id, batch_id=request.batch_id,
                case_id=request.case_id, attempt_id=request.attempt_id,
                request_sha=request.request_sha256, admission_sha=request.admission_sha256,
                owner_token=token, pre_fsp_sha256=request.pre_fsp_sha256,
                source_setup_fsp_sha256=request.source_setup_fsp_sha256,
                source_run_fsp_sha256=request.source_run_fsp_sha256,
                physical_contract_sha256=request.physical_contract_sha256,
                ledger_before_sha256=sha256(self.path), entered_at=time.time(),
                config_sha256=self.config.sha256, release_sha256=self.config.release.sha256,
                scientific_admission_sha256=self.config.scientific_admission.sha256,
                solver_entered=True, physical_process_confirmed=False, replay_count=0)
            durable_json(target, receipt)
            fault('coupling_receipt_committed')
            data['entered_case_ids'].append(request.case_id)
            data['remaining_case_ids'].remove(request.case_id)
            data['entry_count'] += 1
            data['remaining_count'] -= 1
            row = data['case_records'][request.case_id]
            row.update(phase='V2_ENTRY_UNCERTAIN', entry_count=1, replay_count=0,
                       solver_entered=True, request_sha256=request.request_sha256,
                       entry_receipt=str(target), entry_receipt_sha256=sha256(target))
            replace_json(self.path, data)
            fault('coupling_ledger_committed')
            return receipt

    def reconcile_entry_evidence(self, request):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            receipt_path = self.receipt_path(request)
            if not receipt_path.exists():
                raise Refused('DIAG2_ENTRY_RECONCILIATION_RECEIPT_MISSING')
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt.get('request_sha') != request.request_sha256 or receipt.get('config_sha256') != self.config.sha256:
                raise Refused('DIAG2_ENTRY_RECONCILIATION_BINDING_UNKNOWN')
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if request.case_id in data['entered_case_ids']:
                rec = data['case_records'][request.case_id]
                if rec.get('request_sha256') != request.request_sha256 or rec.get('phase') != 'V2_ENTRY_UNCERTAIN':
                    raise Refused('DIAG2_ENTRY_RECONCILIATION_RECORD_CONFLICT')
                return dict(entered=True, replay_allowed=False, repaired=False)
            if (sha256(self.path) != receipt.get('ledger_before_sha256')
                    or request.case_id not in data['remaining_case_ids']):
                raise Refused('DIAG2_ENTRY_RECONCILIATION_CONCURRENT_CHANGE')
            data['entered_case_ids'].append(request.case_id)
            data['remaining_case_ids'].remove(request.case_id)
            data['entry_count'] += 1
            data['remaining_count'] -= 1
            data['case_records'][request.case_id].update(phase='V2_ENTRY_UNCERTAIN',
                entry_count=1, replay_count=0, solver_entered=True,
                request_sha256=request.request_sha256, entry_receipt=str(receipt_path),
                entry_receipt_sha256=sha256(receipt_path))
            replace_json(self.path, data)
            return dict(entered=True, replay_allowed=False, repaired=True)

    @staticmethod
    def _arrays_equal(left, right):
        import numpy as np
        try:
            with np.load(left, allow_pickle=False) as a, np.load(right, allow_pickle=False) as b:
                return set(a.files) == set(b.files) and all(np.array_equal(a[k], b[k]) for k in a.files)
        except Exception:
            return False

    def finish_truth(self, request, evidence):
        with exclusive(self.path.with_suffix('.v2_writer.lock')):
            data = json.loads(self.path.read_text(encoding='utf-8'))
            row = data['case_records'].get(request.case_id, {})
            if (request.case_id not in data['entered_case_ids']
                    or row.get('phase') not in {'V2_ENTRY_UNCERTAIN', 'V2_TRUTH_VALID'}
                    or row.get('request_sha256') != request.request_sha256):
                raise Refused('DIAG2_TERMINAL_BINDING_CONFLICT')
            validation = evidence.get('validation', {})
            if (validation.get('verdict') != 'PASS' or validation.get('outputs') != 609
                    or validation.get('fresh_load_verified') is not True
                    or validation.get('actual_importer') != self.config.importer_entrypoint):
                raise Refused('DIAG2_LOAD_IMPORTER_TERMINAL_REQUIRED')
            if row.get('phase') == 'V2_TRUTH_VALID':
                previous = row.get('evidence', {})
                if previous.get('bundle') != evidence.get('bundle') or previous.get('validation', {}).get('outputs') != 609:
                    raise Refused('DIAG2_IDEMPOTENT_TERMINAL_CONFLICT')
                previous_labels = previous.get('validation', {}).get('labels_artifact', {})
                fresh_labels = validation.get('labels_artifact', {})
                if not self._arrays_equal(previous_labels.get('path', ''), fresh_labels.get('path', '')):
                    raise Refused('DIAG2_IDEMPOTENT_LABEL_DATA_CONFLICT')
                terminal_path = Path(row.get('terminal_receipt', ''))
                if not terminal_path.is_file() or sha256(terminal_path) != row.get('terminal_receipt_sha256'):
                    raise Refused('DIAG2_IDEMPOTENT_TERMINAL_RECEIPT_MISSING_OR_CHANGED')
                return
            descriptor = validation.get('labels_artifact')
            if not isinstance(descriptor, dict) or sha256(descriptor.get('path', '')) != descriptor.get('sha256'):
                raise Refused('DIAG2_LABEL_SHA_INVALID')
            labels_dir = self.path.parent / 'DIAG2_LABELS'
            labels_dir.mkdir(parents=True, exist_ok=True)
            label_target = labels_dir / (request.case_id + '__attempt_001.npz')
            if label_target.exists():
                if not self._arrays_equal(label_target, descriptor['path']):
                    raise Refused('DIAG2_LABEL_PUBLICATION_CONFLICT')
            else:
                stage = label_target.with_name(label_target.name + '.partial.' + uuid.uuid4().hex)
                try:
                    with stage.open('xb') as out:
                        out.write(Path(descriptor['path']).read_bytes())
                        out.flush(); os.fsync(out.fileno())
                    if sha256(stage) != descriptor['sha256']:
                        raise Refused('DIAG2_LABEL_COPY_SHA_MISMATCH')
                    os.link(stage, label_target)
                finally:
                    if stage.exists(): stage.unlink()
            stable_validation = {
                'verdict': validation['verdict'], 'outputs': validation['outputs'],
                'fresh_load_verified': True, 'actual_importer': validation['actual_importer'],
                'labels_artifact_sha256': sha256(label_target),
                'time_convergence': validation.get('time_convergence'),
                'time_convergence_artifact_sha256': validation.get('time_convergence_artifact', {}).get('sha256'),
            }
            terminal = dict(schema='APCD_COUPLING_DIAG2_TERMINAL_RECEIPT_V1',
                dataset_id=request.dataset_id, batch_id=request.batch_id,
                case_id=request.case_id, attempt_id=request.attempt_id,
                request_sha256=request.request_sha256, status='TRUTH_VALID_AND_LABELS_VALID',
                replay_count=0, truth_bundle=evidence.get('bundle'),
                validation=stable_validation,
                published_labels=dict(path=str(label_target), sha256=sha256(label_target)))
            terminal_path = self.path.parent / ('DIAG2_TERMINAL_' + request.case_id + '__attempt_001.json')
            if terminal_path.exists():
                if json.loads(terminal_path.read_text(encoding='utf-8')) != terminal:
                    raise Refused('DIAG2_TERMINAL_RECEIPT_CONFLICT')
            else:
                durable_json(terminal_path, terminal)
            if request.case_id not in data['truth_valid_case_ids']:
                data['truth_valid_case_ids'].append(request.case_id); data['truth_valid_count'] += 1
            if request.case_id not in data['labels_valid_case_ids']:
                data['labels_valid_case_ids'].append(request.case_id); data['labels_valid_count'] += 1
            row.update(phase='V2_TRUTH_VALID', truth_valid=True, labels_valid=True,
                       terminal_receipt=str(terminal_path), terminal_receipt_sha256=sha256(terminal_path),
                       evidence=evidence)
            replace_json(self.path, data)


class SerialLedger(Ledger):
    def register(self,request,config):
        if request.config_sha256!=config.sha256:raise Refused('CONFIG_REQUEST_MISMATCH')
        with self.transaction() as db:
            # A reviewed config/release revision may govern NEW cases after all previous truth is valid.
            conflicts=db.execute("SELECT 1 FROM tasks WHERE config_sha<>? AND state<>'TRUTH_VALID' LIMIT 1",(config.sha256,)).fetchone()
            if conflicts:raise Refused('UNRESOLVED_OLD_CONFIG_TASK')
            try:
                db.execute('INSERT INTO tasks(case_id,attempt_id,request_sha,config_sha,payload,state) VALUES(?,?,?,?,?,?)',
                    (request.case_id,request.attempt_id,request.request_sha256,config.sha256,request.model_dump_json(),'REGISTERED'))
            except sqlite3.IntegrityError as exc:raise Refused('DUPLICATE_CASE_ATTEMPT_OR_REQUEST') from exc
            self.event(db,request.request_sha256,'REGISTERED',request.model_dump())

    def audit(self):
        result=super().audit()
        mirrors=[json.loads(e['payload']) for e in result['events'] if e['kind']=='COUPLING_ENTRY_MIRRORED']
        result['mode']='SERIAL_EXECUTION'
        result['conservative_scientific_entries']=sum(r.get('mode')=='PRODUCTION_GPU' for r in mirrors)
        result['observed_engine_processes']=[json.loads(e['payload']) for e in result['events'] if e['kind']=='ENGINE_PROCESS']
        result['scientific_solver_invocations']=None if result['conservative_scientific_entries'] else 0
        return result

    def note(self, request, token, kind, payload):
        with self.transaction() as db:
            self.fence(db,request.request_sha256,token)
            self.event(db,request.request_sha256,kind,payload)

    def mirror(self, request, token, receipt):
        with self.transaction() as db:
            self.fence(db,request.request_sha256,token)
            row=db.execute('SELECT * FROM tasks WHERE request_sha=?',(request.request_sha256,)).fetchone()
            if row['state']!='CLAIMED' or row['entered']: raise Refused('LOCAL_ENTRY_NOT_PREPARED')
            db.execute("UPDATE tasks SET entered=1,state='ENTRY_UNCERTAIN',entry_at=?,pre_sha=?,contract_sha=? WHERE request_sha=?",
                (receipt['entered_at'],request.pre_fsp_sha256,request.physical_contract_sha256,request.request_sha256))
            self.event(db,request.request_sha256,'COUPLING_ENTRY_MIRRORED',receipt)

    def launch_once(self, request, token, budget):
        record=budget.reconcile(request)
        if not record['entered_in_ledger'] or not record['receipt'] or record['receipt']['owner_token']!=token or record['receipt']['request_sha']!=request.request_sha256:
            raise Refused('COUPLING_DURABLE_ENTRY_NOT_BOUND')
        with self.transaction() as db:
            self.fence(db,request.request_sha256,token)
            cur=db.execute("UPDATE tasks SET state='LAUNCH_REQUESTED' WHERE request_sha=? AND state='ENTRY_UNCERTAIN' AND entered=1",(request.request_sha256,))
            if cur.rowcount!=1: raise Refused('LAUNCH_ALREADY_REQUESTED_NO_REPLAY')
            budget.mark_launch_request(request,token)
            self.event(db,request.request_sha256,'LAUNCH_REQUESTED',record)

    def terminal(self, request, token, *, evidence=None, error=None):
        with self.transaction() as db:
            self.fence(db,request.request_sha256,token)
            row=db.execute('SELECT * FROM tasks WHERE request_sha=?',(request.request_sha256,)).fetchone()
            if evidence and not row['entered']:raise Refused('TRUTH_WITHOUT_LOCAL_ENTRY_FORBIDDEN')
            state='TRUTH_VALID' if evidence else 'HOLD_NO_REPLAY'
            db.execute('UPDATE tasks SET state=?,error=?,bundle=? WHERE request_sha=?',(state,error,json.dumps(evidence),request.request_sha256))
            self.event(db,request.request_sha256,state,dict(evidence=evidence,error=error))
            if evidence: db.execute('UPDATE slot SET token=NULL,owner=NULL,request_sha=NULL WHERE id=1')


def require_trusted_production_config(config):
    if config.mode=='PRODUCTION_GPU':
        from .general import is_general
        if not is_general(config):raise Refused('TRUSTED_V21_ADMISSION_PATH_REQUIRED')


def validate_admission(config,request):
    require_trusted_production_config(config)
    from .general import is_general, validate_general
    if is_general(config): return validate_general(config,request)
    if diag2_config(config):
        from .diag2 import validate_diag2_admission
        return validate_diag2_admission(config,request)
    if registered_config(config):
        from .v3 import validate_registered
        return validate_registered(config,request)
    if request.config_sha256!=config.sha256: raise Refused('CONFIG_REQUEST_MISMATCH')
    queue=config.queue.read()
    exact=[r for r in queue['ordered_cases'] if r['case_id']==request.case_id]
    if len(exact)!=1 or any(exact[0][k]!=getattr(request,k) for k in ['attempt_id','role']) or exact[0]['ordered_D_nm']!=list(request.ordered_D_nm):
        raise Refused('FROZEN_CASE_MISMATCH')
    if any(v<100 or v>230 or v%5 for v in request.ordered_D_nm):raise Refused('FROZEN_GRID_INVALID')
    manifest=request.source_manifest.read();request.physical_contract.read()
    if request.physical_contract.sha256!=CONTRACT_SHA or sha256(request.pre_fsp)!=request.pre_fsp_sha256:
        raise Refused('FROZEN_SOURCE_HASH_MISMATCH')
    artifacts=manifest['artifacts']
    desc=artifacts['staged_fsp']
    if sha256(Path(request.source_manifest.path).parent/desc['path'])!=request.pre_fsp_sha256 or desc['sha256']!=request.pre_fsp_sha256:
        raise Refused('MANIFEST_FSP_BINDING_MISMATCH')
    release=config.release.read()
    if release.get('schema')!='APCD_V2_SERIAL_RELEASE_V1' or release.get('mode')!=config.mode or release.get('queue_sha256')!=config.queue.sha256 or release.get('expires_unix',0)<time.time() or request.admission_sha256 not in release.get('requests',[]):
        raise Refused('FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND')
    if config.mode=='PRODUCTION_GPU' and (release.get('science_authorized') is not True or release.get('legacy_ingress_closed') is not True or release.get('owner_clear') is not True):
        raise Refused('CUTOVER_OR_SCIENTIFIC_AUTHORIZATION_REQUIRED')
    if sha256(config.fdtd_executable)!=config.executable_sha256:raise Refused('EXECUTABLE_PIN_CHANGED')
    if manifest.get('case_id')!=request.case_id or manifest.get('attempt_id')!=request.attempt_id:
        raise Refused('SOURCE_MANIFEST_IDENTITY_MISMATCH')
    for desc in artifacts.values():
        if isinstance(desc,dict) and 'path' in desc and 'sha256' in desc:
            if sha256(Path(request.source_manifest.path).parent/desc['path'])!=desc['sha256']:
                raise Refused('SOURCE_ARTIFACT_PIN_CHANGED')
    return release


def process_gate(allowed_pid=None):
    """Unknown FDTD/Python access fails closed; never terminate foreign activity."""
    evidence=[]
    for p in psutil.process_iter(['pid','name']):
        name=(p.info['name'] or '').lower()
        if not any(x in name for x in ['fdtd','python']):continue
        try:
            row=identity(p.pid); evidence.append(row)
            cmd=' '.join(row['command']).lower()
            if p.pid==allowed_pid:continue
            if ('fdtd' in name and '-server' not in cmd) or any(x in cmd for x in ['serial_queue.py','gpu_runner_v1','pw_scientific_launcher.py']):
                raise Refused('FOREIGN_SCIENCE_OR_LEGACY_OWNER_PRESENT')
        except psutil.NoSuchProcess:pass
        except psutil.AccessDenied as exc:raise Refused('PROCESS_OWNERSHIP_UNKNOWN') from exc
    return evidence


class ProductionNativeBackend:
    """Independent gated execution; NativeBackend.run remains permanently refused."""
    def execute(self, config, request, ledger, token, budget, fsp, fault=lambda step:None):
        if config.mode!='PRODUCTION_GPU':raise Refused('NATIVE_PRODUCTION_MODE_REQUIRED')
        validate_admission(config,request)
        ledger.note(request,token,'FINAL_GPU_REVALIDATION',gpu_inventory_gate(config))
        contract=request.physical_contract.read()
        if config.schema_version=='APCD_GPU_V21_SERIAL_V1':
            from .general import profile_postprocess_contract
            contract=profile_postprocess_contract(config,request)['resolved_contract']
        spec=launch_spec(config,fsp,list(dict.fromkeys(contract['monitors'].values())))
        Path(fsp.parent/'run_gpu.lsf').write_text(spec['script'],encoding='utf-8')
        return self._execute(config,request,ledger,token,budget,spec['command'],fsp.parent,fault)

    def _execute(self,config,request,ledger,token,budget,command,cwd,fault):
        if config.mode=='PRODUCTION_GPU':
            validate_admission(config,request)
            ledger.note(request,token,'PRELAUNCH_GPU_RESOURCE_GATE',gpu_inventory_gate(config))
        ledger.note(request,token,'PRELAUNCH_PROCESS_CENSUS',{'processes':process_gate(os.getpid())})
        ledger.launch_once(request,token,budget)
        fault('launch_requested')
        log=Path(cwd)/'native.log'
        started=time.time()
        with log.open('xb') as output:
            p=subprocess.Popen(command,cwd=cwd,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,close_fds=True)
            fault('process_started')
            observed={}
            try:
                head=identity(p.pid);observed[p.pid]=head
                ledger.note(request,token,'LAUNCHER_PROCESS',head)
                while p.poll() is None:
                    try:
                        children=psutil.Process(p.pid).children(recursive=True)
                    except psutil.NoSuchProcess:
                        if p.poll() is not None:break
                        raise Refused('LAUNCHER_IDENTITY_LOST')
                    for child in children:
                        try:row=identity(child.pid)
                        except psutil.NoSuchProcess:continue
                        observed[child.pid]=row
                        if 'fdtd-engine' in Path(row['executable']).name.lower():
                            engine_cwd=Path(psutil.Process(child.pid).cwd())
                            matches=[]
                            for argument in row['command']:
                                if str(argument).lower().endswith('.fsp'):
                                    candidate=Path(argument)
                                    candidate=candidate if candidate.is_absolute() else engine_cwd/candidate
                                    matches.append(candidate.resolve()==Path(command[-1]).resolve())
                            if row['creation_time']<head['creation_time']-0.001 or not any(matches):
                                raise Refused('ENGINE_PROCESS_PROJECT_OR_ANCESTRY_MISMATCH')
                            row['working_directory']=str(engine_cwd)
                            ledger.note(request,token,'ENGINE_PROCESS',row)
                    ledger.note(request,token,'HEARTBEAT',dict(time=time.time(),processes=list(observed.values())))
                    time.sleep(config.heartbeat_seconds)
                output.flush();os.fsync(output.fileno())
                if any(identity_state(row) not in ['dead','reused'] for pid,row in observed.items() if pid!=p.pid):
                    raise Refused('DESCENDANT_STILL_LIVE_OR_UNKNOWN')
                result=dict(returncode=p.returncode,launcher=head,processes=list(observed.values()),log=str(log),log_sha256=sha256(log),started_unix=started,returned_unix=time.time(),native_wall_seconds=time.time()-started)
                ledger.note(request,token,'PROCESS_RETURNED',result)
                if p.returncode:raise Refused('NATIVE_RETURN_OR_LICENSE_ERROR:'+str(p.returncode))
                if config.mode=='PRODUCTION_GPU' and not any('fdtd-engine' in Path(row['executable']).name.lower() for row in observed.values()):
                    raise Refused('ENGINE_PID_NOT_OBSERVED')
                return result
            except BaseException:
                # Never kill an engine or wait forever after worker failure. Durable entry holds.
                raise


class EquivalentBackend(ProductionNativeBackend):
    def __init__(self,script):self.script=Path(script)
    def execute(self,config,request,ledger,token,budget,fsp,fault=lambda step:None):
        if config.mode!='PRODUCTION_EQUIVALENT' or config.fdtd_executable!=sys.executable or not self.script.read_text(encoding='utf-8').startswith('# APCD_ZERO_SOLVER_FIXTURE'):
            raise Refused('ZERO_SOLVER_EXECUTABLE_REQUIRED')
        return self._execute(config,request,ledger,token,budget,[sys.executable,str(self.script),str(fsp)],fsp.parent,fault)


def run_serial_case(config,request,ledger,backend,validator,*,fault=lambda step:None,archive=archive_pair):
    require_trusted_production_config(config)
    budget=budget_for(config)
    token=ledger.claim(request.request_sha256,identity())
    try:
        validate_admission(config,request);budget.validate(request);window_admission(config,request)
        if config.mode=='PRODUCTION_GPU':
            if type(backend) is not ProductionNativeBackend or not isinstance(validator,NativeTruthValidator):
                raise Refused('FORMAL_NATIVE_IMPLEMENTATIONS_REQUIRED')
            dependencies=validator.preflight(request) if config.schema_version=='APCD_GPU_V21_SERIAL_V1' else validator.preflight()
            ledger.note(request,token,'TRUTH_DEPENDENCY_PREFLIGHT',dependencies)
            preflight=native_preflight(config,request)
            ledger.note(request,token,'NATIVE_PREFLIGHT',preflight)
        fault('preflight')
        process_gate(os.getpid())
        folder=case_storage(config,request)/'attempts'/request.request_sha256
        folder.mkdir(parents=True,exist_ok=False)
        fsp=folder/'run.fsp';shutil.copyfile(request.pre_fsp,fsp)
        if sha256(fsp)!=request.pre_fsp_sha256:raise Refused('STAGING_SHA_MISMATCH')
        receipt=budget.prepare_entry(request,token,fault)
        fault('before_local_mirror');ledger.mirror(request,token,receipt);fault('after_local_mirror')
        execution=backend.execute(config,request,ledger,token,budget,fsp,fault)
        fault('solver_returned')
        evidence=validate_truth(config,request,fsp,validator,archive)
        if (registered_config(config) or diag2_config(config)) and isinstance(execution,dict):
            # Preserve launcher wall time, return code, log SHA and observed PID/create-time
            # evidence in every terminal receipt, including the DIAG2 consumer path.
            evidence['execution']=execution
        fault('truth_valid_before_coupling');budget.finish_truth(request,evidence)
        fault('coupling_truth_before_local');ledger.terminal(request,token,evidence=evidence)
        return evidence
    except BaseException as exc:
        ledger.terminal(request,token,error=repr(exc))
        if registered_config(config) and isinstance(exc,Refused) and str(exc)=='WINDOW_INSUFFICIENT_NO_NEW_ENTRY':
            from .v3 import close_proven_window_preentry
            close_proven_window_preentry(config,request,ledger,token)
        raise


def validate_truth(config,request,fsp,validator,archive=archive_pair):
    destination=case_storage(config,request)/'archives'/request.request_sha256
    if destination.exists():
        inventory=bundle_inventory(destination/'run.fsp',config.native_h5_name)
        if inventory!=bundle_inventory(fsp,config.native_h5_name):raise Refused('RECOVERY_ARCHIVE_CONFLICT')
        bundle=dict(path=str(destination),files=inventory,receipt_sha256=sha256(destination/'bundle_receipt.json'))
    else:bundle=archive(fsp,destination,config.native_h5_name)
    validated=load_only(destination/'run.fsp',config.native_h5_name,lambda p:validator(p,request,destination))
    from .diag2 import is_diag2_config
    expected_importer=getattr(config,'importer_entrypoint','load_verified_runner_case')
    if validated.get('verdict')!='PASS' or validated.get('outputs')!=609 or validated.get('fresh_load_verified') is not True or validated.get('actual_importer')!=expected_importer:
        raise Refused('FRESH_LOAD_AND_REAL_IMPORTER_REQUIRED')
    if config.mode=='PRODUCTION_GPU' and not validated.get('labels_artifact'):
        raise Refused('DURABLE_COUPLING_LABELS_REQUIRED')
    return dict(bundle=bundle,validation=validated)


def recover_load_only(config,request,ledger,validator):
    snapshot=ledger.audit(); slot=snapshot['slot']; token=slot['token']
    if not token or slot['request_sha']!=request.request_sha256:raise Refused('RECOVERY_OWNER_REQUIRED')
    owner=json.loads(slot['owner'])
    if identity_state(owner) not in ['dead','reused']:
        raise Refused('RECOVERY_WORKER_STILL_LIVE_OR_UNKNOWN')
    process_gate(os.getpid())
    # Process exit receipts and confirmed engine exit are required; missing evidence never implies done.
    returns=[json.loads(e['payload']) for e in snapshot['events'] if e['request_sha']==request.request_sha256 and e['kind']=='PROCESS_RETURNED']
    if len(returns)!=1 or returns[0]['returncode']!=0 or any(identity_state(p) not in ['dead','reused'] for p in returns[0]['processes']):
        raise Refused('RECOVERY_PROCESS_EXIT_NOT_PROVEN')
    evidence=validate_truth(config,request,case_storage(config,request)/'attempts'/request.request_sha256/'run.fsp',validator)
    budget=budget_for(config)
    record=json.loads(budget.path.read_text(encoding='utf-8'))['case_records'][request.case_id]
    if record['phase']=='V2_ENTRY_UNCERTAIN':budget.finish_truth(request,evidence)
    elif record['phase']!='V2_TRUTH_VALID' or record.get('evidence',{}).get('bundle')!=evidence['bundle']:raise Refused('RECOVERY_COUPLING_CONFLICT')
    ledger.terminal(request,token,evidence=evidence)
    return evidence


def controller(config,requests,backend,validator,*,fault=lambda step:None):
    with exclusive(Path(config.coupling_ledger).with_suffix('.v2_controller.lock')), exclusive(Path(config.runtime_root)/'.v2_controller.lock'):
        return controller_owned(config,requests,backend,validator,fault=fault)


def controller_owned(config,requests,backend,validator,*,fault=lambda step:None):
    """Existing serial loop; caller must retain both controller OS locks."""
    if diag2_config(config):
        from .diag2 import validate_diag2_batch
        validate_diag2_batch(config,requests)
    ledger=SerialLedger(Path(config.runtime_root)/'ledger.sqlite3')
    slot=ledger.audit()['slot']
    if slot['token']:
        candidate=[r for r in requests if r.request_sha256==slot['request_sha']]
        if len(candidate)!=1 or identity_state(json.loads(slot['owner'])) not in ['dead','reused']:
            raise Refused('PERSISTED_OWNER_REQUIRES_REVIEW')
        # This function has no solver/backend parameter. Only a proven returned process can recover.
        recover_load_only(config,candidate[0],ledger,validator)
    for request in requests:
        previous=[r for r in ledger.audit()['tasks'] if r['request_sha']==request.request_sha256]
        if previous and previous[0]['state']=='REGISTERED' and not previous[0]['entered']:
            ready=[e for e in ledger.audit()['events'] if e['request_sha']==request.request_sha256 and e['kind']=='PREENTRY_REBOUND_READY']
            if len(ready)!=1 or json.loads(ready[0]['payload']).get('new_request_sha256')!=request.request_sha256:
                raise Refused('REGISTERED_RECOVERY_NOT_EXPLICITLY_REBOUND')
            run_serial_case(config,request,ledger,backend,validator,fault=fault)
            if ledger.audit()['slot']['token']:raise Refused('TRUTH_BEFORE_NEXT_REQUIRED')
            continue
        if previous:
            external=json.loads(Path(config.coupling_ledger).read_text(encoding='utf-8'))
            if previous[0]['state']=='TRUTH_VALID' and external['case_records'].get(request.case_id,{}).get('phase')=='V2_TRUTH_VALID':
                evidence=json.loads(previous[0]['bundle']); bundle=evidence['bundle']
                if bundle_inventory(Path(bundle['path'])/'run.fsp',config.native_h5_name)!=bundle['files'] or external['case_records'][request.case_id].get('evidence',{}).get('bundle')!=bundle:
                    raise Refused('PERSISTED_TRUTH_INTEGRITY_CONFLICT')
                continue
            raise Refused('PREVIOUS_ATTEMPT_REQUIRES_REVIEW_NO_REPLAY')
        validate_admission(config,request);window_admission(config,request)
        ledger.register(request,config)
        run_serial_case(config,request,ledger,backend,validator,fault=fault)
        if ledger.audit()['slot']['token']:raise Refused('TRUTH_BEFORE_NEXT_REQUIRED')
    return ledger.audit()


def gpu_inventory_gate(config):
    import csv
    import io
    result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
    devices=list(csv.reader(io.StringIO(result.stdout)))
    if len(devices)!=1 or len(devices[0])!=2 or devices[0][0].strip()!=config.gpu_device:
        raise Refused('GPU_DEVICE_NOT_QUALIFIED')
    values=[int(devices[0][1].strip())]
    if values[0]<1369:raise Refused('GPU_MEMORY_NOT_QUALIFIED')
    result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
    from .gpu_readonly import resolve_idle_edt, snapshot, wddm_exclusivity
    wddm_samples=[]
    for index in range(3):
        wddm_samples.append(snapshot())
        if index < 2: time.sleep(1)
    wddm=wddm_exclusivity(wddm_samples)
    gpu_consumers=resolve_idle_edt(classify_gpu_consumers(result.stdout))
    if any(r['classification'] not in ['DISPLAY_ACTIVITY','VERIFIED_IDLE_EDT_GUI','VERIFIED_IDLE_DESKTOP'] for r in gpu_consumers):
        raise Refused('EXTERNAL_GPU_SCIENCE_OR_UNATTRIBUTED_CONSUMER')
    return dict(gpu_free_mib=values[0],gpu_consumers=gpu_consumers,wddm_activity=wddm)


def native_preflight(config,request):
    gpu=gpu_inventory_gate(config)
    from .native_readonly import native_session,pinned_module
    pin=config.truth_toolchain['lumapi']
    lum=pinned_module(pin.path,pin.sha256,'lumapi')
    receipt={}
    with native_session(lum.FDTD,{request.pre_fsp:request.pre_fsp_sha256},receipt,allow_license=True) as fd:
        fd.eval("checkout('FDTD_Solutions_engine');")
        fd.load(request.pre_fsp)
        names=[fd.getresource('FDTD',i,'name') for i in range(1,int(fd.getresource('FDTD'))+1)]
        if config.gpu_resource not in names:raise Refused('EXACT_GPU_RESOURCE_NOT_PRESENT')
        check=fd.runsystemcheck('FDTD','GPU')
        import numpy as np
        maximum=float(np.asarray(check['Approximate_GPU_Memory_Requirements']['Maximum_Bytes']).item())
        if maximum>gpu['gpu_free_mib']*1024*1024:raise Refused('EXACT_CASE_GPU_MEMORY_INSUFFICIENT')
    # API feature availability is not GPU-engine license confirmation.
    return dict(API_LICENSE_AVAILABLE=True,GPU_ENGINE_LICENSE_NOT_TESTED=True,maximum_gpu_bytes=maximum,resources=names,**gpu)


def classify_gpu_consumers(text):
    """WDDM can enumerate desktop apps with N/A memory; never equate N/A to idle."""
    import csv
    import io
    display={'dwm.exe','explorer.exe','msedge.exe','msedgewebview2.exe','searchhost.exe','startmenuexperiencehost.exe','textinputhost.exe','shellexperiencehost.exe','shellhost.exe','applicationframehost.exe','systemsettings.exe','taskmgr.exe','tabtip.exe','phoneexperiencehost.exe','crossdeviceresume.exe','hipsdaemon.exe','todesk.exe','awesun.exe','gameviewerserver.exe'}
    rows=[]
    for cells in csv.reader(io.StringIO(text)):
        if not cells:continue
        if len(cells)!=3:raise Refused('GPU_CONSUMER_SCHEMA_UNKNOWN')
        try:
            pid=int(cells[0].strip());record=identity(pid)
        except (ValueError,psutil.AccessDenied,psutil.NoSuchProcess) as exc:
            raise Refused('GPU_CONSUMER_IDENTITY_UNKNOWN') from exc
        image=cells[1].strip()
        if os.path.normcase(os.path.normpath(record['executable']))!=os.path.normcase(os.path.normpath(image)):
            raise Refused('GPU_PID_IMAGE_MISMATCH')
        classification='DISPLAY_ACTIVITY' if Path(image).name.lower() in display else 'SCIENCE_OR_UNATTRIBUTED'
        rows.append(dict(**record,reported_memory=cells[2].strip(),classification=classification))
    return rows



def _diag2_time_convergence_telemetry(fd, request, np):
    """Read terminal FDTD timing only for the two frozen DIAG2 roles."""
    if getattr(request, 'dataset_id', None) != 'APCD_COUPLING_V3_TIME_DIAG2_V1':
        return None
    if getattr(request, 'role', None) != 'TIME_CONVERGENCE_DIAGNOSTIC_ONLY':
        raise Refused('DIAG2_ROLE_NOT_ALLOWLISTED')
    if getattr(request, 'case_id', None) not in ('K6V3_TIME_DIAG2_A1_5NM_6PS', 'K6V3_TIME_DIAG2_A2_5NM_6PS'):
        raise Refused('DIAG2_CASE_NOT_ALLOWLISTED')
    if getattr(request, 'attempt_id', None) != 'attempt_001':
        raise Refused('DIAG2_ATTEMPT_NOT_ALLOWLISTED')
    max_time = float(request.simulation_time_s)
    threshold = float(request.auto_shutoff_min)
    if max_time != 6e-12 or threshold != 1e-6:
        raise Refused('DIAG2_TIME_CONTRACT_NOT_6PS_1E6')

    names = set(str(fd.getresult('FDTD')).splitlines())
    required = {'status', 'autoshutoff level', 'initialization time',
                'simulation run time', 'total gpu sms'}
    if not required <= names:
        raise Refused('DIAG2_FDTD_TELEMETRY_RESULT_SET_INCOMPLETE')
    status_raw = np.asarray(fd.getresult('FDTD', 'status')).reshape(-1)
    if status_raw.size != 1 or not np.isfinite(status_raw).all():
        raise Refused('DIAG2_FDTD_STATUS_INVALID')
    status_float = float(status_raw[0])
    status = int(round(status_float))
    if status_float != status:
        raise Refused('DIAG2_FDTD_STATUS_NONINTEGER')

    level = fd.getresult('FDTD', 'autoshutoff level')
    if not isinstance(level, dict) or not {'t', 'wall clock time', 'autoshutoff'} <= set(level):
        raise Refused('DIAG2_AUTOSHUTOFF_RESULT_SCHEMA_INVALID')
    times = np.asarray(level['t'], dtype=float).reshape(-1)
    wall = np.asarray(level['wall clock time'], dtype=float).reshape(-1)
    values = np.asarray(level['autoshutoff'], dtype=float).reshape(-1)
    if times.size < 2 or times.size != wall.size or times.size != values.size:
        raise Refused('DIAG2_AUTOSHUTOFF_CURVE_LENGTH_INVALID')
    if not all(np.isfinite(x).all() for x in (times, wall, values)):
        raise Refused('DIAG2_AUTOSHUTOFF_CURVE_NONFINITE')
    if np.any(times < 0) or np.any(wall < 0) or np.any(values < 0):
        raise Refused('DIAG2_AUTOSHUTOFF_CURVE_NEGATIVE')
    if np.any(np.diff(times) <= 0) or np.any(np.diff(wall) < 0):
        raise Refused('DIAG2_AUTOSHUTOFF_CURVE_ORDER_INVALID')

    benchmarks = {}
    for name in ('simulation run time', 'initialization time', 'total gpu sms'):
        value = np.asarray(fd.getresult('FDTD', name), dtype=float).reshape(-1)
        if value.size != 1 or not np.isfinite(value).all() or float(value[0]) < 0:
            raise Refused('DIAG2_FDTD_BENCHMARK_RESULT_INVALID:' + name)
        benchmarks[name] = float(value[0])
    final = float(values[-1])
    met = final <= threshold
    stop_reason = {1: 'SIMULATION_TIME_LIMIT', 2: 'AUTO_SHUTOFF', 3: 'DIVERGED'}.get(
        status, 'INCOMPLETE_OR_UNKNOWN_STATUS')
    if status == 2:
        convergence = 'AUTO_SHUTOFF_THRESHOLD_MET' if met else 'AUTO_SHUTOFF_STATUS_THRESHOLD_CONFLICT'
    elif status == 1:
        convergence = 'THRESHOLD_MET_AT_TIME_LIMIT' if met else 'TIME_CONVERGENCE_UNRESOLVED'
    elif status == 3:
        convergence = 'DIVERGED'
    else:
        convergence = 'INCOMPLETE_OR_UNKNOWN_STATUS'
    return dict(
        schema='APCD_GPU_V2_DIAG2_FDTD_TIME_EVIDENCE_V1',
        dataset_id=request.dataset_id, case_id=request.case_id,
        attempt_id=request.attempt_id, role=request.role,
        request_sha256=request.request_sha256,
        physical_contract_sha256=request.physical_contract_sha256,
        configured_simulation_time_s=max_time, auto_shutoff_threshold=threshold,
        status_code=status, stop_reason=stop_reason,
        time_convergence_status=convergence,
        # Status 1 means the engine reached the configured time limit. The sampled
        # curve's last point can precede that limit by one recorder interval.
        simulation_physical_time_s=max_time if status == 1 else float(times[-1]),
        autoshutoff_sampled_last_time_s=float(times[-1]),
        solver_simulation_run_time_s=benchmarks['simulation run time'],
        solver_initialization_time_s=benchmarks['initialization time'],
        total_gpu_sms=benchmarks['total gpu sms'],
        gpu_engine_result_confirmed=benchmarks['total gpu sms'] > 0,
        final_autoshutoff_value=final, auto_shutoff_threshold_met_at_stop=met,
        autoshutoff_curve=dict(simulation_time_s=times.tolist(),
                               wall_clock_time_s=wall.tolist(),
                               autoshutoff=values.tolist()),
        sample_count=int(times.size))


def _require_diag2_terminal_evidence(evidence, artifact):
    if evidence['status_code'] == 3:
        raise Refused('DIAG2_FDTD_DIVERGED:' + str(artifact))
    if evidence['status_code'] not in (1, 2):
        raise Refused('DIAG2_FDTD_TERMINAL_STATUS_INVALID:' + str(artifact))
    if not evidence['gpu_engine_result_confirmed']:
        raise Refused('DIAG2_GPU_ENGINE_RESULT_UNCONFIRMED:' + str(artifact))
    if evidence['time_convergence_status'] == 'AUTO_SHUTOFF_STATUS_THRESHOLD_CONFLICT':
        raise Refused('DIAG2_AUTO_SHUTOFF_STATUS_CONFLICT:' + str(artifact))


class NativeTruthValidator:
    """Reuse the G025 verified LOAD/postprocess/importer contracts, never science run."""
    def __init__(self,config):self.config=config

    def _dependencies(self):
        import h5py
        import numpy as np
        import importlib
        from .native_readonly import native_session,pinned_module
        cfg=self.config
        for pin in cfg.truth_toolchain.values():
            if sha256(pin.path)!=pin.sha256:raise Refused('TRUTH_DEPENDENCY_PIN_CHANGED')
        helper=cfg.truth_toolchain.get('incident_power_helper')
        if helper is None:raise Refused('INCIDENT_POWER_HELPER_PIN_REQUIRED')
        from .science import mdc_tmm_complex_incident_power_v1 as incident_power
        if Path(incident_power.__file__).resolve()!=Path(helper.path).resolve() or sha256(incident_power.__file__)!=helper.sha256:
            raise Refused('INCIDENT_POWER_HELPER_PIN_CHANGED')
        post=cfg.truth_toolchain['postprocessor'];api=cfg.truth_toolchain['lumapi']
        for path in [Path(cfg.coupling_root)/'scripts/coupling_ml']:
            if str(path) not in sys.path:sys.path.insert(0,str(path))
        from . import science
        launcher=pinned_module(post.path,post.sha256,'apcd_gpu_v2.science.postprocess')
        lum=pinned_module(api.path,api.sha256,'lumapi')
        importer=importlib.import_module(getattr(cfg,'importer_module','k6_v2_pipeline.ingest'))
        if sha256(importer.__file__)!=cfg.truth_toolchain['importer'].sha256:raise Refused('IMPORTER_SOURCE_PIN_CHANGED')
        from .diag2 import is_diag2_config
        if is_diag2_config(cfg) or cfg.schema_version=='APCD_GPU_V21_SERIAL_V1':
            if not callable(getattr(importer,cfg.importer_entrypoint,None)) or (cfg.label_validator_entrypoint is not None and not callable(getattr(importer,cfg.label_validator_entrypoint,None))):
                raise Refused('DIAG2_IMPORTER_ENTRYPOINTS_REQUIRED')
        elif not callable(getattr(importer,'load_verified_runner_case',None)):
            raise Refused('IMPORTER_ENTRYPOINT_REQUIRED')
        return h5py,np,launcher,lum,importer

    def preflight(self,request=None):
        h5py,np,launcher,lum,importer=self._dependencies()
        science={}
        if self.config.schema_version=='APCD_GPU_V21_SERIAL_V1':
            from .general import validate_profile_admission
            if request is None: raise Refused('PROFILE_PREFLIGHT_REQUEST_REQUIRED')
            science=validate_profile_admission(self.config,request,importer)
            from .general import profile_postprocess_contract
            projection=profile_postprocess_contract(self.config,request)
            science['postprocess_contract_view']={k:v for k,v in projection.items() if k!='resolved_contract'}
        return dict(verdict='PASS',numpy=np.__version__,h5py=h5py.__version__,
                    pins={key:pin.sha256 for key,pin in self.config.truth_toolchain.items()},native_session_opened=False,
                    **({'science_profile_admission':science} if science else {}))

    def __call__(self,fsp,request,destination):
        from .native_readonly import native_session
        h5py,np,launcher,lum,importer=self._dependencies()
        cfg=self.config;post=cfg.truth_toolchain['postprocessor']
        pc=request.physical_contract.read()
        projection=None
        if cfg.schema_version=='APCD_GPU_V21_SERIAL_V1':
            from .general import profile_postprocess_contract
            projection=profile_postprocess_contract(cfg,request)
            pc=projection['resolved_contract']
        output=case_storage(cfg,request)/'validation'/request.request_sha256/uuid.uuid4().hex
        output.mkdir(parents=True)
        task='V2_'+request.request_sha256[:24]
        postcfg=dict(pw_contract=pc,run_fsp=str(fsp),case=request.case_id,attempt=request.attempt_id,task=task,gpu_resource_name=cfg.gpu_resource)
        session={};time_evidence=None;time_artifact=None
        with native_session(lum.FDTD,{str(fsp):sha256(fsp)},session) as fd:
            fd.load(str(fsp))
            if getattr(request,'dataset_id',None)=='APCD_COUPLING_V3_TIME_DIAG2_V1':
                try:
                    time_evidence=_diag2_time_convergence_telemetry(fd,request,np)
                except BaseException as exc:
                    time_artifact=output/'FDTD_TIME_DIAGNOSTICS_ERROR.json'
                    durable_json(time_artifact,dict(schema='APCD_GPU_V2_DIAG2_FDTD_TIME_EVIDENCE_ERROR_V1',
                        case_id=request.case_id,attempt_id=request.attempt_id,request_sha256=request.request_sha256,error=repr(exc)))
                    raise Refused('DIAG2_TIME_TELEMETRY_INVALID:'+str(time_artifact)) from exc
                time_artifact=output/'FDTD_TIME_DIAGNOSTICS.json'
                durable_json(time_artifact,time_evidence)
                _require_diag2_terminal_evidence(time_evidence, time_artifact)
            launcher.load_only_validate(fd,postcfg)
            for monitor in dict.fromkeys(pc['monitors'].values()):
                waves=299792458/np.asarray(fd.getdata(monitor,'f')).reshape(-1)*1e9
                if len(waves)!=21 or not np.allclose(np.sort(waves),np.arange(440,461),atol=1e-6,rtol=0):raise Refused('NATIVE_WAVELENGTHS_INVALID')
                for component in ['Ex','Ey','Ez','Hx','Hy','Hz']:
                    a=np.asarray(fd.getdata(monitor,component))
                    if not np.iscomplexobj(a) or not np.isfinite(a).all():raise Refused('NATIVE_COMPLEX_EH_INVALID')
                for axis in ['x','y','z']:
                    a=np.asarray(fd.getdata(monitor,axis))
                    if not a.size or not np.isfinite(a).all():raise Refused('NATIVE_COORDINATES_INVALID')
            raw,metrics,paths=launcher.postprocess(fd,postcfg,str(output))
        for key in ['order_sign','reference_plane_deembedding','lossy_gan']:
            if metrics.get(key,{}).get('status')!='PASS':raise Refused('SCIENTIFIC_VALIDATION_FAILED:'+key)
        raw['run_id']=task
        if time_evidence is not None:metrics['diag2_time_convergence']=time_evidence
        Path(paths['raw_json']).write_text(json.dumps(raw,sort_keys=True,indent=2),encoding='utf-8')
        truth=output/'truth.h5'
        with h5py.File(truth,'x') as h5:
            for key,value in dict(run_id=task,case_id=request.case_id,attempt_id=request.attempt_id,launcher_id='pw_scientific_launcher.py@'+post.sha256).items():h5.attrs[key]=value
            for key,value in dict(raw_json=raw,metrics_json=metrics).items():h5.create_dataset(key,data=json.dumps(value,sort_keys=True,default=str),dtype=h5py.string_dtype('utf-8'))
            h5.flush()
        manifest=output/'source_manifest.json'
        manifest_body=dict(case_id=request.case_id,attempt_id=request.attempt_id,geometry=list(request.ordered_D_nm),physical_contract_sha256=request.physical_contract_sha256,pre_fsp_sha256=request.pre_fsp_sha256,run_id=task)
        if cfg.schema_version=='APCD_GPU_V21_SERIAL_V1':
            from .general import profile_native_bindings
            profile_native=profile_native_bindings(cfg,request,fsp)
            manifest_body['postprocess_contract_view']={k:v for k,v in projection.items() if k!='resolved_contract'}
            manifest_body.update(request_sha256=profile_native['request_sha256'],
                execution_request_sha256=profile_native['execution_request_sha256'],
                physical_contract_file_sha256=profile_native['physical_contract_file_sha256'],
                source_acceptance_file_sha256=profile_native['source_acceptance_file_sha256'],
                native_fsp_sha256=profile_native['native_fsp']['sha256'],native_h5_sha256=profile_native['native_h5']['sha256'])
            manifest_body.update(batch_id=request.batch_id,profile_id=cfg.validation_profile,
                source_manifest_path=request.source_manifest.path,source_manifest_sha256=request.source_manifest.sha256,
                admission_sha256=cfg.science_admission.sha256,manifest_sha256=cfg.batch_manifest.sha256,
                certification_sha256=next(p.certification.sha256 for p in cfg.platform.profiles if p.profile_id==cfg.validation_profile),
                role=request.role,ordered_D_nm=list(request.ordered_D_nm))
        from .diag2 import is_diag2_config
        if is_diag2_config(cfg):
            manifest_body.update(dataset_id=request.dataset_id,batch_id=request.batch_id,role=request.role,
                ordered_D1_D6_nm=list(request.ordered_D_nm),geometry_sha256=request.geometry_sha256,
                candidate_pre_fsp_sha256=request.pre_fsp_sha256,
                source_run_fsp_sha256=request.source_run_fsp_sha256,
                source_setup_fsp_sha256=request.source_setup_fsp_sha256,
                simulation_time_s=request.simulation_time_s,auto_shutoff_min=request.auto_shutoff_min,
                source_manifest_path=request.source_manifest.path,source_manifest_sha256=request.source_manifest.sha256)
        durable_json(manifest,manifest_body)
        def descriptor(p):return dict(path=str(p),sha256=sha256(p))
        record=dict(case_id=request.case_id,attempt_id=request.attempt_id,role=request.role,ordered_D_nm=list(request.ordered_D_nm),physical_contract_sha256=request.physical_contract_sha256,status='DONE',solver_invocations=1,replay_count=0,
            source_manifest=descriptor(manifest),state_npz=descriptor(paths['state_npz']),state_metadata=descriptor(paths['state_metadata']),raw_npz=descriptor(paths['raw_fields']),raw_metadata=descriptor(paths['raw_json']),orders_json=descriptor(paths['angular']),truth_h5=descriptor(truth))
        if cfg.schema_version=='APCD_GPU_V21_SERIAL_V1':
            record.update(profile_native)
            record.update(batch_id=request.batch_id,profile_id=cfg.validation_profile,
                manifest_sha256=cfg.batch_manifest.sha256,admission_sha256=cfg.science_admission.sha256,
                certification_sha256=manifest_body['certification_sha256'])
        if is_diag2_config(cfg):
            record.update(dataset_id=request.dataset_id,batch_id=request.batch_id,geometry_sha256=request.geometry_sha256,
                simulation_time_s=request.simulation_time_s,auto_shutoff_min=request.auto_shutoff_min,
                source_run_fsp_sha256=request.source_run_fsp_sha256,source_setup_fsp_sha256=request.source_setup_fsp_sha256)
            imported=getattr(importer,cfg.importer_entrypoint)(record,expected_role=request.role,
                root=Path(cfg.coupling_root),registry=cfg.registry.read())
            labels=getattr(importer,cfg.label_validator_entrypoint)(imported.c_hat,imported.p_scale,
                case_id=request.case_id,physical_contract_sha256=request.physical_contract_sha256)
            if not isinstance(labels,dict) or labels.get('verdict')!='PASS' or labels.get('outputs')!=609:
                raise Refused('DIAG2_COUPLING_LABEL_VALIDATION_FAILED')
        elif cfg.schema_version=='APCD_GPU_V21_SERIAL_V1':
            from .general import import_profile_truth
            imported,labels=import_profile_truth(cfg,request,record,importer)
        elif registered_config(cfg):
            from .v3 import import_truth
            imported,labels=import_truth(cfg,request,record,importer)
        else:
            imported=importer.load_verified_runner_case(record,expected_role=request.role,root=Path(cfg.coupling_root))
            from .coupling import validate_labels
            labels=validate_labels(imported.c_hat,imported.p_scale,role=request.role,physical_contract_sha256=CONTRACT_SHA)
        label_path=output/'labels.npz'
        with label_path.open('xb') as stream:
            np.savez_compressed(stream,case_id=np.asarray(request.case_id),attempt_id=np.asarray(request.attempt_id),role=np.asarray(request.role),ordered_D_nm=np.asarray(request.ordered_D_nm,dtype=np.int64),wavelengths_nm=np.arange(440,461),order_m=np.arange(-3,4),polarization=np.asarray(['TE','TM']),C_hat_real=imported.c_hat.real,C_hat_imag=imported.c_hat.imag,P_scale=imported.p_scale,eta=imported.eta,absolute_order=imported.absolute_order)
            stream.flush();os.fsync(stream.fileno())
        actual_importer=getattr(cfg,'importer_entrypoint','load_verified_runner_case')
        result=dict(verdict='PASS',outputs=labels['outputs'],actual_importer=actual_importer,fresh_load_verified=True,record=record,native_session=session,labels_artifact=descriptor(label_path),**({'registered_provenance':labels['provenance']} if registered_config(cfg) else {}))
        if cfg.schema_version=='APCD_GPU_V21_SERIAL_V1': result['science_profile_acceptance']=labels
        if time_evidence is not None:
            result['time_convergence']=time_evidence
            result['time_convergence_artifact']=descriptor(time_artifact)
        durable_json(output/'validation.json',result)
        return result
