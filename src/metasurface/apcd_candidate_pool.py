from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

from metasurface.apcd_active_learning import build_candidate_parameter_schema


CANDIDATE_POOL_FIELDS = [
    "candidate_id",
    "candidate_family",
    "source",
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
    "predicted_phase_bin",
    "intended_role",
    "requires_fdtd",
    "status",
    "notes",
]

ANCHOR_VARIANT_IDS = ["p1W_m5", "p2W_p10", "p1L_m10", "p1L_m5", "p1L_p5"]

BASELINE_VALUES = {
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


def build_baseline_candidate() -> dict[str, object]:
    return _candidate_row(
        candidate_id="baseline",
        candidate_family="baseline",
        source="ml_ready_dataset_v0_anchor",
        intended_role="validated reference anchor; include in every pool",
        notes="existing real FDTD row reused as anchor; no new FDTD run in 09-P2",
        **BASELINE_VALUES,
    )


def build_anchor_candidates_from_v0(dataset_v0_csv: str | Path) -> list[dict[str, object]]:
    path = Path(dataset_v0_csv)
    with path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["variant_id"]: row for row in rows}
    anchors: list[dict[str, object]] = []
    for variant_id in ANCHOR_VARIANT_IDS:
        if variant_id not in by_id:
            continue
        row = by_id[variant_id]
        anchors.append(
            _candidate_row(
                candidate_id=variant_id,
                candidate_family="v0_good_anchor",
                source="ml_ready_dataset_v0",
                intended_role="existing good v0 candidate anchor for DOE comparison",
                notes="existing real FDTD row reused as anchor; no surrogate prediction; no new FDTD run in 09-P2",
                **_geometry_from_dataset_row(row),
            )
        )
    return anchors


def build_bounded_doe_candidates() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    specs = [
        (
            "p1w_p2w",
            "p1W + p2W combined width perturbation",
            [
                {"p1_width_nm": 60, "p2_width_nm": 140},
                {"p1_width_nm": 60, "p2_width_nm": 160},
                {"p1_width_nm": 65, "p2_width_nm": 155},
                {"p1_width_nm": 75, "p2_width_nm": 145},
                {"p1_width_nm": 80, "p2_width_nm": 160},
                {"p1_width_nm": 85, "p2_width_nm": 140},
                {"p1_width_nm": 60, "p2_width_nm": 170},
                {"p1_width_nm": 90, "p2_width_nm": 130},
            ],
        ),
        (
            "p1l_p1w",
            "p1L + p1W combined perturbation",
            [
                {"p1_length_nm": 115, "p1_width_nm": 60},
                {"p1_length_nm": 120, "p1_width_nm": 65},
                {"p1_length_nm": 125, "p1_width_nm": 80},
                {"p1_length_nm": 135, "p1_width_nm": 60},
                {"p1_length_nm": 145, "p1_width_nm": 75},
                {"p1_length_nm": 150, "p1_width_nm": 85},
            ],
        ),
        (
            "p1w_dx",
            "p1W + internal_dx perturbation",
            [
                {"p1_width_nm": 60, "internal_dx_nm": -30},
                {"p1_width_nm": 65, "internal_dx_nm": 20},
                {"p1_width_nm": 75, "internal_dx_nm": -20},
                {"p1_width_nm": 80, "internal_dx_nm": 30},
                {"p1_width_nm": 85, "internal_dx_nm": -10},
                {"p1_width_nm": 90, "internal_dx_nm": 40},
            ],
        ),
        (
            "p2w_dy",
            "p2W + internal_dy perturbation",
            [
                {"p2_width_nm": 135, "internal_dy_nm": -30},
                {"p2_width_nm": 140, "internal_dy_nm": 20},
                {"p2_width_nm": 145, "internal_dy_nm": -20},
                {"p2_width_nm": 155, "internal_dy_nm": 30},
                {"p2_width_nm": 160, "internal_dy_nm": -10},
                {"p2_width_nm": 170, "internal_dy_nm": 40},
            ],
        ),
        (
            "p1l_p2w",
            "p1L + p2W combined perturbation",
            [
                {"p1_length_nm": 115, "p2_width_nm": 160},
                {"p1_length_nm": 120, "p2_width_nm": 145},
                {"p1_length_nm": 125, "p2_width_nm": 170},
                {"p1_length_nm": 135, "p2_width_nm": 135},
                {"p1_length_nm": 145, "p2_width_nm": 155},
                {"p1_length_nm": 150, "p2_width_nm": 130},
            ],
        ),
        (
            "p1w_p2w_dx",
            "p1W + p2W + internal_dx combined perturbation",
            [
                {"p1_width_nm": 60, "p2_width_nm": 160, "internal_dx_nm": -30},
                {"p1_width_nm": 65, "p2_width_nm": 145, "internal_dx_nm": 30},
                {"p1_width_nm": 75, "p2_width_nm": 170, "internal_dx_nm": -20},
                {"p1_width_nm": 80, "p2_width_nm": 135, "internal_dx_nm": 20},
                {"p1_width_nm": 85, "p2_width_nm": 155, "internal_dx_nm": -40},
                {"p1_width_nm": 90, "p2_width_nm": 140, "internal_dx_nm": 40},
            ],
        ),
        (
            "lhs_like",
            "deterministic Latin-hypercube-like mixed perturbation",
            [
                {"p1_length_nm": 110, "p1_width_nm": 55, "p2_length_nm": 70, "p2_width_nm": 130, "internal_dx_nm": -40, "internal_dy_nm": 30},
                {"p1_length_nm": 115, "p1_width_nm": 80, "p2_length_nm": 95, "p2_width_nm": 165, "internal_dx_nm": 20, "internal_dy_nm": -40},
                {"p1_length_nm": 120, "p1_width_nm": 90, "p2_length_nm": 80, "p2_width_nm": 150, "internal_dx_nm": -10, "internal_dy_nm": 10},
                {"p1_length_nm": 125, "p1_width_nm": 60, "p2_length_nm": 105, "p2_width_nm": 140, "internal_dx_nm": 40, "internal_dy_nm": -20},
                {"p1_length_nm": 135, "p1_width_nm": 85, "p2_length_nm": 75, "p2_width_nm": 170, "internal_dx_nm": -20, "internal_dy_nm": 40},
                {"p1_length_nm": 140, "p1_width_nm": 65, "p2_length_nm": 100, "p2_width_nm": 135, "internal_dx_nm": 30, "internal_dy_nm": 0},
                {"p1_length_nm": 145, "p1_width_nm": 75, "p2_length_nm": 90, "p2_width_nm": 155, "internal_dx_nm": 0, "internal_dy_nm": -30},
                {"p1_length_nm": 150, "p1_width_nm": 70, "p2_length_nm": 85, "p2_width_nm": 160, "internal_dx_nm": -30, "internal_dy_nm": 20},
            ],
        ),
    ]

    for family, role, deltas in specs:
        for index, delta in enumerate(deltas, start=1):
            candidate_id = f"doe_{family}_{index:02d}"
            row = _candidate_row(
                candidate_id=candidate_id,
                candidate_family=assign_candidate_family(delta, default=family),
                source="deterministic_mixed_doe_v0",
                intended_role=role,
                notes="bounded DOE scaffold only; requires later gap validation and real FDTD; no surrogate prediction",
                **_with_baseline(delta),
            )
            rows.append(row)
    return rows


def validate_candidate_bounds(
    candidate: dict[str, object],
    parameter_schema: Iterable[dict[str, object]] | None = None,
    *,
    strict: bool = True,
) -> list[str]:
    schema = list(parameter_schema if parameter_schema is not None else build_candidate_parameter_schema())
    bounds = {str(row["parameter_name"]): row for row in schema}
    violations: list[str] = []
    for name, row in bounds.items():
        if name not in candidate:
            violations.append(f"{name}: missing")
            continue
        value = candidate[name]
        min_value = row["min_value"]
        max_value = row["max_value"]
        if _is_number_like(min_value) and _is_number_like(max_value):
            numeric_value = _to_float(value)
            if numeric_value < float(min_value) or numeric_value > float(max_value):
                violations.append(f"{name}: {numeric_value:g} outside [{float(min_value):g}, {float(max_value):g}]")
        elif str(value) != str(row["baseline_value"]):
            violations.append(f"{name}: {value!r} must remain fixed at {row['baseline_value']!r}")

    if float(candidate.get("p1_rotation_deg", 0)) != 67.5:
        violations.append("p1_rotation_deg: must remain fixed at 67.5")
    if float(candidate.get("p2_rotation_deg", 0)) != 112.5:
        violations.append("p2_rotation_deg: must remain fixed at 112.5")
    if float(candidate.get("p2_length_nm", 0)) == 150.0 and float(candidate.get("p2_width_nm", 0)) == 85.0:
        violations.append("p2 geometry 150 x 85 nm is beta-selective and is not allowed")

    if violations and strict:
        raise ValueError("; ".join(violations))
    return violations


def assign_candidate_family(candidate_delta: dict[str, object], default: str = "mixed_doe") -> str:
    changed = {key for key, value in candidate_delta.items() if key in BASELINE_VALUES and value != BASELINE_VALUES[key]}
    if changed == {"p1_width_nm", "p2_width_nm"}:
        return "p1w_p2w_combo"
    if changed == {"p1_length_nm", "p1_width_nm"}:
        return "p1l_p1w_combo"
    if changed == {"p1_width_nm", "internal_dx_nm"}:
        return "p1w_internal_dx_combo"
    if changed == {"p2_width_nm", "internal_dy_nm"}:
        return "p2w_internal_dy_combo"
    if changed == {"p1_length_nm", "p2_width_nm"}:
        return "p1l_p2w_combo"
    if changed == {"p1_width_nm", "p2_width_nm", "internal_dx_nm"}:
        return "p1w_p2w_internal_dx_combo"
    if len(changed) >= 4:
        return "lhs_like_mixed_combo"
    return default


def export_candidate_pool_csv(candidates: Iterable[dict[str, object]], path: str | Path) -> Path:
    row_list = list(candidates)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_POOL_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in CANDIDATE_POOL_FIELDS} for row in row_list)
    return output_path


def summarize_candidate_pool(candidates: Sequence[dict[str, object]]) -> dict[str, object]:
    family_counts = Counter(str(row["candidate_family"]) for row in candidates)
    ids = [str(row["candidate_id"]) for row in candidates]
    anchors_present = [anchor for anchor in ["baseline", *ANCHOR_VARIANT_IDS] if anchor in ids]
    violations = []
    for row in candidates:
        violations.extend(f"{row['candidate_id']}: {item}" for item in validate_candidate_bounds(row, strict=False))
    return {
        "candidate_count": len(candidates),
        "family_counts": dict(sorted(family_counts.items())),
        "anchors_present": anchors_present,
        "bounds_ok": len(violations) == 0,
        "bounds_violations": violations,
        "unique_candidate_ids": len(set(ids)) == len(ids),
    }


def build_candidate_pool(dataset_v0_csv: str | Path) -> list[dict[str, object]]:
    candidates = [build_baseline_candidate()]
    candidates.extend(build_anchor_candidates_from_v0(dataset_v0_csv))
    candidates.extend(build_bounded_doe_candidates())
    return _deduplicate_candidates(candidates)


def write_candidate_pool_summary(path: str | Path, candidates: Sequence[dict[str, object]]) -> Path:
    summary = summarize_candidate_pool(candidates)
    family_lines = [f"- `{family}`: {count}" for family, count in summary["family_counts"].items()]
    lines = [
        "# APCD K=6 Bounded Candidate Pool v0 Summary",
        "",
        "Scope: 09-P2 candidate pool scaffold only. No FDTD run was performed. No lumapi call was made. No `.fsp` file was exported. No model was trained. No surrogate prediction was generated. This is not a steering result.",
        "",
        f"Candidate count: {summary['candidate_count']}",
        f"Unique candidate IDs: {summary['unique_candidate_ids']}",
        f"Bounds check: {'passed' if summary['bounds_ok'] else 'failed'}",
        f"Anchors present: {', '.join(summary['anchors_present'])}",
        "",
        "Candidate family distribution:",
        "",
        *family_lines,
        "",
        "All rows use fixed rotations `67.5 / 112.5 deg`, `requires_fdtd=true`, and `status=not_evaluated`.",
        "",
        "The `predicted_phase_bin` column is intentionally blank because no surrogate prediction was made.",
        "",
        "Geometry notes: this scaffold uses conservative bounds and fixed fractional positions. Precise gap validation is deferred to the next validation step before any FDTD job.",
    ]
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _candidate_row(
    *,
    candidate_id: str,
    candidate_family: str,
    source: str,
    intended_role: str,
    notes: str,
    p1_length_nm: object,
    p1_width_nm: object,
    p2_length_nm: object,
    p2_width_nm: object,
    p1_frac_x: object,
    p1_frac_y: object,
    p2_frac_x: object,
    p2_frac_y: object,
    internal_dx_nm: object,
    internal_dy_nm: object,
    p1_rotation_deg: object,
    p2_rotation_deg: object,
    period_x_nm: object,
    period_y_nm: object,
    height_nm: object,
    material: object,
    substrate: object,
) -> dict[str, object]:
    row = {
        "candidate_id": candidate_id,
        "candidate_family": candidate_family,
        "source": source,
        "p1_length_nm": _number(p1_length_nm),
        "p1_width_nm": _number(p1_width_nm),
        "p2_length_nm": _number(p2_length_nm),
        "p2_width_nm": _number(p2_width_nm),
        "p1_frac_x": _number(p1_frac_x),
        "p1_frac_y": _number(p1_frac_y),
        "p2_frac_x": _number(p2_frac_x),
        "p2_frac_y": _number(p2_frac_y),
        "internal_dx_nm": _number(internal_dx_nm),
        "internal_dy_nm": _number(internal_dy_nm),
        "p1_rotation_deg": _number(p1_rotation_deg),
        "p2_rotation_deg": _number(p2_rotation_deg),
        "period_x_nm": _number(period_x_nm),
        "period_y_nm": _number(period_y_nm),
        "height_nm": _number(height_nm),
        "material": str(material),
        "substrate": str(substrate),
        "predicted_phase_bin": "",
        "intended_role": intended_role,
        "requires_fdtd": "true",
        "status": "not_evaluated",
        "notes": notes,
    }
    validate_candidate_bounds(row)
    return row


def _geometry_from_dataset_row(row: dict[str, str]) -> dict[str, object]:
    return {key: row[key] for key in BASELINE_VALUES}


def _with_baseline(delta: dict[str, object]) -> dict[str, object]:
    row = dict(BASELINE_VALUES)
    row.update(delta)
    return row


def _deduplicate_candidates(candidates: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    seen_ids: set[str] = set()
    output: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in seen_ids:
            raise ValueError(f"duplicate candidate_id: {candidate_id}")
        seen_ids.add(candidate_id)
        output.append(candidate)
    return output


def _number(value: object) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number


def _to_float(value: object) -> float:
    return float(value)


def _is_number_like(value: object) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
