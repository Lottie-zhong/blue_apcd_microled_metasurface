from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_2a_h500_dimer_validation"

LIB_CSV = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure" / "lp_h500_best_6bin_library_stage11_1e.csv"
PAIR_CSV = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure" / "lp_pair_candidates_h500_stage11_1e_merged_reranked.csv"

GEOM_FILES = [
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_plan.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j1_identity_patch_plan_stage11_1d.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure" / "h500_j1_gap_closure_plan_stage11_1e.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_plan.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j2_hwp_patch_plan_stage11_1d.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure" / "h500_j2_gap_closure_plan_stage11_1e.csv",
]

PLAN_CSV = OUT_DIR / "h500_dimer_validation_plan_stage11_2a.csv"
SUMMARY_MD = OUT_DIR / "h500_dimer_validation_plan_summary_stage11_2a.md"
PREVIEW_PNG = OUT_DIR / "h500_dimer_layout_preview_stage11_2a.png"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
LAMBDA_NM = 450.0
PX_NM = 431.907786
PY_NM = 432.0
HEIGHT_NM = 500.0
MIN_GAP_NM = 20.0
MIN_EDGE_NM = 10.0

FIELDS = [
    "dimer_case_id", "bin_deg", "source_pair_id", "j1_candidate_id", "j2_candidate_id", "height_nm",
    "lambda_nm", "p_x_nm", "p_y_nm", "j1_shape_family", "j1_geometry_params", "j2_length_nm",
    "j2_width_nm", "j2_rotation_deg", "placement_type", "j1_center_x_nm", "j1_center_y_nm",
    "j2_center_x_nm", "j2_center_y_nm", "dimer_gap_nm", "edge_margin_nm", "geometry_legal",
    "static_predicted_ratio", "static_phase_error_deg", "static_output_phase_deg", "static_target_x_power",
    "static_leak_y_power", "priority", "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def f(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def geom_map() -> dict[str, dict[str, str]]:
    out = {}
    for path in GEOM_FILES:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if cid:
                out[cid] = row
    return out


def bbox_for_j1(row: dict[str, str]) -> tuple[float, float, dict[str, float | str]]:
    shape = row.get("shape_family", "")
    if shape == "circle":
        d = f(row.get("diameter_nm"))
        return d, d, {"diameter_nm": d}
    if shape == "square":
        s = f(row.get("side_nm"))
        return s, s, {"side_nm": s}
    L = f(row.get("length_nm"))
    W = f(row.get("width_nm"))
    return L, W, {"length_nm": L, "width_nm": W, "rotation_deg": f(row.get("rotation_deg"), 0.0)}


def bbox_for_j2(row: dict[str, str]) -> tuple[float, float, dict[str, float]]:
    L = f(row.get("length_nm"))
    W = f(row.get("width_nm"))
    return L, W, {"length_nm": L, "width_nm": W, "rotation_deg": f(row.get("rotation_deg"), 0.0)}


def overlap_gap(cx1: float, cy1: float, bx1: float, by1: float, cx2: float, cy2: float, bx2: float, by2: float) -> float:
    dx = abs(cx2 - cx1) - (bx1 + bx2) / 2.0
    dy = abs(cy2 - cy1) - (by1 + by2) / 2.0
    if dx >= 0 and dy >= 0:
        return math.hypot(dx, dy)
    if dx >= 0:
        return dx
    if dy >= 0:
        return dy
    return -min(-dx, -dy)


def edge_margin(cx1: float, cy1: float, bx1: float, by1: float, cx2: float, cy2: float, bx2: float, by2: float) -> float:
    return min(
        PX_NM / 2 - max(abs(cx1) + bx1 / 2, abs(cx2) + bx2 / 2),
        PY_NM / 2 - max(abs(cy1) + by1 / 2, abs(cy2) + by2 / 2),
    )


def placement_options(bx1: float, by1: float, bx2: float, by2: float) -> list[dict[str, float | str | bool]]:
    options = []
    trials = []
    sep_x = (bx1 + bx2) / 2 + MIN_GAP_NM
    trials.append(("x_pair", -sep_x / 2, 0.0, sep_x / 2, 0.0))
    sep_y = (by1 + by2) / 2 + MIN_GAP_NM
    trials.append(("y_pair", 0.0, -sep_y / 2, 0.0, sep_y / 2))
    diag_sep_x = (bx1 + bx2) / 2 + MIN_GAP_NM / math.sqrt(2)
    diag_sep_y = (by1 + by2) / 2 + MIN_GAP_NM / math.sqrt(2)
    trials.append(("diag_pair", -diag_sep_x / 2, -diag_sep_y / 2, diag_sep_x / 2, diag_sep_y / 2))
    for name, x1, y1, x2, y2 in trials:
        gap = overlap_gap(x1, y1, bx1, by1, x2, y2, bx2, by2)
        edge = edge_margin(x1, y1, bx1, by1, x2, y2, bx2, by2)
        legal = gap >= MIN_GAP_NM - 1e-6 and edge >= MIN_EDGE_NM - 1e-6
        options.append(
            {
                "placement_type": name,
                "j1_center_x_nm": x1,
                "j1_center_y_nm": y1,
                "j2_center_x_nm": x2,
                "j2_center_y_nm": y2,
                "dimer_gap_nm": gap,
                "edge_margin_nm": edge,
                "geometry_legal": legal,
            }
        )
    options.sort(key=lambda o: (not bool(o["geometry_legal"]), -float(o["edge_margin_nm"]), -float(o["dimer_gap_nm"])))
    return options


def pair_sort_key(row: dict[str, str]) -> tuple:
    return (
        0 if row.get("pair_quality") == "strong_fab_candidate" else 1,
        f(row.get("phase_error_deg")),
        -f(row.get("predicted_ratio")),
        -f(row.get("target_x_power")),
        f(row.get("s1_s2_phase_mismatch_deg")),
        abs(1.0 - f(row.get("s1_s2_amp_ratio"))),
    )


def make_plan() -> tuple[list[dict[str, str]], list[str]]:
    geom = geom_map()
    lib_rows = read_csv(LIB_CSV)
    all_pairs = [r for r in read_csv(PAIR_CSV) if r.get("pair_quality") == "strong_fab_candidate"]
    infeasible_notes = []
    selected: list[dict[str, str]] = []
    seen_pairs = set()

    primary_ids = {r["pair_id"] for r in lib_rows}
    for bin_deg in PHASE_BINS:
        candidates = [r for r in all_pairs if int(f(r.get("target_phase_bin_deg"))) == bin_deg]
        candidates.sort(key=pair_sort_key)
        primary = [r for r in lib_rows if int(f(r.get("bin_deg"))) == bin_deg]
        by_pair = {r["pair_id"]: r for r in all_pairs}
        ordered = []
        for r in primary:
            if r["pair_id"] in by_pair:
                ordered.append(by_pair[r["pair_id"]])
        ordered += [r for r in candidates if r["pair_id"] not in {x["pair_id"] for x in ordered}]
        legal_count_for_bin = 0
        target_count = 3 if bin_deg in {60, 120} else 2
        for pair in ordered:
            if pair["pair_id"] in seen_pairs:
                continue
            row = build_plan_row(pair, geom, primary=pair["pair_id"] in primary_ids)
            if row["geometry_legal"] == "true":
                selected.append(row)
                seen_pairs.add(pair["pair_id"])
                legal_count_for_bin += 1
            elif pair["pair_id"] in primary_ids:
                infeasible_notes.append(f"primary {pair['pair_id']} bin {bin_deg}: {row['notes']}")
            if legal_count_for_bin >= target_count:
                break
        if legal_count_for_bin == 0:
            # Keep the best infeasible primary/candidate as evidence.
            for pair in ordered[:1]:
                if pair["pair_id"] not in seen_pairs:
                    selected.append(build_plan_row(pair, geom, primary=pair["pair_id"] in primary_ids))
                    seen_pairs.add(pair["pair_id"])
    selected = selected[:12]
    for i, row in enumerate(selected, start=1):
        row["dimer_case_id"] = f"H500DIMER2A_{i:03d}_B{row['bin_deg']}_{row['placement_type']}"
    return selected, infeasible_notes


def build_plan_row(pair: dict[str, str], geom: dict[str, dict[str, str]], primary: bool) -> dict[str, str]:
    j1_id = pair["j1_candidate_id"]
    j2_id = pair["j2_candidate_id"]
    j1 = geom.get(j1_id, {})
    j2 = geom.get(j2_id, {})
    bx1, by1, j1_params = bbox_for_j1(j1)
    bx2, by2, j2_params = bbox_for_j2(j2)
    if any(math.isnan(v) for v in [bx1, by1, bx2, by2]):
        opt = {"placement_type": "infeasible_in_single_dimer_cell", "j1_center_x_nm": math.nan, "j1_center_y_nm": math.nan, "j2_center_x_nm": math.nan, "j2_center_y_nm": math.nan, "dimer_gap_nm": math.nan, "edge_margin_nm": math.nan, "geometry_legal": False}
        note = "missing geometry parameters"
    else:
        opt = placement_options(bx1, by1, bx2, by2)[0]
        note = "primary static-library pair" if primary else "backup strong static pair"
        if not opt["geometry_legal"]:
            note = "infeasible_in_single_dimer_cell: gap or edge margin below threshold"
    return {
        "dimer_case_id": "",
        "bin_deg": str(int(f(pair.get("target_phase_bin_deg", pair.get("bin_deg"))))),
        "source_pair_id": pair["pair_id"],
        "j1_candidate_id": j1_id,
        "j2_candidate_id": j2_id,
        "height_nm": fmt(HEIGHT_NM),
        "lambda_nm": fmt(LAMBDA_NM),
        "p_x_nm": fmt(PX_NM),
        "p_y_nm": fmt(PY_NM),
        "j1_shape_family": j1.get("shape_family", ""),
        "j1_geometry_params": json.dumps(j1_params, sort_keys=True),
        "j2_length_nm": fmt(j2_params.get("length_nm", math.nan)),
        "j2_width_nm": fmt(j2_params.get("width_nm", math.nan)),
        "j2_rotation_deg": fmt(j2_params.get("rotation_deg", 0.0)),
        "placement_type": str(opt["placement_type"]),
        "j1_center_x_nm": fmt(float(opt["j1_center_x_nm"])),
        "j1_center_y_nm": fmt(float(opt["j1_center_y_nm"])),
        "j2_center_x_nm": fmt(float(opt["j2_center_x_nm"])),
        "j2_center_y_nm": fmt(float(opt["j2_center_y_nm"])),
        "dimer_gap_nm": fmt(float(opt["dimer_gap_nm"])),
        "edge_margin_nm": fmt(float(opt["edge_margin_nm"])),
        "geometry_legal": "true" if opt["geometry_legal"] else "false",
        "static_predicted_ratio": pair.get("predicted_ratio", ""),
        "static_phase_error_deg": pair.get("phase_error_deg", ""),
        "static_output_phase_deg": pair.get("output_phase_deg", ""),
        "static_target_x_power": pair.get("target_x_power", ""),
        "static_leak_y_power": pair.get("leak_y_power", ""),
        "priority": "primary" if primary else "backup",
        "notes": note,
    }


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_preview(rows: list[dict[str, str]]) -> None:
    w, h = 1000, 760
    pix = bytearray([255, 255, 255] * w * h)
    def setpx(x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = 3 * (y * w + x); pix[i:i+3] = bytes(c)
    def rect(x0: int, y0: int, x1: int, y1: int, c: tuple[int, int, int], fill: bool) -> None:
        for yy in range(max(0, y0), min(h, y1)):
            for xx in range(max(0, x0), min(w, x1)):
                if fill or xx in (x0, x1-1) or yy in (y0, y1-1): setpx(xx, yy, c)
    def ellipse(cx: int, cy: int, rx: int, ry: int, c: tuple[int, int, int]) -> None:
        for yy in range(cy-ry, cy+ry+1):
            for xx in range(cx-rx, cx+rx+1):
                if ((xx-cx)/max(rx,1))**2 + ((yy-cy)/max(ry,1))**2 <= 1: setpx(xx, yy, c)
    for i, r in enumerate(rows[:12]):
        x0 = 45 + (i % 4) * 235
        y0 = 45 + (i // 4) * 220
        rect(x0, y0, x0+155, y0+155, (60, 60, 60), False)
        if r["geometry_legal"] != "true":
            continue
        scale = 0.25
        cx1 = x0 + 77 + int(f(r["j1_center_x_nm"]) * scale)
        cy1 = y0 + 77 - int(f(r["j1_center_y_nm"]) * scale)
        cx2 = x0 + 77 + int(f(r["j2_center_x_nm"]) * scale)
        cy2 = y0 + 77 - int(f(r["j2_center_y_nm"]) * scale)
        p = json.loads(r["j1_geometry_params"])
        if r["j1_shape_family"] == "circle":
            d = int(f(p.get("diameter_nm")) * scale)
            ellipse(cx1, cy1, d//2, d//2, (70, 130, 210))
        else:
            bx = int((f(p.get("side_nm")) if "side_nm" in p else f(p.get("length_nm"))) * scale)
            by = int((f(p.get("side_nm")) if "side_nm" in p else f(p.get("width_nm"))) * scale)
            rect(cx1-bx//2, cy1-by//2, cx1+bx//2, cy1+by//2, (80, 170, 120), True)
        bx2 = int(f(r["j2_length_nm"]) * scale); by2 = int(f(r["j2_width_nm"]) * scale)
        rect(cx2-bx2//2, cy2-by2//2, cx2+bx2//2, cy2+by2//2, (220, 110, 70), True)
    raw = b"".join(b"\x00" + bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    PREVIEW_PNG.write_bytes(data)


def write_summary(rows: list[dict[str, str]], infeasible_notes: list[str]) -> None:
    legal = [r for r in rows if r["geometry_legal"] == "true"]
    covered = sorted({int(r["bin_deg"]) for r in legal})
    lines = [
        "# Stage11-2A H500 Dimer Validation Plan",
        "",
        "Boundary: Stage11-1E produced a H500-only 6-bin strong static Jones/phasor library. This is not yet dimer verified, not K=6 steering, and not LP steering completed.",
        "",
        f"dimer_plan_case_count = {len(rows)}",
        f"geometry_legal_count = {len(legal)}",
        f"infeasible_count = {len(rows) - len(legal)}",
        f"bins_covered_by_legal_dimers = {covered}",
        "",
        "This planner only creates H500 single-dimer validation cases. No K=6 full FDTD or phase-gradient supercell is generated.",
        "",
        "## Infeasible primary notes",
    ]
    lines += [f"- {x}" for x in infeasible_notes] if infeasible_notes else ["- none"]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not LIB_CSV.exists():
        raise SystemExit(f"missing required input: {LIB_CSV}")
    if not PAIR_CSV.exists():
        raise SystemExit(f"missing required input: {PAIR_CSV}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows, infeasible = make_plan()
    write_csv(PLAN_CSV, rows, FIELDS)
    write_summary(rows, infeasible)
    write_preview(rows)
    legal = [r for r in rows if r["geometry_legal"] == "true"]
    print(f"dimer_plan_case_count={len(rows)}")
    print(f"geometry_legal_count={len(legal)}")
    print(f"infeasible_count={len(rows)-len(legal)}")
    print("bins_covered_by_legal_dimers=" + ",".join(str(x) for x in sorted({int(r["bin_deg"]) for r in legal})))
    if infeasible:
        print("infeasible_pairs=" + " | ".join(infeasible))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
