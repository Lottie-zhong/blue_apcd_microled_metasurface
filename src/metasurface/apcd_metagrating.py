from __future__ import annotations

import csv
import math
from pathlib import Path
from types import ModuleType
from typing import Iterable

from metasurface.config import APCDDimerMaterialConfig, APCDSingleDimerConfig, RuntimeConfig, load_runtime_config
from metasurface.lumapi_runner import import_lumapi


APCD_METAGRATING_GEOMETRY_FIELDS = [
    "K",
    "dimer_index",
    "pillar_index_in_dimer",
    "global_pillar_index",
    "x_nm",
    "y_nm",
    "length_nm",
    "width_nm",
    "height_nm",
    "rotation_deg",
    "frac_x",
    "frac_y",
    "dimer_pitch_nm",
    "supercell_period_nm",
    "wavelength_nm",
    "target_angle_deg",
]


APCD_PHASE_GRADIENT_FIELDS = [
    "K",
    "dimer_index",
    "x_nm",
    "dimer_pitch_nm",
    "supercell_period_nm",
    "target_angle_deg",
    "uniform_phase_rad",
    "plus_ramp_phase_rad",
    "plus_ramp_phase_deg",
    "minus_ramp_phase_rad",
    "minus_ramp_phase_deg",
    "plus_ramp_complex_real",
    "plus_ramp_complex_imag",
    "minus_ramp_complex_real",
    "minus_ramp_complex_imag",
]


def read_apcd_metagrating_geometry_csv(path: Path) -> list[dict[str, float | int]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                {
                    "K": int(row["K"]),
                    "dimer_index": int(row["dimer_index"]),
                    "pillar_index_in_dimer": int(row["pillar_index_in_dimer"]),
                    "global_pillar_index": int(row["global_pillar_index"]),
                    "x_nm": float(row["x_nm"]),
                    "y_nm": float(row["y_nm"]),
                    "length_nm": float(row["length_nm"]),
                    "width_nm": float(row["width_nm"]),
                    "height_nm": float(row["height_nm"]),
                    "rotation_deg": float(row["rotation_deg"]),
                    "frac_x": float(row["frac_x"]),
                    "frac_y": float(row["frac_y"]),
                    "dimer_pitch_nm": float(row["dimer_pitch_nm"]),
                    "supercell_period_nm": float(row["supercell_period_nm"]),
                    "wavelength_nm": float(row["wavelength_nm"]),
                    "target_angle_deg": float(row["target_angle_deg"]),
                }
            )
    return rows


def build_phase_gradient_requirements(
    geometry_rows: list[dict[str, float | int]],
) -> list[dict[str, float | int]]:
    if not geometry_rows:
        raise ValueError("Cannot build phase-gradient requirements without geometry rows")

    K = int(geometry_rows[0]["K"])
    validate_apcd_metagrating_geometry_rows(geometry_rows, K)
    dimer_rows = _dimer_center_rows(geometry_rows, K)
    phase_step_rad = 2 * math.pi / K

    rows: list[dict[str, float | int]] = []
    for dimer in dimer_rows:
        dimer_index = int(dimer["dimer_index"])
        plus_phase = _wrap_phase_rad(phase_step_rad * dimer_index)
        minus_phase = _wrap_phase_rad(-phase_step_rad * dimer_index)
        rows.append(
            {
                "K": K,
                "dimer_index": dimer_index,
                "x_nm": float(dimer["x_nm"]),
                "dimer_pitch_nm": float(dimer["dimer_pitch_nm"]),
                "supercell_period_nm": float(dimer["supercell_period_nm"]),
                "target_angle_deg": float(dimer["target_angle_deg"]),
                "uniform_phase_rad": 0.0,
                "plus_ramp_phase_rad": plus_phase,
                "plus_ramp_phase_deg": math.degrees(plus_phase),
                "minus_ramp_phase_rad": minus_phase,
                "minus_ramp_phase_deg": math.degrees(minus_phase),
                "plus_ramp_complex_real": math.cos(plus_phase),
                "plus_ramp_complex_imag": math.sin(plus_phase),
                "minus_ramp_complex_real": math.cos(minus_phase),
                "minus_ramp_complex_imag": math.sin(minus_phase),
            }
        )
    return rows


def normalized_structure_factor(phases_rad: Iterable[float], order_m: int) -> complex:
    phases = list(phases_rad)
    if not phases:
        raise ValueError("phases_rad must not be empty")
    K = len(phases)
    total = 0j
    for index, phase in enumerate(phases):
        target_channel_amplitude = complex(math.cos(phase), math.sin(phase))
        grating_phase = complex(
            math.cos(-2 * math.pi * order_m * index / K),
            math.sin(-2 * math.pi * order_m * index / K),
        )
        total += target_channel_amplitude * grating_phase
    return total / K


def write_phase_gradient_requirements_csv(rows: Iterable[dict[str, object]], path: Path) -> Path:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_PHASE_GRADIENT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_phase_gradient_sanity_check(
    rows: list[dict[str, float | int]],
    path: Path,
) -> Path:
    if not rows:
        raise ValueError("Cannot write phase-gradient sanity check without rows")

    K = int(rows[0]["K"])
    phase_step_deg = 360.0 / K
    uniform_phases = [float(row["uniform_phase_rad"]) for row in rows]
    plus_phases = [float(row["plus_ramp_phase_rad"]) for row in rows]
    minus_phases = [float(row["minus_ramp_phase_rad"]) for row in rows]
    uniform_plus = abs(normalized_structure_factor(uniform_phases, order_m=1))
    uniform_minus = abs(normalized_structure_factor(uniform_phases, order_m=-1))
    plus_to_plus = abs(normalized_structure_factor(plus_phases, order_m=1))
    plus_to_minus = abs(normalized_structure_factor(plus_phases, order_m=-1))
    minus_to_plus = abs(normalized_structure_factor(minus_phases, order_m=1))
    minus_to_minus = abs(normalized_structure_factor(minus_phases, order_m=-1))

    phase_lines = [
        (
            f"| {int(row['dimer_index'])} | {float(row['x_nm'])} | "
            f"{float(row['plus_ramp_phase_deg'])} | {float(row['minus_ramp_phase_deg'])} |"
        )
        for row in rows
    ]

    lines = [
        f"# APCD K={K} Dimer Phase-Gradient Sanity Check",
        "",
        "## Current State",
        "",
        "- Current K-dimer setup is a geometry scaffold.",
        "- Each dimer is already represented as a structure group.",
        "- Current geometry does not imply a t_{alpha*<-alpha} phase-gradient.",
        "- No FDTD, RCWA, far-field, or diffraction-order result is reported here.",
        "",
        "## APCD Target Channel",
        "",
        "The metagrating target channel is `t_{alpha*<-alpha}`, not ordinary x/y, L/R, or total transmission alone.",
        "",
        "A useful dimer state must simultaneously provide:",
        "",
        "- high `|t_{alpha*<-alpha}|`",
        "- low beta leakage",
        "- prescribed target-channel phase `phi_i`",
        "",
        "## Structure-Factor Sanity Check",
        "",
        "Using the approximate discrete structure factor",
        "",
        "```text",
        "A_m = sum_i a_i * exp(-i 2*pi*m*i/K)",
        "```",
        "",
        "uniform identical dimers have `a_i = 1`. For `m = +1` and `m = -1`, the normalized structure factor should be near zero when K > 1. Therefore, the current uniform scaffold alone should not be claimed as a +15 deg directional metagrating.",
        "",
        f"- uniform_A_plus1_normalized_abs: {uniform_plus}",
        f"- uniform_A_minus1_normalized_abs: {uniform_minus}",
        f"- plus_ramp_A_plus1_normalized_abs: {plus_to_plus}",
        f"- plus_ramp_A_minus1_normalized_abs: {plus_to_minus}",
        f"- minus_ramp_A_plus1_normalized_abs: {minus_to_plus}",
        f"- minus_ramp_A_minus1_normalized_abs: {minus_to_minus}",
        "",
        "## Required Phase Ramp",
        "",
        f"- K: {K}",
        f"- phase_step_deg: {phase_step_deg}",
        "",
        "| dimer_index | x_nm | plus_ramp_phase_deg | minus_ramp_phase_deg |",
        "|---:|---:|---:|---:|",
        *phase_lines,
        "",
        "## Sign Convention Caveat",
        "",
        "Both plus-ramp and minus-ramp targets are listed because the sign corresponding to the GUI/FDTD +15 deg order must be verified by later diffraction-order extraction. This report does not assert which ramp sign is final.",
        "",
        "## Recommended Route",
        "",
        "Step B: build diffraction-order / far-field extraction and verify the order sign convention.",
        "",
        "Step C: build a dimer phase-state design mechanism, for example dynamic phase through small geometry variants, detour phase / local displacement, or possibly constrained dimer rotation only if the alpha/beta target remains valid.",
        "",
        "Global rotation may change the APCD allowed state alpha and should not be used casually as a phase knob.",
        "",
        "Step D: find K dimer variants that simultaneously satisfy alpha-pass, beta-suppressed, and the target-channel phase ramp.",
        "",
        "## Explicit Non-Goals",
        "",
        "- Do not treat the current uniform scaffold as the final metagrating.",
        "- Do not claim +15 deg steering is already achieved.",
        "- Do not start a large sweep from this report.",
        "- Do not switch to TiO2 or 450 nm.",
        "- Do not do ML.",
        "- Do not treat K as the number of individual nanopillars.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_phase_gradient_outputs(
    geometry_csv: Path,
    requirements_csv: Path,
    sanity_check_md: Path,
) -> tuple[Path, Path, list[dict[str, float | int]]]:
    geometry_rows = read_apcd_metagrating_geometry_csv(geometry_csv)
    rows = build_phase_gradient_requirements(geometry_rows)
    csv_path = write_phase_gradient_requirements_csv(rows, requirements_csv)
    md_path = write_phase_gradient_sanity_check(rows, sanity_check_md)
    return csv_path, md_path, rows


def _wrap_phase_rad(phase_rad: float) -> float:
    return phase_rad % (2 * math.pi)


def _dimer_center_rows(
    geometry_rows: list[dict[str, float | int]],
    K: int,
) -> list[dict[str, float | int]]:
    dimer_rows: list[dict[str, float | int]] = []
    for dimer_index in range(K):
        rows = [row for row in geometry_rows if int(row["dimer_index"]) == dimer_index]
        if len(rows) != 2:
            raise ValueError(f"dimer_index={dimer_index} must contain exactly 2 nanopillars")
        first = rows[0]
        dimer_rows.append(
            {
                "dimer_index": dimer_index,
                "x_nm": sum(float(row["x_nm"]) for row in rows) / len(rows),
                "dimer_pitch_nm": float(first["dimer_pitch_nm"]),
                "supercell_period_nm": float(first["supercell_period_nm"]),
                "target_angle_deg": float(first["target_angle_deg"]),
            }
        )
    return dimer_rows


def calculate_supercell_period_nm(wavelength_nm: float, target_angle_deg: float) -> float:
    sin_theta = math.sin(math.radians(target_angle_deg))
    if sin_theta <= 0:
        raise ValueError("target_angle_deg must give a positive first-order grating period")
    return wavelength_nm / sin_theta


def build_apcd_k_dimer_metagrating_geometry(
    config: APCDSingleDimerConfig,
    K: int,
    target_angle_deg: float = 15.0,
) -> list[dict[str, float | int]]:
    if K <= 0:
        raise ValueError("K must be positive")

    geometry = config.geometry
    wavelength_nm = float(config.target.wavelength_nm)
    supercell_period_nm = calculate_supercell_period_nm(wavelength_nm, target_angle_deg)
    dimer_pitch_nm = supercell_period_nm / K
    local_period_y_nm = float(geometry.period_y_nm)

    pillars = [geometry.nanopillar_1, geometry.nanopillar_2]
    rows: list[dict[str, float | int]] = []

    global_pillar_index = 0
    for dimer_index in range(K):
        dimer_cell_x_start_nm = -0.5 * supercell_period_nm + dimer_index * dimer_pitch_nm
        dimer_center_x_nm = dimer_cell_x_start_nm + 0.5 * dimer_pitch_nm

        for pillar_index_in_dimer, pillar in enumerate(pillars, start=1):
            if pillar.frac_x is None or pillar.frac_y is None:
                raise ValueError("APCD metagrating requires fractional pillar coordinates")

            x_local_nm = (pillar.frac_x - 0.5) * dimer_pitch_nm
            y_local_nm = (pillar.frac_y - 0.5) * local_period_y_nm
            rows.append(
                {
                    "K": K,
                    "dimer_index": dimer_index,
                    "pillar_index_in_dimer": pillar_index_in_dimer,
                    "global_pillar_index": global_pillar_index,
                    "x_nm": dimer_center_x_nm + x_local_nm,
                    "y_nm": y_local_nm,
                    "length_nm": float(pillar.length_nm),
                    "width_nm": float(pillar.width_nm),
                    "height_nm": float(geometry.height_nm),
                    "rotation_deg": float(pillar.rotation_deg),
                    "frac_x": float(pillar.frac_x),
                    "frac_y": float(pillar.frac_y),
                    "dimer_pitch_nm": dimer_pitch_nm,
                    "supercell_period_nm": supercell_period_nm,
                    "wavelength_nm": wavelength_nm,
                    "target_angle_deg": float(target_angle_deg),
                }
            )
            global_pillar_index += 1

    return rows


def validate_alpha_pass_dimer_source(config: APCDSingleDimerConfig) -> None:
    geometry = config.geometry
    p1 = geometry.nanopillar_1
    p2 = geometry.nanopillar_2

    expected = [
        (p1.length_nm, 130.0, "nanopillar_1.length_nm"),
        (p1.width_nm, 70.0, "nanopillar_1.width_nm"),
        (p1.frac_x, 0.75, "nanopillar_1.frac_x"),
        (p1.frac_y, 0.75, "nanopillar_1.frac_y"),
        (p1.rotation_deg, 67.5, "nanopillar_1.rotation_deg"),
        (p2.length_nm, 85.0, "nanopillar_2.length_nm"),
        (p2.width_nm, 150.0, "nanopillar_2.width_nm"),
        (p2.frac_x, 0.25, "nanopillar_2.frac_x"),
        (p2.frac_y, 0.25, "nanopillar_2.frac_y"),
        (p2.rotation_deg, 112.5, "nanopillar_2.rotation_deg"),
    ]
    for observed, target, name in expected:
        if observed is None or not math.isclose(float(observed), target, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"{name} must be {target} for the validated alpha-pass dimer")


def write_apcd_metagrating_geometry_csv(rows: Iterable[dict[str, object]], path: Path) -> Path:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_METAGRATING_GEOMETRY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_apcd_metagrating_geometry_summary(
    rows: list[dict[str, float | int]],
    config: APCDSingleDimerConfig,
    path: Path,
) -> Path:
    if not rows:
        raise ValueError("Cannot write a geometry summary without rows")

    first = rows[0]
    K = int(first["K"])
    nanopillar_count = len(rows)
    p1 = config.geometry.nanopillar_1
    p2 = config.geometry.nanopillar_2

    lines = [
        f"# APCD K={K} Dimer Metagrating Geometry Dry Run",
        "",
        "- status: dry_run_geometry",
        f"- K: {K}",
        f"- dimer_count: {K}",
        f"- nanopillar_count: {nanopillar_count}",
        f"- wavelength_nm: {first['wavelength_nm']}",
        f"- target_angle_deg: {first['target_angle_deg']}",
        f"- supercell_period_nm: {first['supercell_period_nm']}",
        f"- dimer_pitch_nm: {first['dimer_pitch_nm']}",
        "- K_definition: K is the number of APCD dimers, not the number of individual nanopillars.",
        "- total_nanopillars: 2K",
        "",
        "Alpha-pass dimer source geometry:",
        "",
        (
            f"- nanopillar_1: length_nm={p1.length_nm}, width_nm={p1.width_nm}, "
            f"frac=({p1.frac_x}, {p1.frac_y}), rotation_deg={p1.rotation_deg}"
        ),
        (
            f"- nanopillar_2: length_nm={p2.length_nm}, width_nm={p2.width_nm}, "
            f"frac=({p2.frac_x}, {p2.frac_y}), rotation_deg={p2.rotation_deg}"
        ),
        "- pillar_2_switched_length_width: True",
        "- source_config: configs/apcd_fig2_elliptical_633nm_alpha_pass.yaml",
        "",
        "Scope note:",
        "",
        "- This file is a dry-run geometry definition only.",
        "- This is not an FDTD result.",
        "- This is not an .fsp export.",
        "- This is not a far-field or diffraction-order result.",
        "- No lumapi call is required to generate this file.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_apcd_metagrating_dry_run_outputs(
    config: APCDSingleDimerConfig,
    K: int,
    output_dir: Path,
    target_angle_deg: float = 15.0,
) -> tuple[Path, Path, list[dict[str, float | int]]]:
    validate_alpha_pass_dimer_source(config)
    rows = build_apcd_k_dimer_metagrating_geometry(config, K=K, target_angle_deg=target_angle_deg)
    csv_path = write_apcd_metagrating_geometry_csv(rows, output_dir / "geometry.csv")
    summary_path = write_apcd_metagrating_geometry_summary(rows, config, output_dir / "geometry_summary.md")
    return csv_path, summary_path, rows


def validate_apcd_metagrating_geometry_rows(rows: list[dict[str, float | int]], K: int) -> None:
    if len(rows) != 2 * K:
        raise ValueError(f"K={K} geometry must contain {2 * K} nanopillars, found {len(rows)}")
    if {int(row["K"]) for row in rows} != {K}:
        raise ValueError(f"All geometry rows must have K={K}")
    if len({int(row["global_pillar_index"]) for row in rows}) != len(rows):
        raise ValueError("global_pillar_index values must be unique")
    for dimer_index in range(K):
        dimer_rows = [row for row in rows if int(row["dimer_index"]) == dimer_index]
        if len(dimer_rows) != 2:
            raise ValueError(f"dimer_index={dimer_index} must contain exactly 2 nanopillars")

    for row in rows:
        pillar_index = int(row["pillar_index_in_dimer"])
        length = float(row["length_nm"])
        width = float(row["width_nm"])
        rotation = float(row["rotation_deg"])
        if pillar_index == 1:
            if not (math.isclose(length, 130.0) and math.isclose(width, 70.0) and math.isclose(rotation, 67.5)):
                raise ValueError("pillar 1 must keep the alpha-pass 130 x 70 nm, 67.5 deg geometry")
        elif pillar_index == 2:
            if math.isclose(length, 150.0) and math.isclose(width, 85.0):
                raise ValueError("original beta-selective pillar 2 geometry 150 x 85 nm is not allowed")
            if not (math.isclose(length, 85.0) and math.isclose(width, 150.0) and math.isclose(rotation, 112.5)):
                raise ValueError("pillar 2 must keep the alpha-pass 85 x 150 nm, 112.5 deg geometry")
        else:
            raise ValueError("pillar_index_in_dimer must be 1 or 2")


def export_apcd_metagrating_setup_only(
    config: APCDSingleDimerConfig,
    rows: list[dict[str, float | int]],
    runtime: RuntimeConfig,
    lumapi: ModuleType,
    fsp_output: Path,
) -> dict[str, object]:
    K = int(rows[0]["K"]) if rows else 0
    validate_alpha_pass_dimer_source(config)
    validate_apcd_metagrating_geometry_rows(rows, K)

    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        _build_apcd_metagrating_setup_model(fdtd, config, rows)
        fsp_output.parent.mkdir(parents=True, exist_ok=True)
        fdtd.save(str(fsp_output))
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass

    return apcd_metagrating_setup_summary_row(rows, fsp_output)


def export_apcd_metagrating_setup_only_from_runtime_file(
    config: APCDSingleDimerConfig,
    geometry_csv: Path,
    runtime_path: Path,
    fsp_output: Path,
) -> dict[str, object]:
    rows = read_apcd_metagrating_geometry_csv(geometry_csv)
    runtime = load_runtime_config(runtime_path)
    if not runtime.enable_lumerical:
        raise RuntimeError("runtime.enable_lumerical is false; setup-only .fsp export requires lumapi")
    lumapi = import_lumapi(runtime)
    return export_apcd_metagrating_setup_only(config, rows, runtime, lumapi, fsp_output)


def apcd_metagrating_setup_summary_row(
    rows: list[dict[str, float | int]],
    fsp_output: Path,
) -> dict[str, object]:
    if not rows:
        raise ValueError("Cannot summarize an empty metagrating setup")
    first = rows[0]
    K = int(first["K"])
    return {
        "K": K,
        "nanopillar_count": len(rows),
        "supercell_period_nm": float(first["supercell_period_nm"]),
        "dimer_pitch_nm": float(first["dimer_pitch_nm"]),
        "wavelength_nm": float(first["wavelength_nm"]),
        "target_angle_deg": float(first["target_angle_deg"]),
        "fsp_output": str(fsp_output),
        "dimer_group_count": K,
        "pillars_per_dimer_group": 2,
        "dimer_group_names": ", ".join(f"dimer_{index:02d}" for index in range(K)),
        "status": "setup_only",
        "fdtd_run_called": False,
    }


def write_apcd_metagrating_setup_summary(
    row: dict[str, object],
    geometry_csv: Path,
    path: Path,
) -> Path:
    K = int(row["K"])
    lines = [
        f"# APCD K={K} Dimer Metagrating Setup-Only Export",
        "",
        "- status: setup_only",
        f"- K: {K}",
        f"- nanopillar_count: {row['nanopillar_count']}",
        f"- supercell_period_nm: {row['supercell_period_nm']}",
        f"- dimer_pitch_nm: {row['dimer_pitch_nm']}",
        f"- wavelength_nm: {row['wavelength_nm']}",
        f"- target_angle_deg: {row['target_angle_deg']}",
        f"- geometry_source_csv: {geometry_csv}",
        f"- output_fsp_path: {row['fsp_output']}",
        "- fdtd_run_called: False",
        f"- dimer_group_count: {row['dimer_group_count']}",
        f"- pillars_per_dimer_group: {row['pillars_per_dimer_group']}",
        f"- group_names: {row['dimer_group_names']}",
        "",
        "Alpha-pass switched dimer geometry:",
        "",
        "- pillar 1: 130 x 70 nm, rotation 67.5 deg",
        "- pillar 2: 85 x 150 nm, rotation 112.5 deg",
        "- pillar_2_switched_length_width: True",
        "",
        "Scope note:",
        "",
        "- Current .fsp is setup-only.",
        "- FDTD was not run.",
        "- This is not an FDTD result.",
        "- No far-field or diffraction-order result has been extracted.",
        "- Current structure is only a K-dimer scaffold.",
        "- Future work must inspect or introduce the t_{alpha*<-alpha} phase-gradient design logic.",
        "- Future real runs must evaluate diffraction-order efficiency, not only total T.",
        "",
        "Dimer grouping:",
        "",
        "- Each APCD dimer is represented as one structure group.",
        "- Each structure group contains two nanopillars.",
        f"- Group names are ordered as {row['dimer_group_names']}.",
        "- This grouping is for GUI inspection and future dimer-level phase-gradient design.",
        "- Geometry is unchanged from the previous setup export.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_apcd_metagrating_gui_checklist(row: dict[str, object], path: Path) -> Path:
    K = int(row["K"])
    expected_pitch = "407.62 nm" if K == 6 else "349.39 nm" if K == 7 else "Lambda / K"
    lines = [
        f"# APCD K={K} Metagrating GUI Inspection Checklist",
        "",
        f"- [ ] Confirm there are 2K = {row['nanopillar_count']} nanopillars.",
        f"- [ ] Confirm object tree contains K = {K} dimer structure groups.",
        "- [ ] Confirm each dimer group contains exactly 2 nanopillars.",
        f"- [ ] Confirm dimer group names are ordered from dimer_00 to dimer_{K - 1:02d}.",
        "- [ ] Confirm grouping did not change pillar geometry or positions.",
        "- [ ] Confirm x span is about 2.4457 um.",
        "- [ ] Confirm y span is about 340 nm.",
        f"- [ ] Confirm K={K} dimer pitch is about {expected_pitch}.",
        "- [ ] Confirm pillar 2 is 85 x 150 nm, not 150 x 85 nm.",
        "- [ ] Confirm source is normal incidence.",
        "- [ ] Confirm T_fields monitor is on the transmission side.",
        "- [ ] Confirm T power monitor is on the transmission side.",
        "- [ ] Confirm z boundaries are PML.",
        "- [ ] Confirm x/y boundaries are periodic or Bloch-compatible.",
        "- [ ] Confirm c-Si nanopillars and Al2O3 substrate/material settings.",
        "- [ ] Confirm nm-to-um unit conversion is correct in the GUI.",
        "- [ ] Confirm this setup has no run results.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _build_apcd_metagrating_setup_model(
    fdtd: object,
    config: APCDSingleDimerConfig,
    rows: list[dict[str, float | int]],
) -> None:
    nm = 1e-9
    geometry = config.geometry
    simulation = config.simulation
    material = config.material

    first = rows[0]
    x_span = float(first["supercell_period_nm"]) * nm
    y_span = geometry.period_y_nm * nm
    height = geometry.height_nm * nm
    substrate_thickness = simulation.substrate_thickness_nm * nm
    wavelength = config.target.wavelength_nm * nm

    z_min = -substrate_thickness
    z_max = height + simulation.z_padding_above_nm * nm
    source_z = -simulation.source_offset_nm * nm
    monitor_z = height + simulation.monitor_offset_nm * nm

    fdtd.switchtolayout()
    fdtd.deleteall()

    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z min", z_min)
    fdtd.set("z max", z_max)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", simulation.mesh_accuracy)
    fdtd.set("simulation time", simulation.simulation_time_fs * 1e-15)

    fdtd.addrect()
    fdtd.set("name", "substrate")
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z min", z_min)
    fdtd.set("z max", 0)
    _set_metagrating_material(fdtd, material, is_substrate=True)

    K = int(first["K"])
    for dimer_index in range(K):
        group_name = f"dimer_{dimer_index:02d}"
        fdtd.addstructuregroup()
        fdtd.set("name", group_name)
        _set_group_scope(fdtd, f"::model::{group_name}")
        dimer_rows = sorted(
            (row for row in rows if int(row["dimer_index"]) == dimer_index),
            key=lambda row: int(row["pillar_index_in_dimer"]),
        )
        for row in dimer_rows:
            fdtd.addrect()
            fdtd.set("name", f"pillar_{int(row['pillar_index_in_dimer'])}")
            fdtd.set("x", float(row["x_nm"]) * nm)
            fdtd.set("y", float(row["y_nm"]) * nm)
            fdtd.set("x span", float(row["length_nm"]) * nm)
            fdtd.set("y span", float(row["width_nm"]) * nm)
            fdtd.set("z min", 0)
            fdtd.set("z max", height)
            fdtd.set("first axis", "z")
            fdtd.set("rotation 1", float(row["rotation_deg"]))
            _set_metagrating_material(fdtd, material, is_substrate=False)
        _set_group_scope(fdtd, "::model")

    _add_normal_incidence_plane_wave(fdtd, x_span, y_span, source_z, wavelength)

    fdtd.addpower()
    fdtd.set("name", "T")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z", monitor_z)

    fdtd.addprofile()
    fdtd.set("name", "T_fields")
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z", monitor_z)


def _set_metagrating_material(fdtd: object, material: APCDDimerMaterialConfig, is_substrate: bool) -> None:
    material_name = material.substrate_material_lumerical if is_substrate else material.meta_material_lumerical
    material_index = material.substrate_index if is_substrate else material.meta_index
    fdtd.set("material", material_name)
    if material_name == "<Object defined dielectric>" and material_index is not None:
        fdtd.set("index", material_index)


def _set_group_scope(fdtd: object, scope: str) -> None:
    if hasattr(fdtd, "groupscope"):
        fdtd.groupscope(scope)
    else:
        escaped = scope.replace("\\", "\\\\").replace('"', '\\"')
        fdtd.eval(f'groupscope("{escaped}");')


def _add_normal_incidence_plane_wave(
    fdtd: object,
    x_span: float,
    y_span: float,
    z: float,
    wavelength: float,
) -> None:
    fdtd.addplane()
    fdtd.set("name", "source_x")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", x_span)
    fdtd.set("y span", y_span)
    fdtd.set("z", z)
    fdtd.set("wavelength start", wavelength)
    fdtd.set("wavelength stop", wavelength)
    fdtd.set("polarization angle", 0)
    fdtd.set("phase", 0)
    fdtd.set("amplitude", 1)
