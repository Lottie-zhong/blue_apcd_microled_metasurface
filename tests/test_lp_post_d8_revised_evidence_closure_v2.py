import json
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
AN=ROOT/'outputs/lp_ml_dataset_v1/analysis'
def test_revised_evidence_counts_and_rank():
 e=json.loads((AN/'b120_j2lm06_post_d8_revised_evidence_closure_audit_v2.json').read_text())
 assert (e['new_geometry_count'],e['planned_subruns'],e['accepted'],e['failed'],e['missing'])==(13,26,26,0,0)
 assert e['new_complete_jones']==13 and e['unique_complete_jones']==22
 d=json.loads((AN/'b120_j2lm06_post_d8_revised_design_matrix_audit_v2.json').read_text())
 assert d['rank']==10 and d['alias_rows_excluded_from_fit']==5
def test_outcome_and_no_d9():
 o=json.loads((AN/'b120_j2lm06_post_d8_revised_outcome_v2.json').read_text())
 assert o['outcome']=='REVISED_QUADRATIC_MODEL_PHASE_VALID_PROJECTOR_PARTIAL' and o['no_d9']
