import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_240_300_expanded_search_stage11_3b4.py"
spec = importlib.util.spec_from_file_location("stage11_3b4", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_phase_distance_wraps():
    assert mod.phase_dist(350, 10) == 20
    assert mod.phase_dist(10, 350) == 20


def test_candidate_pool_cap_logic():
    rows = {}
    for i in range(20):
        rows[f"H500DIMER12A_{i:03d}_B240_x_pair_swap_G90_O-28"] = {"dimer_case_id": f"H500DIMER12A_{i:03d}_B240_x_pair_swap_G90_O-28", "target_actual_bin_deg": "240"}
    for i in range(20):
        rows[f"H500DIMER12D_{i:03d}_B300_x_pair_swap_G70_O-30"] = {"dimer_case_id": f"H500DIMER12D_{i:03d}_B300_x_pair_swap_G70_O-30", "target_actual_bin_deg": "300"}
    selected = mod.select_expanded_candidates(rows)
    assert len(selected[240]) <= 12
    assert len(selected[300]) <= 12


def test_manifest_only_missing_wavelengths():
    existing = {(mod.CONTROL_BINS[0], 449): {}, (mod.CONTROL_BINS[0], 451): {}}
    rows_by_id = {mod.CONTROL_BINS[0]: {"dimer_case_id": mod.CONTROL_BINS[0]}, mod.FROZEN_240: {"dimer_case_id": mod.FROZEN_240, "target_actual_bin_deg": "240"}, mod.FROZEN_300: {"dimer_case_id": mod.FROZEN_300, "target_actual_bin_deg": "300"}}
    manifest, evidence = mod.build_manifest(existing, rows_by_id)
    assert any(r["candidate_id"] == mod.CONTROL_BINS[0] and r["wavelength_nm"] == "450" for r in manifest)
    assert next(r for r in evidence if r["candidate_id"] == mod.CONTROL_BINS[0])["missing_before"] == "450"


def test_candidate_ranking_gates_fail_ratio():
    rows = []
    for wl in mod.WAVELENGTHS:
        rows.append({"target_bin_deg": 240, "candidate_id": "A", "wavelength_nm": wl, "conversion_to_leakage_ratio": "5", "Tx": "0.8", "matrix_error": "0.2", "phase_error_to_target_deg": "5"})
    ranked = mod.rank_candidates(rows)
    assert ranked[0]["candidate_pass_flag"] == "false"
    assert "ratio" in ranked[0]["failed_gates"]


def test_tuple_reconstruction_no_duplicate_ids():
    rows = []
    ids = ["A0", "A60", "A120", "A180", "A240", "A300"]
    for slot, cid in zip([0, 60, 120, 180, 240, 300], ids):
        for wl in mod.WAVELENGTHS:
            rows.append({"target_bin_deg": slot, "candidate_id": cid, "wavelength_nm": wl, "selected_phase_deg": slot, "Tx": "0.8", "conversion_to_leakage_ratio": "8", "matrix_error": "0.2", "phase_error_to_target_deg": "0"})
    ranking = mod.rank_candidates(rows)
    tuples = mod.tuple_after_expansion(rows, ranking)
    assert len({tuples[0][f"slot_{s}_candidate_id"] for s in [0, 60, 120, 180, 240, 300]}) == 6
