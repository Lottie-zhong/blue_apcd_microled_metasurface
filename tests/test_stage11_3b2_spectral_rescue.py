import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_spectral_rescue_stage11_3b2.py"
spec = importlib.util.spec_from_file_location("stage11_3b2", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_select_candidate_geometries_caps_targets_and_controls():
    rows = [
        {"dimer_case_id": "H500DIMER2C_004_B120_x_pair_swap_G60_O-20", "target_actual_bin_deg": "120"},
        {"dimer_case_id": "H500DIMER2H_009_B120_y_pair_noswap_G20_O-40", "target_actual_bin_deg": "120"},
        {"dimer_case_id": "H500DIMER2F_026_B240_x_pair_swap_G90_O-28", "target_actual_bin_deg": "240"},
        {"dimer_case_id": "H500DIMER12A_001_B240_x_pair_swap_G90_O-28", "target_actual_bin_deg": "240"},
        {"dimer_case_id": "H500DIMER2D_006_B240_x_pair_swap_G80_O-30", "target_actual_bin_deg": "300"},
    ]
    selected = mod.select_candidate_geometries(rows)
    assert len(selected) == 5
    assert {int(r["target_bin_deg"]) for r in selected} == {120, 240, 300}
    assert any(r["candidate_id"] == mod.CONTROLS[120] for r in selected)
    assert len(selected) <= 20


def test_summarize_candidates_flags_failed_ratio_gate():
    rows = [
        {"fdtd_status": "ok", "target_bin_deg": "240", "candidate_id": "A", "wavelength_nm": "449", "conversion_to_leakage_ratio": "7", "Tx": "0.7", "matrix_error": "0.2", "phase_error_to_target_deg": "5"},
        {"fdtd_status": "ok", "target_bin_deg": "240", "candidate_id": "A", "wavelength_nm": "450", "conversion_to_leakage_ratio": "5", "Tx": "0.7", "matrix_error": "0.2", "phase_error_to_target_deg": "5"},
        {"fdtd_status": "ok", "target_bin_deg": "240", "candidate_id": "A", "wavelength_nm": "451", "conversion_to_leakage_ratio": "8", "Tx": "0.7", "matrix_error": "0.2", "phase_error_to_target_deg": "5"},
    ]
    summary = mod.summarize_candidates(rows)[0]
    assert summary["rescue_candidate"] == "false"
    assert "ratio" in summary["failed_gate"]
    assert summary["worst_ratio"] == "5.000000"
