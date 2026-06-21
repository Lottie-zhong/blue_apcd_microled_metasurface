from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from metasurface.stage13_lp_first_dipole_config import (
    ALL_CASE_IDS,
    FIRST_RUN_CASE_IDS,
    Q_NM,
    SOURCE_Z_NM,
    build_blocker_status,
    build_cases,
    build_config,
    load_and_validate_inputs,
)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture_evidence(tmp_path: Path) -> dict[str, object]:
    patch_csv = tmp_path / "patch.csv"
    q_csv = tmp_path / "q.csv"
    config_json = tmp_path / "config.json"
    fdtd_py = tmp_path / "stage12_k6_fdtd.py"
    write_csv(
        patch_csv,
        [
            {
                "patch_option_id": "A_small",
                "N_supercells_x": 3,
                "N_supercells_y": 19,
                "estimated_geometry_count": "342 dimers; 684 nanopillars",
            }
        ],
    )
    write_csv(q_csv, [{"q_candidate_id": "q_candidate_1", "q_nm": Q_NM}])
    config_json.write_text(json.dumps({"recommended_patch_option_id": "A_small", "recommended_q_nm": Q_NM}), encoding="utf-8")
    fdtd_py.write_text('fdtd.set("z min", 0)\n', encoding="utf-8")
    return load_and_validate_inputs(patch_csv, q_csv, config_json, fdtd_py)


def test_manual_inputs_validate_and_reference_plane_is_explicit(tmp_path: Path) -> None:
    evidence = fixture_evidence(tmp_path)

    assert evidence["source_reference_plane_inferred"] is True
    assert "pillar base plane z=0" in evidence["source_reference_plane"]


def test_six_cases_are_complete_prepared_and_unblocked() -> None:
    cases = build_cases()

    assert [row["case_id"] for row in cases] == ALL_CASE_IDS
    assert all(row["status"] == "prepared_not_run" for row in cases)
    assert all(row["blocking_issues"] == "" for row in cases)
    assert all(row["source_z_nm"] == SOURCE_Z_NM for row in cases)
    assert cases[2]["source_x_nm"] == Q_NM
    assert cases[4]["source_x_nm"] == -Q_NM


def test_config_is_no_dbr_no_run_and_center_first(tmp_path: Path) -> None:
    config = build_config(fixture_evidence(tmp_path), build_cases())

    assert config["run_fdtd"] is False
    assert config["create_or_modify_fsp"] is False
    assert config["device_options"] == {"DBR": "off", "RCLED": "off"}
    assert config["next_fdtd_case_ids"] == FIRST_RUN_CASE_IDS
    assert config["case_blocking_issues"] == []
    assert config["manual_approvals"]["source_z"]["source_z_status"] == "diagnostic_manual_placeholder"
    assert config["dipole_model"]["coherent_addition_between_orientations"] is False
    assert "complex vector" in config["farfield_extraction"]["required"]
    assert "CONFIGURATION_UNBLOCKED" in build_blocker_status()
