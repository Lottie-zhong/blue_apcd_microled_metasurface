import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1e2_j1_anisotropy_attribution"
H1E1 = ROOT / "reports/stage_h1e1_j1_anisotropy"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_exact_manifest():
    m = json.loads((H1E1 / "h1e1_candidate_manifest.json").read_text(encoding="utf-8"))
    audit = load("h1e2_child_audit.json")
    assert len(m["candidates"]) == 8
    assert len(audit["children"]) == 8
    assert audit["solver_entered_delta"] == 0
    assert audit["no_new_solver"] is True


def test_strict_phase_region_and_route():
    region = load("h1e2_strict_child_phase_regions.json")
    assert len(region["new_children"]) == 2
    assert all(not x["new_island"] for x in region["new_children"])
    route = load("h1e2_route_decision.json")
    assert route["physics_classification"] == "J1_ANISOTROPY_STRICT_LEVER_WITHIN_EXISTING_CLUSTER"
    assert route["route"] == "ADD_ONE_NEW_LOCAL_DIMER_DOF"
    assert route["recommended_dof"] == "independent_J1_rotation_deg"


def test_finite_difference_pairs_are_reproducible():
    sens = load("h1e2_anisotropy_sensitivity.json")["families"]
    assert set(sens) == {"GLOBAL_006", "GLOBAL_015", "H1C1B_V2_012"}
    assert [(x["d_plus_nm"], x["d_minus_nm"]) for x in sens["GLOBAL_015"]] == [(2, -2)]
    for rows in sens.values():
        assert len(rows[0]["slopes"]) == 9
        assert rows[0]["diagnostic"].startswith("LOCAL_EMPIRICAL")


def test_quarantine_and_registry_gates():
    q = load("h1e2_quarantine_forensic.json")
    assert q["solver_entered"] is True
    assert q["raw_data_present"] is True
    assert q["formal_checkpoint_present"] is False
    assert q["classification"] == "RAW_DATA_PRESENT_BUT_FORMAL_INVALID"
    assert q["solver_replay"] is False
    reg = load("h1e2_registry_audit.json")
    assert reg["total_versioned_rows"] == 506
    assert reg["ml_admitted"] is False
    assert reg["no_fabricated_full_jones_rows"] is True


def test_proposed_next_stage_is_not_executed():
    p = load("h1e2_proposed_next_stage.json")
    assert p["status"] == "PROPOSED_ONLY_NOT_EXECUTED"
    assert p["candidate_count"] == 6
    assert p["formal_subrun_budget"] == 12
    assert p["solver_entered"] is False


def test_h1e2_implementation_is_zero_solver():
    source = (ROOT / "scripts/lp_h1e2_j1_anisotropy_attribution.py").read_text(encoding="utf-8").lower()
    assert "lumapi" not in source
    assert "run_case" not in source
    assert "subprocess" not in source
    assert "lumapi" not in source
    assert "engine" not in source
