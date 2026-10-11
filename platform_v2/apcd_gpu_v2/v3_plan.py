"""Finite V3 phases inside the one V2 controller; no allocator or solver retry."""
import json
import time
import uuid
import subprocess
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
from typing import Literal
from .artifacts import durable_json,sha256
from .config import StrictModel
from .ledger import Refused
from .serial import Pin,SerialLedger,exclusive,controller_owned,ProductionNativeBackend,NativeTruthValidator,replace_json
from .v3 import V3Config,V3Request,V3Budget,registry_cases,ROLES,morning_report,rebind_proven_window


class Plan(StrictModel):
    schema: Literal['APCD_V3_FINITE_PHASE_PLAN_V1']
    template_config: Pin
    code_inventory: Pin
    diagnostic_evaluator: Pin
    expires_unix: float
    latest_window_days: Literal[3] = 3
    max_new_entries: Literal[56] = 56


def deadline(now):
    local=datetime.fromtimestamp(now,timezone(timedelta(hours=8)))
    end=local.replace(hour=10,minute=0,second=0,microsecond=0)
    if local>=end:end+=timedelta(days=1)
    return end.timestamp()


def verify_code(plan):
    data=plan.code_inventory.read()
    root=Path(data['code_root']).resolve()
    for name,pin in data['files'].items():
        p=(root/name).resolve()
        if root not in p.parents or sha256(p)!=pin['sha256']:raise Refused('IMMUTABLE_CODE_INVENTORY_CHANGED')
    plan.diagnostic_evaluator.read() if Path(plan.diagnostic_evaluator.path).suffix=='.json' else None
    if sha256(plan.diagnostic_evaluator.path)!=plan.diagnostic_evaluator.sha256:raise Refused('NUMERICAL_EVALUATOR_PIN_CHANGED')


def remaining_phase(config,kind):
    rows=registry_cases(config);data=json.loads(Path(config.coupling_ledger).read_text())
    # Never interpret lost local state or a partial external receipt as a fresh budget.
    budget=V3Budget(config)
    uncertain=set(data['entered_case_ids'])-set(data['truth_valid_case_ids'])
    if uncertain:raise Refused('UNCERTAIN_SCIENCE_ENTRY_HOLD')
    for p in budget.receipts.glob('*__attempt_001.json'):
        if json.loads(p.read_text())['case_id'] not in data['truth_valid_case_ids']:raise Refused('UNCERTAIN_RECEIPT_HOLD')
    selected=[x for x in rows.values() if ROLES[x['role']].startswith(kind) and x['case_id'] in data['remaining_unentered_case_ids']]
    return selected


def finite_phase(config,rows,folder,*,gate=None,now=None):
    now=time.time() if now is None else now
    folder=Path(folder);folder.mkdir(exist_ok=False,parents=True)
    doc=config.model_dump();doc['window']['deadline_unix']=deadline(now)
    if gate is not None:doc['diagnostic_gate']=gate.model_dump()
    # Admission digest deliberately excludes configuration SHA to break the hash cycle.
    provisional=[V3Request(case_id=x['case_id'],attempt_id=x['attempt_id'],role=x['role'],ordered_D_nm=tuple(x['ordered_D_nm']),pre_fsp=x['pre_fsp'],pre_fsp_sha256=x['pre_fsp_sha256'],source_manifest=x['source_manifest'],physical_contract=x['physical_contract'],physical_contract_sha256=x['physical_contract_sha256'],config_sha256='',dataset_id=config.dataset_id,registry_sha256=config.registry.sha256,frozen_case_sha256=x['frozen_case_sha256']) for x in rows]
    release=dict(schema='APCD_V3_FINITE_SERIAL_RELEASE_V1',dataset_id=config.dataset_id,queue_sha256=config.queue.sha256,registry_sha256=config.registry.sha256,requests=[x.admission_sha256 for x in provisional],expires_unix=deadline(now),science_authorized=True,science_acceptance_sha256=config.science_acceptance.sha256)
    path=folder/'release.json';durable_json(path,release);doc['release']=dict(path=str(path),sha256=sha256(path))
    cfg=V3Config.model_validate(doc)
    reqs=[x.model_copy(update={'config_sha256':cfg.sha256}) for x in provisional]
    durable_json(folder/'config.json',cfg.model_dump());durable_json(folder/'requests.json',[x.model_dump() for x in reqs])
    return cfg,reqs


def diagnostic_gate(plan,config,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    data=dict(schema='V3_COUPLING_NUMERICAL_GATE_INPUT_V1',ledger=dict(path=config.coupling_ledger,sha256=sha256(config.coupling_ledger)),registry=config.registry.model_dump(),identity_authority=config.identity_authority.model_dump())
    pin=folder/'input.json';out=folder/'receipt.json';durable_json(pin,data)
    proc=subprocess.run([sys.executable,plan.diagnostic_evaluator.path,'--input',str(pin),'--input-sha256',sha256(pin),'--output',str(out)],stdin=subprocess.DEVNULL,capture_output=True,text=True)
    (folder/'evaluator.log').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
    if proc.returncode!=0 or not out.exists():raise Refused('FROZEN_NUMERICAL_ADVANCEMENT_HOLD')
    result=json.loads(out.read_text())
    if result.get('advance_to_development') is not True or result.get('inputs',{}).get('registry',{}).get('sha256')!=config.registry.sha256:raise Refused('FROZEN_NUMERICAL_GATE_NOT_PASS')
    return Pin(path=str(out),sha256=sha256(out))


def run_plan(plan,*,backend=None,validator_factory=None,gate_runner=diagnostic_gate):
    if time.time()>=plan.expires_unix:raise Refused('FINITE_PLAN_EXPIRED')
    verify_code(plan)
    config=V3Config.model_validate(plan.template_config.read())
    if config.mode=='PRODUCTION_GPU':
        if backend is not None or validator_factory is not None or gate_runner is not diagnostic_gate:raise Refused('PRODUCTION_PLAN_IMPLEMENTATION_OVERRIDE_FORBIDDEN')
        for pin in [config.engineering_acceptance,config.science_acceptance,config.sealed_identity_acceptance]:
            accepted=pin.read()
            if accepted.get('verdict')!='PASS' or accepted.get('registry_sha256')!=config.registry.sha256 or accepted.get('code_inventory_sha256')!=plan.code_inventory.sha256:raise Refused('INSTALLED_PLAN_ADMISSION_NOT_PASS')
    runroot=Path(config.v3_data_root)/'PRODUCTION_CUSTODIAN_PRIVATE'/'windows'/uuid.uuid4().hex
    runroot.mkdir(parents=True)
    outcome='PARTIAL'
    state_path=Path(config.v3_data_root)/'V3_AUDIT_METADATA/PRODUCTION_STATE.json'
    state_path.parent.mkdir(parents=True,exist_ok=True)
    status=dict(status='CONTROLLER_STARTED',dataset_id=config.dataset_id,code_inventory_sha256=plan.code_inventory.sha256,registry_sha256=config.registry.sha256,expires_unix=plan.expires_unix)
    owned=False
    try:
        with exclusive(Path(config.coupling_ledger).with_suffix('.v2_controller.lock')),exclusive(Path(config.runtime_root)/'.v2_controller.lock'):
            owned=True;replace_json(state_path,status)
            ledger=SerialLedger(Path(config.runtime_root)/'ledger.sqlite3')
            if ledger.audit()['slot']['token']:raise Refused('PERSISTED_OWNER_REVIEW_OR_LOAD_ONLY_REQUIRED')
            gate=None
            for kind in ['DIAGNOSTIC','DEVELOPMENT','SEALED_EVALUATION']:
                verify_code(plan)
                if time.time()>=plan.expires_unix:raise Refused('FINITE_PLAN_EXPIRED')
                rows=remaining_phase(config,kind)
                if kind=='DEVELOPMENT':gate=gate_runner(plan,config,runroot/'numerical_gate')
                if not rows:continue
                phase,requests=finite_phase(config,rows,runroot/kind,gate=gate)
                if phase.window.deadline_unix>plan.expires_unix:
                    raise Refused('WINDOW_EXCEEDS_FINITE_PLAN')
                impl=backend if backend is not None else ProductionNativeBackend()
                validator=validator_factory(phase) if validator_factory is not None else NativeTruthValidator(phase)
                status.update(status='RUNNING',phase=kind,config_sha256=phase.sha256,release_sha256=phase.release.sha256,release_expires_unix=phase.release.read()['expires_unix'],science_authorized=True)
                replace_json(state_path,status)
                for request in requests:rebind_proven_window(phase,request,ledger)
                controller_owned(phase,requests,impl,validator)
            final=json.loads(Path(config.coupling_ledger).read_text())
            if final['labels_valid_count']!=56 or final['entered_count']!=56:raise Refused('FINAL56_RECONCILIATION_INCOMPLETE')
            outcome='COMPLETE'
    except Refused as exc:
        outcome='WINDOW_STOP' if str(exc)=='WINDOW_INSUFFICIENT_NO_NEW_ENTRY' else 'HOLD'
        durable_json(runroot/'TERMINAL.json',dict(status=outcome,reason=str(exc),new_entry_retry_allowed=outcome=='WINDOW_STOP',automatic_replay=0))
        if outcome!='WINDOW_STOP':raise
    except BaseException as exc:
        outcome='HOLD'
        durable_json(runroot/'TERMINAL.json',dict(status='HOLD',reason=repr(exc),automatic_replay=0));raise
    finally:
        if owned:
            status['status']=outcome;replace_json(state_path,status)
        report=morning_report(config,SerialLedger(Path(config.runtime_root)/'ledger.sqlite3').audit())
        report['window_outcome']=outcome
        durable_json(runroot/'SAFE_SUMMARY.json',report)
    return outcome
