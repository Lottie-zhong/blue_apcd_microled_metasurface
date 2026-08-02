import json
from pathlib import Path
ROOT=Path(__file__).parents[1];A=ROOT/'outputs/lp_ml_dataset_v1/analysis';P=ROOT/'outputs/lp_ml_dataset_v1/plans';R=ROOT/'reports'
def ld(n): return json.loads((A/n).read_text())
def test_d9_contract():
 i=ld('b120_j2lm06_d9_evidence_caveat_inventory_v1.json');assert i['start_head_required']=='4866190c027253eff611633b05dd74cb6023213f' and i['cross_branch_execution']['candidate_count']==18 and i['cross_branch_execution']['subrun_count']==36 and i['current_task']['solver_calls']==0 and i['historical_hard_gate']['enum']=='HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE'
 p=ld('b120_j2lm06_d9_phase_gradient_sanity_audit_v1.json');assert p['phase_fit']['max_unwrap_correction_deg']<1e-10 and len(p['phase_fit']['loo_gradients_deg_per_unit'])==6
 b=ld('b120_j2lm06_d9_bridge_threshold_sensitivity_v1.json');assert b['node_count']==20 and set(b['thresholds'])=={'1','0.75','0.5'} and b['solver_calls']==0
 a=ld('b120_j2lm06_d9_anchor_adjudication_v1.json');assert a['outcome']=='RETAIN_EXISTING_DUAL_ANCHORS'
 o=ld('b120_j2lm06_d9_evidence_review_outcome_v1.json');assert o['review_outcome']!='D9_DUAL_ANCHOR_PLANNING_READY_PROSPECTIVE'
 c=json.loads((P/'b120_j2lm06_d9_prospective_planning_contract_v1.json').read_text());assert c['max_geometries']==8 and c['max_xy_subruns']==16 and not c['solver_authorized'] and c['no_D9_geometry_in_this_task']
 assert not list((ROOT/'outputs/lp_ml_dataset_v1/execution_packages').glob('*d9*')) and not list((ROOT/'outputs/lp_ml_dataset_v1/staging').glob('*d9*'))
