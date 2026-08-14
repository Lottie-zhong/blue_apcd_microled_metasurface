import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lp_global_h_h1c1b0_attribution_v1.py"
REPORT = ROOT / "reports" / "stage_h1c1b0_broadband_attribution"


def load_module():
    spec = importlib.util.spec_from_file_location("h1c1b0_test_module", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_has_zero_solver_and_scheduler_surface():
    source = SCRIPT.read_text(encoding="utf-8")
    assert ".run(" not in source
    assert "GlobalSlotScheduler" not in source
    assert "fdtd.run" not in source.lower()
    assert "rcwa.run" not in source.lower()


def test_quarantine_audit_is_entered_no_replay_and_no_recovery():
    audit = json.loads((REPORT / "h1c1b0_quarantine_recovery_audit.json").read_text(encoding="utf-8"))
    assert audit["zero_new_solver"] is True
    assert audit["solver_replay"] is False
    assert audit["postprocess_recovered_count"] == 0
    assert len(audit["cases"]) == 3
    assert all(row["entered_solver"] is True for row in audit["cases"])
    assert all(row["solver_replay"] is False for row in audit["cases"])
    assert all(row["raw_broadband_complex_field_data_exists"] is True for row in audit["cases"])
    assert all(row["classification"] == "PARTIAL_ARTIFACT_NOT_ENOUGH_FOR_FORMAL_RESULT" for row in audit["cases"])


def test_failure_matrix_has_exact_grid_and_strict_only_9_of_9():
    module = load_module()
    matrix = list(__import__("csv").DictReader((REPORT / "h1c1b0_broadband_failure_matrix.csv").open(encoding="utf-8", newline="")))
    assert len(matrix) == 21
    for row in matrix:
        profile = json.loads(row["wavelength_profile"])
        assert len(profile) == 9
        assert [float(item["wavelength_nm"]) for item in profile] == module.GRID
        if row["formal_strict_candidate"] in (True, "True"):
            assert int(row["projector_pass_count_9"]) == 9
    assert sum(row["projector_pass_count_9"] in ("7", "8", 7, 8) for row in matrix) == 2


def test_near_miss_is_diagnostic_only_and_not_strict():
    bank = json.loads((REPORT / "h1c1b0_near_miss_bank.json").read_text(encoding="utf-8"))
    assert bank["formal_candidate_bank"] is False
    assert {row["projector_pass_count_9"] for row in bank["candidates"]} <= {7, 8}
    assert all(row["formal_candidate"] is False and row["diagnostic_only"] is True for row in bank["candidates"])
    assert {row["geometry_uid"] for row in bank["candidates"]} == {"GLOBAL_002", "GLOBAL_018"}


def test_phase_coverage_separates_strict_and_diagnostic_near_miss():
    coverage = json.loads((REPORT / "h1c1b0_six_bin_coverage_map.json").read_text(encoding="utf-8"))
    assert coverage["common_phase_offset_free"] is True
    assert coverage["strict_only"]["occupied_bins"]
    assert coverage["strict_plus_near_miss"]["occupied_bins"]
    assert coverage["near_miss_never_promoted"] is True


def test_ml_registry_audit_preserves_flags_and_no_fabrication():
    audit = json.loads((REPORT / "h1c1b0_ml_registry_audit.json").read_text(encoding="utf-8"))
    assert audit["row_count"] == 209
    assert audit["complete_broadband_geometry_count"] == 21
    assert audit["complete_broadband_each_9_rows"] is True
    assert audit["historical_only_450_nm"] is True
    assert audit["no_fabricated_broadband_rows"] is True
    assert audit["ml_eligible_all"] is True
    assert audit["ml_admitted_false_all"] is True
    assert audit["split_unassigned_all"] is True
    assert audit["quarantined_not_masquerading_as_complete"] is True
    assert audit["ML_DATASET_READINESS"] == "NOT_READY_FOR_FORMAL_ML_RESTART"


def test_proposed_batch_is_legal_unique_and_unexecuted():
    proposal = json.loads((REPORT / "h1c1b0_adaptive_batch_proposal.json").read_text(encoding="utf-8"))
    assert proposal["status"] == "PROPOSED_ONLY_NO_SOLVER_AUTHORIZATION"
    assert proposal["count"] == 24
    rows = proposal["candidates"]
    assert len({row["exact_hash"] for row in rows}) == 24
    assert all(row["solver_authorized"] is False and row["solver_entered"] is False and row["solver_replay"] is False for row in rows)
    assert all(row["legality"]["pass"] is True for row in rows)
    assert all(row["role"] in {"STRICT_NEIGHBOR_PROJECTOR_ROBUSTNESS", "NEAR_STRICT_RESCUE", "PHASE_GAP_TARGET", "GLOBAL_COVERAGE_CONTROL"} for row in rows)
    assert proposal["no_h1b_local_edge_route_restart"] is True
    assert proposal["no_uniform_sobol_repeat"] is True


def test_c_attribution_keeps_seed_nonformal():
    report = json.loads((REPORT / "h1c1b0_c_failure_attribution.json").read_text(encoding="utf-8"))
    assert report["status"] == "CENTER_ONLY_COMPATIBLE"
    assert report["formal_broadband_six_bin_candidate"] is False
    assert report["remains_global_six_bin_candidate_seed_450nm"] is True
    assert report["failed_wavelengths"] == [451.5, 452.0, 452.5, 453.0, 453.5, 454.0]
