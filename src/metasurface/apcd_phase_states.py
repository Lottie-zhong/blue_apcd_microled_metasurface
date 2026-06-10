from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable


APCD_PHASE_STATE_LIBRARY_FIELDS = [
    "K",
    "phase_state_index",
    "phase_target_deg",
    "phase_target_rad",
    "ramp_sign",
    "geometry_variant_id",
    "source_geometry",
    "pillar_1_length_nm",
    "pillar_1_width_nm",
    "pillar_1_rotation_deg",
    "pillar_2_length_nm",
    "pillar_2_width_nm",
    "pillar_2_rotation_deg",
    "pillar_1_dx_nm",
    "pillar_1_dy_nm",
    "pillar_2_dx_nm",
    "pillar_2_dy_nm",
    "dimer_dx_nm",
    "dimer_dy_nm",
    "t_alpha_star_from_alpha_real",
    "t_alpha_star_from_alpha_imag",
    "t_alpha_star_from_alpha_abs",
    "t_alpha_star_from_alpha_phase_deg",
    "target_conversion",
    "t_beta_star_from_alpha_abs",
    "t_alpha_star_from_beta_abs",
    "t_beta_star_from_beta_abs",
    "beta_to_target_leakage",
    "beta_total_leakage",
    "phase_error_deg",
    "amplitude_pass",
    "leakage_pass",
    "phase_pass",
    "overall_pass",
    "notes",
]


APCD_PHASE_STATE_CANDIDATE_ROUTE_FIELDS = [
    "variant_id",
    "candidate_type",
    "description",
    "pillar_1_length_nm",
    "pillar_1_width_nm",
    "pillar_1_rotation_deg",
    "pillar_2_length_nm",
    "pillar_2_width_nm",
    "pillar_2_rotation_deg",
    "changed_parameter",
    "delta_nm",
    "expected_role",
    "requires_fDTD",
    "notes",
]


DEFAULT_PHASE_STATE_THRESHOLDS = {
    "target_conversion_early": 0.5,
    "target_conversion_strong": 0.7,
    "beta_to_target_leakage_max": 0.1,
    "beta_total_leakage_max": 0.2,
    "target_to_beta_ratio_min": 6.0,
    "phase_error_early_deg": 20.0,
    "phase_error_strong_deg": 10.0,
    "eps": 1.0e-12,
}


DEFAULT_ALPHA_PASS_GEOMETRY = {
    "source_geometry": "configs/apcd_fig2_elliptical_633nm_alpha_pass.yaml",
    "pillar_1_length_nm": 130.0,
    "pillar_1_width_nm": 70.0,
    "pillar_1_rotation_deg": 67.5,
    "pillar_2_length_nm": 85.0,
    "pillar_2_width_nm": 150.0,
    "pillar_2_rotation_deg": 112.5,
}


def baseline_alpha_pass_geometry() -> dict[str, float]:
    return {
        "pillar_1_length_nm": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_1_length_nm"]),
        "pillar_1_width_nm": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_1_width_nm"]),
        "pillar_1_rotation_deg": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_1_rotation_deg"]),
        "pillar_2_length_nm": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_2_length_nm"]),
        "pillar_2_width_nm": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_2_width_nm"]),
        "pillar_2_rotation_deg": float(DEFAULT_ALPHA_PASS_GEOMETRY["pillar_2_rotation_deg"]),
    }


def build_one_factor_geometry_variants() -> list[dict[str, object]]:
    baseline = baseline_alpha_pass_geometry()
    variant_specs = [
        ("baseline", "none", 0.0, "validated alpha-pass reference"),
        ("p1L_m10", "pillar_1_length_nm", -10.0, "test p1 length intrinsic phase sensitivity"),
        ("p1L_m5", "pillar_1_length_nm", -5.0, "test p1 length intrinsic phase sensitivity"),
        ("p1L_p5", "pillar_1_length_nm", 5.0, "test p1 length intrinsic phase sensitivity"),
        ("p1L_p10", "pillar_1_length_nm", 10.0, "test p1 length intrinsic phase sensitivity"),
        ("p1W_m5", "pillar_1_width_nm", -5.0, "test p1 width intrinsic phase sensitivity"),
        ("p1W_p5", "pillar_1_width_nm", 5.0, "test p1 width intrinsic phase sensitivity"),
        ("p2L_m5", "pillar_2_length_nm", -5.0, "test p2 length intrinsic phase sensitivity"),
        ("p2L_p5", "pillar_2_length_nm", 5.0, "test p2 length intrinsic phase sensitivity"),
        ("p2W_m10", "pillar_2_width_nm", -10.0, "test p2 width intrinsic phase sensitivity"),
        ("p2W_m5", "pillar_2_width_nm", -5.0, "test p2 width intrinsic phase sensitivity"),
        ("p2W_p5", "pillar_2_width_nm", 5.0, "test p2 width intrinsic phase sensitivity"),
        ("p2W_p10", "pillar_2_width_nm", 10.0, "test p2 width intrinsic phase sensitivity"),
    ]

    rows = []
    for variant_id, parameter, delta_nm, role in variant_specs:
        geometry = dict(baseline)
        if parameter != "none":
            geometry[parameter] = float(geometry[parameter]) + delta_nm
        row = {
            "variant_id": variant_id,
            "candidate_type": "baseline" if variant_id == "baseline" else "one_factor_geometry_variant",
            "description": _variant_description(variant_id, parameter, delta_nm),
            **geometry,
            "changed_parameter": parameter,
            "delta_nm": delta_nm,
            "expected_role": role,
            "requires_fDTD": "yes_future_order_resolved_jones_evaluation",
            "notes": (
                "route scaffold only; not evaluated; no FDTD run; not a steering result; "
                "candidate must later use alpha/beta -> alpha*/beta* pass/fail criteria"
            ),
        }
        validate_variant_geometry(row)
        rows.append(row)
    return rows


def validate_variant_geometry(row: dict[str, object]) -> bool:
    if float(row["pillar_1_rotation_deg"]) != 67.5:
        raise ValueError("pillar_1_rotation_deg must remain 67.5 deg in this route")
    if float(row["pillar_2_rotation_deg"]) != 112.5:
        raise ValueError("pillar_2_rotation_deg must remain 112.5 deg in this route")
    for key in (
        "pillar_1_length_nm",
        "pillar_1_width_nm",
        "pillar_2_length_nm",
        "pillar_2_width_nm",
    ):
        if float(row[key]) <= 0:
            raise ValueError(f"{key} must be positive")
    if float(row["pillar_2_length_nm"]) == 150.0 and float(row["pillar_2_width_nm"]) == 85.0:
        raise ValueError("original beta-selective pillar 2 geometry 150 x 85 nm is not allowed")

    baseline = baseline_alpha_pass_geometry()
    changed = [
        key
        for key in (
            "pillar_1_length_nm",
            "pillar_1_width_nm",
            "pillar_2_length_nm",
            "pillar_2_width_nm",
        )
        if not math.isclose(float(row[key]), float(baseline[key]))
    ]
    if row["variant_id"] == "baseline":
        if changed:
            raise ValueError("baseline variant must not change geometry")
    elif len(changed) != 1:
        raise ValueError("one-factor variants must change exactly one geometry parameter")
    return True


def export_candidate_route_rows() -> list[dict[str, object]]:
    return build_one_factor_geometry_variants()


def write_candidate_route_csv(rows: Iterable[dict[str, object]], path: Path) -> Path:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_PHASE_STATE_CANDIDATE_ROUTE_FIELDS)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in APCD_PHASE_STATE_CANDIDATE_ROUTE_FIELDS}
            for row in row_list
        )
    return path


def write_minimal_candidate_route_report(
    path: Path,
    rows: Iterable[dict[str, object]],
    *,
    supercell_period_nm: float = 2445.724192163921,
) -> Path:
    row_list = list(rows)
    detour_step_nm = displacement_for_phase_deg(60, order_m=1, supercell_period_nm=supercell_period_nm)
    variant_ids = ", ".join(str(row["variant_id"]) for row in row_list)
    lines = [
        "# APCD K=6 Minimal Phase-State Candidate Route",
        "",
        "## Scope",
        "",
        "This 08-P3 report defines a minimal K=6 phase-state candidate generation route.",
        "",
        "No FDTD run was performed. No `.fsp` file was exported. This route is not evaluated and is not a steering result.",
        "",
        "This is route only: it does not build a phase-ramp supercell, does not generate a large candidate set, does not do K=7, and does not switch to TiO2/450 nm or ML.",
        "",
        "## Current Basis",
        "",
        "- Phase 1 alpha-pass dimer Gate 1 passed.",
        "- The 07 order-resolved Jones pipeline has been opened for complex `J_xy` and `alpha/beta -> alpha*/beta*` evaluation.",
        "- 08-P1 phase-state schema and pass/fail criteria have been completed.",
        "- 08-P2 detour mechanism note has been completed.",
        "- There is currently no real phase-state candidate library.",
        "",
        "## Why Detour Displacement Is Not Used Directly",
        "",
        f"- For the simple `order_m=+1` convention, a `60 deg` detour phase requires `{detour_step_nm} nm` displacement.",
        f"- This is `Lambda/6`, using `Lambda = {supercell_period_nm} nm`.",
        "- This equals the K=6 dimer pitch scale.",
        "- Such a large move can reorder dimers rather than act as independent local phase tuning.",
        "- It can also change supercell sampling, nearest-neighbor spacing, and coupling.",
        "- Therefore detour displacement is kept as an analytic/sign-convention reference, not the final K=6 phase-state library.",
        "",
        "## Minimal Small-Geometry Variant Route",
        "",
        "Baseline alpha-pass dimer:",
        "",
        "- pillar 1: length `130 nm`, width `70 nm`, rotation `67.5 deg`",
        "- pillar 2: length `85 nm`, width `150 nm`, rotation `112.5 deg`",
        "",
        "Candidate principle:",
        "",
        "- Use one-factor-at-a-time length/width perturbations.",
        "- Keep both rotations fixed.",
        "- Do not generate all parameter combinations.",
        "- Do not use the original beta-selective pillar 2 geometry `150 x 85 nm`.",
        "- Future evaluation must use the existing order-resolved Jones pipeline.",
        "- Candidate pass/fail must use `phase_state_library_schema.csv` and `phase_state_pass_fail_criteria.md`.",
        "",
        f"Candidate count: {len(row_list)}",
        "",
        f"Variant IDs: `{variant_ids}`",
        "",
        "The chosen minimal set is baseline plus one-factor changes:",
        "",
        "- `pillar_1_length_nm`: baseline +/- 5 nm, +/- 10 nm",
        "- `pillar_1_width_nm`: baseline +/- 5 nm",
        "- `pillar_2_length_nm`: baseline +/- 5 nm",
        "- `pillar_2_width_nm`: baseline +/- 5 nm, +/- 10 nm",
        "",
        "## Output CSV",
        "",
        "`outputs/apcd_k6_metagrating_633nm/phase_state_candidate_route.csv` records route candidates only.",
        "",
        "It deliberately does not include fake `t_alpha_star_from_alpha`, leakage, or phase metrics.",
        "",
        "## Next Evidence Needed",
        "",
        "- Run no simulation in this step.",
        "- Later, evaluate only a very small selected set through the existing order-resolved Jones pipeline.",
        "- Only after candidates show high `|t_{alpha*<-alpha}|`, low beta leakage, and small target-channel phase error should a K=6 phase-ramp scaffold be considered.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_minimal_candidate_route_outputs(
    output_dir: Path,
    report_path: Path,
) -> tuple[Path, Path, list[dict[str, object]]]:
    rows = export_candidate_route_rows()
    csv_path = write_candidate_route_csv(rows, output_dir / "phase_state_candidate_route.csv")
    written_report = write_minimal_candidate_route_report(report_path, rows)
    return csv_path, written_report, rows


def detour_phase_deg(
    order_m: int,
    displacement_nm: float,
    supercell_period_nm: float,
    convention: str = "minus180_180",
) -> float:
    if supercell_period_nm == 0:
        raise ValueError("supercell_period_nm must be nonzero")
    phase_deg = 360.0 * int(order_m) * float(displacement_nm) / float(supercell_period_nm)
    return wrap_phase_deg(phase_deg, convention=convention)


def displacement_for_phase_deg(
    phase_deg: float,
    order_m: int,
    supercell_period_nm: float,
) -> float:
    if int(order_m) == 0:
        raise ValueError("order_m must be nonzero for detour displacement")
    return float(phase_deg) * float(supercell_period_nm) / (360.0 * int(order_m))


def build_k6_detour_displacement_targets(
    ramp_sign: str,
    supercell_period_nm: float,
    *,
    order_m: int = 1,
    phase_convention: str = "minus180_180",
) -> list[dict[str, float | int | str]]:
    sign = _normalize_ramp_sign(ramp_sign)
    rows: list[dict[str, float | int | str]] = []
    for index, phase_target_deg in enumerate(build_k6_phase_targets(sign)):
        displacement_nm = displacement_for_phase_deg(
            phase_deg=phase_target_deg,
            order_m=order_m,
            supercell_period_nm=supercell_period_nm,
        )
        rows.append(
            {
                "K": 6,
                "phase_state_index": index,
                "ramp_sign": sign,
                "order_m": int(order_m),
                "phase_target_unwrapped_deg": phase_target_deg,
                "phase_target_deg": wrap_phase_deg(phase_target_deg, convention=phase_convention),
                "dimer_dx_nm": displacement_nm,
                "detour_phase_deg": detour_phase_deg(
                    order_m=order_m,
                    displacement_nm=displacement_nm,
                    supercell_period_nm=supercell_period_nm,
                    convention=phase_convention,
                ),
                "notes": "analytic detour scaffold only; no FDTD run; not a steering result",
            }
        )
    return rows


def summarize_phase_generation_options() -> list[dict[str, str]]:
    return [
        {
            "mechanism": "detour_displacement",
            "priority": "A",
            "summary": (
                "Move the whole dimer group center to add order-dependent analytic phase; "
                "does not change intrinsic t_alpha_star_from_alpha phase."
            ),
            "risk": "Sign convention, supercell sampling, and coupling must be verified before use.",
        },
        {
            "mechanism": "small_geometry_variants",
            "priority": "B",
            "summary": "Perturb pillar length/width to tune intrinsic dynamic phase.",
            "risk": "May degrade alpha-pass and beta suppression; must use order-resolved Jones metrics.",
        },
        {
            "mechanism": "constrained_global_rotation",
            "priority": "C",
            "summary": "Possible geometric-phase-like knob, but not a default route for APCD.",
            "risk": "Global rotation may change the allowed alpha state and alpha/beta basis relation.",
        },
        {
            "mechanism": "hybrid_geometry_displacement",
            "priority": "later",
            "summary": "Combine small geometry variants with limited displacement.",
            "risk": "More degrees of freedom; keep deferred until single-knob behavior is understood.",
        },
    ]


def build_k6_phase_targets(ramp_sign: str) -> list[float]:
    sign = _normalize_ramp_sign(ramp_sign)
    values = [60.0 * index for index in range(6)]
    if sign == "minus":
        return [0.0 if index == 0 else -value for index, value in enumerate(values)]
    return values


def wrap_phase_deg(angle: float, convention: str = "minus180_180") -> float:
    if convention == "minus180_180":
        return ((float(angle) + 180.0) % 360.0) - 180.0
    if convention == "0_360":
        return float(angle) % 360.0
    raise ValueError(f"Unsupported phase convention: {convention}")


def phase_error_deg(measured: float, target: float) -> float:
    return abs(wrap_phase_deg(float(measured) - float(target), convention="minus180_180"))


def compute_phase_state_metrics(
    *,
    t_alpha_star_from_alpha: complex,
    t_beta_star_from_alpha: complex = 0 + 0j,
    t_alpha_star_from_beta: complex = 0 + 0j,
    t_beta_star_from_beta: complex = 0 + 0j,
    phase_target_deg: float,
    eps: float = 1.0e-12,
) -> dict[str, float]:
    target_abs = abs(t_alpha_star_from_alpha)
    target_phase_deg = wrap_phase_deg(math.degrees(math.atan2(t_alpha_star_from_alpha.imag, t_alpha_star_from_alpha.real)))
    target_conversion = target_abs**2
    beta_to_target_leakage = abs(t_alpha_star_from_beta) ** 2
    beta_total_leakage = beta_to_target_leakage + abs(t_beta_star_from_beta) ** 2
    return {
        "t_alpha_star_from_alpha_real": t_alpha_star_from_alpha.real,
        "t_alpha_star_from_alpha_imag": t_alpha_star_from_alpha.imag,
        "t_alpha_star_from_alpha_abs": target_abs,
        "t_alpha_star_from_alpha_phase_deg": target_phase_deg,
        "target_conversion": target_conversion,
        "t_beta_star_from_alpha_abs": abs(t_beta_star_from_alpha),
        "t_alpha_star_from_beta_abs": abs(t_alpha_star_from_beta),
        "t_beta_star_from_beta_abs": abs(t_beta_star_from_beta),
        "beta_to_target_leakage": beta_to_target_leakage,
        "beta_total_leakage": beta_total_leakage,
        "target_to_beta_ratio": target_conversion / max(beta_to_target_leakage, eps),
        "phase_error_deg": phase_error_deg(target_phase_deg, phase_target_deg),
    }


def evaluate_phase_state_pass_fail(
    metrics: dict[str, float],
    thresholds: dict[str, float] | None = None,
    *,
    strength: str = "early",
) -> dict[str, bool]:
    limits = dict(DEFAULT_PHASE_STATE_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)
    if strength not in {"early", "strong"}:
        raise ValueError("strength must be 'early' or 'strong'")

    target_key = "target_conversion_strong" if strength == "strong" else "target_conversion_early"
    phase_key = "phase_error_strong_deg" if strength == "strong" else "phase_error_early_deg"

    amplitude_pass = float(metrics["target_conversion"]) >= limits[target_key]
    leakage_pass = (
        float(metrics["beta_to_target_leakage"]) <= limits["beta_to_target_leakage_max"]
        and float(metrics["beta_total_leakage"]) <= limits["beta_total_leakage_max"]
        and float(metrics["target_to_beta_ratio"]) >= limits["target_to_beta_ratio_min"]
    )
    phase_pass = float(metrics["phase_error_deg"]) <= limits[phase_key]
    return {
        "amplitude_pass": amplitude_pass,
        "leakage_pass": leakage_pass,
        "phase_pass": phase_pass,
        "overall_pass": amplitude_pass and leakage_pass and phase_pass,
    }


def build_phase_state_schema_rows(
    *,
    K: int = 6,
    ramp_signs: Iterable[str] = ("plus", "minus"),
    geometry: dict[str, object] | None = None,
    phase_convention: str = "minus180_180",
) -> list[dict[str, object]]:
    if K != 6:
        raise ValueError("Phase 08 schema scaffold currently supports K=6 only")

    geometry_values = dict(DEFAULT_ALPHA_PASS_GEOMETRY)
    if geometry:
        geometry_values.update(geometry)

    rows: list[dict[str, object]] = []
    for ramp_sign in ramp_signs:
        normalized_sign = _normalize_ramp_sign(ramp_sign)
        for index, target_deg in enumerate(build_k6_phase_targets(normalized_sign)):
            wrapped_target_deg = wrap_phase_deg(target_deg, convention=phase_convention)
            row = {field: math.nan for field in APCD_PHASE_STATE_LIBRARY_FIELDS}
            row.update(
                {
                    "K": K,
                    "phase_state_index": index,
                    "phase_target_deg": wrapped_target_deg,
                    "phase_target_rad": math.radians(wrapped_target_deg),
                    "ramp_sign": normalized_sign,
                    "geometry_variant_id": f"k6_{normalized_sign}_state_{index}_schema_only",
                    "source_geometry": geometry_values["source_geometry"],
                    "pillar_1_length_nm": geometry_values["pillar_1_length_nm"],
                    "pillar_1_width_nm": geometry_values["pillar_1_width_nm"],
                    "pillar_1_rotation_deg": geometry_values["pillar_1_rotation_deg"],
                    "pillar_2_length_nm": geometry_values["pillar_2_length_nm"],
                    "pillar_2_width_nm": geometry_values["pillar_2_width_nm"],
                    "pillar_2_rotation_deg": geometry_values["pillar_2_rotation_deg"],
                    "pillar_1_dx_nm": 0.0,
                    "pillar_1_dy_nm": 0.0,
                    "pillar_2_dx_nm": 0.0,
                    "pillar_2_dy_nm": 0.0,
                    "dimer_dx_nm": 0.0,
                    "dimer_dy_nm": 0.0,
                    "amplitude_pass": "",
                    "leakage_pass": "",
                    "phase_pass": "",
                    "overall_pass": "",
                    "notes": (
                        "dry-run schema row; NaN optical fields; no FDTD run; "
                        "schema only; not a steering result"
                    ),
                }
            )
            rows.append(row)
    return rows


def write_phase_state_library_schema(rows: Iterable[dict[str, object]], path: Path) -> Path:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=APCD_PHASE_STATE_LIBRARY_FIELDS)
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, math.nan) for field in APCD_PHASE_STATE_LIBRARY_FIELDS}
            for row in row_list
        )
    return path


def write_phase_state_pass_fail_criteria(path: Path) -> Path:
    lines = [
        "# APCD K=6 Phase-State Library Pass/Fail Criteria",
        "",
        "## Scope",
        "",
        "This file defines the Phase 08 initial engineering schema and pass/fail criteria for a future K=6 dimer-level phase-state candidate library.",
        "",
        "No FDTD run was performed.",
        "",
        "This is schema only, not a steering result.",
        "",
        "There is currently no real phase-state candidate library.",
        "",
        "The schema prepares later candidate dimer evaluation; it does not prove a true APCD directional metagrating.",
        "",
        "## Phase Convention",
        "",
        "The dry-run CSV uses the `[-180, 180)` wrapped convention for `phase_target_deg` and `t_alpha_star_from_alpha_phase_deg`.",
        "",
        "The plus ramp before wrapping is:",
        "",
        "```text",
        "0, 60, 120, 180, 240, 300 deg",
        "```",
        "",
        "With `[-180, 180)` wrapping this is stored as:",
        "",
        "```text",
        "0, 60, 120, -180, -120, -60 deg",
        "```",
        "",
        "The minus ramp is:",
        "",
        "```text",
        "0, -60, -120, -180, -240, -300 deg",
        "```",
        "",
        "With `[-180, 180)` wrapping this is stored as:",
        "",
        "```text",
        "0, -60, -120, -180, 120, 60 deg",
        "```",
        "",
        "Phase error is the absolute shortest wrapped difference in degrees.",
        "",
        "## Target Channel",
        "",
        "The phase target applies to the APCD target channel:",
        "",
        "```text",
        "t_{alpha*<-alpha}",
        "```",
        "",
        "It is not an ordinary x/y phase target.",
        "",
        "All pass/fail checks must be based on the `alpha/beta -> alpha*/beta*` basis.",
        "",
        "Do not judge success from total T alone.",
        "",
        "Do not judge success from `grating()` power alone.",
        "",
        "The uniform scaffold's 0th-order result cannot be reused as six phase states.",
        "",
        "## Initial Engineering Thresholds",
        "",
        "These are Phase 08 initial engineering thresholds, not final paper metrics.",
        "",
        "| Metric | Early acceptable | Strong candidate |",
        "|---|---:|---:|",
        "| `target_conversion` | `>= 0.5` | `>= 0.7` |",
        "| `beta_to_target_leakage` | `<= 0.1` | `<= 0.1` |",
        "| `beta_total_leakage` | `<= 0.2` | `<= 0.2` |",
        "| `target_to_beta_ratio` | `>= 6` | `>= 6` |",
        "| `phase_error_deg` | `<= 20 deg` | `<= 10 deg` |",
        "",
        "Definitions:",
        "",
        "```text",
        "target_conversion = |t_{alpha*<-alpha}|^2",
        "beta_to_target_leakage = |t_{alpha*<-beta}|^2",
        "beta_total_leakage = |t_{alpha*<-beta}|^2 + |t_{beta*<-beta}|^2",
        "target_to_beta_ratio = target_conversion / max(beta_to_target_leakage, eps)",
        "```",
        "",
        "## Physical Boundaries",
        "",
        "- Global rotation may change the allowed alpha state and should not be the default phase knob.",
        "- APCD here must not be treated as an ordinary PB half-wave-plate design.",
        "- The original beta-selective pillar 2 geometry `150 x 85 nm` must not enter the candidate library baseline.",
        "- The baseline remains pillar 1 `130 x 70 nm`, rotation `67.5 deg`; pillar 2 `85 x 150 nm`, rotation `112.5 deg`.",
        "- K means dimer count. K=6 means 6 dimers and 12 nanopillars.",
        "- Do not switch to K=7, TiO2/450 nm, ML, large sweeps, or phase-ramp supercell assembly in this schema step.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_phase_state_dry_run_outputs(output_dir: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    rows = build_phase_state_schema_rows(K=6, ramp_signs=("plus", "minus"))
    schema_path = write_phase_state_library_schema(rows, output_dir / "phase_state_library_schema.csv")
    criteria_path = write_phase_state_pass_fail_criteria(output_dir / "phase_state_pass_fail_criteria.md")
    return schema_path, criteria_path, rows


def _variant_description(variant_id: str, parameter: str, delta_nm: float) -> str:
    if variant_id == "baseline":
        return "validated alpha-pass baseline geometry; route reference only"
    sign = "plus" if delta_nm > 0 else "minus"
    return f"one-factor {parameter} {sign} {abs(delta_nm):g} nm from alpha-pass baseline"


def _normalize_ramp_sign(ramp_sign: str) -> str:
    value = str(ramp_sign).lower()
    if value in {"plus", "+", "+1", "1"}:
        return "plus"
    if value in {"minus", "-", "-1"}:
        return "minus"
    raise ValueError("ramp_sign must be plus or minus")
