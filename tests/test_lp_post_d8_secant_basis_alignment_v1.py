import csv
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
ML = ROOT / "outputs/lp_ml_dataset_v1"


def _json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_common_basis_and_secant_counts():
    basis = _json("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_recalibration_common_basis_v1.json")
    assert basis["basis_status"] == "PASS"
    assert basis["raw_variable_vector"] == ["J1_side_nm", "J2_length_nm", "J2_width_nm", "D_nm", "Psi_deg"]
    assert basis["active_raw_vector"] == ["J2_width_nm", "D_nm", "Psi_deg"]
    rows = list(csv.DictReader((ML / "analysis/b120_j2lm06_d7_d8_recalibration_secant_table_v1.csv").open(encoding="utf-8")))
    assert len(rows) == 21
    assert {r["family"] for r in rows} == {"S1_J2LM06_TO_D7", "S2_D7_TO_D8", "S3_D8_TO_RECALIBRATION", "S4_D8_TO_D8_LOWEST_PHASE"}


def test_units_closure_and_no_fabricated_hessian():
    jac = _json("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_recalibration_jacobian_secant_alignment_v1.json")
    closure = _json("outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_tetrahedral_closure_audit_v1.json")
    assert "normalized" in json.dumps(jac)
    assert closure["hessian_claim"] is False
    assert closure["curvature_evidence"] in {"no detectable curvature", "BOUNDED_CURVATURE_EVIDENCE", "SIGNIFICANT_UNRESOLVED_CURVATURE", "INSUFFICIENT_EVIDENCE"}


def test_route_contract_is_analysis_only():
    route = _json("outputs/lp_ml_dataset_v1/plans/b120_j2lm06_post_d8_secant_route_decision_contract_v1.json")
    assert route["status"] == "ANALYSIS_ONLY"
    assert route["solver_calls"] == 0
    assert route["d9_authorized"] is False
    assert route["new_candidate_geometry_authorized"] is False
    assert route["route_outcome"] in {
        "SECANT_ALIGNED_READY_FOR_BOUNDED_PROGRESS_PLAN",
        "DIRECTION_VALID_SCALE_UNCERTAIN",
        "LOCAL_CURVATURE_REQUIRES_ADDITIONAL_DIAGNOSTIC",
        "ACTIVE_BASIS_INCONSISTENT",
        "HARD_GATE_DATA_CONFLICT",
    }
