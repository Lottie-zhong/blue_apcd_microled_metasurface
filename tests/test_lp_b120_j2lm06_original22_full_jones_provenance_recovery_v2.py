import json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); A=R/'outputs/lp_ml_dataset_v1/analysis'
def test_manifest_is_unique_original22():
 d=json.loads((A/'b120_j2lm06_original22_full_jones_provenance_audit_v2.json').read_text())
 assert d['original22_count']==22 and d['alias_rows_excluded']==5
 assert d['classification_counts']['DATA_CONFLICT']==9
 assert d['classification_counts']['FORMAL_COMPLEX_COMPONENTS_MISSING']==0
 assert d['solver_calls']==0
def test_partial_recovery_still_hard_gates_on_hash_conflicts():
 d=json.loads((A/'b120_j2lm06_original22_full_jones_provenance_audit_v2.json').read_text())
 assert d['status']=='HARD_GATE_ORIGINAL22_FORMAL_COMPLEX_JONES_UNRECOVERABLE'
 assert d['classification_counts']['RECONSTRUCTED_FROM_ACCEPTED_XY_WEIGHTED_G0']==13
 assert d['geometry_hash_matches']==13
def test_crosscheck_does_not_override_identity_gate():
 d=json.loads((A/'b120_j2lm06_original22_recovered_jones_consistency_audit_v2.json').read_text())
 assert d['source_txx_metric_crosscheck_rows']==22
 assert d['full_jones_model_completion']=='NOT_AUTHORIZED'
 assert d['bounded6_replay']=='STOPPED_BEFORE_REPLAY'
