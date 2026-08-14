import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1e3b_j2_decoupling_audit"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_existing_j2_dof():
    source = (ROOT / "scripts/lp_h1e3b_j2_decoupling_audit.py").read_text(encoding="utf-8").lower()
    assert "lumapi" not in source and "subprocess" not in source
    g = load("h1e3b_historical_grammar_audit.json")
    assert g["J2_length_width_independently_assignable"] is True
    assert g["J2_ANISOTROPY_ALREADY_EXISTING_DOF"] is True


def test_sampling_and_d2_classification():
    c = load("h1e3b_j2_sampling_coverage.json")
    assert c["H550_canonical_registry"]["records"] == 488
    assert c["H550_canonical_registry"]["J2_L_minus_J2_W_range_nm"] == [-6.0, 20.0]
    assert c["constant_mean_direction"]["both_signs_observed"] is True
    assert c["constant_mean_direction"]["classification"] == "LOCAL_SEARCH_DIRECTION_ALREADY_EXPLORED"


def test_semantics_and_decoupling_identity():
    s = load("h1e3b_j2_orientation_decoupling.json")
    assert s["current_constraint"] == "theta_J2=Psi"
    assert s["old_grammar_recovered_at_delta_theta_J2"] == 0.0
    assert all(s["independence"].values())
    p = load("h1e3b_psi_confounded_semantics.json")
    assert p["J1_orientation_deg"] == 0.0
    assert p["Psi_range_deg"][0] < 0 < p["Psi_range_deg"][1]


def test_route_and_proposed_probe():
    r = load("h1e3b_route_decision.json")
    assert r["d2_classification"] == "LOCAL_SEARCH_DIRECTION"
    assert r["route"] == "DECOUPLE_J2_ORIENTATION_FROM_DISPLACEMENT_FIRST"
    assert r["recommended_next_dof"] == "delta_theta_J2_deg"
    p = load("h1e3b_proposed_next_stage.json")
    assert p["status"] == "PROPOSED_ONLY_NOT_EXECUTED"
    assert p["candidate_count"] == 6
    assert p["formal_subrun_budget"] == 12
    assert p["solver_entered"] is False
    assert all(abs(v["delta_theta_J2_deg"]) == 1 for v in p["variants"])


def test_registry_and_ml_invariants():
    r = load("h1e3b_route_decision.json")
    assert r["registry_rows"] == 506
    assert r["ml_admitted"] is False
    assert r["solver_entered_delta"] == 0
