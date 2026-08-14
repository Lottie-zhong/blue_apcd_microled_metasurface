import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "stage_h1c1b1_sixbin_closure"


def load(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_zero_solver_and_exact_strict_bank():
    bank = load("h1c1b1_strict_bank_v1.json")
    assert bank["count"] == 7
    assert bank["strict_ids"] == [
        "GLOBAL_006", "GLOBAL_015", "H1C1B_V2_005", "H1C1B_V2_009",
        "H1C1B_V2_010", "H1C1B_V2_012", "H1C1B_V2_015"
    ]
    guard = load("h1c1b1_zero_solver_guard.json")
    assert guard["solver_entered_delta"] == 0
    assert guard["new_fdtd"] == guard["new_rcwa"] == guard["new_physics_solver"] == 0
    assert guard["solver_replay"] is False
    assert guard["raw_evidence_modified"] is False


def test_exhaustive_subsets_assignments_and_all_wavelengths():
    exhaustive = load("h1c1b1_six_tuple_exhaustive.json")
    assert exhaustive["subset_count"] == 7
    assert exhaustive["assignments_per_subset"] == 720
    assert exhaustive["tuple_count"] == 5040
    assert exhaustive["ranking_computed_full_precision"] is True
    assert len(exhaustive["ranking"][0]) == len(exhaustive["tuple_record_fields"])
    best = load("h1c1b1_best_six_bin_tuple.json")["best"]
    assert sorted(best["assignment_bin_by_geometry"].values()) == list(range(6))
    assert len(best["per_wavelength_optimal_phi0_deg"]) == 9
    assert len(best["adjacent_spacing_errors_deg"]) == 9
    assert len(best["opposite_bin_180_spacing_errors_deg"]) == 9


def test_phase_classification_and_order_crossing_are_diagnostic_only():
    phase = load("h1c1b1_phase_coverage.json")
    assert phase["classification"] == "STRICT_BANK_EXPANDED_BUT_PHASE_CLUSTERED"
    assert phase["numeric_acceptance_threshold_frozen"] is False
    assert len(phase["all7_per_wavelength"]) == 9
    best = load("h1c1b1_best_six_bin_tuple.json")["best"]
    assert best["phase_order_consistency"] == "PHASE_ORDER_CROSSING"


def test_quarantine_and_ml_guards():
    forensic = load("h1c1b1_quarantine_forensic.json")
    assert len(forensic["cases"]) == 3
    assert forensic["postprocess_recovered_count"] == 0
    assert forensic["solver_replay"] is False
    assert all(item["entered_solver"] and not item["solver_replay"] for item in forensic["cases"])
    assert all(item["classification"] == "RAW_DATA_PRESENT_BUT_FORMAL_INVALID" for item in forensic["cases"])
    ml = load("h1c1b1_ml_registry_audit.json")
    assert ml["row_count"] == 398
    assert ml["H1C1A_full_jones_rows"] == 189
    assert ml["H1C1B_full_jones_rows"] == 189
    assert ml["ml_eligible_all_true"] is True
    assert ml["ml_admitted_all_false"] is True
    assert ml["split_unassigned_only"] is True
    assert ml["x_only_excluded"] is True


def test_proposed_next_stage_is_not_started():
    proposal = load("h1c1b1_proposed_next_stage.json")
    assert proposal["status"] == "PROPOSED_ONLY"
    assert proposal["automatic_start"] is False
    assert proposal["requires_chart_authorization"] is True
    assert proposal["solver_entered"] == 0
