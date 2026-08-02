import json
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
def test_prospective_contract_and_reused_physics():
    p=json.loads((ML/"plans/b120_j2lm06_post_d8_cross_branch_diagnostic_plan_v1.json").read_text())
    pre=json.loads((ML/"analysis/b120_j2lm06_post_d8_cross_branch_preregistration_v1.json").read_text())
    route=json.loads((ML/"plans/b120_j2lm06_post_d8_cross_branch_route_contract_v1.json").read_text())
    assert p["candidate_count"]==18 and pre["candidate_count"]==18
    assert pre["group_counts"]=={"PHASE_LOCAL":6,"PROJECTOR_LOCAL":6,"BRIDGE":6}
    assert pre["geometry_gates"]["exact_unique"] and pre["geometry_gates"]["canonical_unique"] and pre["geometry_gates"]["symmetry_unique"]
    assert pre["staging_checkpoint_count"]==36 and pre["candidate_checkpoint_count"]==18
    assert pre["checkpoint_identity_audit"]["failed"]==0
    assert route["historical_gate"]=="HISTORICAL_FULL_JONES_GATE_REMAINS_BLOCKED"
    assert route["no_historical_primary_replay_claim"] and route["no_d9_candidate_plan"]
    assert route["no_additional_solver_authorization"]
    assert route["diagnosis"] in {"CROSS_BRANCH_ACTIVE_MANIFOLD_CONNECTED","ROTATED_CROSS_BRANCH_MANIFOLD_CONNECTED","DUAL_ANCHOR_LOCAL_MANIFOLDS_SEPARATE_BUT_STABLE","JOINT_ACTIVE_BASIS_ROTATION_CONFIRMED","REINTRODUCE_INACTIVE_VARIABLES_REQUIRED","GLOBAL_PHASE_PLATEAU_CONFIRMED","HARD_GATE_DATA_CONFLICT"}
