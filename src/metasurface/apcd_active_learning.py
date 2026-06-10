from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence


ML_READY_DATASET_SCHEMA_FIELDS = [
    "column_name",
    "column_role",
    "dtype",
    "required",
    "notes",
]

ML_INPUT_COLUMNS = [
    "variant_id",
    "candidate_family",
    "p1_length_nm",
    "p1_width_nm",
    "p2_length_nm",
    "p2_width_nm",
    "p1_frac_x",
    "p1_frac_y",
    "p2_frac_x",
    "p2_frac_y",
    "internal_dx_nm",
    "internal_dy_nm",
    "p1_rotation_deg",
    "p2_rotation_deg",
    "period_x_nm",
    "period_y_nm",
    "height_nm",
    "material",
    "substrate",
]

ML_OUTPUT_LABEL_COLUMNS = [
    "t_alpha_star_from_alpha_real",
    "t_alpha_star_from_alpha_imag",
    "t_alpha_star_from_alpha_abs",
    "phase_deg",
    "phase_shift_vs_baseline_deg",
    "target_conversion",
    "opposite_spin_leakage",
    "conversion_to_leakage_ratio",
    "PD",
    "overall_early_pass",
    "source_result_csv",
    "notes",
]

CANDIDATE_PARAMETER_SCHEMA_FIELDS = [
    "parameter_name",
    "baseline_value",
    "min_value",
    "max_value",
    "step_or_sampling",
    "search_stage",
    "notes",
]


DEFAULT_BASELINE = {
    "p1_length_nm": 130.0,
    "p1_width_nm": 70.0,
    "p2_length_nm": 85.0,
    "p2_width_nm": 150.0,
    "p1_frac_x": 0.75,
    "p1_frac_y": 0.75,
    "p2_frac_x": 0.25,
    "p2_frac_y": 0.25,
    "internal_dx_nm": 0.0,
    "internal_dy_nm": 0.0,
    "p1_rotation_deg": 67.5,
    "p2_rotation_deg": 112.5,
    "period_x_nm": 340.0,
    "period_y_nm": 340.0,
    "height_nm": 300.0,
    "material": "c-Si",
    "substrate": "Al2O3",
}


def build_ml_dataset_schema() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    dtype_by_column = {
        "variant_id": "string",
        "candidate_family": "string",
        "material": "string",
        "substrate": "string",
        "overall_early_pass": "boolean_or_blank",
        "source_result_csv": "string",
        "notes": "string",
    }
    notes_by_column = {
        "variant_id": "Stable candidate identifier; one row per evaluated dimer state.",
        "candidate_family": "Examples: baseline, multi_parameter_candidate, active_learning_round_n.",
        "p1_rotation_deg": "Fixed to 67.5 deg in the first search stage.",
        "p2_rotation_deg": "Fixed to 112.5 deg in the first search stage.",
        "t_alpha_star_from_alpha_real": "Preferred surrogate target; avoids phase wrap ambiguity.",
        "t_alpha_star_from_alpha_imag": "Preferred surrogate target; combines with real part for phase.",
        "phase_deg": "Derived wrapped phase; useful for binning but not the only supervision target.",
        "phase_shift_vs_baseline_deg": "Wrapped target-channel shift relative to the validated baseline.",
        "target_conversion": "Higher is better for alpha -> alpha* target channel.",
        "opposite_spin_leakage": "Lower is better; captures leakage into the opposite spin channel.",
        "conversion_to_leakage_ratio": "Higher is better; use an epsilon guard when computed.",
        "PD": "Polarization discrimination metric from the existing APCD analysis convention.",
        "overall_early_pass": "Engineering pass/fail label, not a final paper metric.",
        "source_result_csv": "Path to the real FDTD result CSV when available.",
        "notes": "Must state dry-run, missing data, or result provenance explicitly.",
    }

    for column in ML_INPUT_COLUMNS:
        rows.append(
            {
                "column_name": column,
                "column_role": "input_parameter",
                "dtype": dtype_by_column.get(column, "float"),
                "required": "yes",
                "notes": notes_by_column.get(column, "Candidate geometry or material descriptor."),
            }
        )
    for column in ML_OUTPUT_LABEL_COLUMNS:
        rows.append(
            {
                "column_name": column,
                "column_role": "output_label" if column not in {"source_result_csv", "notes"} else "metadata",
                "dtype": dtype_by_column.get(column, "float"),
                "required": "yes" if column not in {"source_result_csv", "notes"} else "recommended",
                "notes": notes_by_column.get(column, "Real FDTD-derived label; leave blank until evaluated."),
            }
        )
    return rows


def build_candidate_parameter_schema() -> list[dict[str, object]]:
    return [
        _parameter_row("p1_length_nm", 130.0, 110.0, 150.0, "lhs_or_grid_5_nm", "stage1_search", "Primary multi-parameter geometry search variable."),
        _parameter_row("p1_width_nm", 70.0, 55.0, 90.0, "lhs_or_grid_5_nm", "stage1_search", "Primary multi-parameter geometry search variable."),
        _parameter_row("p2_length_nm", 85.0, 70.0, 105.0, "lhs_or_grid_5_nm", "stage1_search", "Primary multi-parameter geometry search variable."),
        _parameter_row("p2_width_nm", 150.0, 130.0, 170.0, "lhs_or_grid_5_nm", "stage1_search", "Primary multi-parameter geometry search variable."),
        _parameter_row("p1_frac_x", 0.75, 0.65, 0.85, "optional_lhs_0.02", "stage2_optional", "Fractional position; keep near alpha-pass layout initially."),
        _parameter_row("p1_frac_y", 0.75, 0.65, 0.85, "optional_lhs_0.02", "stage2_optional", "Fractional position; keep near alpha-pass layout initially."),
        _parameter_row("p2_frac_x", 0.25, 0.15, 0.35, "optional_lhs_0.02", "stage2_optional", "Fractional position; keep near alpha-pass layout initially."),
        _parameter_row("p2_frac_y", 0.25, 0.15, 0.35, "optional_lhs_0.02", "stage2_optional", "Fractional position; keep near alpha-pass layout initially."),
        _parameter_row("internal_dx_nm", 0.0, -40.0, 40.0, "lhs_or_grid_10_nm", "stage1_search", "Relative in-plane dimer offset candidate variable."),
        _parameter_row("internal_dy_nm", 0.0, -40.0, 40.0, "lhs_or_grid_10_nm", "stage1_search", "Relative in-plane dimer offset candidate variable."),
        _parameter_row("p1_rotation_deg", 67.5, 67.5, 67.5, "fixed", "fixed_stage1", "Do not search initially; changing it may alter alpha/beta allowed state."),
        _parameter_row("p2_rotation_deg", 112.5, 112.5, 112.5, "fixed", "fixed_stage1", "Do not search initially; changing it may alter alpha/beta allowed state."),
        _parameter_row("period_x_nm", 340.0, 340.0, 340.0, "fixed", "fixed_stage1", "Keep baseline single-dimer period for the first active-learning scaffold."),
        _parameter_row("period_y_nm", 340.0, 340.0, 340.0, "fixed", "fixed_stage1", "Keep baseline single-dimer period for the first active-learning scaffold."),
        _parameter_row("height_nm", 300.0, 300.0, 300.0, "fixed", "fixed_stage1", "Do not reopen height in this stage."),
        _parameter_row("material", "c-Si", "c-Si", "c-Si", "fixed", "fixed_stage1", "Do not switch material in 09-P0."),
        _parameter_row("substrate", "Al2O3", "Al2O3", "Al2O3", "fixed", "fixed_stage1", "Keep the validated substrate convention."),
    ]


def wrap_phase_deg(phase_deg: float, convention: str = "[-180,180)") -> float:
    normalized = _normalize_phase_convention(convention)
    phase = float(phase_deg)
    if normalized == "minus180_180":
        return ((phase + 180.0) % 360.0) - 180.0
    if normalized == "0_360":
        return phase % 360.0
    raise ValueError(f"Unsupported phase convention: {convention}")


def phase_bin_targets(k: int = 6, convention: str = "[-180,180)") -> list[float]:
    if int(k) <= 0:
        raise ValueError("k must be positive")
    step = 360.0 / int(k)
    return [wrap_phase_deg(index * step, convention=convention) for index in range(int(k))]


def phase_error_to_bins(phase_deg: float, targets: Sequence[float]) -> dict[str, object]:
    if not targets:
        raise ValueError("targets must contain at least one phase bin")
    wrapped_phase = wrap_phase_deg(phase_deg)
    per_bin_errors = []
    for index, target in enumerate(targets):
        signed_error = wrap_phase_deg(wrapped_phase - float(target))
        per_bin_errors.append(
            {
                "phase_bin_index": index,
                "target_phase_deg": float(target),
                "signed_error_deg": signed_error,
                "abs_error_deg": abs(signed_error),
            }
        )
    nearest = min(per_bin_errors, key=lambda row: (float(row["abs_error_deg"]), int(row["phase_bin_index"])))
    return {
        "phase_deg": wrapped_phase,
        "nearest_bin_index": nearest["phase_bin_index"],
        "nearest_target_deg": nearest["target_phase_deg"],
        "signed_error_deg": nearest["signed_error_deg"],
        "abs_error_deg": nearest["abs_error_deg"],
        "per_bin_errors": per_bin_errors,
    }


def score_candidate_for_phase_bin(
    *,
    phase_deg: float,
    target_phase_deg: float,
    target_conversion: float,
    opposite_spin_leakage: float,
    conversion_to_leakage_ratio: float | None = None,
    PD: float | None = None,
    surrogate_uncertainty: float = 0.0,
    phase_tolerance_deg: float = 30.0,
) -> dict[str, float]:
    if phase_tolerance_deg <= 0:
        raise ValueError("phase_tolerance_deg must be positive")
    phase_error = abs(wrap_phase_deg(float(phase_deg) - float(target_phase_deg)))
    phase_score = max(0.0, 1.0 - phase_error / phase_tolerance_deg)
    target_score = _clip01(float(target_conversion))
    leakage_score = 1.0 - _clip01(float(opposite_spin_leakage))
    if conversion_to_leakage_ratio is None:
        ratio_score = 0.5
    else:
        ratio_score = _clip01(math.log1p(max(0.0, float(conversion_to_leakage_ratio))) / math.log1p(20.0))
    pd_score = 0.5 if PD is None else _clip01((float(PD) + 1.0) / 2.0)
    uncertainty_bonus = 0.1 * _clip01(float(surrogate_uncertainty))
    active_learning_score = (
        0.40 * phase_score
        + 0.25 * target_score
        + 0.20 * leakage_score
        + 0.10 * ratio_score
        + 0.05 * pd_score
        + uncertainty_bonus
    )
    return {
        "active_learning_score": active_learning_score,
        "phase_error_deg": phase_error,
        "phase_score": phase_score,
        "target_score": target_score,
        "leakage_score": leakage_score,
        "ratio_score": ratio_score,
        "pd_score": pd_score,
        "uncertainty_bonus": uncertainty_bonus,
    }


def rank_candidates_by_active_learning_score(
    candidates: Iterable[dict[str, object]],
    targets: Sequence[float] | None = None,
    *,
    per_bin: int = 3,
) -> list[dict[str, object]]:
    if per_bin <= 0:
        raise ValueError("per_bin must be positive")
    candidate_rows = list(candidates)
    phase_targets = list(targets if targets is not None else phase_bin_targets(k=6))
    ranked: list[dict[str, object]] = []
    for bin_index, target in enumerate(phase_targets):
        scored_for_bin = []
        for candidate in candidate_rows:
            score = score_candidate_for_phase_bin(
                phase_deg=_float_from_row(candidate, "phase_deg"),
                target_phase_deg=float(target),
                target_conversion=_float_from_row(candidate, "target_conversion"),
                opposite_spin_leakage=_float_from_row(candidate, "opposite_spin_leakage"),
                conversion_to_leakage_ratio=_optional_float_from_row(candidate, "conversion_to_leakage_ratio"),
                PD=_optional_float_from_row(candidate, "PD"),
                surrogate_uncertainty=_optional_float_from_row(candidate, "surrogate_uncertainty") or 0.0,
            )
            scored_for_bin.append(
                {
                    **candidate,
                    "phase_bin_index": bin_index,
                    "target_phase_deg": float(target),
                    **score,
                }
            )
        scored_for_bin.sort(
            key=lambda row: (
                -float(row["active_learning_score"]),
                float(row["phase_error_deg"]),
                str(row.get("variant_id", "")),
            )
        )
        ranked.extend(scored_for_bin[:per_bin])
    return ranked


def validate_candidate_bounds(
    candidate: dict[str, object],
    parameter_schema: Iterable[dict[str, object]] | None = None,
    *,
    strict: bool = True,
) -> list[str]:
    schema = list(parameter_schema if parameter_schema is not None else build_candidate_parameter_schema())
    violations: list[str] = []
    for row in schema:
        name = str(row["parameter_name"])
        if name not in candidate:
            violations.append(f"{name}: missing")
            continue
        value = candidate[name]
        min_value = row["min_value"]
        max_value = row["max_value"]
        if _is_number_like(min_value) and _is_number_like(max_value):
            numeric_value = _try_float(value)
            if numeric_value is None:
                violations.append(f"{name}: non-numeric value {value!r}")
                continue
            if numeric_value < float(min_value) or numeric_value > float(max_value):
                violations.append(f"{name}: {numeric_value:g} outside [{float(min_value):g}, {float(max_value):g}]")
        elif str(value) != str(row["baseline_value"]):
            violations.append(f"{name}: {value!r} must remain fixed at {row['baseline_value']!r}")
    if violations and strict:
        raise ValueError("; ".join(violations))
    return violations


def write_rows_csv(rows: Iterable[dict[str, object]], path: Path, fieldnames: Sequence[str]) -> Path:
    row_list = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in row_list)
    return path


def write_phase_bin_targets_csv(path: Path, *, k: int = 6, convention: str = "[-180,180)") -> Path:
    targets = phase_bin_targets(k=k, convention=convention)
    rows = [
        {
            "K": int(k),
            "phase_bin_index": index,
            "phase_target_deg": target,
            "convention": convention,
            "notes": "K means dimer count; K=6 uses 60 deg target-channel phase bins.",
        }
        for index, target in enumerate(targets)
    ]
    return write_rows_csv(rows, path, ["K", "phase_bin_index", "phase_target_deg", "convention", "notes"])


def write_active_learning_scoring_rules(path: Path) -> Path:
    lines = [
        "# APCD K=6 Active Learning Scoring Rules",
        "",
        "Scope: scaffold only. No training is performed here. No FDTD run is performed here. No `.fsp` file is exported here. This is not a steering result.",
        "",
        "## Candidate score",
        "",
        "For each predicted candidate and each K=6 phase bin, compute:",
        "",
        "```text",
        "score = 0.40 * phase_score",
        "      + 0.25 * target_score",
        "      + 0.20 * leakage_score",
        "      + 0.10 * ratio_score",
        "      + 0.05 * pd_score",
        "      + 0.10 * surrogate_uncertainty_bonus",
        "```",
        "",
        "- `phase_score = max(0, 1 - wrapped_phase_error_deg / 30)`",
        "- `target_score = clip(target_conversion, 0, 1)`",
        "- `leakage_score = 1 - clip(opposite_spin_leakage, 0, 1)`",
        "- `ratio_score = clip(log1p(conversion_to_leakage_ratio) / log1p(20), 0, 1)`",
        "- `pd_score = clip((PD + 1) / 2, 0, 1)`",
        "",
        "Higher score is better. The ranking is done per phase bin, then the top 2-3 candidates per bin are selected for future real FDTD verification.",
        "",
        "## Active learning loop planned for later",
        "",
        "1. Train a small surrogate from the current real FDTD dataset.",
        "2. Predict responses for a bounded candidate pool.",
        "3. Rank candidates separately for the 0/60/120/180/240/300 deg target-channel phase bins.",
        "4. Select 2-3 candidates per bin.",
        "5. Run real FDTD outside this scaffold step.",
        "6. Append verified rows to the dataset and retrain.",
        "",
        "Use real/imaginary `t_alpha_star_from_alpha` as primary surrogate outputs because phase wraps at +/-180 deg.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _parameter_row(
    parameter_name: str,
    baseline_value: object,
    min_value: object,
    max_value: object,
    step_or_sampling: str,
    search_stage: str,
    notes: str,
) -> dict[str, object]:
    return {
        "parameter_name": parameter_name,
        "baseline_value": baseline_value,
        "min_value": min_value,
        "max_value": max_value,
        "step_or_sampling": step_or_sampling,
        "search_stage": search_stage,
        "notes": notes,
    }


def _normalize_phase_convention(convention: str) -> str:
    value = str(convention).strip().lower()
    if value in {"[-180,180)", "minus180_180", "-180_180", "minus180"}:
        return "minus180_180"
    if value in {"[0,360)", "0_360", "zero360"}:
        return "0_360"
    raise ValueError(f"Unsupported phase convention: {convention}")


def _clip01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _float_from_row(row: dict[str, object], key: str) -> float:
    value = _try_float(row.get(key))
    if value is None:
        raise ValueError(f"Candidate is missing numeric {key}")
    return value


def _optional_float_from_row(row: dict[str, object], key: str) -> float | None:
    return _try_float(row.get(key))


def _try_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_number_like(value: object) -> bool:
    return _try_float(value) is not None
