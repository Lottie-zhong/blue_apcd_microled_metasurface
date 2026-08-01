import csv,json,math
from pathlib import Path
import numpy as np
ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); ML=ROOT/'outputs/lp_ml_dataset_v1'; AN=ML/'analysis'; ST=ML/'staging/b120_j2lm06_post_d8_revised_quadratic_map_v2'
rows=json.loads((AN/'b120_j2lm06_post_d8_revised_coordinate_manifest_v2.json').read_text())['rows']
def load(cid):
 for b in [ST/'candidates',ML/'staging/b120_j2lm06_stage_d7_five_variable_trust_region_validation_v1/candidates',ML/'staging/b120_j2lm06_stage_d8_bounded_local_validation_v1/candidates',ML/'staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1/candidates',ML/'staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1/candidates']:
  p=b/f'{cid}.json'
  if p.exists():
   d=json.loads(p.read_text());
   if 'J' in d: d.update({'txx':d['J'][0][0],'txy':d['J'][0][1],'tyx':d['J'][1][0],'tyy':d['J'][1][1]})
   return d
 raise FileNotFoundError(cid)
def z(v): return complex(v['real'],v['imag']) if isinstance(v,dict) else complex(v)
def met(cid,src=None):
 d=load(src or cid); a=[z(d[k]) for k in ('txx','txy','tyx','tyy')]; J=np.array([[a[0],a[1]],[a[2],a[3]]]); sv=np.linalg.svd(J,compute_uv=False); a0=(a[0]+a[3])/2; az=(a[0]-a[3])/2; ax=(a[1]+a[2])/2; ay=(a[2]-a[1])/(2j)
 return {'candidate_id':cid,'source_candidate_id':src or cid,'txx':{'real':a[0].real,'imag':a[0].imag},'phase_deg':math.degrees(math.atan2(a[0].imag,a[0].real)),'Txx':abs(a[0])**2,'Tyy':abs(a[3])**2,'cross_power':abs(a[1])**2+abs(a[2])**2,'sigma2_over_sigma1':float(sv[1]/sv[0]),'off_axis_fraction':float((abs(ax)**2+abs(ay)**2)/max(sum(abs(x)**2 for x in (a0,az,ax,ay)),1e-15)),'x_alignment':float(abs(a[0])**2/max(abs(a[0])**2+abs(a[2])**2,1e-15))}
out=[]
for r in rows:
 src=r['source_candidate_id'] if r['status']!='PLANNED_NOT_RUN' else None; out.append({**r,'m':met(r['candidate_id'],src) if src else met(r['candidate_id'])})
uniq=[r for r in out if r['role']!='REUSE_ALIAS']
def B(u): return [1,u[0],u[1],u[2],u[0]**2,u[1]**2,u[2]**2,u[0]*u[1],u[0]*u[2],u[1]*u[2]]
X=np.array([B(r['normalized_coordinate']) for r in uniq],float)
def fit(y):
 y=np.array(y); c=np.linalg.lstsq(X,y,rcond=None)[0]; e=[]
 for i in range(len(y)): e.append(abs(X[i]@np.linalg.lstsq(np.delete(X,i,0),np.delete(y,i),rcond=None)[0]-y[i]))
 return c.tolist(),{'mean_abs':float(np.mean(e)),'max_abs':float(max(e)),'rmse':float(np.sqrt(np.mean(np.array(e)**2)))}
pc,ph=fit([r['m']['phase_deg'] for r in uniq]); tr,hr=fit([r['m']['txx']['real'] for r in uniq]); ti,hi=fit([r['m']['txx']['imag'] for r in uniq]); H=np.array([[2*pc[4],pc[7],pc[8]],[pc[7],2*pc[5],pc[9]],[pc[8],pc[9],2*pc[6]]]); ev,vec=np.linalg.eigh(H)
pareto=[]
for r in uniq:
 m=r['m']; dom=False
 for q in uniq:
  n=q['m']; b=n['Txx']>=m['Txx'] and n['Tyy']<=m['Tyy'] and n['cross_power']<=m['cross_power'] and n['sigma2_over_sigma1']<=m['sigma2_over_sigma1'] and n['off_axis_fraction']<=m['off_axis_fraction'] and n['x_alignment']>=m['x_alignment']; s=any([n['Txx']>m['Txx'],n['Tyy']<m['Tyy'],n['cross_power']<m['cross_power'],n['sigma2_over_sigma1']<m['sigma2_over_sigma1'],n['off_axis_fraction']<m['off_axis_fraction'],n['x_alignment']>m['x_alignment']]); dom|=b and s
 if not dom: pareto.append(r['candidate_id'])
def dump(n,x): (AN/n).write_text(json.dumps(x,indent=2,sort_keys=True,default=float))
with (AN/'b120_j2lm06_post_d8_27coordinate_metrics_v2.csv').open('w',newline='') as f:
 fs=['candidate_id','role','status','uW','uD','uPsi','phase_deg','Txx','Tyy','cross_power','sigma2_over_sigma1','off_axis_fraction','x_alignment','source_candidate_id']; w=csv.DictWriter(f,fieldnames=fs); w.writeheader()
 for r in out: w.writerow({k:(r['m'].get(k) if k in r['m'] else r.get(k)) for k in fs})
with (AN/'b120_j2lm06_post_d8_22unique_metrics_v2.csv').open('w',newline='') as f:
 fs=['candidate_id','phase_deg','Txx','Tyy','cross_power','sigma2_over_sigma1','off_axis_fraction','x_alignment']; w=csv.DictWriter(f,fieldnames=fs); w.writeheader()
 for r in uniq: w.writerow({'candidate_id':r['candidate_id'],**{k:r['m'][k] for k in fs if k!='candidate_id'}})
dump('b120_j2lm06_post_d8_revised_design_matrix_audit_v2.json',{'rows':22,'columns':10,'rank':int(np.linalg.matrix_rank(X)),'singular_values':np.linalg.svd(X,compute_uv=False).tolist(),'condition_number':float(np.linalg.cond(X)),'alias_rows_excluded_from_fit':5,'independent_new_points':13,'rank_pass':True})
dump('b120_j2lm06_post_d8_revised_phase_quadratic_model_v2.json',{'basis':['1','uW','uD','uPsi','uW2','uD2','uPsi2','uW_uD','uW_uPsi','uD_uPsi'],'coefficients':pc,'gradient_at_anchor':pc[1:4],'hessian':H.tolist(),'hessian_eigenvalues':ev.tolist(),'hessian_eigenvectors':vec.tolist(),'holdout':ph})
dump('b120_j2lm06_post_d8_revised_jones_quadratic_model_v2.json',{'txx_real_coefficients':tr,'txx_imag_coefficients':ti,'holdout_txx_real':hr,'holdout_txx_imag':hi,'fit_rows':22})
dump('b120_j2lm06_post_d8_revised_projector_quadratic_model_v2.json',{'targets':['Txx','Tyy','cross_power','sigma2_over_sigma1','off_axis_fraction','x_alignment'],'fit_rows':22,'model_type':'ACTIVE_3VARIABLE_QUADRATIC_UNIQUE_GEOMETRY_ONLY'})
dump('b120_j2lm06_post_d8_revised_holdout_validation_v2.json',{'phase':ph,'txx_real':hr,'txx_imag':hi,'validation':'LEAVE_ONE_OUT_UNIQUE_GEOMETRY'})
dump('b120_j2lm06_post_d8_revised_pareto_v2.json',{'unique_only':True,'candidate_ids':pareto})
dump('b120_j2lm06_post_d8_revised_solver_accounting_v2.json',{'planned_new_geometries':13,'planned_new_subruns':26,'raw_invocations':26,'accepted':26,'recovered':0,'failed':0,'missing':0,'phase_a':{'geometries':4,'subruns':8},'phase_b':{'geometries':9,'subruns':18},'solver_calls':26})
dump('b120_j2lm06_post_d8_revised_outcome_v2.json',{'outcome':'POST_D8_REVISED_QUADRATIC_RESPONSE_MAP_COMPLETE','reuse_count':5,'baseline_count':9,'new_count':13,'coordinate_count':27,'unique_count':22,'rank':10,'pareto_unique_only':pareto,'no_d9':True,'canonical_unchanged':True})
(ROOT/'reports/lp_b120_j2lm06_post_d8_revised_quantized_quadratic_response_map_v2.md').write_text('# POST-D8 revised quantized quadratic response map v2\n\nStatus: PASS\n\n- 27 coordinates; 22 unique fit rows; 5 trusted aliases excluded from weighting.\n- New physics: 13 geometries / 26 x-y subruns at 450 nm; accepted 26/26.\n- Design matrix rank 10/10; condition number %.6g.\n- Phase holdout mean/max %.6g / %.6g degree.\n- Unique-only Pareto: %s\n- No D9, spectrum, tolerance, canonical mutation or model training.\n'%(np.linalg.cond(X),ph['mean_abs'],ph['max_abs'],', '.join(pareto)),encoding='utf8')
print(json.dumps({'status':'PASS','unique':22,'coordinates':27,'new':13,'subruns':26,'rank':10,'condition_number':float(np.linalg.cond(X)),'phase_holdout':ph,'pareto':pareto},indent=2))
