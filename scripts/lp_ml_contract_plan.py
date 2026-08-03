from __future__ import annotations
import csv, hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
from scipy.stats import qmc

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
PLAN = ROOT / "outputs/lp_ml_dataset_v1/plans"
ANALYSIS = ROOT / "outputs/lp_ml_dataset_v1/analysis"
PLAN.mkdir(parents=True, exist_ok=True); ANALYSIS.mkdir(parents=True, exist_ok=True)

def canon(x): return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()
def sha(x): return hashlib.sha256(canon(x)).hexdigest()
def write_json(p, x):
    t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding='utf-8'); os.replace(t,p)
def write_csv(p, rows):
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    t=p.with_suffix(p.suffix+'.tmp')
    with t.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    os.replace(t,p)

FIXED={"H_nm":500.0,"period_x_nm":432.0,"period_y_nm":432.0,"material":"APCD_TIO2_NATIVE_M1","background":"air","source":"normal_incidence_plane_wave","reference_plane":"field_monitor_z_1000_nm","field_monitor_z_nm":1000.0,"mesh":"frozen_mesh_contract","boundaries":"x/y_periodic_z_PML","observable":"coordinate_weighted_full_period_G0","endpoint_handling":"duplicate_endpoint_remove_then_periodic_reclosure","normalization":"sqrt(T)/norm(weighted_Ex,weighted_Ey)","jones_convention":"[[txx,txy],[tyx,tyy]]"}
RANGES={"J1_side_nm":[108,112],"J2_length_nm":[106,110],"J2_width_nm":[98,102],"D_nm":[196.0,204.0],"Psi_deg":[-1.2,1.2]}

def geom_hash(j1,l,w,cx,cy):
    g={"J1_shape":"sharp_rectangle","J1_side_nm":float(j1),"J2_shape":"sharp_rectangle","J2_length_nm":float(l),"J2_width_nm":float(w),"J1_center_x_nm":-float(cx),"J1_center_y_nm":-float(cy),"J2_center_x_nm":float(cx),"J2_center_y_nm":float(cy),"J1_rotation_deg":0.0,"J2_rotation_deg":0.0,**FIXED}
    return sha(g), g

existing=set(); existing_vectors=set()
gm=ROOT/'outputs/lp_ml_dataset_v1/canonical_v1_21/geometry_master_v1_17.csv'
if gm.exists():
    with gm.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            try:
                j=float(r.get('J1_side_nm') or 0); l=float(r.get('J2_length_nm') or 0); w=float(r.get('J2_width_nm') or 0)
                cx=abs(float(r.get('J2_center_x_nm') or 0)); cy=abs(float(r.get('J2_center_y_nm') or 0));
                if j and l and w: existing_vectors.add((round(j,3),round(l,3),round(w,3),round(cx,3),round(cy,3)))
                if r.get('exact_geometry_hash'): existing.add(r['exact_geometry_hash'])
            except Exception: pass

def feasible(j,l,w,cx,cy):
    direct=2*math.hypot(cx,cy)-max(j,w)
    # conservative periodic image margin based on rectangular bounding boxes
    periodic=min(432-2*cx-max(j,w), 432-2*abs(cy)-max(j,l))
    return direct>=60 and periodic>=60 and cx+max(j,l)/2<216 and abs(cy)+max(j,w)/2<216

def make_row(i,cat,j,l,w,cx,cy,role):
    D=2*math.hypot(cx,cy); psi=math.degrees(math.atan2(cy,cx)) if cx else 90.0
    eh,g=geom_hash(j,l,w,cx,cy)
    return {"candidate_id":f"LPML_R1_{cat}_{i:03d}","category":cat,"role":role,"candidate_order":i,"J1_side_nm":int(j),"J2_length_nm":int(l),"J2_width_nm":int(w),"D_nm":D,"Psi_deg":psi,"requested_D_nm":D,"requested_Psi_deg":psi,"J1_center_x_nm":-cx,"J1_center_y_nm":-cy,"J2_center_x_nm":cx,"J2_center_y_nm":cy,"H_nm":500.0,"period_x_nm":432.0,"period_y_nm":432.0,"material":"APCD_TIO2_NATIVE_M1","direct_gap_nm":2*math.hypot(cx,cy)-max(j,w),"periodic_gap_nm":min(432-2*cx-max(j,w),432-2*abs(cy)-max(j,l)),"integer_or_half_grid_centers":True,"primitive_valid":True,"manufacturing_pass":True,"exact_geometry_hash_sha256":eh,"canonical_relative_geometry_hash_sha256":sha({"J1_side_nm":int(j),"J2_length_nm":int(l),"J2_width_nm":int(w),"cx_abs":cx,"cy_abs":abs(cy),"H_nm":500.0,"period":432.0}),"symmetry_equivalence_geometry_hash_sha256":sha({"J1_side_nm":int(j),"J2_length_nm":int(l),"J2_width_nm":int(w),"radius":round(math.hypot(cx,cy),6),"H_nm":500.0,"period":432.0}),"duplicate_against_formal":False,"planning_status":"PLANNED_NOT_RUN","physics_status":"ABSENT_NOT_SIMULATED","prediction_status":"MODEL_PREDICTION_NOT_PHYSICS_LABEL","wavelength_authorization":"450.0-454.0_nm_step_0.5_nm","fixed_contract_hash":sha(FIXED)}

rows=[]; used=set(); vectors=set()
def add(cat, role, vals):
    j,l,w,cx,cy=vals; key=(int(j),int(l),int(w),round(cx,3),round(cy,3));
    if key in used or key in existing_vectors or not feasible(*vals): return False
    r=make_row(len(rows)+1,cat,int(j),int(l),int(w),float(cx),float(cy),role)
    if r['exact_geometry_hash_sha256'] in existing: return False
    used.add(key); vectors.add(key); rows.append(r); return True

sob=qmc.Sobol(d=5,scramble=False,seed=0).random_base2(m=8)
for u in sob:
    j=round(108+4*u[0]); l=round(106+4*u[1]); w=round(98+4*u[2]);
    cx=round((98+4*u[3])*2)/2; cy=round((-2+4*u[4])*2)/2
    add('GLOBAL_SOBOL','GLOBAL_FEASIBLE_SPACE', (j,l,w,cx,cy))
    if sum(1 for r in rows if r['category']=='GLOBAL_SOBOL')>=128: break

def region(base, cat, role, n, seed):
    rng=np.random.default_rng(seed); tries=0
    while sum(1 for r in rows if r['category']==cat)<n and tries<10000:
        tries+=1
        du=rng.integers(-2,3,size=3); dcx=float(rng.choice([-1.5,-1,-.5,0,.5,1,1.5])); dcy=float(rng.choice([-1,-.5,0,.5,1]))
        vals=(base[0]+int(du[0]),base[1]+int(du[1]),base[2]+int(du[2]),round((base[3]+dcx)*2)/2,round((base[4]+dcy)*2)/2)
        add(cat,role,vals)
region((110,107,100,100.0,0.5),'PHASE_REGION','PHASE_REGION',64,101)
region((110,106,99,100.0,1.0),'PROJECTOR_REGION','PROJECTOR_REGION',32,202)
region((108,110,102,98.0,2.0),'BOUNDARY_FAILURE','BOUNDARY_FAILURE_LEARNING',32,303)
assert sum(r['category']=='GLOBAL_SOBOL' for r in rows)==128
assert sum(r['category']=='PHASE_REGION' for r in rows)==64
assert sum(r['category']=='PROJECTOR_REGION' for r in rows)==32
assert sum(r['category']=='BOUNDARY_FAILURE' for r in rows)==32
assert len(rows)==256 and len({r['exact_geometry_hash_sha256'] for r in rows})==256

sm=[]
for cat,n in [('GLOBAL_SOBOL',8),('PHASE_REGION',4),('PROJECTOR_REGION',2),('BOUNDARY_FAILURE',2)]: sm += [r for r in rows if r['category']==cat][:n]
assert len(sm)==16
for i,r in enumerate(sm,1): r['smoke_order']=i; r['smoke_status']='PLANNED_NOT_RUN'; r['smoke_physics_label']='ABSENT_NOT_SIMULATED'

contract={"contract_version":"LP_ML_DATASET_V1","status":"FROZEN_FOR_ROUND1_SMOKE","d9_closeout":{"D9_status":"CONTRACT_EVIDENCE_GAP","solver_authorized":False,"candidate_generation_authorized":False,"old_batch_B_authorized":False,"old_batch_2_authorized":False,"bridge_status":"PAUSED","absolute_projector_guard":"NOT_IDENTIFIABLE","phase_anchor_retained":True,"historical_hard_gate":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"},"input_features":["J1_side_nm","J2_length_nm","J2_width_nm","D_nm","Psi_deg","sin_Psi","cos_Psi"],"fixed_physics":FIXED,"raw_labels":{"complex_jones":["txx","txy","tyx","tyy"],"representation":"real_imag_per_element","complete_xy_required":True,"no_symmetry_assumption":True},"derived_labels":{"phase":"wrapped_and_unwrapped_txx_phase_deg","powers":["Txx","Tyy","Txy","Tyx","cross_power_xy_yx","combined_leakage","target_transmission","orthogonal_rejection"],"singular_values":["sigma1","sigma2","sigma2_over_sigma1"],"continuous_metric":"projection_error_apcd_v1","manufacturing":["direct_gap_nm","periodic_gap_nm","primitive_valid","manufacturing_pass"]},"projection_error_apcd_v1":{"target_jones_real_imag":[[1.0,0.0],[0.0,0.0]],"formula":"1 - abs(vdot(J_target,J))^2/(norm_F(J_target)^2*norm_F(J)^2), with best complex scalar removed analytically","continuous_metric_only":True,"absolute_guard":False,"not_equivalent_to_historical_projection_error_fields":True,"scalar_phase_invariant":True,"unit_test_required":True},"historical_seed_audit":{"dedupe_key":"exact_geometry_hash_sha256","aliases_do_not_weight":True,"450_nm_only_not_broadband":True,"plans_predictions_excluded_from_physics":True,"batch_a_4_allowed_as_post_canonical_prospective_physics":True,"contaminated_historical_geometry_or_observable":"excluded_or_quarantined"},"round1":{"full_plan_count":256,"composition":{"GLOBAL_SOBOL":128,"PHASE_REGION":64,"PROJECTOR_REGION":32,"BOUNDARY_FAILURE":32},"smoke_count":16,"smoke_composition":{"GLOBAL_SOBOL":8,"PHASE_REGION":4,"PROJECTOR_REGION":2,"BOUNDARY_FAILURE":2},"no_existing_formal_geometry_duplicates":True,"selection_not_model_best":True},"broadband_smoke":{"geometry_count":16,"solver_entries_max":32,"wavelengths_nm":[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0],"spectral_rows_expected":144,"lifecycle":"x->checkpoint->reload->acceptance->9 wavelengths; y->checkpoint->reload->acceptance->9 wavelengths","entered_accounting_before_run":True,"no_auto_rerun":True},"labels":{"projector_pass_fail":"FORBIDDEN","d9_approval":"FORBIDDEN","phase_library_promotion":"FORBIDDEN","model_fill":"FORBIDDEN"},"solver_ceiling":{"planned_subruns":32,"wavelength_nm_only":[450.0,454.0],"no_process_termination":True}}

write_json(PLAN/'lp_ml_dataset_v1_contract_v1.json',contract)
write_json(PLAN/'lp_ml_dataset_v1_input_schema_v1.json',{"schema_version":"LP_ML_INPUT_V1","fields":contract['input_features']+["H_nm","period_x_nm","period_y_nm","material"],"quantization":"integer dimensions; half-grid centers; no sub-grid"})
write_json(PLAN/'lp_ml_dataset_v1_raw_label_schema_v1.json',{"schema_version":"LP_ML_RAW_LABEL_V1","fields":[f'{e}_{part}' for e in ('txx','txy','tyx','tyy') for part in ('real','imag')]+['source_T','normalization_scale','selected_power','closure_residual','complex_normalization_residual'],"required":"complete x/y formal weighted-G0"})
write_json(PLAN/'lp_ml_dataset_v1_derived_label_schema_v1.json',{"schema_version":"LP_ML_DERIVED_LABEL_V1","fields":sum([['phase_wrapped_deg','phase_unwrapped_deg'],['Txx','Tyy','Txy','Tyx','cross_power_xy_yx','combined_leakage','target_transmission','orthogonal_rejection'],['sigma1','sigma2','sigma2_over_sigma1'],['projection_error_apcd_v1'],['direct_gap_nm','periodic_gap_nm','primitive_valid','manufacturing_pass']],[]),"projector_labels":"none"})
write_json(PLAN/'lp_ml_dataset_v1_projection_error_apcd_v1.json',contract['projection_error_apcd_v1'])
write_json(PLAN/'lp_ml_dataset_v1_5d_design_space_contract_v1.json',{"ranges":RANGES,"fixed":FIXED,"envelope_basis":"conservative common range recovered from canonical_v1.21/D5-D8/bounded/Batch-A/manufacturing contracts","conflicts_recorded":["legacy canonical broad D/J2 dimensions exceed active D7-D8 local family; conservative active-family envelope selected","Psi center-derived from half-grid centers"],"no_arbitrary_expansion":True})
write_csv(PLAN/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv',rows); write_json(PLAN/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.json',{"plan_version":"LP_ML_ROUND1_256_V1","candidate_count":256,"composition":{"GLOBAL_SOBOL":128,"PHASE_REGION":64,"PROJECTOR_REGION":32,"BOUNDARY_FAILURE":32},"candidates":rows,"sha256":sha(rows)})
write_csv(PLAN/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv',sm); write_json(PLAN/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.json',{"plan_version":"LP_ML_ROUND1_SMOKE_16_V1","candidate_count":16,"candidates":sm,"sha256":sha(sm)})
write_json(PLAN/'lp_ml_dataset_v1_broadband_smoke_execution_contract_v1.json',{"contract_version":"LP_ML_BROADBAND_SMOKE_EXECUTION_V1","status":"AUTHORIZED","geometry_count":16,"subrun_count":32,"wavelengths_nm":[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0],"source_contract_sha256":sha(contract),"smoke_plan_sha256":sha(sm),"solver_entered_accounting":"atomic before fdtd.run","no_auto_retry":True,"failure_outcome_enum":["LP_ML_PIPELINE_SMOKE_PASS_READY_FOR_ROUND1_PRODUCTION","LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED","LP_ML_PIPELINE_SMOKE_HARD_GATE"]})
write_json(PLAN/'lp_ml_dataset_v1_dataset_manifest_v1.json',{"manifest_version":"LP_ML_DATASET_V1","seed_scope":"historical seed audit metadata only","physics_rows_included":"formal complete weighted-G0 only","plans_predictions_excluded":True,"d9_closeout":contract['d9_closeout']})
write_csv(PLAN/'lp_ml_dataset_v1_historical_seed_inclusion_exclusion_audit_v1.csv',[{"cohort":"canonical_v1.21 formal","status":"AUDIT_REQUIRED_BEFORE_MODEL_USE","include_rule":"complete native weighted-G0 x/y with compatible reference/normalization","dedupe":"exact_geometry_hash_sha256","notes":"450-only is not broadband"},{"cohort":"D5-D8/bounded/Batch-A","status":"COHORT_METADATA_ONLY_UNTIL_ROW_AUDIT","include_rule":"formal prospective complete Jones may be included with origin labels","dedupe":"exact_geometry_hash_sha256","notes":"no plans/predictions"},{"cohort":"historical hard-gate contaminated","status":"EXCLUDE_OR_QUARANTINE","include_rule":"none","dedupe":"none","notes":"preserve hard-gate evidence"}])
write_json(PLAN/'lp_ml_dataset_v1_historical_seed_inclusion_exclusion_audit_v1.json',{"dedupe_key":"exact_geometry_hash_sha256","aliases_do_not_weight":True,"cohorts":["canonical_v1.21","D5-D8","bounded","Batch-A","historical_hard_gate_quarantine"],"wavelength_note":"450-only seeds not broadband","plans_predictions_excluded":True})
write_json(ANALYSIS/'lp_ml_dataset_v1_wavelength_coverage_summary_v1.json',{"contract_wavelengths_nm":[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0],"expected_rows":144,"smoke_geometries":16,"solver_entries_max":32})
print(json.dumps({"plan_count":len(rows),"smoke_count":len(sm),"composition":{c:sum(r['category']==c for r in rows) for c in ['GLOBAL_SOBOL','PHASE_REGION','PROJECTOR_REGION','BOUNDARY_FAILURE']},"protected":True},indent=2))
