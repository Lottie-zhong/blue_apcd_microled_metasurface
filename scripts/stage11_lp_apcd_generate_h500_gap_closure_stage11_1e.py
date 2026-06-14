from __future__ import annotations

import csv
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure"

J1_1A = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_fdtd_results_pilot.csv"
J2_1B = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"
J1_1D = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j1_identity_patch_fdtd_results_stage11_1d.csv"
J2_1D = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j2_hwp_patch_fdtd_results_stage11_1d.csv"
PAIR_1D = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "lp_pair_candidates_stage11_1d_merged_reranked.csv"

J1_PLAN_0 = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_plan.csv"
J1_PLAN_1D = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j1_identity_patch_plan_stage11_1d.csv"
J2_PLAN_1B = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_plan.csv"
J2_PLAN_1D = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j2_hwp_patch_plan_stage11_1d.csv"

J1_OUT = OUT_DIR / "h500_j1_gap_closure_plan_stage11_1e.csv"
J2_OUT = OUT_DIR / "h500_j2_gap_closure_plan_stage11_1e.csv"
SUMMARY = OUT_DIR / "stage11_1e_h500_gap_closure_plan_summary.md"
PREVIEW = OUT_DIR / "stage11_1e_h500_gap_closure_preview.png"

LAMBDA_NM = 450
PX_NM = 431.907786
PY_NM = 432.0
HEIGHT_NM = 500
MATERIAL = "dielectric_n2p6_blue_baseline"
TARGET_BINS = [0, 240]

J1_FIELDS = [
    "candidate_id", "source_stage", "shape_family", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "diameter_nm", "side_nm", "length_nm", "width_nm", "rotation_deg", "bbox_x_nm", "bbox_y_nm",
    "min_feature_nm", "edge_margin_nm", "geometry_legal", "target_bin_deg", "expected_s1_phase_deg",
    "nearest_existing_candidate", "nearest_existing_s1_phase_deg", "priority", "expected_role", "patch_reason",
]
J2_FIELDS = [
    "candidate_id", "source_stage", "base_candidate_id", "material", "lambda_nm", "p_x_nm", "p_y_nm", "height_nm",
    "length_nm", "width_nm", "rotation_deg", "bbox_x_nm", "bbox_y_nm", "min_feature_nm", "edge_margin_nm",
    "geometry_legal", "target_bin_deg", "target_j1_anchor", "expected_s2_phase_deg",
    "nearest_existing_s2_phase_deg", "priority", "expected_role", "patch_reason",
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


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def angle_err(a: float, b: float) -> float:
    return abs(wrap180(a - b))


def legal(bx: float, by: float) -> tuple[bool, float, float]:
    margin = min((PX_NM - bx) / 2.0, (PY_NM - by) / 2.0)
    min_feature = min(bx, by)
    return margin >= 30.0 and min_feature >= 40.0, margin, min_feature


def geom_maps() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in [J1_PLAN_0, J1_PLAN_1D, J2_PLAN_1B, J2_PLAN_1D]:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if cid:
                out[cid] = row
    return out


def h500(row: dict[str, str]) -> bool:
    return abs(f(row.get("height_nm")) - 500.0) <= 1.0


def load_existing_j1(geom: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    out = []
    seen = set()
    for source, path in [("stage11_1a", J1_1A), ("stage11_1d", J1_1D)]:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok" or not h500(row):
                continue
            seen.add(cid)
            g = geom.get(cid, {})
            out.append(
                {
                    "id": cid,
                    "source": source,
                    "shape": row.get("shape_family") or g.get("shape_family", ""),
                    "phase": f(row.get("s1_phase_deg", row.get("common_phase_deg"))),
                    "amp": f(row.get("s1_amp", "")),
                    "loose": row.get("identity_like_pass_loose") == "true",
                    "strict": row.get("identity_like_pass_strict") == "true",
                    "tmean": f(row.get("T_mean")),
                    "diameter": f(g.get("diameter_nm")),
                    "side": f(g.get("side_nm")),
                    "length": f(g.get("length_nm")),
                    "width": f(g.get("width_nm")),
                }
            )
    return out


def load_existing_j2(geom: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    out = []
    seen = set()
    for source, path in [("stage11_1b", J2_1B), ("stage11_1d", J2_1D)]:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok" or not h500(row):
                continue
            seen.add(cid)
            g = geom.get(cid, {})
            out.append(
                {
                    "id": cid,
                    "source": source,
                    "phase": f(row.get("s2_phase_deg", row.get("common_phase_deg"))),
                    "amp": f(row.get("s2_amp", "")),
                    "loose": row.get("hwp_like_pass_loose") == "true",
                    "near_pass": row.get("hwp_like_pass_loose") == "true" or (f(row.get("retardance_abs_to_180_deg")) <= 35 and f(row.get("T_mean")) >= 0.15),
                    "tmean": f(row.get("T_mean")),
                    "length": f(row.get("length_nm", g.get("length_nm"))),
                    "width": f(row.get("width_nm", g.get("width_nm"))),
                }
            )
    return out


def nearest_phase(items: list[dict[str, object]], target: float) -> dict[str, object]:
    valid = [x for x in items if not math.isnan(float(x["phase"]))]
    return min(valid, key=lambda x: angle_err(float(x["phase"]), target)) if valid else {}


def diagnose_bin(bin_deg: int, pairs: list[dict[str, str]]) -> dict[str, str]:
    sub = [r for r in pairs if h500({"height_nm": r.get("j1_height_nm", "")}) and int(f(r.get("target_phase_bin_deg"))) == bin_deg]
    phase_hits = [r for r in sub if r.get("phase_hit_strict") == "true"]
    ratio_hits = [r for r in sub if r.get("ratio_pass_strict") == "true"]
    strong = [r for r in sub if r.get("pair_quality") == "strong_fab_candidate"]
    best_ratio = max(sub, key=lambda r: f(r.get("predicted_ratio")), default={})
    best_phase = min(sub, key=lambda r: f(r.get("phase_error_deg")), default={})
    reasons = []
    if not phase_hits:
        reasons.append("missing_phase_hit")
    if not ratio_hits:
        reasons.append("s1_s2_phase_or_amp_mismatch")
    if phase_hits and not strong:
        if not any(r.get("j1_valid_loose") == "true" for r in phase_hits):
            reasons.append("weak_j1_Tmean")
        if not any(r.get("j2_valid_loose") == "true" for r in phase_hits):
            reasons.append("weak_j2_Tmean")
        if any(f(r.get("s1_s2_amp_ratio")) < 0.75 for r in phase_hits):
            reasons.append("s1_s2_amp_mismatch")
        if any(f(r.get("s1_s2_phase_mismatch_deg")) > 30 for r in phase_hits):
            reasons.append("s1_s2_phase_mismatch")
    if best_phase and f(best_phase.get("phase_error_deg")) <= 8 and f(best_phase.get("predicted_ratio")) < 6:
        reasons.append("phase_only_low_ratio")
    if best_ratio and f(best_ratio.get("predicted_ratio")) >= 10 and f(best_ratio.get("phase_error_deg")) > 8:
        reasons.append("high_ratio_but_phase_missed")
    if not strong:
        reasons.append("missing_j1_phase_anchor")
        reasons.append("missing_j2_phase_anchor")
    return {
        "bin": str(bin_deg),
        "phase_hit_count": str(len(phase_hits)),
        "ratio_hit_count": str(len(ratio_hits)),
        "strong_count": str(len(strong)),
        "best_ratio": fmt(f(best_ratio.get("predicted_ratio"))),
        "best_ratio_phase_error": fmt(f(best_ratio.get("phase_error_deg"))),
        "best_phase_error": fmt(f(best_phase.get("phase_error_deg"))),
        "diagnosis": ", ".join(dict.fromkeys(reasons)) or "already_closed",
    }


def expected_by_nearest(items: list[dict[str, object]], shape: str, size: float, target: float) -> tuple[str, float, float]:
    same = [x for x in items if x.get("shape") == shape and x.get("loose")]
    if shape == "circle":
        same = [x for x in same if not math.isnan(float(x.get("diameter", math.nan)))]
        nearest = min(same, key=lambda x: abs(float(x["diameter"]) - size), default={})
    elif shape == "square":
        same = [x for x in same if not math.isnan(float(x.get("side", math.nan)))]
        nearest = min(same, key=lambda x: abs(float(x["side"]) - size), default={})
    else:
        nearest = nearest_phase([x for x in items if x.get("shape") == "near_square_rect" and x.get("loose")], target)
    if not nearest:
        nearest = nearest_phase(items, target)
    return str(nearest.get("id", "")), float(nearest.get("phase", math.nan)), angle_err(float(nearest.get("phase", math.nan)), target)


def make_j1_plan(existing_j1: list[dict[str, object]]) -> list[dict[str, str]]:
    candidates = []
    seen_geom: set[tuple] = set()
    # Existing measured dimensions to avoid exact reruns when geometry metadata is known.
    for x in existing_j1:
        key = (x.get("shape"), round(float(x.get("diameter", 0) or 0), 3), round(float(x.get("side", 0) or 0), 3), round(float(x.get("length", 0) or 0), 3), round(float(x.get("width", 0) or 0), 3))
        seen_geom.add(key)

    for bin_deg in TARGET_BINS:
        target_phase = float(bin_deg)
        raw = []
        for shape in ["circle", "square"]:
            for size in range(80, 341, 10):
                key = (shape, size if shape == "circle" else 0, size if shape == "square" else 0, 0, 0)
                if key in seen_geom:
                    continue
                nearest_id, nearest_phase, err = expected_by_nearest(existing_j1, shape, size, target_phase)
                raw.append((err, shape, size, nearest_id, nearest_phase))
        raw.sort(key=lambda x: x[0])
        selected = raw[:18]

        rect_anchors = [
            x for x in existing_j1
            if x.get("shape") == "near_square_rect" and x.get("loose") and not math.isnan(float(x.get("length", math.nan))) and not math.isnan(float(x.get("width", math.nan)))
        ]
        rect_anchors.sort(key=lambda x: angle_err(float(x["phase"]), target_phase))
        rect_selected = []
        rect_seen = set()
        for anchor in rect_anchors[:4]:
            L0 = float(anchor["length"])
            W0 = float(anchor["width"])
            for dL in [-20, -10, 0, 10, 20]:
                for dW in [-20, -10, 0, 10, 20]:
                    L, W = L0 + dL, W0 + dW
                    if abs(L - W) > 50:
                        continue
                    ok, margin, min_feature = legal(L, W)
                    key = ("near_square_rect", 0, 0, round(L, 3), round(W, 3))
                    if ok and key not in seen_geom and key not in rect_seen:
                        rect_seen.add(key)
                        rect_selected.append((angle_err(float(anchor["phase"]), target_phase), "near_square_rect", (L, W), str(anchor["id"]), float(anchor["phase"])))
        rect_selected.sort(key=lambda x: x[0])
        selected += rect_selected[:6]

        for _, shape, size_or_pair, nearest_id, nearest_phase in selected[:24]:
            if len(candidates) >= 48:
                break
            if shape == "circle":
                bx = by = float(size_or_pair)
                diameter, side, length, width = bx, math.nan, math.nan, math.nan
            elif shape == "square":
                bx = by = float(size_or_pair)
                diameter, side, length, width = math.nan, bx, math.nan, math.nan
            else:
                length, width = float(size_or_pair[0]), float(size_or_pair[1])
                bx, by = length, width
                diameter, side = math.nan, math.nan
            ok, margin, min_feature = legal(bx, by)
            if not ok:
                continue
            candidates.append(
                {
                    "candidate_id": f"H500J1G1E_{len(candidates)+1:04d}_{shape}_B{bin_deg}",
                    "source_stage": "stage11_1e_h500_gap_closure",
                    "shape_family": shape,
                    "material": MATERIAL,
                    "lambda_nm": str(LAMBDA_NM),
                    "p_x_nm": f"{PX_NM:.6f}",
                    "p_y_nm": f"{PY_NM:.6f}",
                    "height_nm": str(HEIGHT_NM),
                    "diameter_nm": fmt(diameter),
                    "side_nm": fmt(side),
                    "length_nm": fmt(length),
                    "width_nm": fmt(width),
                    "rotation_deg": "0.000000",
                    "bbox_x_nm": fmt(bx),
                    "bbox_y_nm": fmt(by),
                    "min_feature_nm": fmt(min_feature),
                    "edge_margin_nm": fmt(margin),
                    "geometry_legal": "true",
                    "target_bin_deg": str(bin_deg),
                    "expected_s1_phase_deg": fmt(target_phase),
                    "nearest_existing_candidate": nearest_id,
                    "nearest_existing_s1_phase_deg": fmt(nearest_phase),
                    "priority": "highest" if bin_deg in {0, 240} else "medium",
                    "expected_role": "H500 J1 identity-like s1 phase anchor",
                    "patch_reason": "Stage11-1E H500-only gap closure for missing 0/240 strong bins",
                }
            )
    return candidates[:48]


def make_j2_plan(existing_j2: list[dict[str, object]], existing_j1: list[dict[str, object]]) -> list[dict[str, str]]:
    anchors = [
        x for x in existing_j2
        if x.get("near_pass") and not math.isnan(float(x.get("length", math.nan))) and not math.isnan(float(x.get("width", math.nan)))
    ]
    priority_ids = {
        "J2HWP_0019_L210_W90_H500", "J2HWP_0027_L240_W90_H500", "J2HWP_0035_L270_W90_H500",
        "J2HWP_0007_L150_W90_H500", "J2HWP_0044_L300_W110_H500", "J2HWP_0053_L330_W130_H500",
    }
    rows = []
    seen = set()
    for bin_deg in TARGET_BINS:
        target_j1 = nearest_phase([x for x in existing_j1 if x.get("loose")], float(bin_deg))
        target_phase = float(target_j1.get("phase", bin_deg))
        ranked = sorted(anchors, key=lambda x: (0 if x["id"] in priority_ids else 1, angle_err(float(x["phase"]), target_phase), -float(x.get("tmean", 0) or 0)))
        local = []
        for anchor in ranked[:8]:
            L0, W0 = float(anchor["length"]), float(anchor["width"])
            for dL in [-15, -10, -5, 0, 5, 10, 15]:
                for dW in [-15, -10, -5, 0, 5, 10, 15]:
                    L, W = L0 + dL, W0 + dW
                    if L <= W:
                        continue
                    ok, margin, min_feature = legal(L, W)
                    key = (round(L, 3), round(W, 3), bin_deg)
                    if ok and key not in seen:
                        seen.add(key)
                        local.append((angle_err(float(anchor["phase"]), target_phase), anchor, L, W, margin, min_feature))
        local.sort(key=lambda x: x[0])
        for _, anchor, L, W, margin, min_feature in local[:36]:
            if len(rows) >= 72:
                break
            rows.append(
                {
                    "candidate_id": f"H500J2G1E_{len(rows)+1:04d}_L{int(round(L))}_W{int(round(W))}_B{bin_deg}",
                    "source_stage": "stage11_1e_h500_gap_closure",
                    "base_candidate_id": str(anchor["id"]),
                    "material": MATERIAL,
                    "lambda_nm": str(LAMBDA_NM),
                    "p_x_nm": f"{PX_NM:.6f}",
                    "p_y_nm": f"{PY_NM:.6f}",
                    "height_nm": str(HEIGHT_NM),
                    "length_nm": fmt(L),
                    "width_nm": fmt(W),
                    "rotation_deg": "0.000000",
                    "bbox_x_nm": fmt(L),
                    "bbox_y_nm": fmt(W),
                    "min_feature_nm": fmt(min_feature),
                    "edge_margin_nm": fmt(margin),
                    "geometry_legal": "true",
                    "target_bin_deg": str(bin_deg),
                    "target_j1_anchor": str(target_j1.get("id", "")),
                    "expected_s2_phase_deg": fmt(target_phase),
                    "nearest_existing_s2_phase_deg": fmt(float(anchor["phase"])),
                    "priority": "highest",
                    "expected_role": "H500 J2 HWP-like s2 phase/amplitude match",
                    "patch_reason": "Local H500 L/W closure around HWP pass or near-pass anchors for missing 0/240 bins",
                }
            )
    return rows[:72]


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_preview(j1: list[dict[str, str]], j2: list[dict[str, str]]) -> None:
    w, h = 1000, 520
    pix = bytearray([255, 255, 255] * w * h)
    def setpx(x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = 3 * (y * w + x); pix[i:i+3] = bytes(c)
    def rect(x0: int, y0: int, x1: int, y1: int, c: tuple[int, int, int], fill: bool) -> None:
        for yy in range(max(0, y0), min(h, y1)):
            for xx in range(max(0, x0), min(w, x1)):
                if fill or xx in (x0, x1-1) or yy in (y0, y1-1):
                    setpx(xx, yy, c)
    def ellipse(cx: int, cy: int, rx: int, ry: int, c: tuple[int, int, int]) -> None:
        for yy in range(cy-ry, cy+ry+1):
            for xx in range(cx-rx, cx+rx+1):
                if ((xx-cx)/max(rx,1))**2 + ((yy-cy)/max(ry,1))**2 <= 1:
                    setpx(xx, yy, c)
    samples = j1[:8] + j2[:8]
    for i, r in enumerate(samples):
        x0 = 50 + (i % 4) * 230
        y0 = 45 + (i // 4) * 115
        rect(x0, y0, x0+145, y0+95, (70, 70, 70), False)
        bx = int(f(r.get("bbox_x_nm")) * 0.28)
        by = int(f(r.get("bbox_y_nm")) * 0.28)
        if r.get("shape_family") == "circle":
            ellipse(x0+72, y0+48, bx//2, by//2, (70, 130, 210))
        else:
            color = (220, 110, 70) if r["candidate_id"].startswith("H500J2") else (80, 170, 120)
            rect(x0+72-bx//2, y0+48-by//2, x0+72+bx//2, y0+48+by//2, color, True)
    raw = b"".join(b"\x00" + bytes(pix[y*w*3:(y+1)*w*3]) for y in range(h))
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    PREVIEW.write_bytes(data)


def write_summary(j1: list[dict[str, str]], j2: list[dict[str, str]], d0: dict[str, str], d240: dict[str, str]) -> None:
    lines = [
        "# Stage11-1E H500 Gap Closure Plan",
        "",
        "Target: H500-only fabrication-main same-height static LP-APCD 6-bin library.",
        "Existing H500 strong bins from Stage11-1D: 60, 120, 180, 300.",
        "Missing bins targeted here: 0, 240.",
        "",
        "Core formulas: s1=(tx+ty)/2, s2=(tx-ty)/2, predicted_ratio=|s1+s2|^2/max(|s1-s2|^2, eps).",
        "High ratio requires s1_amp approximately s2_amp and s1_phase approximately s2_phase.",
        "",
        "## Data-driven diagnosis",
        f"- 0 deg: {d0['diagnosis']}; phase_hits={d0['phase_hit_count']}; ratio_hits={d0['ratio_hit_count']}; best_ratio={d0['best_ratio']} at phase_error={d0['best_ratio_phase_error']}",
        f"- 240 deg: {d240['diagnosis']}; phase_hits={d240['phase_hit_count']}; ratio_hits={d240['ratio_hit_count']}; best_ratio={d240['best_ratio']} at phase_error={d240['best_ratio_phase_error']}",
        "",
        "Patch action: both J1 common-phase anchors and J2 HWP-like s2 anchors are patched for 0/240.",
        "",
        f"J1 gap closure case_count = {len(j1)}",
        f"J2 gap closure case_count = {len(j2)}",
        f"J1 0/240 count = {sum(1 for r in j1 if r['target_bin_deg']=='0')}/{sum(1 for r in j1 if r['target_bin_deg']=='240')}",
        f"J2 0/240 count = {sum(1 for r in j2 if r['target_bin_deg']=='0')}/{sum(1 for r in j2 if r['target_bin_deg']=='240')}",
        "",
        "Evidence boundary: planner only creates H500 single-pillar patch plans. No FDTD, no dimer, no K=6 full simulation.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    for path in [J1_1A, J2_1B, J1_1D, J2_1D, PAIR_1D]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    geom = geom_maps()
    existing_j1 = load_existing_j1(geom)
    existing_j2 = load_existing_j2(geom)
    pairs = read_csv(PAIR_1D)
    d0 = diagnose_bin(0, pairs)
    d240 = diagnose_bin(240, pairs)
    j1 = make_j1_plan(existing_j1)
    j2 = make_j2_plan(existing_j2, existing_j1)
    write_csv(J1_OUT, j1, J1_FIELDS)
    write_csv(J2_OUT, j2, J2_FIELDS)
    write_summary(j1, j2, d0, d240)
    write_preview(j1, j2)
    print(f"j1_gap_closure_case_count={len(j1)}")
    print(f"j2_gap_closure_case_count={len(j2)}")
    print(f"j1_0={sum(1 for r in j1 if r['target_bin_deg']=='0')} j1_240={sum(1 for r in j1 if r['target_bin_deg']=='240')}")
    print(f"j2_0={sum(1 for r in j2 if r['target_bin_deg']=='0')} j2_240={sum(1 for r in j2 if r['target_bin_deg']=='240')}")
    print(f"diagnosis_0={d0['diagnosis']}")
    print(f"diagnosis_240={d240['diagnosis']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
