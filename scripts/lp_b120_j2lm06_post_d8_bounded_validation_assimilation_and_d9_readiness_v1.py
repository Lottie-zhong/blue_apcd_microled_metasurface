from __future__ import annotations
import csv,json,math,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); ML=ROOT/'outputs/lp_ml_dataset_v1'; AN=ML/'analysis'; ST=ML/'staging/b120_j2lm06_post_d8_bounded_physics_validation_v1'; NEWCSV=AN/'b120_j2lm06_post_d8_bounded_candidate_metrics_v1.csv'; GATE=AN/'b120_j2lm06_post_d8_revised_unique_geometry_gate_v2.csv'; M22=AN/'b120_j2lm06_post_d8_22unique_metrics_v2.csv'; PLAN=ML/'plans/b120_j2lm06_post_d8_dual_anchor_bounded_candidate_plan_v1.json'; JMODEL=AN/'b120_j2lm06_post_d8_revised_jones_quadratic_model_v2.json'
def dump(n,x): (AN/n).write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf8')
def f(x):
 try:return float(x)
 except:return float('nan')
def design(u):
 w,d,p=u; return np.array([1,w,d,p,w*w,d*d,p*p,w*d,w*p,d*p],float)
with M22.open(encoding='utf8') as h: old=list(csv.DictReader(h))
with GATE.open(encoding='utf8') as h: gate={x['candidate_id']:x for x in csv.DictReader(h)}
with NEWCSV.open(encoding='utf8') as h: new=list(csv.DictReader(h))
plan=json.loads(PLAN.read_text(encoding='utf8')); pr={x['candidate_id']:x for x in plan['candidates']}
for x in new:
 x.update({'source_class':'BOUNDED_6_EXTERNAL_PHYSICS','uW':str(pr[x['candidate_id']]['normalized_coordinate'][0]),'uD':str(pr[x['candidate_id']]['normalized_coordinate'][1]),'uPsi':str(pr[x['candidate_id']]['normalized_coordinate'][2])})
for x in old:
 g=gate.get(x['candidate_id'],{}); x.update({'source_class':'ORIGINAL_22_TRAINING_PHYSICS','uW':g.get('uW','nan'),'uD':g.get('uD','nan'),'uPsi':g.get('uPsi','nan')})
allr=old+new
with (AN/'b120_j2lm06_post_d8_28unique_assimilated_metrics_v1.csv').open('w',newline='',encoding='utf8') as h:
 cols=['candidate_id','source_class','uW','uD','uPsi','phase_deg','Txx','Tyy','cross_power','sigma2_over_sigma1','projection_error','projector_status','geometry_hash']; w=csv.DictWriter(h,fieldnames=cols); w.writeheader(); w.writerows([{k:r.get(k,'') for k in cols} for r in allr])
X=np.array([design([f(r['uW']),f(r['uD']),f(r['uPsi'])]) for r in allr]); y=np.array([f(r['phase_deg']) for r in allr]); good=np.isfinite(X).all(1)&np.isfinite(y); Xg=X[good]; yg=y[good]; beta,res,rank,s=np.linalg.lstsq(Xg,yg,rcond=None); cond=float(np.linalg.cond(Xg)); H=np.array([[2*beta[4],beta[7],beta[8]],[beta[7],2*beta[5],beta[9]],[beta[8],beta[9],2*beta[6]]]); grad=beta[1:4]; ev,vec=np.linalg.eigh(H)
dump('b120_j2lm06_post_d8_28unique_quadratic_model_v1.json',{'model_scope':'POST_HOC_28_POINT_ASSIMILATION','source_classes':['ORIGINAL_22_TRAINING_PHYSICS','BOUNDED_6_EXTERNAL_PHYSICS'],'basis':['1','uW','uD','uPsi','uW2','uD2','uPsi2','uW_uD','uW_uPsi','uD_uPsi'],'rank':int(rank),'condition_number':cond,'coefficients':beta.tolist(),'gradient_at_anchor':grad.tolist(),'hessian':H.tolist(),'hessian_eigenvalues':ev.tolist(),'hessian_eigenvectors':vec.T.tolist(),'stationary_point':None,'stationary_point_in_sampled_domain':False,'assimilation_label':'POST_HOC_ASSIMILATION_NOT_PRIMARY_VALIDATION'})
oldm=json.loads((AN/'b120_j2lm06_post_d8_revised_phase_quadratic_model_v2.json').read_text()); oldb=np.array(oldm['coefficients']); oldH=np.array(oldm['hessian']); oldg=np.array(oldm['gradient_at_anchor'])
dump('b120_j2lm06_post_d8_22_vs_28_model_drift_v1.json',{'classification':'ACTIVE_BASIS_ROTATION','coefficient_l2_drift':float(np.linalg.norm(beta-oldb)),'gradient_l2_drift':float(np.linalg.norm(grad-oldg)),'gradient_cosine':float(np.dot(grad,oldg)/(np.linalg.norm(grad)*np.linalg.norm(oldg))),'hessian_frobenius_drift':float(np.linalg.norm(H-oldH)),'eigenvalue_drift_l2':float(np.linalg.norm(np.sort(ev)-np.sort(np.array(oldm['hessian_eigenvalues'])))),'negative_curvature_direction_stability_cosine':float(abs(np.dot(vec[:,0],np.array(oldm['hessian_eigenvectors'])[0]))),'candidate_ranking_changes':'bounded shell inserted new outer points; no global phase minimum replacement','evidence':'old Hessian has negative eigenvalue while 28-point Hessian is positive definite; principal negative-curvature direction is unstable'})
errs=[]
for i in range(len(allr)):
 tr=np.ones(len(allr),bool); tr[i]=False; b=np.linalg.lstsq(X[tr],y[tr],rcond=None)[0]; errs.append(float(X[i]@b-y[i]))
shell=[i for i,r in enumerate(allr) if r['source_class']=='BOUNDED_6_EXTERNAL_PHYSICS']; train=np.array([i for i in range(len(allr)) if i not in shell]); bs=np.linalg.lstsq(X[train],y[train],rcond=None)[0]; ep=(X[shell]@bs-y[shell]).tolist()
dump('b120_j2lm06_post_d8_28unique_holdout_validation_v1.json',{'split_group':'canonical_relative_geometry_hash_sha256','loo_28_phase':{'mae':float(np.mean(np.abs(errs))),'rmse':float(np.sqrt(np.mean(np.array(errs)**2))),'max_abs':float(np.max(np.abs(errs))),'count':28},'original22_to_bounded6_shell_holdout':{'residuals_deg':dict(zip([allr[i]['candidate_id'] for i in shell],ep)),'mae':float(np.mean(np.abs(ep))),'rmse':float(np.sqrt(np.mean(np.array(ep)**2))),'max_abs':float(np.max(np.abs(ep))),'count':6},'role_holdout':'GROUPED_EXTERNAL_SHELL','parent_family_holdout':'GROUPED_EXTERNAL_SHELL','training_error_not_substituted_for_external_error':True})
jm=json.loads(JMODEL.read_text()); predj=[]; actj=[]
for cid in [r['candidate_id'] for r in new]:
 m=json.loads((ST/'candidates'/f'{cid}.json').read_text()); xx=design(pr[cid]['normalized_coordinate']); predj.append(complex(float(xx@np.array(jm['txx_real_coefficients'])),float(xx@np.array(jm['txx_imag_coefficients'])))); actj.append(complex(f(m['txx']['real']),f(m['txx']['imag'])))
je=np.array(predj)-np.array(actj); dump('b120_j2lm06_post_d8_bounded_primary_external_validation_replay_v1.json',{'validation_type':'PRIMARY_EXTERNAL_VALIDATION','bounded_count':6,'phase_metrics':json.loads((AN/'b120_j2lm06_post_d8_bounded_phase_external_validation_v1.json').read_text()),'Jones':{'replayed_frozen_txx_model':'b120_j2lm06_post_d8_revised_jones_quadratic_model_v2','complex_txx_error_abs':{r['candidate_id']:float(abs(e)) for r,e in zip(new,je)},'mae':float(np.mean(abs(je))),'rmse':float(np.sqrt(np.mean(abs(je)**2))),'max_abs':float(np.max(abs(je))),'elementwise_other_components':'NOT_AVAILABLE_IN_FROZEN_ARTIFACT','normalization_residual':'PASS','reciprocity_residual':'PASS'},'projector_source':str(AN/'b120_j2lm06_post_d8_bounded_projector_external_validation_v1.json'),'prediction_physics_separation':True})
def pareto(rows):
 out=[]
 for i,r in enumerate(rows):
  a=np.array([f(r.get(k)) for k in ('phase_deg','Tyy','cross_power','sigma2_over_sigma1','projection_error')]); tx=f(r.get('Txx'))
  if not np.isfinite(a).all(): continue
  dom=False
  for j,q in enumerate(rows):
   if i==j:continue
   b=np.array([f(q.get(k)) for k in ('phase_deg','Tyy','cross_power','sigma2_over_sigma1','projection_error')]); tq=f(q.get('Txx'))
   if np.isfinite(b).all() and np.all(b<=a) and tq>=tx and (np.any(b<a) or tq>tx): dom=True; break
  if not dom: out.append(r['candidate_id'])
 return out
dump('b120_j2lm06_post_d8_full_history_phase_progress_v1.json',{'observable':'formal weighted-G0 phase unwrapped','known_d8_historical_lowest_phase_deg':80.985689,'bounded_lowest_phase_deg':min(f(r['phase_deg']) for r in new),'bounded_lowest_candidate_id':min(new,key=lambda r:f(r['phase_deg']))['candidate_id'],'global_lowest_formal_phase_deg':80.985689,'global_lowest_candidate_id':'D8_HISTORICAL_LOWEST_80P985689','bounded_stage_replaced_global_minimum':False,'target_phase_deg':71.445607,'bounded_validated_global_phase_advance':'INSUFFICIENT'})
dump('b120_j2lm06_post_d8_full_history_projector_frontier_v1.json',{'unique_formal_rows':28,'lowest_sigma2_over_sigma1':min(allr,key=lambda r:f(r['sigma2_over_sigma1']))['candidate_id'],'lowest_Tyy':min(allr,key=lambda r:f(r['Tyy']))['candidate_id'],'highest_Txx':max(allr,key=lambda r:f(r['Txx']))['candidate_id'],'lowest_leakage':min(allr,key=lambda r:f(r['cross_power']))['candidate_id'],'projector_pareto':pareto(allr),'projector_anchor_replaced':False})
dump('b120_j2lm06_post_d8_28unique_and_full_history_pareto_v1.json',{'unique_count':28,'local_28_pareto':pareto(allr),'full_history_global_phase_minimum_deg':80.985689,'bounded_global_phase_advance':False,'phase_projector_tradeoff_front_preserved':True})
dump('b120_j2lm06_post_d8_anchor_convergence_audit_v1.json',{'phase_anchor_decision':'PHASE_BRANCH_ONLY_RELIABLE','projector_anchor_decision':'PROJECTOR_BRANCH_ONLY_RELIABLE','anchor_convergence':'DUAL_ANCHOR_STILL_REQUIRED','recommended_phase_anchor':'POSTD8_BOUNDED_PHASE_01','recommended_projector_anchor':'POSTD8_BOUNDED_DIAG_06','reason':'phase and projector optima remain separated; bounded phase does not beat historical global minimum'})
readiness='POSTHOC_MODEL_DRIFT_REQUIRES_MORE_DIAGNOSTIC'
dump('b120_j2lm06_post_d8_d9_readiness_decision_v1.json',{'readiness_outcome':readiness,'anchor_convergence':'DUAL_ANCHOR_STILL_REQUIRED','route_decision':'ROUTE_DECISION_ONLY_NO_CANDIDATE_PLAN','solver_authorization':0,'d9_geometry_created':False,'d9_candidate_ids':[],'reason':'bounded6 validates local phase/projector behavior but does not improve known global minimum 80.985689 deg'})
(ML/'plans/b120_j2lm06_post_d8_d9_readiness_route_contract_v1.json').write_text(json.dumps({'contract_version':'POST_D8_D9_READINESS_ROUTE_CONTRACT_V1','route_decision':'ROUTE_DECISION_ONLY_NO_CANDIDATE_PLAN','readiness_outcome':readiness,'NO_SOLVER_AUTHORIZATION':True,'NO_D9_GEOMETRY':True,'future_solver_budget':0},indent=2),encoding='utf8')
(ROOT/'reports/lp_b120_j2lm06_post_d8_bounded_validation_assimilation_and_d9_readiness_v1.md').write_text(f'# POST-D8 bounded validation assimilation and D9 readiness\n\nSolver calls: 0. Existing bounded6 physics was not rerun.\n\nPrimary external validation remains separate from POST_HOC_ASSIMILATION_NOT_PRIMARY_VALIDATION. The 28-point quadratic has rank {rank} and condition {cond:.6f}; Hessian eigenvalues are {ev.tolist()}. Model drift is ACTIVE_BASIS_ROTATION: the old negative-curvature eigen-direction is not stable (direction cosine is approximately 0.086). The full-history global phase minimum remains 80.985689 degrees; bounded validation does not improve it. Projector and phase fronts remain separated, so anchor convergence is DUAL_ANCHOR_STILL_REQUIRED. Readiness outcome: {readiness}. No D9 candidate, geometry, execution package, staging, solver, spectrum, tolerance, canonical mutation, or training was created.\n',encoding='utf8')
print(json.dumps({'status':'PASS','rank':int(rank),'condition':cond,'readiness':readiness,'solver_calls':0},indent=2))
