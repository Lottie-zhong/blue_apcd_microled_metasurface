from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable, Sequence


CANDIDATE_ID = "H500_LP_APCD_K6_XGRAD_FROZEN_STAGE12"
Q_STATUS = "requires_manual_definition"
AUDIT_FIELDS = [
    "candidate_id",
    "source_design_origin",
    "input_file_paths",
    "propagation_direction",
    "gradient_axis",
    "target_output_LP",
    "patch_Nx",
    "patch_Ny",
    "number_of_supercells",
    "number_of_dimers",
    "number_of_units",
    "has_true_center_unit",
    "has_true_center_dimer",
    "center_unit_id",
    "center_dimer_id",
    "center_dimer_x_nm",
    "center_dimer_y_nm",
    "source_center_x_nm",
    "source_center_y_nm",
    "source_center_z_nm",
    "q_definition",
    "q_nm",
    "q_status",
    "x_plus_qp_x_nm",
    "x_minus_qp_x_nm",
    "mirror_error_nm",
    "left_edge_distance_nm",
    "right_edge_distance_nm",
    "edge_symmetry_error_nm",
    "nearest_J1_distance_nm",
    "nearest_J2_distance_nm",
    "nearest_dimer_or_pillar_summary",
    "geometry_audit_pass",
    "blocking_issues",
    "warnings",
    "integer_nm_centers",
    "integer_nm_dimensions",
    "integer_degree_rotations",
    "min_gap_nm",
    "sub_nm_coordinates_detected",
    "non_integer_angles_detected",
    "fabrication_notes",
]

CASE_FIELDS = [
    "case_id",
    "candidate_id",
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
    "result_csv",
    "status",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"required input file not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv_rows(rows: Iterable[dict[str, object]], path: Path, fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def nullable(value: float, digits: int = 9) -> float | None:
    return None if math.isnan(value) else round(value, digits)


def is_integer(value: float, tol: float = 1e-6) -> bool:
    return not math.isnan(value) and abs(value - round(value)) <= tol


def _j1_dimensions_and_rotation(row: dict[str, str]) -> tuple[float, float, float]:
    params = json.loads(row.get("j1_geometry_params") or "{}")
    family = row.get("j1_shape_family", "")
    if family == "circle":
        diameter = flt(params.get("diameter_nm"))
        return diameter, diameter, flt(params.get("rotation_deg"), 0.0)
    if family == "square":
        side = flt(params.get("side_nm"))
        return side, side, flt(params.get("rotation_deg"), 0.0)
    return flt(params.get("length_nm")), flt(params.get("width_nm")), flt(params.get("rotation_deg"), 0.0)


def _centered_geometry(layout_rows: Sequence[dict[str, str]]) -> tuple[list[dict[str, object]], float]:
    if len(layout_rows) != 6:
        raise ValueError(f"frozen Stage12 LP K=6 layout must contain 6 dimers; got {len(layout_rows)}")
    period_values = {round(flt(row.get("supercell_period_lambda_nm")), 9) for row in layout_rows}
    if len(period_values) != 1 or any(math.isnan(value) for value in period_values):
        raise ValueError("unable to establish one Stage12 supercell period")
    period_nm = next(iter(period_values))
    shift_nm = period_nm / 2.0
    geometry: list[dict[str, object]] = []
    for row in layout_rows:
        j1_w, j1_h, j1_rot = _j1_dimensions_and_rotation(row)
        j2_w = flt(row.get("j2_length_nm"))
        j2_h = flt(row.get("j2_width_nm"))
        dimer_x = flt(row.get("supercell_center_x_nm")) - shift_nm
        dimer_y = flt(row.get("supercell_center_y_nm"))
        j1_x = flt(row.get("j1_abs_center_x_nm")) - shift_nm
        j1_y = flt(row.get("j1_abs_center_y_nm"))
        j2_x = flt(row.get("j2_abs_center_x_nm")) - shift_nm
        j2_y = flt(row.get("j2_abs_center_y_nm"))
        geometry.append(
            {
                "id": str(row.get("candidate_id", "")),
                "index": int(flt(row.get("supercell_index"))),
                "dimer_x": dimer_x,
                "dimer_y": dimer_y,
                "j1_x": j1_x,
                "j1_y": j1_y,
                "j1_w": j1_w,
                "j1_h": j1_h,
                "j1_rot": j1_rot,
                "j2_x": j2_x,
                "j2_y": j2_y,
                "j2_w": j2_w,
                "j2_h": j2_h,
                "j2_rot": flt(row.get("j2_rotation_deg"), 0.0),
                "height": flt(row.get("height_nm")),
            }
        )
    return geometry, period_nm


def build_geometry_audit(
    repo_root: Path,
    layout_csv: Path,
    geometry_csv: Path,
    official_metrics_csv: Path,
    gui_fsp: Path,
) -> dict[str, object]:
    layout_rows = read_csv_rows(layout_csv)
    geometry_rows = read_csv_rows(geometry_csv)
    read_csv_rows(official_metrics_csv)
    geometry, period_nm = _centered_geometry(layout_rows)

    dimer_center = next((item for item in geometry if abs(float(item["dimer_x"])) <= 1e-6 and abs(float(item["dimer_y"])) <= 1e-6), None)
    j1_distances = [(math.hypot(float(item["j1_x"]), float(item["j1_y"])), item) for item in geometry]
    j2_distances = [(math.hypot(float(item["j2_x"]), float(item["j2_y"])), item) for item in geometry]
    all_pillars = sorted(
        [(distance, "J1", item) for distance, item in j1_distances]
        + [(distance, "J2", item) for distance, item in j2_distances],
        key=lambda entry: entry[0],
    )
    min_x = min(min(float(item["j1_x"]) - float(item["j1_w"]) / 2.0, float(item["j2_x"]) - float(item["j2_w"]) / 2.0) for item in geometry)
    max_x = max(max(float(item["j1_x"]) + float(item["j1_w"]) / 2.0, float(item["j2_x"]) + float(item["j2_w"]) / 2.0) for item in geometry)
    center_values = [
        coordinate
        for item in geometry
        for coordinate in (float(item["dimer_x"]), float(item["dimer_y"]), float(item["j1_x"]), float(item["j1_y"]), float(item["j2_x"]), float(item["j2_y"]))
    ]
    dimension_values = [
        value
        for item in geometry
        for value in (float(item["j1_w"]), float(item["j1_h"]), float(item["j2_w"]), float(item["j2_h"]), float(item["height"]))
    ]
    angle_values = [value for item in geometry for value in (float(item["j1_rot"]), float(item["j2_rot"]))]
    gap_candidates = [
        flt(row.get("internal_clearance_nm")) for row in geometry_rows
    ] + [flt(row.get("min_neighbor_clearance_nm")) for row in geometry_rows]
    finite_gaps = [value for value in gap_candidates if not math.isnan(value)]

    blockers = [
        "frozen_stage12_artifact_is_periodic_supercell_not_finite_patch",
        "finite_patch_Nx_Ny_and_replication_rule_missing",
        "q_requires_manual_definition",
        "source_center_z_requires_manual_definition",
    ]
    warnings = [
        "K=6 means six dimers; centered source supercell has no true x=0 center dimer",
        "GUI FSP is evidence-only and was not opened or modified",
        "sub-nm centers belong to the frozen Stage12 layout and were not rounded",
    ]
    if not gui_fsp.is_file():
        warnings.append("optional Stage12 GUI inspection FSP was not found")
    paths = [layout_csv, geometry_csv, official_metrics_csv]
    if gui_fsp.is_file():
        paths.append(gui_fsp)
    relative_paths = [path.relative_to(repo_root).as_posix() if path.is_relative_to(repo_root) else str(path) for path in paths]
    nearest_summary = [
        {
            "pillar": pillar,
            "dimer_index": int(item["index"]),
            "candidate_id": item["id"],
            "distance_nm": round(distance, 9),
        }
        for distance, pillar, item in all_pillars[:4]
    ]
    return {
        "candidate_id": CANDIDATE_ID,
        "source_design_origin": "frozen Stage12 H500 LP-APCD K=6 x-gradient periodic supercell",
        "input_file_paths": json.dumps(relative_paths, ensure_ascii=False),
        "propagation_direction": "+z",
        "gradient_axis": "x",
        "target_output_LP": "x",
        "patch_Nx": None,
        "patch_Ny": None,
        "number_of_supercells": None,
        "number_of_dimers": 6,
        "number_of_units": 6,
        "has_true_center_unit": False,
        "has_true_center_dimer": dimer_center is not None,
        "center_unit_id": None,
        "center_dimer_id": None if dimer_center is None else dimer_center["id"],
        "center_dimer_x_nm": None if dimer_center is None else nullable(float(dimer_center["dimer_x"])),
        "center_dimer_y_nm": None if dimer_center is None else nullable(float(dimer_center["dimer_y"])),
        "source_center_x_nm": 0.0,
        "source_center_y_nm": 0.0,
        "source_center_z_nm": None,
        "q_definition": "undefined: no frozen LP finite-patch/unit-cell source-position rule found",
        "q_nm": None,
        "q_status": Q_STATUS,
        "x_plus_qp_x_nm": None,
        "x_minus_qp_x_nm": None,
        "mirror_error_nm": None,
        "left_edge_distance_nm": round(abs(min_x), 9),
        "right_edge_distance_nm": round(abs(max_x), 9),
        "edge_symmetry_error_nm": round(abs(abs(min_x) - abs(max_x)), 9),
        "nearest_J1_distance_nm": round(min(j1_distances, key=lambda item: item[0])[0], 9),
        "nearest_J2_distance_nm": round(min(j2_distances, key=lambda item: item[0])[0], 9),
        "nearest_dimer_or_pillar_summary": json.dumps(nearest_summary, ensure_ascii=False),
        "geometry_audit_pass": False,
        "blocking_issues": json.dumps(blockers, ensure_ascii=False),
        "warnings": json.dumps(warnings, ensure_ascii=False),
        "integer_nm_centers": all(is_integer(value) for value in center_values),
        "integer_nm_dimensions": all(is_integer(value) for value in dimension_values),
        "integer_degree_rotations": all(is_integer(value) for value in angle_values),
        "min_gap_nm": None if not finite_gaps else round(min(finite_gaps), 9),
        "sub_nm_coordinates_detected": any(not is_integer(value) for value in center_values),
        "non_integer_angles_detected": any(not is_integer(value) for value in angle_values),
        "fabrication_notes": (
            f"Frozen source supercell period is {period_nm:.6f} nm; physical dimensions and rotations are integer-valued, "
            "but centered coordinates include sub-nm values. No rounding or geometry modification was performed."
        ),
    }


def build_geometry_markdown(audit: dict[str, object]) -> str:
    blockers = json.loads(str(audit["blocking_issues"]))
    warnings = json.loads(str(audit["warnings"]))
    lines = [
        "# Stage13-0 LP Dipole Geometry Audit",
        "",
        "## Scope boundary",
        "",
        "- Read-only audit of the frozen Stage12 H500 LP-APCD K=6 x-gradient geometry.",
        "- No FDTD simulation was run; no `.fsp` file was created or modified.",
        "- Coordinate system: metasurface in x-y, height along z, source below, emission and monitor toward +z.",
        "- K=6 means six dimers, not six nanopillars.",
        "",
        "## Geometry conclusion",
        "",
        f"- Candidate: `{audit['candidate_id']}`.",
        "- The frozen Stage12 artifact is one periodic K=6 supercell; a finite-patch Nx/Ny replication definition was not found.",
        f"- True center unit: `{audit['has_true_center_unit']}`.",
        f"- True center dimer: `{audit['has_true_center_dimer']}`.",
        f"- Source center x/y: `{audit['source_center_x_nm']}`, `{audit['source_center_y_nm']}` nm.",
        f"- Source center z: `{audit['source_center_z_nm']}`.",
        f"- q status: `{audit['q_status']}`; q_nm: `{audit['q_nm']}`.",
        "- CP-branch q was not reused and no LP q was guessed.",
        f"- Left/right footprint edge distances: `{audit['left_edge_distance_nm']}` / `{audit['right_edge_distance_nm']}` nm.",
        f"- Edge symmetry error: `{audit['edge_symmetry_error_nm']}` nm.",
        f"- Geometry audit pass: `{audit['geometry_audit_pass']}`.",
        "",
        "## Manufacturability",
        "",
        f"- Integer-nm centers: `{audit['integer_nm_centers']}`.",
        f"- Integer-nm dimensions: `{audit['integer_nm_dimensions']}`.",
        f"- Integer-degree rotations: `{audit['integer_degree_rotations']}`.",
        f"- Minimum inferred gap: `{audit['min_gap_nm']}` nm.",
        f"- Sub-nm coordinates detected: `{audit['sub_nm_coordinates_detected']}`.",
        f"- Non-integer angles detected: `{audit['non_integer_angles_detected']}`.",
        f"- Notes: {audit['fabrication_notes']}",
        "",
        "## Blocking issues before FDTD",
        "",
    ]
    lines.extend(f"- `{item}`" for item in blockers)
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in warnings)
    lines.extend(["", "## Evidence paths", "", f"`{audit['input_file_paths']}`", ""])
    return "\n".join(lines)


def build_minimal_cases(audit: dict[str, object], result_dir: str = "outputs/stage13_1_lp_dipole_results") -> list[dict[str, object]]:
    q_nm = audit.get("q_nm")
    source_z = audit.get("source_center_z_nm")
    positions = [
        ("center", audit.get("source_center_x_nm")),
        ("x_plus_qp", None if q_nm is None else float(audit["source_center_x_nm"]) + float(q_nm)),
        ("x_minus_qp", None if q_nm is None else float(audit["source_center_x_nm"]) - float(q_nm)),
    ]
    rows: list[dict[str, object]] = []
    for position, source_x in positions:
        for orientation in ("x", "y"):
            case_id = f"{position}_{orientation}"
            rows.append(
                {
                    "case_id": case_id,
                    "candidate_id": audit["candidate_id"],
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
                    "source_x_nm": "" if source_x is None else source_x,
                    "source_y_nm": audit.get("source_center_y_nm", 0.0),
                    "source_z_nm": "" if source_z is None else source_z,
                    "simulation_time_fs": 100,
                    "result_csv": f"{result_dir}/{case_id}.csv",
                    "status": "prepared_not_run",
                }
            )
    return rows


def build_config(audit: dict[str, object], cases: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "stage": "Stage13-1",
        "candidate_id": audit["candidate_id"],
        "design_state": "frozen_read_only",
        "target_LP": "x",
        "propagation_direction": "+z",
        "farfield_monitor_direction": "+z",
        "farfield_grid": 101,
        "simulation_time_fs": 100,
        "cone_deg_list": [5, 10, 20],
        "cone_30_deg": {"enabled": False},
        "source_positions": ["center", "x_plus_qp", "x_minus_qp"],
        "dipole_orientations": ["x", "y"],
        "run_fdtd": False,
        "q_definition": audit["q_definition"],
        "q_nm": audit["q_nm"],
        "q_status": audit["q_status"],
        "source_center_z_nm": audit["source_center_z_nm"],
        "case_ids": [row["case_id"] for row in cases],
        "polarization_model": {
            "separate_dipole_cases": True,
            "coherent_Ex_Ey_addition_across_dipole_orientations": False,
            "unpolarized_intensity_sum": "I_unpol = I_xdip + I_ydip",
        },
        "lp_metrics": {
            "target_LP_power": "x-LP projected far-field power",
            "leakage_LP_power": "y-LP projected far-field power",
            "LP_fraction": "target_LP_power / (target_LP_power + leakage_LP_power)",
            "target_to_leakage_ratio": "target_LP_power / leakage_LP_power",
            "DoCP_is_main_metric": False,
        },
        "farfield_extraction": {
            "required": "complex vector far field Ex/Ey/Ez from farfieldvector3d or equivalent",
            "farfield3d_intensity_only_is_sufficient": False,
            "reason": "LP projection requires complex vector field components",
        },
        "blocking_issues_before_fdtd": json.loads(str(audit["blocking_issues"])),
    }


def build_readme(audit: dict[str, object]) -> str:
    return """# Stage13-0/1 LP Dipole Preparation

This package is configuration and geometry-audit metadata only. It does not run FDTD and does not modify the frozen H500 LP-APCD K=6 x-gradient design.

## Coordinate convention

- Metasurface plane: x-y; nanopillar height: z.
- Dipole/MicroLED source: below the metasurface.
- Target emission and far-field monitor: +z.
- Structure/source x-y origin: (0, 0).
- The frozen periodic K=6 source supercell has no true center dimer. A finite-patch definition is still missing.

## Source and polarization rules

- Prepare x- and y-oriented in-plane electric dipoles as separate cases.
- Never coherently add Ex/Ey fields from different dipole orientations.
- Unpolarized response is the incoherent power sum: `I_unpol = I_xdip + I_ydip`.
- q is not copied from the CP branch. Here `q_nm` is null with `requires_manual_definition` because no frozen LP finite-patch source-position rule was found.

## LP metrics

- `target_LP_power`: x-LP projected far-field power.
- `leakage_LP_power`: y-LP projected far-field power.
- `LP_fraction = target_LP_power / (target_LP_power + leakage_LP_power)`.
- `target_to_leakage_ratio = target_LP_power / leakage_LP_power`.
- DoCP is not a main metric for this LP branch.

## Required later extraction

Later extraction must use the complex vector far field (`Ex`, `Ey`, `Ez`) from `farfieldvector3d` or an equivalent API. `farfield3d` intensity alone is insufficient for LP projection.

## Run boundary

- `run_fdtd = false`.
- Six cases are prepared but not run: center/x-plus-q/x-minus-q, each with x/y dipole orientation.
- Cone statistics are configured for 5, 10, and 20 degrees; 30 degrees is disabled.
- Resolve every item in `blocking_issues_before_fdtd` before any FDTD task.
"""


def load_single_audit(path: Path) -> dict[str, object]:
    rows = read_csv_rows(path)
    if len(rows) != 1:
        raise ValueError(f"expected one geometry audit row; got {len(rows)}")
    row: dict[str, object] = dict(rows[0])
    for key in ("q_nm", "source_center_z_nm", "source_center_x_nm", "source_center_y_nm"):
        value = str(row.get(key, "")).strip()
        row[key] = None if value == "" else float(value)
    return row
