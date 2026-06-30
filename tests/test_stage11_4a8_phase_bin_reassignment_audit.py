from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_phase_bin_reassignment_audit_stage11_4a8.py"
spec = importlib.util.spec_from_file_location("a8", SCRIPT)
a8 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a8)


def test_nearest_bin_wraps_correctly():
    assert a8.nearest_bin(358) == 0
    assert a8.nearest_bin(49) == 60
    assert a8.nearest_bin(310) == 300


def test_row_audit_reassigns_wrong_b300_to_actual_bin():
    row = {
        "candidate_id": "c",
        "wavelength_nm": "451",
        "selected_phase_deg": "55",
        "target_Tx": "0.8",
        "y_leakage": "0.05",
        "conversion_to_leakage_ratio": "16",
        "matrix_error": "0.2",
        "pass_level": "fail",
    }
    out = a8.row_audit(row)
    assert out["nearest_actual_bin_deg"] == 60
    assert out["pass_level_as_original"] == "fail"
    assert out["pass_level_as_reassigned"] == "strict"
    assert out["reassignment_recommendation"] == "candidate_for_B60"


def test_write_outputs_reports_b300_unsolved():
    summary = a8.write_outputs()
    assert summary["planning_only"] is True
    assert summary["no_fdtd_lumerical"] is True
    assert summary["b300_solved"] is False
    assert 300 in summary["remaining_missing_or_weak_bins"]
    assert a8.AUDIT_CSV.exists()
    assert a8.REPORT_MD.exists()
