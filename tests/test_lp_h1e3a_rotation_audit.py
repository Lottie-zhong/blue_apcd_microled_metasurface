import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1e3a_j1_rotation_audit"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_semantics():
    source = (ROOT / "scripts/lp_h1e3a_rotation_audit.py").read_text(encoding="utf-8").lower()
    assert "lumapi" not in source and "subprocess" not in source
    sem = load("h1e3a_geometry_semantics.json")
    assert sem["Psi_semantics"] == "coupled displacement azimuth and J2 local rotation parameter"
    assert sem["current_orientations"]["J1_rotation_deg"] == 0.0
    assert sem["independent_J1_rotation"]["independent_of_Psi"] is True
    assert sem["duplicate_dof"] is False


def test_rotated_jones_identity_and_projector_diagnosis():
    checks = load("h1e3a_rotation_jones_checks.json")
    assert checks["derivative_check"] is True
    assert checks["dJxx_dtheta_at_zero"] == "0"
    assert checks["dJxy_dtheta_at_zero"] == "a-b"
    risk = load("h1e3a_rotation_projector_risk.json")
    assert risk["diagnosis"] == "PROJECTOR_MIXING_DOMINANT_FIRST_ORDER; common-phase is not first-order"
    assert risk["pb_phase_assumption"] is False


def test_risk_route_and_angle_review():
    route = load("h1e3a_route_decision.json")
    assert route["j1_rotation_classification"] == "J1_ROTATION_PROJECTOR_RISK_DOMINANT"
    assert route["j1_rotation_probe_approved"] is False
    assert route["recommended_next_dof"] == "independent_J2_anisotropy_d_nm"
    angle = load("h1e3a_angle_range_review.json")
    assert angle["recommended_J1_rotation_first_scale_deg"] == [-2, 2]
    assert angle["fifteen_degree_justified"] is False


def test_proposed_alternative_is_deterministic_and_unexecuted():
    p = load("h1e3a_proposed_next_stage.json")
    assert p["status"] == "PROPOSED_ONLY_NOT_EXECUTED"
    assert p["variable"] == "J2_anisotropy_d_nm"
    assert p["candidate_count"] == 6
    assert p["formal_subrun_budget"] == 12
    assert p["solver_entered"] is False
    assert all(x["bounds_pass"] for x in p["variants"])
    assert {x["geometry_uid"] for x in p["parents"]} == {"H1C1B_V2_009", "GLOBAL_015", "GLOBAL_006"}


def test_registry_and_ml_invariants():
    route = load("h1e3a_route_decision.json")
    assert route["registry_rows"] == 506
    assert route["ml_admitted"] is False
    assert route["solver_entered_delta"] == 0
