"""Frozen H1/H2 development evaluation, no fitted models or confirmation truth."""
import json,csv,datetime
from pathlib import Path
import numpy as np
from . import adapter as A,engine as E
from k6_v2_pipeline import h1,ingest,contracts as C
def summary(x):
 x=np.asarray(x,float);return {'median':float(np.median(x)),'q95':float(np.quantile(x,.95)),'worst':float(np.max(x)),'mean':float(np.mean(x))}
def diagnostics(truth,pred,ids,meta):
 # Fixed diagnostic rules: no alignment/rescaling. Truth amplitude squared weights.
 sq=abs(truth)**2;err=abs(pred-truth)**2;norm=np.sqrt(sq.sum((1,2,3)));pnorm=np.linalg.norm(pred.reshape(len(pred),-1),axis=1)
 phase=np.angle(pred*np.conj(truth));frac=sq/sq.sum((2,3),keepdims=True);mask=frac>=1e-4
 ph=np.sqrt((sq*phase**2*mask).sum((1,2,3))/(sq*mask).sum((1,2,3)))
 predsq=abs(pred)**2;predph=np.sqrt((predsq*phase**2*mask).sum((1,2,3))/(predsq*mask).sum((1,2,3)))
 phase_defined=(abs(pred)>np.finfo(float).eps);coverage=(sq*mask*phase_defined).sum((1,2,3))/(sq*mask).sum((1,2,3))
 rel_num=np.zeros(len(ids));rel_den=np.zeros(len(ids))
 for i in range(7):
  for j in range(i+1,7):
   delta=np.angle(pred[:,:,i,:]*np.conj(pred[:,:,j,:])*np.conj(truth[:,:,i,:])*truth[:,:,j,:])
   w=abs(truth[:,:,i,:])*abs(truth[:,:,j,:]);use=mask[:,:,i,:]&mask[:,:,j,:]
   rel_num+=(w*delta**2*use).sum((1,2));rel_den+=(w*use).sum((1,2))
 relative=np.sqrt(np.divide(rel_num,rel_den,out=np.zeros_like(rel_num),where=rel_den>0))
 wr=np.sqrt(err.sum((2,3))/sq.sum((2,3)));order=np.sqrt(err.sum((1,3))/sq.sum((1,3)));pol=np.sqrt(err.sum((1,2))/sq.sum((1,2)))
 rows=[]
 for k,cid in enumerate(ids):
  rows.append({'case_id':cid,'role':meta[cid]['role'],'stratum':meta[cid]['stratum'],'state_norm_ratio':float(pnorm[k]/norm[k]),'zero_prediction_relative_RMSE':1.,'state_relative_RMSE':float(np.sqrt(err[k].sum()/sq[k].sum())),'amplitude_relative_RMSE':float(np.linalg.norm(abs(pred[k])-abs(truth[k]))/norm[k]),'truth_weighted_significant_absolute_phase_RMSE_rad':float(ph[k]),'prediction_weighted_same_mask_absolute_phase_RMSE_rad':float(predph[k]),'significant_truth_phase_coverage':float(coverage[k]),'truth_weighted_cross_order_relative_phase_RMSE_rad':float(relative[k]),'relative_phase_weight_present':bool(rel_den[k]>0),'wavelength_state_relative_RMSE':wr[k].tolist(),'order_state_relative_RMSE':order[k].tolist(),'polarization_state_relative_RMSE':pol[k].tolist()})
 wi=np.unravel_index(np.argmax(wr),wr.shape);oi=np.unravel_index(np.argmax(order),order.shape)
 return {'norm_ratio':summary(pnorm/norm),'amplitude_relative_RMSE':summary([q['amplitude_relative_RMSE'] for q in rows]),'truth_weighted_phase_RMSE':summary(ph),'prediction_weighted_phase_RMSE':summary(predph),'relative_phase_RMSE':summary(relative),'weighting_caution':'Prediction-weight changes are not phase prediction changes. Undefined prediction phases have explicit truth-weight coverage. Relative-phase all order pairs within each polarization, pair-amplitude weight; significant truth mask per wavelength >=1e-4. No oracle phase alignment.','phase_rules':'diagnostic only, no H1 gates added or altered','error_energy_fraction_by_order':(err.sum((0,1,3))/err.sum()).tolist(),'error_energy_fraction_TE_TM':(err.sum((0,1,2))/err.sum()).tolist(),'error_energy_fraction_by_wavelength':(err.sum((0,2,3))/err.sum()).tolist(),'worst_wavelength':{'case_id':ids[wi[0]],'wavelength_nm':440+wi[1],'relative_RMSE':float(wr[wi])},'worst_order':{'case_id':ids[oi[0]],'m':int(oi[1]-3),'relative_RMSE':float(order[oi])},'geometry_rows':rows,'strata':{s:{'count':sum(q['stratum']==s for q in rows),'state':summary([q['state_relative_RMSE'] for q in rows if q['stratum']==s]),'norm_ratio':summary([q['state_norm_ratio'] for q in rows if q['stratum']==s])} for s in sorted({q['stratum'] for q in rows})}}
def main(col,plan,refits):
 by={c.case_id:c for c in col.cases};meta={q['case_id']:q for q in A.inventory()['cases']};results={};allpred={};audits={};dec=h1.load_h2_decoder()
 ids=tuple(cid for f in range(1,5) for cid in plan.outer_validation_ids[f]);assert len(ids)==len(set(ids))==124 and all(by[c].role!=C.ROLE_OLD32 for c in ids)
 ct=np.array([by[c].c_hat for c in ids]);pt=np.array([by[c].p_scale for c in ids]);eta=np.array([by[c].eta for c in ids]);absolute=np.array([by[c].absolute_order for c in ids])
 for kind in ['RBF_KRR','CARTESIAN_MLP']:
  results[kind]={}
  for n in [32,64,124]:
   seeds=[None] if kind=='RBF_KRR' else [0,1,2];cp=[];pp=[];fold_results={}
   for seed in seeds:
    cc=[];ps=[]
    for f in range(1,5):
     run=next(run for run in refits if run.task.phase=='learning_curve' and run.task.model_kind==kind and run.task.training_geometry_count==n and run.task.outer_fold==f and run.task.seed==seed)
     assert run.prediction_case_ids==plan.outer_validation_ids[f];cc.append(run.predicted_c_hat);ps.append(run.predicted_p_scale)
    cp.append(np.concatenate(cc));pp.append(np.concatenate(ps))
   cp=np.array(cp);pp=np.array(pp);key=f'{kind}_n{n}'
   report=h1.evaluate_original_h1(ct,cp,pt,pp,eta,absolute,dec)
   for f in range(1,5):
    ix=[k for k,c in enumerate(ids) if c in plan.outer_validation_ids[f]]
    fold_results[str(f)]=h1.evaluate_original_h1(ct[ix],cp[:,ix],pt[ix],pp[:,ix],eta[ix],absolute[ix],dec)
   report.update(model=kind,refit_geometry_count=n,validation_geometry_count=124,validation_identity_scope='124 surviving new development geometries; original old32 train-only, historically exposed',folds=fold_results,selection_visible_outer_train_counts=[124,125,126,125],claim='development only; no independent confirmation or production admission')
   results[kind][str(n)]=report
   diag=diagnostics(ct,cp.mean(0),ids,meta);diag['per_seed']=[diagnostics(ct,c,ids,meta) for c in cp];audits[key]=diag
   per=[]
   for cid,row,dg in zip(ids,report['aggregate']['per_geometry'],diag['geometry_rows']):per.append({'case_id':cid,**row,**{k:v for k,v in dg.items() if not isinstance(v,list)}})
   A.write(A.OUT/f'{key}_PER_GEOMETRY.json',per)
   np.savez_compressed(A.OUT/f'{key}_OOF_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=pp)
   allpred[key]=(cp,pp)
  A.write(A.OUT/('KRR_LEARNING_CURVE_RESULTS.json' if kind=='RBF_KRR' else 'MLP_LEARNING_CURVE_RESULTS.json'),results[kind])
 comparison={}
 for n in [32,64,124]:
  ka=results['RBF_KRR'][str(n)]['aggregate']['per_geometry'];ma=results['CARTESIAN_MLP'][str(n)]['aggregate']['per_geometry'];entry={}
  for k in ka[0]:
   a=np.array([q[k] for q in ka]);b=np.array([q[k] for q in ma]);entry[k]={'MLP_minus_KRR':summary(b-a),'MLP_wins':int((b<a).sum()),'MLP_losses':int((b>a).sum()),'per_geometry_delta':[{'case_id':c,'delta':float(v)} for c,v in zip(ids,b-a)]}
  comparison[str(n)]=entry
 curve_deltas={}
 for kind in results:
  a=np.array([q['state_relative_rmse'] for q in results[kind]['32']['aggregate']['per_geometry']]);b=np.array([q['state_relative_rmse'] for q in results[kind]['124']['aggregate']['per_geometry']]);curve_deltas[kind]={'124_minus32':summary(b-a),'improved':int((b<a).sum()),'worsened':int((b>a).sum()),'by_fold':{str(f):summary((b-a)[[k for k,c in enumerate(ids) if c in plan.outer_validation_ids[f]]]) for f in range(1,5)},'no_p_value':'Correlated nested folds/scales and seeds; geometry is independent unit; no wavelength-times-seed significance claim'}
 A.write(A.OUT/'PAIRED_MODEL_COMPARISON.json',{'matched_geometry_ids':list(ids),'model_deltas':comparison,'learning_curve_deltas':curve_deltas,'old65G_comparability':'different validation IDs/scope; not paired causal improvement'})
 A.write(A.OUT/'ERROR_MODE_AND_NORM_AUDIT.json',audits)
 A.write(A.OUT/'H1_H2_FINAL_EVALUATION.json',{'evaluations':results,'unchanged_h1_sha256':C.H1_AUTHORITY_SHA256,'unchanged_h2_sha256':C.H2_DECODER_SHA256,'development_status':{kind:('DEVELOPMENT_H1_PASS' if r['124']['all_applicable_numeric_gates_attained'] else 'DEVELOPMENT_H1_FAIL') for kind,r in results.items()},'P_scale_equals_total_power_reason':'frozen H2 total_power = predicted physical P_scale; state modal powers are normalized into routing, absolute_order=eta*P_scale','independent_confirmation':False,'production_admission':False})
 # Freeze final geometry-only predictions. No confirmation-response loader is called.
 reg=ingest.load_frozen_case_registry(A.ROOT);confirm=[(cid,row) for cid,row in sorted(reg.confirmation.items()) if row['role'] not in ('CONFIRMATION_LOCAL_COMBO',) and 'LOCAL' not in row['role']]
 assert len(confirm)==28
 freeze=[]
 for kind in ['RBF_KRR','CARTESIAN_MLP']:
  runs=[run for run in refits if run.task.phase=='final' and run.task.model_kind==kind];xx=np.array([q['ordered_D_nm'] for cid,q in confirm],float)
  pr=[E.predict_fit_run(run,xx) for run in runs];cc=np.array([q[0] for q in pr]);ps=np.array([q[1] for q in pr]);p=A.OUT/f'FINAL_{kind}_SEALED_GEOMETRY_ONLY_PREDICTIONS.npz'
  np.savez_compressed(p,case_ids=np.array([cid for cid,q in confirm]),C_hat_real=cc.real,C_hat_imag=cc.imag,P_scale=ps,C_hat_seed_mean_real=cc.mean(0).real,C_hat_seed_mean_imag=cc.mean(0).imag,P_scale_physical_seed_mean=ps.mean(0))
  freeze.append({'model':kind,'prediction_path':str(p),'sha256':A.sha(p),'purpose':'geometry-only predictions frozen, not confirmation evaluation','confirmation_response_access':0,'model_files':[{'path':str(A.OUT/'models/final'/run.task.task_id/'fit_manifest.json'),'sha256':A.sha(A.OUT/'models/final'/run.task.task_id/'fit_manifest.json')} for run in runs]})
 A.write(A.OUT/'FINAL_MODEL_AND_PREDICTION_FREEZE.json',{'models':freeze,'evaluator_source_sha256':A.sha(Path(h1.__file__)),'gate_sha256':C.H1_AUTHORITY_SHA256,'28_global_confirmation_responses': 'SEALED_NOT_ACCESSED','4_local_confirmation':'SEALED_NO_MODEL_NO_PREDICTION; local13 SUSPENDED','new_confirmation_HF':0})
 A.write(A.OUT/'LOCAL13_FIT_SUSPENSION_RECORD.json',{'status':'SUSPENDED','missing':'K6LDA1_DEV_D6_M05','local_fits':0,'confirmation4':'sealed','NP88D_two_fits':'PENDING_NOT_EXECUTED','fits_not_in268':2})
 print('H1_RESULT',json.dumps({k:{n:{'state':r['aggregate']['metrics']['state_relative_rmse'],'gates':r['gates']} for n,r in v.items()} for k,v in results.items()}),flush=True)
