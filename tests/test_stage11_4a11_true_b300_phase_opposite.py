from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stage11_lp_true_b300_phase_opposite_stage11_4a11.py"
spec = importlib.util.spec_from_file_location("a11", SCRIPT)
a11 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(a11)


def test_run_matrix_is_g2_only_and_12_cases():
    rows = a11.run_matrix()
    assert len(rows) == 12
    assert {int(float(r["height_nm"])) for r in rows} == {600}
    assert {int(float(r["phase_bin_deg"])) for r in rows} == {300}
    assert {int(float(r["wavelength_nm"])) for r in rows} == {451, 452, 453}
    assert {r["group_id"] for r in rows} == {a11.GROUP_ID}
    assert len({r["candidate_id"] for r in rows}) == 4
    assert {r["source_pair_id"] for r in rows} == a11.G2_SOURCE_IDS


def test_reassignment_helpers_match_a10_contract():
    assert a11.nearest_bin(302) == 300
    assert a11.nearest_bin(58) == 60
    assert a11.reassignment_flag(300, "strict") == "true_b300_candidate"
    assert a11.reassignment_flag(240, "loose") == "reassigned_B240"
    assert a11.reassignment_flag(60, "fail") == "none"


def test_rank_candidates_detects_reassignment():
    rows = []
    for wl in a11.WAVELENGTHS:
        rows.append({"candidate_id": "c", "case_id": str(wl), "wavelength_nm": str(wl), "status": "ok", "conversion_to_leakage_ratio": "8", "target_Tx": "0.8", "matrix_error": "0.3", "phase_error_deg": "80", "nearest_actual_bin_deg": "240", "reassignment_flag": "reassigned_B240"})
    ranked = a11.rank_candidates(rows)
    assert ranked[0]["best_pass_level"] == "fail"
    assert ranked[0]["reassignment_flag"] == "reassigned_B240"
