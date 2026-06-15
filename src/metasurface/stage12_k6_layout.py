from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from metasurface.stage12_k6_analytic import DEFAULT_DIMER_PITCH_X_NM, DEFAULT_WAVELENGTH_NM, FORWARD_BINS, K, read_phase_library


OUTPUT_DIR_NAME = "stage12_1_h500_lp_k6_forward_layout"
FORWARD_ORDER = FORWARD_BINS

LAYOUT_FIELDS = [
    "supercell_index",
    "phase_bin_deg",
    "candidate_id",
    "source_stage",
    "source_file",
    "source_plan_file",
    "source_plan_id",
    "j1_candidate_id",
    "j2_candidate_id",
    "height_nm",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "supercell_period_lambda_nm",
    "dimer_pitch_x_nm",
    "supercell_center_x_nm",
    "supercell_center_y_nm",
    "placement_type",
    "swap_order",
    "gap_nm",
    "local_offset_nm",
    "j1_shape_family",
    "j1_geometry_params",
    "j1_center_x_nm",
    "j1_center_y_nm",
    "j1_abs_center_x_nm",
    "j1_abs_center_y_nm",
    "j1_footprint_x_nm",
    "j1_footprint_y_nm",
    "j2_length_nm",
    "j2_width_nm",
    "j2_rotation_deg",
    "j2_center_x_nm",
    "j2_center_y_nm",
    "j2_abs_center_x_nm",
    "j2_abs_center_y_nm",
    "j2_footprint_x_nm",
    "j2_footprint_y_nm",
]

GEOMETRY_AUDIT_FIELDS = [
    "supercell_index",
    "phase_bin_deg",
    "candidate_id",
    "source_plan_geometry_legal",
    "internal_clearance_nm",
    "neighbor_clearance_prev_nm",
    "neighbor_clearance_next_nm",
    "min_neighbor_clearance_nm",
    "assigned_cell_left_nm",
    "assigned_cell_right_nm",
    "footprint_min_x_nm",
    "footprint_max_x_nm",
    "footprint_min_y_nm",
    "footprint_max_y_nm",
    "unit_cell_margin_x_nm",
    "unit_cell_margin_y_nm",
    "supercell_margin_x_nm",
    "crosses_unit_boundary",
    "crosses_supercell_boundary",
    "geometry_legal",
    "audit_notes",
]

PHASE_AUDIT_FIELDS = [
    "supercell_index",
    "phase_bin_deg",
    "candidate_id",
    "actual_common_phase_deg",
    "phase_err_deg",
    "Tx",
    "blocked_y_leakage",
    "conversion_to_leakage_ratio",
    "matrix_error",
]


@dataclass(frozen=True)
class Footprint:
    label: str
    center_x_nm: float
    center_y_nm: float
    width_x_nm: float
    width_y_nm: float

    @property
    def min_x(self) -> float:
        return self.center_x_nm - self.width_x_nm / 2.0

    @property
    def max_x(self) -> float:
        return self.center_x_nm + self.width_x_nm / 2.0

    @property
    def min_y(self) -> float:
        return self.center_y_nm - self.width_y_nm / 2.0

    @property
    def max_y(self) -> float:
        return self.center_y_nm + self.width_y_nm / 2.0


@dataclass(frozen=True)
class LayoutBundle:
    layout_rows: list[dict[str, object]]
    geometry_rows: list[dict[str, object]]
    phase_rows: list[dict[str, object]]
    run_plan_md: str
    summary_md: str


def build_stage12_1_layout(repo_root: Path, handoff_csv: Path) -> LayoutBundle:
    entries = read_phase_library(handoff_csv)
    plan_rows_by_candidate = find_source_plan_rows(repo_root, [entries[bin_deg].candidate_id for bin_deg in FORWARD_ORDER])
    layout_rows: list[dict[str, object]] = []
    phase_rows: list[dict[str, object]] = []
    lambda_nm = DEFAULT_WAVELENGTH_NM
    pitch_x_nm = DEFAULT_DIMER_PITCH_X_NM
    supercell_period_nm = pitch_x_nm * K
    p_y_nm = 432.0

    for index, bin_deg in enumerate(FORWARD_ORDER):
        entry = entries[bin_deg]
        source = plan_rows_by_candidate[entry.candidate_id]
        center_x = (index + 0.5) * pitch_x_nm
        center_y = 0.0
        j1_w, j1_h = j1_footprint(source)
        j2_w = flt(source.get("j2_length_nm"))
        j2_h = flt(source.get("j2_width_nm"))
        row = {
            "supercell_index": index,
            "phase_bin_deg": bin_deg,
            "candidate_id": entry.candidate_id,
            "source_stage": entry.source_stage,
            "source_file": entry.source_file,
            "source_plan_file": source["_source_plan_file"],
            "source_plan_id": source.get("dimer_case_id") or source.get("dimer_patch_id") or source.get("candidate_id") or "",
            "j1_candidate_id": source.get("j1_candidate_id", ""),
            "j2_candidate_id": source.get("j2_candidate_id", ""),
            "height_nm": source.get("height_nm", "500.000000"),
            "lambda_nm": source.get("lambda_nm", f"{lambda_nm:.6f}"),
            "p_x_nm": source.get("p_x_nm", f"{pitch_x_nm:.6f}"),
            "p_y_nm": source.get("p_y_nm", f"{p_y_nm:.6f}"),
            "supercell_period_lambda_nm": supercell_period_nm,
            "dimer_pitch_x_nm": pitch_x_nm,
            "supercell_center_x_nm": center_x,
            "supercell_center_y_nm": center_y,
            "placement_type": source.get("placement_type", ""),
            "swap_order": source.get("swap_order", ""),
            "gap_nm": source.get("gap_nm", ""),
            "local_offset_nm": source.get("local_offset_nm", ""),
            "j1_shape_family": source.get("j1_shape_family", ""),
            "j1_geometry_params": source.get("j1_geometry_params", ""),
            "j1_center_x_nm": source.get("j1_center_x_nm", ""),
            "j1_center_y_nm": source.get("j1_center_y_nm", ""),
            "j1_abs_center_x_nm": center_x + flt(source.get("j1_center_x_nm")),
            "j1_abs_center_y_nm": center_y + flt(source.get("j1_center_y_nm")),
            "j1_footprint_x_nm": j1_w,
            "j1_footprint_y_nm": j1_h,
            "j2_length_nm": source.get("j2_length_nm", ""),
            "j2_width_nm": source.get("j2_width_nm", ""),
            "j2_rotation_deg": source.get("j2_rotation_deg", ""),
            "j2_center_x_nm": source.get("j2_center_x_nm", ""),
            "j2_center_y_nm": source.get("j2_center_y_nm", ""),
            "j2_abs_center_x_nm": center_x + flt(source.get("j2_center_x_nm")),
            "j2_abs_center_y_nm": center_y + flt(source.get("j2_center_y_nm")),
            "j2_footprint_x_nm": j2_w,
            "j2_footprint_y_nm": j2_h,
        }
        layout_rows.append(row)
        phase_rows.append(
            {
                "supercell_index": index,
                "phase_bin_deg": bin_deg,
                "candidate_id": entry.candidate_id,
                "actual_common_phase_deg": entry.actual_common_phase_deg,
                "phase_err_deg": entry.phase_err_deg,
                "Tx": entry.Tx,
                "blocked_y_leakage": entry.blocked_y_leakage,
                "conversion_to_leakage_ratio": entry.conversion_to_leakage_ratio,
                "matrix_error": entry.matrix_error,
            }
        )

    geometry_rows = audit_geometry(layout_rows, pitch_x_nm, p_y_nm, supercell_period_nm)
    summary_md = build_summary_md(handoff_csv, layout_rows, geometry_rows, phase_rows, lambda_nm, supercell_period_nm)
    run_plan_md = build_stage12_2_run_plan_md(lambda_nm, supercell_period_nm, geometry_rows, phase_rows)
    return LayoutBundle(layout_rows, geometry_rows, phase_rows, run_plan_md, summary_md)


def find_source_plan_rows(repo_root: Path, candidate_ids: Sequence[str]) -> dict[str, dict[str, str]]:
    pending = set(candidate_ids)
    found: dict[str, dict[str, str]] = {}
    for path in sorted((repo_root / "outputs").rglob("*.csv")):
        name = path.name.lower()
        if "plan" not in name or "stage12_" in path.as_posix().lower():
            continue
        for row in read_csv_rows(path):
            row_id = row.get("dimer_case_id") or row.get("dimer_patch_id") or row.get("candidate_id") or ""
            if row_id in pending:
                row = dict(row)
                row["_source_plan_file"] = path.relative_to(repo_root).as_posix()
                found[row_id] = row
                pending.remove(row_id)
                if not pending:
                    return found
    if pending:
        raise ValueError(f"missing source plan rows for: {sorted(pending)}")
    return found


def audit_geometry(layout_rows: Sequence[dict[str, object]], pitch_x_nm: float, p_y_nm: float, supercell_period_nm: float) -> list[dict[str, object]]:
    footprints_by_index = [footprints_for_row(row) for row in layout_rows]
    rows: list[dict[str, object]] = []
    for index, row in enumerate(layout_rows):
        fps = footprints_by_index[index]
        internal = footprint_clearance(fps[0], fps[1])
        prev_clearance = min_neighbor_clearance(footprints_by_index[index - 1], fps, shift_b_nm=0.0)
        if index == 0:
            prev_clearance = min_neighbor_clearance(footprints_by_index[-1], fps, shift_a_nm=-supercell_period_nm)
        next_clearance = min_neighbor_clearance(fps, footprints_by_index[(index + 1) % len(layout_rows)], shift_b_nm=0.0)
        if index == len(layout_rows) - 1:
            next_clearance = min_neighbor_clearance(fps, footprints_by_index[0], shift_b_nm=supercell_period_nm)
        min_neighbor = min(prev_clearance, next_clearance)
        min_x = min(fp.min_x for fp in fps)
        max_x = max(fp.max_x for fp in fps)
        min_y = min(fp.min_y for fp in fps)
        max_y = max(fp.max_y for fp in fps)
        cell_left = index * pitch_x_nm
        cell_right = (index + 1) * pitch_x_nm
        margin_x = min(min_x - cell_left, cell_right - max_x)
        margin_y = min(min_y + p_y_nm / 2.0, p_y_nm / 2.0 - max_y)
        supercell_margin_x = min(min_x, supercell_period_nm - max_x)
        crosses_unit = margin_x < 0 or margin_y < 0
        crosses_supercell = min_x < 0 or max_x > supercell_period_nm or min_y < -p_y_nm / 2.0 or max_y > p_y_nm / 2.0
        source_legal = str(row.get("source_plan_geometry_legal") or row.get("geometry_legal", "true")).lower() != "false"
        legal = source_legal and internal >= 20.0 and min_neighbor >= 20.0 and not crosses_unit and not crosses_supercell
        notes = []
        if internal < 20.0:
            notes.append("internal_clearance_below_20nm")
        if min_neighbor < 20.0:
            notes.append("neighbor_clearance_below_20nm")
        if crosses_unit:
            notes.append("crosses_assigned_unit_cell")
        if crosses_supercell:
            notes.append("crosses_supercell_or_y_period")
        rows.append(
            {
                "supercell_index": row["supercell_index"],
                "phase_bin_deg": row["phase_bin_deg"],
                "candidate_id": row["candidate_id"],
                "source_plan_geometry_legal": source_legal,
                "internal_clearance_nm": internal,
                "neighbor_clearance_prev_nm": prev_clearance,
                "neighbor_clearance_next_nm": next_clearance,
                "min_neighbor_clearance_nm": min_neighbor,
                "assigned_cell_left_nm": cell_left,
                "assigned_cell_right_nm": cell_right,
                "footprint_min_x_nm": min_x,
                "footprint_max_x_nm": max_x,
                "footprint_min_y_nm": min_y,
                "footprint_max_y_nm": max_y,
                "unit_cell_margin_x_nm": margin_x,
                "unit_cell_margin_y_nm": margin_y,
                "supercell_margin_x_nm": supercell_margin_x,
                "crosses_unit_boundary": crosses_unit,
                "crosses_supercell_boundary": crosses_supercell,
                "geometry_legal": legal,
                "audit_notes": ";".join(notes) if notes else "ok",
            }
        )
    return rows


def footprints_for_row(row: dict[str, object]) -> list[Footprint]:
    return [
        Footprint(
            "j1",
            float(row["j1_abs_center_x_nm"]),
            float(row["j1_abs_center_y_nm"]),
            float(row["j1_footprint_x_nm"]),
            float(row["j1_footprint_y_nm"]),
        ),
        Footprint(
            "j2",
            float(row["j2_abs_center_x_nm"]),
            float(row["j2_abs_center_y_nm"]),
            float(row["j2_footprint_x_nm"]),
            float(row["j2_footprint_y_nm"]),
        ),
    ]


def min_neighbor_clearance(a: Sequence[Footprint], b: Sequence[Footprint], shift_a_nm: float = 0.0, shift_b_nm: float = 0.0) -> float:
    shifted_a = [Footprint(fp.label, fp.center_x_nm + shift_a_nm, fp.center_y_nm, fp.width_x_nm, fp.width_y_nm) for fp in a]
    shifted_b = [Footprint(fp.label, fp.center_x_nm + shift_b_nm, fp.center_y_nm, fp.width_x_nm, fp.width_y_nm) for fp in b]
    return min(footprint_clearance(left, right) for left in shifted_a for right in shifted_b)


def footprint_clearance(a: Footprint, b: Footprint) -> float:
    gap_x = abs(a.center_x_nm - b.center_x_nm) - (a.width_x_nm + b.width_x_nm) / 2.0
    gap_y = abs(a.center_y_nm - b.center_y_nm) - (a.width_y_nm + b.width_y_nm) / 2.0
    if gap_x >= 0 and gap_y >= 0:
        return math.hypot(gap_x, gap_y)
    if gap_x >= 0:
        return gap_x
    if gap_y >= 0:
        return gap_y
    return max(gap_x, gap_y)


def j1_footprint(row: dict[str, str]) -> tuple[float, float]:
    family = row.get("j1_shape_family", "")
    params = json.loads(row.get("j1_geometry_params") or "{}")
    if family == "circle":
        diameter = flt(params.get("diameter_nm"))
        return diameter, diameter
    if family == "square":
        side = flt(params.get("side_nm"))
        return side, side
    return flt(params.get("length_nm")), flt(params.get("width_nm"))


def build_summary_md(
    handoff_csv: Path,
    layout_rows: Sequence[dict[str, object]],
    geometry_rows: Sequence[dict[str, object]],
    phase_rows: Sequence[dict[str, object]],
    lambda_nm: float,
    supercell_period_nm: float,
) -> str:
    min_internal = min(float(row["internal_clearance_nm"]) for row in geometry_rows)
    min_neighbor = min(float(row["min_neighbor_clearance_nm"]) for row in geometry_rows)
    min_clearance = min(min_internal, min_neighbor)
    legal = all(str(row["geometry_legal"]).lower() == "true" for row in geometry_rows)
    risk = min(phase_rows, key=lambda row: float(row["Tx"]))
    theta = expected_theta_deg(1, lambda_nm, supercell_period_nm)
    can_proceed = legal and int(risk["phase_bin_deg"]) == 240
    lines = [
        "# Stage12-1 H500 LP-APCD K=6 Forward Layout Summary",
        "",
        "## Boundary",
        "",
        "- No FDTD was run.",
        "- No `.fsp` file was generated.",
        "- No LP steering completion is claimed.",
        "- This is forward-order layout preparation and geometry audit only.",
        "",
        "## Input",
        "",
        f"- Frozen handoff library: `{handoff_csv.as_posix()}`",
        "- Forward order: `[0, 60, 120, 180, 240, 300]`.",
        "",
        "## Geometry",
        "",
        f"- K dimers: `{K}`.",
        f"- Per-dimer pitch: `{DEFAULT_DIMER_PITCH_X_NM:.6f}` nm.",
        f"- Supercell period Lambda: `{supercell_period_nm:.6f}` nm.",
        f"- Geometry legal: `{legal}`.",
        f"- Minimum internal clearance: `{min_internal:.6f}` nm.",
        f"- Minimum neighboring-dimer clearance: `{min_neighbor:.6f}` nm.",
        f"- Minimum clearance overall: `{min_clearance:.6f}` nm.",
        "- No dimer crosses its assigned unit cell or supercell boundary in this audit." if legal else "- One or more boundary/clearance checks failed; inspect geometry audit CSV.",
        "",
        "## Phase And Amplitude",
        "",
        "| index | bin | actual_common_phase_deg | phase_err_deg | Tx | ratio | matrix_error |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in phase_rows:
        lines.append(
            f"| {row['supercell_index']} | {row['phase_bin_deg']} | {float(row['actual_common_phase_deg']):.6f} | "
            f"{float(row['phase_err_deg']):.6f} | {float(row['Tx']):.6f} | "
            f"{float(row['conversion_to_leakage_ratio']):.6f} | {float(row['matrix_error']):.6f} |"
        )
    lines.extend(
        [
            "",
            "## Steering Relation",
            "",
            f"- `sin(theta_m) = m * lambda / Lambda = m * {lambda_nm:.6f} / {supercell_period_nm:.6f}`.",
            f"- Expected +1 angle: `{theta:.6f}` deg.",
            "",
            "## Risk And Next Step",
            "",
            f"- Key risk bin: `{risk['phase_bin_deg']}` deg, Tx `{float(risk['Tx']):.6f}`, ratio `{float(risk['conversion_to_leakage_ratio']):.6f}`, matrix_error `{float(risk['matrix_error']):.6f}`.",
            f"- Stage12-2 can proceed to one minimal K=6 full-FDTD validation: `{can_proceed}`.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_stage12_2_run_plan_md(lambda_nm: float, supercell_period_nm: float, geometry_rows: Sequence[dict[str, object]], phase_rows: Sequence[dict[str, object]]) -> str:
    legal = all(str(row["geometry_legal"]).lower() == "true" for row in geometry_rows)
    theta = expected_theta_deg(1, lambda_nm, supercell_period_nm)
    return "\n".join(
        [
            "# Stage12-2 Minimal K=6 Full-FDTD Validation Plan",
            "",
            "## Boundary",
            "",
            "This is a run plan only. Stage12-1 did not run FDTD and did not create `.fsp` outputs.",
            "",
            "## Proposed Minimal Validation",
            "",
            "- Use only the H500 forward K=6 layout from Stage12-1.",
            "- Run one full K=6 supercell FDTD validation only after explicit approval.",
            "- Extract order-resolved diffraction/Jones evidence for the +1 order before claiming LP steering.",
            "- Do not run H600/H700.",
            "- Do not run reverse order unless Stage12-2 explicitly requests it.",
            "",
            "## Preconditions",
            "",
            f"- Geometry legal from Stage12-1: `{legal}`.",
            f"- Expected +1 angle from analytic grating relation: `{theta:.6f}` deg.",
            "- Key risk bin remains 240 deg due to weakest Tx and largest matrix_error.",
            "",
            "## Required Evidence Before Any Steering Claim",
            "",
            "- FDTD success status.",
            "- Result CSV and summary Markdown.",
            "- Diffraction-order resolved +1 field/Jones extraction.",
            "- Basis conversion status for the selected LP-APCD channel.",
        ]
    ) + "\n"


def expected_theta_deg(order: int, lambda_nm: float, supercell_period_nm: float) -> float:
    return math.degrees(math.asin(order * lambda_nm / supercell_period_nm))


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv_rows(rows: Iterable[dict[str, object]], path: Path, fields: Sequence[str]) -> None:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row_list)
