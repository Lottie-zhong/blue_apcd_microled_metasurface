from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage11_lp_h600_b240_mechanism_expansion_stage11_4a5.py"
spec = importlib.util.spec_from_file_location("stage11_4a5", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_run_matrix_scope_and_count():
    rows = mod.run_matrix()
    assert len(rows) == 36
    assert {int(float(r["height_nm"])) for r in rows} == {600}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {240}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {mod.GROUP_ID}


def test_mechanism_families_are_expanded():
    geoms = mod.mechanism_geometries()
    placements = {g["placement_type"] for g in geoms}
    assert {"x_pair", "y_pair", "diag_pair"}.issubset(placements)
    assert max(float(g["gap_nm"]) for g in geoms if g["placement_type"] == "x_pair") >= 120


def test_near_miss_requires_selectivity_gain_and_matrix_gain():
    assert mod.near_miss(2.1, 0.90, 40.0) is True
    assert mod.near_miss(1.5, 0.90, 40.0) is False
    assert mod.near_miss(2.1, 1.10, 40.0) is False


def test_result_fields_match_requested_columns():
    assert mod.RESULT_FIELDS == ["case_id", "group_id", "height_nm", "wavelength_nm", "phase_bin_deg", "candidate_id", "target_Tx", "y_leakage", "conversion_to_leakage_ratio", "selected_phase_deg", "phase_error_deg", "matrix_error", "pass_level", "result_csv", "status"]
