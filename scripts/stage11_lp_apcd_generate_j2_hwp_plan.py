from __future__ import annotations

import csv
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan"

WAVELENGTH_NM = 450
PX_NM = 431.907786
PY_NM = 432.0
MATERIAL = "dielectric_n2p6_blue_baseline"
HEIGHTS_NM = [500, 600, 700]
LENGTHS_NM = [120, 150, 180, 210, 240, 270, 300, 330]
WIDTHS_NM = [50, 70, 90, 110, 130, 150, 170, 190]

FIELDS = [
    "candidate_id",
    "shape_family",
    "material",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "height_nm",
    "center_x_nm",
    "center_y_nm",
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


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for h in HEIGHTS_NM:
        for length in LENGTHS_NM:
            for width in WIDTHS_NM:
                if length <= width:
                    continue
                edge_margin = min((PX_NM - length) / 2.0, (PY_NM - width) / 2.0)
                min_feature = min(length, width)
                legal = edge_margin >= 30.0 and min_feature >= 40.0
                if not legal:
                    continue
                rows.append(
                    {
                        "candidate_id": f"J2HWP_{len(rows)+1:04d}_L{length}_W{width}_H{h}",
                        "shape_family": "rectangle_nanofin",
                        "material": MATERIAL,
                        "lambda_nm": str(WAVELENGTH_NM),
                        "p_x_nm": f"{PX_NM:.6f}",
                        "p_y_nm": f"{PY_NM:.6f}",
                        "height_nm": str(h),
                        "center_x_nm": "0.000000",
                        "center_y_nm": "0.000000",
                        "length_nm": f"{length:.6f}",
                        "width_nm": f"{width:.6f}",
                        "rotation_deg": "0.000000",
                        "bbox_x_nm": f"{length:.6f}",
                        "bbox_y_nm": f"{width:.6f}",
                        "min_feature_nm": f"{min_feature:.6f}",
                        "edge_margin_nm": f"{edge_margin:.6f}",
                        "geometry_legal": "true",
                        "expected_role": "J2 HWP-like single pillar for LP-APCD",
                        "notes": "static rectangle nanofin plan; requires x/y FDTD extraction before any HWP-like claim",
                    }
                )
    return rows[:96]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_config(path: Path, count: int) -> None:
    text = f"""# Stage11-1B LP-APCD J2 HWP-like static scan plan
stage: Stage11-1B
branch: Track B LP-APCD
mode: static_plan_then_pilot_fdtd
frozen_baseline:
  wavelength_nm: {WAVELENGTH_NM}
  p_x_nm: {PX_NM:.6f}
  p_y_nm: {PY_NM:.6f}
  material: {MATERIAL}
  height_nm: {HEIGHTS_NM}
j2_goal:
  role: HWP-like single pillar
  retardance_deg: "wrap_to_180(ty_phase_deg - tx_phase_deg) near +/-180"
  amp_balance: "|t_x| ~= |t_y|"
  T_mean: high
  common_phase_deg: "angle((tx_complex - ty_complex) / 2)"
shape_ranges:
  shape_family: rectangle_nanofin
  length_nm: {LENGTHS_NM}
  width_nm: {WIDTHS_NM}
  rotation_deg: 0
filters:
  - length_nm > width_nm
  - edge_margin_nm >= 30
  - min_feature_nm >= 40
  - geometry_legal = true
outputs:
  plan_csv: outputs/blue10k6_lp_apcd_j2_hwp_scan/j2_hwp_plan.csv
  case_count: {count}
guardrails:
  - "No K=6 full FDTD."
  - "No dimer FDTD."
  - "Do not claim LP steering from single-pillar pilot data."
"""
    path.write_text(text, encoding="utf-8")


def write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Stage11-1B J2 HWP-Like Static Plan",
        "",
        f"case_count = {len(rows)}",
        "",
        "- Only stable rectangle nanofin primitive is used.",
        "- Regular hexagon, octagon, and ellipse primitives are not used in this J2 pilot because Stage11-1A exposed primitive instability.",
        "- This file is a static plan, not an optical result.",
        "- J2 HWP-like status requires real tx/ty amplitude and phase extraction.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_preview(path: Path, rows: list[dict[str, str]]) -> None:
    w, h = 1100, 620
    pix = bytearray([255, 255, 255] * w * h)

    def setpx(x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < w and 0 <= y < h:
            i = 3 * (y * w + x)
            pix[i : i + 3] = bytes(c)

    def rect(x0: int, y0: int, x1: int, y1: int, c: tuple[int, int, int], fill: bool) -> None:
        for y in range(max(0, y0), min(h, y1)):
            for x in range(max(0, x0), min(w, x1)):
                if fill or x in (x0, x1 - 1) or y in (y0, y1 - 1):
                    setpx(x, y, c)

    samples = [rows[i] for i in [0, 5, 12, 20, 32, 45, 60, 75] if i < len(rows)]
    for idx, row in enumerate(samples):
        col = idx % 4
        rr = idx // 4
        x0 = 70 + col * 250
        y0 = 90 + rr * 240
        rect(x0, y0, x0 + 170, y0 + 170, (80, 80, 80), False)
        lx = int(float(row["length_nm"]) * 0.35)
        wy = int(float(row["width_nm"]) * 0.35)
        rect(x0 + 85 - lx // 2, y0 + 85 - wy // 2, x0 + 85 + lx // 2, y0 + 85 + wy // 2, (68, 132, 206), True)
        # bar code for height
        bars = int(float(row["height_nm"]) // 100)
        for b in range(bars):
            rect(x0 + 15 + b * 8, y0 + 185, x0 + 20 + b * 8, y0 + 210, (230, 120, 70), True)

    raw = b"".join(b"\x00" + bytes(pix[y * w * 3 : (y + 1) * w * 3]) for y in range(h))
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    path.write_bytes(data)


def main() -> int:
    rows = build_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "j2_hwp_plan.csv", rows)
    write_config(OUT_DIR / "j2_hwp_scan_config.yaml", len(rows))
    write_summary(OUT_DIR / "j2_hwp_static_summary.md", rows)
    write_preview(OUT_DIR / "j2_hwp_geometry_preview.png", rows)
    print(f"j2_hwp_plan_case_count={len(rows)}")
    print(f"output={OUT_DIR / 'j2_hwp_plan.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
