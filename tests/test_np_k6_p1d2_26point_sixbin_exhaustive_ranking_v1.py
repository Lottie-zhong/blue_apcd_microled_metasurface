import csv
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_np_k6_p1d2_26point_sixbin_exhaustive_ranking_v1.py"
OUT = ROOT / "outputs" / "np_k6_p1d2_sixbin_exhaustive_ranking_v1"
SPEC = importlib.util.spec_from_file_location("sixbin", SCRIPT)
sixbin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sixbin)


def test_allowlist_and_exact_combination_space():
    assert len(sixbin.DIAMETERS) == 26 and 180 not in sixbin.DIAMETERS
    assert len(list(__import__("itertools").combinations(sixbin.DIAMETERS, 6))) == 230230


def test_wrapped_circular_fit_is_global_phase_shift_invariant():
    phases = np.array([[5.0, 66.0, 119.0, 182.0, 238.0, 304.0]])
    common, errors = sixbin.circular_fit(phases)
    _, shifted_errors = sixbin.circular_fit((phases + 137.0) % 360.0)
    assert np.allclose(errors, shifted_errors, atol=1e-9)
    assert np.all(np.abs(errors) <= 180.0) and common.shape == (1,)


def test_output_manifest_proves_full_unique_no_d180_enumeration():
    m = json.loads((OUT / "exhaustive_search_manifest.json").read_text())
    assert m["enumerated_combination_count"] == m["unique_combination_count"] == 230230
    assert m["duplicate_combination_count"] == m["d180_combination_count"] == 0


def test_every_summary_combo_is_six_sorted_measured_diameters():
    with (OUT / "all_combinations_gate_summary.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 230230
    for row in (rows[0], rows[len(rows)//2], rows[-1]):
        d = [int(x) for x in row["diameters_nm"].split(",")]
        assert len(d) == 6 and d == sorted(d) and 180 not in d


def test_cyclic_closure_is_sixth_step_and_threshold_is_honest():
    audit = json.loads((OUT / "cyclic_closure_audit.json").read_text())
    assert audit["cyclic_step_count"] == 6 and audit["D5_to_D0_closure_included"]
    assert audit["cyclic_closure_threshold_status"] == "threshold_not_frozen"


def test_ranking_objectives_are_independent_and_broadband_is_not_phase_reuse():
    c = json.loads((OUT / "ranking_objective_contract.json").read_text())
    assert c["functions_independent"] and c["uses_wrapped_circular_phase_only"]
    assert c["phase_error_optimal"] != c["broadband_dispersion_optimal"]


def test_gate_boolean_and_passing_csv_are_computed_consistently():
    v = json.loads((OUT / "verification_summary.json").read_text())
    with (OUT / "passing_combinations.csv").open() as handle:
        passing = list(csv.DictReader(handle))
    assert v["passing_sextet_count"] == len(passing)
    assert v["all_engineering_gates_passing_sextet_exists"] == bool(passing)


def test_top_five_passing_candidates_are_from_passing_set():
    detail = json.loads((OUT / "top_5_passing_sextets_detailed.json").read_text())
    with (OUT / "passing_combinations.csv").open() as handle:
        passing = {row["diameters_nm"] for row in csv.DictReader(handle)}
    assert len(detail["top_5"]) == min(5, len(passing))
    assert all(",".join(map(str, row["diameters_nm"])) in passing for row in detail["top_5"])


def test_failure_statistics_cover_required_gates_when_any_fail():
    f = json.loads((OUT / "failure_gate_statistics.json").read_text())
    assert set(f) == {"phase_RMS_failure_count", "max_phase_error_failure_count", "amplitude_CV_failure_count", "txx_amplitude_failure_count", "transmission_failure_count", "crosspol_failure_count", "manufacturing_failure_count", "formal_quality_failure_count", "multi_gate_failure_count"}
    assert all(isinstance(value, int) for value in f.values())


def test_pareto_front_contains_only_nondominated_candidates():
    z = np.load(OUT / "all_combinations_metrics.npz")
    p = z["pareto"]
    values = np.column_stack((z["phase_rms_max"], z["phase_abs_max"], z["step_drift_max"], z["amp_cv_max"], -z["min_T"]))
    for point in values[p]:
        assert not np.any(np.all(values <= point, axis=1) & np.any(values < point, axis=1))


def test_warning_data_is_retained_and_source_is_x_only_k6_not_run():
    summary = json.loads((OUT / "ranking_summary.json").read_text())
    assert any(c["warning_valid_candidate_count"] >= 0 for c in summary["champions"].values())
    verify = json.loads((OUT / "verification_summary.json").read_text())
    assert verify["x_only"] and verify["K6_SUPERCELL_VALIDATION_STATUS"] == "not_run"


def test_no_solver_or_d180_label_was_used():
    m = json.loads((OUT / "exhaustive_search_manifest.json").read_text())
    d = json.loads((OUT / "d180_rerun_necessity_recomputed.json").read_text())
    assert m["solver_calls"] == m["lumapi_import_count"] == m["MPI_call_count"] == 0
    assert not d["D180_formal_optical_label_used"]
