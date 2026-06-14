from __future__ import annotations

import csv
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan"
PLAN_CSV = OUT_DIR / "j1_identity_plan.csv"
PILOT_CSV = OUT_DIR / "j1_identity_pilot_cases.csv"
SUMMARY_MD = OUT_DIR / "j1_identity_pilot_selection_summary.md"

BASE_SHAPES = ["circle", "square", "regular_hexagon", "regular_octagon"]
ANISO_SHAPES = ["near_square_rect", "near_circle_ellipse"]
HEIGHTS = ["500", "600", "700"]
TARGET_BASE_FEATURE_NM = {
    "circle": 180.0,
    "square": 180.0,
    "regular_hexagon": 190.0,
    "regular_octagon": 190.0,
    "near_square_rect": 180.0,
    "near_circle_ellipse": 180.0,
}

FIELDNAMES = [
    "candidate_id",
    "shape_family",
    "material",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "height_nm",
    "center_x_nm",
    "center_y_nm",
    "diameter_nm",
    "side_nm",
    "length_nm",
    "width_nm",
    "rotation_deg",
    "bbox_x_nm",
    "bbox_y_nm",
    "min_feature_nm",
    "edge_margin_nm",
    "geometry_legal",
    "pilot_reason",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def as_float(text: str) -> float:
    try:
        return float(text)
    except Exception:
        return float("nan")


def legal(row: dict[str, str]) -> bool:
    return row.get("geometry_legal", "").strip().lower() in {"true", "1", "yes"}


def feature_size(row: dict[str, str]) -> float:
    values = [as_float(row.get(name, "")) for name in ["diameter_nm", "side_nm", "length_nm", "width_nm"]]
    return max([v for v in values if v == v], default=0.0)


def choose_nearest(rows: list[dict[str, str]], height: str, shape: str) -> dict[str, str] | None:
    candidates = [
        row
        for row in rows
        if legal(row)
        and row.get("height_nm", "").split(".")[0] == height
        and row.get("shape_family") == shape
        and as_float(row.get("edge_margin_nm", "")) >= 50.0
    ]
    if not candidates:
        return None
    target = TARGET_BASE_FEATURE_NM[shape]
    candidates.sort(
        key=lambda row: (
            abs(feature_size(row) - target),
            -as_float(row.get("edge_margin_nm", "")),
            row.get("candidate_id", ""),
        )
    )
    return candidates[0]


def select_pilot(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(row: dict[str, str] | None, reason: str) -> None:
        if row is None:
            return
        cid = row["candidate_id"]
        if cid in seen or len(selected) >= 24:
            return
        seen.add(cid)
        out = {name: row.get(name, "") for name in FIELDNAMES if name != "pilot_reason"}
        out["pilot_reason"] = reason
        selected.append(out)

    for height in HEIGHTS:
        for shape in BASE_SHAPES:
            add(choose_nearest(rows, height, shape), f"mandatory {shape} coverage at height {height} nm")

    for height in HEIGHTS:
        for shape in ANISO_SHAPES:
            add(choose_nearest(rows, height, shape), f"anisotropy pilot for {shape} at height {height} nm")
            # Add a second nearby anisotropy point when available.
            candidates = [
                row
                for row in rows
                if legal(row)
                and row.get("height_nm", "").split(".")[0] == height
                and row.get("shape_family") == shape
                and row["candidate_id"] not in seen
                and as_float(row.get("edge_margin_nm", "")) >= 50.0
            ]
            candidates.sort(key=lambda row: (-as_float(row.get("edge_margin_nm", "")), row.get("candidate_id", "")))
            add(candidates[0] if candidates else None, f"second anisotropy pilot for {shape} at height {height} nm")

    return selected[:24]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]]) -> None:
    by_height: dict[str, int] = {}
    by_shape: dict[str, int] = {}
    for row in rows:
        by_height[row["height_nm"]] = by_height.get(row["height_nm"], 0) + 1
        by_shape[row["shape_family"]] = by_shape.get(row["shape_family"], 0) + 1
    lines = [
        "# Stage11-1A J1 Identity-Like Pilot Selection",
        "",
        f"pilot_case_count = {len(rows)}",
        "",
        "Selection rules:",
        "- Max 24 cases.",
        "- geometry_legal must be true.",
        "- Edge margin must be >= 50 nm for this pilot.",
        "- Covers heights 500, 600, 700 nm.",
        "- Covers circle, square, regular_hexagon, regular_octagon at every height.",
        "- Adds near_square_rect and near_circle_ellipse representatives to test weak anisotropy.",
        "",
        f"By height: {by_height}",
        f"By shape_family: {by_shape}",
        "",
        "Evidence boundary: this is a static pilot selection only. No Lumerical run is performed by this selector.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not PLAN_CSV.exists():
        raise SystemExit(f"missing required plan: {PLAN_CSV}")
    rows = read_rows(PLAN_CSV)
    pilot = select_pilot(rows)
    write_csv(PILOT_CSV, pilot)
    write_summary(pilot)
    print(f"pilot_case_count={len(pilot)}")
    print(f"output={PILOT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
