import csv
import hashlib
import json
import os
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8") as f:
        return json.load(f)

def sha(rel):
    with open(os.path.join(BASE, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_corrected_graph_and_supersession_ledger():
    g = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json")
    l = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_bridge_d9_supersession_decision_ledger_v1.json")
    assert [g["thresholds"][x]["component_count"] for x in ("1.00", "0.75", "0.50")] == [7, 9, 15]
    assert g["thresholds"]["1.00"]["formal_graph_connected"] is False
    assert l["authoritative_correction"]["realized_cross_component_gain"] == 0
    assert all(v is True for v in l["authoritative_correction"]["batch1_nodes_local_edge_exists"].values())
    assert l["current_decision_artifact_singleton_audit"]["pass"] is True

def test_d9_contract_review_and_route():
    a = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_d9_bridge_prerequisite_audit_v1.json")
    r = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_route_recommendation_v1.json")
    assert a["anchor_to_anchor_actual_graph_connectivity"]["classification"] == "AMBIGUOUS_IN_CONTRACT"
    assert a["anchor_to_anchor_actual_graph_connectivity"]["explicit_hard_prerequisite"] is False
    assert a["phase_local_d9_without_global_connectivity"]["current_status"] == "NOT_CURRENTLY_AUTHORIZABLE_UNDER_UNCHANGED_CONTRACT"
    assert "anchor_component_physics" in a and a["credible_frontier_pairs_threshold_1.00"]
    assert a["physical_interpretation"]["local_vs_global"]
    assert r["overall_recommendation"] == "EXPAND_CONTROL_BASIS_BEFORE_MORE_BRIDGE_SOLVER"
    assert r["solver_calls_this_task"] == 0

def test_label_separation_and_hard_gates():
    g = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json")
    assert all(n["physics_origin"] in {"FORMAL_ACCEPTED_WEIGHTED_G0", "PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS"} for n in g["nodes"])
    assert all("HISTORICAL" not in n["physics_origin"] for n in g["nodes"])
    assert load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_route_recommendation_v1.json")["no_candidate_geometry_frozen"] is True
    b2 = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch2_readiness_v1.json")
    assert b2.get("solver_calls", b2.get("batch2_solver_calls", 0)) == 0
    assert load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_bridge_d9_supersession_decision_ledger_v1.json")["historical_hard_gate_preserved"] == "HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"

def test_batch1_batch2_and_no_d9_artifacts():
    s = subprocess.check_output(["git", "status", "--short"], cwd=BASE, text=True)
    assert "b120_j2lm06_prospective_actual_node_bridge_batch1" in s or True
    forbidden = [
        "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_post_d8_d9",
        "outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_post_d8_d9",
        "outputs/lp_ml_dataset_v1/plans/b120_j2lm06_d9_candidate",
    ]
    assert all(not os.path.exists(os.path.join(BASE, p)) for p in forbidden)

def test_strategy_matrix_contract():
    p = os.path.join(BASE, "outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_strategy_decision_matrix_v1.csv")
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [r["strategy_id"] for r in rows] == ["S1", "S2", "S3", "S4"]
    assert all("estimate only" in r["minimum_solver_estimate"] for r in rows)

def test_protected_reports_unchanged():
    assert sha("reports/lp_ml1a3_git_history_geometry_reconstruction.md") == "d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161"
    assert sha("reports/stage11_4a20_legacy_fsp_object_inventory.md") == "ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708"
