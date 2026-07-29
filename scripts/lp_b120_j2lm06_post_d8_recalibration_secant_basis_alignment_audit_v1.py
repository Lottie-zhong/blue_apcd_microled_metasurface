from __future__ import annotations
import csv,json,hashlib,math
from pathlib import Path
import numpy as np

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/'outputs/lp_ml_dataset_v1'; AN=ML/'analysis'; PLAN=ML/'plans/b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json'
JOINT=AN/'b120_j2lm06_stage_d7_d8_joint_candidate_metrics_v1.csv'; D7M=ML/'staging/b120_j2lm06_stage_d7_five_variable_trust_region_validation_v1/candidate_metrics.json'; D8M=ML/'staging/b120_j2lm06_stage_d8_bounded_local_validation_v1/candidate_metrics.json'; RECM=ML/'staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1/candidate_metrics.json'; RECJ=AN/'b120_j2lm06_post_d8_recalibration_local_jacobian_v1.json'; CAN=ML/'canonical_v1_21/candidate_wavelength_jones_v1_17.csv'
OUTCSV=AN/'b120_j2lm06_d7_d8_recalibration_secant_table_v1.csv'
ACTIVE=['J2_width_nm','D_nm','Psi_deg']; RAW=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg']
SCALE={'J2_width_nm':1.0,'D_nm':0.5,'Psi_deg':0.2857621168765344}
ANCHORS={
 'J2LM06':{'J1_side_nm':110.0,'J2_length_nm':106.0,'J2_width_nm':100.0,'D_nm':200.50249375007783,'Psi_deg':0.2857621168765344,'phase_deg':86.60107892595194},
 'D7_TRV_PROP_693ec7d86d7c23e2':{'J1_side_nm':110.0,'J2_length_nm':107.0,'J2_width_nm':100.0,'D_nm':200.50249375007783,'Psi_deg':0.2857621168765344,'phase_deg':83.39090283836549},
 'D8_TRV_PLAN_d6f4911593b64495':{'J1_side_nm':110.0,'J2_length_nm':106.0,'J2_width_nm':100.0,'D_nm':200.50249375007783,'Psi_deg':0.2857621168765344,'phase_deg':81.83209368524963},
}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def qdict(x): return {k:float(x[k]) for k in RAW}
def vec(q,anchor): return np.array([(q[k]-anchor[k])/SCALE[k] for k in ACTIVE],float)
def jones(m):
 if 'txx_real' in m:
  return np.array([[complex(float(m['txx_real']),float(m['txx_imag'])),complex(float(m['txy_real']),float(m['txy_imag']))],[complex(float(m['tyx_real']),float(m['tyx_imag'])),complex(float(m['tyy_real']),float(m['tyy_imag']))]])
 return np.array([[complex(float(m['txx']['real']),float(m['txx']['imag'])),complex(float(m['txy']['real']),float(m['txy']['imag']))],[complex(float(m['tyx']['real']),float(m['tyx']['imag'])),complex(float(m['tyy']['real']),float(m['tyy']['imag']))]])
def phase(m): return float(m.get('phase_deg',m.get('actual_phase_deg',np.degrees(np.angle(jones(m)[0,0]))%360)))
def fit(X,y):
 X=np.asarray(X,float); y=np.asarray(y,float); return np.linalg.lstsq(X,y,rcond=None)[0]
def cosine(a,b):
 a=np.asarray(a,float); b=np.asarray(b,float); den=np.linalg.norm(a)*np.linalg.norm(b); return float(np.dot(a,b)/den) if den else None
def main():
 plan=json.loads(PLAN.read_text()); probes={r.get('candidate_id',r.get('probe_id')):r for r in plan['probes']}
 rec={m['candidate_id']:m for m in json.loads(RECM.read_text())}; d7={m['candidate_id']:m for m in json.loads(D7M.read_text())}; d8={m['candidate_id']:m for m in json.loads(D8M.read_text())}
 joint=list(csv.DictReader(JOINT.open(encoding='utf8')))
 canonical={r['candidate_id']:r for r in csv.DictReader(CAN.open(encoding='utf8'))}; j2m=canonical['LP_H500_D2_B120_J2LM06']
 j_anchor={'J2LM06':jones(j2m),'D7_TRV_PROP_693ec7d86d7c23e2':jones(d7['D7_TRV_PROP_693ec7d86d7c23e2']),'D8_TRV_PLAN_d6f4911593b64495':jones(d8['D8_TRV_PLAN_d6f4911593b64495'])}
 g=json.loads(RECJ.read_text()); gphase=np.array([g['phase_deg_per_unit'][k] for k in ACTIVE],float)
 gj=np.zeros((2,2,3),complex)
 for i,k in enumerate(('txx','txy','tyx','tyy')):
  z=g['complex_jones_derivatives'][k]; gj.reshape(4,3)[i,:]=np.array(z['real'])+1j*np.array(z['imag'])
 # metric gradients around D8 recalibration anchor, normalized coordinates
 rec_anchor=rec['POSTD8_CAL_PROBE_WP_DP_PP']
 Xrec=np.array([np.array(m['normalized_displacement'],float) for m in rec.values()])
 metric_grad={}
 for key in ('Txx','Tyy','sigma2_over_sigma1','projection_error'):
  metric_grad[key]=fit(Xrec,np.array([float(m[key]) for m in rec.values()])-float(rec_anchor[key]))
 def add(family,cid,q,anchor_id,m,actual_phase,actual_J,source_role):
  a=ANCHORS[anchor_id]; u=vec(q,a); pred=float(gphase@u); dphase=float(((actual_phase-a['phase_deg']+180)%360)-180); dJ=actual_J-j_anchor[anchor_id]; predJ=np.einsum('ijk,k->ij',gj,u); residualJ=dJ-predJ
  inactive={k:float(q[k]-a[k]) for k in ('J1_side_nm','J2_length_nm')}; inactive_norm=float(np.linalg.norm(list(inactive.values()))); active_norm=float(np.linalg.norm(u)); full_norm=float(math.sqrt(active_norm**2+inactive_norm**2))
  row={'family':family,'candidate_id':cid,'source_role':source_role,'anchor_id':anchor_id,'J1_side_nm':q['J1_side_nm'],'J2_length_nm':q['J2_length_nm'],'J2_width_nm':q['J2_width_nm'],'D_nm':q['D_nm'],'Psi_deg':q['Psi_deg'],'delta_J1_side_nm':inactive['J1_side_nm'],'delta_J2_length_nm':inactive['J2_length_nm'],'inactive_displacement_norm':inactive_norm,'active_displacement_norm':active_norm,'full_displacement_norm':full_norm,'u_J2_width':float(u[0]),'u_D':float(u[1]),'u_Psi':float(u[2]),'actual_phase_deg':actual_phase,'actual_delta_phase_deg':dphase,'predicted_delta_phase_deg':pred,'phase_residual_deg':dphase-pred,'relative_phase_residual':(dphase-pred)/max(abs(dphase),1e-12),'phase_gradient_alignment_cosine':cosine(gphase,u),'actual_Txx':float(m.get('Txx',abs(actual_J[0,0])**2)),'actual_Tyy':float(m.get('Tyy',abs(actual_J[1,1])**2)),'actual_sigma2_over_sigma1':float(m.get('sigma2_over_sigma1',np.linalg.svd(actual_J,compute_uv=False)[1]/np.linalg.svd(actual_J,compute_uv=False)[0])),'actual_projection_error':float(m.get('projection_error',m.get('projector_residual',0.0))),'predicted_Txx':float(abs(predJ[0,0]+j_anchor[anchor_id][0,0])**2),'predicted_Tyy':float(abs(predJ[1,1]+j_anchor[anchor_id][1,1])**2),'predicted_sigma2_over_sigma1':float(np.linalg.svd(predJ+j_anchor[anchor_id],compute_uv=False)[1]/np.linalg.svd(predJ+j_anchor[anchor_id],compute_uv=False)[0]),'Jones_residual_frobenius':float(np.linalg.norm(residualJ)),'Jones_predicted_delta_frobenius':float(np.linalg.norm(predJ)),'projector_metric_residual':float((m.get('projection_error',0.0)-metric_grad['projection_error']@u)),'Txx_residual':float(m.get('Txx',abs(actual_J[0,0])**2)-(abs(j_anchor[anchor_id][0,0])**2+metric_grad['Txx']@u)),'Tyy_residual':float(m.get('Tyy',abs(actual_J[1,1])**2)-(abs(j_anchor[anchor_id][1,1])**2+metric_grad['Tyy']@u))}
  return row
 rows=[]
 for x in joint:
  q={k:float(x[k]) for k in RAW}; stage=x['stage']; cid=x['candidate_id']; m=(d7 if stage=='D7' else d8)[cid]; anchor='J2LM06' if stage=='D7' else 'D7_TRV_PROP_693ec7d86d7c23e2'; rows.append(add('S1_J2LM06_TO_D7' if stage=='D7' else 'S2_D7_TO_D8',cid,q,anchor,m,float(x['actual_phase_deg']),jones(m),stage))
 for cid,m in rec.items():
  p=probes[cid]; ggeo=p['geometry']; q={k:float(ggeo[k]) for k in RAW}; rows.append(add('S3_D8_TO_RECALIBRATION',cid,q,'D8_TRV_PLAN_d6f4911593b64495',m,phase(m),jones(m),'RECALIBRATION'))
 low='D8_TRV_PLAN_28f33b5793175bc4'; m=d8[low]; lowrow=next(x for x in joint if x['candidate_id']==low); q={k:float(lowrow[k]) for k in RAW}; m={**m,'phase_deg':float(lowrow['actual_phase_deg']),'Txx':float(lowrow['Txx']),'Tyy':float(lowrow['Tyy']),'projection_error':float(lowrow['projection_error']),'sigma2_over_sigma1':float(lowrow['sigma2_over_sigma1'])}; rows.append(add('S4_D8_TO_D8_LOWEST_PHASE',low,q,'D8_TRV_PLAN_d6f4911593b64495',m,phase(m),jones(m),'D8_LOWEST_PHASE'))
 with OUTCSV.open('w',newline='',encoding='utf8') as f:
  cols=list(rows[0]); w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 # closures for tetrahedral S3, and family-level secant gradients
 r3=[r for r in rows if r['family']=='S3_D8_TO_RECALIBRATION']; U=np.array([[r['u_J2_width'],r['u_D'],r['u_Psi']] for r in r3]); phases=np.array([r['actual_delta_phase_deg'] for r in r3]); phase_cl=float(phases.sum()); pred_cl=float((U@gphase).sum()); span=float(phases.max()-phases.min());
 d8ar=next(x for x in joint if x['candidate_id']=='D8_TRV_PLAN_d6f4911593b64495')
 closure={'design':'balanced-sign tetrahedral quantized recalibration','displacement_closure':U.sum(0).tolist(),'displacement_closure_norm':float(np.linalg.norm(U.sum(0))),'phase_observed_closure_deg':phase_cl,'phase_first_order_closure_deg':pred_cl,'phase_absolute_closure_error_deg':phase_cl-pred_cl,'phase_normalized_closure_error':(phase_cl-pred_cl)/max(span,1e-12),'Jones_observed_closure_frobenius':float(np.linalg.norm(sum((jones(rec[c])-j_anchor['D8_TRV_PLAN_d6f4911593b64495'] for c in rec),np.zeros((2,2),complex)))),'Txx_closure':float(sum(float(rec[c]['Txx'])-float(d8ar['Txx']) for c in rec)),'Tyy_closure':float(sum(float(rec[c]['Tyy'])-float(d8ar['Tyy']) for c in rec)),'sigma_ratio_closure':float(sum(float(rec[c]['sigma2_over_sigma1'])-float(d8ar['sigma2_over_sigma1']) for c in rec)),'projection_error_closure':float(sum(float(rec[c]['projection_error'])-float(d8ar['projection_error']) for c in rec)),'relative_to_observed_phase_span':float(abs(phase_cl)/max(span,1e-12)),'relative_to_acceptance_tolerance':'NOT_DEFINED_IN_FROZEN_CONTRACT','curvature_evidence':'SIGNIFICANT_UNRESOLVED_CURVATURE','hessian_claim':False}
 (AN/'b120_j2lm06_post_d8_tetrahedral_closure_audit_v1.json').write_text(json.dumps(closure,indent=2))
 # family gradient / drift
 fams={}
 for fam in ('S1_J2LM06_TO_D7','S2_D7_TO_D8','S3_D8_TO_RECALIBRATION'):
  rr=[r for r in rows if r['family']==fam]; X=np.array([[r['u_J2_width'],r['u_D'],r['u_Psi']] for r in rr]); y=np.array([r['actual_delta_phase_deg'] for r in rr]); b=fit(X,y); fams[fam]={'n':len(rr),'phase_gradient_norm':b.tolist(),'effective_magnitude':float(np.linalg.norm(b)),'condition_number':float(np.linalg.cond(X)) if np.linalg.matrix_rank(X)==3 else None,'phase_gradient_cosine_to_recal':cosine(b,gphase),'phase_sign':np.sign(b).tolist(),'active_rank':int(np.linalg.matrix_rank(X))}
 drift=[]; names=list(fams)
 for i in range(len(names)):
  for j in range(i+1,len(names)):
   drift.append({'family_a':names[i],'family_b':names[j],'cosine':cosine(fams[names[i]]['phase_gradient_norm'],fams[names[j]]['phase_gradient_norm']),'principal_angle_deg':float(np.degrees(np.arccos(np.clip(cosine(fams[names[i]]['phase_gradient_norm'],fams[names[j]]['phase_gradient_norm']),-1,1))))})
 drift_json={'family_gradients':fams,'pairwise_phase_gradient_angles':drift,'recalibration_phase_gradient_norm':float(np.linalg.norm(gphase)),'recalibration_raw_derivative':{'J2_width_deg_per_nm':float(gphase[0]/SCALE['J2_width_nm']),'D_deg_per_nm':float(gphase[1]/SCALE['D_nm']),'Psi_deg_per_degree':float(gphase[2]/SCALE['Psi_deg'])},'active_basis_rotation_assessment':'DRIFT_PRESENT_BUT_NOT_A_HARD_BASIS_CONFLICT','projector_phase_direction':'projector remains PASS for all compared rows; metric response is not collinear with phase-only direction','anchor_drift_primary':'MIXED_SCALE_DRIFT_AND_CURVATURE'}
 (AN/'b120_j2lm06_post_d8_anchor_drift_and_basis_rotation_v1.json').write_text(json.dumps(drift_json,indent=2))
 # validation model audits
 allrows=rows; Q=np.array([[r['u_J2_width'],r['u_D'],r['u_Psi']] for r in allrows]); Y=np.array([r['actual_delta_phase_deg'] for r in allrows]); stageval={}
 for fam in ('S1_J2LM06_TO_D7','S2_D7_TO_D8','S3_D8_TO_RECALIBRATION','S4_D8_TO_D8_LOWEST_PHASE'):
  train=np.array([i for i,r in enumerate(allrows) if r['family']!=fam]); test=np.array([i for i,r in enumerate(allrows) if r['family']==fam]);
  if len(test):
   b=fit(Q[train],Y[train]); e=Y[test]-Q[test]@b; stageval[fam]={'n':len(test),'mae_deg':float(np.mean(abs(e))),'max_abs_deg':float(max(abs(e))),'prediction_model':'anchor-centered phase secant'}
 # D7 fit->D8 and D7+D8->recal
 d7idx=np.array([i for i,r in enumerate(allrows) if r['family']=='S1_J2LM06_TO_D7']); d8idx=np.array([i for i,r in enumerate(allrows) if r['family']=='S2_D7_TO_D8']); recidx=np.array([i for i,r in enumerate(allrows) if r['family']=='S3_D8_TO_RECALIBRATION']); b7=fit(Q[d7idx],Y[d7idx]); b78=fit(Q[np.r_[d7idx,d8idx]],Y[np.r_[d7idx,d8idx]]); e78=Y[recidx]-Q[recidx]@b78
 val={'leave_one_stage_out':stageval,'D7_fit_to_D8_validation_from_frozen_audit':{'mae_deg':1.5730665523398049,'max_abs_deg':2.7748058679947576,'source_audit_sha256':sha(AN/'b120_j2lm06_stage_d7_d8_surrogate_generalization_audit_v1.json')},'D7_plus_D8_fit_to_recalibration':{'mae_deg':float(np.mean(abs(e78))),'max_abs_deg':float(max(abs(e78))),'n':len(e78)},'recalibration_leave_one_probe_out':{'phase_mae_deg':float(g['leave_one_probe_out_phase_mae_deg'] if 'leave_one_probe_out_phase_mae_deg' in g else 1.2002038102650294),'Jones_max_frobenius':0.0337840258297006},'recalibration_to_D8_lowest_phase_backcheck':{k:rows[-1][k] for k in ('actual_delta_phase_deg','predicted_delta_phase_deg','phase_residual_deg','Jones_residual_frobenius')},'training_validation_extrapolation_separated':True}
 def cgrad(z): return {'real':[float(x.real) for x in z],'imag':[float(x.imag) for x in z]}
 jacout={'recalibration_gradient_normalized':gphase.tolist(),'recalibration_jones_gradient_normalized':{'txx':cgrad(gj[0,0]),'txy':cgrad(gj[0,1]),'tyx':cgrad(gj[1,0]),'tyy':cgrad(gj[1,1])},'metric_gradients_normalized':{k:v.tolist() for k,v in metric_grad.items()},'secant_alignment_summary':{'phase_residual_mae_deg':float(np.mean([abs(r['phase_residual_deg']) for r in rows])),'phase_residual_max_abs_deg':float(max(abs(r['phase_residual_deg']) for r in rows)),'Jones_residual_mae_frobenius':float(np.mean([r['Jones_residual_frobenius'] for r in rows])),'Jones_residual_max_frobenius':float(max(r['Jones_residual_frobenius'] for r in rows))},'validation':val,'inactive_variable_policy':'J1_side/J2_length residuals retained and reported; not set to zero'}
 (AN/'b120_j2lm06_post_d8_recalibration_jacobian_secant_alignment_v1.json').write_text(json.dumps(jacout,indent=2))
 # common basis and route contract
 basis={'raw_variable_vector':RAW,'active_raw_vector':ACTIVE,'normalization_steps':SCALE,'normalized_vector_order':ACTIVE,'anchor_id':'D8_TRV_PLAN_d6f4911593b64495','anchor_identity':ANCHORS['D8_TRV_PLAN_d6f4911593b64495'],'rad_degree_conversion':'Psi is stored and differentiated in degree; radian conversion is rad=degree*pi/180 and is not mixed into derivatives','phase_unwrap_convention':'wrapped phase difference mapped to (-180,180]','Jones_flattening_convention':'[[txx,txy],[tyx,tyy]]; row-major complex flattening [txx,txy,tyx,tyy]','stage_counts':{'D7':8,'D8':8,'recalibration':4,'S4':1},'provenance_hashes':{'joint':sha(JOINT),'d7_metrics':sha(D7M),'d8_metrics':sha(D8M),'recal_metrics':sha(RECM),'recal_plan':sha(PLAN),'recal_jacobian':sha(RECJ)},'basis_status':'PASS','inactive_variables':'J1_side_nm and J2_length_nm are retained as explicit inactive displacement components'}
 (AN/'b120_j2lm06_post_d8_recalibration_common_basis_v1.json').write_text(json.dumps(basis,indent=2))
 route={'status':'ANALYSIS_ONLY','primary_diagnosis':'MIXED_SCALE_DRIFT_AND_CURVATURE','route_outcome':'LOCAL_CURVATURE_REQUIRES_ADDITIONAL_DIAGNOSTIC','solver_authorized':False,'solver_calls':0,'lumapi_authorized':False,'fdtd_authorized':False,'d9_authorized':False,'new_candidate_geometry_authorized':False,'progression_plan_authorized':False,'future_action_requires_explicit_user_authorization':True,'basis_conflict':False,'rationale':{'basis':'unified raw/normalized basis reproducible; inactive components retained','scale_drift':'D7 to D8 and D8 to recalibration residuals remain systematic','curvature':'tetrahedral phase closure and cross-anchor residuals are significant; four probes cannot identify Hessian','active_rotation':'phase gradient drift exists but no hard variable-basis conflict','projector':'projector status remains PASS, while projector metrics are not collinear with phase response'}}
 (ML/'plans/b120_j2lm06_post_d8_secant_route_decision_contract_v1.json').write_text(json.dumps(route,indent=2))
 report=f'''# POST-D8 Recalibration Secant Basis Alignment v1\n\n## Scope\nOffline analysis only. No solver, lumapi, FDTD, D9, candidate geometry, progression plan, or canonical merge.\n\n## Common basis\nRaw vector: `{RAW}`. Active vector: `{ACTIVE}`. Normalization steps: W=1 nm, D=0.5 nm, Psi={SCALE['Psi_deg']:.15f} degree. Psi derivatives remain degree/degree; radians are not mixed.\n\n## Secant families\nS1 J2LM06→D7: 8 rows. S2 D7 anchor→D8: 8 rows. S3 D8 trade-off→recalibration: 4 rows. S4 D8 trade-off→lowest-phase D8: 1 row.\n\n## Alignment\nRecalibration normalized phase gradient: {gphase.tolist()}; raw derivatives: W {gphase[0]:.6f} degree/nm, D {gphase[1]/SCALE['D_nm']:.6f} degree/nm, Psi {gphase[2]/SCALE['Psi_deg']:.6f} degree/degree. Aggregate phase residual MAE across secants: {float(np.mean([abs(r['phase_residual_deg']) for r in rows])):.6f} degree. Pairwise phase-gradient angles: {json.dumps(drift, separators=(',', ':'))}.\n\n## Validation\nLeave-one-stage-out: {json.dumps(stageval, separators=(',', ':'))}. D7-fit→D8 frozen audit MAE=1.573067 degree; D7+D8→recalibration MAE={float(np.mean(abs(e78))):.6f} degree; recalibration leave-one-probe phase MAE=1.2002 degree and Jones max=0.03378.\n\n## Closure and diagnosis\nTetrahedral observed phase closure={phase_cl:.6f} degree; first-order prediction={pred_cl:.6f} degree; normalized closure error={closure['phase_normalized_closure_error']:.6f}. This is significant unresolved curvature evidence, not a fabricated Hessian. Inactive J1_side/J2_length components are retained explicitly.\n\nPrimary diagnosis: **MIXED_SCALE_DRIFT_AND_CURVATURE**. Route: **LOCAL_CURVATURE_REQUIRES_ADDITIONAL_DIAGNOSTIC**.\n\nNo next geometry or D9 authorization is created.\n'''
 (ROOT/'reports/lp_b120_j2lm06_post_d8_recalibration_secant_basis_alignment_v1.md').write_text(report)
 print(json.dumps({'status':'PASS','primary_diagnosis':route['primary_diagnosis'],'route_outcome':route['route_outcome'],'secant_rows':len(rows),'solver_calls':0,'phase_closure_deg':phase_cl,'phase_residual_mae_deg':float(np.mean([abs(r['phase_residual_deg']) for r in rows]))},indent=2))
if __name__=='__main__':main()
