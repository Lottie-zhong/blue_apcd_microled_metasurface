import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_frozen_sixbin_449_451_runner_stage11_3b1.py"
spec = importlib.util.spec_from_file_location("stage11_3b1", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_make_run_matrix_has_12_cases_and_no_450():
    rows = mod.make_run_matrix()
    assert len(rows) == 12
    assert {int(r["wavelength_nm"]) for r in rows} == {449, 451}
    assert {int(r["bin_deg"]) for r in rows} == {0, 60, 120, 180, 240, 300}
    assert all("WL450NM" not in r["dimer_case_id"] for r in rows)


def test_summarize_detects_weakest_ratio_and_phase():
    rows = [
        {"fdtd_status": "ok", "wavelength_nm": "449", "bin_deg": "0", "conversion_to_leakage_ratio": "8", "phase_error_to_bin_deg": "2"},
        {"fdtd_status": "ok", "wavelength_nm": "449", "bin_deg": "60", "conversion_to_leakage_ratio": "4", "phase_error_to_bin_deg": "9"},
    ]
    s = mod.summarize(rows)
    assert s["weakest_selectivity_bin"] == "60"
    assert s["worst_phase_drift_bin"] == "60"
    assert s["frozen_set_plausible_449_450_451"] is False
