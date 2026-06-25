import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_spectral_robust_phase_library_audit_stage11_3a.py"
spec = importlib.util.spec_from_file_location("stage11_3a", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_candidate_pool_normalizes_phase_and_bin():
    row = {
        "candidate_id": "H500DIMER_TEST_B240_x_pair_swap_G80_O-30",
        "phase_deg": "-119.0",
        "Tx": "0.7",
        "leakage": "0.05",
        "ratio": "14",
        "matrix_error": "0.2",
    }
    out = mod.normalize_candidate(row, Path("outputs/stage12_11a_h500_lp_k6_phase_origin_search/stage12_11a_candidate_pool.csv"))
    assert out["nearest_bin_450_deg"] == 240
    assert out["geometry_family"] == "x_pair_swap"
    assert out["ratio_450"] == 14


def test_spectral_metric_extraction_and_collapse_detection():
    metrics = {
        "ratio_449": 8.0,
        "ratio_450": 12.0,
        "ratio_451": 3.5,
        "ratio_452": 1.0,
        "phase_449": 230.0,
        "phase_451": 250.0,
    }
    fields = mod.robust_score_fields(metrics)
    assert fields["min_ratio_449_451"] == 3.5
    assert fields["long_wavelength_collapse_flag"] is True
    assert round(fields["phase_slope_449_451"], 6) == 10.0


def test_rescue_priority_classification_for_240_collapse():
    row = {"intended_bin_deg": 240, "nearest_bin_450_deg": 240, "long_wavelength_collapse_flag": True, "min_ratio_449_451": 3.7}
    assert mod.classify_rescue_priority(row) == "priority_1_240_long_wavelength_collapse"


def test_ml_lite_readiness_thresholds():
    assert mod.classify_ml_readiness(42)[0] == "not_ready"
    assert mod.classify_ml_readiness(250)[0] == "ml_lite_pilot_possible"
    assert mod.classify_ml_readiness(600)[0] == "ml_lite_ready"
