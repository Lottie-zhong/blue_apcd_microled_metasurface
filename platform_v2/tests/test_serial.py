import json
import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from apcd_gpu_v2.artifacts import sha256, archive_pair
from apcd_gpu_v2.config import CONTRACT_SHA
from apcd_gpu_v2.ledger import Refused
from apcd_gpu_v2.native import NativeBackend
from apcd_gpu_v2.serial import (SerialConfig,SerialRequest,SerialLedger,CouplingBudget,Pin,
    EquivalentBackend,ProductionNativeBackend,controller,run_serial_case,exclusive,validate_admission,validate_truth)


CONTRACT=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1\acceptance_config.json')


def fixture(tmp_path,count=1,script_body=None):
    root=tmp_path/'zero_solver';root.mkdir()
    if not CONTRACT.exists():pytest.skip('frozen remote contract required')
    pc=json.loads(CONTRACT.read_text(encoding='utf-8'))['physical_contract_path']
    contract=root/'contract.json';shutil.copyfile(pc,contract);assert sha256(contract)==CONTRACT_SHA
    pre=root/'pre.fsp';pre.write_bytes(b'APCD_ZERO_SOLVER_FIXTURE_PRE')
    queue=root/'queue.json';release=root/'release.json';budget=root/'coupling.json'
    cases=[dict(case_id=f'K6GDP2_DEV_G{i:03d}',attempt_id='attempt_001',role='DEVELOPMENT_GLOBAL',ordered_D_nm=[105,105,220,105,180,135]) for i in range(27,27+count)]
    queue.write_text(json.dumps(dict(ordered_cases=cases)),encoding='utf-8')
    reqs=[]
    for case in cases:
        manifest=root/(case['case_id']+'.json');manifest.write_text(json.dumps(dict(case_id=case['case_id'],attempt_id='attempt_001',artifacts={'staged_fsp':{'path':'pre.fsp','sha256':sha256(pre)}})),encoding='utf-8')
        reqs.append(SerialRequest(**{**case,'ordered_D_nm':tuple(case['ordered_D_nm'])},pre_fsp=str(pre),pre_fsp_sha256=sha256(pre),source_manifest=Pin(path=str(manifest),sha256=sha256(manifest)),physical_contract=Pin(path=str(contract),sha256=sha256(contract)),physical_contract_sha256=CONTRACT_SHA,config_sha256='pending'))
    release.write_text(json.dumps(dict(schema='APCD_V2_SERIAL_RELEASE_V1',mode='PRODUCTION_EQUIVALENT',queue_sha256=sha256(queue),expires_unix=time.time()+3600,requests=[r.admission_sha256 for r in reqs],science_authorized=False)),encoding='utf-8')
    cfg=SerialConfig(schema_version='APCD_V2_SERIAL_V1',mode='PRODUCTION_EQUIVALENT',runtime_root=str(root),coupling_ledger=str(budget),queue=Pin(path=str(queue),sha256=sha256(queue)),release=Pin(path=str(release),sha256=sha256(release)),fdtd_executable=sys.executable,executable_sha256=sha256(sys.executable),gpu_resource='GPU license audit',native_h5_name='run_output.h5',physical_contract_sha256=CONTRACT_SHA,heartbeat_seconds=0.05)
    reqs=[r.model_copy(update={'config_sha256':cfg.sha256}) for r in reqs]
    budget.write_text(json.dumps(dict(authorized_development_case_count=count,entered_case_ids=[],entered_count=0,remaining_unentered_case_ids=[c['case_id'] for c in cases],remaining_unentered_count=count,truth_valid_case_ids=[],truth_valid_count=0,labels_valid_case_ids=[],labels_valid_count=0,case_records={})),encoding='utf-8')
    script=root/'fake_solver.py';script.write_text('# APCD_ZERO_SOLVER_FIXTURE\n'+(script_body or '''import sys,time
from pathlib import Path
import numpy as np,h5py
p=Path(sys.argv[1]);time.sleep(0.2);p.write_bytes(b"OFFLINE_SOLVED_FIXTURE_NOT_NATIVE_FSP")
p.with_suffix("").mkdir()
with h5py.File(p.with_suffix("")/"run_output.h5","w") as h:
 for c in ['Ex','Ey','Ez','Hx','Hy','Hz']:h.create_dataset('Monitor1/'+c,data=np.ones((2,2,1,21),complex))
print("ZERO_SCIENTIFIC_SOLVER")
'''),encoding='utf-8')
    return cfg,reqs,EquivalentBackend(script)


def validator(fsp,request,dest):
    return dict(verdict='PASS',outputs=609,fresh_load_verified=True,actual_importer='load_verified_runner_case',test_double=True)


def test_serial_ten_case_truth_before_next_and_restart(tmp_path):
    cfg,requests,backend=fixture(tmp_path,10)
    result=controller(cfg,requests,backend,validator)
    assert all(t['state']=='TRUTH_VALID' and t['entered']==1 for t in result['tasks'])
    assert result['slot']['token'] is None
    events=[e['kind'] for e in result['events']]
    assert events.count('LAUNCHER_PROCESS')==10 and events.count('HEARTBEAT')>=10
    assert events.count('TRUTH_VALID')==10
    assert len(controller(cfg,requests,backend,validator)['events'])==len(result['events'])
    external=json.loads(Path(cfg.coupling_ledger).read_text());assert external['entered_count']==external['truth_valid_count']==10


@pytest.mark.parametrize('point',['coupling_receipt_committed','coupling_ledger_committed','before_local_mirror','after_local_mirror','launch_requested','process_started','solver_returned','truth_valid_before_coupling','coupling_truth_before_local'])
def test_cross_ledger_crash_no_replay_no_refund(tmp_path,point):
    cfg,rs,backend=fixture(tmp_path,2)
    def fault(step):
        if step==point:raise RuntimeError('INJECT:'+step)
    with pytest.raises(RuntimeError,match='INJECT'):controller(cfg,rs,backend,validator,fault=fault)
    ledger=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3');assert ledger.audit()['slot']['token']
    assert ledger.audit()['tasks'][0]['state']=='HOLD_NO_REPLAY'
    evidence=CouplingBudget(cfg).reconcile(rs[0]);assert evidence['receipt'] and not evidence['replay_allowed']
    with pytest.raises(Refused):controller(cfg,rs,backend,validator)
    with pytest.raises(Refused,match='NO_REPLAY'):CouplingBudget(cfg).validate(rs[0])
    assert not (Path(cfg.runtime_root)/'attempts'/rs[1].request_sha256).exists()
    # A lost local SQLite file cannot allow replay through the authoritative Coupling evidence.
    alternate=SerialLedger(Path(cfg.runtime_root)/'alternate.sqlite3');alternate.register(rs[0],cfg)
    with pytest.raises(Refused,match='NO_REPLAY'):run_serial_case(cfg,rs[0],alternate,backend,validator)
    # Let an injected lost-receipt fixture process finish naturally; never kill.
    time.sleep(0.7)


@pytest.mark.parametrize('body',['import sys;sys.exit(9)','import sys;print("GPU_LICENSE_DENIED");sys.exit(7)','print("returned_without_truth")'])
def test_launcher_error_license_and_incomplete_truth_hold(tmp_path,body):
    cfg,rs,backend=fixture(tmp_path,2,body)
    with pytest.raises(Refused):controller(cfg,rs,backend,validator)
    assert json.loads(Path(cfg.coupling_ledger).read_text())['entered_count']==1
    assert SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['slot']['token']


def test_actual_popen_failure_is_conservative(tmp_path,monkeypatch):
    cfg,rs,backend=fixture(tmp_path)
    def fail(*args,**kw):raise OSError('Popen launch failure')
    monkeypatch.setattr('apcd_gpu_v2.serial.subprocess.Popen',fail)
    with pytest.raises(OSError):controller(cfg,rs,backend,validator)
    assert CouplingBudget(cfg).reconcile(rs[0])['entered_in_ledger']


def test_importer_failure_stops_autofill_and_retains_truth(tmp_path):
    cfg,rs,backend=fixture(tmp_path,2)
    def fail(*args):raise ValueError('importer failed')
    with pytest.raises(ValueError):controller(cfg,rs,backend,fail)
    assert (Path(cfg.runtime_root)/'archives'/rs[0].request_sha256/'run.fsp').exists()
    assert json.loads(Path(cfg.coupling_ledger).read_text())['truth_valid_count']==0


def test_save_interruption_then_load_only_recovery_does_not_rerun(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    ledger=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3');ledger.register(rs[0],cfg)
    calls=[]
    def partial(fsp,destination,name):
        def copy(a,b):calls.append(str(a));shutil.copy2(a,b);raise OSError('save interrupted')
        return archive_pair(fsp,destination,name,copy=copy)
    with pytest.raises(OSError):run_serial_case(cfg,rs[0],ledger,backend,validator,archive=partial)
    events=ledger.audit()['events'];launches=sum(e['kind']=='LAUNCH_REQUESTED' for e in events)
    evidence=validate_truth(cfg,rs[0],Path(cfg.runtime_root)/'attempts'/rs[0].request_sha256/'run.fsp',validator)
    assert evidence['validation']['outputs']==609
    assert sum(e['kind']=='LAUNCH_REQUESTED' for e in ledger.audit()['events'])==launches==1
    assert list((Path(cfg.runtime_root)/'archives').glob('*.partial.*'))


def test_two_controllers_os_lock_and_two_workers(tmp_path):
    cfg,rs,backend=fixture(tmp_path,2)
    with exclusive(Path(cfg.coupling_ledger).with_suffix('.v2_controller.lock')):
        with pytest.raises(Refused,match='LOCK'):controller(cfg,rs,backend,validator)
    l=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3')
    for r in rs:l.register(r,cfg)
    token=l.claim(rs[0].request_sha256,{'pid':123,'creation_time':1,'executable':'fixture'})
    with pytest.raises(Refused,match='OTHER_OWNER'):l.claim(rs[1].request_sha256,{})
    with pytest.raises(Refused,match='FENCING'):l.note(rs[0],'stale','BAD',{})
    assert l.reconcile_dead_owner(token,lambda owner:'reused')=='FAILED_PREENTRY'


def test_entered_pid_reuse_never_releases(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    l=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3');l.register(rs[0],cfg)
    token=l.claim(rs[0].request_sha256,dict(pid=1,creation_time=2,executable='fixture'))
    receipt=CouplingBudget(cfg).prepare_entry(rs[0],token);l.mirror(rs[0],token,receipt)
    assert l.reconcile_dead_owner(token,lambda owner:'reused')=='NEEDS_REVIEW_NO_REPLAY'
    assert l.audit()['slot']['token']==token


def test_release_tamper_and_preflight_denial_before_entry(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    Path(cfg.release.path).write_text('{}')
    with pytest.raises(Refused,match='PIN_CHANGED'):controller(cfg,rs,backend,validator)
    assert not CouplingBudget(cfg).receipt_path(rs[0]).exists()


def test_cross_ledger_reconciliation_repairs_count_but_never_launches(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    def crash(step):
        if step=='coupling_receipt_committed':raise RuntimeError('receipt only')
    with pytest.raises(RuntimeError):controller(cfg,rs,backend,validator,fault=crash)
    budget=CouplingBudget(cfg)
    assert not budget.reconcile(rs[0])['entered_in_ledger']
    assert budget.reconcile_entry_evidence(rs[0])==dict(entered=True,replay_allowed=False,repaired=True)
    assert budget.reconcile_entry_evidence(rs[0])['repaired'] is False
    assert not any(e['kind']=='LAUNCH_REQUESTED' for e in SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3').audit()['events'])
    with pytest.raises(Refused):controller(cfg,rs,backend,validator)


def test_restored_local_database_cannot_repeat_coupling_launch(tmp_path):
    cfg,rs,_=fixture(tmp_path)
    l=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3');l.register(rs[0],cfg)
    token=l.claim(rs[0].request_sha256,dict(pid=1,creation_time=2,executable='fixture'))
    budget=CouplingBudget(cfg);receipt=budget.prepare_entry(rs[0],token);l.mirror(rs[0],token,receipt)
    l.launch_once(rs[0],token,budget)
    with l.transaction() as db:
        db.execute("UPDATE tasks SET state='ENTRY_UNCERTAIN'")  # fixture simulates restoring an older SQLite snapshot
    with pytest.raises(Refused,match='COUPLING_LAUNCH_ALREADY_REQUESTED'):l.launch_once(rs[0],token,budget)
    assert budget.reconcile(rs[0])['entered_in_ledger']


def test_wddm_display_is_not_science_and_unattributed_is_not_cleared(monkeypatch):
    from apcd_gpu_v2 import serial
    def id(pid):return dict(pid=pid,creation_time=12,executable=r'C:\Windows\dwm.exe' if pid==1 else r'N:\ansysedt.exe')
    monkeypatch.setattr(serial,'identity',id)
    rows=serial.classify_gpu_consumers('1, C:\\Windows\\dwm.exe, [N/A]\n2, N:\\ansysedt.exe, [N/A]')
    assert rows[0]['classification']=='DISPLAY_ACTIVITY' and rows[1]['classification']=='SCIENCE_OR_UNATTRIBUTED'


def test_coupling_labels_atomic_publication_interruption_recovers_without_reentry(tmp_path,monkeypatch):
    import numpy as np
    from apcd_gpu_v2 import serial
    cfg,rs,_=fixture(tmp_path)
    config=cfg.model_copy(update={'mode':'PRODUCTION_GPU'})
    request=rs[0].model_copy(update={'config_sha256':config.sha256})
    budget=CouplingBudget(config);budget.prepare_entry(request,'fixture-owner')
    labels=Path(cfg.runtime_root)/'verified_labels.npz'
    np.savez_compressed(labels,C_hat_real=np.ones((21,7,2)),C_hat_imag=np.zeros((21,7,2)),P_scale=np.ones(21))
    evidence=dict(bundle={'fixture':True},validation=dict(labels_artifact=dict(path=str(labels),sha256=sha256(labels)),record={'fixture_only':True}))
    link=serial.os.link;calls=[]
    def interrupted(src,dst):
        calls.append(str(dst))
        if len(calls)==2:raise OSError('ingest receipt publish interrupted')
        return link(src,dst)
    monkeypatch.setattr(serial.os,'link',interrupted)
    with pytest.raises(OSError):budget.finish_truth(request,evidence)
    target=Path(cfg.coupling_ledger).parent/('INGESTED_TRUTH_'+request.case_id+'_V1.npz')
    before=sha256(target)
    assert json.loads(Path(cfg.coupling_ledger).read_text())['truth_valid_count']==0
    monkeypatch.setattr(serial.os,'link',link)
    budget.finish_truth(request,evidence)
    assert sha256(target)==before
    assert json.loads(Path(cfg.coupling_ledger).read_text())['truth_valid_count']==1
    assert budget.reconcile(request)['entered_in_ledger']


def test_science_path_cannot_use_fake_and_original_refusal_survives(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    with pytest.raises(Refused,match='PRODUCTION_MODE'):ProductionNativeBackend().execute(cfg,rs[0],None,None,None,Path('run.fsp'))
    with pytest.raises(Refused,match='AUTHORIZATION'):NativeBackend().run()


def test_invalid_parallel_config_and_ledger_mismatch(tmp_path):
    cfg,rs,backend=fixture(tmp_path)
    with pytest.raises(ValueError):SerialConfig(**{**cfg.model_dump(),'slots':2})
    data=json.loads(Path(cfg.coupling_ledger).read_text());data['entered_count']=1;Path(cfg.coupling_ledger).write_text(json.dumps(data))
    with pytest.raises(Refused,match='COUNT_CONFLICT'):CouplingBudget(cfg).validate(rs[0])


def test_real_coupling_importer_reuses_g025_evidence_no_api():
    cfg=json.loads(CONTRACT.read_text(encoding='utf-8'))
    sys.path.insert(0,str(Path(cfg['coupling_root'])/'scripts/coupling_ml'))
    from k6_v2_pipeline import ingest
    receipt=json.loads(Path('D:/project/worktrees/blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2/reports/native_acceptance_v1/g025_actual_importer.json').read_text(encoding='utf-8'))
    assert sha256(ingest.__file__)==receipt['importer_source_sha256']
    truth=ingest.load_verified_runner_case(receipt['input_record'],expected_role='DEVELOPMENT_GLOBAL',root=Path(cfg['coupling_root']))
    assert truth.c_hat.shape==(21,7,2) and truth.p_scale.shape==(21,)


def test_production_native_path_uses_verified_spec_but_holds_unobserved_engine(tmp_path,monkeypatch):
    from apcd_gpu_v2 import serial
    cfg,rs,equivalent=fixture(tmp_path)
    pin=Pin(path=cfg.queue.path,sha256=cfg.queue.sha256)
    # Explicit test release for the PRODUCTION_GPU code branch; never a production approval.
    release=json.loads(Path(cfg.release.path).read_text());release.update(mode='PRODUCTION_GPU',science_authorized=True,legacy_ingress_closed=True,owner_clear=True)
    Path(cfg.release.path).write_text(json.dumps(release))
    config=cfg.model_copy(update={'mode':'PRODUCTION_GPU','release':Pin(path=cfg.release.path,sha256=sha256(cfg.release.path)),'truth_toolchain':dict(lumapi=pin,postprocessor=pin,decoder=pin,importer=pin),'coupling_root':str(tmp_path)})
    request=rs[0].model_copy(update={'config_sha256':config.sha256})
    ledger=SerialLedger(Path(cfg.runtime_root)/'production_branch_test.sqlite3');ledger.register(request,config)
    original=serial.subprocess.Popen;captured=[]
    def launch(command,**kwargs):
        captured.append(command)
        assert command[1:5]==['-nw','-hide','-trust-script','-run']
        return original([sys.executable,str(equivalent.script),command[-1]],**kwargs)
    monkeypatch.setattr(serial.subprocess,'Popen',launch)
    monkeypatch.setattr(serial,'native_preflight',lambda *args:None)
    monkeypatch.setattr(serial,'gpu_inventory_gate',lambda config:{'test_double':True})
    validator=serial.NativeTruthValidator(config)
    with pytest.raises(Refused,match='ENGINE_PID_NOT_OBSERVED'):
        run_serial_case(config,request,ledger,ProductionNativeBackend(),validator)
    assert len(captured)==1 and ledger.audit()['slot']['token']
    lsf=Path(captured[0][-2]).read_text()
    assert 'run("FDTD","GPU","GPU license audit")' in lsf and 'save;' in lsf and 'switchtolayout' not in lsf


def test_real_worker_abrupt_exit_and_load_only_recovery(tmp_path):
    import subprocess
    from apcd_gpu_v2.serial import recover_load_only
    cfg,rs,backend=fixture(tmp_path,2)
    root=Path(cfg.runtime_root)
    (root/'config.json').write_text(cfg.model_dump_json());(root/'request.json').write_text(rs[0].model_dump_json())
    child=root/'crash_worker.py'
    child.write_text('''import sys,os,json
from pathlib import Path
from apcd_gpu_v2.serial import *
cfg=SerialConfig.model_validate_json(Path(sys.argv[1]).read_text())
r=SerialRequest.model_validate_json(Path(sys.argv[2]).read_text())
l=SerialLedger(Path(cfg.runtime_root)/'ledger.sqlite3');l.register(r,cfg)
def fault(step):
 if step=='solver_returned':os._exit(33)
run_serial_case(cfg,r,l,EquivalentBackend(Path(cfg.runtime_root)/'fake_solver.py'),None,fault=fault)
''')
    result=subprocess.run([sys.executable,str(child),str(root/'config.json'),str(root/'request.json')],capture_output=True,text=True)
    assert result.returncode==33,result.stderr
    ledger=SerialLedger(root/'ledger.sqlite3');assert ledger.audit()['slot']['token']
    before=sum(e['kind']=='LAUNCH_REQUESTED' for e in ledger.audit()['events'])
    result=controller(cfg,rs,backend,validator)
    assert not result['slot']['token'] and all(t['state']=='TRUTH_VALID' for t in result['tasks'])
    assert sum(e['kind']=='LAUNCH_REQUESTED' and e['request_sha']==rs[0].request_sha256 for e in result['events'])==before==1
    assert sum(e['kind']=='LAUNCH_REQUESTED' for e in result['events'])==2


def test_vendored_science_has_no_old_runtime_import_or_execution():
    import ast
    from apcd_gpu_v2.science import postprocess as p
    source=Path(p.__file__).read_text(encoding='utf-8');tree=ast.parse(source)
    functions={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
    assert not any('run_' in name for name in functions)
    assert 'shared_fdtd.engine' not in source
    provenance=json.loads(Path(p.__file__).with_name('PROVENANCE.json').read_text(encoding='utf-8'))
    original=ast.parse(Path(provenance['original_postprocessor']).read_text(encoding='utf-8'))
    old={n.name:n for n in original.body if isinstance(n,ast.FunctionDef)}
    for n in tree.body:
        if isinstance(n,ast.FunctionDef) and n.name!='postprocess':
            class NormalizeImport(ast.NodeTransformer):
                def visit_ImportFrom(self,node):
                    if node.module=='shared_fdtd.tools.pw_complex_floquet_state_v1':
                        node.module='pw_complex_floquet_state_v1';node.level=1
                    return node
            normalized=NormalizeImport().visit(old[n.name])
            assert ast.dump(n,include_attributes=False)==ast.dump(normalized,include_attributes=False)
    assert sha256(Path(p.__file__).with_name('pw_complex_floquet_state_v1.py'))==provenance['decoder_sha']


def test_native_truth_validator_with_saved_g025_and_real_importer(tmp_path,monkeypatch):
    import numpy as np
    from apcd_gpu_v2 import native_readonly as nr
    from apcd_gpu_v2.serial import NativeTruthValidator
    from apcd_gpu_v2.science import postprocess
    cfg,requests,_=fixture(tmp_path)
    acceptance=json.loads(CONTRACT.read_text(encoding='utf-8'))
    receipt=json.loads(Path('D:/project/worktrees/blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2/reports/native_acceptance_v1/g025_actual_importer.json').read_text(encoding='utf-8'))
    import k6_v2_pipeline.ingest as importer
    path=Path(postprocess.__file__)
    pins=dict(postprocessor=Pin(path=str(path),sha256=sha256(path)),decoder=Pin(path=str(path.with_name('pw_complex_floquet_state_v1.py')),sha256=sha256(path.with_name('pw_complex_floquet_state_v1.py'))),lumapi=Pin(path=acceptance['lumapi_path'],sha256=acceptance['lumapi_sha256']),importer=Pin(path=str(Path(importer.__file__)),sha256=sha256(importer.__file__)))
    cfg=cfg.model_copy(update={'truth_toolchain':pins,'coupling_root':acceptance['coupling_root']})
    request=requests[0].model_copy(update={'case_id':'K6GDP2_DEV_G025','ordered_D_nm':tuple(receipt['input_record']['ordered_D_nm']),'config_sha256':cfg.sha256})
    fsp=tmp_path/'existing_copy.fsp';fsp.write_bytes(b'API_LOAD_FIXTURE_NOT_REAL_FSP')
    class Session:
        closed=False
        def load(self,p):pass
        def getdata(self,monitor,component):
            if component=='f':return 299792458/(np.arange(440,461)*1e-9)
            if component in ['x','y','z']:return np.array([0.,1.])
            return np.ones((2,2,1,21),complex)
        def close(self):self.closed=True
    session=Session()
    class Lum:
        FDTD=staticmethod(lambda **kw:session)
    original=nr.pinned_module
    def pinned(p,h,n):
        assert sha256(p)==h
        if n=='lumapi':return Lum
        if n=='apcd_gpu_v2.science.postprocess':return postprocess
        return original(p,h,n)
    monkeypatch.setattr(nr,'pinned_module',pinned)
    monkeypatch.setattr(postprocess,'load_only_validate',lambda fd,cfg:None)
    def saved_postprocess(fd,config,out):
        # API and postprocessing doubles consume accepted historical evidence; importer is real.
        out=Path(out);record=receipt['input_record'];paths={}
        mapping={'state_npz':'state_npz','state_metadata':'state_metadata','raw_fields':'raw_npz','raw_json':'raw_metadata','angular':'orders_json'}
        for key,desc in mapping.items():
            src=Path(record[desc]['path']);dest=out/src.name;shutil.copyfile(src,dest);paths[key]=dest
        raw=json.loads(paths['raw_json'].read_text(encoding='utf-8'));raw['raw_complex_fields']['path']=str(paths['raw_fields'])
        paths['raw_json'].write_text(json.dumps(raw),encoding='utf-8')
        return raw,raw['metrics'],paths
    monkeypatch.setattr(postprocess,'postprocess',saved_postprocess)
    result=NativeTruthValidator(cfg)(fsp,request,tmp_path)
    assert result['verdict']=='PASS' and result['outputs']==609 and session.closed
    with np.load(result['labels_artifact']['path'],allow_pickle=False) as saved:
        assert saved['C_hat_real'].shape==(21,7,2) and saved['P_scale'].shape==(21,)
    assert all(e['api'] not in ['run','save','switchtolayout'] for e in result['native_session']['events'])
