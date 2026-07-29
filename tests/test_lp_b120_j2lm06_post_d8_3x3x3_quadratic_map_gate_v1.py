import csv, hashlib, json
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_lp_stage11_4'); A=R/'outputs/lp_ml_dataset_v1/analysis'; P=R/'outputs/lp_ml_dataset_v1/plans'; S=R/'outputs/lp_ml_dataset_v1/staging'
def j(p): return json.loads(p.read_text())
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def test_grid_contract_conflict_is_exact():
 m=j(A/'b120_j2lm06_post_d8_27point_cube_manifest_v1.json'); assert m['status']=='HARD_GATE_DATA_CONFLICT'; assert m['normalized_coordinate_count']==27; assert m['existing_declared_coordinate_count']==9; assert m['new_declared_coordinate_count']==18; assert m['duplicate_new_coordinate_count']==5; assert m['new_physically_unique_count']==13; assert m['maximum_physical_unique_count_under_contract']==22; assert all(c['formal_complete_jones_verified'] for c in m['conflicts']); assert all(x['evidence']['physics_label']=='FORMAL_ACCEPTED_WEIGHTED_G0' for c in m['conflicts'] for x in c['formal_evidence'])
def test_conflicting_ids_and_no_dynamic_replacement():
 m=j(A/'b120_j2lm06_post_d8_27point_cube_manifest_v1.json'); ids={x['planned_candidate_id'] for x in m['conflicts']}; assert ids=={'POSTD8_QMAP_WM_D0_P0','POSTD8_QMAP_W0_D0_PM','POSTD8_QMAP_WP_D0_PM','POSTD8_QMAP_WM_D0_PP','POSTD8_QMAP_WM_D0_PM'}; p=j(P/'b120_j2lm06_post_d8_3x3x3_quadratic_map_plan_v1.json'); assert not p['dynamic_replacement']; assert not p['existing_geometry_rerun']; assert not p['execution_authorized']
def test_geometry_gate_has_18_rows_and_five_duplicates():
 with (A/'b120_j2lm06_post_d8_3level_grid_geometry_gate_v1.csv').open(newline='') as f: rows=list(csv.DictReader(f)); assert len(rows)==18; assert sum(int(r['duplicate_count'])>0 for r in rows)==5; assert all(r['center_grid_pass']=='True' and r['manufacturing_pass']=='True' for r in rows)
def test_solver_accounting_pre_solver_stop():
 a=j(A/'b120_j2lm06_post_d8_quadratic_map_solver_accounting_v1.json'); assert a['planned_geometries']==18 and a['planned_subruns']==36; assert a['raw_invocations']==a['accepted']==a['recovered']==a['failed']==0; assert a['pre_solver_compatibility_stops']==1; assert a['solver_entered_records']==0; assert a['phase_a_status']=='NOT_STARTED_HARD_GATE' and a['phase_b_status']=='NOT_STARTED_HARD_GATE'
def test_no_execution_package_or_physics_staging():
 assert not (R/'outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_post_d8_3x3x3_quadratic_map_execution_package_v1').exists(); assert not (S/'b120_j2lm06_post_d8_3x3x3_quadratic_map_v1').exists()
def test_outcome_and_no_model_claim():
 o=j(A/'b120_j2lm06_post_d8_quadratic_map_outcome_v1.json'); assert o['formal_outcome']=='HARD_GATE_DATA_CONFLICT'; assert o['solver_calls']==0; assert not o['quadratic_model_fit']; assert not o['hessian_published']; assert not o['pareto_computed']; assert o['no_d9']
def test_source_hashes_are_current():
 m=j(A/'b120_j2lm06_post_d8_27point_cube_manifest_v1.json'); assert all(h(R/k)==v for k,v in m['source_hashes'].items())