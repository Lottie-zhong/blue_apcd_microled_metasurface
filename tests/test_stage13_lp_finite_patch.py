from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_finite_patch import (
    build_cases,
    build_config,
    build_patch_options,
    build_q_decisions,
    build_source_z_decisions,
    parse_frozen_supercell,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture_meta(tmp_path: Path) -> dict[str, object]:
    pitch = 432.0
    period = 6 * pitch
    layout = []
    for index in range(6):
        center = (index + 0.5) * pitch
        layout.append(
            {
                "supercell_index": index,
                "phase_bin_deg": index * 60,
                "candidate_id": f"d{index}",
                "supercell_period_lambda_nm": period,
                "p_y_nm": pitch,
                "dimer_pitch_x_nm": pitch,
                "supercell_center_x_nm": center,
                "supercell_center_y_nm": 0,
                "j1_shape_family": "square",
                "j1_geometry_params": json.dumps({"side_nm": 100}),
                "j1_abs_center_x_nm": center - 75,
                "j1_abs_center_y_nm": 0,
                "j2_abs_center_x_nm": center + 75,
                "j2_abs_center_y_nm": 0,
                "j2_length_nm": 100,
                "j2_width_nm": 80,
                "j2_rotation_deg": 0,
            }
        )
    geometry = [{"internal_clearance_nm": 50, "min_neighbor_clearance_nm": 100} for _ in layout]
    layout_csv = tmp_path / "layout.csv"
    geometry_csv = tmp_path / "geometry.csv"
    write_csv(layout_csv, layout)
    write_csv(geometry_csv, geometry)
    return parse_frozen_supercell(layout_csv, geometry_csv, [layout_csv, geometry_csv], tmp_path)


def test_patch_options_preserve_frozen_A_and_expose_B_C_tradeoffs(tmp_path: Path) -> None:
    options = build_patch_options(fixture_meta(tmp_path))
    by_id = {row["patch_option_id"]: row for row in options}

    assert len(options) >= 3
    assert by_id["A_small"]["recommended_for_first_FDTD"] is True
    assert by_id["A_small"]["phase_ramp_preserved"] is True
    assert by_id["A_small"]["has_true_center_dimer"] is False
    assert by_id["B_dimer_centered_small"]["has_true_center_dimer"] is True
    assert by_id["C_integer_fabrication_small"]["max_coordinate_perturbation_nm"] >= 0
    assert by_id["C_integer_fabrication_small"]["recommended_for_first_FDTD"] is False


def test_q_is_inferred_from_lp_pitch_not_cp_and_source_z_stays_null(tmp_path: Path) -> None:
    meta = fixture_meta(tmp_path)
    q_rows = build_q_decisions(meta, "fixture_lp_layout.csv")
    z_rows = build_source_z_decisions()
    q1 = q_rows[0]

    assert q1["q_nm"] == 108.0
    assert q1["safe_to_use_for_stage13_minimal_xline"] is True
    assert q1["recommended"] is True
    assert all(row["source_z_nm"] is None for row in z_rows)
    assert all(row["safe_to_use"] is False for row in z_rows)


def test_cases_fill_safe_q_but_remain_blocked_and_not_run(tmp_path: Path) -> None:
    meta = fixture_meta(tmp_path)
    patches = build_patch_options(meta)
    q_rows = build_q_decisions(meta, "fixture_lp_layout.csv")
    z_rows = build_source_z_decisions()
    cases = build_cases(patches, q_rows)
    config = build_config(meta, patches, q_rows, z_rows, cases)

    assert [row["case_id"] for row in cases] == [
        "center_x",
        "center_y",
        "x_plus_qp_x",
        "x_plus_qp_y",
        "x_minus_qp_x",
        "x_minus_qp_y",
    ]
    assert cases[2]["source_x_nm"] == 108.0
    assert cases[4]["source_x_nm"] == -108.0
    assert all(row["source_z_nm"] == "" for row in cases)
    assert all(row["status"] == "prepared_not_run" for row in cases)
    assert config["run_fdtd"] is False
    assert config["create_or_modify_fsp"] is False
    assert config["source_z_status"] == "requires_manual_definition"
    assert config["manual_approval_required_before_fdtd"] is True
