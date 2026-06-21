from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_4_center_dipole import (
    ALLOWED_CASE_IDS,
    EXPECTED_NANOPILLARS,
    build_patch_inventory,
    incoherent_rows,
    interpret_center,
    load_approved_plan,
    lp_metrics_from_fields,
    resolved_setup,
    validate_case_selection,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture_plan(tmp_path: Path) -> dict[str, object]:
    config = {
        "finite_patch": "A_small",
        "manual_approvals": {
            "finite_patch": {
                "replication": {"N_supercells_x": 3, "N_supercells_y": 19},
                "estimated_geometry": {"dimers": 342, "nanopillars": 684},
            }
        },
        "device_options": {"DBR": "off", "RCLED": "off"},
        "next_fdtd_case_ids": ["center_x", "center_y"],
        "farfield_grid": 101,
        "simulation_time_fs": 100,
        "cone_deg_list": [5, 10, 20],
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    cases_path = tmp_path / "cases.csv"
    write_csv(
        cases_path,
        [
            {"case_id": "center_x", "source_x_nm": 0, "source_y_nm": 0, "source_z_nm": -200},
            {"case_id": "center_y", "source_x_nm": 0, "source_y_nm": 0, "source_z_nm": -200},
        ],
    )
    layout = []
    pitch = 432.0
    period = pitch * 6
    for index in range(6):
        center = (index + 0.5) * pitch
        layout.append(
            {
                "supercell_index": index,
                "phase_bin_deg": index * 60,
                "candidate_id": f"d{index}",
                "lambda_nm": 450,
                "height_nm": 500,
                "supercell_period_lambda_nm": period,
                "p_y_nm": pitch,
                "j1_shape_family": "square",
                "j1_geometry_params": json.dumps({"side_nm": 100}),
                "j1_abs_center_x_nm": center - 70,
                "j1_abs_center_y_nm": 0,
                "j2_abs_center_x_nm": center + 70,
                "j2_abs_center_y_nm": 0,
                "j2_length_nm": 100,
                "j2_width_nm": 80,
                "j2_rotation_deg": 0,
            }
        )
    layout_path = tmp_path / "layout.csv"
    write_csv(layout_path, layout)
    return load_approved_plan(config_path, cases_path, layout_path)


def test_exact_center_case_gate_rejects_any_other_selection() -> None:
    validate_case_selection(ALLOWED_CASE_IDS)
    with pytest.raises(ValueError):
        validate_case_selection(["center_x"])
    with pytest.raises(ValueError):
        validate_case_selection(["center_x", "center_y", "x_plus_qp_x"])


def test_A_small_inventory_count_and_no_device_stack(tmp_path: Path) -> None:
    plan = fixture_plan(tmp_path)
    inventory = build_patch_inventory(plan)
    setup = resolved_setup(plan, inventory)

    assert len(inventory) == EXPECTED_NANOPILLARS
    assert setup["estimated_dimers"] == 342
    assert setup["DBR"] is False
    assert setup["RCLED"] is False
    assert "no substrate" in setup["background_stack"]
    assert setup["monitor_direction"] == "+z"
    assert setup["solver_processes"] == 4


def test_complex_vector_lp_projection_and_Ez_total_handling() -> None:
    ux = np.linspace(-0.4, 0.4, 11)
    uy = np.linspace(-0.4, 0.4, 11)
    ex = np.ones((11, 11), dtype=np.complex128) * (1 + 1j)
    ey = np.ones((11, 11), dtype=np.complex128) * 0.5j
    ez = np.ones((11, 11), dtype=np.complex128) * 0.25
    rows = lp_metrics_from_fields(ex, ey, ez, ux, uy, [20])

    assert len(rows) == 1
    assert rows[0]["LP_fraction"] == pytest.approx(2.0 / 2.25)
    assert rows[0]["total_cone_power"] > rows[0]["target_LP_power"] + rows[0]["leakage_LP_power"]


def metric_row(case: str, cone: float, target: float, leak: float, total: float) -> dict[str, object]:
    return {
        "case_id": case,
        "cone_deg": cone,
        "target_LP_power": target,
        "leakage_LP_power": leak,
        "total_cone_power": total,
        "status": "ok",
        "extraction_status": "complex_vector_ok",
    }


def test_incoherent_sum_and_stage_interpretation() -> None:
    rows = []
    for cone in (5.0, 10.0, 20.0):
        rows.append(metric_row("center_x", cone, 8.0, 1.0, 9.5))
        rows.append(metric_row("center_y", cone, 2.0, 3.0, 5.5))
    incoh = incoherent_rows(rows)
    status, recommendation = interpret_center(incoh)

    assert len(incoh) == 3
    assert incoh[0]["target_LP_power_incoherent"] == 10.0
    assert incoh[0]["leakage_LP_power_incoherent"] == 4.0
    assert incoh[0]["LP_fraction_incoherent"] == pytest.approx(10 / 14)
    assert status == "pass_minimal_center"
    assert "+/-q" in recommendation
