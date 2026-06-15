from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2f_h500_dimer_120_240_refine"
SRC = OUT_DIR / "h500_dimer_120_240_refine_source_pairs_stage11_2f.csv"
BEST_2E = REPO_ROOT / "outputs/blue10k6_lp_apcd_stage11_2e_h500_dimer_240_fine_pull/h500_dimer_best_actual_6bin_library_stage11_2e.csv"
PLAN = OUT_DIR / "h500_dimer_120_240_refine_patch_plan_stage11_2f.csv"
SUMMARY = OUT_DIR / "h500_dimer_120_240_refine_patch_plan_summary_stage11_2f.md"
PREVIEW = OUT_DIR / "h500_dimer_120_240_refine_patch_preview_stage11_2f.png"

PX = 431.907786
PY = 432.0
H = 500.0
LAM = 450.0

FIELDS = [
    "dimer_case_id",
    "refine_pair_id",
    "target_actual_bin_deg",
    "source_pair_id",
    "static_original_bin_deg",
    "j1_candidate_id",
    "j2_candidate_id",
    "height_nm",
    "lambda_nm",
    "p_x_nm",
    "p_y_nm",
    "j1_shape_family",
    "j1_geometry_params",
    "j2_length_nm",
    "j2_width_nm",
    "j2_rotation_deg",
    "placement_type",
    "swap_order",
    "gap_nm",
    "local_offset_nm",
    "j1_center_x_nm",
    "j1_center_y_nm",
    "j2_center_x_nm",
    "j2_center_y_nm",
    "dimer_gap_nm",
    "edge_margin_nm",
    "geometry_legal",
    "expected_failure_mode_to_fix",
    "expected_effect",
    "priority",
    "中文说明",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def flt(value: object, default: float = math.nan) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def fmt(value: float) -> str:
    return "" if math.isnan(value) else f"{value:.6f}"


def sizes(row: dict[str, str]) -> tuple[float, float, float, float]:
    geom = json.loads(row["j1_geometry_params"])
    fam = row["j1_shape_family"]
    if fam == "circle":
        j1x = j1y = flt(geom.get("diameter_nm"))
    elif fam == "square":
        j1x = j1y = flt(geom.get("side_nm"))
    else:
        j1x = flt(geom.get("length_nm"))
        j1y = flt(geom.get("width_nm"))
    return j1x, j1y, flt(row["j2_length_nm"]), flt(row["j2_width_nm"])


def place(row: dict[str, str], placement: str, gap: float, offset: float, swap: bool) -> tuple[float, float, float, float, float, float, bool]:
    j1x, j1y, j2x, j2y = sizes(row)
    if placement == "x_pair":
        sep = (j1x + j2x) / 2 + gap
        x1, y1, x2, y2 = -sep / 2 + offset / 2, 0.0, sep / 2 + offset / 2, 0.0
    elif placement == "diag_pair":
        sepx = (j1x + j2x) / 2 + gap / math.sqrt(2)
        sepy = (j1y + j2y) / 2 + gap / math.sqrt(2)
        x1, y1, x2, y2 = -sepx / 2 + offset / 2, -sepy / 2 + offset / 2, sepx / 2 + offset / 2, sepy / 2 + offset / 2
    else:
        sep = (j1y + j2y) / 2 + gap
        x1, y1, x2, y2 = 0.0, -sep / 2 + offset / 2, 0.0, sep / 2 + offset / 2
    if swap:
        x1, y1, x2, y2 = x2, y2, x1, y1
    dx = abs(x2 - x1) - (j1x + j2x) / 2
    dy = abs(y2 - y1) - (j1y + j2y) / 2
    dgap = math.hypot(dx, dy) if dx >= 0 and dy >= 0 else (dx if dx >= 0 else (dy if dy >= 0 else -min(-dx, -dy)))
    edge = min(
        PX / 2 - max(abs(x1) + j1x / 2, abs(x2) + j2x / 2),
        PY / 2 - max(abs(y1) + j1y / 2, abs(y2) + j2y / 2),
    )
    return x1, y1, x2, y2, dgap, edge, dgap >= 20 and edge >= 10


def tiny_png(path: Path) -> None:
    width, height = 320, 180
    pixels = bytearray([255, 255, 255] * width * height)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def variants(row: dict[str, str]) -> list[tuple[str, float, float, bool]]:
    target = row["target_actual_bin_deg"]
    specs: list[tuple[str, float, float, bool]] = []
    if target == "120":
        for placement in ["x_pair", "diag_pair"]:
            for gap in [70, 80, 90, 100, 120, 60]:
                for offset in [-30, -20, -10, 0, 10, 20, -40]:
                    for swap in [False, True]:
                        specs.append((placement, float(gap), float(offset), swap))
        return sorted(specs, key=lambda s: (0 if 70 <= s[1] <= 100 else 1, 0 if s[0] == "x_pair" else 1, abs(s[2] + 20), 0 if s[3] else 1))
    for gap in [90, 88, 92, 86, 94, 84, 96]:
        for offset in [-25, -28, -22, -30, -20, -32, -35]:
            specs.append(("x_pair", float(gap), float(offset), True))
    for gap in [90, 80, 100]:
        for offset in [-25, -35, -15]:
            specs.append(("diag_pair", float(gap), float(offset), True))
    return sorted(specs, key=lambda s: (0 if s[0] == "x_pair" else 1, abs(s[1] - 90), abs(s[2] + 25)))


def main() -> None:
    for path in [SRC, BEST_2E]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str, float, float, bool]] = set()
    for source in read_csv(SRC):
        cap = 2 if source["target_actual_bin_deg"] == "120" else 3
        count = 0
        for placement, gap, offset, swap in variants(source):
            if count >= cap or len(rows) >= 60:
                break
            x1, y1, x2, y2, dgap, edge, legal = place(source, placement, gap, offset, swap)
            if not legal:
                continue
            key = (source["source_pair_id"], placement, gap, offset, swap)
            if key in seen:
                continue
            seen.add(key)
            count += 1
            target = source["target_actual_bin_deg"]
            rows.append({
                "dimer_case_id": f"H500DIMER2F_{len(rows)+1:03d}_B{target}_{placement}_{'swap' if swap else 'noswap'}_G{int(gap)}_O{int(offset)}",
                "refine_pair_id": source["refine_pair_id"],
                "target_actual_bin_deg": target,
                "source_pair_id": source["source_pair_id"],
                "static_original_bin_deg": source["static_original_bin_deg"],
                "j1_candidate_id": source["j1_candidate_id"],
                "j2_candidate_id": source["j2_candidate_id"],
                "height_nm": fmt(H),
                "lambda_nm": fmt(LAM),
                "p_x_nm": fmt(PX),
                "p_y_nm": fmt(PY),
                "j1_shape_family": source["j1_shape_family"],
                "j1_geometry_params": source["j1_geometry_params"],
                "j2_length_nm": source["j2_length_nm"],
                "j2_width_nm": source["j2_width_nm"],
                "j2_rotation_deg": "0.000000",
                "placement_type": placement,
                "swap_order": "J2-J1" if swap else "J1-J2",
                "gap_nm": fmt(gap),
                "local_offset_nm": fmt(offset),
                "j1_center_x_nm": fmt(x1),
                "j1_center_y_nm": fmt(y1),
                "j2_center_x_nm": fmt(x2),
                "j2_center_y_nm": fmt(y2),
                "dimer_gap_nm": fmt(dgap),
                "edge_margin_nm": fmt(edge),
                "geometry_legal": "true",
                "expected_failure_mode_to_fix": source["expected_failure_mode_to_fix"],
                "expected_effect": "120: reduce blocked y-input leakage; 240: fine pull selected-channel common phase",
                "priority": source["priority"],
                "中文说明": source["中文说明"],
                "notes": "Stage11-2F H500 dimer 120/240 APCD projection-phase refinement; no K=6.",
            })

    write_csv(PLAN, rows, FIELDS)
    gaps = [flt(row["gap_nm"]) for row in rows]
    offsets = [flt(row["local_offset_nm"]) for row in rows]
    lines = [
        "# Stage11-2F H500 120/240 Refine Patch Plan",
        "",
        f"source_pair_count = {len(read_csv(SRC))}",
        f"plan_case_count = {len(rows)}",
        f"legal_count = {sum(row['geometry_legal'] == 'true' for row in rows)}",
        f"target_120_count = {sum(row['target_actual_bin_deg'] == '120' for row in rows)}",
        f"target_240_count = {sum(row['target_actual_bin_deg'] == '240' for row in rows)}",
        f"x_pair_count = {sum(row['placement_type'] == 'x_pair' for row in rows)}",
        f"diag_pair_count = {sum(row['placement_type'] == 'diag_pair' for row in rows)}",
        f"gap_range_nm = {min(gaps) if gaps else ''} to {max(gaps) if gaps else ''}",
        f"offset_range_nm = {min(offsets) if offsets else ''} to {max(offsets) if offsets else ''}",
        "",
        "Only H500 dimer x/y normal-incidence refinement. No K=6, no metagrating, no H600/H700.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tiny_png(PREVIEW)
    print(f"plan_case_count={len(rows)}")
    print(f"legal_count={sum(row['geometry_legal'] == 'true' for row in rows)}")
    print(f"target_120_count={sum(row['target_actual_bin_deg'] == '120' for row in rows)}")
    print(f"target_240_count={sum(row['target_actual_bin_deg'] == '240' for row in rows)}")
    print(f"x_pair_count={sum(row['placement_type'] == 'x_pair' for row in rows)}")
    print(f"diag_pair_count={sum(row['placement_type'] == 'diag_pair' for row in rows)}")


if __name__ == "__main__":
    main()
