from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from metasurface.stage13_lp_dipole import CANDIDATE_ID, flt, read_csv_rows


PATCH_FIELDS = [
    "patch_option_id",
    "candidate_id",
    "replication_rule",
    "N_supercells_x",
    "N_supercells_y",
    "expected_patch_width_nm",
    "expected_patch_height_nm",
    "has_true_center_dimer",
    "source_center_x_nm",
    "source_center_y_nm",
    "edge_symmetry_error_x_nm",
    "edge_symmetry_error_y_nm",
    "phase_ramp_preserved",
    "center_alignment_note",
    "manufacturability_note",
    "max_coordinate_perturbation_nm",
    "min_gap_after_rounding_nm",
    "estimated_geometry_count",
    "recommended_for_first_FDTD",
    "blocking_issues",
    "warnings",
]

Q_FIELDS = [
    "q_candidate_id",
    "q_definition",
    "q_nm",
    "evidence_source",
    "pros",
    "cons",
    "safe_to_use_for_stage13_minimal_xline",
    "recommended",
    "warnings",
]

Z_FIELDS = [
    "z_candidate_id",
    "z_definition",
    "source_z_nm",
    "evidence_source",
    "safe_to_use",
    "warnings",
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


def _j1_dimensions(row: dict[str, str]) -> tuple[float, float, float]:
    params = json.loads(row.get("j1_geometry_params") or "{}")
    family = row.get("j1_shape_family", "")
    if family == "circle":
        diameter = flt(params.get("diameter_nm"))
        return diameter, diameter, flt(params.get("rotation_deg"), 0.0)
    if family == "square":
        side = flt(params.get("side_nm"))
        return side, side, flt(params.get("rotation_deg"), 0.0)
    return flt(params.get("length_nm")), flt(params.get("width_nm")), flt(params.get("rotation_deg"), 0.0)


def parse_frozen_supercell(layout_csv: Path, geometry_csv: Path, source_paths: Sequence[Path], repo_root: Path) -> dict[str, object]:
    rows = read_csv_rows(layout_csv)
    geometry_rows = read_csv_rows(geometry_csv)
    if len(rows) != 6:
        raise ValueError(f"expected frozen K=6 layout with six dimers; got {len(rows)}")
    period_x_values = {round(flt(row.get("supercell_period_lambda_nm")), 9) for row in rows}
    period_y_values = {round(flt(row.get("p_y_nm")), 9) for row in rows}
    pitch_x_values = {round(flt(row.get("dimer_pitch_x_nm")), 9) for row in rows}
    if len(period_x_values) != 1 or len(period_y_values) != 1 or len(pitch_x_values) != 1:
        raise ValueError("Stage12 layout does not define one consistent x period, y pitch, and phase-bin pitch")
    period_x = next(iter(period_x_values))
    period_y = next(iter(period_y_values))
    pitch_x = next(iter(pitch_x_values))
    derived_pitch = period_x / 6.0
    if abs(derived_pitch - pitch_x) > 1e-6:
        raise ValueError(f"unsafe phase-bin pitch: period/6={derived_pitch}, stored pitch={pitch_x}")
    shift_x = period_x / 2.0
    dimers: list[dict[str, object]] = []
    pillars: list[dict[str, object]] = []
    for row in rows:
        index = int(flt(row.get("supercell_index")))
        dimer_x = flt(row.get("supercell_center_x_nm")) - shift_x
        dimer_y = flt(row.get("supercell_center_y_nm"))
        j1_w, j1_h, j1_rot = _j1_dimensions(row)
        dimer = {
            "supercell_index": index,
            "phase_bin_deg": int(flt(row.get("phase_bin_deg"))),
            "candidate_id": row.get("candidate_id", ""),
            "dimer_center_x_nm": round(dimer_x, 9),
            "dimer_center_y_nm": round(dimer_y, 9),
            "j1_center_x_nm": round(flt(row.get("j1_abs_center_x_nm")) - shift_x, 9),
            "j1_center_y_nm": round(flt(row.get("j1_abs_center_y_nm")), 9),
            "j2_center_x_nm": round(flt(row.get("j2_abs_center_x_nm")) - shift_x, 9),
            "j2_center_y_nm": round(flt(row.get("j2_abs_center_y_nm")), 9),
        }
        dimers.append(dimer)
        pillars.extend(
            [
                {
                    "dimer_index": index,
                    "pillar": "J1",
                    "x_nm": float(dimer["j1_center_x_nm"]),
                    "y_nm": float(dimer["j1_center_y_nm"]),
                    "width_x_nm": j1_w,
                    "width_y_nm": j1_h,
                    "rotation_deg": j1_rot,
                },
                {
                    "dimer_index": index,
                    "pillar": "J2",
                    "x_nm": float(dimer["j2_center_x_nm"]),
                    "y_nm": float(dimer["j2_center_y_nm"]),
                    "width_x_nm": flt(row.get("j2_length_nm")),
                    "width_y_nm": flt(row.get("j2_width_nm")),
                    "rotation_deg": flt(row.get("j2_rotation_deg"), 0.0),
                },
            ]
        )
    footprint = footprint_bounds(pillars)
    min_gap_values = [
        value
        for row in geometry_rows
        for value in (flt(row.get("internal_clearance_nm")), flt(row.get("min_neighbor_clearance_nm")))
        if not math.isnan(value)
    ]
    relative_sources = [path.relative_to(repo_root).as_posix() if path.is_relative_to(repo_root) else str(path) for path in source_paths]
    return {
        "candidate_id": CANDIDATE_ID,
        "source_files_used": relative_sources,
        "supercell_period_x_nm": period_x,
        "supercell_period_y_nm": period_y,
        "phase_bin_pitch_x_nm": derived_pitch,
        "y_pitch_nm": period_y,
        "six_phase_bin_dimer_centers": dimers,
        "pillars": pillars,
        "raw_footprint": footprint,
        "frozen_min_gap_nm": min(min_gap_values),
    }


def footprint_bounds(pillars: Sequence[dict[str, object]]) -> dict[str, float]:
    return {
        "x_min_nm": round(min(float(p["x_nm"]) - float(p["width_x_nm"]) / 2.0 for p in pillars), 9),
        "x_max_nm": round(max(float(p["x_nm"]) + float(p["width_x_nm"]) / 2.0 for p in pillars), 9),
        "y_min_nm": round(min(float(p["y_nm"]) - float(p["width_y_nm"]) / 2.0 for p in pillars), 9),
        "y_max_nm": round(max(float(p["y_nm"]) + float(p["width_y_nm"]) / 2.0 for p in pillars), 9),
    }


def odd_ceiling(value: float) -> int:
    result = max(1, math.ceil(value))
    return result if result % 2 == 1 else result + 1


def tile_geometry(meta: dict[str, object], nx: int, ny: int, shift_x_nm: float = 0.0, round_centers: bool = False) -> tuple[list[dict[str, object]], list[float]]:
    period_x = float(meta["supercell_period_x_nm"])
    period_y = float(meta["y_pitch_nm"])
    tiled: list[dict[str, object]] = []
    perturbations: list[float] = []
    for ix in range(-(nx // 2), nx // 2 + 1):
        for iy in range(-(ny // 2), ny // 2 + 1):
            for pillar in meta["pillars"]:
                x_raw = float(pillar["x_nm"]) + ix * period_x + shift_x_nm
                y_raw = float(pillar["y_nm"]) + iy * period_y
                x = float(round(x_raw)) if round_centers else x_raw
                y = float(round(y_raw)) if round_centers else y_raw
                perturbations.append(math.hypot(x - x_raw, y - y_raw))
                tiled.append({**pillar, "x_nm": x, "y_nm": y, "tile_x": ix, "tile_y": iy})
    return tiled, perturbations


def footprint_clearance(a: dict[str, object], b: dict[str, object]) -> float:
    gap_x = abs(float(a["x_nm"]) - float(b["x_nm"])) - (float(a["width_x_nm"]) + float(b["width_x_nm"])) / 2.0
    gap_y = abs(float(a["y_nm"]) - float(b["y_nm"])) - (float(a["width_y_nm"]) + float(b["width_y_nm"])) / 2.0
    if gap_x >= 0 and gap_y >= 0:
        return math.hypot(gap_x, gap_y)
    if gap_x >= 0:
        return gap_x
    if gap_y >= 0:
        return gap_y
    return max(gap_x, gap_y)


def minimum_gap(pillars: Sequence[dict[str, object]]) -> float:
    best = math.inf
    for index, left in enumerate(pillars):
        for right in pillars[index + 1 :]:
            best = min(best, footprint_clearance(left, right))
    return best


def _edge_errors(pillars: Sequence[dict[str, object]]) -> tuple[float, float]:
    bounds = footprint_bounds(pillars)
    return (
        round(abs(abs(bounds["x_min_nm"]) - abs(bounds["x_max_nm"])), 9),
        round(abs(abs(bounds["y_min_nm"]) - abs(bounds["y_max_nm"])), 9),
    )


def _option(
    meta: dict[str, object],
    option_id: str,
    nx: int,
    ny: int,
    rule: str,
    shift_x_nm: float,
    round_centers: bool,
    true_center: bool,
    phase_preserved: bool,
    center_note: str,
    fab_note: str,
    recommended: bool,
    blockers: list[str],
    warnings: list[str],
) -> dict[str, object]:
    pillars, perturbations = tile_geometry(meta, nx, ny, shift_x_nm=shift_x_nm, round_centers=round_centers)
    edge_x, edge_y = _edge_errors(pillars)
    rounded_gap = minimum_gap(pillars) if round_centers else None
    return {
        "patch_option_id": option_id,
        "candidate_id": meta["candidate_id"],
        "replication_rule": rule,
        "N_supercells_x": nx,
        "N_supercells_y": ny,
        "expected_patch_width_nm": round(nx * float(meta["supercell_period_x_nm"]), 9),
        "expected_patch_height_nm": round(ny * float(meta["y_pitch_nm"]), 9),
        "has_true_center_dimer": true_center,
        "source_center_x_nm": 0.0,
        "source_center_y_nm": 0.0,
        "edge_symmetry_error_x_nm": edge_x,
        "edge_symmetry_error_y_nm": edge_y,
        "phase_ramp_preserved": phase_preserved,
        "center_alignment_note": center_note,
        "manufacturability_note": fab_note,
        "max_coordinate_perturbation_nm": round(max(perturbations), 9) if round_centers else 0.0,
        "min_gap_after_rounding_nm": None if rounded_gap is None else round(rounded_gap, 9),
        "estimated_geometry_count": f"{nx * ny * 6} dimers; {nx * ny * 12} nanopillars",
        "recommended_for_first_FDTD": recommended,
        "blocking_issues": json.dumps(blockers),
        "warnings": json.dumps(warnings),
    }


def build_patch_options(meta: dict[str, object]) -> list[dict[str, object]]:
    period_x = float(meta["supercell_period_x_nm"])
    y_pitch = float(meta["y_pitch_nm"])
    small_ny = odd_ceiling(3 * period_x / y_pitch)
    medium_ny = odd_ceiling(5 * period_x / y_pitch)
    closest = sorted(meta["six_phase_bin_dimer_centers"], key=lambda item: (abs(float(item["dimer_center_x_nm"])), int(item["supercell_index"])))
    selected = closest[0]
    center_shift = -float(selected["dimer_center_x_nm"])
    common_blockers = ["manual_patch_option_approval_required", "manual_q_candidate_approval_required", "source_z_requires_manual_definition"]
    return [
        _option(
            meta,
            "A_small",
            3,
            small_ny,
            "whole frozen K=6 supercells at symmetric integer tile indices about x=0; odd y rows about y=0",
            0.0,
            False,
            False,
            True,
            "Optical origin remains at the patch coordinate center and lies between the two central dimers.",
            "Frozen sub-nm coordinates are preserved exactly; no fabrication rounding is applied.",
            True,
            common_blockers,
            ["recommended geometry only; FDTD remains blocked until explicit manual approval", "no true center dimer"],
        ),
        _option(
            meta,
            "A_medium",
            5,
            medium_ny,
            "whole frozen K=6 supercells at symmetric integer tile indices about x=0; odd y rows about y=0",
            0.0,
            False,
            False,
            True,
            "Optical origin remains between the two central dimers.",
            "Frozen sub-nm coordinates are preserved exactly.",
            False,
            common_blockers + ["defer_medium_patch_until_A_small_cost_and_boundary_behavior_are_reviewed"],
            ["larger geometry count than the first validation needs"],
        ),
        _option(
            meta,
            "B_dimer_centered_small",
            3,
            small_ny,
            f"A_small whole-supercell replication translated by {center_shift:.9f} nm so dimer index {selected['supercell_index']} is at x=0",
            center_shift,
            False,
            True,
            True,
            f"Dimer index {selected['supercell_index']} (phase {selected['phase_bin_deg']} deg) is centered; the nearest-center choice has a symmetric tie.",
            "Frozen internal geometry is unchanged, but the optical-axis/phase-origin registration shifts.",
            False,
            common_blockers + ["nearest_center_dimer_tie_requires_manual_choice", "shifted_phase_origin_requires_edge_review"],
            ["edge symmetry changes after centering one dimer", "phase-bin origin relative to source is changed"],
        ),
        _option(
            meta,
            "C_integer_fabrication_small",
            3,
            small_ny,
            "A_small replication followed by nearest-integer-nm rounding of every J1/J2 center",
            0.0,
            True,
            False,
            False,
            "Optical origin remains fixed; no center dimer is forced.",
            "Integer centers are generated as an audit candidate only; dimensions/rotations remain frozen and integer-valued.",
            False,
            common_blockers + ["integer_rounding_tolerance_validation_required"],
            ["do not call fabrication-ready without optical/tolerance validation"],
        ),
    ]


def build_q_decisions(meta: dict[str, object], layout_source: str) -> list[dict[str, object]]:
    pitch = float(meta["phase_bin_pitch_x_nm"])
    centers = sorted(float(item["dimer_center_x_nm"]) for item in meta["six_phase_bin_dimer_centers"])
    spacings = [right - left for left, right in zip(centers, centers[1:])]
    nearest = min(spacings)
    local_pairs = []
    for dimer in meta["six_phase_bin_dimer_centers"]:
        dx = float(dimer["j2_center_x_nm"]) - float(dimer["j1_center_x_nm"])
        dy = float(dimer["j2_center_y_nm"]) - float(dimer["j1_center_y_nm"])
        local_pairs.append((math.hypot(dx, dy), dx, dy, int(dimer["supercell_index"])))
    local_distance, local_dx, local_dy, local_index = min(local_pairs)
    warning = "Numerically equal to the historical CP q only because the independently parsed LP pitch is the same; no CP value was reused."
    return [
        {
            "q_candidate_id": "q_candidate_1",
            "q_definition": "phase_bin_pitch_x_nm / 4",
            "q_nm": round(pitch / 4.0, 9),
            "evidence_source": f"{layout_source}; Lambda_x/6={pitch:.9f} nm",
            "pros": "directly tied to the frozen LP phase-bin lattice; symmetric +/-x placement",
            "cons": "quarter-pitch is a sampling choice, not an optimized emitter position",
            "safe_to_use_for_stage13_minimal_xline": True,
            "recommended": True,
            "warnings": warning,
        },
        {
            "q_candidate_id": "q_candidate_2",
            "q_definition": "nearest center-to-neighbor dimer distance / 4",
            "q_nm": round(nearest / 4.0, 9),
            "evidence_source": f"parsed six LP dimer centers; nearest spacing={nearest:.9f} nm",
            "pros": "independent center-list cross-check of q_candidate_1",
            "cons": "redundant for this uniformly spaced frozen supercell",
            "safe_to_use_for_stage13_minimal_xline": True,
            "recommended": False,
            "warnings": warning,
        },
        {
            "q_candidate_id": "q_candidate_3",
            "q_definition": "nearest local J1/J2 spacing based x-line offset",
            "q_nm": None,
            "evidence_source": f"nearest local pair is dimer {local_index}: distance={local_distance:.9f} nm, dx={local_dx:.9f} nm, dy={local_dy:.9f} nm",
            "pros": "would register the source to local pillar geometry if a physically justified rule existed",
            "cons": "nearest pair is not a validated x-line source-position rule; converting it to q would be arbitrary",
            "safe_to_use_for_stage13_minimal_xline": False,
            "recommended": False,
            "warnings": "Rejected rather than guessed.",
        },
    ]


def build_source_z_decisions() -> list[dict[str, object]]:
    cp_evidence = "scripts/blue_stage10_cp_zprop_validation/run_cp_zprop_center_xy_t100.py uses GaN top z=0 and source z=-200 nm in the CP branch"
    return [
        {
            "z_candidate_id": "z_candidate_1",
            "z_definition": "MQW plane from an LP MicroLED vertical stack",
            "source_z_nm": None,
            "evidence_source": "No MQW/active-layer z metadata found in frozen Stage12 or Stage13 LP inputs.",
            "safe_to_use": False,
            "warnings": "Requires an explicit LP MicroLED stack and MQW-plane definition.",
        },
        {
            "z_candidate_id": "z_candidate_2",
            "z_definition": "metasurface_bottom_z_nm (0) minus a user-approved source offset",
            "source_z_nm": None,
            "evidence_source": "Stage12 pillars use z_min=0; no LP dipole offset is frozen.",
            "safe_to_use": False,
            "warnings": f"Do not silently import -200 nm; {cp_evidence}.",
        },
        {
            "z_candidate_id": "z_candidate_3",
            "z_definition": "later sweep placeholder: metasurface_bottom_z_nm minus an approved list of offsets",
            "source_z_nm": None,
            "evidence_source": "No approved LP source-z sweep list exists.",
            "safe_to_use": False,
            "warnings": "Define the vertical stack, allowed source region, and offset list before simulation.",
        },
    ]


def build_cases(patch_options: Sequence[dict[str, object]], q_rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    patch = next(row for row in patch_options if row["recommended_for_first_FDTD"] is True)
    q = next(row for row in q_rows if row["recommended"] is True and row["safe_to_use_for_stage13_minimal_xline"] is True)
    q_nm = float(q["q_nm"])
    blockers = json.dumps(["manual_patch_option_approval_required", "manual_q_candidate_approval_required", "source_z_requires_manual_definition"])
    positions = [("center", 0.0), ("x_plus_qp", q_nm), ("x_minus_qp", -q_nm)]
    cases: list[dict[str, object]] = []
    for position, x_nm in positions:
        for orientation in ("x", "y"):
            case_id = f"{position}_{orientation}"
            cases.append(
                {
                    "case_id": case_id,
                    "candidate_id": CANDIDATE_ID,
                    "patch_option_id": patch["patch_option_id"],
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
                    "source_x_nm": round(x_nm, 9),
                    "source_y_nm": 0.0,
                    "source_z_nm": "",
                    "simulation_time_fs": 100,
                    "q_nm": round(q_nm, 9),
                    "q_definition": q["q_definition"],
                    "result_csv": f"outputs/stage13_3_lp_dipole_results/{case_id}.csv",
                    "status": "prepared_not_run",
                    "blocking_issues": blockers,
                }
            )
    return cases


def build_config(meta: dict[str, object], patches: Sequence[dict[str, object]], q_rows: Sequence[dict[str, object]], z_rows: Sequence[dict[str, object]], cases: Sequence[dict[str, object]]) -> dict[str, object]:
    recommended_patch = next(row for row in patches if row["recommended_for_first_FDTD"] is True)
    recommended_q = next(row for row in q_rows if row["recommended"] is True)
    return {
        "stage": "Stage13-2",
        "scope": "finite-patch definition and q/source-z decision package only",
        "run_fdtd": False,
        "create_or_modify_fsp": False,
        "frozen_stage12_supercell_modified": False,
        "coordinate_convention": {
            "metasurface_plane": "x-y",
            "height_axis": "z",
            "source_location": "below metasurface",
            "target_emission": "+z",
            "farfield_monitor_direction": "+z",
            "gradient_axis": "x",
            "target_LP": "x",
            "K_definition": "six dimers per supercell, not six nanopillars",
        },
        "frozen_supercell": {key: value for key, value in meta.items() if key != "pillars"},
        "J1_J2_centers_per_dimer": meta["six_phase_bin_dimer_centers"],
        "patch_options": list(patches),
        "recommended_patch_option_id": recommended_patch["patch_option_id"],
        "recommended_patch_status": "geometry_recommendation_pending_manual_approval",
        "q_decisions": list(q_rows),
        "recommended_q_candidate_id": recommended_q["q_candidate_id"],
        "recommended_q_nm": recommended_q["q_nm"],
        "q_status": "safely_inferred_pending_manual_approval",
        "source_z_decisions": list(z_rows),
        "source_z_nm": None,
        "source_z_status": "requires_manual_definition",
        "case_ids": [row["case_id"] for row in cases],
        "manual_approval_required_before_fdtd": True,
        "fdtd_blocking_items": [
            "approve one finite-patch option",
            "approve q_candidate_1 or supply another LP-specific q",
            "define and approve LP source_z_nm from a vertical stack",
        ],
    }


def build_report(meta: dict[str, object], patches: Sequence[dict[str, object]], q_rows: Sequence[dict[str, object]], z_rows: Sequence[dict[str, object]]) -> str:
    recommended_patch = next(row for row in patches if row["recommended_for_first_FDTD"] is True)
    integer_patch = next(row for row in patches if row["patch_option_id"] == "C_integer_fabrication_small")
    recommended_q = next(row for row in q_rows if row["recommended"] is True)
    fp = meta["raw_footprint"]
    lines = [
        "# Stage13-2 LP Finite-Patch Definition And q/source-z Decision Report",
        "",
        "## Scope boundary",
        "",
        "- Decision/configuration package only; no FDTD was run.",
        "- No `.fsp` file was created, opened, or modified.",
        "- The frozen Stage12 H500 LP-APCD K=6 periodic supercell is read-only.",
        "- Coordinate convention is x-y metasurface, z height, source below, +z emission/monitor, x gradient, x-LP target.",
        "- K=6 means six dimers (12 nanopillars) per supercell.",
        "",
        "## Discovered frozen-supercell evidence",
        "",
        f"- Candidate: `{meta['candidate_id']}`.",
        f"- Source files: `{json.dumps(meta['source_files_used'])}`.",
        f"- Supercell period x: `{meta['supercell_period_x_nm']}` nm.",
        f"- Supercell/y pitch: `{meta['supercell_period_y_nm']}` nm.",
        f"- Phase-bin pitch x = Lambda_x/6: `{meta['phase_bin_pitch_x_nm']}` nm.",
        f"- Raw footprint x: `{fp['x_min_nm']}` to `{fp['x_max_nm']}` nm.",
        f"- Raw footprint y: `{fp['y_min_nm']}` to `{fp['y_max_nm']}` nm.",
        "- Six dimer centers and all J1/J2 centers were parsed into the JSON candidate package.",
        "",
        "## Patch decision",
        "",
        f"- Recommended geometry for the first later FDTD: `{recommended_patch['patch_option_id']}`.",
        f"- Size: `{recommended_patch['N_supercells_x']} x {recommended_patch['N_supercells_y']}` whole-supercell/y-row tiles.",
        f"- Estimated geometry: `{recommended_patch['estimated_geometry_count']}`.",
        "- Reason: it preserves the frozen phase ramp and optical origin without forcing a center dimer or rounding coordinates.",
        "- This is a recommendation pending manual approval, not authorization to run FDTD.",
        "",
        "### Candidate summary",
        "",
        "| option | Nx | Ny | true center dimer | phase ramp preserved | x edge error (nm) | y edge error (nm) | first-FDTD recommendation |",
        "| --- | ---: | ---: | --- | --- | ---: | ---: | --- |",
    ]
    for row in patches:
        lines.append(
            f"| {row['patch_option_id']} | {row['N_supercells_x']} | {row['N_supercells_y']} | {row['has_true_center_dimer']} | "
            f"{row['phase_ramp_preserved']} | {row['edge_symmetry_error_x_nm']} | {row['edge_symmetry_error_y_nm']} | {row['recommended_for_first_FDTD']} |"
        )
    lines.extend(
        [
            "",
            f"- Option C maximum 2D center perturbation after integer rounding: `{integer_patch['max_coordinate_perturbation_nm']}` nm.",
            f"- Option C conservative minimum gap after rounding: `{integer_patch['min_gap_after_rounding_nm']}` nm versus the frozen `20.0 nm` minimum.",
            "- Therefore Option C is not gap-safe by the existing 20 nm rule and requires redesign/tolerance validation.",
        ]
    )
    lines.extend(
        [
            "",
            "## q decision",
            "",
            f"- Recommended candidate: `{recommended_q['q_candidate_id']}`.",
            f"- q = `{recommended_q['q_nm']}` nm, independently derived from the frozen LP phase-bin pitch.",
            "- q was safely inferred for case preparation, but still requires explicit manual approval before FDTD.",
            "- The numerical match to the historical CP q is incidental; no CP q value was reused.",
            "",
            "| q candidate | q (nm) | safe for minimal x-line | recommended |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in q_rows:
        lines.append(f"| {row['q_candidate_id']} | {row['q_nm']} | {row['safe_to_use_for_stage13_minimal_xline']} | {row['recommended']} |")
    lines.extend(
        [
            "",
            "## source-z decision",
            "",
            "- No LP MQW plane or approved vertical-stack source position was found.",
            "- `source_z_nm` remains `null`; status is `requires_manual_definition`.",
            "- CP-branch `-200 nm` evidence is not transferable to this LP patch and was not selected.",
            "",
            "| z candidate | source z (nm) | safe |",
            "| --- | ---: | --- |",
        ]
    )
    for row in z_rows:
        lines.append(f"| {row['z_candidate_id']} | {row['source_z_nm']} | {row['safe_to_use']} |")
    lines.extend(
        [
            "",
            "## FDTD blocking items",
            "",
            "1. Manually approve one finite-patch option (recommended: A_small).",
            "2. Manually approve q_candidate_1 or supply another LP-specific q.",
            "3. Define and approve LP source_z_nm from a vertical stack/MQW decision.",
            "",
            "Until all three are resolved, every case remains `prepared_not_run` and `run_fdtd=false`.",
            "",
        ]
    )
    return "\n".join(lines)


def build_readme() -> str:
    return """# Stage13-2 LP Finite-Patch Decision Package

This directory contains lightweight definitions and manual-decision metadata only. No FDTD was run, and the frozen Stage12 K=6 periodic supercell was not modified.

## Recommendation

- Geometry: `A_small`, a 3-supercell x replication with odd symmetric y rows.
- q: `q_candidate_1 = phase_bin_pitch_x_nm / 4`, derived from the LP layout and pending manual approval.
- source z: unresolved; no LP MQW/vertical-stack position is frozen.

## Boundaries

- `run_fdtd=false`.
- No `.fsp` files belong in this package.
- x/y dipole orientations remain separate; unpolarized power is the incoherent sum.
- Later LP extraction must use complex vector far-field components, not intensity-only `farfield3d`.
- Manual approval of patch, q, and source z is required before any simulation task.
"""
