from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence


SELECTED_BATCH_FIELDS = [
    "batch_id",
    "candidate_id",
    "candidate_family",
    "selection_reason",
    "p1_length_nm",
    "p1_width_nm",
    "p2_length_nm",
    "p2_width_nm",
    "internal_dx_nm",
    "internal_dy_nm",
    "p1_rotation_deg",
    "p2_rotation_deg",
    "geometry_pass",
    "recommended_for_fdtd",
    "requires_fdtd",
    "status",
    "notes",
]

PREFERRED_FAMILY_ORDER = [
    "p1w_p2w_combo",
    "p1l_p1w_combo",
    "p1w_internal_dx_combo",
    "p2w_internal_dy_combo",
    "p1l_p2w_combo",
    "p1w_p2w_internal_dx_combo",
    "lhs_like_mixed_combo",
]

PREFERRED_CANDIDATE_IDS = [
    "doe_p1w_p2w_02",
    "doe_p1l_p1w_04",
    "doe_p1w_dx_01",
    "doe_p2w_dy_04",
    "doe_p1l_p2w_01",
    "doe_p1w_p2w_dx_02",
    "doe_lhs_like_01",
    "doe_lhs_like_02",
]


def load_candidate_pool(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_geometry_validation(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return {row["candidate_id"]: row for row in csv.DictReader(handle)}


def filter_geometry_pass_candidates(
    candidates: Iterable[dict[str, str]],
    validation_by_id: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    output = []
    for candidate in candidates:
        candidate_id = candidate["candidate_id"]
        validation = validation_by_id.get(candidate_id, {})
        if (
            candidate_id != "baseline"
            and validation.get("overall_geometry_pass") == "True"
            and validation.get("recommended_for_fdtd") == "True"
        ):
            output.append({**candidate, **_validation_fields(validation)})
    return output


def score_candidate_diversity_rule_based(candidate: dict[str, str]) -> tuple[int, int, int, int, str]:
    family = candidate["candidate_family"]
    family_rank = PREFERRED_FAMILY_ORDER.index(family) if family in PREFERRED_FAMILY_ORDER else 99
    candidate_rank = PREFERRED_CANDIDATE_IDS.index(candidate["candidate_id"]) if candidate["candidate_id"] in PREFERRED_CANDIDATE_IDS else 99
    changed_count = sum(
        1
        for key, baseline in {
            "p1_length_nm": 130.0,
            "p1_width_nm": 70.0,
            "p2_length_nm": 85.0,
            "p2_width_nm": 150.0,
            "internal_dx_nm": 0.0,
            "internal_dy_nm": 0.0,
        }.items()
        if float(candidate[key]) != baseline
    )
    displacement_bonus = int(float(candidate["internal_dx_nm"]) != 0.0) + int(float(candidate["internal_dy_nm"]) != 0.0)
    return (family_rank, candidate_rank, -changed_count, -displacement_bonus, candidate["candidate_id"])


def select_first_fdtd_batch(
    candidates: Iterable[dict[str, str]],
    validation_by_id: dict[str, dict[str, str]],
    *,
    batch_size: int = 8,
) -> list[dict[str, object]]:
    if not 6 <= batch_size <= 10:
        raise ValueError("batch_size should stay within the requested 6-10 range")
    eligible = filter_geometry_pass_candidates(candidates, validation_by_id)
    by_id = {candidate["candidate_id"]: candidate for candidate in eligible}
    selected: list[dict[str, str]] = []

    for candidate_id in PREFERRED_CANDIDATE_IDS:
        if candidate_id in by_id and len(selected) < batch_size:
            selected.append(by_id[candidate_id])

    if len(selected) < batch_size:
        selected_ids = {candidate["candidate_id"] for candidate in selected}
        remaining = [candidate for candidate in eligible if candidate["candidate_id"] not in selected_ids]
        remaining.sort(key=score_candidate_diversity_rule_based)
        selected.extend(remaining[: batch_size - len(selected)])

    return [_selected_row(index, candidate) for index, candidate in enumerate(selected[:batch_size], start=1)]


def export_selected_batch_csv(rows: Iterable[dict[str, object]], path: str | Path) -> Path:
    row_list = list(rows)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SELECTED_BATCH_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in SELECTED_BATCH_FIELDS} for row in row_list)
    return output_path


def summarize_selected_batch(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    families = Counter(str(row["candidate_family"]) for row in rows)
    ids = [str(row["candidate_id"]) for row in rows]
    dx_values = [float(row["internal_dx_nm"]) for row in rows]
    dy_values = [float(row["internal_dy_nm"]) for row in rows]
    return {
        "selected_count": len(rows),
        "selected_candidate_ids": ids,
        "family_counts": dict(sorted(families.items())),
        "unique_candidate_ids": len(set(ids)) == len(ids),
        "has_negative_internal_dx": any(value < 0 for value in dx_values),
        "has_positive_internal_dx": any(value > 0 for value in dx_values),
        "has_negative_internal_dy": any(value < 0 for value in dy_values),
        "has_positive_internal_dy": any(value > 0 for value in dy_values),
        "status_values": sorted({str(row["status"]) for row in rows}),
    }


def write_selected_batch_summary(path: str | Path, rows: Sequence[dict[str, object]]) -> Path:
    summary = summarize_selected_batch(rows)
    family_lines = [f"- `{family}`: {count}" for family, count in summary["family_counts"].items()]
    selected_lines = [f"- `{row['candidate_id']}`: {row['selection_reason']}" for row in rows]
    lines = [
        "# APCD K=6 First FDTD Batch v0 Summary",
        "",
        "Scope: 09-P4 rule-based selection only. No FDTD run was performed. No lumapi call was made. No `.fsp` file was exported. No model was trained. No surrogate prediction was generated. This is not a steering result.",
        "",
        f"Selected count: {summary['selected_count']}",
        f"Unique candidate IDs: {summary['unique_candidate_ids']}",
        f"Status values: {', '.join(summary['status_values'])}",
        "",
        "Selected candidates:",
        "",
        *selected_lines,
        "",
        "Candidate family distribution:",
        "",
        *family_lines,
        "",
        "Diversity checks:",
        "",
        f"- negative internal_dx covered: {summary['has_negative_internal_dx']}",
        f"- positive internal_dx covered: {summary['has_positive_internal_dx']}",
        f"- negative internal_dy covered: {summary['has_negative_internal_dy']}",
        f"- positive internal_dy covered: {summary['has_positive_internal_dy']}",
        "",
        "All selected rows came from geometry-passing `recommended_for_fdtd=true` candidates. Baseline is excluded because it already has a real result.",
    ]
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _validation_fields(validation: dict[str, str]) -> dict[str, str]:
    return {
        "geometry_pass": validation.get("overall_geometry_pass", ""),
        "recommended_for_fdtd": validation.get("recommended_for_fdtd", ""),
    }


def _selected_row(index: int, candidate: dict[str, str]) -> dict[str, object]:
    return {
        "batch_id": f"batch01_{index:02d}",
        "candidate_id": candidate["candidate_id"],
        "candidate_family": candidate["candidate_family"],
        "selection_reason": _selection_reason(candidate),
        "p1_length_nm": _number(candidate["p1_length_nm"]),
        "p1_width_nm": _number(candidate["p1_width_nm"]),
        "p2_length_nm": _number(candidate["p2_length_nm"]),
        "p2_width_nm": _number(candidate["p2_width_nm"]),
        "internal_dx_nm": _number(candidate["internal_dx_nm"]),
        "internal_dy_nm": _number(candidate["internal_dy_nm"]),
        "p1_rotation_deg": _number(candidate["p1_rotation_deg"]),
        "p2_rotation_deg": _number(candidate["p2_rotation_deg"]),
        "geometry_pass": candidate["geometry_pass"],
        "recommended_for_fdtd": candidate["recommended_for_fdtd"],
        "requires_fdtd": candidate["requires_fdtd"],
        "status": "selected_not_run",
        "notes": "09-P4 selected by rule-based diversity; no surrogate prediction; no FDTD run yet",
    }


def _selection_reason(candidate: dict[str, str]) -> str:
    family = candidate["candidate_family"]
    role = {
        "p1w_p2w_combo": "width-width combined perturbation to test p1/p2 width interaction",
        "p1l_p1w_combo": "p1 length-width interaction with positive length and negative width perturbation",
        "p1w_internal_dx_combo": "p1 width plus negative internal_dx displacement",
        "p2w_internal_dy_combo": "p2 width plus positive internal_dy displacement",
        "p1l_p2w_combo": "p1 length plus p2 width interaction",
        "p1w_p2w_internal_dx_combo": "three-knob width-width-internal_dx interaction",
        "lhs_like_mixed_combo": "LHS-like mixed geometry/displacement diversity point",
    }
    return role.get(family, "rule-based diversity selection")


def _number(value: object) -> int | float:
    number = float(value)
    return int(number) if number.is_integer() else number
