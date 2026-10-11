"""Post-fit train/validation and artifact integrity audit. Never fits."""
import numpy as np
from pathlib import Path
from . import adapter as A,engine as E
from k6_v2_pipeline import contracts as C,h1
def summary(x):
 x=np.asarray(x,float);return {'median':float(np.median(x)),'q95':float(np.quantile(x,.95)),'min':float(np.min(x)),'max':float(np.max(x))}
def main():
 import torch
 torch.set_num_threads(1)
 done=A.read(A.OUT/'TRAINING_COMPLETION.json');assert done['fits_complete']==268
 ledger=A.read(A.OUT/'FIT_EXECUTION_LEDGER.json');assert len(ledger['fits'])==268 and all(q['status']=='COMPLETE' for q in ledger['fits'].values())
 col=A.load_collection(False);by={c.case_id:c for c in col.cases};plan=A.build_plan();records=[];art=[];reload_max=0.
 # Full current-byte verification of every saved model/checkpoint/prediction/trajectory.
 for tid,row in ledger['fits'].items():
  task=E.FitTask(**{**row['task'],'train_case_ids':tuple(row['task']['train_case_ids']),'prediction_case_ids':tuple(row['task']['prediction_case_ids'])})
  out=A.OUT/'models'/task.phase/tid;m=A.read(out/'fit_manifest.json')
  assert A.sha(out/'fit_manifest.json')==row['fit_manifest_sha256']
  for name,digest in m['artifact_sha256'].items():
   if digest is not None:
    p=out/name;assert A.sha(p)==digest;art.append({'fit_id':tid,'path':str(p),'sha256':digest,'bytes':p.stat().st_size})
  assert m['normalization']['target']['c_shared_rms']>0 and m['normalization']['target']['log_p_std']>0
  assert m['task']['train_case_ids']==row['preprocessing_case_ids'];assert row['reload']['absolute_delta_C_hat']==row['reload']['absolute_delta_P_scale']==0
  if task.phase not in ('learning_curve','final'):continue
  run=E._load_cached_fit(task,out,m['data_sha256']);ids=task.train_case_ids;xx=np.array([by[c].ordered_D_nm for c in ids],float);ct=np.array([by[c].c_hat for c in ids]);pt=np.array([by[c].p_scale for c in ids]);pred,ps=E.predict_fit_run(run,xx)
  if task.phase=='final':
   pp=out/'DEVELOPMENT_TRAIN_PREDICTIONS.npz'
   np.savez_compressed(pp,case_ids=np.array(ids),C_hat_real=pred.real,C_hat_imag=pred.imag,P_scale=ps)
   art.append({'fit_id':tid,'path':str(pp),'sha256':A.sha(pp),'bytes':pp.stat().st_size,'purpose':'saved final156 training predictions, not held-out evaluation'})
  state=np.linalg.norm((pred-ct).reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
  scale=np.linalg.norm(ps-pt,axis=1)/np.linalg.norm(pt,axis=1)
  ratio=np.linalg.norm(pred.reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
  Y=np.concatenate([C.pack_model_target(by[c].c_hat,by[c].p_scale) for c in ids]);trainmean=np.repeat(run.target_scaler.c_mean[None],len(ids),0).reshape(len(ids),21,7,2,2);mc=trainmean[...,0]+1j*trainmean[...,1]
  const=np.linalg.norm((mc-ct).reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
  records.append({'task':row['task'],'normalized_training_loss':run.training_loss,'actual_updates':run.actual_updates,'selected_update':run.best_update,'train_state_relative_RMSE':summary(state),'train_state_norm_ratio':summary(ratio),'train_P_scale_relative_RMSE':summary(scale),'constant_train_mean_state_relative_RMSE':summary(const),'not_heldout_H1':'descriptive training errors only, no admission conclusion'})
 A.write(A.OUT/'TRAIN_VS_HELDOUT_DIAGNOSTIC.json',{'fits':records,'no_additional_fits':True,'final_training_data':'156 development groups, not independent validation'})
 A.write(A.OUT/'MODEL_ARTIFACTS_AND_SHA.json',{'artifacts':art,'fits_verified':268,'reload_max_abs_delta':reload_max,'checkpoint_bytes':sum(q['bytes'] for q in art),'no_corrupt_or_missing_artifacts':True,'fit_budget_ledger_sha256':A.sha(A.OUT/'FIT_EXECUTION_LEDGER.json')})
 A.write(A.OUT/'EXECUTION_COUNTS_FINAL.json',{'CPU_logical_fits':268,'internal_KRR_heads':'one logical fit contains state and log-P_scale heads, not standalone scientific P_scale fits','inner_KRR':108,'inner_MLP':108,'curve_KRR':12,'curve_MLP':36,'final_KRR':1,'final_MLP':3,'local_fits':0,'NP_fits':0,'FDTD':0,'GPU_solver':0,'replay':0,'confirmation_response_access':0,'standalone_P_scale_fits':0,'extra_synthetic_fits':0})
 # Descriptive phase-roughness and support-distance associations, not new inputs/gates.
 result={};seed_diagnostics={};meta={q['case_id']:q for q in A.inventory()['cases']}
 for kind in ['RBF_KRR','CARTESIAN_MLP']:
  for size in [32,64,124]:
   key=f'{kind}_n{size}'
   with np.load(A.OUT/(key+'_OOF_PREDICTIONS.npz'),allow_pickle=False) as z:ids=z['case_ids'].tolist();cps=z['C_hat_real']+1j*z['C_hat_imag'];pps=z['P_scale'];cp=cps.mean(0)
   ct=np.array([by[c].c_hat for c in ids]);err=np.linalg.norm((cp-ct).reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
   power=abs(ct)**2;mask=power/power.sum((2,3),keepdims=True)>=1e-4;increment=np.angle(ct[:,1:]*np.conj(ct[:,:-1]));weight=np.sqrt(power[:,1:]*power[:,:-1])*mask[:,1:]*mask[:,:-1]
   rough=np.sqrt((weight*increment**2).sum((1,2,3))/weight.sum((1,2,3)))
   distances=[]
   for c in ids:
    fold=next(f for f in range(1,5) if c in plan.outer_validation_ids[f]);task=next(t for t in plan.curve_templates if t.outer_fold==fold and t.training_geometry_count==size and t.model_kind==kind)
    xx=np.array([by[q].ordered_D_nm for q in task.train_case_ids]);distances.append(float(np.linalg.norm((xx-np.array(by[c].ordered_D_nm))/130.,axis=1).min()))
   result[key]={'per_geometry':[{'case_id':c,'state_error':float(e),'circular_spectral_phase_increment_RMS_rad_per_1nm':float(q),'nearest_refit_geometry_distance_normalized_130nm':float(d),'stratum':meta[c]['stratum']} for c,e,q,d in zip(ids,err,rough,distances)],'state_vs_spectral_phase_increment_pearson':float(np.corrcoef(err,rough)[0,1]),'state_vs_support_distance_pearson':float(np.corrcoef(err,distances)[0,1]),'interpretation':'Post-hoc descriptive correlation only, not causality. Wrapped adjacent 1nm phase increments are not unaliased derivatives. Support distance never enters training or selection.'}
   pt=np.array([by[c].p_scale for c in ids]);eta=np.array([by[c].eta for c in ids]);ab=np.array([by[c].absolute_order for c in ids]);norms=np.linalg.norm(cps.reshape(len(cps),len(ids),-1),axis=2);after=np.linalg.norm(cp.reshape(len(ids),-1),axis=1);truthnorm=np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
   seed_diagnostics[key]={'per_seed':[h1.evaluate_original_h1(ct,cps[i],pt,pps[i],eta,ab) for i in range(len(cps))],'aggregation_per_geometry':[{'case_id':c,'truth_C_hat_norm':float(t),'mean_seed_C_hat_norm_before':float(before),'complex_mean_C_hat_norm_after':float(n),'after_over_before':float(n/before)} for c,t,before,n in zip(ids,truthnorm,norms.mean(0),after)],'interpretation':'Per-seed single-candidate seed-stability is N/A; original three-seed aggregate H1 in H1_H2_FINAL_EVALUATION remains authoritative; no candidate reselection'}
 A.write(A.OUT/'POSTHOC_SPECTRAL_AND_COVERAGE_ASSOCIATIONS.json',result)
 A.write(A.OUT/'PER_SEED_AND_AGGREGATION_DETAIL.json',seed_diagnostics)
 A.write(A.OUT/'ORIGINAL_H1_GATE_THRESHOLDS.json',h1.load_h1_authority())
 print('POST_AUDIT_PASS',len(art),sum(q['bytes'] for q in art),flush=True)
