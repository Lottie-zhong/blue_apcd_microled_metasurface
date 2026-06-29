from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_h600_b240_role_recombination_stage11_4a3.py"
spec = importlib.util.spec_from_file_location("stage11_4a3", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_run_matrix_scope_and_count():
    rows = mod.run_matrix()
    assert len(rows) == 24
    assert {int(float(r["height_nm"])) for r in rows} == {600}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {240}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {mod.GROUP_ID}


def test_pass_level_reuses_a1_thresholds():
    assert mod.pass_level(6.0, 0.45, 0.50, 25.0) == "strict"
    assert mod.pass_level(3.0, 0.10, 1.00, 35.0) == "loose"
    assert mod.pass_level(1.0, 0.50, 0.40, 10.0) == "fail"


def test_result_fields_match_requested_columns():
    expected = [
        "case_id", "group_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx",
        "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error",
        "pass_level", "result_csv", "status",
    ]
    assert mod.RESULT_FIELDS == expected


def test_ranking_detects_near_miss():
    rows = []
    for wl in [451, 452, 453]:
        rows.append({
            "candidate_id": "C1", "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "2.5",
            "target_Tx": "0.30", "matrix_error": "0.80", "phase_error_deg": "30", "pass_level": "fail",
        })
    ranked = mod.rank_candidates(rows)
    assert ranked[0]["complete_451_452_453"] == "true"
    assert ranked[0]["near_miss"] == "true"
