from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from metasurface.stage12_k6_fdtd import build_model, flt, read_csv_rows, write_csv_rows


FORWARD_BINS = [0, 60, 120, 180, 240, 300]
OUTPUT_DIR_NAME = "stage12_3b_h500_lp_k6_gui_inspection"
FSP_FILENAME = "stage12_3b_h500_lp_k6_forward_gui_inspection.fsp"

MARKER_FIELDS = [
    "supercell_index",
    "phase_bin_deg",
    "candidate_id",
    "dimer_center_x_nm",
    "dimer_center_y_nm",
    "geometry_family",
    "actual_common_phase_deg",
    "Tx",
    "ratio",
    "matrix_error",
    "internal_clearance_nm",
    "neighbor_clearance_prev_nm",
    "neighbor_clearance_next_nm",
    "is_240_risk_bin",
    "is_20nm_min_clearance_dimer",
    "adjacent_to_20nm_min_clearance_region",
]


@dataclass(frozen=True)
class Stage12GuiPaths:
    layout_plan_csv: Path
    geometry_audit_csv: Path
    phase_amplitude_audit_csv: Path
    output_dir: Path
    fsp_path: Path


def validate_forward_layout(layout_rows: Sequence[dict[str, str]]) -> None:
    bins = [int(float(row["phase_bin_deg"])) for row in layout_rows]
    if bins != FORWARD_BINS:
        raise ValueError(f"Stage12-3B requires forward bins {FORWARD_BINS}; got {bins}")
    if len(layout_rows) != len(FORWARD_BINS):
        raise ValueError(f"Stage12-3B requires exactly 6 dimers; got {len(layout_rows)}")
    bad_h = [row for row in layout_rows if abs(flt(row.get("height_nm")) - 500.0) > 1e-6]
    if bad_h:
        raise ValueError("Stage12-3B is H500 only")


def build_marker_table(
    layout_rows: Sequence[dict[str, str]],
    geometry_rows: Sequence[dict[str, str]],
    phase_rows: Sequence[dict[str, str]],
) -> list[dict[str, object]]:
    validate_forward_layout(layout_rows)
    geometry_by_index = {int(float(row["supercell_index"])): row for row in geometry_rows}
    phase_by_index = {int(float(row["supercell_index"])): row for row in phase_rows}
    internal_values = [flt(row.get("internal_clearance_nm")) for row in geometry_rows]
    min_internal = min(value for value in internal_values if not math.isnan(value))
    min_indices = {
        int(float(row["supercell_index"]))
        for row in geometry_rows
        if abs(flt(row.get("internal_clearance_nm")) - min_internal) <= 1e-6
    }
    adjacent_indices = set(min_indices)
    for index in min_indices:
        if index > 0:
            adjacent_indices.add(index - 1)
        if index < len(layout_rows) - 1:
            adjacent_indices.add(index + 1)

    markers: list[dict[str, object]] = []
    for row in layout_rows:
        index = int(float(row["supercell_index"]))
        phase = phase_by_index[index]
        geometry = geometry_by_index[index]
        family = f"{row.get('j1_shape_family', '')}+rect_j2/{row.get('placement_type', '')}".strip("/")
        bin_deg = int(float(row["phase_bin_deg"]))
        markers.append(
            {
                "supercell_index": index,
                "phase_bin_deg": bin_deg,
                "candidate_id": row.get("candidate_id", ""),
                "dimer_center_x_nm": row.get("supercell_center_x_nm", ""),
                "dimer_center_y_nm": row.get("supercell_center_y_nm", ""),
                "geometry_family": family,
                "actual_common_phase_deg": phase.get("actual_common_phase_deg", ""),
                "Tx": phase.get("Tx", ""),
                "ratio": phase.get("conversion_to_leakage_ratio", phase.get("ratio", "")),
                "matrix_error": phase.get("matrix_error", ""),
                "internal_clearance_nm": geometry.get("internal_clearance_nm", ""),
                "neighbor_clearance_prev_nm": geometry.get("neighbor_clearance_prev_nm", ""),
                "neighbor_clearance_next_nm": geometry.get("neighbor_clearance_next_nm", ""),
                "is_240_risk_bin": str(bin_deg == 240),
                "is_20nm_min_clearance_dimer": str(index in min_indices),
                "adjacent_to_20nm_min_clearance_region": str(index in adjacent_indices),
            }
        )
    return markers


def write_summary(path: Path, fsp_path: Path, marker_rows: Sequence[dict[str, object]], fsp_generated: bool) -> None:
    bins = [str(row["phase_bin_deg"]) for row in marker_rows]
    risk = [row for row in marker_rows if str(row["is_240_risk_bin"]).lower() == "true"]
    min_clearance = min(flt(row.get("internal_clearance_nm")) for row in marker_rows)
    adjacent = [str(row["phase_bin_deg"]) for row in marker_rows if str(row["adjacent_to_20nm_min_clearance_region"]).lower() == "true"]
    risk_line = "none"
    if risk:
        r = risk[0]
        risk_line = f"bin {r['phase_bin_deg']} candidate {r['candidate_id']} Tx={r['Tx']} ratio={r['ratio']} matrix_error={r['matrix_error']}"
    text = f"""# Stage12-3B H500 LP-APCD K=6 GUI Inspection Setup

- Purpose: setup-only Lumerical GUI inspection file for the exact Stage12-1/Stage12-2 H500 forward K=6 supercell.
- Forward bin order: [{', '.join(bins)}].
- FSP path: `{fsp_path}`.
- FSP generated successfully: {fsp_generated}.
- Boundary: no FDTD was run.
- Boundary: no optimization was run.
- Boundary: this does not claim LP steering completion.

## Included Setup

The `.fsp` was built with the same Stage12-2 geometry builder used for the minimal validation: H500 dielectric dimers, periodic x/y FDTD region, z PML, x-LP source placeholder, and transmission monitor `T` placeholder for later GUI inspection. No separate substrate object was added because the Stage12-2 convention used object-defined dielectric pillars in the default background.

## Markers

- Marker table: `stage12_3b_geometry_marker_table.csv`.
- Key 240 deg risk bin: {risk_line}.
- Minimum internal clearance: {min_clearance:.6f} nm.
- Bins adjacent to the 20 nm minimum-clearance region: {', '.join(adjacent)}.

## Use Boundary

This file is for visual/setup inspection before any later Stage12-4 or GUI-driven diagnostic work. It should not be treated as a completed steering result by itself.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def export_gui_inspection_fsp(lumapi: object, runtime: object, layout_rows: Sequence[dict[str, str]], fsp_path: Path) -> None:
    fsp_path.parent.mkdir(parents=True, exist_ok=True)
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=getattr(runtime, "hide_gui", True))
        build_model(fdtd, layout_rows, polarization="x")
        fdtd.save(str(fsp_path))
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def run_stage12_3b(paths: Stage12GuiPaths, lumapi: object, runtime: object) -> dict[str, object]:
    layout_rows = read_csv_rows(paths.layout_plan_csv)
    geometry_rows = read_csv_rows(paths.geometry_audit_csv)
    phase_rows = read_csv_rows(paths.phase_amplitude_audit_csv)
    markers = build_marker_table(layout_rows, geometry_rows, phase_rows)
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    marker_csv = paths.output_dir / "stage12_3b_geometry_marker_table.csv"
    write_csv_rows(markers, marker_csv, MARKER_FIELDS)
    export_gui_inspection_fsp(lumapi, runtime, layout_rows, paths.fsp_path)
    summary_md = paths.output_dir / "stage12_3b_gui_inspection_summary.md"
    write_summary(summary_md, paths.fsp_path, markers, paths.fsp_path.exists())
    return {
        "fsp_path": str(paths.fsp_path),
        "fsp_generated": paths.fsp_path.exists(),
        "marker_csv": str(marker_csv),
        "summary_md": str(summary_md),
        "marker_count": len(markers),
    }
