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
    cert=write(root/'science/profile.json',dict(profile_id='COUPLING_609D_V1',verdict='PASS',toolchain={}))
    platform=Platform(schema_version='APCD_GPU_V21_PLATFORM_V1',mode='PRODUCTION_EQUIVALENT',
        runtime_root=str(root),science_root=str(root/'science'),source_root=str(root/'data'),coupling_root=str(root/'coupling'),
        science_owner_sid='SCIENCE',consumer_sid='CONSUMER',operator_sids=['OPERATOR'],fdtd_executable=sys.executable,
        executable_sha256=sha256(sys.executable),gpu_resource='GPU license audit',native_h5_name='run_output.h5',
        heartbeat_seconds=0.01,profiles=[dict(profile_id='COUPLING_609D_V1',truth_toolchain={},certification=cert)])
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


def batch(platform,name,count=2,hold=False,entered=0,case_ids=None,simtime=6e-12):
    root=Path(platform.runtime_root);data=root/'data'/name;data.mkdir(parents=True)
    control=write(root/'science'/name/'control.json',dict(batch_id=name,hold=hold,admission_pass=True,manifest_sha='pending'))
    cases=[]
    for i,cid in enumerate(case_ids or [name+'_'+str(i) for i in range(count)]):
        fsp=data/(cid+'.fsp');fsp.write_bytes(b'SETUP_FIXTURE')
        pc=write(data/(cid+'_physics.json'),dict(simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6,monitors={'M':'M'}))
        source=write(data/(cid+'_source.json'),dict(case_id=cid,attempt_id='attempt_001'))
        source_acceptance=write(root/'science'/name/(cid+'_source_acceptance.json'),dict(verdict='PASS',fresh_load_verified=True,
            case_id=cid,attempt_id='attempt_001',ordered_D_nm=[120]*6,source_fsp_sha=sha256(fsp),physics_contract_sha=pc['sha256'],simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6))
        cases.append(dict(case_id=cid,attempt_id='attempt_001',role='DEVELOPMENT_GLOBAL',ordered_D_nm=[120]*6,
            source_fsp=dict(path=str(fsp),sha256=sha256(fsp)),source_manifest=source,source_acceptance=source_acceptance,physics_contract=pc,
            physics_contract_sha=pc['sha256'],simulation_time_s=simtime,mesh_nm=5.0,auto_shutoff_min=1e-6))
    ledger=data/'science_ledger.json'
    body=dict(schema_version='APCD_GPU_V21_BATCH_V1',batch_id=name,science_owner='SCIENCE',case_count=count,
        approved_entry_budget=count,solver_backend='LUMERICAL_2025R1_GPU',required_truth_artifacts=['FSP','SIBLING_H5','FRESH_LOAD'],
        label_validation_profile='COUPLING_609D_V1',approved_case_set=[c['case_id'] for c in cases],batch_science_hold=hold,
        science_control=control,science_ledger=str(ledger),cases=cases)
    body['manifest_sha']=digest(body);manifest=Pin(**write(root/'science'/name/'manifest.json',body))
    # mutable hold is owner controlled; immutable manifest only pins original identity.
    cp=Path(control['path']);write(cp,dict(batch_id=name,hold=hold,admission_pass=True,manifest_sha=body['manifest_sha']))
    admission=Pin(**write(root/'science'/name/'admission.json',dict(schema_version='APCD_GPU_V21_SCIENCE_ADMISSION_V1',
        batch_id=name,science_owner='SCIENCE',manifest_sha=body['manifest_sha'],manifest_file_sha=manifest.sha256,
        approved_case_set=body['approved_case_set'],approved_entry_budget=count,scientific_admission='PASS',engineering_admission='PASS',
        revoked=False,no_replay=True,label_validation_profile=body['label_validation_profile'],
        profile_certification_sha=platform.profiles[0].certification.sha256,science_ledger=str(ledger))))
    ids=body['approved_case_set'];old=ids[:entered]
    write(ledger,dict(batch_id=name,admission_sha256=admission.sha256,authorized_development_case_count=count,
        entered_case_ids=old,entered_count=entered,remaining_unentered_case_ids=ids[entered:],remaining_unentered_count=count-entered,
        truth_valid_case_ids=old,truth_valid_count=entered,labels_valid_case_ids=old,labels_valid_count=entered,
        case_records={cid:dict(phase='V2_TRUTH_VALID') for cid in old}))
    return manifest,admission,ledger


def validator(cfg):
    return lambda fsp,req,dest:dict(verdict='PASS',outputs=609,fresh_load_verified=True,actual_importer='load_verified_runner_case',test_double=True)


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
    data=json.loads(a[2].read_text());data['authorized_development_case_count']=3;write(a[2],data)
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
    bad=lambda target:dict(owner='SCIENCE',rules=[dict(sid='CONSUMER',rights=2,allow=True)])
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



