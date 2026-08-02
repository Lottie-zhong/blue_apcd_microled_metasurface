import json, pathlib, subprocess, sys

ROOT=pathlib.Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
AN=ROOT/"outputs/lp_ml_dataset_v1/analysis"
PL=ROOT/"outputs/lp_ml_dataset_v1/plans"

def load(p):
    with open(p,encoding="utf-8") as f:return json.load(f)

def test_batch_a_ledger_and_final_sentinel():
    l=load(AN/"b120_j2lm06_j2length_inclusive_completion_supersession_ledger_v1.json")
    assert (l["planned_subruns"],l["entered_subruns"],l["accepted_subruns"])==(8,8,8)
    assert l["solver_calls_this_offline_task"]==0 and l["no_rerun"]
    assert "FINAL sentinel" in l["direct_root_cause"]

def test_phase_floor_and_claim_boundary():
    x=load(AN/"b120_j2lm06_j2length_inclusive_phase_floor_audit_v1.json")
    assert x["new_floor_candidate_id"]=="PDBX_PHASE_L2_M01"
    assert x["improvement_deg"]>0 and x["historical_primary_claim"] is False

def test_four_actual_nodes_and_graph():
    m=load(AN/"b120_j2lm06_j2length_inclusive_post_canonical_actual_node_assimilation_manifest_v1.json")
    assert m["node_count"]==4 and all(n["complete_jones"] for n in m["nodes"])
    g=load(AN/"b120_j2lm06_j2length_inclusive_actual_node_graph_v1.json")
    assert g["node_count"]==42 and len([n for n in g["nodes"] if n["physics_origin"]=="PROSPECTIVE_FORMAL_BATCH_A_ACTUAL"])==4
    assert g["anchor_continuity"]["formal_bridge_path"] is False
    assert all(g["thresholds"][q]["formal_graph_connected"] is False for q in ("1.00","0.75","0.50"))

def test_projector_guard_no_invented_threshold():
    g=load(AN/"b120_j2lm06_j2length_inclusive_projector_guard_audit_v1.json")
    assert len(g["nodes"])==4 and g["thresholds_invented"] is False
    assert all(n["absolute_guard_threshold_status"]=="INDETERMINATE_CONTRACT_DEFINITION" for n in g["nodes"])

def test_d9_draft_only_and_no_d9_package():
    d=load(PL/"b120_j2lm06_j2length_inclusive_d9_phase_local_contract_amendment_draft_v1.json")
    assert d["status"]=="DRAFT_FOR_APPROVAL" and d["solver_authorized"] is False and d["candidate_geometry_count"]==0
    assert not list((ROOT/"outputs/lp_ml_dataset_v1/execution_packages").glob("*j2length*D9*"))
