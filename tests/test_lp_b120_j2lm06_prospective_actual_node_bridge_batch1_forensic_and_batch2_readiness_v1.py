import csv, hashlib, json, subprocess
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); A=R/'outputs/lp_ml_dataset_v1/analysis'; S=R/'outputs/lp_ml_dataset_v1/staging/b120_j2lm06_prospective_actual_node_bridge_batch1_v1'
B1=['PDBG_PHASE_EXIT_01','PDBG_PROJECTOR_EXIT_03','PDBG_CUT_SPLITTER_05','PDBG_ALT_PATH_07']; B2=['PDBG_PHASE_EXIT_02','PDBG_PROJECTOR_EXIT_04','PDBG_CUT_SPLITTER_06','PDBG_BASIS_TEST_08']
def j(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def test_predicate_decomposition_reproducible():
 f=j(A/'b120_j2lm06_prospective_actual_node_bridge_batch1_singleton_forensic_v1.json'); assert f['candidate_ids']==B1 and f['solver_calls']==0
 assert f['frozen_predicate_thresholds']['multipliers']==[1.0,0.75,0.5]
 rows=list(csv.DictReader((A/'b120_j2lm06_prospective_actual_node_bridge_batch1_singleton_edge_predicates_v1.csv').open(encoding='utf-8')))
 assert len(rows)==192 and {r['candidate_id'] for r in rows}==set(B1)
 assert all(r['threshold_multiplier'] in {'1.0','0.75','0.5'} for r in rows)
 assert all(r['predicate'] in {'coordinate_comparability','jones_frobenius','phase','Tyy','leakage','sigma_ratio','projector_margin','manufacturing_geometry_legality'} for r in rows)
def test_prediction_physics_separation_and_readiness():
 p=j(A/'b120_j2lm06_prospective_actual_node_bridge_batch1_plan_prediction_realization_audit_v1.json'); assert p['prediction_label']=='MODEL_PREDICTION_NOT_PHYSICS_LABEL' and p['physics_label']=='PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS'; assert p['realized_component_merging_potential']==0
 r=j(A/'b120_j2lm06_prospective_actual_node_bridge_batch2_readiness_v1.json'); assert r['overall_recommendation']=='DO_NOT_AUTHORIZE_BATCH2_UNCHANGED'; assert [x['candidate_id'] for x in r['candidate_readiness']]==B2; assert all(x['solver_calls']==0 and x['plan_unchanged'] for x in r['candidate_readiness'])
def test_no_solver_or_batch2_artifacts():
 a=j(S/'solver_accounting.json'); assert a['solver_calls']==8 and a['raw_invocations']==8
 events=[json.loads(x) for x in (S/'solver_entry_events.ndjson').read_text(encoding='utf-8').splitlines()]; assert sum('entered_utc' in x for x in events)==8
 assert not list((R/'outputs/lp_ml_dataset_v1/staging').glob('*batch2*')); assert not list((R/'outputs/lp_ml_dataset_v1/execution_packages').glob('*batch2*'))
 assert not any('D9' in p.name for p in (R/'outputs/lp_ml_dataset_v1').rglob('*') if p.is_file() and 'batch1' not in str(p).lower())
def test_frozen_plan_and_protected_integrity():
 plan=R/'outputs/lp_ml_dataset_v1/plans/b120_j2lm06_prospective_actual_node_bridge_diagnostic_plan_v1.json'; assert hashlib.sha256(plan.read_bytes()).hexdigest()=='4bdde0aededb6d7fcb9fa06c69e8e8ae0860f24f1043482521aecf3751b23f83'; assert j(plan)['candidate_order']==['PDBG_PHASE_EXIT_01','PDBG_PHASE_EXIT_02','PDBG_PROJECTOR_EXIT_03','PDBG_PROJECTOR_EXIT_04','PDBG_CUT_SPLITTER_05','PDBG_CUT_SPLITTER_06','PDBG_ALT_PATH_07','PDBG_BASIS_TEST_08']
 for rel,h in {'reports/lp_ml1a3_git_history_geometry_reconstruction.md':'d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161','reports/stage11_4a20_legacy_fsp_object_inventory.md':'ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'}.items(): assert hashlib.sha256((R/rel).read_bytes()).hexdigest()==h
 rel='outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_actual_node_formal_graph_components_v1.json'; assert subprocess.check_output(['git','hash-object','--path',rel,str(R/rel)],cwd=str(R),text=True).strip()==subprocess.check_output(['git','rev-parse','e594702369b0a7a56644525cfa0570360797d77a:'+rel],cwd=str(R),text=True).strip()
