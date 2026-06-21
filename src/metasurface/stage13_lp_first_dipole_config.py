from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from metasurface.stage13_lp_dipole import CANDIDATE_ID, flt, read_csv_rows


APPROVAL_STATUS = "manually_approved_for_first_no_dbr_diagnostic"
PATCH_OPTION_ID = "A_small"
Q_NM = 107.9769465
Q_DEFINITION = "LP phase-bin pitch / 4"
SOURCE_Z_NM = -200.0
SOURCE_Z_STATUS = "diagnostic_manual_placeholder"
FIRST_RUN_CASE_IDS = ["center_x", "center_y"]
ALL_CASE_IDS = [
    "center_x",
    "center_y",
    "x_plus_qp_x",
    "x_plus_qp_y",
    "x_minus_qp_x",
    "x_minus_qp_y",
]

CASE_FIELDS = [
    "case_id",
    "candidate_id",
    "patch_option_id",
    "position",
    "dipole_orientation",
    "cone_deg",
    "target_LP",
    "target_LP_power",
    "leakage_LP_power",
    "LP_fraction",
    "target_to_leakage_ratio",
    "total_cone_power",
    "farfield_grid",
    "source_x_nm",
    "source_y_nm",
    "source_z_nm",
    "simulation_time_fs",
    "q_nm",
    "q_definition",
    "result_csv",
    "status",
    "blocking_issues",
]


def load_and_validate_inputs(
    patch_csv: Path,
    q_csv: Path,
    stage13_2_config_json: Path,
    stage12_fdtd_py: Path,
) -> dict[str, object]:
    patch_rows = read_csv_rows(patch_csv)
    q_rows = read_csv_rows(q_csv)
    if not stage13_2_config_json.is_file():
        raise FileNotFoundError(f"required Stage13-2 config not found: {stage13_2_config_json}")
    if not stage12_fdtd_py.is_file():
        raise FileNotFoundError(f"required Stage12 geometry builder not found: {stage12_fdtd_py}")
    patch = next((row for row in patch_rows if row.get("patch_option_id") == PATCH_OPTION_ID), None)
    if patch is None:
        raise ValueError("Stage13-2 A_small patch option is missing")
    if int(flt(patch.get("N_supercells_x"))) != 3 or int(flt(patch.get("N_supercells_y"))) != 19:
        raise ValueError("A_small no longer matches the manually approved 3 x 19 replication")
    if patch.get("estimated_geometry_count") != "342 dimers; 684 nanopillars":
        raise ValueError("A_small geometry count no longer matches the manual approval")
    q = next((row for row in q_rows if row.get("q_candidate_id") == "q_candidate_1"), None)
    if q is None or abs(flt(q.get("q_nm")) - Q_NM) > 1e-9:
        raise ValueError("Stage13-2 q_candidate_1 does not match the manually approved LP q")
    prior_config = json.loads(stage13_2_config_json.read_text(encoding="utf-8"))
    if prior_config.get("recommended_patch_option_id") != PATCH_OPTION_ID:
        raise ValueError("Stage13-2 recommended patch is not A_small")
    if abs(float(prior_config.get("recommended_q_nm")) - Q_NM) > 1e-9:
        raise ValueError("Stage13-2 recommended q does not match the manual approval")
    source_text = stage12_fdtd_py.read_text(encoding="utf-8")
    base_is_zero = 'fdtd.set("z min", 0)' in source_text
    reference_plane = (
        "Stage12 metasurface/pillar base plane z=0 nm; source_z=-200 nm is 200 nm below that plane"
        if base_is_zero
        else "current finite-patch/metasurface script reference plane; exact z=0 base could not be inferred"
    )
    return {
        "patch": patch,
        "q": q,
        "prior_config": prior_config,
        "source_reference_plane": reference_plane,
        "source_reference_plane_inferred": base_is_zero,
        "source_paths": [
            patch_csv.as_posix(),
            q_csv.as_posix(),
            stage13_2_config_json.as_posix(),
            stage12_fdtd_py.as_posix(),
        ],
    }


def build_cases() -> list[dict[str, object]]:
    positions = [("center", 0.0), ("x_plus_qp", Q_NM), ("x_minus_qp", -Q_NM)]
    rows: list[dict[str, object]] = []
    for position, source_x_nm in positions:
        for orientation in ("x", "y"):
            case_id = f"{position}_{orientation}"
            rows.append(
                {
                    "case_id": case_id,
                    "candidate_id": CANDIDATE_ID,
                    "patch_option_id": PATCH_OPTION_ID,
                    "position": position,
                    "dipole_orientation": orientation,
                    "cone_deg": "5;10;20",
                    "target_LP": "x",
                    "target_LP_power": "",
                    "leakage_LP_power": "",
                    "LP_fraction": "",
                    "target_to_leakage_ratio": "",
                    "total_cone_power": "",
                    "farfield_grid": 101,
                    "source_x_nm": source_x_nm,
                    "source_y_nm": 0.0,
                    "source_z_nm": SOURCE_Z_NM,
                    "simulation_time_fs": 100,
                    "q_nm": Q_NM,
                    "q_definition": Q_DEFINITION,
                    "result_csv": f"outputs/stage13_4_lp_first_no_dbr_dipole/{case_id}.csv",
                    "status": "prepared_not_run",
                    "blocking_issues": "",
                }
            )
    return rows


def build_config(evidence: dict[str, object], cases: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "stage": "Stage13-3",
        "task": "LP first no-DBR dipole manual approval config",
        "run_fdtd": False,
        "create_or_modify_fsp": False,
        "frozen_stage12_supercell_modified": False,
        "coordinate_convention": {
            "metasurface_plane": "x-y",
            "nanopillar_height_axis": "z",
            "source_location": "below metasurface",
            "target_emission": "+z",
            "farfield_monitor_direction": "+z",
            "gradient_axis": "x",
            "target_LP": "x",
            "K_definition": "six dimers per supercell, not six nanopillars",
        },
        "manual_approvals": {
            "finite_patch": {
                "patch_option_id": PATCH_OPTION_ID,
                "replication": {"N_supercells_x": 3, "N_supercells_y": 19},
                "estimated_geometry": {"dimers": 342, "nanopillars": 684},
                "approval_status": APPROVAL_STATUS,
                "reason": "preserves the frozen K=6 phase ramp and optical origin without forcing a center dimer",
            },
            "q": {
                "q_nm": Q_NM,
                "q_definition": Q_DEFINITION,
                "evidence": "Lambda_x / 6 / 4 = 2591.446716 / 6 / 4",
                "approval_status": APPROVAL_STATUS,
                "note": "Independently derived from the LP phase-bin pitch; numerical agreement with historical CP q is incidental and CP q was not reused.",
            },
            "source_z": {
                "source_z_nm": SOURCE_Z_NM,
                "source_z_status": SOURCE_Z_STATUS,
                "reference_plane": evidence["source_reference_plane"],
                "reference_plane_inferred": evidence["source_reference_plane_inferred"],
                "usage_boundary": "First no-DBR diagnostic depth inspired by CP-branch debugging only; not a final MicroLED MQW or DBR/RCLED device-stack position.",
                "approval_status": APPROVAL_STATUS,
            },
        },
        "device_options": {"DBR": "off", "RCLED": "off"},
        "finite_patch": PATCH_OPTION_ID,
        "farfield_grid": 101,
        "simulation_time_fs": 100,
        "cone_deg_list": [5, 10, 20],
        "full_xy_source_position_sweep": False,
        "dipole_model": {
            "orientations": ["x", "y"],
            "separate_simulations_required": True,
            "coherent_addition_between_orientations": False,
            "unpolarized_combination": "I_unpol = I_xdip + I_ydip",
        },
        "farfield_extraction": {
            "required": "complex vector Ex/Ey/Ez from farfieldvector3d or equivalent",
            "intensity_only_farfield3d_is_sufficient": False,
        },
        "lp_metrics": {
            "target_LP": "x",
            "leakage_LP": "y",
            "LP_fraction": "target_LP_power / (target_LP_power + leakage_LP_power)",
            "target_to_leakage_ratio": "target_LP_power / leakage_LP_power",
            "also_record": ["total_cone_power"],
        },
        "case_ids_prepared": [row["case_id"] for row in cases],
        "next_fdtd_case_ids": FIRST_RUN_CASE_IDS,
        "later_case_ids": [case_id for case_id in ALL_CASE_IDS if case_id not in FIRST_RUN_CASE_IDS],
        "case_blocking_issues": [],
        "global_notes": [
            "source_z is a diagnostic_manual_placeholder, not a final device-stack source position",
            "the next separately authorized FDTD task should run center_x and center_y only",
            "do not add DBR/RCLED or a full source-position sweep to the first diagnostic",
        ],
        "source_evidence_paths": evidence["source_paths"],
    }


def build_manual_approval_record(evidence: dict[str, object]) -> str:
    return f"""# Stage13-3 Manual Approval Record

## Scope

- Configuration and approval record only; no FDTD was run.
- No `.fsp` file was created, opened, or modified.
- The frozen Stage12 H500 LP-APCD K=6 x-gradient supercell remains unchanged.

## Approved finite patch

- `patch_option_id`: `{PATCH_OPTION_ID}`
- Replication: `3 x 19` tiles
- Estimated geometry: `342 dimers / 684 nanopillars`
- Approval status: `{APPROVAL_STATUS}`
- Reason: preserves the frozen K=6 phase ramp and optical origin without forcing a center dimer.

## Approved q

- `q_nm`: `{Q_NM}`
- Definition: `{Q_DEFINITION}`
- Evidence: `Lambda_x / 6 / 4 = 2591.446716 / 6 / 4`
- Approval status: `{APPROVAL_STATUS}`
- Boundary: q was independently derived from the LP phase-bin pitch. Its numerical match to historical CP q is incidental; CP q was not reused.

## Approved diagnostic source z

- `source_z_nm`: `{SOURCE_Z_NM}`
- Status: `{SOURCE_Z_STATUS}`
- Reference plane: {evidence['source_reference_plane']}.
- Approval status: `{APPROVAL_STATUS}`
- Usage boundary: borrowed only as a first no-DBR diagnostic depth inspired by CP-branch dipole debugging. It is not a final MicroLED MQW position and must not be used as a final DBR/RCLED device-stack value.

## Coordinate and polarization boundary

- Metasurface: x-y; nanopillar height: z; source below; emission/monitor: +z.
- Gradient axis: x; target LP: x; leakage LP: y.
- K=6 means six dimers per supercell.
- x/y dipoles are separate simulations. Never coherently add their fields.
- Later unpolarized response: `I_unpol = I_xdip + I_ydip`.
"""


def build_blocker_status() -> str:
    return f"""# Stage13-3 FDTD Blocker Status

## Decision

`CONFIGURATION_UNBLOCKED_FOR_NEXT_FIRST_NO_DBR_DIAGNOSTIC`

The patch, q, and diagnostic source-z decisions are manually approved. All six case rows have empty `blocking_issues`. This task still has `run_fdtd=false`; execution requires a separate FDTD task.

## Cleared decisions

- Patch: `{PATCH_OPTION_ID}`, 3 x 19 tiles.
- q: `{Q_NM}` nm from the LP phase-bin pitch / 4.
- source z: `{SOURCE_Z_NM}` nm as `{SOURCE_Z_STATUS}`.
- DBR: off.
- RCLED: off.

## Mandatory first-run order

Run only these two cases in the next FDTD stage:

1. `center_x`
2. `center_y`

Do not launch the four ±q cases until the two center diagnostics are reviewed.

## Prepared for later

- `center_x`
- `center_y`
- `x_plus_qp_x`
- `x_plus_qp_y`
- `x_minus_qp_x`
- `x_minus_qp_y`

## Non-blocking but mandatory caveats

- source z is a diagnostic placeholder, not a final MQW/device-stack location.
- Use complex-vector Ex/Ey/Ez for later LP projection; intensity-only `farfield3d` is insufficient.
- Keep x/y dipole simulations separate and combine only powers/intensities incoherently.
- Do not add DBR, RCLED, a larger patch, or a full x-y source-position sweep to the first diagnostic.
"""


def build_readme() -> str:
    return """# Stage13-3 First No-DBR Dipole Configuration

This package records the manual approvals for A_small, LP-derived q, and a diagnostic source z. It prepares six cases but runs nothing.

- `run_fdtd=false`
- DBR/RCLED: off
- First next-stage runs: `center_x`, then `center_y`
- Four ±q cases remain prepared for later
- source z = -200 nm is a diagnostic placeholder relative to the Stage12 pillar-base z=0 plane, not a final MQW/device-stack position
- Later LP projection requires complex vector Ex/Ey/Ez
- Unpolarized response uses `I_unpol = I_xdip + I_ydip`
"""
