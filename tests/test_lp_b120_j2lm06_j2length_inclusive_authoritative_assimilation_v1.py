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
    sys.path.insert(0,str(ROOT/"scripts"))
    from lp_b120_j2lm06_j2length_inclusive_batch_a_offline_finalize_v1 import parse_ledger_token
    assert parse_ledger_token("FINAL")["kind"]=="FINAL"

def test_phase_floor_and_claim_boundary():
    x=load(AN/"b120_j2lm06_j2length_inclusive_phase_floor_audit_v1.json")
    assert x["new_floor_candidate_id"]=="PDBX_PHASE_L2_M01"
    assert x["improvement_deg"]>0 and x["historical_primary_claim"] is False
    assert x["wrapped_unwrapped_consistent"] is True
    assert x["common_offset_semantics"].startswith("No arbitrary offset")

def test_four_actual_nodes_and_graph():
    m=load(AN/"b120_j2lm06_j2length_inclusive_post_canonical_actual_node_assimilation_manifest_v1.json")
    assert m["node_count"]==4 and all(n["complete_jones"] for n in m["nodes"])
    g=load(AN/"b120_j2lm06_j2length_inclusive_actual_node_graph_v1.json")
    assert g["node_count"]==42 and len([n for n in g["nodes"] if n["physics_origin"]=="PROSPECTIVE_FORMAL_BATCH_A_ACTUAL"])==4
    assert g["anchor_continuity"]["formal_bridge_path"] is False
    assert g["anchor_continuity"]["frontier_refresh_status"].startswith("PROSPECTIVE_METRIC")
    assert all(g["thresholds"][q]["formal_graph_connected"] is False for q in ("1.00","0.75","0.50"))

def test_xy_checkpoint_provenance_and_no_batch_followups():
    a=load(AN/"b120_j2lm06_j2length_inclusive_batch_a_subrun_accounting_v1.json")
    grouped={}
    for r in a["records"]:
        assert r["accepted"] and r["checkpoint_reload"]=="PASS" and r["formal_acceptance"]=="PASS"
        assert r["wavelength_nm"]==450.0 and r["weighted_G0_version"]=="LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"
        grouped.setdefault(r["candidate_id"],[]).append(r)
    assert len(grouped)==4 and all({r["polarization"] for r in rs}=={"x","y"} for rs in grouped.values())
    o=load(AN/"b120_j2lm06_j2length_inclusive_batch_a_outcome_v1.json")
    assert o["batch_b_readiness"]=="BATCH_B_NOT_JUSTIFIED" and o["no_d9"] is True

def test_projector_guard_no_invented_threshold():
    g=load(AN/"b120_j2lm06_j2length_inclusive_projector_guard_audit_v1.json")
    assert len(g["nodes"])==4 and g["thresholds_invented"] is False
    assert all(n["absolute_guard_threshold_status"]=="INDETERMINATE_CONTRACT_DEFINITION" for n in g["nodes"])
    required={"Txx","Tyy","txy_leakage","tyx_leakage","formal_combined_leakage","sigma2_over_sigma1","projection_error","jones_frobenius_step","manufacturing_margin","complete_jones"}
    assert all(required <= set(n["metric_audits"]) for n in g["nodes"])
    assert all(n["guard_status"]=="PROJECTOR_GATE_INDETERMINATE" for n in g["nodes"])

def test_d9_draft_only_and_no_d9_package():
    d=load(PL/"b120_j2lm06_j2length_inclusive_d9_phase_local_contract_amendment_draft_v1.json")
    assert d["status"]=="DRAFT_FOR_APPROVAL" and d["solver_authorized"] is False and d["candidate_geometry_count"]==0
    assert not list((ROOT/"outputs/lp_ml_dataset_v1/execution_packages").glob("*j2length*D9*"))

def test_route_matrix_has_required_comparison_columns():
    import csv
    with open(AN/"b120_j2lm06_j2length_inclusive_future_route_decision_matrix_v1.csv",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==4
    required={"current_evidence","unresolved_risk","minimum_new_solver_estimate","information_gain","relevance_to_six_phase_broadband_library","contract_change_required","known_failure_repeat_likelihood"}
    assert required <= set(rows[0])
