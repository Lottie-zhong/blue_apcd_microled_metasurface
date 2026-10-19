from pathlib import Path
import runpy,json,time,warnings
import numpy as np,joblib
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');p=R/'scripts/coupling_ml/gpu_active_learning_mainline_v1.py'
t=p.read_text();t=t.replace("assert np.array_equal(m.predict(x[:3]),joblib.load(p).predict(x[:3]))","assert np.allclose(m.predict(x[:3]),joblib.load(p).predict(x[:3]),rtol=1e-12,atol=1e-12)")
t=t.replace(" (O/'models').mkdir(exist_ok=True);final=[]"," np.savez_compressed(O/'TRAINING_DATA_AND_OOF.npz',case_ids=ids,roles=roles,D_nm=x,eta=eta,P_scale=ps,P_plus1_H2=ab,heldout=vi,**oof,**{k+'_sd':v for k,v in sd.items()})\n put('FOLDS.json',folds);put('MODEL_METRICS.json',summary);put('UNCERTAINTY.json',uncertainty)\n (O/'models').mkdir(exist_ok=True);final=[]")
p.write_text(t,encoding='utf-8');ns=runpy.run_path(str(p));O=ns['O'];put=ns['put'];A=ns['A'];C=ns['C'];h1=ns['h1']
ledger=json.loads((O/'FIT_LEDGER.json').read_text());assert all(z['state']=='COMPLETE' for z in ledger)
cs=A.load_collection(False).training_cases();x=np.array([c.ordered_D_nm for c in cs]);ids=np.array([c.case_id for c in cs]);roles=np.array([c.role for c in cs]);eta=np.array([c.eta[:,4] for c in cs]);ps=np.array([c.p_scale for c in cs]);ab=h1.reconstruct_h2(np.array([c.c_hat for c in cs]),ps,h1.load_h2_decoder())['absolute_order'][:,:,4];y=np.c_[eta,np.log(ps)]
specs=[('Mean',17),('KRR',17)]+[(k,s) for k in ['ExtraTrees','MLP'] for s in [17,29,43]];done={z['id'] for z in ledger};final=[]
with threadpool_limits(limits=2):
 for k,s in specs:
  tag=f'final/{k}/seed{s}';path=O/f'models/{k}_{s}.joblib'
  if tag in done:
   assert path.exists();m=joblib.load(path)
  else:
   m=ns['make'](k,s);row={'id':tag,'n_train':156,'state':'STARTED'};ledger.append(row);put('FIT_LEDGER.json',ledger);start=time.perf_counter()
   with warnings.catch_warnings(record=True) as ws:warnings.simplefilter('always');m.fit(x,y)
   row.update(state='COMPLETE',seconds=time.perf_counter()-start,warnings=[str(z.message) for z in ws]);put('FIT_LEDGER.json',ledger);joblib.dump(m,path)
  a=m.predict(x);b=joblib.load(path).predict(x);assert np.allclose(a,b,rtol=1e-12,atol=1e-12);final.append({'kind':k,'seed':s,'path':str(path),'reload_max_abs_delta':float(np.max(np.abs(a-b)))})
assert len(ledger)==104
curves=json.loads((O/'LEARNING_CURVES.json').read_text());summary={}
for k,_ in specs:
 if k in summary:continue
 rows=[curves[f'fold{f}/n{156-len(A.build_plan().outer_validation_ids[f])}'][k] for f in range(1,5)];weights=np.array([len(A.build_plan().outer_validation_ids[f]) for f in range(1,5)]);out={}
 for target in ['eta','log_P_scale','P_scale','P_plus1_H2']:
  out[target]={m:float(np.average([r['metrics'][target][m]**(2 if m=='RMSE' else 1) for r in rows],weights=weights)**(.5 if m=='RMSE' else 1)) for m in ['MAE','RMSE']}
  if target!='log_P_scale':out[target]['450nm']={m:float(np.average([r['metrics'][target]['450nm'][m]**(2 if m=='RMSE' else 1) for r in rows],weights=weights)**(.5 if m=='RMSE' else 1)) for m in ['MAE','RMSE']};out[target]['450nm']['mean_fold_Spearman']=float(np.mean([r['metrics'][target]['450nm']['Spearman'] for r in rows if r['metrics'][target]['450nm']['Spearman'] is not None])) if k!='Mean' else None
 out['mean_fold_seed_prediction_sd']=float(np.mean([r['seed_prediction_sd'] for r in rows]));summary[k]=out
np.savez_compressed(O/'TRAINING_DATA.npz',case_ids=ids,roles=roles,D_nm=x,eta=eta,P_scale=ps,P_plus1_H2=ab)
put('MODEL_METRICS.json',summary);put('FINAL_MODELS.json',final);put('FOLDS.json',[{'fold':f,'heldout_ids':A.build_plan().outer_validation_ids[f]} for f in range(1,5)])
put('RECOVERY_AUDIT.json',{'failure':'post-fit exact float reload equality for multithreaded ExtraTrees; predictions differ only reduction rounding; fixed tolerant1e-12 check','completed_fits_replayed':0,'original_completed_at_failure':len(done),'new_remaining_fits':104-len(done),'limitation':'original OOF arrays were in memory and lost on assertion; all per-fold metrics and curves persisted; summary reconstructs exact weighted MAE/RMSE and mean within-fold Spearman; no pooled ranking or uncertainty-error calibration asserted','future_checkpoint_fix':True})
put('UNCERTAINTY.json',{'kind':'raw seed and intermodel dispersion; not calibrated','heldout_seed_sd':{k:v['mean_fold_seed_prediction_sd'] for k,v in summary.items()},'heldout_uncertainty_error_association':'NOT_AVAILABLE_OOF_CHECKPOINT_LOST; no refits to reconstruct','not_a_confidence_interval':True})
put('TRAINING_COMPLETE.json',{'fits':104,'fit_wall_seconds_sum':sum(z['seconds'] for z in ledger),'warning_fits':sum(bool(z['warnings']) for z in ledger),'heldout_geometries':124,'real_entries':0,'FDTD':0,'sealed_responses':0,'replayed_fits':0})
print('RECOVERED',json.dumps(summary),flush=True)
