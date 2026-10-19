from pathlib import Path
import json,sqlite3,sys,importlib.util,ast,copy,hashlib,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
package=read(D/'AL50_FAST_PRODUCTION_MANIFEST.json');cases=package['cases'];assert len(cases)==50 and len(set(c['external_execution_id'] for c in cases))==50
sys.path[:0]=[str(P),str(R/'scripts/coupling_ml')];s=importlib.util.spec_from_file_location('al50_frozen_runner',P/'minimal_batch_runner_v3.1_final.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
fix=D/'offline_interface_fixture';fix.mkdir();runner=m.MinimalBatchRunner(db_path=fix/'SCHEMA_ONLY_ZERO_ENTRY.sqlite',output_dir=fix/'unused_output',lock_path=fix/'UNUSED.lock');tests=[]
for c,b in zip(cases,package['runner_batches']):
 assert hashlib.sha256(Path(c['input_fsp']).read_bytes()).hexdigest()==c['source_fsp_sha256']
 ok,msg=runner.submit_batch(b['manifest']);assert ok,msg;tests.append({'test':c['case_id']+'_input_and_installed_submit','pass':True})
first=read(package['runner_batches'][0]['manifest']);bad=copy.deepcopy(first);bad['batch_name']+='__DUPLICATE_FIXTURE';bp=fix/'duplicate_fixture.json';bp.write_text(json.dumps(bad),encoding='utf-8');ok,msg=runner.submit_batch(bp);assert not ok and 'UNIQUE' in msg;tests.append({'test':'crossbatch_duplicate_execution_rejected','pass':True})
bad=copy.deepcopy(first);bad['batch_name']+='__WRONG_SHA_FIXTURE';bad['jobs'][0]['source_fsp_sha256']='0'*64;bp=fix/'wrongsha_fixture.json';bp.write_text(json.dumps(bad),encoding='utf-8');ok,msg=runner.submit_batch(bp);assert not ok and 'SHA256' in msg;tests.append({'test':'invalid_sha_rejected','pass':True})
c=sqlite3.connect(fix/'SCHEMA_ONLY_ZERO_ENTRY.sqlite');assert c.execute('select count(*) from jobs').fetchone()[0]==50 and c.execute('select count(*) from solver_entries').fetchone()[0]==0;c.close();tests.append({'test':'fixture_entries_zero','pass':True})
source=(D/'al50_extract_native_v1.py').read_text(encoding='utf-8');compile(source,'al50_extract_native_v1.py','exec')
for n in ast.walk(ast.parse(source)):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):assert n.func.attr not in ['run','save','switchtolayout','eval']
sp=importlib.util.spec_from_file_location('al50_extractor',D/'al50_extract_native_v1.py');e=importlib.util.module_from_spec(sp);sp.loader.exec_module(e);assert callable(e.extract);tests.append({'test':'native_extractor_import_and_solver_forbidden_AST','pass':True})
# Independent zero-fit reevaluation of saved172G OOF on exactsame124heldout identities.
s=importlib.util.spec_from_file_location('al50_reuse_metrics',R/'scripts/coupling_ml/gpu_active_learning_mainline_v1.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);data=np.load(AL/'ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);oof=np.load(AL/'ML_UPDATE/OOF_PREDICTIONS.npz',allow_pickle=False);ids=list(data['case_ids']);idx={s:i for i,s in enumerate(ids)};folds=read(AL/'ML_UPDATE/FOLDS.json');before=read(A/'MODEL_METRICS.json');reported=read(AL/'ML_UPDATE/MODEL_MAE_RANKING_BEFORE_AFTER.json');vi=np.array([idx[s] for f in folds for s in f['heldout_old_ids']]);y=np.c_[data['eta'],np.log(data['P_scale'])];audit={}
for k in ['Mean','KRR','ExtraTrees','MLP']:
 pred=oof[k];actual=M.evaluate(y[vi],pred[vi],data['P_plus1_H2'][vi]);audit[k]={}
 for t in ['eta','P_scale','P_plus1_H2']:
  rhos=[]
  for f in folds:
   val=np.array([idx[s] for s in f['heldout_old_ids']]);fm=M.evaluate(y[val],pred[val],data['P_plus1_H2'][val]);rr=fm[t]['450nm']['Spearman']
   if rr is not None:rhos.append(rr)
  rho=float(np.mean(rhos)) if rhos else None;rep=reported[k][t];assert abs(actual[t]['MAE']-rep['MAE_after_same124'])<1e-12 and abs(before[k][t]['MAE']-rep['MAE_before'])<1e-12
  assert (rho is None and rep['mean_fold_Spearman_after'] is None) or abs(rho-rep['mean_fold_Spearman_after'])<1e-12
  audit[k][t]={'MAE_before':rep['MAE_before'],'MAE_after_verified':actual[t]['MAE'],'rho_before':rep['mean_fold_Spearman_before'],'rho_after_verified':rho}
put('AL16_MODEL_METRIC_RECHECK_ZERO_FIT.json',{'status':'PASS_SAME124_SPLITS_AND_DEFINITION','results':audit,'new_fits':0,'before_topk_or_pooled_OOF':'Unavailable historically, not invented/refit','reused_OOF':str(AL/'ML_UPDATE/OOF_PREDICTIONS.npz')});tests.append({'test':'AL16_metrics_same124_zero_fit_recompute','pass':True})
con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(r) for r in con.execute('select * from jobs')];entries=[dict(r) for r in con.execute('select * from solver_entries')];con.close();prior=read(D/'DEDUPLICATION_AUDIT.json');assert jobs==prior['canonical_jobs'] and entries==prior['canonical_entries'];assert not any(j.get('external_execution_id') in {c['external_execution_id'] for c in cases} for j in jobs)
put('OFFLINE_INTERFACE_ACCEPTANCE.json',{'passed':len(tests),'failed':0,'tests':tests,'real_or_fake_run_called':False,'fixture_jobs':50,'fixture_entries':0,'production_db_unchanged':True,'AL50_production_submitted':0,'new_native_outputs_available':False,'scope':'Input/manifest/identity/importwiring offlinePASS; prospective50physicsvalidity only after separatelyauthorizedrealruns'})
print('AL50_OFFLINE_PASS',len(tests));print('COVERAGE',json.dumps(read(D/'COVERAGE_AND_SPARSE_DIMENSIONS.json')));print('PREP',json.dumps(read(D/'PREPARATION_AUDIT.json')))
