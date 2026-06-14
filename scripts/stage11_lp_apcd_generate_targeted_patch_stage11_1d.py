from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch"
J1_IN = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_fdtd_results_pilot.csv"
J2_IN = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"
RECS_IN = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing" / "lp_targeted_scan_recommendations_stage11_1c.csv"
PAIR_1C_IN = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing" / "lp_pair_candidates_stage11_1c_reranked.csv"

J1_PLAN = OUT_DIR / "j1_identity_patch_plan_stage11_1d.csv"
J2_PLAN = OUT_DIR / "j2_hwp_patch_plan_stage11_1d.csv"
SUMMARY = OUT_DIR / "stage11_1d_targeted_patch_plan_summary.md"
PREVIEW = OUT_DIR / "stage11_1d_patch_geometry_preview.png"

LAMBDA_NM = 450
PX_NM = 431.907786
PY_NM = 432.0
MATERIAL = "dielectric_n2p6_blue_baseline"
PHASE_BINS = [0, 60, 120, 180, 240, 300]

J1_FIELDS = [
    "candidate_id", "source_stage", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "diameter_nm", "side_nm", "length_nm", "width_nm", "rotation_deg", "bbox_x_nm", "bbox_y_nm",
    "min_feature_nm", "edge_margin_nm", "geometry_legal", "target_bin_deg", "priority", "expected_role", "patch_reason",
]
J2_FIELDS = [
    "candidate_id", "source_stage", "base_candidate_id", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "length_nm", "width_nm", "rotation_deg", "bbox_x_nm", "bbox_y_nm", "min_feature_nm", "edge_margin_nm",
    "geometry_legal", "target_bin_deg", "target_j1_anchor", "priority", "expected_role", "patch_reason",
]


def read_csv(path: Path) -> list[dict[str, str]]:
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


def legal(bx: float, by: float) -> tuple[bool, float, float]:
    margin = min((PX_NM - bx) / 2.0, (PY_NM - by) / 2.0)
    min_feature = min(bx, by)
    return margin >= 30.0 and min_feature >= 40.0, margin, min_feature


def priority_for_bin(bin_deg: int) -> str:
    if bin_deg == 60:
        return "highest_priority_gap"
    if bin_deg in {0, 300, 120}:
        return "high"
    return "medium"


def add_j1(rows: list[dict[str, str]], seen: set[tuple], height: int, shape: str, target_bin: int, **params: float) -> None:
    if shape == "circle":
        bx = by = params["diameter_nm"]
    elif shape == "square":
        bx = by = params["side_nm"]
    else:
        bx = params["length_nm"]
        by = params["width_nm"]
    ok, margin, min_feature = legal(bx, by)
    if not ok:
        return
    key = (height, shape, round(params.get("diameter_nm", 0), 3), round(params.get("side_nm", 0), 3), round(params.get("length_nm", 0), 3), round(params.get("width_nm", 0), 3), target_bin)
    if key in seen or len(rows) >= 72:
        return
    seen.add(key)
    rows.append(
        {
            "candidate_id": f"J1P1D_{len(rows)+1:04d}_{shape}_B{target_bin}_H{height}",
            "source_stage": "stage11_1d_targeted_patch",
            "shape_family": shape,
            "material": MATERIAL,
            "lambda_nm": str(LAMBDA_NM),
            "p_x_nm": f"{PX_NM:.6f}",
            "p_y_nm": f"{PY_NM:.6f}",
            "height_nm": str(height),
            "diameter_nm": fmt(params.get("diameter_nm")),
            "side_nm": fmt(params.get("side_nm")),
            "length_nm": fmt(params.get("length_nm")),
            "width_nm": fmt(params.get("width_nm")),
            "rotation_deg": "0.000000",
            "bbox_x_nm": f"{bx:.6f}",
            "bbox_y_nm": f"{by:.6f}",
            "min_feature_nm": f"{min_feature:.6f}",
            "edge_margin_nm": f"{margin:.6f}",
            "geometry_legal": "true",
            "target_bin_deg": str(target_bin),
            "priority": priority_for_bin(target_bin),
            "expected_role": "J1 identity-like same-height common-phase anchor",
            "patch_reason": "Stage11-1C found phase-only pairs; add same-height identity-like anchors targeting s1 phase and amplitude match",
        }
    )


def fmt(value: object) -> str:
    if value is None:
        return ""
    x = f(value)
    return "" if math.isnan(x) else f"{x:.6f}"


def make_j1_plan() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple] = set()
    bins_priority = [60, 0, 300, 120, 180, 240]
    h_shape_sizes = {
        500: {
            "circle": [100, 140, 180, 220, 260, 300],
            "square": [100, 140, 180, 220, 260, 300],
            "near_square_rect": [(160, 140), (180, 150), (220, 190), (260, 220), (300, 260), (320, 280)],
        },
        600: {
            "circle": [80, 120, 160, 200, 240, 280],
            "square": [80, 120, 160, 200, 240, 280],
            "near_square_rect": [(140, 120), (180, 150), (220, 180), (240, 210), (280, 240), (300, 260)],
        },
    }
    for height in [500, 600]:
        for i, target_bin in enumerate(bins_priority):
            add_j1(rows, seen, height, "circle", target_bin, diameter_nm=h_shape_sizes[height]["circle"][i])
            add_j1(rows, seen, height, "square", target_bin, side_nm=h_shape_sizes[height]["square"][i])
            L, W = h_shape_sizes[height]["near_square_rect"][i]
            add_j1(rows, seen, height, "near_square_rect", target_bin, length_nm=L, width_nm=W)
    # Fill to 36 per height with extra circle/square local anchors.
    for height in [500, 600]:
        for size in [80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320]:
            for shape in ["circle", "square"]:
                target_bin = bins_priority[(len([r for r in rows if r["height_nm"] == str(height)])) % len(bins_priority)]
                if shape == "circle":
                    add_j1(rows, seen, height, shape, target_bin, diameter_nm=size)
                else:
                    add_j1(rows, seen, height, shape, target_bin, side_nm=size)
                if len([r for r in rows if r["height_nm"] == str(height)]) >= 36:
                    break
            if len([r for r in rows if r["height_nm"] == str(height)]) >= 36:
                break
    return rows[:72]


def load_j2_anchors() -> list[dict[str, str]]:
    anchor_ids = {
        "J2HWP_0019_L210_W90_H500", "J2HWP_0027_L240_W90_H500", "J2HWP_0035_L270_W90_H500",
        "J2HWP_0007_L150_W90_H500", "J2HWP_0044_L300_W110_H500", "J2HWP_0053_L330_W130_H500",
        "J2HWP_0063_L150_W90_H600", "J2HWP_0068_L180_W90_H600", "J2HWP_0083_L240_W90_H600",
        "J2HWP_0092_L270_W110_H600", "J2HWP_0096_L270_W190_H600",
    }
    return [r for r in read_csv(J2_IN) if r["candidate_id"] in anchor_ids]


def nearest_bin(phase: float) -> int:
    return min(PHASE_BINS, key=lambda b: abs((phase - b + 180) % 360 - 180))


def add_j2(rows: list[dict[str, str]], seen: set[tuple], anchor: dict[str, str], L: float, W: float, max_per_height: int = 48) -> None:
    height = int(f(anchor["height_nm"]))
    if height not in {500, 600} or L <= W:
        return
    if sum(1 for r in rows if r["height_nm"] == str(height)) >= max_per_height:
        return
    ok, margin, min_feature = legal(L, W)
    if not ok:
        return
    key = (height, round(L, 3), round(W, 3))
    if key in seen or len(rows) >= 96:
        return
    seen.add(key)
    target_bin = nearest_bin(f(anchor.get("common_phase_deg"), 60.0))
    if target_bin not in PHASE_BINS:
        target_bin = 60
    rows.append(
        {
            "candidate_id": f"J2P1D_{len(rows)+1:04d}_L{int(L)}_W{int(W)}_H{height}",
            "source_stage": "stage11_1d_targeted_patch",
            "base_candidate_id": anchor["candidate_id"],
            "material": MATERIAL,
            "lambda_nm": str(LAMBDA_NM),
            "p_x_nm": f"{PX_NM:.6f}",
            "p_y_nm": f"{PY_NM:.6f}",
            "height_nm": str(height),
            "length_nm": f"{L:.6f}",
            "width_nm": f"{W:.6f}",
            "rotation_deg": "0.000000",
            "bbox_x_nm": f"{L:.6f}",
            "bbox_y_nm": f"{W:.6f}",
            "min_feature_nm": f"{min_feature:.6f}",
            "edge_margin_nm": f"{margin:.6f}",
            "geometry_legal": "true",
            "target_bin_deg": str(target_bin),
            "target_j1_anchor": "",
            "priority": priority_for_bin(target_bin),
            "expected_role": "J2 HWP-like same-height s2 contribution",
            "patch_reason": "Local L/W patch around Stage11-1B HWP-like anchor to improve s2 phase/amplitude match with J1",
        }
    )


def make_j2_plan() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple] = set()
    anchors = load_j2_anchors()
    anchors.sort(key=lambda r: (0 if nearest_bin(f(r.get("common_phase_deg"))) == 60 else 1, -f(r.get("hwp_like_score"))))
    for height in [500, 600]:
        for anchor in [a for a in anchors if int(f(a["height_nm"])) == height]:
            L0 = f(anchor["length_nm"])
            W0 = f(anchor["width_nm"])
            for dL in [-20, -10, 0, 10, 20]:
                for dW in [-20, -10, 0, 10, 20]:
                    add_j2(rows, seen, anchor, L0 + dL, W0 + dW, max_per_height=48)
    return rows[:96]


def write_summary(j1: list[dict[str, str]], j2: list[dict[str, str]]) -> None:
    def count(rows: list[dict[str, str]], key: str, value: str) -> int:
        return sum(1 for r in rows if r[key] == value)
    lines = [
        "# Stage11-1D Targeted Patch Plan",
        "",
        "Stage11-1C evidence:",
        "- strong_fab_candidate = 0",
        "- weak_phase_only = 248",
        "- sim_trend_candidate = 54",
        "",
        "This patch targets ratio, not phase-bin nearest hit alone.",
        "",
        "Core diagnostic:",
        "- J1: s1 = (tx_complex + ty_complex) / 2",
        "- J2: s2 = (tx_complex - ty_complex) / 2",
        "- predicted_ratio = |s1+s2|^2 / max(|s1-s2|^2, eps)",
        "- high ratio requires s1_s2_amp_ratio -> 1 and s1_s2_phase_mismatch_deg -> 0",
        "",
        f"J1 patch case_count = {len(j1)}",
        f"J2 patch case_count = {len(j2)}",
        f"J1 H500/H600 = {count(j1, 'height_nm', '500')}/{count(j1, 'height_nm', '600')}",
        f"J2 H500/H600 = {count(j2, 'height_nm', '500')}/{count(j2, 'height_nm', '600')}",
        f"J1 60deg targeted = {count(j1, 'target_bin_deg', '60')}",
        f"J2 60deg targeted = {count(j2, 'target_bin_deg', '60')}",
        "",
        "No H700 cases are included. No FDTD is run by this planner.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_preview(j1: list[dict[str, str]], j2: list[dict[str, str]]) -> None:
    w, h = 1200, 700
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
    samples = j1[:8] + j2[:8]
    for i, r in enumerate(samples):
        x0 = 60 + (i % 4) * 270
        y0 = 70 + (i // 4) * 150
        rect(x0, y0, x0+150, y0+120, (80, 80, 80), False)
        bx = int(f(r.get("bbox_x_nm")) * 0.32)
        by = int(f(r.get("bbox_y_nm")) * 0.32)
        if r.get("shape_family") == "circle":
            ellipse(x0+75, y0+60, bx//2, by//2, (70, 130, 210))
        else:
            rect(x0+75-bx//2, y0+60-by//2, x0+75+bx//2, y0+60+by//2, (220, 110, 70) if r.get("candidate_id","").startswith("J2") else (80,170,120), True)
    raw = b"".join(b"\x00" + bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    PREVIEW.write_bytes(data)


def main() -> int:
    for path in [J1_IN, J2_IN, RECS_IN, PAIR_1C_IN]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    j1 = make_j1_plan()
    j2 = make_j2_plan()
    write_csv(J1_PLAN, j1, J1_FIELDS)
    write_csv(J2_PLAN, j2, J2_FIELDS)
    write_summary(j1, j2)
    write_preview(j1, j2)
    print(f"j1_patch_case_count={len(j1)}")
    print(f"j2_patch_case_count={len(j2)}")
    print(f"j1_H500={sum(1 for r in j1 if r['height_nm']=='500')} j1_H600={sum(1 for r in j1 if r['height_nm']=='600')}")
    print(f"j2_H500={sum(1 for r in j2 if r['height_nm']=='500')} j2_H600={sum(1 for r in j2 if r['height_nm']=='600')}")
    print(f"target_60_count={sum(1 for r in j1+j2 if r['target_bin_deg']=='60')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
