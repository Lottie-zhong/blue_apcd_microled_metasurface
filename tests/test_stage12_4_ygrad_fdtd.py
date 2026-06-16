from __future__ import annotations

import math
from pathlib import Path

from metasurface.stage12_k6_fdtd import read_csv_rows
from metasurface.stage12_k6_ygrad_fdtd import (
    GROUP_PREFIX,
    audit_ygrad_geometry,
    build_marker_table,
    compute_selectivity,
    dimer_label,
    normalize_ygrad_orders,
    transform_xgrad_to_ygrad,
    y_order_power,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE12_1 = REPO_ROOT / "outputs/stage12_1_h500_lp_k6_forward_layout"

def test_ygrad_transform_moves_centers_without_rotating_internal_geometry() -> None:
    source = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_layout_plan.csv")
    ygrad = transform_xgrad_to_ygrad(source)
    assert [row["phase_bin_deg"] for row in ygrad] == [0, 60, 120, 180, 240, 300]
    assert all(float(row["supercell_center_x_nm"]) == 0.0 for row in ygrad)
    assert [round(float(row["supercell_center_y_nm"]), 6) for row in ygrad] == [round((i + 0.5) * float(source[0]["dimer_pitch_x_nm"]), 6) for i in range(6)]
    for src, dst in zip(source, ygrad):
        assert math.isclose(float(dst["j1_center_x_nm"]), float(src["j1_abs_center_x_nm"]) - float(src["supercell_center_x_nm"]))
        assert math.isclose(float(dst["j1_center_y_nm"]), float(src["j1_abs_center_y_nm"]) - float(src["supercell_center_y_nm"]))
        assert math.isclose(float(dst["j2_center_x_nm"]), float(src["j2_abs_center_x_nm"]) - float(src["supercell_center_x_nm"]))
        assert math.isclose(float(dst["j2_center_y_nm"]), float(src["j2_abs_center_y_nm"]) - float(src["supercell_center_y_nm"]))
        assert dst["j1_geometry_params"] == src["j1_geometry_params"]
        assert dst["j2_rotation_deg"] == src["j2_rotation_deg"]

def test_ygrad_order_interpretation_uses_m_plus_one_and_uy() -> None:
    raw = [
        {"order_n": 0, "order_m": 0, "expected_ux": 0.0, "expected_uy": 0.0, "order_efficiency_source_norm": 0.1},
        {"order_n": 0, "order_m": 1, "expected_ux": 0.0, "expected_uy": math.sin(math.radians(10.0)), "order_efficiency_source_norm": 0.3},
        {"order_n": 1, "order_m": 0, "expected_ux": math.sin(math.radians(10.0)), "expected_uy": 0.0, "order_efficiency_source_norm": 0.2},
    ]
    rows = normalize_ygrad_orders(raw, "run", "x")
    assert y_order_power(rows, 1) == 0.3
    target = [row for row in rows if row["order_n"] == 0 and row["order_m"] == 1][0]
    assert math.isclose(target["theta_yz_deg"], 10.0, abs_tol=1e-9)

def test_ygrad_group_labels_and_marker_flags() -> None:
    source = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_layout_plan.csv")
    phase = read_csv_rows(STAGE12_1 / "stage12_1_k6_forward_phase_amplitude_audit.csv")
    ygrad = transform_xgrad_to_ygrad(source)
    geometry = audit_ygrad_geometry(ygrad)
    markers = build_marker_table(ygrad, geometry, phase)
    assert dimer_label(4, 240) == "DIMER_04_BIN240_phase240_RISK"
    assert GROUP_PREFIX == "K6_LP_APCD_H500_forward_ygrad_plus10"
    assert [row["phase_bin_deg"] for row in markers] == [0, 60, 120, 180, 240, 300]
    assert [row["phase_bin_deg"] for row in markers if row["is_240_risk_bin"] == "True"] == [240]

def test_ygrad_selectivity_metrics_use_target_m_plus_one() -> None:
    result_rows = [
        {"polarization": "x", "fdtd_status": "ok", "dominant_order_n": 0, "dominant_order_m": 1, "plus1_y_direction_consistent": True},
        {"polarization": "y", "fdtd_status": "ok", "dominant_order_n": 0, "dominant_order_m": 2},
    ]
    order_rows = [
        {"polarization": "x", "order_n": 0, "order_m": 1, "order_power_source_norm": 0.3, "total_transmission": 0.5},
        {"polarization": "x", "order_n": 1, "order_m": 0, "order_power_source_norm": 0.2, "total_transmission": 0.5},
        {"polarization": "y", "order_n": 0, "order_m": 1, "order_power_source_norm": 0.03, "total_transmission": 0.4},
        {"polarization": "y", "order_n": 0, "order_m": 2, "order_power_source_norm": 0.08, "total_transmission": 0.4},
    ]
    metrics = {row["metric"]: row["value"] for row in compute_selectivity(result_rows, order_rows)}
    assert metrics["effective_target_power"] == 0.3
    assert metrics["effective_blocked_leakage"] == 0.03
    assert metrics["target_order_selectivity_ratio"] == 10.0
    assert metrics["dominant_y_leakage_order_m"] == 2
    assert metrics["overall_stage12_4_pass"] is True
