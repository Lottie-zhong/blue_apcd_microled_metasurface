from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_dipole import build_config, build_geometry_audit, build_minimal_cases


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    pitch = 432.0
    period = 6 * pitch
    layout = []
    for index in range(6):
        center = (index + 0.5) * pitch
        layout.append(
            {
                "supercell_index": index,
                "candidate_id": f"d{index}",
                "supercell_period_lambda_nm": period,
                "supercell_center_x_nm": center,
                "supercell_center_y_nm": 0,
                "j1_shape_family": "square",
                "j1_geometry_params": json.dumps({"side_nm": 100.0}),
                "j1_abs_center_x_nm": center - 75.0,
                "j1_abs_center_y_nm": 0,
                "j2_abs_center_x_nm": center + 75.0,
                "j2_abs_center_y_nm": 0,
                "j2_length_nm": 100,
                "j2_width_nm": 80,
                "j2_rotation_deg": 0,
                "height_nm": 500,
            }
        )
    geometry = [{"internal_clearance_nm": 50, "min_neighbor_clearance_nm": 100} for _ in range(6)]
    metrics = [{"metric": "official_gradient_axis", "value": "x", "status": "FROZEN", "notes": "fixture"}]
    layout_csv = tmp_path / "layout.csv"
    geometry_csv = tmp_path / "geometry.csv"
    metrics_csv = tmp_path / "metrics.csv"
    gui_fsp = tmp_path / "missing.fsp"
    write_csv(layout_csv, layout)
    write_csv(geometry_csv, geometry)
    write_csv(metrics_csv, metrics)
    return layout_csv, geometry_csv, metrics_csv, gui_fsp


def test_audit_does_not_invent_finite_patch_q_or_center_dimer(tmp_path: Path) -> None:
    inputs = fixture_inputs(tmp_path)
    audit = build_geometry_audit(tmp_path, *inputs)

    assert audit["number_of_dimers"] == 6
    assert audit["has_true_center_dimer"] is False
    assert audit["patch_Nx"] is None
    assert audit["patch_Ny"] is None
    assert audit["q_nm"] is None
    assert audit["q_status"] == "requires_manual_definition"
    assert audit["geometry_audit_pass"] is False
    assert "q_requires_manual_definition" in audit["blocking_issues"]


def test_minimal_cases_are_six_separate_prepared_dipoles(tmp_path: Path) -> None:
    audit = build_geometry_audit(tmp_path, *fixture_inputs(tmp_path))
    cases = build_minimal_cases(audit)

    assert [row["case_id"] for row in cases] == [
        "center_x",
        "center_y",
        "x_plus_qp_x",
        "x_plus_qp_y",
        "x_minus_qp_x",
        "x_minus_qp_y",
    ]
    assert all(row["status"] == "prepared_not_run" for row in cases)
    assert all(row["target_LP_power"] == "" for row in cases)
    assert all(row["cone_deg"] == "5;10;20" for row in cases)
    assert all(row["source_x_nm"] == "" for row in cases[2:])


def test_config_forbids_fdtd_and_requires_complex_vector_far_field(tmp_path: Path) -> None:
    audit = build_geometry_audit(tmp_path, *fixture_inputs(tmp_path))
    config = build_config(audit, build_minimal_cases(audit))

    assert config["run_fdtd"] is False
    assert config["propagation_direction"] == "+z"
    assert config["farfield_monitor_direction"] == "+z"
    assert config["polarization_model"]["coherent_Ex_Ey_addition_across_dipole_orientations"] is False
    assert config["polarization_model"]["unpolarized_intensity_sum"] == "I_unpol = I_xdip + I_ydip"
    assert "Ex/Ey/Ez" in config["farfield_extraction"]["required"]
    assert config["farfield_extraction"]["farfield3d_intensity_only_is_sufficient"] is False
    assert config["lp_metrics"]["DoCP_is_main_metric"] is False
