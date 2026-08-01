import json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); ML=ROOT/"outputs/lp_ml_dataset_v1"
def test_provenance_gate_and_reachability():
 d=json.loads((ML/"analysis/b120_j2lm06_post_d8_repository_worktree_provenance_audit_v1.json").read_text()); assert d["provenance_gate"]=="PASS"; assert d["cb57069_reachable_from_branch"] is True
def test_full_jones_has_eight_outputs_and_excludes_bounded6():
 d=json.loads((ML/"analysis/b120_j2lm06_post_d8_frozen_full_jones_model_reconstruction_v2.json").read_text()); assert len(d["coefficients"])==8; assert d["bounded6_excluded_from_fit"] is True; assert d["design_matrix_rank"]==10
def test_txx_gate_blocks_replay_without_solver():
 t=json.loads((ML/"analysis/b120_j2lm06_post_d8_frozen_txx_reproduction_audit_v2.json").read_text()); assert t["status"]=="HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"; r=json.loads((ML/"analysis/b120_j2lm06_post_d8_bounded_full_jones_primary_external_replay_v1.json").read_text()); assert r["status"].startswith("NOT_EXECUTED"); assert r["solver_calls"]==0
def test_route_has_no_d9_or_solver():
 r=json.loads((ML/"analysis/b120_j2lm06_post_d8_full_jones_readiness_update_v1.json").read_text()); assert r["NO_SOLVER_AUTHORIZATION"] and r["NO_D9_GEOMETRY"]; assert r["next_diagnostic_class"]=="PHASE_PROJECTOR_CROSS_BRANCH_DIAGNOSTIC"
