from pathlib import Path
import json,sqlite3,sys,importlib.util,ast,copy,hashlib,datetime,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');old=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION'
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
assert (D/'PREPARATION_AUDIT.json').exists(),'Preparation not complete; never launch solver'
pkg=rd(D/'AL50_COMPLEX_PRODUCTION_MANIFEST.json');cases=pkg['cases'];assert len(cases)==50 and len({c['case_id'] for c in cases})==50 and len({c['external_execution_id'] for c in cases})==50
meta=rd(D/'DEDUPLICATION_AUDIT.json');con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(r) for r in con.execute('select * from jobs')];entries=[dict(r) for r in con.execute('select * from solver_entries')];con.close();assert entries==meta['canonical_entries'];assert jobs==meta['canonical_jobs'];assert not any(j['external_execution_id'] in {c['external_execution_id'] for c in cases} for j in jobs)
# Frozen platform identity once at admission, no modification.
assert hashlib.sha256((P/'minimal_batch_runner_v3.1_final.py').read_bytes()).hexdigest()=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7'
sys.path[:0]=[str(P),str(R/'scripts/coupling_ml')];spec=importlib.util.spec_from_file_location('complex_frozen_runner',P/'minimal_batch_runner_v3.1_final.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
fix=D/'offline_interface_fixture';fix.mkdir();runner=m.MinimalBatchRunner(db_path=fix/'SCHEMA_ONLY_ZERO_ENTRY.sqlite',output_dir=fix/'unused_output',lock_path=fix/'UNUSED.lock');tests=[]
contract=rd(D/'FAST_FROZEN_PHYSICS_CONTRACT.json')
from k6_v2_pipeline import ingest as I,contracts as CT
assert I._canon(contract['contract'])==contract['contract_sha256']==CT.PHYSICAL_CONTRACT_SHA256
for c,b in zip(cases,pkg['runner_batches']):
 assert c['physical_contract_sha256']==contract['contract_sha256'];assert c['maximum_entries']==c['entries_authorized']==1;assert c['budget_proposal_id']=='AL50_COMPLEX_R03_BUDGET_PROPOSAL_V1'
 check=rd(c['readback']);assert check['geometry']['diameter_range_step_pass'] and check['geometry']['all_other_audited_properties_same_as_template'];a=check['fresh_saved_load_readback'];assert a['FDTD']['simulation time']==3e-12 and a['FDTD']['auto shutoff min']==1e-6;assert c['source_fsp_sha256']==check['source_fsp_sha256'];assert I.sha256_file(c['input_fsp'])==c['source_fsp_sha256']
 g=np.array(c['ordered_D_nm']);assert np.all((g>=100)&(g<=230)&((g-100)%5==0));assert all(abs(a[f'NP_D{k}']['radius']*2e9-d)<1e-9 for k,d in enumerate(g,1))
 ok,msg=runner.submit_batch(b['manifest']);assert ok,msg;tests.append({'test':c['case_id']+'_freshload_identity_sha_submit','pass':True})
first=rd(pkg['runner_batches'][0]['manifest']);bad=copy.deepcopy(first);bad['batch_name']+='__DUPLICATE_FIXTURE';p=fix/'duplicate.json';p.write_text(json.dumps(bad));ok,msg=runner.submit_batch(p);assert not ok and 'UNIQUE' in msg;tests.append({'test':'duplicate_execution_rejected','pass':True})
bad=copy.deepcopy(first);bad['batch_name']+='__WRONG_SHA_FIXTURE';bad['jobs'][0]['source_fsp_sha256']='0'*64;p=fix/'wrong_sha.json';p.write_text(json.dumps(bad));ok,msg=runner.submit_batch(p);assert not ok and 'SHA256' in msg;tests.append({'test':'wrong_source_sha_rejected','pass':True})
con=sqlite3.connect(fix/'SCHEMA_ONLY_ZERO_ENTRY.sqlite');assert con.execute('select count(*) from solver_entries').fetchone()[0]==0;assert con.execute('select count(*) from jobs').fetchone()[0]==50;con.close();tests.append({'test':'fixture_zero_entry','pass':True})
source=(D/'al50_extract_native_v1.py').read_text();compile(source,'extract','exec')
for n in ast.walk(ast.parse(source)):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):assert n.func.attr not in ['run','save','switchtolayout','eval']
for n in ['TRAIN_STAGE.py','ANALYZE_STAGE.py','AL50_STAGE_EVALUATION.py']:compile((D/n).read_text(),n,'exec')
tests.append({'test':'extractor_and_stage_compile_no_solver_calls','pass':True})
# Protect exact prior authority content. No oldledger rewrite.
protected=rd(old/'PROTECTED_LEDGER_SNAPSHOTS.json')
for v in protected:assert rd(v['path'])==v['content']
protected.append({'path':str(old/'AL50_SCIENCE_LEDGER.json'),'content':rd(old/'AL50_SCIENCE_LEDGER.json')})
# Explicit DOE56 authority remains unchanged.
doe=Q/'APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json';protected.append({'path':str(doe),'content':rd(doe)})
put('PROTECTED_LEDGER_SNAPSHOTS.json',protected);put('PRODUCTION_DB_BEFORE.json',{'jobs':jobs,'entries':entries})
import shared_resource_gate as resource
policy=rd(P/'shared_resource_policy.json');req=first['jobs'][0]['resource_requirements'];snapshot=resource.check(req,D,policy);put('LIVE_PREFLIGHT_RESOURCES.json',snapshot)
assert not snapshot['hold_reasons'],snapshot['hold_reasons'];tests.append({'test':'live_resource_admission_no_hold','pass':True})
firsttwo=[next(c['case_id'] for c in cases if c['selection_role']==v) for v in ['coverage','complex_disagreement']]
pkg['canary_first_two']=firsttwo;pkg['execution_order']=firsttwo+[v for v in pkg['execution_order'] if v not in firsttwo];pkg['status']='ALL_PRODUCTION_HARD_GATES_PASS';pkg['budget_proposal']['authorized_entries']=50;put('AL50_COMPLEX_PRODUCTION_MANIFEST.json',pkg)
put('REAL_EXECUTION_AUTHORITY.json',{'task':D.name,'max_entries':50,'per_case':1,'first_two':firsttwo,'V1_superseded_denied':[c['external_execution_id'] for c in rd(Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1/AL50_FAST_PRODUCTION_MANIFEST.json')['cases']],'budget_id':'AL50_COMPLEX_R03_BUDGET_PROPOSAL_V1','user_authorization':'Current explicit user task: independent new50, after all hardgatesPASS, first coverage then disagreement, canaries scientificallyvalid before remaining48','no_replay':True,'frozen_manifest':str(D/'AL50_COMPLEX_PRODUCTION_MANIFEST.json'),'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','next_batch':0})
put('PRODUCTION_HARD_GATES.json',{'status':'PASS','eight_hard_gates':{'history_dedup':'PASS','all50_freshload':'PASS','runner_identity_binding':'PASS','science_ledger':'PASS','actual_resource_gate':'PASS','frozen_material_numerics':'PASS','budget50_percase1':'PASS','removed_old_cases_denied':'PASS'},'passed':len(tests),'failed':0,'tests':tests,'new_entries':0,'fixture_only_jobs':50,'fixture_entries':0,'resource_refresh_before_each_case':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print('ALL_HARD_GATES_PASS',len(tests),firsttwo)
