from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable, Sequence

from metasurface.apcd_candidate_pool import validate_candidate_bounds


VALIDATION_FIELDS = [
    "candidate_id",
    "candidate_family",
    "same_cell_min_gap_nm",
    "periodic_image_min_gap_nm",
    "minimum_gap_nm_threshold",
    "bounds_pass",
    "same_cell_gap_pass",
    "periodic_gap_pass",
    "beta_selective_geometry_pass",
    "rotation_policy_pass",
    "overall_geometry_pass",
    "recommended_for_fdtd",
    "notes",
]

NEIGHBORHOOD_VALIDATION_FIELDS = [
    "candidate_id",
    "candidate_family",
    "source_reference",
    "same_cell_min_gap_nm",
    "periodic_image_min_gap_nm",
    "minimum_gap_nm_threshold",
    "bounds_pass",
    "same_cell_gap_pass",
    "periodic_gap_pass",
    "beta_selective_geometry_pass",
    "rotation_policy_pass",
    "overall_geometry_pass",
    "recommended_for_fdtd",
    "notes",
]

FINE_VALIDATION_FIELDS = [
    "candidate_id",
    "candidate_family",
    "same_cell_min_gap_nm",
    "periodic_image_min_gap_nm",
    "minimum_gap_nm_threshold",
    "bounds_pass",
    "same_cell_gap_pass",
    "periodic_gap_pass",
    "beta_selective_geometry_pass",
    "rotation_policy_pass",
    "duplicate_geometry_pass",
    "overall_geometry_pass",
    "recommended_for_fdtd",
    "notes",
]

EXISTING_P1W_DX_REFERENCE_GEOMETRIES = {
    # doe_p1w_dx_01
    (130.0, 60.0, 85.0, 150.0, -30.0, 0.0),
    # nhood_p1w_dx_05
    (130.0, 60.0, 85.0, 150.0, -35.0, 0.0),
    # nhood_p1w_dx_02
    (130.0, 55.0, 85.0, 150.0, -30.0, 0.0),
}


Point = tuple[float, float]
Polygon = list[Point]


def rectangle_corners_nm(
    length_nm: float,
    width_nm: float,
    rotation_deg: float,
    center_x_nm: float,
    center_y_nm: float,
) -> Polygon:
    half_l = float(length_nm) / 2.0
    half_w = float(width_nm) / 2.0
    theta = math.radians(float(rotation_deg))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    local = [(-half_l, -half_w), (half_l, -half_w), (half_l, half_w), (-half_l, half_w)]
    return [
        (
            float(center_x_nm) + x * cos_t - y * sin_t,
            float(center_y_nm) + x * sin_t + y * cos_t,
        )
        for x, y in local
    ]


def polygon_min_distance_nm(poly_a: Sequence[Point], poly_b: Sequence[Point]) -> float:
    a = list(poly_a)
    b = list(poly_b)
    if _polygons_overlap(a, b):
        return 0.0
    distances = []
    for segment_a in _segments(a):
        for segment_b in _segments(b):
            distances.append(_segment_distance(segment_a[0], segment_a[1], segment_b[0], segment_b[1]))
    return min(distances)


def estimate_same_cell_gap_nm(candidate: dict[str, object]) -> float:
    p1, p2 = _candidate_polygons(candidate)
    return polygon_min_distance_nm(p1, p2)


def estimate_periodic_image_gap_nm(
    candidate: dict[str, object],
    period_x_nm: float | None = None,
    period_y_nm: float | None = None,
) -> float:
    period_x = float(period_x_nm if period_x_nm is not None else candidate["period_x_nm"])
    period_y = float(period_y_nm if period_y_nm is not None else candidate["period_y_nm"])
    central = _candidate_polygons(candidate)
    shifted_pairs: list[tuple[Polygon, Polygon]] = []
    for i, poly in enumerate(central):
        for j, image in enumerate(central):
            for ix in (-1, 0, 1):
                for iy in (-1, 0, 1):
                    if ix == 0 and iy == 0:
                        continue
                    shifted = _shift_polygon(image, ix * period_x, iy * period_y)
                    shifted_pairs.append((poly, shifted))
    return min(polygon_min_distance_nm(a, b) for a, b in shifted_pairs)


def validate_candidate_geometry(candidate: dict[str, object], minimum_gap_nm: float = 5.0) -> dict[str, object]:
    same_cell_gap = estimate_same_cell_gap_nm(candidate)
    periodic_gap = estimate_periodic_image_gap_nm(candidate)
    bounds_errors = validate_candidate_bounds(candidate, strict=False)
    bounds_pass = not bounds_errors
    same_cell_gap_pass = same_cell_gap >= float(minimum_gap_nm)
    periodic_gap_pass = periodic_gap >= float(minimum_gap_nm)
    beta_selective_geometry_pass = not (
        float(candidate["p2_length_nm"]) == 150.0 and float(candidate["p2_width_nm"]) == 85.0
    )
    rotation_policy_pass = (
        float(candidate["p1_rotation_deg"]) == 67.5 and float(candidate["p2_rotation_deg"]) == 112.5
    )
    overall = (
        bounds_pass
        and same_cell_gap_pass
        and periodic_gap_pass
        and beta_selective_geometry_pass
        and rotation_policy_pass
    )
    notes = []
    if bounds_errors:
        notes.extend(bounds_errors)
    if not same_cell_gap_pass:
        notes.append("same-cell gap below threshold")
    if not periodic_gap_pass:
        notes.append("periodic-image gap below threshold")
    if not beta_selective_geometry_pass:
        notes.append("beta-selective p2 geometry 150 x 85 nm is not allowed")
    if not rotation_policy_pass:
        notes.append("rotation policy changed from 67.5 / 112.5 deg")
    if not notes:
        notes.append("geometry sanity validation passed; optical response still unknown")

    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_family": candidate["candidate_family"],
        "same_cell_min_gap_nm": same_cell_gap,
        "periodic_image_min_gap_nm": periodic_gap,
        "minimum_gap_nm_threshold": float(minimum_gap_nm),
        "bounds_pass": bounds_pass,
        "same_cell_gap_pass": same_cell_gap_pass,
        "periodic_gap_pass": periodic_gap_pass,
        "beta_selective_geometry_pass": beta_selective_geometry_pass,
        "rotation_policy_pass": rotation_policy_pass,
        "overall_geometry_pass": overall,
        "recommended_for_fdtd": overall,
        "notes": "; ".join(notes),
    }


def validate_candidate_pool(
    candidates: Iterable[dict[str, object]],
    minimum_gap_nm: float = 5.0,
) -> list[dict[str, object]]:
    return [validate_candidate_geometry(candidate, minimum_gap_nm=minimum_gap_nm) for candidate in candidates]


def validate_neighborhood_candidate_pool(
    candidates: Iterable[dict[str, object]],
    minimum_gap_nm: float = 5.0,
) -> list[dict[str, object]]:
    rows = []
    for candidate in candidates:
        row = validate_candidate_geometry(candidate, minimum_gap_nm=minimum_gap_nm)
        row["source_reference"] = candidate.get("source_reference", "")
        rows.append(row)
    return rows


def validate_fine_candidate_geometry(
    candidate: dict[str, object],
    *,
    duplicate_geometry_pass: bool = True,
    minimum_gap_nm: float = 5.0,
) -> dict[str, object]:
    row = validate_candidate_geometry(candidate, minimum_gap_nm=minimum_gap_nm)
    notes = [] if row["notes"] == "geometry sanity validation passed; optical response still unknown" else [row["notes"]]
    row["duplicate_geometry_pass"] = duplicate_geometry_pass
    row["overall_geometry_pass"] = bool(row["overall_geometry_pass"] and duplicate_geometry_pass)
    row["recommended_for_fdtd"] = row["overall_geometry_pass"]
    if not duplicate_geometry_pass:
        notes.append("duplicates existing p1w_dx reference geometry")
    if not notes:
        notes.append("geometry sanity validation passed; duplicate check passed; optical response still unknown")
    row["notes"] = "; ".join(notes)
    return row


def validate_fine_candidate_pool(
    candidates: Iterable[dict[str, object]],
    minimum_gap_nm: float = 5.0,
    existing_geometries: Iterable[tuple[float, float, float, float, float, float]] = EXISTING_P1W_DX_REFERENCE_GEOMETRIES,
) -> list[dict[str, object]]:
    existing = set(existing_geometries)
    seen: set[tuple[float, float, float, float, float, float]] = set()
    rows = []
    for candidate in candidates:
        key = _geometry_key(candidate)
        duplicate_pass = key not in existing and key not in seen
        rows.append(
            validate_fine_candidate_geometry(
                candidate,
                duplicate_geometry_pass=duplicate_pass,
                minimum_gap_nm=minimum_gap_nm,
            )
        )
        seen.add(key)
    return rows


def export_candidate_validation_csv(rows: Iterable[dict[str, object]], path: str | Path) -> Path:
    row_list = list(rows)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VALIDATION_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in VALIDATION_FIELDS} for row in row_list)
    return output_path


def export_neighborhood_candidate_validation_csv(rows: Iterable[dict[str, object]], path: str | Path) -> Path:
    row_list = list(rows)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=NEIGHBORHOOD_VALIDATION_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in NEIGHBORHOOD_VALIDATION_FIELDS} for row in row_list)
    return output_path


def export_fine_candidate_validation_csv(rows: Iterable[dict[str, object]], path: str | Path) -> Path:
    row_list = list(rows)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINE_VALIDATION_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in FINE_VALIDATION_FIELDS} for row in row_list)
    return output_path


def read_candidate_pool_csv(path: str | Path) -> list[dict[str, object]]:
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize_validation(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    pass_rows = [row for row in rows if _is_true(row["overall_geometry_pass"])]
    recommended = [row for row in rows if _is_true(row["recommended_for_fdtd"])]
    fail_rows = [row for row in rows if not _is_true(row["overall_geometry_pass"])]
    anchors = ["baseline", "p1W_m5", "p2W_p10", "p1L_m10", "p1L_m5", "p1L_p5"]
    anchor_status = {
        anchor: next((bool(_is_true(row["overall_geometry_pass"])) for row in rows if row["candidate_id"] == anchor), False)
        for anchor in anchors
    }
    reason_counts: dict[str, int] = {}
    for row in fail_rows:
        for reason in str(row["notes"]).split("; "):
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "total": total,
        "geometry_pass_count": len(pass_rows),
        "fail_count": len(fail_rows),
        "recommended_for_fdtd_count": len(recommended),
        "anchor_status": anchor_status,
        "fail_reason_counts": dict(sorted(reason_counts.items())),
    }


def summarize_neighborhood_validation(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    pass_rows = [row for row in rows if _is_true(row["overall_geometry_pass"])]
    recommended = [row for row in rows if _is_true(row["recommended_for_fdtd"])]
    fail_rows = [row for row in rows if not _is_true(row["overall_geometry_pass"])]
    family_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        family = str(row["candidate_family"])
        if family not in family_counts:
            family_counts[family] = {"total": 0, "pass": 0, "fail": 0, "recommended": 0}
        family_counts[family]["total"] += 1
        if _is_true(row["overall_geometry_pass"]):
            family_counts[family]["pass"] += 1
        else:
            family_counts[family]["fail"] += 1
        if _is_true(row["recommended_for_fdtd"]):
            family_counts[family]["recommended"] += 1

    fail_reason_counts: dict[str, int] = {}
    for row in fail_rows:
        for reason in str(row["notes"]).split("; "):
            fail_reason_counts[reason] = fail_reason_counts.get(reason, 0) + 1

    same_cell_gaps = [float(row["same_cell_min_gap_nm"]) for row in rows]
    periodic_gaps = [float(row["periodic_image_min_gap_nm"]) for row in rows]
    return {
        "total": total,
        "geometry_pass_count": len(pass_rows),
        "fail_count": len(fail_rows),
        "recommended_for_fdtd_count": len(recommended),
        "minimum_same_cell_gap_nm": min(same_cell_gaps) if same_cell_gaps else None,
        "minimum_periodic_image_gap_nm": min(periodic_gaps) if periodic_gaps else None,
        "family_counts": dict(sorted(family_counts.items())),
        "fail_reason_counts": dict(sorted(fail_reason_counts.items())),
    }


def summarize_fine_validation(rows: Sequence[dict[str, object]]) -> dict[str, object]:
    total = len(rows)
    pass_rows = [row for row in rows if _is_true(row["overall_geometry_pass"])]
    recommended = [row for row in rows if _is_true(row["recommended_for_fdtd"])]
    fail_rows = [row for row in rows if not _is_true(row["overall_geometry_pass"])]
    duplicate_fail_rows = [row for row in rows if not _is_true(row["duplicate_geometry_pass"])]
    family_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        family = str(row["candidate_family"])
        if family not in family_counts:
            family_counts[family] = {"total": 0, "pass": 0, "fail": 0, "recommended": 0}
        family_counts[family]["total"] += 1
        if _is_true(row["overall_geometry_pass"]):
            family_counts[family]["pass"] += 1
        else:
            family_counts[family]["fail"] += 1
        if _is_true(row["recommended_for_fdtd"]):
            family_counts[family]["recommended"] += 1

    fail_reason_counts: dict[str, int] = {}
    for row in fail_rows:
        for reason in str(row["notes"]).split("; "):
            fail_reason_counts[reason] = fail_reason_counts.get(reason, 0) + 1

    same_cell_gaps = [float(row["same_cell_min_gap_nm"]) for row in rows]
    periodic_gaps = [float(row["periodic_image_min_gap_nm"]) for row in rows]
    return {
        "total": total,
        "geometry_pass_count": len(pass_rows),
        "fail_count": len(fail_rows),
        "recommended_for_fdtd_count": len(recommended),
        "minimum_same_cell_gap_nm": min(same_cell_gaps) if same_cell_gaps else None,
        "minimum_periodic_image_gap_nm": min(periodic_gaps) if periodic_gaps else None,
        "duplicate_geometry_pass_count": total - len(duplicate_fail_rows),
        "duplicate_geometry_fail_count": len(duplicate_fail_rows),
        "family_counts": dict(sorted(family_counts.items())),
        "fail_reason_counts": dict(sorted(fail_reason_counts.items())),
    }


def _candidate_polygons(candidate: dict[str, object]) -> tuple[Polygon, Polygon]:
    period_x = float(candidate["period_x_nm"])
    period_y = float(candidate["period_y_nm"])
    p1_center_x, p1_center_y, p2_center_x, p2_center_y = _candidate_centers(candidate, period_x, period_y)
    p1 = rectangle_corners_nm(
        length_nm=float(candidate["p1_length_nm"]),
        width_nm=float(candidate["p1_width_nm"]),
        rotation_deg=float(candidate["p1_rotation_deg"]),
        center_x_nm=p1_center_x,
        center_y_nm=p1_center_y,
    )
    p2 = rectangle_corners_nm(
        length_nm=float(candidate["p2_length_nm"]),
        width_nm=float(candidate["p2_width_nm"]),
        rotation_deg=float(candidate["p2_rotation_deg"]),
        center_x_nm=p2_center_x,
        center_y_nm=p2_center_y,
    )
    return p1, p2


def _candidate_centers(
    candidate: dict[str, object],
    period_x_nm: float,
    period_y_nm: float,
) -> tuple[float, float, float, float]:
    internal_dx = float(candidate.get("internal_dx_nm", 0.0))
    internal_dy = float(candidate.get("internal_dy_nm", 0.0))
    p1_center_x = (float(candidate["p1_frac_x"]) - 0.5) * period_x_nm + internal_dx / 2.0
    p1_center_y = (float(candidate["p1_frac_y"]) - 0.5) * period_y_nm + internal_dy / 2.0
    p2_center_x = (float(candidate["p2_frac_x"]) - 0.5) * period_x_nm - internal_dx / 2.0
    p2_center_y = (float(candidate["p2_frac_y"]) - 0.5) * period_y_nm - internal_dy / 2.0
    return p1_center_x, p1_center_y, p2_center_x, p2_center_y


def _polygons_overlap(poly_a: Polygon, poly_b: Polygon) -> bool:
    for seg_a in _segments(poly_a):
        for seg_b in _segments(poly_b):
            if _segments_intersect(seg_a[0], seg_a[1], seg_b[0], seg_b[1]):
                return True
    return _point_in_polygon(poly_a[0], poly_b) or _point_in_polygon(poly_b[0], poly_a)


def _segments(poly: Polygon) -> list[tuple[Point, Point]]:
    return [(poly[index], poly[(index + 1) % len(poly)]) for index in range(len(poly))]


def _segment_distance(a: Point, b: Point, c: Point, d: Point) -> float:
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(
        _point_segment_distance(a, c, d),
        _point_segment_distance(b, c, d),
        _point_segment_distance(c, a, b),
        _point_segment_distance(d, a, b),
    )


def _point_segment_distance(point: Point, start: Point, end: Point) -> float:
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - sx, py - sy)
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    closest_x = sx + t * dx
    closest_y = sy + t * dy
    return math.hypot(px - closest_x, py - closest_y)


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    eps = 1.0e-12
    return (
        abs(o1) <= eps and _on_segment(a, c, b)
        or abs(o2) <= eps and _on_segment(a, d, b)
        or abs(o3) <= eps and _on_segment(c, a, d)
        or abs(o4) <= eps and _on_segment(c, b, d)
    )


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return (
        min(a[0], c[0]) - 1.0e-12 <= b[0] <= max(a[0], c[0]) + 1.0e-12
        and min(a[1], c[1]) - 1.0e-12 <= b[1] <= max(a[1], c[1]) + 1.0e-12
    )


def _point_in_polygon(point: Point, polygon: Polygon) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersects = (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def _shift_polygon(poly: Polygon, dx: float, dy: float) -> Polygon:
    return [(x + dx, y + dy) for x, y in poly]


def _is_true(value: object) -> bool:
    return value is True or str(value) == "True"


def _geometry_key(candidate: dict[str, object]) -> tuple[float, float, float, float, float, float]:
    return (
        float(candidate["p1_length_nm"]),
        float(candidate["p1_width_nm"]),
        float(candidate["p2_length_nm"]),
        float(candidate["p2_width_nm"]),
        float(candidate.get("internal_dx_nm", 0.0)),
        float(candidate.get("internal_dy_nm", 0.0)),
    )
