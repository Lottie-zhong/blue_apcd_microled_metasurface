from __future__ import annotations
import csv, hashlib, itertools, json, math
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_lp_stage11_4'); ML=ROOT/'outputs/lp_ml_dataset_v1'; AN=ML/'analysis'; PL=ML/'plans'; REP=ROOT/'reports'
EXPECTED_HEAD='4f4964310c88e05768816f6129ef78f4e027a79c'; ANCHOR='D8_TRV_PLAN_d6f4911593b64495'
OUT_GATE=AN/'b120_j2lm06_post_d8_3level_grid_geometry_gate_v1.csv'; OUT_MAN=AN/'b120_j2lm06_post_d8_27point_cube_manifest_v1.json'; OUT_ACCOUNT=AN/'b120_j2lm06_post_d8_quadratic_map_solver_accounting_v1.json'; OUTCOME=AN/'b120_j2lm06_post_d8_quadratic_map_outcome_v1.json'; PLAN=PL/'b120_j2lm06_post_d8_3x3x3_quadratic_map_plan_v1.json'; CHECK=AN/'b120_j2lm06_post_d8_3x3x3_quadratic_map_gate_checksum_v1.json'; REPORT=REP/'lp_b120_j2lm06_post_d8_3x3x3_quadratic_response_map_v1.md'
SOURCES=[PL/'b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json',PL/'b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json',PL/'b120_j2lm06_bounded_local_validation_stage_d8_v1.json',ML/'staging/b120_j2lm06_stage_d8_bounded_local_validation_v1/candidates/D8_TRV_PLAN_d6f4911593b64495.json',ML/'staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1/candidate_metrics.json',ML/'staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1/candidate_metrics.json',AN/'b120_j2lm06_post_d8_curvature_central_gradient_v1.json',AN/'b120_j2lm06_post_d8_curvature_directional_second_difference_v1.json',ML/'canonical_v1_21/canonical_manifest_v1_21.json']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def hobj(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def relhash(g): return hobj({'J1_side_nm':g['J1_side_nm'],'J2_length_nm':g['J2_length_nm'],'J2_width_nm':g['J2_width_nm'],'D_rel_nm':g['D_nm'],'Psi_rel_deg':g['Psi_deg']})
def code(v): return 'P' if v==1 else 'M' if v==-1 else '0'
def cid(u): return f'POSTD8_QMAP_W{code(u[0])}_D{code(u[1])}_P{code(u[2])}'
def make(u):
 c=cid(u); j1=[-100.,-.5]; j2=[100.5+.5*u[1],.5+u[2]]; w=100.+u[0]; dx=j2[0]-j1[0]; dy=j2[1]-j1[1]; d=math.hypot(dx,dy); psi=math.degrees(math.atan2(dy,dx)); g={'candidate_id':c,'normalized_coordinate':list(u),'J1_side_nm':110.,'J2_length_nm':106.,'J2_width_nm':w,'J1_center_nm':j1,'J2_center_nm':j2,'D_nm':d,'Psi_deg':psi,'H_nm':500.,'period_nm':432.,'material':'APCD_TIO2_NATIVE_M1','direct_gap_nm':d-108.,'nearest_periodic_gap_nm':432.-d-108.,'no_overlap':d>=108.,'primitive_valid':True,'center_grid':'INTEGER_OR_EXACT_HALF_NM'}; g['exact_geometry_hash_sha256']=hobj(g); g['canonical_relative_geometry_hash_sha256']=relhash(g); g['symmetry_equivalence_hash_sha256']=relhash(g); return g
coords=list(itertools.product([-1,0,1],repeat=3)); center=(0,0,0); corners=[u for u in coords if all(abs(x)==1 for x in u)]; axes=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]; pairs=[(1,1,0),(1,-1,0),(-1,1,0),(-1,-1,0),(1,0,1),(1,0,-1),(-1,0,1),(-1,0,-1),(0,1,1),(0,1,-1),(0,-1,1),(0,-1,-1)]; new=axes+pairs; geoms=[make(u) for u in new]
assert len(coords)==27 and len(new)==18 and set(new)==set(coords)-{center}-set(corners)
# Evidence tuples from canonical and selected formal plans.
existing=[]; gm=ML/'canonical_v1_21/geometry_master_v1_17.csv'
with gm.open(encoding='utf-8-sig',newline='') as f:
 for r in csv.DictReader(f):
  try: existing.append({'id':r.get('candidate_id','CANONICAL'),'source':'canonical_v1_21','tuple':(round(float(r['J1_side_nm']),9),round(float(r['J2_length_nm']),9),round(float(r['J2_width_nm']),9),round(float(r['D_nm']),9),round(float(r['directed_PSI_deg']),9))})
  except Exception: pass
selected_plans=[PL/'b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json',PL/'b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json',PL/'b120_j2lm06_bounded_local_validation_stage_d8_v1.json']
for p in selected_plans:
 data=json.loads(p.read_text()); stack=[data]
 while stack:
  x=stack.pop()
  if isinstance(x,dict):
   g=x.get('geometry',x)
   if all(k in g for k in ['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg']): existing.append({'id':g.get('candidate_id',x.get('candidate_id','PLAN')),'source':str(p.relative_to(ROOT)).replace('\\','/'),'tuple':(round(float(g['J1_side_nm']),9),round(float(g['J2_length_nm']),9),round(float(g['J2_width_nm']),9),round(float(g['D_nm']),9),round(float(g['Psi_deg']),9))})
   stack.extend(x.values())
  elif isinstance(x,list): stack.extend(x)
def formal_evidence(eid):
    if eid.startswith('D8_TRV_PLAN_'):
        base=ML/'staging/b120_j2lm06_stage_d8_bounded_local_validation_v1'
    elif eid.startswith('POSTD8_CAL_'):
        base=ML/'staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1'
    elif eid.startswith('POSTD8_CURV_'):
        base=ML/'staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1'
    else:
        return None
    cand=base/'candidates'/f'{eid}.json'; x=base/'subruns'/eid/'x'/'checkpoint.json'; y=base/'subruns'/eid/'y'/'checkpoint.json'
    if not (cand.exists() and x.exists() and y.exists()): return None
    data=json.loads(cand.read_text())
    return {'candidate_path':str(cand.relative_to(ROOT)).replace('\\','/'),'candidate_sha256':sha(cand),'x_checkpoint_path':str(x.relative_to(ROOT)).replace('\\','/'),'x_checkpoint_sha256':sha(x),'y_checkpoint_path':str(y.relative_to(ROOT)).replace('\\','/'),'y_checkpoint_sha256':sha(y),'physics_label':data.get('physics_label'),'complete_jones':all(k in data for k in ['txx','txy','tyx','tyy']) or 'Jones' in data}
rows=[]; conflicts=[]
for i,g in enumerate(geoms,1):
 key=(round(g['J1_side_nm'],9),round(g['J2_length_nm'],9),round(g['J2_width_nm'],9),round(g['D_nm'],9),round(g['Psi_deg'],9)); hits=[]
 for e in existing:
  if e['tuple']==key and e['id'] not in {x['id'] for x in hits}: hits.append(e)
 if hits:
  ev=[{'existing_id':h['id'],'evidence':formal_evidence(h['id'])} for h in hits]; conflicts.append({'planned_candidate_id':g['candidate_id'],'normalized_coordinate':g['normalized_coordinate'],'raw_geometry_tuple':list(key),'existing_hits':hits,'formal_evidence':ev,'formal_complete_jones_verified':all(x['evidence'] and x['evidence']['complete_jones'] and x['evidence']['physics_label']=='FORMAL_ACCEPTED_WEIGHTED_G0' for x in ev)})
 rows.append({'execution_order':i,'phase':'A_AXES' if i<=6 else 'B_TWO_VARIABLE','candidate_id':g['candidate_id'],'uW':g['normalized_coordinate'][0],'uD':g['normalized_coordinate'][1],'uPsi':g['normalized_coordinate'][2],'J2_width_nm':g['J2_width_nm'],'D_nm':g['D_nm'],'Psi_deg':g['Psi_deg'],'J1_center_x_nm':g['J1_center_nm'][0],'J1_center_y_nm':g['J1_center_nm'][1],'J2_center_x_nm':g['J2_center_nm'][0],'J2_center_y_nm':g['J2_center_nm'][1],'direct_gap_nm':g['direct_gap_nm'],'nearest_periodic_gap_nm':g['nearest_periodic_gap_nm'],'exact_geometry_hash_sha256':g['exact_geometry_hash_sha256'],'canonical_relative_geometry_hash_sha256':g['canonical_relative_geometry_hash_sha256'],'symmetry_equivalence_hash_sha256':g['symmetry_equivalence_hash_sha256'],'center_grid_pass':all(abs(v*2-round(v*2))<1e-9 for v in g['J1_center_nm']+g['J2_center_nm']),'manufacturing_pass':g['direct_gap_nm']>=60 and g['nearest_periodic_gap_nm']>=60 and g['no_overlap'] and g['primitive_valid'],'duplicate_count':len(hits),'duplicate_ids':'|'.join(h['id'] for h in hits),'gate_status':'HARD_GATE_DATA_CONFLICT' if hits else 'GEOMETRY_LEGAL_UNRUN'})
assert len(conflicts)==5
with OUT_GATE.open('w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
source_hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in SOURCES}
# Symbolic grid has 27 coordinates but five candidate coordinates alias existing physical geometries; only 22 unique physical geometries can result under this mapping.
manifest={'manifest_version':'POST_D8_27POINT_CUBE_MANIFEST_V1','status':'HARD_GATE_DATA_CONFLICT','anchor_id':ANCHOR,'grid_contract':'ACTIVE_SUBSPACE_3LEVEL_GRID_V1','normalized_coordinate_count':27,'existing_declared_coordinate_count':9,'new_declared_coordinate_count':18,'duplicate_new_coordinate_count':5,'new_physically_unique_count':13,'maximum_physical_unique_count_under_contract':22,'grid_coordinates':[list(u) for u in coords],'new_coordinates':[list(u) for u in new],'conflicts':conflicts,'conflict_rule':'new geometry duplicates existing formal geometry; stop and do not replace or rerun','geometry_gate_sha256':sha(OUT_GATE),'source_hashes':source_hashes}; dump(OUT_MAN,manifest)
plan={'plan_version':'POST_D8_ACTIVE_SUBSPACE_3X3X3_QUADRATIC_RESPONSE_MAP_V1','status':'STOPPED_PRE_SOLVER_HARD_GATE_DATA_CONFLICT','expected_head':EXPECTED_HEAD,'anchor_id':ANCHOR,'planned_geometries':18,'planned_subruns':36,'authorized_wavelength_nm':[450],'actual_quantized_mapping':{'J2_width_nm':'100+uW','J2_relative_dx_nm':'200.5+0.5*uD','J2_relative_dy_nm':'1+uPsi','D_Psi_recomputed':True},'candidate_order':[g['candidate_id'] for g in geoms],'conflicting_candidate_ids':[c['planned_candidate_id'] for c in conflicts],'nonconflicting_candidate_ids':[g['candidate_id'] for g in geoms if g['candidate_id'] not in {c['planned_candidate_id'] for c in conflicts}],'execution_authorized':False,'execution_package_created':False,'physics_staging_created':False,'dynamic_replacement':False,'existing_geometry_rerun':False,'solver_calls':0,'source_hashes':source_hashes}; dump(PLAN,plan)
account={'accounting_version':'POST_D8_3X3X3_QUADRATIC_MAP_SOLVER_ACCOUNTING_V1','status':'PRE_SOLVER_HARD_GATE','planned_geometries':18,'planned_subruns':36,'raw_invocations':0,'successful_completions':0,'accepted':0,'recovered':0,'failed':0,'duplicates':5,'missing':36,'unauthorized_runs':0,'pre_solver_compatibility_stops':1,'solver_entered_records':0,'phase_a_status':'NOT_STARTED_HARD_GATE','phase_b_status':'NOT_STARTED_HARD_GATE','execution_package_created':False,'physics_staging_created':False}; dump(OUT_ACCOUNT,account)
outcome={'outcome_version':'POST_D8_3X3X3_QUADRATIC_MAP_OUTCOME_V1','formal_outcome':'HARD_GATE_DATA_CONFLICT','reason':'Five of the required 18 new coordinates map to existing formal geometries under the frozen actual quantized steps; the contract simultaneously requires exactly 18 new geometries and forbids reruns or replacement.','conflicting_candidate_ids':[c['planned_candidate_id'] for c in conflicts],'solver_calls':0,'quadratic_model_fit':False,'hessian_published':False,'pareto_computed':False,'no_d9':True}; dump(OUTCOME,outcome)
report=f'''# APCD LP POST-D8 3x3x3 Quadratic Response Map v1\n\n## Status\n`HARD_GATE_DATA_CONFLICT` before solver entry.\n\n## Environment and accounting\nExpected HEAD `{EXPECTED_HEAD}`. Planned: 18 new geometries / 36 x-y subruns / 450 nm. Actual solver invocations: 0; accepted/recovered/failed: 0/0/0; missing: 36. Phase A and Phase B were not started. No execution package or physics staging was created.\n\n## Geometry-grid conflict\nThe frozen mapping uses J2 width `100+uW`, relative x separation `200.5+0.5*uD` nm and relative y separation `1+uPsi` nm, with D/Psi recomputed from integer/half-grid centers. It produces 27 symbolic coordinates but only 22 physically unique geometries because five required new coordinates duplicate existing formal geometries.\n\n| planned coordinate | planned ID | existing formal geometry |\n|---|---|---|\n'''
for c in conflicts: report += f"| `{tuple(c['normalized_coordinate'])}` | `{c['planned_candidate_id']}` | `{'`, `'.join(h['id'] for h in c['existing_hits'])}` |\n"
report+='''\nThe task contract explicitly requires 18 new geometries and forbids existing-geometry reruns, point removal, substitution, or dynamic insertion. Therefore execution cannot proceed without a revised geometry-grid contract. No quadratic design matrix, active 3x3 Hessian, holdout validation or 27-point Pareto result is claimed.\n\n## Constraints\nExisting D7/D8/recalibration/curvature/canonical physics remained read-only. No D9, K6/K7, spectrum, tolerance, Micro-LED device simulation, canonical merge, model training, solver retry or external-process termination occurred.\n'''
REPORT.write_text(report,encoding='utf-8')
files=[OUT_GATE,OUT_MAN,OUT_ACCOUNT,OUTCOME,PLAN,REPORT]; dump(CHECK,{'manifest_version':'POST_D8_3X3X3_QUADRATIC_MAP_GATE_CHECKSUM_V1','status':'PASS','files':{str(p.relative_to(ROOT)).replace('\\','/'):{'sha256':sha(p),'bytes':p.stat().st_size} for p in files},'source_hashes':source_hashes,'solver_calls':0})
print(json.dumps({'status':'HARD_GATE_DATA_CONFLICT','conflicts':conflicts,'planned_subruns':36,'raw_invocations':0,'execution_package_created':False,'physics_staging_created':False},indent=2))