import csv, json
from pathlib import Path
ROOT=Path(r'D:\\project\\worktrees\\blue_apcd_lp_stage11_4')
ANA=ROOT/'outputs/lp_ml_dataset_v1/analysis'; PL=ROOT/'outputs/lp_ml_dataset_v1/plans'
def test_bridge_gap_plan_contract():
    p=json.loads((PL/'b120_j2lm06_prospective_actual_node_bridge_diagnostic_plan_v1.json').read_text())
    assert p['candidate_count']==8 and p['subruns']==16 and p['wavelength_nm']==[450]
    assert p['status']=='PLANNED_PROSPECTIVE_BRIDGE_DIAGNOSTIC' and p['future_batch_1']['geometry_count']==4
    assert all('D9' not in c['candidate_id'] for c in p['candidates'])
    assert len({c['geometry']['exact_geometry_hash_sha256'] for c in p['candidates']})==8
    g=json.loads((ANA/'b120_j2lm06_actual_node_formal_graph_components_v1.json').read_text())
    assert g['node_count']==24 and g['edge_count']==74 and all(m['component_count']>1 for m in g['thresholds'].values())
    assert json.loads((ANA/'b120_j2lm06_actual_node_bridge_barrier_diagnosis_v1.json').read_text())['barrier_diagnosis'] in {'SPARSE_ACTUAL_NODE_SAMPLING_GAP_DOMINANT','JONES_CONTINUITY_THRESHOLD_BARRIER_DOMINANT','PROJECTOR_GUARD_BARRIER_DOMINANT','MIXED_JONES_PROJECTOR_BRIDGE_BARRIER','MANUFACTURING_TOPOLOGY_BARRIER','ACTIVE_VARIABLE_INSUFFICIENCY_SUSPECTED'}
