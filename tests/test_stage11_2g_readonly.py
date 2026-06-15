import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage11_lp_apcd_diagnose_h500_120_selectivity_stage11_2g.py"
spec = importlib.util.spec_from_file_location("stage11_2g_readonly", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_nearest_phase_bin_wraps_negative_phase():
    nearest, err = mod.nearest_phase_bin(-127.365287)
    assert nearest == 240
    assert round(err, 6) == 7.365287


def test_normalize_row_computes_ratio6_leakage_budget():
    row = {
        "dimer_case_id": "H500DIMER_TEST_B120_x_pair_swap_G60_O-20",
        "t_xx_amp": "0.7",
        "t_yx_amp": "0.0",
        "t_xy_amp": "0.2",
        "t_yy_amp": "0.1",
        "t_xx_phase_deg": "123",
        "fdtd_status": "ok",
    }
    out = mod.normalize_row(row, Path("outputs/blue10k6_lp_apcd_stage11_2c_h500_dimer_alt_pairs/h500_dimer_alt_patch_fdtd_results_stage11_2c.csv"))
    assert out["nearest_bin_deg"] == 120
    assert round(out["selected_x_power"], 6) == 0.49
    assert round(out["leakage"], 6) == 0.05
    assert round(out["ratio"], 6) == 9.8
    assert round(out["leakage_budget_for_ratio6"], 6) == round(0.49 / 6, 6)
    assert out["strict_margin_ratio"] > 0
