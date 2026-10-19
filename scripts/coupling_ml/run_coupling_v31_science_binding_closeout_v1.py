from pathlib import Path
import sys,json,sqlite3,subprocess,importlib.util,copy
from types import SimpleNamespace as NS
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_DIAG2_V31_FINAL_EXECUTION_GATE_CLOSEOUT_V1';O.mkdir(exist_ok=False)
sys.path.insert(0,str(R/'scripts/coupling_ml'));sys.path.insert(0,r'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\platform_v2')
from k6_v2_pipeline import ingest as I
from apcd_gpu_v2.serial import Diag2Budget
from coupling_v31_science_binding_v1 import bind_original_case,write_binding_exclusive,simulate_bound_entry
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(O/n).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n',encoding='utf-8')
put('GIT_BASELINE.json',{k:subprocess.check_output(['git','-C',str(R)]+v,text=True).strip() for k,v in [('head',['rev-parse','HEAD']),('branch',['branch','--show-current']),('ahead_behind',['rev-list','--left-right','--count','HEAD...@{u}']),('status',['status','--short']),('staged',['diff','--cached','--name-only'])]})
F=O/'identity_fixture';F.mkdir();B=R/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/fixtures/B_DIAG2_TEST_FIXTURE';manifest=read(B/'BATCH_MANIFEST_TEST_FIXTURE_ONLY.json');cases=manifest['cases'];ids=[x['case_id'] for x in cases]
runner_path=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py');spec=importlib.util.spec_from_file_location('deployed_runner_binding_fixture',runner_path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
db=F/'runner_fixture.db';runner=mod.MinimalBatchRunner(str(db));m=F/'BATCH_TEST_FIXTURE_ONLY.json';m.write_text(json.dumps({'batch_name':'K6V3_TIME_DIAG2_V1_BATCH_001','description':'TEST_FIXTURE_ONLY_NO_SOLVER','jobs':[{'input_fsp':c['source_fsp']['path'],'sha256':c['source_fsp']['sha256']} for c in cases]}));assert runner.submit_batch(str(m))[0]
con=sqlite3.connect(db);con.row_factory=sqlite3.Row;batch=dict(con.execute('select * from batches').fetchone());jobs=[dict(r) for r in con.execute('select * from jobs order by id')];con.close()
bindings=[bind_original_case(c,batch,j,db) for c,j in zip(cases,jobs)]
for b in bindings:write_binding_exclusive(F/(b['case_id']+'_BINDING_TEST_FIXTURE_ONLY.json'),b)
pins={'registry':I.sha256_file(B/'BATCH_MANIFEST_TEST_FIXTURE_ONLY.json'),'admission':I.sha256_file(B/'SCIENCE_ADMISSION_TEST_FIXTURE_ONLY.json'),'contract':cases[0]['physics_contract_sha'],'release':I.sha256_file(runner_path)}
def create_budget(folder):
 folder.mkdir(exist_ok=False);p=folder/'SCIENCE_LEDGER_TEST_FIXTURE_ONLY.json'
 j={'schema':Diag2Budget.schema,'status':'OPEN','TEST_FIXTURE_ONLY':True,'dataset_id':'APCD_COUPLING_V3_TIME_DIAG2_V1','batch_id':'K6V3_TIME_DIAG2_V1_BATCH_001','case_ids':ids,'max_new_entries':2,'per_case_entry_limit':1,'automatic_replays':0,'registry_sha256':pins['registry'],'scientific_admission_sha256':pins['admission'],'physical_contract_sha256':pins['contract'],'entered_case_ids':[],'remaining_case_ids':ids.copy(),'truth_valid_case_ids':[],'labels_valid_case_ids':[],'entry_count':0,'remaining_count':2,'truth_valid_count':0,'labels_valid_count':0,'case_records':{c:{'attempt_id':'attempt_001','max_entry_count':1,'entry_count':0,'replay_count':0,'phase':'UNENTERED'} for c in ids}}
 p.write_text(json.dumps(j,indent=2));body={'mode':'TEST_FIXTURE_ONLY','ledger':str(p),'pins':pins};cfg=NS(coupling_ledger=str(p),registry=NS(sha256=pins['registry']),scientific_admission=NS(sha256=pins['admission']),physical_contract_sha256=pins['contract'],mode='TEST_FIXTURE_ONLY',sha256=I._canon(body),release=NS(sha256=pins['release']));return Diag2Budget(cfg)
checks=read(R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1/CONTRACT_SOURCE_AUDIT.json')['source_setup_checks']
requests=[]
for c in cases:
 pins_by_role={x['role']:x['sha256'] for x in checks if x['case_id']==c['case_id']}
 requests.append(NS(case_id=c['case_id'],attempt_id=c['attempt_id'],request_sha256=c['case_request_sha256'],dataset_id='APCD_COUPLING_V3_TIME_DIAG2_V1',batch_id='K6V3_TIME_DIAG2_V1_BATCH_001',admission_sha256=pins['admission'],pre_fsp_sha256=c['source_fsp']['sha256'],source_setup_fsp_sha256=pins_by_role['direct_source_setup_pre_fsp'],source_run_fsp_sha256=pins_by_role['source_run_anchor_fsp'],physical_contract_sha256=c['physics_contract_sha']))
budget=create_budget(F/'shared_old_new_adapter');launches=[];tests=[]
def mock_launch(b):
 req=next(x for x in requests if x.case_id==b['case_id']);proof=budget.reconcile(req);assert proof['entered_in_ledger'] and proof['receipt']['solver_entered'] is True
 con=sqlite3.connect(db);rows=con.execute('select job_id,attempt_id from solver_entries where job_id=?',(b['runner_job_id'],)).fetchall();con.close();assert rows==[(b['runner_job_id'],b['runner_attempt_tag'])]
 launches.append({'binding':b,'science_entry_before_mock_launch':True,'Runner_entry_before_mock_launch':True,'actual_solver_called':False});return 'MOCK_ONLY_NO_ENGINE'
for b,r in zip(bindings,requests):assert simulate_bound_entry(b,r,budget,runner,F,mock_launch)=='MOCK_ONLY_NO_ENGINE'
tests.append({'name':'A1_A2_science_to_real_Runner_SQLite_rows_positive_simulation','pass':True})
# Independent SQL/JSON reconciliation, without trusting adapter return values.
con=sqlite3.connect(db);actual=con.execute('select job_id,attempt_id from solver_entries order by job_id').fetchall();con.close();s=read(budget.path);assert len(actual)==2 and s['entry_count']==2 and s['remaining_count']==0 and s['labels_valid_count']==0
tests.append({'name':'independent_SQLite_JSON_WAL_reconciliation','pass':True})
def refused(name,f):
 try:f()
 except Exception as ex:tests.append({'name':name,'pass':True,'reason':str(ex)});return
 raise AssertionError(name)
for r in requests:refused('legacy_V2_adapter_rejects_case_consumed_by_V31_'+r.case_id,lambda r=r:Diag2Budget(budget.config).validate(r))
refused('V31_repeat_rejected',lambda:simulate_bound_entry(bindings[0],requests[0],budget,runner,F,mock_launch))
refused('binding_overwrite_rejected',lambda:write_binding_exclusive(F/(ids[0]+'_BINDING_TEST_FIXTURE_ONLY.json'),bindings[0]))
wrong=copy.deepcopy(jobs[0]);wrong['input_fsp_sha256']='0'*64;refused('wrong_inputSHA_rejected_in_science_binding',lambda:bind_original_case(cases[0],batch,wrong,db))
# Reverse direction uses the same unmodified budget adapter and writer/WAL rules.
reverse=create_budget(F/'reverse_old_first');reverse.prepare_entry(requests[0],'OLD_EXECUTOR_TEST_ONLY');refused('new_adapter_rejects_original_identity_after_old_entry',lambda:Diag2Budget(reverse.config).validate(requests[0]))
# A crash after durable entry receipt cannot make a new free attempt.
crash=create_budget(F/'receipt_before_ledger_crash')
def fault(step):
 if step=='coupling_receipt_committed':raise RuntimeError('SIMULATED_CRASH_NO_SOLVER')
refused('crash_after_entry_receipt',lambda:crash.prepare_entry(requests[0],'CRASH_TEST_ONLY',fault=fault));assert read(crash.path)['entry_count']==0
refused('uncertain_receipt_blocks_retry',lambda:crash.validate(requests[0]));repair=crash.reconcile_entry_evidence(requests[0]);assert repair['entered'] and not repair['replay_allowed'] and read(crash.path)['entry_count']==1
tests.append({'name':'existing_conservative_reconciliation_no_refund','pass':True})
put('IDENTITY_JOB_BINDING_OFFLINE_TESTS.json',{'status':'PASS_FOR_ISOLATED_INTERFACE','tests':tests,'pass':len(tests),'fail':0,'actual_launches':0,'fixture_Runner_entry_rows':2,'fixture_budget_entry_rows_total_across_independent_scenarios':4,'real_DIAG2_entry_count':0,'new_budget_authority':False,'source_authority':'frozen existing B test authority only; not productionapproval','bindings':bindings,'launch_order_evidence':launches,'independent_SQLite_rows':actual,'shared_adapter':'unmodified apcd_gpu_v2.serial.Diag2Budget','shared_writer_lock':'existing .v2_writer.lock','receipt_crash_recovery':repair,'production_binding':'HOLD: no actual production job rows; V2/V3 shared activation/fencing enforcement not independently attested'})
print('IDENTITY_ZERO_SOLVER_PASS',len(tests),flush=True)
