import hashlib
import json
import os
import subprocess
import csv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8") as f:
        return json.load(f)

def sha(rel):
    with open(os.path.join(BASE, rel), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def test_anchor_provenance_and_absolute_geometry():
    p = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_j2length_evidence_provenance_audit_v1.json")
    assert p["status"] == "PASS_OFFLINE_PLANNING_ONLY"
    assert p["anchors"]["phase"]["physics_label"] == "FORMAL_ACCEPTED_WEIGHTED_G0"
    assert p["anchors"]["projector"]["physics_label"] == "FORMAL_ACCEPTED_WEIGHTED_G0"
    assert p["anchors"]["phase"]["complete_jones"] and p["anchors"]["projector"]["complete_jones"]
    assert p["anchors"]["phase"]["geometry"]["J2_length_nm"] == 106.0
    assert p["anchors"]["projector"]["geometry"]["J2_length_nm"] == 106.0

def test_four_d_round_trip_and_symmetric_pairs():
    p = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_plan_v1.json")
    assert p["candidate_count"] == 4 and p["subrun_count"] == 8
    assert [r["delta_J2_length_nm"] for r in p["candidates"]] == [-1.0, 1.0, -1.0, 1.0]
    for r in p["candidates"]:
        assert r["delta_J2_width_nm"] == r["delta_D_nm"] == r["delta_Psi_deg"] == 0.0
        assert r["geometry"]["J2_length_nm"] == 106.0 + r["delta_J2_length_nm"]
        assert r["status"] == "PLANNED_NOT_RUN"
    with open(os.path.join(BASE, "outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_plan_v1.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4
    assert all(r["exact_geometry_hash_sha256"] and r["canonical_relative_geometry_hash_sha256"] for r in rows)

def test_hash_and_manufacturing_gates():
    p = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_j2length_evidence_provenance_audit_v1.json")
    h = p["hash_audit"]
    assert h["new_exact_unique"] and h["new_canonical_unique"] and h["new_symmetry_unique"]
    assert not h["exact_collisions"] and not h["canonical_collisions"] and not h["symmetry_collisions"]
    plan = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_plan_v1.json")
    assert all(r["geometry"]["no_overlap"] and r["geometry"]["primitive_valid"] for r in plan["candidates"])
    assert all(r["direct_gap_nm"] >= 60 and r["nearest_periodic_gap_nm"] >= 60 for r in plan["candidates"])

def test_contract_labels_and_budgets():
    c = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_contract_v1.json")
    b = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_batch_b_conditional_plan_v1.json")
    f = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_future_solver_contract_v1.json")
    assert c["solver_calls"] == 0 and not c["solver_authorized"]
    assert c["local_coordinates"]["qL_nm"] == 1.0
    assert c["batch_a"]["count"] == 4 and c["batch_a"]["xy_subruns"] == 8
    assert b["status"] == "UNFROZEN_PENDING_BATCH_A_PHYSICS" and not b["authorized"]
    assert b["max_geometries"] == 2 and b["max_xy_subruns"] == 4
    assert f["solver_calls"] == 0 and f["no_runnable_package"] and f["no_staging"]

def test_prediction_physics_separation_and_outcome_gate():
    p = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_j2length_prediction_uncertainty_table_v1.json")
    g = load("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_batch_a_outcome_gate_v1.json")
    assert p["prediction_label"] == "MODEL_PREDICTION_NOT_PHYSICS_LABEL"
    assert all(r["trust_region"] == "OUTSIDE_VERIFIED_CURRENT_ANCHOR_TRUST_REGION" for r in p["rows"])
    assert "J2L_NEW_CONTROL_DIRECTION_VALIDATED" in g["outcomes"]
    assert "Batch B" in " ".join(g["no_auto_authorization"])

def test_old_batch2_and_protected_integrity():
    old = load("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch2_readiness_v1.json")
    assert old.get("solver_calls", old.get("batch2_solver_calls", 0)) == 0
    assert sha("reports/lp_ml1a3_git_history_geometry_reconstruction.md") == "d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161"
    assert sha("reports/stage11_4a20_legacy_fsp_object_inventory.md") == "ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708"

def test_no_solver_or_runnable_package_paths():
    forbidden = [
        "outputs/lp_ml_dataset_v1/staging/b120_j2lm06_j2length_inclusive",
        "outputs/lp_ml_dataset_v1/execution_packages/b120_j2lm06_j2length_inclusive",
        "outputs/lp_ml_dataset_v1/plans/b120_j2lm06_j2length_inclusive_execution_package_v1.json",
    ]
    assert all(not os.path.exists(os.path.join(BASE, p)) for p in forbidden)
