import json, hashlib
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_lp_stage11_4')
A=R/'outputs/lp_ml_dataset_v1/analysis'; P=R/'outputs/lp_ml_dataset_v1/plans'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def test_hard_gate_and_zero_budget():
 p=json.loads((P/'b120_j2lm06_post_d8_trust_region_shrink_diagnostic_plan_v1.json').read_text()); assert p['status']=='HARD_GATE_QUANTIZATION_FLOOR_PREVENTS_MEANINGFUL_SHRINK'; assert p['probe_count']==0; assert p['future_budget']['geometries']==0; assert p['future_budget']['x_y_subruns']==0; assert p['no_solver_authorization'] and p['no_d9_authorization']
def test_quantization_alpha_audit():
 a=json.loads((A/'b120_j2lm06_post_d8_trust_region_shrink_factor_audit_v1.json').read_text()); assert a['solver_calls']==0; assert a['quantization_floor']['hard_gate']; assert a['quantization_floor']['collapse_alphas']==[0.2,0.125]; assert a['quantization_floor']['minimum_nonzero_integer_width_alpha']==1.0; assert a['central_gradient']['rank']==3; assert a['curvature']['sign_consistency'] is True
 rows=a['rows']; assert len(rows)==26; assert sum(r['duplicate_anchor'] for r in rows if r['design']=='A_UNIFORM_RADIAL')==8; assert all(r['manufacturing_pass'] for r in rows)
def test_designs_rejected_and_no_staging():
 d=json.loads((A/'b120_j2lm06_post_d8_trust_region_design_comparison_v1.json').read_text()); assert all(x['status']=='REJECTED_QUANTIZATION' for x in d['design_summaries']); assert not (R/'outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_post_d8_trust_region_shrink_v1').exists(); assert not (R/'outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_trust_region_shrink_v1').exists()
def test_contract_no_solver_and_label_separation():
 e=json.loads((P/'b120_j2lm06_post_d8_trust_region_shrink_execution_contract_v1.json').read_text()); m=json.loads((P/'b120_j2lm06_post_d8_trust_region_shrink_ml_label_contract_v1.json').read_text()); assert e['solver_calls']==0 and e['status']=='PLANNING_ONLY_NOT_AUTHORIZED'; assert m['physics_fields']=='ABSENT_NOT_SIMULATED' and m['prediction_label']=='MODEL_PREDICTION_NOT_PHYSICS_LABEL'; assert m['no_prediction_physics_mixing']
def test_primary_sources_bound():
 a=json.loads((A/'b120_j2lm06_post_d8_trust_region_shrink_factor_audit_v1.json').read_text()); for_rel=['outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json','outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json']; assert all(a['source_hashes'][x]==h(R/x) for x in for_rel)
