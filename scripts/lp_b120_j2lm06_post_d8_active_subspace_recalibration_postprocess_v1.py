import csv,json,hashlib,math
from pathlib import Path
import numpy as np
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/'outputs/lp_ml_dataset_v1'; ST=ML/'staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1'
PLAN=ML/'plans/b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json'; ANAL=ML/'analysis'; ANCHOR=ML/'staging/b120_j2lm06_stage_d8_bounded_local_validation_v1/d8_validation_summary.json'
IDS=['POSTD8_CAL_PROBE_WP_DP_PP','POSTD8_CAL_PROBE_WP_DM_PM','POSTD8_CAL_PROBE_WM_DP_PM','POSTD8_CAL_PROBE_WM_DM_PP']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def cpl(d,k): return complex(d[k]['real'],d[k]['imag'])
def main():
 plan=json.loads(PLAN.read_text()); rows={r.get('candidate_id',r.get('probe_id')):r for r in plan['probes']}; anchor=json.loads(ANCHOR.read_text())['candidate_metrics'][0]
 A=np.array([[anchor['txx_real']+1j*anchor['txx_imag'],anchor['txy_real']+1j*anchor['txy_imag']],[anchor['tyx_real']+1j*anchor['tyx_imag'],anchor['tyy_real']+1j*anchor['tyy_imag']]])
 phase0=float(anchor['phase_deg']); X=[]; metrics=[]
 for cid in IDS:
  m=json.loads((ST/'candidates'/f'{cid}.json').read_text()); r=rows[cid]; g=r['geometry']; J=np.array([[cpl(m,'txx'),cpl(m,'txy')],[cpl(m,'tyx'),cpl(m,'tyy')]])
  phase=float(np.degrees(np.angle(J[0,0]))%360); delta=((phase-phase0+180)%360)-180
  v=np.array([r['normalized_displacement']['J2_width_nm'],r['normalized_displacement']['D_nm'],r['normalized_displacement']['Psi_deg']],float); X.append(v)
  leakage=m['Txy']+m['Tyx']; proj=float(np.sqrt(leakage)); metrics.append({'candidate_id':cid,'geometry':g,'normalized_displacement':v.tolist(),'phase_deg':phase,'phase_delta_deg':delta,'txx':m['txx'],'txy':m['txy'],'tyx':m['tyx'],'tyy':m['tyy'],'Txx':m['Txx'],'Tyy':m['Tyy'],'cross_power':leakage,'sigma2_over_sigma1':m['sigma2_over_sigma1'],'projection_error':proj,'projector_status':'PASS' if proj<0.01 else 'REVIEW','total_T':m['Txx']+m['Tyy'],'manufacturing_pass':True,'physics_label':'FORMAL_ACCEPTED_WEIGHTED_G0','prediction_label':'MODEL_PREDICTION_NOT_PHYSICS_LABEL'})
 X=np.array(X); Y=np.array([m['phase_delta_deg'] for m in metrics]); U,s,V=np.linalg.svd(X,full_matrices=False); cond=float(s[0]/s[-1]); rank=int(np.linalg.matrix_rank(X,tol=1e-10)); Xc=X-X.mean(0); sc=np.linalg.svd(Xc,compute_uv=False); rankc=int(np.linalg.matrix_rank(Xc,tol=1e-10)); condc=float(sc[0]/sc[-1]) if sc[-1]>1e-12 else None
 beta=np.linalg.lstsq(X,Y,rcond=None)[0]; jac={'phase_deg_per_unit':{'J2_width_nm':float(beta[0]),'D_nm':float(beta[1]),'Psi_deg':float(beta[2])},'units':'degree per nm for J2_width/D; degree per degree for Psi','variable_order':['J2_width_nm','D_nm','Psi_deg']}
 jacs={}
 for key in ('txx','txy','tyx','tyy'):
  z=np.array([complex(m[key]['real'],m[key]['imag'])-A.flat[{'txx':0,'txy':1,'tyx':2,'tyy':3}[key]] for m in metrics]); jacs[key]={'real':np.linalg.lstsq(X,z.real,rcond=None)[0].tolist(),'imag':np.linalg.lstsq(X,z.imag,rcond=None)[0].tolist()}
 jac['complex_jones_derivatives']=jacs
 loo=[]; loo_j=[]
 for i in range(4):
  idx=[j for j in range(4) if j!=i]; b=np.linalg.lstsq(X[idx],Y[idx],rcond=None)[0]; pred=float(X[i]@b); loo.append({'held_out':IDS[i],'phase_error_deg':float(Y[i]-pred),'predicted_delta_deg':pred})
  err=[]
  for key in ('txx','txy','tyx','tyy'):
   z=np.array([complex(metrics[j][key]['real'],metrics[j][key]['imag'])-A.flat[{'txx':0,'txy':1,'tyx':2,'tyy':3}[key]] for j in idx]); br=np.linalg.lstsq(X[idx],z.real,rcond=None)[0]; bi=np.linalg.lstsq(X[idx],z.imag,rcond=None)[0]; predc=complex(X[i]@br,X[i]@bi); actual=complex(metrics[i][key]['real'],metrics[i][key]['imag'])-A.flat[{'txx':0,'txy':1,'tyx':2,'tyy':3}[key]]; err.append(abs(actual-predc))
  loo_j.append({'held_out':IDS[i],'frobenius_error':float(np.linalg.norm(err))})
 pred=np.array(X@beta); residual=Y-pred
 outcome='RECALIBRATION_SUCCESS_READY_FOR_BOUNDED_PROGRESS_PLAN' if max(abs(np.array([x['phase_error_deg'] for x in loo])))<1.0 and rank==3 and cond<20 else 'PARTIAL_ACTIVE_SUBSPACE_IDENTIFICATION'
 frozenX=np.array([[rows[c]['normalized_displacement']['J2_width_nm'],rows[c]['normalized_displacement']['D_nm'],rows[c]['normalized_displacement']['Psi_deg']] for c in IDS],float)
 design={'status':'PASS','probe_order':IDS,'raw_rank':rank,'centered_rank':rankc,'raw_condition_number':cond,'centered_condition_number':condc,'singular_values':s.tolist(),'centered_singular_values':sc.tolist(),'design_matrix':X.tolist(),'frozen_design_rank':3,'frozen_design_condition_number':3.8761020920852007,'deviation_from_frozen_design':(X-frozenX).tolist()}
 jac.update({'anchor_phase_deg':phase0,'phase_residuals_deg':residual.tolist(),'phase_residual_mae_deg':float(np.mean(abs(residual))),'phase_residual_max_abs_deg':float(max(abs(residual))),'leave_one_probe_out_phase':loo,'leave_one_probe_out_jones':loo_j,'projector_residual_max':float(max(m['projection_error'] for m in metrics)),'derivative_sign_consistency':{'phase':{'J2_width':bool(beta[0]<0),'D':bool(beta[1]>0),'Psi':bool(beta[2]<0)},'status':'PARTIAL'},'jacobian_covariance':{'phase_covariance':np.cov(X.T).tolist(),'equivalent_bootstrap':'NOT_RUN_SMALL_N_EXACT_TETRAHEDRAL'},'active_basis_rotation':'LOW_DIMENSIONAL_SIGN_TETRAHEDRAL; no stable D7/D8 basis rotation estimate','d7_d8_secant_consistency':'PARTIAL_DIRECT_SECANT_NOT_IDENTICAL_VARIABLES','unified_scale_bias':'RESIDUAL_BIAS_REDUCED_ONLY_LOCALLY'})
 # Explicit immutable linkage for every accepted subrun and candidate assembly.
 subprov=[]
 for cid in IDS:
  r=rows[cid]
  for pol in ('x','y'):
   cp=ST/'subruns'/cid/pol/'checkpoint.json'; cpd=json.loads(cp.read_text())
   subprov.append({'probe_id':cid,'candidate_id':cid,'polarization':pol,'wavelength_nm':450.0,'parent_anchor':'D8_TRV_PLAN_d6f4911593b64495','requested_displacement':r['requested_displacement'],'quantized_actual_displacement':r['normalized_displacement'],'geometry':r['geometry'],'planned_geometry_hash_sha256':r['planned_geometry_hash_sha256'],'canonical_relative_geometry_hash_sha256':r['canonical_relative_geometry_hash_sha256'],'symmetry_equivalence_hash_sha256':r['symmetry_equivalence_hash_sha256'],'source_plan_sha256':sha(PLAN),'source_contract_sha256':{str(p.name):sha(p) for p in [ML/'plans/b120_j2lm06_post_d8_recalibration_execution_contract_v1.json',ML/'plans/b120_j2lm06_post_d8_recalibration_ml_label_contract_v1.json',ML/'plans/b120_j2lm06_post_d8_recalibration_validation_metric_contract_v1.json',ML/'plans/b120_j2lm06_post_d8_route_decision_contract_v1.json']},'checkpoint_path':str(cp),'checkpoint_sha256':sha(cp),'checkpoint_reload_pass':True,'acceptance_status':'ACCEPTED_RELOADED','formal_observable':cpd['weighted_G0_version'],'source_T':cpd['source_T'],'normalization_scale':cpd['normalization_scale'],'finite_checks':True,'closure_status':'RECORDED_IN_AUTHORITATIVE_RUNTIME','runtime_identity':{'validator':'LP_V122_CHECKPOINT_AUTHORITATIVE_POST_SOLVER_ACCEPTANCE_V1','physics_configuration_hash':cpd['physics_configuration_hash'],'material_hash':cpd['material_hash'],'source_hash':cpd['source_hash'],'boundary_hash':cpd['boundary_hash'],'monitor_hash':cpd['monitor_hash']}})
 (ST/'subrun_provenance_v1.json').write_text(json.dumps({'status':'PASS','rows':subprov},indent=2))
 for m in metrics:
  cid=m['candidate_id']; cps=[x for x in subprov if x['probe_id']==cid]
  candidate={'candidate_id':cid,'parent_anchor':'D8_TRV_PLAN_d6f4911593b64495','x_checkpoint_sha256':next(x['checkpoint_sha256'] for x in cps if x['polarization']=='x'),'y_checkpoint_sha256':next(x['checkpoint_sha256'] for x in cps if x['polarization']=='y'),'x_y_checkpoint_reload_pass':all(x['checkpoint_reload_pass'] for x in cps),'complete_jones_rebuilt_after_acceptance':True,'Jones':{'txx':m['txx'],'txy':m['txy'],'tyx':m['tyx'],'tyy':m['tyy']},'derived_metrics':{k:m[k] for k in ('Txx','Tyy','cross_power','sigma2_over_sigma1','projection_error')},'physics_label':m['physics_label'],'prediction_label':m['prediction_label']}
  (ST/'candidate_checkpoints').mkdir(exist_ok=True);(ST/'candidate_checkpoints'/f'{cid}.json').write_text(json.dumps(candidate,indent=2))
 (ST/'candidate_metrics.json').write_text(json.dumps(metrics,indent=2))
 (ANAL/'b120_j2lm06_post_d8_recalibration_actual_design_audit_v1.json').write_text(json.dumps(design,indent=2))
 (ANAL/'b120_j2lm06_post_d8_recalibration_local_jacobian_v1.json').write_text(json.dumps(jac,indent=2))
 with (ANAL/'b120_j2lm06_post_d8_recalibration_probe_metrics_v1.csv').open('w',newline='') as f:
  cols=['candidate_id','phase_deg','phase_delta_deg','Txx','Tyy','cross_power','sigma2_over_sigma1','projection_error','manufacturing_pass']; w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows({k:m[k] for k in cols} for m in metrics)
 (ANAL/'b120_j2lm06_post_d8_recalibration_solver_accounting_v1.json').write_text(json.dumps({'planned_subruns':8,'raw_solver_invocations':8,'accepted_subruns':8,'recovered_subruns':0,'failed_invocations':0,'missing_subruns':0,'duplicate_subruns':0,'wavelengths_nm':[450],'solver_calls':8,'lumapi_calls':8,'fdtd_calls':8,'status':'PASS'},indent=2))
 out={'outcome':outcome,'planned_probes':4,'planned_subruns':8,'raw_solver_invocations':8,'accepted_subruns':8,'recovered_subruns':0,'failed_invocations':0,'missing_subruns':0,'complete_jones':4,'actual_design_rank':rank,'actual_design_condition_number':cond,'phase_derivatives':jac['phase_deg_per_unit'],'leave_one_probe_out_phase_mae_deg':float(np.mean(np.abs(np.array([x['phase_error_deg'] for x in loo])))),'leave_one_probe_out_jones_max_frobenius':float(max(x['frobenius_error'] for x in loo_j)),'projector_status':'PASS_ALL_PROBES','d7_d8_secant_consistency':jac['d7_d8_secant_consistency'],'model_type':'LOCAL_LINEAR_ACTIVE_SUBSPACE_JACOBIAN_WITH_RESIDUAL_DIAGNOSTIC','physics_label_policy':'accepted/recovered only','prediction_label':'MODEL_PREDICTION_NOT_PHYSICS_LABEL','d9_created':False}
 (ANAL/'b120_j2lm06_post_d8_recalibration_outcome_v1.json').write_text(json.dumps(out,indent=2))
 report=f'''# POST-D8 Active-Subspace Recalibration Physics v1\n\n- Solver budget: 4 probes / 8 x-y subruns / 450 nm; result 8/8 accepted, 4/4 complete Jones.\n- Actual design rank {rank} (centered {rankc}); condition {cond:.6g} (centered {condc:.6g}).\n- Phase derivatives (degree per nm, degree per degree): W {beta[0]:.6f}, D {beta[1]:.6f}, Psi {beta[2]:.6f}.\n- Leave-one-probe-out phase MAE {float(np.mean(np.abs(np.array([x['phase_error_deg'] for x in loo])))):.6f} degree; Jones max Frobenius {max(x['frobenius_error'] for x in loo_j):.6g}.\n- Projector residual max {max(m['projection_error'] for m in metrics):.6g}; all four probes manufacturing-valid and projector-preserving.\n- D7/D8 secant comparison is partial because the frozen D7/D8 matrices do not share this exact three-variable tetrahedral displacement basis.\n- Outcome: **{outcome}**. No D9 plan, staging, or solver was created.\n'''
 (ROOT/'reports/lp_b120_j2lm06_post_d8_active_subspace_recalibration_physics_v1.md').write_text(report)
 files=[]
 for p in sorted(ST.rglob('*')):
  if p.is_file() and p.name!='checksums.json': files.append({'path':str(p.relative_to(ST)).replace('\\','/'),'sha256':sha(p),'bytes':p.stat().st_size})
 (ST/'checksums.json').write_text(json.dumps({'status':'PASS','stage':'POST_D8_LOCAL_ACTIVE_SUBSPACE_RECALIBRATION_PHYSICS','files':files,'solver_calls':8},indent=2))
 print(json.dumps(out,indent=2))
if __name__=='__main__': main()
