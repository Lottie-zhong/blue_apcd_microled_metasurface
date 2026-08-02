import csv, json
from pathlib import Path

ROOT = Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
ANA = ROOT/'outputs/lp_ml_dataset_v1/analysis'
STG = ROOT/'outputs/lp_ml_dataset_v1/staging/b120_j2lm06_prospective_actual_node_bridge_batch1_v1'
IDS = ['PDBG_PHASE_EXIT_01','PDBG_PROJECTOR_EXIT_03','PDBG_CUT_SPLITTER_05','PDBG_ALT_PATH_07']

def j(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def test_batch1_manifest_and_accounting():
    a=j(STG/'solver_accounting.json'); assert a['planned']==a['raw_invocations']==a['successful']==a['accepted']==8
    assert a['failed']==a['missing']==a['duplicate_invocations']==a['unauthorized_invocations']==0
    assert a['wavelengths_nm']==[450]
    b=j(STG/'batch_1_results.json'); assert b['candidate_ids']==IDS and b['batch2_authorized'] is False and b['d9_authorized'] is False
    assert not list((ROOT/'outputs/lp_ml_dataset_v1/staging').glob('*batch2*'))
    assert not list((ROOT/'outputs/lp_ml_dataset_v1/execution_packages').glob('*batch2*'))

def test_batch1_jones_and_provenance():
    rows=list(csv.DictReader((ANA/'b120_j2lm06_prospective_actual_node_bridge_batch1_candidate_metrics_v1.csv').open(encoding='utf-8')))
    assert [r['candidate_id'] for r in rows]==IDS
    assert all(float(r['wavelength_nm'])==450.0 for r in rows)
    assert all(r['physics_label']=='PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS' for r in rows)
    assert all(r['observable_label']=='FORMAL_WEIGHTED_G0_JONES' for r in rows)
    assert all(r['projector_lineage']=='projector_preserved_from_backbone' for r in rows)
    audit=j(ANA/'b120_j2lm06_prospective_actual_node_bridge_batch1_complete_jones_audit_v1.json')
    assert audit['candidate_count']==4 and audit['subrun_count']==8 and audit['status']=='PASS'

def test_batch1_graph_gate_and_no_d9():
    g=j(ANA/'b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json')
    assert g['node_count']==38 and g['edge_count']==92 and g['batch2_authorized'] is False and g['d9_authorized'] is False
    assert g['batch1_additions']==IDS
    gate=j(ANA/'b120_j2lm06_prospective_actual_node_bridge_batch1_graph_gate_v1.json')
    assert gate['outcome']=='BATCH1_DIAGNOSTIC_NO_FORMAL_CONNECTIVITY_GAIN'
    assert [gate['thresholds'][k]['component_count'] for k in ['1.00','0.75','0.50']]==[7,9,15]
    assert all(not gate['thresholds'][k]['formal_path_exists'] for k in ['1.00','0.75','0.50'])
    assert all(not gate['thresholds'][k]['new_nodes_singleton'] for k in ['1.00','0.75','0.50'])

def test_historical_hard_gate_and_protected_hashes():
    assert 'HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE' in (ROOT/'reports/lp_b120_j2lm06_original22_missing9_regeneration_and_full_jones_replay_v1.md').read_text(encoding='utf-8') if (ROOT/'reports/lp_b120_j2lm06_original22_missing9_regeneration_and_full_jones_replay_v1.md').exists() else True
    import hashlib
    expected={'reports/lp_ml1a3_git_history_geometry_reconstruction.md':'d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161','reports/stage11_4a20_legacy_fsp_object_inventory.md':'ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708'}
    for rel,h in expected.items(): assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h
