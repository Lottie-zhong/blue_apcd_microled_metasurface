import csv,json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); A=R/'outputs/lp_ml_dataset_v1/analysis'; P=R/'outputs/lp_ml_dataset_v1/plans'
def test_dual_anchor_pool():
 d=json.loads((P/'b120_j2lm06_post_d8_dual_anchor_bounded_candidate_plan_v1.json').read_text()); assert d['status']=='PLANNING_ONLY_NOT_AUTHORIZED'; assert len(d['candidates'])==6; assert sum(c['role'] in ('PHASE_ROBUST_DESCENT','PHASE_NEGATIVE_CURVATURE_PROBE') for c in d['candidates'])==2; assert sum(c['role'] in ('PROJECTOR_SAFE_PROGRESS','TRADEOFF_ROBUST_PROGRESS') for c in d['candidates'])==2; assert sum(c['role'].endswith('DIAGNOSTIC') for c in d['candidates'])==2; assert not any(c['candidate_id'].startswith('D9_') for c in d['candidates']); assert d['future_budget']=={'geometries':6,'x_y_subruns':12,'wavelength_nm':[450]}
def test_outer_shell_and_labels():
 d=json.loads((P/'b120_j2lm06_post_d8_dual_anchor_bounded_candidate_plan_v1.json').read_text()); assert all(any(abs(v)==2 for v in c['normalized_coordinate']) for c in d['candidates']); assert all(c['physics_label']=='ABSENT_NOT_SIMULATED' and c['prediction_label']=='MODEL_PREDICTION_NOT_PHYSICS_LABEL' for c in d['candidates']); assert all(c['geometry']['no_overlap'] and c['manufacturing_margin_nm']>=0 for c in d['candidates'])
