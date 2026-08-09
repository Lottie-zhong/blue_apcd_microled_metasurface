import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AN = ROOT / "outputs/lp_ml_dataset_v1/analysis"
PL = ROOT / "outputs/lp_ml_dataset_v1/plans"


def load_json(name):
    return json.loads((AN / name).read_text(encoding="utf-8"))


def load_plan():
    return json.loads((PL / "lp_5d_phase_reachability_probe_v2.json").read_text(encoding="utf-8"))


def test_exact_quarantine_identity_only():
    q = json.loads((ROOT / "outputs/lp_ml_dataset_v1/clean_v2/quarantine_manifest_v2.json").read_text(encoding="utf-8"))
    rec = load_json("lp_ml_inverse_stage1_5d_054_exact_identity_reconciliation_v2.json")
    adm = load_json("lp_ml_inverse_stage1_5d_reachability_admission_v2.json")
    assert q["candidate_id"] == "LPML_R1_GLOBAL_SOBOL_054"
    assert q["decision"] == "QUARANTINED_INCOMPLETE_NO_COMPLETE_JONES_V1"
    assert rec["r1_exact_hash_rows"] == 0
    assert rec["authoritative_quarantine_manifest"]["exact_geometry_hash"] == q["exact_geometry_hash_sha256"]
    assert adm["r1_hash_admitted_rows"] == 0
    assert set(adm["id_contains_054_admitted"]) == {
        "LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054",
        "LPML_R3_054",
    }
    assert all(v["classification"] == "LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE" for v in rec["identity_groups"].values())


def test_corrected_admission_counts():
    adm = load_json("lp_ml_inverse_stage1_5d_reachability_admission_v2.json")
    assert adm["clean_v3_exact_geometry_count"] == 377
    assert adm["admitted_unique_geometry_count"] == 409
    assert adm["source_counts"]["clean_v3"]["rows_450_admitted"] == 377
    assert adm["source_counts"]["stage1_prospective"]["rows_450_admitted"] == 35
    assert adm["r2_054_hash_admitted"] == 1
    assert adm["solver_calls"] == 0


def test_authoritative_bounds_and_quantization():
    b = load_json("lp_ml_inverse_stage1_5d_authoritative_bounds_ledger_v2.json")
    assert b["bounds"]["J1_side_nm"]["lower"] == 108
    assert b["bounds"]["J1_side_nm"]["upper"] == 112
    assert b["bounds"]["J2_length_nm"]["lower"] == 106
    assert b["bounds"]["J2_length_nm"]["upper"] == 110
    assert b["bounds"]["J2_width_nm"]["lower"] == 98
    assert b["bounds"]["J2_width_nm"]["upper"] == 102
    assert b["bounds"]["D_nm"]["lower"] == 196.0
    assert b["bounds"]["D_nm"]["upper"] == 204.0
    assert b["bounds"]["Psi_deg"]["lower"] == -1.2
    assert b["bounds"]["Psi_deg"]["upper"] == 1.2
    assert b["quantization"]["dimensions"] == "integer"
    assert b["quantization"]["centers"] == "integer_or_exact_half_nm"
    assert b["quantization"]["sub_grid"] is False
    assert b["minimum_gap_rule"]["direct_gap_nm"]["lower"] == 60.0
    assert b["minimum_gap_rule"]["periodic_gap_nm"]["lower"] == 60.0
    assert b["observed_support_is_not_design_bounds"] is True


def test_plan_count_roles_and_legality():
    p = load_plan()
    rows = p["candidates"]
    assert len(rows) == 24
    assert p["future_budget"] == {"geometries": 24, "x_y_subruns": 48, "wavelength_nm": [450]}
    assert p["solver_calls"] == 0
    assert p["no_d9"] is True
    assert p["no_new_freedom"] is True
    counts = {}
    for row in rows:
        counts[row["role"]] = counts.get(row["role"], 0) + 1
        assert row["status"] == "PLANNED_NOT_RUN"
        assert row["physics_fields"] == "ABSENT_NOT_SIMULATED"
        assert row["prediction_label"] == "MODEL_PREDICTION_NOT_PHYSICS_LABEL"
        assert row["wavelength_nm"] == 450.0
        assert row["solver_authorized"] is False
        for key in ("center_grid_pass", "quantization_pass", "cell_containment_pass", "no_overlap", "primitive_valid", "manufacturing_pass", "formal_duplicate_pass", "canonical_duplicate_pass", "symmetry_duplicate_pass"):
            assert row[key] is True
        assert row["r1_quarantine_hash_match"] is False
        assert row["direct_gap_nm"] >= 60.0
        assert row["periodic_gap_nm"] >= 60.0
    assert counts == {
        "LOW_PHASE_EXTREME": 6,
        "HIGH_PHASE_EXTREME": 6,
        "PHASE_PROJECTOR_TRADEOFF": 4,
        "5D_BOUNDARY_SPARSE_REGION": 4,
        "DISAGREEMENT_PHYSICS_CONTROL": 4,
    }
    assert len({round(r["Psi_deg"], 6) for r in rows}) >= 3
    assert any(r["Psi_deg"] < 0 for r in rows)
    assert any(r["Psi_deg"] > 0 for r in rows)
    assert any(abs(r["Psi_deg"]) < 1e-12 for r in rows)


def test_legality_audit_and_protected_hashes():
    g = load_json("lp_ml_inverse_stage1_5d_probe_legality_audit_v2.json")
    assert g["candidate_count"] == 24
    assert g["all_bounds_pass"] is True
    assert g["all_duplicate_pass"] is True
    assert g["all_r1_quarantine_excluded"] is True
    c = load_json("lp_ml_inverse_stage1_5d_presolver_reconciliation_checksums_v2.json")
    assert c["solver_calls"] == 0
    assert all(v["unchanged"] and v["before"] == v["after"] for v in c["protected_hashes_before_after"].values())
    assert len(c["generated"]) == 16


def test_route_contract_is_offline_only():
    c = json.loads((PL / "lp_5d_phase_reachability_probe_route_contract_v2.json").read_text(encoding="utf-8"))
    assert c["authorization"] == "OFFLINE_PLAN_ONLY"
    assert c["solver_calls"] == 0
    assert c["no_runnable_solver_package"] is True
    assert c["no_d9"] is True
    assert c["no_new_freedom"] is True
