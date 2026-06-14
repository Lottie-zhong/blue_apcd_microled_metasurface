from __future__ import annotations

import argparse
import csv
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan"

WAVELENGTH_NM = 450
STEERING_ANGLE_DEG = 10
K_DIMERS_PER_SUPERCELL = 6
DIMER_PITCH_X_NM = 431.907786
PERIOD_Y_NM = 432.0
SUPERCELL_PERIOD_NM = DIMER_PITCH_X_NM * K_DIMERS_PER_SUPERCELL
PHASE_STATES_DEG = [0, 60, 120, 180, 240, 300]
HEIGHTS_NM = [500, 600, 700]
MATERIAL = "dielectric_n2p6_blue_baseline"
MIN_GAP_MARGIN_NM = 40.0


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
    "expected_role",
    "notes",
]


def shape_specs() -> list[dict[str, float | str]]:
    specs: list[dict[str, float | str]] = []
    for diameter in [90, 120, 150, 180, 210, 240, 270, 300]:
        specs.append({"shape_family": "circle", "diameter_nm": diameter})
    for side in [90, 120, 150, 180, 210, 240, 270, 300]:
        specs.append({"shape_family": "square", "side_nm": side})
    for diameter in [100, 130, 160, 190, 220, 250, 280, 310]:
        specs.append({"shape_family": "regular_hexagon", "diameter_nm": diameter})
        specs.append({"shape_family": "regular_octagon", "diameter_nm": diameter})
    for length in [120, 150, 180, 210, 240, 270]:
        for width in [120, 150, 180, 210, 240, 270]:
            ratio = length / width
            if 0.85 <= ratio <= 1.15 and length != width:
                specs.append({"shape_family": "near_square_rect", "length_nm": length, "width_nm": width})
    for major in [120, 150, 180, 210, 240, 270]:
        for minor in [120, 150, 180, 210, 240, 270]:
            ratio = major / minor
            if 0.85 <= ratio <= 1.15 and major != minor:
                specs.append({"shape_family": "near_circle_ellipse", "length_nm": major, "width_nm": minor})
    return specs


def bbox(spec: dict[str, float | str]) -> tuple[float, float]:
    family = str(spec["shape_family"])
    if family in {"circle", "regular_hexagon", "regular_octagon"}:
        d = float(spec["diameter_nm"])
        return d, d
    if family == "square":
        s = float(spec["side_nm"])
        return s, s
    return float(spec["length_nm"]), float(spec["width_nm"])


def min_feature(spec: dict[str, float | str]) -> float:
    family = str(spec["shape_family"])
    if family in {"circle", "regular_hexagon", "regular_octagon"}:
        return float(spec["diameter_nm"])
    if family == "square":
        return float(spec["side_nm"])
    return min(float(spec["length_nm"]), float(spec["width_nm"]))


def build_plan() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    serial = 1
    for height_nm in HEIGHTS_NM:
        for spec in shape_specs():
            bx, by = bbox(spec)
            margin = min((DIMER_PITCH_X_NM - bx) / 2.0, (PERIOD_Y_NM - by) / 2.0)
            legal = margin >= MIN_GAP_MARGIN_NM and min_feature(spec) >= 80.0
            family = str(spec["shape_family"])
            rows.append(
                {
                    "candidate_id": f"J1ID_{serial:04d}_{family}_H{height_nm}",
                    "shape_family": family,
                    "material": MATERIAL,
                    "lambda_nm": f"{WAVELENGTH_NM}",
                    "p_x_nm": f"{DIMER_PITCH_X_NM:.6f}",
                    "p_y_nm": f"{PERIOD_Y_NM:.6f}",
                    "height_nm": f"{height_nm}",
                    "center_x_nm": "0.000000",
                    "center_y_nm": "0.000000",
                    "diameter_nm": f"{float(spec.get('diameter_nm', math.nan)):.6f}" if "diameter_nm" in spec else "",
                    "side_nm": f"{float(spec.get('side_nm', math.nan)):.6f}" if "side_nm" in spec else "",
                    "length_nm": f"{float(spec.get('length_nm', math.nan)):.6f}" if "length_nm" in spec else "",
                    "width_nm": f"{float(spec.get('width_nm', math.nan)):.6f}" if "width_nm" in spec else "",
                    "rotation_deg": "0.000000",
                    "bbox_x_nm": f"{bx:.6f}",
                    "bbox_y_nm": f"{by:.6f}",
                    "min_feature_nm": f"{min_feature(spec):.6f}",
                    "edge_margin_nm": f"{margin:.6f}",
                    "geometry_legal": "true" if legal else "false",
                    "expected_role": "J1 identity-like / isotropic-like channel for LP-APCD",
                    "notes": "static plan only; requires Lumerical tx/ty amplitude and phase extraction before any identity-like claim",
                }
            )
            serial += 1
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_config(path: Path) -> None:
    text = f"""# Stage11-0 LP-APCD J1 identity-like static scan plan
stage: Stage11-0
branch: Track B LP-APCD
mode: static_plan_only_no_lumerical
frozen_baseline:
  wavelength_nm: {WAVELENGTH_NM}
  steering_angle_deg: {STEERING_ANGLE_DEG}
  K_dimers_per_supercell: {K_DIMERS_PER_SUPERCELL}
  dimer_pitch_x_nm: {DIMER_PITCH_X_NM:.6f}
  period_y_nm: {PERIOD_Y_NM:.6f}
  supercell_period_nm: {SUPERCELL_PERIOD_NM:.6f}
  phase_states_deg: {PHASE_STATES_DEG}
lp_apcd_logic:
  target: "J_LP-APCD ~= t exp(i phi) |x><x|"
  decomposition: "P_x = |x><x| = 1/2 * (I + H_x)"
  j1_role: "identity-like / isotropic-like single pillar"
  j2_role: "HWP-like single pillar"
  interference: "J1 and J2 add for x input and cancel for y input"
shape_ranges:
  circle_diameter_nm: [90, 120, 150, 180, 210, 240, 270, 300]
  square_side_nm: [90, 120, 150, 180, 210, 240, 270, 300]
  regular_hexagon_diameter_nm: [100, 130, 160, 190, 220, 250, 280, 310]
  regular_octagon_diameter_nm: [100, 130, 160, 190, 220, 250, 280, 310]
  near_square_rect_length_width_nm: [120, 150, 180, 210, 240, 270]
  near_circle_ellipse_major_minor_nm: [120, 150, 180, 210, 240, 270]
  height_nm: {HEIGHTS_NM}
screening_targets_after_fdtd:
  retardance_deg: "wrap_to_180(ty_phase_deg - tx_phase_deg) near 0 or 360"
  amplitude_balance: "|t_x| ~= |t_y|"
  T_mean: "high"
  common_phase: "wide coverage for later six phase bins"
outputs:
  plan_csv: outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_plan.csv
  static_summary_md: outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_static_summary.md
  geometry_preview_png: outputs/blue10k6_lp_apcd_j1_identity_scan/j1_identity_geometry_preview.png
guardrails:
  - "Do not launch large-scale Lumerical or full K=6 FDTD in Stage11-0."
  - "Do not claim any structure is identity-like before real tx/ty extraction."
  - "Do not relabel LP directional emission as photonic spin Hall effect."
  - "Do not use pure PB phase as the default LP steering mechanism."
  - "Do not revert to 633 nm, +15 deg, K=7, p348, or p518."
"""
    path.write_text(text, encoding="utf-8")


def write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    legal = sum(1 for row in rows if row["geometry_legal"] == "true")
    families = sorted({row["shape_family"] for row in rows})
    text = f"""# Stage11-0 J1 Identity-Like Static Scan Plan

本阶段只生成 J1 identity-like / isotropic-like 单柱静态扫描计划。

## Baseline

- wavelength_nm = {WAVELENGTH_NM}
- steering_angle_deg = +{STEERING_ANGLE_DEG}
- K_dimers_per_supercell = {K_DIMERS_PER_SUPERCELL}
- dimer_pitch_x_nm = {DIMER_PITCH_X_NM:.6f}
- period_y_nm = {PERIOD_Y_NM:.6f}
- phase_states_deg = {PHASE_STATES_DEG}

## LP-APCD Logic

J1 提供 identity-like 通道；J2 提供 HWP-like 通道；二者在 x 输入相长，在 y 输入相消；后续通过 common phase / propagation phase / resonance phase 做相位梯度。

## Static Plan

- case_count = {len(rows)}
- geometry_legal_count = {legal}
- shape_families = {", ".join(families)}
- heights_nm = {HEIGHTS_NM}

## Evidence Boundary

尚未声称任何 structure 已实现 identity-like。后续需要 Lumerical 提取 tx/ty amplitude/phase 后，按 retardance、amplitude balance、T_mean 与 common phase coverage 筛选。

本阶段未启动 Lumerical，未完成真实 dimer FDTD，未证明 K=6 steering。
"""
    path.write_text(text, encoding="utf-8")


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_preview_png(path: Path, rows: list[dict[str, str]]) -> None:
    width, height = 1200, 760
    pixels = bytearray([255, 255, 255] * width * height)

    def set_px(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            i = 3 * (y * width + x)
            pixels[i : i + 3] = bytes(color)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], fill: bool = True) -> None:
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                if fill or x in (x0, x1 - 1) or y in (y0, y1 - 1):
                    set_px(x, y, color)

    def ellipse(cx: int, cy: int, rx: int, ry: int, color: tuple[int, int, int]) -> None:
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / max(rx, 1)) ** 2 + ((y - cy) / max(ry, 1)) ** 2 <= 1.0:
                    set_px(x, y, color)

    samples: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if row["height_nm"] == "500" and row["shape_family"] not in seen:
            samples.append(row)
            seen.add(row["shape_family"])
    colors = [(64, 120, 180), (245, 133, 24), (84, 162, 75), (178, 121, 162), (228, 87, 86), (114, 183, 178)]
    for idx, row in enumerate(samples[:6]):
        x0 = 50 + idx * 185
        y0 = 120
        rect(x0, y0, x0 + 150, y0 + 150, (55, 65, 75), fill=False)
        cx, cy = x0 + 75, y0 + 75
        scale = 0.28
        bx = int(float(row["bbox_x_nm"]) * scale)
        by = int(float(row["bbox_y_nm"]) * scale)
        family = row["shape_family"]
        color = colors[idx % len(colors)]
        if family in {"circle", "regular_hexagon", "regular_octagon", "near_circle_ellipse"}:
            ellipse(cx, cy, max(8, bx // 2), max(8, by // 2), color)
        else:
            rect(cx - bx // 2, cy - by // 2, cx + bx // 2, cy + by // 2, color, fill=True)
    # Bottom conceptual K=6 pitch row.
    y = 470
    for i, phase in enumerate(PHASE_STATES_DEG):
        x = 80 + i * 175
        rect(x, y, x + 95, y + 70, (180, 205, 245), fill=True)
        rect(x, y, x + 95, y + 70, (45, 85, 150), fill=False)
        # encode phase as small bars, enough for visual distinction without font dependencies
        for b in range(phase // 60 + 1):
            rect(x + 10 + b * 10, y + 15, x + 16 + b * 10, y + 55, (45, 85, 150), fill=True)

    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height))
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    data += _png_chunk(b"IEND", b"")
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print plan counts without writing outputs")
    args = parser.parse_args()

    rows = build_plan()
    legal = sum(1 for row in rows if row["geometry_legal"] == "true")
    print(f"stage=Stage11-0")
    print(f"j1_identity_plan_case_count={len(rows)}")
    print(f"geometry_legal_count={legal}")
    print("mode=static_plan_only_no_lumerical")
    if args.dry_run:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "j1_identity_plan.csv", rows)
    write_config(OUT_DIR / "j1_identity_scan_config.yaml")
    write_summary(OUT_DIR / "j1_identity_static_summary.md", rows)
    write_preview_png(OUT_DIR / "j1_identity_geometry_preview.png", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
