import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/stage_h1f3c0_helper_history_recovery"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_registry_invariants():
    route = load("helper_route_decision.json")
    proposed = load("helper_proposed_next_stage.json")
    assert proposed["solver_authorized"] is False
    assert proposed["solver_entered_delta"] == 0
    assert route["formal_route"] == "HELPER_FORMAL_REVALIDATION_FIRST"
    with (ROOT / "reports/stage_h1f3c_k6_complex_lever_audit/K6_FULLWAVE_EVIDENCE_REGISTRY.csv").open(newline="", encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == 720


def test_keyword_history_search_and_actual_vs_proposed_classification():
    search = load("helper_search_index.json")
    evidence = load("helper_solver_evidence.json")
    provenance = load("helper_stage_provenance.json")
    assert "helper" in search["terms"]
    assert search["matching_file_count"] > 0
    assert evidence["actual_solver_evidence_exists"] is True
    assert all(item["evidence_class"] == "ACTUAL_FDTD_FULL_JONES" for item in evidence["items"])
    assert provenance["classification_counts"]["PROPOSED_ONLY"] == 1
    assert provenance["classification_counts"]["SETUP_ONLY"] == 1


def test_geometry_and_same_global_h_fabrication_audit():
    geom = load("helper_geometry_recovery.json")
    fab = load("helper_fabrication_audit.json")
    assert geom["helper"]["J3_helper"]["height_nm"] == 300.0
    assert geom["helper"]["J3_helper"]["x_nm"] == -85.0
    assert geom["helper"]["J3_helper"]["y_nm"] == 85.0
    assert fab["same_global_H"] is True
    assert fab["helper_hr_aniso_push_08"]["geometry_validation_pass"] is True
    assert fab["helper_hr_aniso_push_08"]["same_cell_min_gap_nm"] > 50.0


def test_formal_compatibility_is_legacy_not_current():
    compat = load("helper_formal_compatibility.json")
    assert compat["classification"] == "HISTORICAL_HELPER_PROMISING_BUT_LEGACY"
    assert compat["full_jones_x_y"] is True
    assert len(compat["missing_or_mismatched"]) >= 4
    assert compat["formal_revalidation_required"] is True


def test_circular_phase_and_projector_comparison_are_explicit():
    rows = list(csv.DictReader((OUT / "helper_phase_projector_comparison.csv").open(newline="", encoding="utf-8")))
    assert len(rows) == 3
    assert all(r["phase_metric"] == "arg(t_alpha_star_from_alpha)" for r in rows)
    assert all(r["projector_error_current_formal"] == "UNAVAILABLE" for r in rows)
    assert all(r["spectral_scope"].startswith("single wavelength") for r in rows)


def test_helper_vs_grouped_d_and_route_hold():
    compare = load("helper_vs_grouped_d.json")
    proposed = load("helper_proposed_next_stage.json")
    assert compare["no_arbitrary_weighted_score"] is True
    assert compare["grouped_D"]["A_D_probe_nm"] == 4.0
    assert proposed["formal_cases"] == 2
    assert proposed["solver_authorized"] is False
    assert "GROUPED_D_H1F4A_READY" in proposed["if_baseline_not_reusable"]
