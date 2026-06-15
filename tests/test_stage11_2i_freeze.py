import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_freeze_h500_actual_dimer_6bin_stage11_2i.py"
spec = importlib.util.spec_from_file_location("stage11_2i_freeze", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(candidate_id, phase_err, ratio, tx, leakage, matrix_error, strict=True):
    return {
        "candidate_id": candidate_id,
        "nearest_bin_deg": 120,
        "phase_err_deg": phase_err,
        "conversion_to_leakage_ratio": ratio,
        "selected_x_power": tx,
        "blocked_y_leakage": leakage,
        "matrix_error": matrix_error,
        "strict": strict,
    }


def test_rank_prefers_strict_over_higher_ratio_loose():
    strict = row("strict", 8.0, 6.5, 0.5, 0.07, 0.4, True)
    loose = row("loose", 12.0, 100.0, 1.0, 0.01, 0.1, False)
    assert mod.rank_key(strict, 120) < mod.rank_key(loose, 120)


def test_rank_prefers_smaller_phase_error_before_ratio():
    a = row("a", 2.0, 8.0, 0.5, 0.06, 0.2, True)
    b = row("b", 3.0, 100.0, 1.0, 0.01, 0.1, True)
    assert mod.rank_key(a, 120) < mod.rank_key(b, 120)


def test_nearest_bin_wraps_negative_phase_to_240():
    nearest, err = mod.nearest_bin(-127.365287)
    assert nearest == 240
    assert round(err, 6) == 7.365287
