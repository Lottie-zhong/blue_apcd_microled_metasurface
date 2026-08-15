import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "stage_h1f2_k6_frontier_level1"


def load(name):
    return json.loads((REPORT / name).read_text(encoding="utf-8"))


def test_pool_and_phase_gate():
    pool = load("h1f2_constituent_pool_audit.json")
    diversity = load("h1f2_frontier_phase_diversity.json")
    assert pool["versioned_local_dimer_rows"] == 578
    assert pool["strict_count"] == 12
    assert pool["frontier_8_count"] == 4
    assert pool["frontier_7_count"] == 4
    assert pool["excluded_invalid_or_quarantine_in_audited_full_jones_pool"] == 0
    assert diversity["gate"] == "PASS_NEW_COMPLEX_DIRECTIONS"
    assert 0 <= diversity["strict_plus_frontier_phase_circular_coverage_deg"] <= 360


def test_candidate_roles_and_inventory():
    manifest = load("h1f2_candidate_manifest.json")
    candidates = manifest["candidates"]
    assert manifest["wavelength_grid_nm"] == [450.0 + 0.5 * i for i in range(9)]
    assert manifest["max_new_formal_cases"] == 6
    assert manifest["ml_admitted"] is False
    a = candidates["K6_L1_A"]
    b = candidates["K6_L1_B"]
    c = candidates["K6_L1_C"]
    h1f1_a = [
        "H1C1B_V2_005", "H1C1B_V2_005", "H1C1B_V2_015", "H1C1B_V2_015",
        "H1E3C_A_DECOUPLED_MINUS_H1C1B_V2_010",
        "H1E3C_A_TIED_PLUS_H1C1B_V2_010",
    ]
    assert sorted(a["sequence_uids"]) == sorted(h1f1_a)
    assert a["sequence_uids"] != h1f1_a
    assert a["fundamental_period_audit"]["FUNDAMENTAL_PERIOD_6P"] is True
    assert b["constituent_classes"].count("STRICT") == 4
    assert sum(x.startswith("FRONTIER") for x in b["constituent_classes"]) == 2
    assert c["constituent_classes"].count("STRICT") == 3
    assert sum(x.startswith("FRONTIER") for x in c["constituent_classes"]) == 3
    for candidate in candidates.values():
        assert candidate["no_position_shift"] is True
        assert candidate["no_local_geometry_mutation"] is True
        assert candidate["H_global_nm"] == 550.0
        assert str(candidate["geometry_legality"]["no_overlap"]).lower() == "true"
        assert candidate["fundamental_period_audit"]["FUNDAMENTAL_PERIOD_6P"] is True


def test_pre_solver_accounting_and_proxy_governance():
    accounting = load("h1f2_solver_accounting.json")
    proxy = load("h1f2_proxy_vs_fullwave.json")
    registry = load("h1f2_k6_registry_audit.json")
    assert accounting["planned_formal_cases"] == 6
    assert accounting["entered_formal_cases"] == 6
    assert accounting["accepted_formal_cases"] == 6
    assert accounting["replay_cases"] == 0
    assert accounting["max_active_global_fdtd"] <= 2
    assert accounting["max_active_lp_fdtd"] <= 1
    assert proxy["proxy_annotation"] == "NON_AUTHORITATIVE_CONSTITUENT_ADDITIVE_DIAGNOSTIC"
    assert registry["local_registry_rows_before"] == 578
    assert registry["local_registry_rows_unchanged"] is True
    assert registry["ml_admitted"] is False


def test_fullwave_and_registry_closure():
    accounting = load("h1f2_solver_accounting.json")
    registry = load("h1f2_k6_registry_audit.json")
    assert accounting["entered_formal_cases"] == 6
    assert accounting["accepted_formal_cases"] == 6
    assert accounting["quarantine_cases"] == 0
    assert accounting["replay_cases"] == 0
    assert registry["new_k6_rows"] == 54
    assert registry["K6_registry_rows_after"] == 648
    rows = (REPORT / "h1f2_k6_order_jones.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 28
    assert "alpha_star_from_alpha_re" in rows[0]
    assert "target_projector_error" in rows[0]
