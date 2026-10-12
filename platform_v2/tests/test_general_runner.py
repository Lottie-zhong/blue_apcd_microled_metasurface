import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from apcd_gpu_v2.general import (Platform, Registry, Pin, digest, build_requests,
    Manifest, Admission, GeneralBudget, verify_acl, validate_general, load_batch)
from apcd_gpu_v2.serial import EquivalentBackend, exclusive
from apcd_gpu_v2.artifacts import sha256
from apcd_gpu_v2.ledger import Refused


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True),encoding='utf-8')
    return dict(path=str(path),sha256=sha256(path))


def setup(tmp_path):
    root=tmp_path/'zero_solver';root.mkdir()
    cert=write(root/'science/profile.json',dict(profile_id='coupling_609d_v1',verdict='PASS',toolchain={}))
    platform=Platform(schema_version='APCD_GPU_V21_PLATFORM_V1',mode='PRODUCTION_EQUIVALENT',
        runtime_root=str(root),science_root=str(root/'science'),source_root=str(root/'data'),coupling_root=str(root/'coupling'),
        science_owner_sid='SCIENCE',consumer_sid='CONSUMER',operator_sids=['OPERATOR'],fdtd_executable=sys.executable,
        executable_sha256=sha256(sys.executable),gpu_resource='GPU license audit',native_h5_name='run_output.h5',
        heartbeat_seconds=0.01,profiles=[dict(profile_id='coupling_609d_v1',truth_toolchain={},certification=cert)])
    script=root/'fake.py'
    script.write_text('''# APCD_ZERO_SOLVER_FIXTURE
import sys,time
import h5py,numpy as np
from pathlib import Path
p=Path(sys.argv[1]);time.sleep(0.02);p.write_bytes(b'OFFLINE_SOLVED_FIXTURE_NOT_NATIVE_FSP')
p.with_suffix('').mkdir()
with h5py.File(p.with_suffix('')/'run_output.h5','w') as f:
 for name in ['Ex','Ey','Ez','Hx','Hy','Hz']: f.create_dataset('Monitor1/'+name,data=np.ones((1,1,1,21),complex))
''',encoding='utf-8')
    return platform,Registry(platform),EquivalentBackend(script)


def batch(platform,name,count=2,hold=False,entered=0,case_ids=None,simtime=6e-12,physical_identity_sha=None,contract_payload=None,role="DEVELOPMENT_GLOBAL",geometries=None):
    root=Path(platform.runtime_root);data=root/'data'/name;data.mkdir(parents=True)
    control=write(root/'science'/name/'control.json',dict(batch_id=name,hold=hold,admission_pass=True,manifest_sha='pending'))
    cases=[]
    for i,cid in enumerate(case_ids or [name+'_'+str(i) for i in range(count)]):
        fsp=data/(cid+'.fsp');fsp.write_bytes(b'SETUP_FIXTURE')
        pc=write(data/(cid+'_physics.json'),dict(simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6,monitors={'M':'M'}))
        if contract_payload is not None:
            Path(pc['path']).write_text(json.dumps(contract_payload,sort_keys=True,separators=(',',':'),ensure_ascii=True),encoding='utf-8')
            pc['sha256']=sha256(pc['path'])
        geometry=(geometries or {}).get(cid,[120]*6)
        scientific_sha=physical_identity_sha or pc['sha256']
        source=write(data/(cid+'_source.json'),dict(case_id=cid,attempt_id='attempt_001'))
        source_acceptance=write(root/'science'/name/(cid+'_source_acceptance.json'),dict(verdict='PASS',fresh_load_verified=True,
            case_id=cid,attempt_id='attempt_001',ordered_D_nm=geometry,source_fsp_sha=sha256(fsp),physics_contract_sha=scientific_sha,simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6))
        source_acceptance=write(Path(source_acceptance['path']),{**json.loads(Path(source_acceptance['path']).read_text()),
            'role':role,'source_manifest_sha256':source['sha256'],'physics_contract_file_sha256':pc['sha256']})
        cases.append(dict(case_id=cid,attempt_id='attempt_001',role=role,ordered_D_nm=geometry,
            source_fsp=dict(path=str(fsp),sha256=sha256(fsp)),source_manifest=source,source_acceptance=source_acceptance,physics_contract=pc,
            physics_contract_sha=scientific_sha,simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6))
    for row in cases:
        projection={k:v for k,v in row.items() if k!='source_acceptance'}
        row['case_request_sha256']=digest(dict(schema='APCD_COUPLING_CASE_REQUEST_CANON_V1',case_request=projection,source_acceptance_path=row['source_acceptance']['path']))
        proof=json.loads(Path(row['source_acceptance']['path']).read_text())
        proof['case_request_sha256']=row['case_request_sha256']
        row['source_acceptance']=write(Path(row['source_acceptance']['path']),proof)
    ledger=data/'science_ledger.json'
    body=dict(case_request_canonicalization='APCD_COUPLING_CASE_REQUEST_CANON_V1',schema_version='APCD_GPU_V21_BATCH_V1',batch_id=name,science_owner=platform.science_owner_id,case_count=count,
        approved_entry_budget=count,solver_backend='LUMERICAL_2025R1_GPU',required_truth_artifacts=['FSP','SIBLING_H5','FRESH_LOAD'],
        label_validation_profile='coupling_609d_v1',approved_case_set=[c['case_id'] for c in cases],batch_science_hold=hold,
        science_control=control,science_ledger=str(ledger),cases=cases)
    body['manifest_sha']=digest(body);manifest=Pin(**write(root/'science'/name/'manifest.json',body))
    # mutable hold is owner controlled; immutable manifest only pins original identity.
    cp=Path(control['path']);write(cp,dict(batch_id=name,hold=hold,admission_pass=True,manifest_sha=body['manifest_sha']))
    admission=Pin(**write(root/'science'/name/'admission.json',dict(schema_version='APCD_GPU_V21_SCIENCE_ADMISSION_V1',
        batch_id=name,science_owner=platform.science_owner_id,manifest_sha=body['manifest_sha'],manifest_file_sha=manifest.sha256,
        approved_case_set=body['approved_case_set'],approved_entry_budget=count,scientific_admission='PASS',engineering_admission='PASS',
        revoked=False,no_replay=True,label_validation_profile=body['label_validation_profile'],
        profile_certification_sha=platform.profiles[0].certification.sha256,science_ledger=str(ledger))))
    ids=body['approved_case_set'];old=ids[:entered]
    write(ledger,dict(schema='APCD_COUPLING_BATCH_ENTRY_LEDGER_V1',no_replay=True,replay_count=0,batch_id=name,admission_sha256=admission.sha256,authorized_entry_budget=count,
        entered_case_ids=old,entered_count=entered,remaining_unentered_case_ids=ids[entered:],remaining_unentered_count=count-entered,
        truth_valid_case_ids=old,truth_valid_count=entered,labels_valid_case_ids=old,labels_valid_count=entered,
        case_records={cid:dict(phase='V2_TRUTH_VALID') for cid in old}))
    return manifest,admission,ledger


def validator(cfg):
    return lambda fsp,req,dest:dict(verdict='PASS',outputs=609,fresh_load_verified=True,actual_importer='load_authorized_runner_case',test_double=True)


def test_generic_profile_never_routes_diagnostics_by_legacy_dataset(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'NEW_TIME_BATCH')
    _,pairs=build_requests(p,*a[:2])
    req=pairs[0][1].model_copy(update={'role':'TIME_CONVERGENCE_DIAGNOSTIC_ONLY'})
    assert req.dataset_id=='NEW_TIME_BATCH'
    assert pairs[0][0].validation_profile=='coupling_609d_v1'


def test_profile_owner_interface_missing_and_return_binding_fail_closed(tmp_path):
    from types import SimpleNamespace
    from apcd_gpu_v2.general import import_profile_truth
    p,r,b=setup(tmp_path);a=batch(p,'UNSEEN_OWNER_BATCH');r.submit(*a[:2])
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    record=dict(case_id=req.case_id,attempt_id=req.attempt_id,role=req.role,
        ordered_D_nm=list(req.ordered_D_nm),physical_contract_sha256=req.physical_contract_sha256)
    with pytest.raises(Refused,match='INTERFACE_MISSING'):import_profile_truth(cfg,req,record,SimpleNamespace())
    obj=SimpleNamespace(case_id=req.case_id,attempt_id=req.attempt_id,role=req.role,ordered_D_nm=req.ordered_D_nm)
    importer=SimpleNamespace(load_authorized_runner_case=lambda *a,**k:obj,
        validate_authorized_labels=lambda *a,**k:dict(verdict='PASS',outputs=609))
    with pytest.raises(Refused,match='SCIENCE_OWNER_LABEL'):import_profile_truth(cfg,req,record,importer)
    importer.validate_authorized_labels=lambda *a,**k:dict(verdict='PASS',outputs=609,scientific_validated=True,
        profile_id='coupling_609d_v1',physical_contract_sha256=req.physical_contract_sha256,
        case_request_sha256=req.case_request_sha256,physics_contract_file_sha256=req.physical_contract.sha256,
        source_manifest_sha256=req.source_manifest.sha256,source_acceptance_file_sha256=req.source_acceptance.sha256,
        batch_id=cfg.batch_id,case_id=req.case_id,attempt_id=req.attempt_id,role=req.role,ordered_D_nm=list(req.ordered_D_nm),
        manifest_file_sha256=cfg.batch_manifest.sha256,admission_file_sha256=cfg.science_admission.sha256,
        certification_file_sha256=p.profiles[0].certification.sha256)
    assert import_profile_truth(cfg,req,record,importer)[0] is obj
    accepted=importer.validate_authorized_labels
    importer.validate_authorized_labels=lambda *args,**kwargs:{**accepted(*args,**kwargs),'admission_file_sha256':'0'*64}
    with pytest.raises(Refused,match='LABEL_BINDING_CONFLICT'):import_profile_truth(cfg,req,record,importer)
    importer.validate_authorized_labels=accepted
    obj.case_id='FOREIGN'
    with pytest.raises(Refused,match='IMPORTED_IDENTITY'):import_profile_truth(cfg,req,record,importer)
    assert json.loads(a[2].read_text())['entered_count']==0


def test_generic_budget_rejects_legacy_protocol_and_replay(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'INDEPENDENT_BUDGET');r.submit(*a[:2]);r.operate('INDEPENDENT_BUDGET',False)
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    d=json.loads(a[2].read_text());d['schema']='LEGACY_LEDGER';write(a[2],d)
    with pytest.raises(Refused,match='PROTOCOL'):GeneralBudget(cfg).validate(req)
    d['schema']='APCD_COUPLING_BATCH_ENTRY_LEDGER_V1';d['replay_count']=1;write(a[2],d)
    with pytest.raises(Refused,match='PROTOCOL'):GeneralBudget(cfg).validate(req)


def test_profile_admission_requires_science_owner_certified_case_before_entry(tmp_path):
    from types import SimpleNamespace
    from apcd_gpu_v2.general import validate_profile_admission
    p,r,b=setup(tmp_path);a=batch(p,'NEW_CERTIFIED_BATCH');r.submit(*a[:2])
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    with pytest.raises(Refused,match='PREENTRY_INTERFACE_MISSING'):
        validate_profile_admission(cfg,req,SimpleNamespace())
    service=SimpleNamespace(validate_profile_admission=lambda **k:dict(scientific_admission='PASS'))
    with pytest.raises(Refused,match='PREENTRY_NOT_ACCEPTED'):validate_profile_admission(cfg,req,service)
    seen=[]
    def admit(**kwargs):
        seen.append(kwargs)
        return dict(scientific_admission='PASS',profile_id=cfg.validation_profile,case_id=req.case_id,
            attempt_id=req.attempt_id,physical_contract_sha256=req.physical_contract_sha256,
            batch_id=cfg.batch_id,role=req.role,ordered_D_nm=list(req.ordered_D_nm),
            manifest_file_sha256=cfg.batch_manifest.sha256,admission_file_sha256=cfg.science_admission.sha256,
            certification_file_sha256=p.profiles[0].certification.sha256,authorized_entry_budget=2,no_replay=True)
    service.validate_profile_admission=admit
    assert validate_profile_admission(cfg,req,service)['scientific_admission']=='PASS'
    assert seen[0]['authority']['admission_file_sha']==a[1].sha256
    service.validate_profile_admission=lambda **kwargs:{**admit(**kwargs),'authorized_entry_budget':3}
    with pytest.raises(Refused,match='PREENTRY_BINDING_CONFLICT'):validate_profile_admission(cfg,req,service)
    assert json.loads(a[2].read_text())['entered_count']==0
    assert r.ledger.audit()['tasks']==[]


def test_nested_physics_contract_rejected_before_native_entry(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from apcd_gpu_v2.serial import NativeTruthValidator
    p,r,b=setup(tmp_path);a=batch(p,'NESTED_CONTRACT_BATCH');r.submit(*a[:2])
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    validator=NativeTruthValidator(cfg)
    monkeypatch.setattr(validator,'_dependencies',lambda:(SimpleNamespace(__version__='fixture'),SimpleNamespace(__version__='fixture'),None,None,None))
    monkeypatch.setattr('apcd_gpu_v2.general.validate_profile_admission',lambda *a,**k:{'scientific_admission':'PASS'})
    with pytest.raises(Refused,match='RESOLVED_POSTPROCESS_CONTRACT_REQUIRED'):validator.preflight(req)
    assert json.loads(a[2].read_text())['entered_count']==0
    assert not list(a[2].parent.glob('V21_ENTRY_EVIDENCE_*'))


def test_scientific_identity_and_raw_contract_pin_are_separately_bound(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'SEMANTIC_PIN_BATCH',physical_identity_sha='a'*64)
    assert r.submit(*a[:2])=='SUBMITTED_PAUSED'
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    assert req.physical_contract_sha256=='a'*64
    assert req.physical_contract.sha256!='a'*64
    proof=Manifest.model_validate_json(Path(a[0].path).read_text()).cases[0].source_acceptance
    doc=json.loads(Path(proof.path).read_text())
    assert doc['physics_contract_file_sha256']==req.physical_contract.sha256
    assert doc['physics_contract_sha']=='a'*64
    assert json.loads(a[2].read_text())['entered_count']==0


def test_consumer_cannot_bypass_operator_guard_by_calling_registry_api(monkeypatch,tmp_path):
    from types import SimpleNamespace
    p,r,b=setup(tmp_path);a=batch(p,'API_GUARD_BATCH');r.submit(*a[:2])
    r.platform=p.model_copy(update={'mode':'PRODUCTION_GPU'})
    monkeypatch.setattr('apcd_gpu_v2.general.subprocess.run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='CONSUMER'))
    for action in [lambda:r.submit(*a[:2]),lambda:r.operate('API_GUARD_BATCH',False),lambda:r.drain()]:
        with pytest.raises(Refused,match='OPERATOR_IDENTITY_NOT_AUTHORIZED'):action()
    assert json.loads(a[2].read_text())['entered_count']==0
    assert r.status()['batches'][0]['paused']==1


def test_two_batches_independent_hold_budget_and_third_data_only(tmp_path):
    p,r,b=setup(tmp_path)
    a=batch(p,'A',count=6,hold=True,entered=4);saved=a[2].read_bytes();r.submit(*a[:2])
    with pytest.raises(Refused,match='SCIENCE_HOLD'):r.operate('A',False)
    bb=batch(p,'B');assert r.submit(*bb[:2])=='SUBMITTED_PAUSED';r.operate('B',False)
    result=r.drain(backend=b,validator_factory=validator)
    assert len(result['execution']['tasks'])==2 and all(t['state']=='TRUTH_VALID' for t in result['execution']['tasks'])
    assert a[2].read_bytes()==saved
    assert json.loads(bb[2].read_text())['entered_count']==2
    r.drain(backend=b,validator_factory=validator);assert json.loads(bb[2].read_text())['entered_count']==2
    c=batch(p,'C',count=1,simtime=3e-12);r.submit(*c[:2]);r.operate('C',False)
    r.drain(backend=b,validator_factory=validator)
    assert json.loads(c[2].read_text())['truth_valid_count']==1 and a[2].read_bytes()==saved


def test_cross_batch_identity_duplicate_and_manifest_tamper(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);assert r.submit(*a[:2])=='ALREADY_SUBMITTED'
    c=batch(p,'C',case_ids=['A_0','C_1'])
    with pytest.raises(Refused,match='CROSS_BATCH'):r.submit(*c[:2])
    Path(a[0].path).write_text('{}')
    with pytest.raises(Refused,match='PIN_CHANGED'):r.operate('A',False)


def test_unregistered_case_profile_and_budget_tamper(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    with pytest.raises(Refused,match='UNREGISTERED'):validate_general(cfg,req.model_copy(update={'case_id':'FOREIGN'}))
    data=json.loads(a[2].read_text());data['authorized_entry_budget']=3;write(a[2],data)
    with pytest.raises(Refused):GeneralBudget(cfg).validate(req)
    with pytest.raises(Exception):p.model_copy(update={'profiles':[]}).model_validate({**p.model_dump(),'profiles':[{'profile_id':'ARBITRARY_SCRIPT'}]})


@pytest.mark.parametrize('point',['coupling_receipt_committed','coupling_ledger_committed','before_local_mirror','launch_requested','solver_returned','coupling_truth_before_local'])
def test_crash_holds_no_replay_next_or_refund(tmp_path,point):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    def fail(step):
        if step==point:raise RuntimeError('INJECTED')
    with pytest.raises(RuntimeError):r.drain(backend=b,validator_factory=validator,fault=fail)
    with pytest.raises(Refused):r.drain(backend=b,validator_factory=validator)
    data=json.loads(a[2].read_text());assert data['entered_count']<=1
    assert r.ledger.audit()['slot']['token'] and len(r.ledger.audit()['tasks'])==1


def test_pause_natural_completion_then_resume_across_ten_am(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    def pause(step):
        if step=='solver_returned':r.operate('A',True)
    r.drain(backend=b,validator_factory=validator,fault=pause)
    assert json.loads(a[2].read_text())['truth_valid_count']==1
    r.operate('A',False);r.drain(backend=b,validator_factory=validator)
    assert json.loads(a[2].read_text())['truth_valid_count']==2
    source=Path(__import__('apcd_gpu_v2.general',fromlist=['x']).__file__).read_text()
    assert 'deadline(' not in source and 'hour=10' not in source


def test_double_controller_and_sha_integrity(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    with exclusive(Path(p.runtime_root)/'.v2_controller.lock'):
        with pytest.raises(Refused,match='OWNER_LOCK'):r.drain(backend=b,validator_factory=validator)
    r.drain(backend=b,validator_factory=validator)
    bundle=json.loads(r.ledger.audit()['tasks'][0]['bundle'])['bundle']
    (Path(bundle['path'])/'run.fsp').write_bytes(b'CORRUPTED')
    with pytest.raises(Refused,match='INTEGRITY'):r.drain(backend=b,validator_factory=validator)


def test_negative_consumer_acl_and_permission_unknown(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');p=p.model_copy(update={'mode':'PRODUCTION_GPU'})
    good=lambda target:dict(owner='SCIENCE',rules=[dict(sid='SCIENCE',rights=2032127,allow=True),dict(sid='CONSUMER',rights=1179785,allow=True)])
    verify_acl(p,a[0].path,reader=good)
    verify_acl(p,a[2],authority_root=p.source_root,reader=good)
    bad=lambda target:dict(owner='SCIENCE',rules=[dict(sid='CONSUMER',rights=2,allow=True)])
    with pytest.raises(Refused,match='AUTHORITY_WRITE_ALLOWED'):
        verify_acl(p,a[2],authority_root=p.source_root,reader=bad)
    with pytest.raises(Refused,match='AUTHORITY_WRITE'):verify_acl(p,a[0].path,reader=bad)
    def unavailable(target):raise Refused('ACL_EVIDENCE_UNAVAILABLE')
    with pytest.raises(Refused,match='UNAVAILABLE'):verify_acl(p,a[0].path,reader=unavailable)


def test_science_hold_live_after_submit_never_resumed(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    m=Manifest.model_validate_json(Path(a[0].path).read_text());c=json.loads(Path(m.science_control.path).read_text());c['hold']=True
    write(Path(m.science_control.path),c);before=a[2].read_bytes()
    r.drain(backend=b,validator_factory=validator)
    assert a[2].read_bytes()==before and not r.ledger.audit()['tasks']
    with pytest.raises(Refused,match='HOLD'):r.operate('A',False)


def test_general_cli_status_submit_does_not_launch(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');pp=write(Path(p.runtime_root)/'platform.json',p.model_dump())
    tool=Path(__file__).resolve().parents[1]/'tools/general_runner.py'
    cmd=[sys.executable,str(tool),'--platform',pp['path'],'--platform-sha256',pp['sha256']]
    proc=subprocess.run(cmd+['submit','--manifest',a[0].path,'--manifest-sha256',a[0].sha256,'--admission',a[1].path,'--admission-sha256',a[1].sha256],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    status=subprocess.run(cmd+['status'],capture_output=True,text=True);assert status.returncode==0,status.stderr
    assert json.loads(status.stdout)['task_counts']=={}


def test_solver_returned_zero_solver_recovery_then_next(monkeypatch,tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    def fail(step):
        if step=='solver_returned':raise RuntimeError('WORKER_EXIT')
    with pytest.raises(RuntimeError):r.drain(backend=b,validator_factory=validator,fault=fail)
    # Model the persisted worker's confirmed exit. The launcher process actually exited.
    monkeypatch.setattr('apcd_gpu_v2.serial.identity_state',lambda record:'dead')
    r.drain(backend=b,validator_factory=validator)
    data=json.loads(a[2].read_text());assert data['entered_count']==data['truth_valid_count']==2
    assert len([e for e in r.ledger.audit()['events'] if e['kind']=='LAUNCHER_PROCESS'])==2


def test_scientific_source_acceptance_missing_fail_closed(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A')
    m=Manifest.model_validate_json(Path(a[0].path).read_text())
    Path(m.cases[0].source_acceptance.path).write_text('{}')
    with pytest.raises(Refused,match='PIN_CHANGED'):r.submit(*a[:2])


def test_candidate_rejects_residual_doe_plan_cli(tmp_path):
    tool=Path(__file__).resolve().parents[1]/'tools/serial_controller.py'
    proc=subprocess.run([sys.executable,str(tool),'--plan','NEVER_EXECUTE.json','--plan-sha256','0'*64],capture_output=True,text=True)
    assert proc.returncode!=0 and ('--platform' in proc.stderr or 'RETIRED' in proc.stderr)


def test_status_does_not_expose_sealed_response_or_owner_tokens(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2])
    public=json.dumps(r.public_status());assert 'owner_token' not in public and 'bundle' not in public and 'source_fsp' not in public


def test_windows_namespace_case_alias_and_reserved_name_rejected(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2])
    c=batch(p,'C',case_ids=['a_0','C_1'])
    with pytest.raises(Refused,match='CROSS_BATCH'):r.submit(*c[:2])
    doc=json.loads(Path(a[0].path).read_text());doc['batch_id']='CON'
    doc['manifest_sha']=digest({k:v for k,v in doc.items() if k!='manifest_sha'})
    pin=Pin(**write(Path(p.science_root)/'reserved_namespace.json',doc))
    with pytest.raises(Exception,match='WINDOWS_RESERVED'):r.submit(pin,a[1])


@pytest.mark.parametrize('hour,minute',[(9,59),(10,1)])
def test_real_control_flow_has_no_ten_am_boundary(monkeypatch,tmp_path,hour,minute):
    from datetime import datetime,timezone,timedelta
    clock=datetime(2026,10,13,hour,minute,tzinfo=timezone(timedelta(hours=8))).timestamp()
    monkeypatch.setattr('apcd_gpu_v2.general.time.time',lambda:clock)
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2]);r.operate('A',False)
    r.drain(backend=b,validator_factory=validator)
    assert json.loads(a[2].read_text())['truth_valid_count']==2


def test_restored_local_state_cannot_skip_uncertain_other_batch(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');c=batch(p,'C');r.submit(*a[:2]);r.submit(*c[:2]);r.operate('A',False);r.operate('C',False)
    def crash(step):
        if step=='coupling_receipt_committed':raise RuntimeError('CRASH')
    with pytest.raises(RuntimeError):r.drain(backend=b,validator_factory=validator,fault=crash)
    # Simulate restoring an older execution snapshot in this isolated fixture only.
    with r.ledger.transaction() as db:
        db.execute('DELETE FROM tasks');db.execute('UPDATE slot SET token=NULL,owner=NULL,request_sha=NULL')
    with pytest.raises(Refused,match='CROSS_BATCH_UNCERTAIN'):r.drain(backend=b,validator_factory=validator)
    assert json.loads(c[2].read_text())['entered_count']==0


def test_registry_snapshot_loss_retains_nonreplay_evidence(tmp_path):
    p,r,b=setup(tmp_path);a=batch(p,'A');r.submit(*a[:2])
    with r.ledger.transaction() as db:db.execute('DELETE FROM v21_batches')
    with pytest.raises(Refused,match='REGISTRY_LOST'):r.drain(backend=b,validator_factory=validator)





def test_science_request_and_native_truth_bindings_are_distinct(tmp_path):
    from apcd_gpu_v2.general import profile_native_bindings
    import h5py
    p,r,b=setup(tmp_path);a=batch(p,'UNSEEN_NATIVE_BINDING_BATCH')
    _,pairs=build_requests(p,*a[:2]);cfg,req=pairs[0]
    fsp=Path(p.runtime_root)/'saved.fsp';fsp.write_bytes(b'TEST_FIXTURE_ONLY_NOT_NATIVE')
    fsp.with_suffix('').mkdir()
    with h5py.File(fsp.with_suffix('')/'run_output.h5','w') as h:
        import numpy as np
        for component in ['Ex','Ey','Ez','Hx','Hy','Hz']:h['Monitor1/'+component]=np.ones((1,1,1,21),complex)
    record=profile_native_bindings(cfg,req,fsp)
    assert record['request_sha256']==req.case_request_sha256
    assert record['execution_request_sha256']==req.request_sha256
    assert req.case_request_sha256!=req.request_sha256
    assert record['native_fsp']['sha256']==sha256(fsp)
    assert record['native_h5']['sha256']==sha256(fsp.with_suffix('')/'run_output.h5')
    assert record['physical_contract_file_sha256']==req.physical_contract.sha256
    assert record['source_acceptance_file_sha256']==req.source_acceptance.sha256
    (fsp.with_suffix('')/'run_output.h5').unlink()
    with pytest.raises(Exception):profile_native_bindings(cfg,req,fsp)


@pytest.mark.parametrize('batch_name,count', [('DIAG2_GENERIC_OFFLINE_B',2),('UNPREPARED_COUPLING_GENERIC_C',1)])
def test_science_owner_generic_profile_through_gpu_adapter(tmp_path,monkeypatch,batch_name,count):
    """Real profile authority/receipt checks, synthetic numeric kernel, zero solver."""
    from dataclasses import replace
    from apcd_gpu_v2.general import Profile, profile_native_bindings, import_profile_truth, validate_profile_admission
    import numpy as np
    import h5py
    coupling=Path(os.environ['APCD_TEST_COUPLING_ROOT'])
    sys.path.insert(0,str(coupling/'scripts/coupling_ml'))
    from k6_v2_pipeline import generic_profile as G
    from k6_v2_pipeline import ingest as I
    p,registry,backend=setup(tmp_path)
    packet=coupling/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1'
    cert=json.loads((packet/'fixtures/B_DIAG2_TEST_FIXTURE/SCIENCE_OWNER_PROFILE_CERTIFICATION_TEST_FIXTURE_ONLY.json').read_text())
    cert['toolchain']={'importer':sha256(G.__file__)}
    assert p.science_owner_id==G.SCIENCE_OWNER_ID
    assert p.science_owner_sid!=p.science_owner_id
    a=batch(p,batch_name,count=count)
    manifest=json.loads(Path(a[0].path).read_text())
    pc_sha=manifest['cases'][0]['physics_contract_sha']
    cert['allowed_contracts']=[dict(sha256=pc_sha,allowed_roles=['DEVELOPMENT_GLOBAL'],simulation_time_s=6e-12,mesh_nm=5.0,auto_shutoff_min=1e-6)]
    pin=Pin(**write(Path(p.runtime_root)/'science/real_profile_cert.json',cert))
    p=p.model_copy(update={'profiles':[Profile(profile_id='coupling_609d_v1',certification=pin,truth_toolchain={'importer':Pin(path=str(Path(G.__file__)),sha256=sha256(G.__file__))})]})
    admission=json.loads(Path(a[1].path).read_text());admission['profile_certification_sha']=pin.sha256
    admission_pin=Pin(**write(Path(a[1].path),admission))
    ledger=json.loads(a[2].read_text());ledger['admission_sha256']=admission_pin.sha256;write(a[2],ledger)
    _,pairs=build_requests(p,a[0],admission_pin)
    numeric=I.load_old32_engineering_diagnostic(root=coupling).cases[0]
    calls=[]
    def kernel(record,role_map,expected_roles,**kwargs):
        calls.append(record['case_id'])
        return replace(numeric,case_id=record['case_id'],attempt_id=record['attempt_id'],role=record['role'],ordered_D_nm=tuple(record['ordered_D_nm']),provenance={**numeric.provenance,'physical_contract_sha256':record['physical_contract_sha256'],'test_fixture_only':True})
    monkeypatch.setattr(G,'_load_authorized_runner_truth',kernel)
    for cfg,req in pairs:
        assert validate_profile_admission(cfg,req,G)['scientific_admission']=='PASS'
        fsp=Path(p.runtime_root)/(req.case_id+'.fsp');fsp.write_bytes(b'TEST_FIXTURE_ONLY_NOT_NATIVE_FSP')
        fsp.with_suffix('').mkdir()
        with h5py.File(fsp.with_suffix('')/cfg.native_h5_name,'w') as h:
            for component in ['Ex','Ey','Ez','Hx','Hy','Hz']:h['Monitor1/'+component]=np.ones((1,1,1,21),complex)
        bindings=profile_native_bindings(cfg,req,fsp)
        run_manifest=dict(case_id=req.case_id,attempt_id=req.attempt_id,pre_fsp_sha256=req.pre_fsp_sha256,
            source_manifest_path=req.source_manifest.path,source_manifest_sha256=req.source_manifest.sha256,
            batch_id=req.batch_id,profile_id=cfg.validation_profile,admission_sha256=cfg.science_admission.sha256,
            request_sha256=bindings['request_sha256'],source_acceptance_file_sha256=bindings['source_acceptance_file_sha256'],
            native_fsp_sha256=bindings['native_fsp']['sha256'],native_h5_sha256=bindings['native_h5']['sha256'])
        record=dict(case_id=req.case_id,attempt_id=req.attempt_id,role=req.role,ordered_D_nm=list(req.ordered_D_nm),
            physical_contract_sha256=req.physical_contract_sha256,source_manifest=write(Path(p.runtime_root)/(req.case_id+'_run_manifest.json'),run_manifest),**bindings)
        imported,receipt=import_profile_truth(cfg,req,record,G)
        assert receipt['outputs']==609 and receipt['scientific_validated'] is True
        assert receipt['case_request_sha256']==req.case_request_sha256
        with pytest.raises(ValueError,match='runner_request_sha'):
            import_profile_truth(cfg,req,{**record,'request_sha256':req.request_sha256},G)
    assert len(calls)==count
    assert json.loads(a[2].read_text())['entered_count']==0


def test_offline_science_owner_authority_cannot_be_used_for_production(tmp_path):
    from apcd_gpu_v2.general import require_formal_authority
    p,registry,backend=setup(tmp_path)
    for marker in ['test_fixture_only','fixture_only','audit_only']:
        require_formal_authority(p,{marker:True})
        with pytest.raises(Refused,match='OFFLINE_AUTHORITY'):
            require_formal_authority(p.model_copy(update={'mode':'PRODUCTION_GPU'}),{marker:True})
    require_formal_authority(p.model_copy(update={'mode':'PRODUCTION_GPU'}),{})


@pytest.mark.parametrize('batch_name,ids,role',[
    ('SIGNED_DIAG2_RESOLVER_B',['K6V3_TIME_DIAG2_A1_5NM_6PS','K6V3_TIME_DIAG2_A2_5NM_6PS'],'TIME_CONVERGENCE_DIAGNOSTIC_ONLY'),
    ('NEW_RESOLVER_COUPLING_C',['NEVER_PREWIRED_COUPLING_C001'],'DEVELOPMENT_GLOBAL')])
def test_owner_resolver_through_gpu_contract_consumer(tmp_path,monkeypatch,batch_name,ids,role):
    from apcd_gpu_v2.general import Profile, profile_postprocess_contract
    coupling=Path(os.environ['APCD_TEST_COUPLING_ROOT'])
    sys.path.insert(0,str(coupling/'scripts/coupling_ml'))
    from k6_v2_pipeline import generic_profile as G, ingest as I, postprocess_contract_resolver as R
    p,registry,backend=setup(tmp_path)
    packet=coupling/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1'
    contract=json.loads((packet/'SCIENCE_CONTRACT_6PS.json').read_text())
    geometries={'K6V3_TIME_DIAG2_A1_5NM_6PS':[120,160,165,175,160,195],
        'K6V3_TIME_DIAG2_A2_5NM_6PS':[210,115,175,115,180,125]}
    a=batch(p,batch_name,count=len(ids),case_ids=ids,contract_payload=contract,role=role,geometries=geometries)
    manifest=json.loads(Path(a[0].path).read_text());pc_sha=manifest['cases'][0]['physics_contract_sha']
    assert pc_sha=='51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36'
    cert=json.loads((packet/'fixtures/B_DIAG2_TEST_FIXTURE/SCIENCE_OWNER_PROFILE_CERTIFICATION_TEST_FIXTURE_ONLY.json').read_text())
    toolchain={'importer':Pin(path=str(Path(G.__file__)),sha256=sha256(G.__file__)),
        'postprocess_contract_resolver':Pin(path=str(Path(R.__file__)),sha256=sha256(R.__file__))}
    cert['toolchain']={k:v.sha256 for k,v in toolchain.items()}
    cert['allowed_contracts']=[dict(sha256=pc_sha,allowed_roles=[role],simulation_time_s=6e-12,mesh_nm=5.0,auto_shutoff_min=1e-6)]
    cert_pin=Pin(**write(Path(p.runtime_root)/'science/certified_profile.json',cert))
    resolver_cert=dict(schema='APCD_COUPLING_POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1',verdict='PASS',
        science_owner=G.SCIENCE_OWNER_ID,profile_id=G.PROFILE_ID,resolver_schema=R.RESOLVER_SCHEMA,
        resolved_contract_schema=R.RESOLVED_CONTRACT_SCHEMA,resolver_module='k6_v2_pipeline.postprocess_contract_resolver',
        resolver_entrypoint='resolve_postprocess_contract',fields=list(R.FIELDS),
        projection_digest_rule='ingest._canon({schema:resolved_contract_schema,resolved_contract:exact_six_fields})',
        resolver_module_sha256=sha256(R.__file__),generic_profile_sha256=sha256(G.__file__),canonicalizer_module_sha256=sha256(I.__file__),
        source_contract_schema=contract['schema'],source_contract_sha256=pc_sha,
        source_contract_section='parent_physical_contract_fields',test_fixture_only=True)
    resolver_path=Path(p.runtime_root)/'science/resolver_cert_TEST_FIXTURE_ONLY.json'
    resolver_path.write_text(json.dumps(resolver_cert,sort_keys=True,separators=(',',':'),ensure_ascii=True),encoding='utf-8')
    resolver_pin=Pin(path=str(resolver_path),sha256=sha256(resolver_path))
    p=p.model_copy(update={'profiles':[Profile(profile_id=G.PROFILE_ID,certification=cert_pin,
        postprocess_resolver_certification=resolver_pin,truth_toolchain=toolchain)]})
    admission=json.loads(Path(a[1].path).read_text());admission['profile_certification_sha']=cert_pin.sha256
    admission_pin=Pin(**write(Path(a[1].path),admission))
    ledger=json.loads(a[2].read_text());ledger['admission_sha256']=admission_pin.sha256;write(a[2],ledger)
    _,pairs=build_requests(p,a[0],admission_pin)
    for cfg,req in pairs:
        result=profile_postprocess_contract(cfg,req)
        assert result['entry_authorization'] is False and result['solver_entry_count']==0
        assert result['resolved_contract']=={k:contract['parent_physical_contract_fields'][k] for k in R.FIELDS}
        assert result['case_request_sha256']==req.case_request_sha256
        from types import SimpleNamespace
        with monkeypatch.context() as faults:
            faults.setattr('apcd_gpu_v2.native_readonly.pinned_module',lambda *args:SimpleNamespace(resolve_postprocess_contract=lambda **kwargs:{**result,'resolved_contract_sha256':'0'*64}))
            with pytest.raises(Refused,match='PROJECTION_SHA_CONFLICT'):profile_postprocess_contract(cfg,req)
    assert json.loads(a[2].read_text())['entered_count']==0
