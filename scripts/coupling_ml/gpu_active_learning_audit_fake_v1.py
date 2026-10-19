"""Read-only science audit plus explicitly isolated official Runner fake calls."""
from pathlib import Path
import sys,json,subprocess,hashlib,sqlite3,os,importlib.util,copy,time
import numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';O.mkdir(exist_ok=True)
P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');runner=P/'minimal_batch_runner_v3.1_final.py';py=r'C:\Users\DELL\anaconda3\python.exe'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import generic_profile as G,science_ledger as L,contracts as C
from k6_v2_pipeline.test_science_contract_closeout import admission,receipt
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=O/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
git={'head':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','-C',str(R),'branch','--show-current'],text=True).strip(),'status':subprocess.check_output(['git','-C',str(R),'status','--short'],text=True).splitlines(),'staged':subprocess.check_output(['git','-C',str(R),'diff','--cached','--name-only'],text=True).splitlines()};put('GIT_AUDIT_BASELINE.json',git)
actual=sha(runner);dep=read(P/'deployment_manifest.json');assert actual==dep['installed']['sha256']
guide=Path(r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\minimal_runner_candidate\USER_GUIDE_V3.1_CN.md');assert guide.exists()
# Production databases are opened only in SQLite URI read-only mode.
dbs=[]
for base in [P,P.parent/'data',P.parent/'v3_data']:
 if not base.exists():continue
 for db in base.rglob('*.db'):
  try:
   con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);tables=[x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")];row={'path':str(db),'tables':tables}
   if 'jobs' in tables:
    cols=[x[1] for x in con.execute('pragma table_info(jobs)')];row['job_columns']=cols
    if 'input_fsp_path' in cols:row['diag2_input_matches']=[{'id':x[0],'input_fsp_path':x[1],'status':x[2]} for x in con.execute('select id,input_fsp_path,status from jobs') if 'diag2' in str(x[1]).lower()]
   if 'solver_entries' in tables:row['total_solver_entries']=con.execute('select count(*) from solver_entries').fetchone()[0]
   con.close();dbs.append(row)
  except Exception as ex:dbs.append({'path':str(db),'read_error':str(ex)})
contract=R/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/SCIENCE_CONTRACT_6PS.json';doc=read(contract);contractsha=sha(contract);assert contractsha=='51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36'
binding=read(R/'reports/coupling/APCD_COUPLING_DIAG2_FINAL_ADMISSION_BINDING_V1/FINAL_ADMISSION_BINDING_CHECK.json');cases=[];jobs=[]
for c in binding['candidate_binding']['cases']:
 checks=[]
 for d in c['source_setup_checks']:
  path=Path(d['path']);actualsha=sha(path);assert actualsha==d['expected_sha256'];checks.append({'role':d['role'],'path':str(path),'sha256':actualsha,'match':True})
 setup=[z for z in checks if 'candidate' in z['role'] and z['path'].lower().endswith('.fsp')]
 if not setup:
  fsp=Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1\candidate_setups')/c['case_id']/'attempt_001/pre.fsp';setup=[{'path':str(fsp),'sha256':sha(fsp)}]
 cases.append({'case_id':c['case_id'],'attempt_id':c['attempt_id'],'ordered_D_nm':c['ordered_D1_D6_nm'],'max_entries':1,'source_setup_checks':checks,'physics_contract_sha':contractsha})
 jobs.append({'input_fsp':setup[0]['path'],'sha256':setup[0]['sha256']})
put('DIAG2_V31_UNSUBMITTED_MANIFEST_CANDIDATE.json',{'batch_name':'K6V3_TIME_DIAG2_V1_BATCH_001','description':'CANDIDATE ONLY; NOT ADMITTED; DO NOT SUBMIT OR RUN','jobs':jobs,'science_sidecar':{'case_bindings':cases,'approved_historical_max':2,'current_task_real_entry_authority':0,'V31_budget_mapping':'NOT_AUTHENTICATED','runtime_attempt_identity_mapping':'MISSING_V31_GENERATES_ATTEMPTS','contract_file':str(contract),'physics_contract_sha':contractsha,'auto_shutoff_min':1e-6,'simulation_time_s':6e-12,'profile':'coupling_609d_v1'}})
doepath=R/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json';doe=read(doepath);assert doe['entered_count']==4 and doe['remaining_unentered_count']==52
timing=[]
def find_times(v,out):
 if isinstance(v,dict):
  if 'started_unix' in v and 'returned_unix' in v:out.append(float(v['returned_unix'])-float(v['started_unix']))
  for z in v.values():find_times(z,out)
 elif isinstance(v,list):
  for z in v:find_times(z,out)
for cid,row in doe['case_records'].items():
 a=[];find_times(row,a);timing.append({'case_id':cid,'solver_call_seconds_found':a,'end_to_end_seconds':row.get('end_to_end_seconds'),'source':'read existing DOE56 ledger timing metadata only; responses not accessed'})
put('SCIENCE_AUTHORITY_AUDIT.json',{'current_authority':'user APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1','owner':'Coupling-ML Codex','AGENTS':'user supplied; no worktree or parent AGENTS exists','old_owner_handoff_requirement':'superseded by latest user; only Runner internal failures go to maintainer','DIAG2':{'cases':cases,'historical_entered':0,'historical_budget':2,'V31_mapping':'BLOCKED','current_entry_authority':0,'evidence':'last formal issuance HOLD + current read-only Runner DB search; no authenticated DIAG2 ledger newly discovered','truth_6ps_validation':'NOT_RUN'},'DOE56':{'entered':4,'unentered_hold':52,'ledger':str(doepath),'policy':'FROZEN_NUMERICAL_ADVANCEMENT_HOLD'},'production_database_readonly_inventory':dbs,'timing':timing,'contract_sha':contractsha})
put('COST_EVIDENCE.json',{'historical_DIAGNOSTIC_timings':timing,'DIAG2_6ps_measured':'NOT_RUN','V31_real_K6_baseline':'NOT_ESTABLISHED_IN_THIS_TASK','tariff':'UNKNOWN; GPU-hours only, no currency claim'})
# Real resource snapshot; collect names and identity, never credential-bearing command lines.
import psutil
processes=[]
for proc in psutil.process_iter(['pid','name','create_time','username']):
 try:
  d=proc.info
  if any(s in (d['name'] or '').lower() for s in ['fdtd','lumerical','python','mpiexec']):processes.append(d)
 except (psutil.NoSuchProcess,psutil.AccessDenied):pass
nvidia=subprocess.run(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total','--format=csv,noheader'],capture_output=True,text=True)
put('RESOURCE_READONLY_SNAPSHOT.json',{'unix':time.time(),'processes':processes,'nvidia_returncode':nvidia.returncode,'nvidia_stdout':nvidia.stdout,'nvidia_stderr':nvidia.stderr,'admission':'HOLD; no live independent external resource ownership/fencing verifier in V31','WDDM_NA_is_idle':False})
# Official CLI isolated by both cwd and --db; fake records never enter science production ledgers.
S=O/'fake_runner_fixture';S.mkdir(exist_ok=False);db=S/'TEST_ONLY_runner.db';logs=[]
fixture=S/'SYNTHETIC_NOT_FSP_INPUT.txt';fixture.write_text('TEST_FIXTURE_ONLY; NOT NATIVE FSP; ZERO REAL SOLVER\n')
def cli(cmd,batch,extra=[]):
 a=[py,str(runner),cmd,batch,'--db',str(db)]+extra;p=subprocess.run(a,cwd=S,capture_output=True,text=True);logs.append({'argv':a,'cwd':str(S),'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});return p
for batch in ['AL_FAKE_B','AL_FAKE_C','AL_FAKE_CROSS_BATCH_DUP']:
 m=S/(batch+'.json');m.write_text(json.dumps({'batch_name':batch,'description':'TEST_FIXTURE_ONLY','jobs':[{'input_fsp':str(fixture),'sha256':'INTENTIONALLY_WRONG_SHA_NEGATIVE_TEST'}]}));assert cli('submit',batch,['--manifest',str(m)]).returncode==0
assert cli('submit','AL_FAKE_B',['--manifest',str(S/'AL_FAKE_B.json')]).returncode!=0
for batch in ['AL_FAKE_B','AL_FAKE_C']:assert cli('run',batch,['--fake-solver']).returncode==0;cli('status',batch)
con=sqlite3.connect(db);rows=con.execute('select id,status,output_fsp_path from jobs order by id').fetchall();before=con.execute('select count(*) from solver_entries').fetchone()[0];con.close();assert before==2 and rows[0][1]==rows[1][1]=='COMPLETED'
assert Path(rows[0][2]).is_absolute() is False
assert (S/rows[0][2]).read_bytes()==fixture.read_bytes()
spec=importlib.util.spec_from_file_location('installed_v31',runner);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);oldcwd=os.getcwd();os.chdir(S)
try:
 r=mod.MinimalBatchRunner(str(db));assert not r._check_no_replay(rows[0][0])[0];assert r._check_no_replay(rows[2][0])[0]
 ok,msg=r.run_job(rows[0][0],str(fixture),str(S/'NEVER_OUTPUT.fsp'),fake_solver=True);assert not ok
 # Hold actual same mutex from another handle; runner must refuse before fake entry.
 import msvcrt
 lock=open(S/'gpu_runner.lock','r+');msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 try:ok,msg=r.run_job(rows[2][0],str(fixture),str(S/'NEVER_LOCK_OUTPUT.fsp'),fake_solver=True);assert not ok
 finally:msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close();r._release_gpu_lock()
finally:os.chdir(oldcwd)
con=sqlite3.connect(db);assert con.execute('select count(*) from solver_entries').fetchone()[0]==2;con.close()
try:G.validate_profile_admission(authority={},case_id='AL_FAKE_1',attempt_id='attempt_001');raise AssertionError('authority bypass')
except ValueError:pass
# Reuse numeric 609D core on analytic synthetic CaseTruth. Not native extraction or admission.
chat=np.zeros((21,7,2),complex);chat[:,4,0]=1;ps=np.ones(21);eta=np.zeros((21,7));eta[:,4]=1
case=C.CaseTruth('AL_FAKE_1','attempt_001',C.ROLE_GLOBAL_DEV,(100,105,110,115,120,125),chat,ps,eta,eta.copy(),{'fixture_only':True});numeric=G._validate_609d_numeric_payload(case);assert numeric['outputs']==609
states={};receipts={}
for b,cid,pin in [('AL_FAKE_B','AL_FAKE_1','a'*64),('AL_FAKE_C','AL_FAKE_2','b'*64)]:
 adm=admission(b,[cid]);state=L.initial_ledger(adm,pin,expected_science_owner=L.SCIENCE_OWNER_ID);rec=receipt(adm,cid,pin);rec.update(TEST_FIXTURE_ONLY=True,native_truth_validated=False,numeric_core=numeric)
 state=L.reconcile_offline_receipt(state,adm,rec,admission_sha256=pin,expected_science_owner=L.SCIENCE_OWNER_ID,test_fixture_only=True)
 try:L.reconcile_offline_receipt(state,adm,rec,admission_sha256=pin,expected_science_owner=L.SCIENCE_OWNER_ID,test_fixture_only=True);raise AssertionError('replay')
 except L.LedgerError:pass
 states[b]=state;receipts[b]=rec
put('FAKE_BACKEND_E2E.json',{'status':'PARTIAL','runner_fake_transport':'PASS','test_fixture_only':True,'real_solver_entries':0,'fake_database_entries':2,'same_job_no_replay':'PASS','cross_batch_scientific_duplicate_rejection':'FAIL: same input submitted under third batch; job_id No Replay misses scientific identity','incorrect_declared_SHA_rejection':'FAIL: all fake submissions accepted deliberately wrong SHA','mutex_HOLD_no_entry':'PASS','no_authority_profile_rejection':'PASS','mock_609D_numeric_core':'PASS','isolated_fixture_ledger_reconciliation':'PASS','states':states,'receipts':receipts,'positive_pipeline':'official CLI fake copy -> synthetic numeric 609D injected fixture -> mock receipt -> existing isolated ledger; no native H5 or physical-label validity asserted','native_H5_to_609D':'BLOCKED: deployed Runner only saves FSP; separate native E/H exporter and authorized record sidecar not wired','production_ledger_modified':False,'logs':logs})
source=runner.read_text(encoding="utf-8");put('RUNNER_V31_INTERFACE_AUDIT.json',{'installed_sha256':actual,'deployment_pin_matches':True,'guide_source':str(guide),'guide_missing_from_install':True,'CLI':['submit','run','status'],'fake_flag':'--fake-solver','isolation':'explicit --db and cwd isolate lock/outputs','problems':['input SHA stored but not verified','no science case/contract/budget validation','generated attempt_id differs from frozen attempt_001','No Replay by job_id only; cross-batch scientific duplicate accepted','resource gate only local mutex; no external solver/GPU ownership checks','no native H5/EH export or609D record construction','CLI run exits0 even when failed>0; status must be reconciled'],'formal_callability':'PASS','scientific_production_readiness':'HOLD','runner_internal_edits':0,'formal_request_to_maintainer':'read-only defect evidence only; no science delegation; Coupling retains sidecar/postprocessing ownership'})
print('AUDIT_FAKE_COMPLETE',json.dumps({'fake_entries':2,'real_entries':0,'diag2':'HOLD','runner':'HOLD','timing':timing}),flush=True)
