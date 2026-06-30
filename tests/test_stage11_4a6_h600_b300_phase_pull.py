from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_h600_b300_phase_pull_stage11_4a6.py"
spec = importlib.util.spec_from_file_location("a6", SCRIPT)
a6 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a6)


def test_run_matrix_is_b300_only_and_18_cases():
    rows = a6.run_matrix()
    assert len(rows) == 18
    assert {int(float(r["height_nm"])) for r in rows} == {600}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {300}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {a6.GROUP_ID}
    assert len({r["candidate_id"] for r in rows}) == 6
    assert all("B300" in r["source_candidate_id"] for r in rows)


def test_candidate_level_and_near_miss_logic():
    assert a6.candidate_level(6.1, 0.50, 0.49, 24.0, True) == "strict"
    assert a6.candidate_level(3.1, 0.20, 0.99, 34.0, True) == "loose"
    assert a6.candidate_level(6.1, 0.50, 0.49, 40.0, True) == "fail"
    assert a6.is_near_miss(6.1, 0.50, 0.49, 40.0, True, "fail") is True


def test_rank_candidates_prefers_strict_over_near_miss():
    rows = []
    for wl in a6.WAVELENGTHS:
        rows.append({"candidate_id": "strict", "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "7", "target_Tx": "0.7", "matrix_error": "0.4", "phase_error_deg": "10"})
        rows.append({"candidate_id": "near", "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "9", "target_Tx": "0.8", "matrix_error": "0.4", "phase_error_deg": "40"})
    ranked = a6.rank_candidates(rows)
    assert ranked[0]["candidate_id"] == "strict"
    near = next(r for r in ranked if r["candidate_id"] == "near")
    assert near["near_miss"] == "true"
