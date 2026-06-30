from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_true_b300_mini_escape_stage11_4a12.py"
spec = importlib.util.spec_from_file_location("a12", SCRIPT)
a12 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a12)


def test_run_matrix_is_g3_only_and_6_cases():
    rows = a12.run_matrix()
    assert len(rows) == 6
    assert {int(float(r["height_nm"])) for r in rows} == {600}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {300}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {a12.GROUP_ID}
    assert len({r["candidate_id"] for r in rows}) == 2
    assert {r["source_pair_id"] for r in rows} == a12.G3_SOURCE_IDS


def test_reassignment_helpers_match_contract():
    assert a12.nearest_bin(302) == 300
    assert a12.nearest_bin(58) == 60
    assert a12.reassignment_flag(300, "strict") == "true_b300_candidate"
    assert a12.reassignment_flag(0, "loose") == "reassigned_B0"
    assert a12.reassignment_flag(60, "fail") == "none"


def test_rank_candidates_detects_true_b300_loose():
    rows = []
    for wl in a12.WAVELENGTHS:
        rows.append({"candidate_id": "c", "case_id": str(wl), "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "3.5", "target_Tx": "0.5", "matrix_error": "0.8", "phase_error_deg": "20", "nearest_actual_bin_deg": "300", "reassignment_flag": "true_b300_candidate"})
    ranked = a12.rank_candidates(rows)
    assert ranked[0]["best_pass_level"] == "loose"
    assert ranked[0]["reassignment_flag"] == "true_b300_candidate"
