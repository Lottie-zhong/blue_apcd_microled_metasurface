from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_h650_b300_direct_escape_stage11_4a17.py"
spec = importlib.util.spec_from_file_location("a10", SCRIPT)
a10 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a10)


def test_run_matrix_is_g1_only_and_excludes_b60_donors():
    rows = a10.run_matrix()
    assert len(rows) == 12
    assert {int(float(r["height_nm"])) for r in rows} == {650}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {300}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {a10.GROUP_ID}
    assert len({r["candidate_id"] for r in rows}) == 4
    assert not ({r["source_pair_id"] for r in rows} & a10.EXCLUDED_SOURCE_IDS)


def test_nearest_bin_and_reassignment_flag():
    assert a10.nearest_bin(302) == 300
    assert a10.nearest_bin(58) == 60
    assert a10.reassignment_flag(300, "strict") == "true_b300_candidate"
    assert a10.reassignment_flag(60, "strict") == "reassigned_B60"
    assert a10.reassignment_flag(60, "fail") == "none"


def test_rank_candidates_detects_true_b300_strict():
    rows = []
    for wl in a10.WAVELENGTHS:
        rows.append({"candidate_id": "c", "case_id": str(wl), "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "8", "target_Tx": "0.8", "matrix_error": "0.3", "phase_error_deg": "10", "nearest_actual_bin_deg": "300", "reassignment_flag": "true_b300_candidate"})
    ranked = a10.rank_candidates(rows)
    assert ranked[0]["best_pass_level"] == "strict"
    assert ranked[0]["reassignment_flag"] == "true_b300_candidate"
