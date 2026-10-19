import ast,inspect,json,os,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/coupling_ml'))
import m2s_coupling_source_lateral_robustness_controller_v1 as p
import postsolver_persistence_v1 as h
from coupling_fdtd_adapter_v1 import AppSessionFailure

@pytest.fixture
def execution(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'INTEGRATION',tmp_path)
    setup=tmp_path/'setup.fsp';setup.write_bytes(b'setup-only')
    contract=tmp_path/'contract.json';contract.write_text('{}')
    config=dict(schema='M2S_PERSISTENCE_EXECUTION_V1',purpose='TINY_INFRASTRUCTURE_VALIDATION',campaign_id='unit',root=str(tmp_path/'run'),
        jobs=[dict(job_id='job_01',attempt_id='attempt_001',setup_pre_fsp=str(setup),setup_sha256=h.sha256_file(setup),physical_contract_path=str(contract),physical_contract_sha256=h.sha256_file(contract),validation={'frequency_points':3})],code_sha256=p.code_identity(),injection='none')
    path=tmp_path/'execution.json'
    def save():config['manifest_sha256']=p.digest({k:v for k,v in config.items() if k!='manifest_sha256'});h.atomic_json(path,config)
    save();return path,config,save

def test_actual_entrypoint_has_one_worker_and_no_legacy_native_bypass():
    tree=ast.parse(p.ENTRYPOINT.read_text())
    assert len([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker'])==1
    assert 'controller.execute(' in inspect.getsource(p.worker)
    assert 'accept_worker(' in inspect.getsource(p.campaign)
    assert 'str(ENTRYPOINT)' in inspect.getsource(p.campaign)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['FDTD','run','save','close'] for n in ast.walk(ast.parse(inspect.getsource(p.worker))))

def test_legacy_production_invocation_rejected_without_mutation():
    with pytest.raises(h.LifecycleError,match='protected'):p.worker(p.CASES[0])
    with pytest.raises(h.LifecycleError,match='protected'):p.campaign()

def test_manifest_code_and_physical_sha_bound(execution):
    path,c,save=execution
    assert p.load_execution(path)['jobs'][0]['repair_version']==p.REPAIR_VERSION
    c['code_sha256']={};save()
    with pytest.raises(h.LifecycleError,match='code SHA'):p.load_execution(path)
    c['code_sha256']=p.code_identity();save();Path(c['jobs'][0]['setup_pre_fsp']).write_bytes(b'changed')
    with pytest.raises(h.LifecycleError,match='contract SHA'):p.load_execution(path)

def test_production_release_requires_separate_authority(execution):
    path,c,save=execution;c['purpose']='M2S_PRODUCTION';save()
    with pytest.raises((FileNotFoundError,h.LifecycleError)):p.load_execution(path)

def test_authorized_production_manifest_routes_same_worker_without_running(execution,monkeypatch,tmp_path):
    path,c,save=execution
    setup=c['jobs'][0]['setup_pre_fsp'];setup_sha=c['jobs'][0]['setup_sha256']
    jobs=[]
    for case_id in p.CASES:
        contract=next((p.OUT/case_id/'attempt_001').glob('*PHYSICAL_CONTRACT*.json'))
        jobs.append(dict(job_id=case_id,attempt_id='attempt_002',setup_pre_fsp=setup,setup_sha256=setup_sha,
                         physical_contract_path=str(contract),physical_contract_sha256=h.sha256_file(contract)))
    monkeypatch.setattr(p,'ML',tmp_path/'mock_ml')
    c.update(purpose='M2S_PRODUCTION',jobs=jobs,root=str(p.ML/'outputs/coupling_ml/fresh_attempt_002'))
    h.atomic_json(tmp_path/'RELEASE_GATE.json',dict(repair_validation='PASS',code_sha256=p.code_identity()))
    approval=tmp_path/'mock_chart_approval.json'
    h.atomic_json(approval,dict(authority='CHART_M2S_ATTEMPT_002_AUTHORIZATION',approved=True,case_ids=list(p.CASES),solver_entries=2,code_sha256=p.code_identity(),
                               physical_contract_sha256={j['job_id']:j['physical_contract_sha256'] for j in jobs},setup_sha256={j['job_id']:j['setup_sha256'] for j in jobs}))
    c.update(authorization_path=str(approval),authorization_sha256=h.sha256_file(approval));save()
    loaded=p.load_execution(path)
    assert all(j['worker_identity']==str(p.ENTRYPOINT)+'::worker' and j['repair_version']==p.REPAIR_VERSION and j['validation']['frequency_points']==11 for j in loaded['jobs'])
    assert not Path(c['root']).exists()  # Manifest validation alone invokes no worker or solver.

def test_tiny_root_and_four_slot_rejected(execution,tmp_path):
    path,c,save=execution;c['root']=str(tmp_path.parent/'outside');save()
    with pytest.raises(h.LifecycleError,match='sandbox'):p.load_execution(path)
    c['root']=str(tmp_path/'run');c['jobs']=[dict(c['jobs'][0],job_id='job_'+str(i)) for i in range(4)];save()
    with pytest.raises(h.LifecycleError,match='capacity'):p.load_execution(path)

class FakeAdapter:
    runs=0;closed=[]
    def __init__(self,root,manifest,entrypoint):self.root=Path(root);self.manifest=manifest;self.session_id='fake-owner';self.app_processes=[{'pid':999999}];self.live=False
    def open(self,path):self.live=True;return object()
    def run(self,fd):type(self).runs+=1
    def save(self,fd,path):
        if self.manifest['injection']=='session_loss':self.live=False;raise AppSessionFailure('injected dead application')
        if self.manifest['injection']=='save_failure' and Path(path).name=='canonical.fsp':raise PermissionError('injected save error')
        Path(path).write_bytes(b'persisted-truth')
    def rescue_save(self,fd,path):Path(path).write_bytes(b'recovered-truth')
    def live_results_available(self,fd):
        if not self.live:raise AppSessionFailure('dead session')
        return True
    def load_only(self,path,manifest):return dict(ok=True,identity_pass=True,arrays_pass=True,shape_pass=True,sanity_pass=True,run_called=False,session_id='independent-fake')
    def extract_raw(self,fd,post,raw):Path(raw).write_bytes(b'raw')
    def extract_raw_from_post(self,post,raw):Path(raw).write_bytes(b'recovered-raw')
    def close(self,fd):
        states=[json.loads(l)['state'] for l in (self.root/'events.jsonl').read_text().splitlines()]
        assert 'POST_FSP_VALIDATED' in states
        type(self).closed.append(True);self.live=False
    def processes_absent(self):return not self.live

@pytest.fixture
def fake_runtime(monkeypatch):
    released=[];FakeAdapter.runs=0;FakeAdapter.closed=[]
    class Lease:
        slot_id='TEST_SLOT';record={'slot_id':'TEST_SLOT'}
        def start_heartbeat(self,**kw):pass
        def stop_heartbeat(self):pass
        def mark_solver_entered(self):pass
    class Scheduler:
        def acquire_wait(self,*a,**kw):return Lease()
        def release(self,lease,reason):released.append(reason)
    class Module:GlobalSlotScheduler=Scheduler
    monkeypatch.setattr(p,'scheduler_module',lambda:Module)
    monkeypatch.setattr(p,'FDTDAdapter',FakeAdapter)
    monkeypatch.setattr(p,'compatible_process_snapshot',lambda m:{'quality':'AVAILABLE'})
    monkeypatch.setattr(p,'derive_raw',lambda raw,spec:dict(arrays_pass=True,shape_pass=True,sanity_pass=True,finite_derived=True))
    return released

@pytest.mark.parametrize('mode',['none','save_failure','parser_failure','telemetry_failure'])
def test_real_worker_import_and_execution_gates(execution,fake_runtime,mode):
    path,c,save=execution;c['injection']=mode;save()
    assert p.worker('job_01',path)==0
    root=Path(c['root'])/'job_01';result=p.accept_worker(root)
    assert result['status']=='COMPLETED' and FakeAdapter.runs==1 and len(FakeAdapter.closed)==1
    assert fake_runtime and h.sha256_file(root/'frozen.fsp')==c['jobs'][0]['setup_sha256']
    entered=p.read(root/'events.entered.json');assert entered['physical_contract_sha256']==c['jobs'][0]['physical_contract_sha256']
    if mode=='save_failure':assert result['post_fsp'].endswith('recovery.fsp')
    if mode=='parser_failure':assert result['run_invocation_count']==0
    if mode=='telemetry_failure':assert p.read(root/'worker_result.json')['status']=='COMPLETED_WITH_DEGRADED_TELEMETRY'

def test_session_loss_rejected_and_failure_slot_reconciled(execution,fake_runtime):
    path,c,save=execution;c['injection']='session_loss';save()
    assert p.worker('job_01',path)==31
    root=Path(c['root'])/'job_01'
    assert not (root/'completion.json').exists() and not FakeAdapter.closed
    assert p.read(root/'failure.json')['error_class']=='APP_SESSION_FAILURE'
    assert fake_runtime==['FAILED_AFTER_ENTRY_SESSION_ABSENT']
    with pytest.raises(h.LifecycleError):p.accept_worker(root)

def test_original_contract_digest_and_production_validation():
    contract=next(p.OUT.glob('*/attempt_001/*PHYSICAL_CONTRACT*.json'));data=p.read(contract)
    assert data['physical_contract_hash']==p.digest({k:v for k,v in data.items() if k!='physical_contract_hash'})
    spec=p.production_validation(data)
    assert spec['monitor']=='source_interface_complex' and spec['frequency_points']==11
    assert ['FDTD','dimension','3D'] in spec['identity']
    assert next(value for obj,prop,value in spec['identity'] if obj=='source_dipole' and prop=='z')==pytest.approx(-276e-9)
