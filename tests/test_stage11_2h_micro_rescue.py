import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_y_pair_micro_rescue_placement_is_legal_for_compact_geometry():
    mod = load_module("scripts/stage11_lp_apcd_generate_h500_120_y_pair_micro_rescue_stage11_2h.py", "stage11_2h_generate")
    row = {
        "j1_shape_family": "circle",
        "j1_geometry_params": '{"diameter_nm": 100.0}',
        "j2_length_nm": "150",
        "j2_width_nm": "110",
    }
    *_coords, dgap, edge, legal = mod.place_y_pair(row, 20.0, -30.0, False)
    assert legal
    assert dgap >= 16
    assert edge >= 10


def test_audit_metric_computes_leakage_budget_and_ratio():
    mod = load_module("scripts/stage11_lp_apcd_audit_h500_120_y_pair_micro_rescue_stage11_2h.py", "stage11_2h_audit")
    row = {
        "dimer_case_id": "TEST",
        "t_xx_amp": "0.8",
        "t_yx_amp": "0",
        "t_xy_amp": "0.2",
        "t_yy_amp": "0.1",
        "t_xx_phase_deg": "121",
        "fdtd_status": "ok",
    }
    out = mod.metric(row)
    assert out["nearest_bin_deg"] == "120"
    assert round(float(out["selected_x_power"]), 6) == 0.64
    assert round(float(out["blocked_y_leakage"]), 6) == 0.05
    assert round(float(out["conversion_to_leakage_ratio"]), 6) == 12.8
    assert round(float(out["leakage_budget_for_ratio6"]), 6) == round(0.64 / 6, 6)
