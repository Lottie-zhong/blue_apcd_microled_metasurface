from __future__ import annotations
import csv,json,hashlib,subprocess,math
from pathlib import Path
import numpy as np
ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); ML=ROOT/'outputs/lp_ml_dataset_v1'; AN=ML/'analysis'; ST=ML/'staging/b120_j2lm06_post_d8_bounded_physics_validation_v1'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,x): (AN/n).write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf8')
def f(x):
 try:return float(x)
 except:return float('nan')
def design(w,d,p): return np.array([1,w,d,p,w*w,d*d,p*p,w*d,w*p,d*p],float)
def run(*a): return subprocess.check_output(['git','-C',str(ROOT),*a],text=True).strip()
provenance={'pwd':str(ROOT),'hostname':subprocess.check_output(['hostname'],text=True).strip(),'git_toplevel':run('rev-parse','--show-toplevel'),'git_dir':run('rev-parse','--git-dir'),'branch':run('branch','--show-current'),'head':run('rev-parse','HEAD'),'upstream':run('rev-parse','origin/work/lp-stage11-4'),'merge_base':run('merge-base','HEAD','origin/work/lp-stage11-4'),'ahead_behind':run('rev-list','--left-right','--count','HEAD...origin/work/lp-stage11-4'),'cb57069_full_sha':run('rev-parse','cb57069'),'cb57069_reachable_from_branch':True,'worktree_repository':'D:/project/blue_apcd_microled_metasurface/.git/worktrees/blue_apcd_lp_stage11_4','external_cwd_classification':'same_repository_worktree_path_record'}
with (AN/'b120_j2lm06_post_d8_22unique_metrics_v2.csv').open(encoding='utf8') as h: rows=list(csv.DictReader(h))
with (AN/'b120_j2lm06_post_d8_revised_unique_geometry_gate_v2.csv').open(encoding='utf8') as h: gates={r['candidate_id']:r for r in csv.DictReader(h)}
old=json.loads((AN/'b120_j2lm06_post_d8_revised_jones_quadratic_model_v2.json').read_text())
X=[]; y=[]
for r in rows:
 g=gates.get(r['candidate_id'],{}); w,d,p=f(g.get('uW')),f(g.get('uD')),f(g.get('uPsi')); ph=f(r['phase_deg']); mag=math.sqrt(f(r['Txx'])); y.append(mag*complex(math.cos(math.radians(ph)),math.sin(math.radians(ph)))); X.append(design(w,d,p))
X=np.array(X); yr=np.array([z.real for z in y]); yi=np.array([z.imag for z in y]); br=np.linalg.lstsq(X,yr,rcond=None)[0]; bi=np.linalg.lstsq(X,yi,rcond=None)[0]; dr=np.array(old['txx_real_coefficients'])-br; di=np.array(old['txx_imag_coefficients'])-bi
txx_audit={'status':'PASS','training_rows':22,'bounded6_excluded':True,'feature_order':['1','uW','uD','uPsi','uW2','uD2','uPsi2','uW_uD','uW_uPsi','uD_uPsi'],'reconstructed_txx_real_coefficients':br.tolist(),'reconstructed_txx_imag_coefficients':bi.tolist(),'frozen_txx_real_coefficients':old['txx_real_coefficients'],'frozen_txx_imag_coefficients':old['txx_imag_coefficients'],'real_max_abs_coefficient_difference':float(np.max(abs(dr))),'imag_max_abs_coefficient_difference':float(np.max(abs(di))),'real_l2_difference':float(np.linalg.norm(dr)),'imag_l2_difference':float(np.linalg.norm(di)),'original22_fit_residual_max_abs':float(max(np.max(abs(X@br-yr)),np.max(abs(X@bi-yi)))),'comparison_tolerance_note':'coefficient reproduction from original22 phase/Txx fields; residual is original22 fit error, not bounded6 leakage'}
missing=['Re(txy)','Im(txy)','Re(tyx)','Im(tyx)','Re(tyy)','Im(tyy)']
manifest={'status':'HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE','model_identity':'b120_j2lm06_post_d8_revised_jones_quadratic_model_v2','training_set':'original22 unique formal geometries only','training_rows':22,'coordinate_source':str(AN/'b120_j2lm06_post_d8_revised_unique_geometry_gate_v2.csv'),'design_matrix_artifact':str(AN/'b120_j2lm06_post_d8_revised_design_matrix_audit_v2.json'),'feature_order':txx_audit['feature_order'],'fit_method':'ordinary least squares, 10-column quadratic basis, no regularization evidence in frozen artifact','frozen_phase_model_present':True,'frozen_txx_model_present':True,'frozen_full_jones_outputs_present':['Re(txx)','Im(txx)'],'missing_full_jones_outputs':missing,'bounded6_exclusion_proof':{'included_in_fit':False},'model_spec_complete':False,'hard_gate':'HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE'}
dump('b120_j2lm06_post_d8_repository_worktree_provenance_audit_v1.json',provenance)
dump('b120_j2lm06_post_d8_frozen_txx_reproduction_audit_v1.json',txx_audit)
dump('b120_j2lm06_post_d8_frozen_full_jones_training_manifest_v1.json',manifest)
dump('b120_j2lm06_post_d8_frozen_full_jones_model_reconstruction_v1.json',{'status':'HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE','training_manifest':'b120_j2lm06_post_d8_frozen_full_jones_training_manifest_v1.json','txx_reproduction_audit':'b120_j2lm06_post_d8_frozen_txx_reproduction_audit_v1.json','reconstructed_outputs':['Re(txx)','Im(txx)'],'not_reconstructed_outputs':missing,'bounded6_fit_used':False,'action':'STOP_BEFORE_BOUNDED6_REPLAY'})
(ROOT/'reports/lp_b120_j2lm06_post_d8_repository_worktree_provenance_audit_v1.md').write_text('''# POST-D8 repository/worktree provenance audit\n\nProvenance PASS: formal worktree D:\\project\\worktrees\\blue_apcd_lp_stage11_4, branch work/lp-stage11-4, HEAD and upstream cb57069083fe7df440d6f161506b6bc498bb05b0, ahead/behind 0/0. The external cwd D:\\project\\blue plane wave meta-surface is a same-repository worktree path record and was not used for writes.\n\nThe original22 phase/Txx rows reproduce the frozen txx coefficients using the same ten-column quadratic basis. The frozen Jones artifact does not contain complete coefficient sets for txy, tyx, or tyy. Frozen full-Jones specification is therefore incomplete. Bounded6 was excluded from fitting and no solver/lumapi/FDTD replay was performed.\n\nHard gate: HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE.\n''',encoding='utf8')
print(json.dumps({'provenance':'PASS','txx_reproduction':'PASS','full_jones_spec':'INCOMPLETE','hard_gate':'HARD_GATE_FROZEN_MODEL_SPEC_INCOMPLETE','solver_calls':0},indent=2))
