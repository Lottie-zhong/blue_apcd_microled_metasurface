from __future__ import annotations

import argparse
import cmath
import csv
import json
import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
J1_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan"
PAIR_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing"

DIMER_PITCH_X_NM = 431.907786
PERIOD_Y_NM = 432.0
K_DIMERS_PER_SUPERCELL = 6
SUPERCELL_PERIOD_NM = DIMER_PITCH_X_NM * K_DIMERS_PER_SUPERCELL
PHASE_BINS_DEG = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

PAIR_FIELDS = [
    "pair_id",
    "j1_candidate_id",
    "j2_candidate_id",
    "target_phase_bin_deg",
    "output_phase_deg",
    "phase_error_deg",
    "A1",
    "A2",
    "phi1_deg",
    "phi2_deg",
    "target_x_amp",
    "leak_y_amp",
    "target_x_power",
    "leak_y_power",
    "predicted_ratio",
    "amp_match_score",
    "phase_match_score",
    "geometry_legal",
    "pairing_status",
    "reason",
]

PAIR_FIELDS_STAGE11_1B = [
    "pair_id",
    "j1_candidate_id",
    "j2_candidate_id",
    "target_phase_bin_deg",
    "output_phase_deg",
    "phase_error_deg",
    "s1_amp",
    "s2_amp",
    "s1_phase_deg",
    "s2_phase_deg",
    "target_x_amp",
    "leak_y_amp",
    "target_x_power",
    "leak_y_power",
    "predicted_ratio",
    "amp_match_score",
    "phase_match_score",
    "geometry_legal",
    "pairing_status",
    "reason",
]


def wrap180(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def wrap360(x: float) -> float:
    return x % 360.0


def angle_error(a: float, b: float) -> float:
    return abs(wrap180(a - b))


def as_float(value: object, default: float = math.nan) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def complex_from_amp_phase(amp: float, phase_deg: float) -> complex:
    return amp * cmath.exp(1j * math.radians(phase_deg))


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in csv.DictReader(f)]
    except Exception:
        return []


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def synthetic_j1() -> list[dict[str, str]]:
    rows = []
    for phase in PHASE_BINS_DEG:
        rows.append(
            {
                "candidate_id": f"SMOKE_J1_ID_{phase:03d}",
                "A": "0.500000",
                "phi_deg": f"{phase:.6f}",
                "geometry_legal": "true",
            }
        )
    return rows


def synthetic_j2() -> list[dict[str, str]]:
    rows = []
    for phase in PHASE_BINS_DEG:
        rows.append(
            {
                "candidate_id": f"SMOKE_J2_HWP_{phase:03d}",
                "tx_amp": "0.500000",
                "common_phase_deg": f"{phase:.6f}",
                "reusable_status": "smoke_synthetic_only",
                "reason": "synthetic HWP-like row for formula smoke test only",
            }
        )
    return rows


def load_real_j1_candidates(result_path: Path | None = None) -> list[dict[str, str]]:
    if result_path is None:
        result_path = J1_DIR / "j1_identity_results.csv"
    rows = read_csv(result_path)
    out: list[dict[str, str]] = []
    for row in rows:
        candidate_id = row.get("candidate_id", "")
        tx_amp = as_float(row.get("tx_amp"), math.nan)
        ty_amp = as_float(row.get("ty_amp"), math.nan)
        amp = (tx_amp + ty_amp) / 2.0 if not math.isnan(tx_amp) and not math.isnan(ty_amp) else math.nan
        if math.isnan(amp):
            amp = math.sqrt(max(as_float(row.get("T_mean"), math.nan), 0.0))
        phi = as_float(row.get("common_phase_deg"), math.nan)
        if candidate_id and not math.isnan(amp) and not math.isnan(phi):
            out.append(
                {
                    "candidate_id": candidate_id,
                    "A": f"{amp:.6f}",
                    "phi_deg": f"{phi:.6f}",
                    "geometry_legal": row.get("geometry_legal", "true") or "true",
                }
            )
    return out


def load_real_j2_candidates(inventory_path: Path | None = None) -> list[dict[str, str]]:
    if inventory_path is None:
        inventory_path = PAIR_DIR / "j2_reuse_inventory.csv"
    rows = read_csv(inventory_path)
    out: list[dict[str, str]] = []
    for row in rows:
        if row.get("reusable_status") not in {"reusable_final", "reusable_seed_only"}:
            continue
        amp = as_float(row.get("tx_amp"), math.nan)
        phi = as_float(row.get("common_phase_deg"), math.nan)
        if row.get("candidate_id") and not math.isnan(amp) and not math.isnan(phi):
            out.append(row)
    return out


def load_stage11_j1_s1(result_path: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in read_csv(result_path):
        if row.get("extraction_status") != "ok":
            continue
        tx_amp = as_float(row.get("tx_amp"))
        ty_amp = as_float(row.get("ty_amp"))
        tx_phase = as_float(row.get("tx_phase_deg"))
        ty_phase = as_float(row.get("ty_phase_deg"))
        if any(math.isnan(v) for v in [tx_amp, ty_amp, tx_phase, ty_phase]):
            continue
        tx = complex_from_amp_phase(tx_amp, tx_phase)
        ty = complex_from_amp_phase(ty_amp, ty_phase)
        s1 = (tx + ty) / 2.0
        out.append({"candidate_id": row.get("candidate_id", ""), "s": s1, "geometry_legal": "true"})
    return out


def load_stage11_j2_s2(inventory_path: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for row in read_csv(inventory_path):
        if row.get("reusable_status") not in {"reusable_final", "reusable_seed_only"}:
            continue
        tx_amp = as_float(row.get("tx_amp"))
        ty_amp = as_float(row.get("ty_amp"))
        tx_phase = as_float(row.get("tx_phase_deg"))
        ty_phase = as_float(row.get("ty_phase_deg"))
        if any(math.isnan(v) for v in [tx_amp, ty_amp, tx_phase, ty_phase]):
            continue
        tx = complex_from_amp_phase(tx_amp, tx_phase)
        ty = complex_from_amp_phase(ty_amp, ty_phase)
        s2 = (tx - ty) / 2.0
        out.append({"candidate_id": row.get("candidate_id", ""), "s": s2, "reusable_status": row.get("reusable_status", ""), "reason": row.get("reason", "")})
    return out


def pair_rows_stage11_1b(j1_rows: list[dict[str, object]], j2_rows: list[dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for j1 in j1_rows:
        for j2 in j2_rows:
            s1 = complex(j1["s"])
            s2 = complex(j2["s"])
            target = s1 + s2
            leak = s1 - s2
            target_amp = abs(target)
            leak_amp = abs(leak)
            target_power = target_amp * target_amp
            leak_power = leak_amp * leak_amp
            ratio = target_power / max(leak_power, EPS)
            output_phase = wrap360(math.degrees(cmath.phase(target))) if target_amp > EPS else math.nan
            nearest = min(PHASE_BINS_DEG, key=lambda b: angle_error(output_phase, b)) if not math.isnan(output_phase) else 0
            phase_error = angle_error(output_phase, nearest) if not math.isnan(output_phase) else math.nan
            s1_amp = abs(s1)
            s2_amp = abs(s2)
            amp_match = max(0.0, 1.0 - abs(s1_amp - s2_amp) / max(s1_amp, s2_amp, EPS))
            phase_score = max(0.0, 1.0 - phase_error / 30.0) if not math.isnan(phase_error) else 0.0
            if j2.get("reusable_status") == "reusable_final":
                status = "real_j1_real_j2_static_only"
                reason = "real J1 pilot and real J2 Stage11-1B single-pillar rows; static Jones/phasor prediction only, no dimer FDTD"
            elif j2.get("reusable_status") == "reusable_seed_only":
                status = "real_j1_seed_j2_only"
                reason = "real J1 pilot with seed-only J2; not a final LP-APCD dimer candidate"
            else:
                status = "rejected"
                reason = "J2 not reusable"
            rows.append(
                {
                    "pair_id": f"LPPAIR1B_{len(rows)+1:05d}",
                    "j1_candidate_id": str(j1.get("candidate_id", "")),
                    "j2_candidate_id": str(j2.get("candidate_id", "")),
                    "target_phase_bin_deg": str(nearest),
                    "output_phase_deg": fmt(output_phase),
                    "phase_error_deg": fmt(phase_error),
                    "s1_amp": fmt(s1_amp),
                    "s2_amp": fmt(s2_amp),
                    "s1_phase_deg": fmt(wrap360(math.degrees(cmath.phase(s1))) if s1_amp > EPS else math.nan),
                    "s2_phase_deg": fmt(wrap360(math.degrees(cmath.phase(s2))) if s2_amp > EPS else math.nan),
                    "target_x_amp": fmt(target_amp),
                    "leak_y_amp": fmt(leak_amp),
                    "target_x_power": fmt(target_power),
                    "leak_y_power": fmt(leak_power),
                    "predicted_ratio": fmt(ratio),
                    "amp_match_score": fmt(amp_match),
                    "phase_match_score": fmt(phase_score),
                    "geometry_legal": str(j1.get("geometry_legal", "true")),
                    "pairing_status": status,
                    "reason": reason,
                }
            )
    rows.sort(key=lambda r: (int(r["target_phase_bin_deg"]), as_float(r["phase_error_deg"], 999.0), -as_float(r["predicted_ratio"], 0.0)))
    return rows


def pair_rows(j1_rows: list[dict[str, str]], j2_rows: list[dict[str, str]], smoke: bool, pilot: bool = False) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for j1 in j1_rows:
        for j2 in j2_rows:
            a1 = as_float(j1.get("A"), 0.0)
            a2 = as_float(j2.get("tx_amp"), 0.0)
            phi1 = as_float(j1.get("phi_deg"), 0.0)
            phi2 = as_float(j2.get("common_phase_deg"), 0.0)
            s1 = a1 * cmath.exp(1j * math.radians(phi1))
            s2 = a2 * cmath.exp(1j * math.radians(phi2))
            target = s1 + s2
            leak = s1 - s2
            target_amp = abs(target)
            leak_amp = abs(leak)
            target_power = target_amp * target_amp
            leak_power = leak_amp * leak_amp
            ratio = target_power / max(leak_power, EPS)
            output_phase = wrap360(math.degrees(cmath.phase(target))) if target_amp > EPS else math.nan
            nearest = min(PHASE_BINS_DEG, key=lambda b: angle_error(output_phase, b)) if not math.isnan(output_phase) else 0
            phase_error = angle_error(output_phase, nearest) if not math.isnan(output_phase) else math.nan
            amp_score = max(0.0, 1.0 - abs(a1 - a2) / max(a1, a2, EPS))
            phase_score = max(0.0, 1.0 - phase_error / 30.0) if not math.isnan(phase_error) else 0.0
            if smoke:
                status = "smoke_synthetic_only"
            elif pilot:
                status = "pilot_with_seed_j2_only"
            else:
                status = "static_pairing_candidate"
            reason = (
                "synthetic smoke row; validates LP-APCD formula only and must not be treated as a real candidate"
                if smoke
                else (
                    "pilot uses real J1 rows but J2 inventory has no reusable_final rows; seed-only J2 means no final LP-APCD dimer claim"
                    if pilot
                    else "static pairing estimate from available J1/J2 optical rows; requires real dimer FDTD validation"
                )
            )
            rows.append(
                {
                    "pair_id": f"LPPAIR_{len(rows)+1:05d}",
                    "j1_candidate_id": j1.get("candidate_id", ""),
                    "j2_candidate_id": j2.get("candidate_id", ""),
                    "target_phase_bin_deg": f"{nearest}",
                    "output_phase_deg": fmt(output_phase),
                    "phase_error_deg": fmt(phase_error),
                    "A1": fmt(a1),
                    "A2": fmt(a2),
                    "phi1_deg": fmt(phi1),
                    "phi2_deg": fmt(phi2),
                    "target_x_amp": fmt(target_amp),
                    "leak_y_amp": fmt(leak_amp),
                    "target_x_power": fmt(target_power),
                    "leak_y_power": fmt(leak_power),
                    "predicted_ratio": fmt(ratio),
                    "amp_match_score": fmt(amp_score),
                    "phase_match_score": fmt(phase_score),
                    "geometry_legal": j1.get("geometry_legal", "true"),
                    "pairing_status": status,
                    "reason": reason,
                }
            )
    rows.sort(key=lambda r: (int(r["target_phase_bin_deg"]), as_float(r["phase_error_deg"], 999.0), -as_float(r["predicted_ratio"], 0.0)))
    return rows


def fmt(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.6f}"


def write_phase_summary(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# Stage11-0 LP Phase Bin Summary",
        "",
        "| bin_deg | candidate_count | best_pair_id | best_predicted_ratio | best_phase_error_deg | status |",
        "|---:|---:|---|---:|---:|---|",
    ]
    for bin_deg in PHASE_BINS_DEG:
        subset = [row for row in rows if row["target_phase_bin_deg"] == str(bin_deg)]
        if subset:
            best = sorted(subset, key=lambda r: (as_float(r["phase_error_deg"], 999.0), -as_float(r["predicted_ratio"], 0.0)))[0]
            status = best["pairing_status"]
            lines.append(
                f"| {bin_deg} | {len(subset)} | {best['pair_id']} | {best['predicted_ratio']} | {best['phase_error_deg']} | {status} |"
            )
        else:
            lines.append(f"| {bin_deg} | 0 |  |  |  | missing |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation(path: Path, smoke: bool, pair_count: int, pilot: bool = False) -> None:
    if smoke:
        mode = "smoke synthetic formula validation"
    elif pilot:
        mode = "pilot real-J1 with seed-only J2 inventory"
    else:
        mode = "static available-data pairing"
    text = f"""# Stage11-0 LP Pairing Static Validation

mode = {mode}
pair_count = {pair_count}

本文件只验证 LP-APCD J1/J2 pairing 的静态计算框架。

- 未启动 Lumerical。
- 未完成真实 dimer FDTD。
- 未证明 K=6 steering。
- synthetic 数据仅用于 smoke test，不得作为正式物理 candidate。
- pilot_with_seed_j2_only 仅表示真实 J1 pilot 可与 seed-only J2 做静态公式检查；J2 当前 reusable_final = 0 时不得声称 final LP-APCD dimer。
- 下一步需要真实 J1 tx/ty 提取结果后再进行 pair ranking。

LP-APCD 逻辑：J1 提供 identity-like 通道；J2 提供 HWP-like 通道；二者在 x 输入相长，在 y 输入相消；后续通过 common phase / propagation phase / resonance phase 做相位梯度。

本分支不把 LP 定向称为 photonic spin Hall effect，也不默认使用纯 PB phase 做 LP steering。
"""
    path.write_text(text, encoding="utf-8")


def write_validation_stage11_1b(path: Path, pair_count: int) -> None:
    text = f"""# Stage11-1B LP Pairing Static Validation

mode = real J1 + real J2 static Jones/phasor pairing
pair_count = {pair_count}

- J1 identity-like channel uses `s1 = (tx_complex + ty_complex) / 2`.
- J2 HWP-like channel uses `s2 = (tx_complex - ty_complex) / 2`.
- `real_j1_real_j2_static_only` means both sides are real single-pillar FDTD pilot rows, but still no dimer FDTD.
- This is not LP-APCD dimer validation and not K=6 steering proof.
- No K=6 full FDTD was launched.
- No dimer FDTD was launched.
"""
    path.write_text(text, encoding="utf-8")


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_layout_png(path: Path) -> None:
    width, height = 1400, 420
    pixels = bytearray([255, 255, 255] * width * height)

    def set_px(x: int, y: int, c: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            i = 3 * (y * width + x)
            pixels[i : i + 3] = bytes(c)

    def rect(x0: int, y0: int, x1: int, y1: int, c: tuple[int, int, int], fill: bool = True) -> None:
        for y in range(max(0, y0), min(height, y1)):
            for x in range(max(0, x0), min(width, x1)):
                if fill or x in (x0, x1 - 1) or y in (y0, y1 - 1):
                    set_px(x, y, c)

    def circle(cx: int, cy: int, r: int, c: tuple[int, int, int]) -> None:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    set_px(x, y, c)

    y0 = 130
    cell_w = 190
    start_x = 110
    for i, phase in enumerate(PHASE_BINS_DEG):
        x0 = start_x + i * cell_w
        rect(x0, y0, x0 + 155, y0 + 120, (235, 245, 255), True)
        rect(x0, y0, x0 + 155, y0 + 120, (30, 90, 160), False)
        circle(x0 + 58, y0 + 60, 26, (80, 150, 210))
        rect(x0 + 82, y0 + 35, x0 + 118, y0 + 85, (230, 120, 80), True)
        for b in range(phase // 60 + 1):
            rect(x0 + 18 + b * 14, y0 + 96, x0 + 26 + b * 14, y0 + 110, (30, 90, 160), True)
    # border line for supercell
    rect(start_x - 20, y0 - 25, start_x + 6 * cell_w - 35, y0 + 145, (80, 80, 80), False)

    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height))
    data = b"\x89PNG\r\n\x1a\n"
    data += _png_chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += _png_chunk(b"IDAT", zlib.compress(raw, 9))
    data += _png_chunk(b"IEND", b"")
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="use minimal synthetic J1/J2 data for formula and output smoke test")
    parser.add_argument("--j1-results", default=None)
    parser.add_argument("--j2-inventory", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--stage11-1b", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else PAIR_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.stage11_1b:
        if not args.j1_results or not args.j2_inventory:
            raise SystemExit("--stage11-1b requires --j1-results and --j2-inventory")
        j1_complex = load_stage11_j1_s1(Path(args.j1_results))
        j2_complex = load_stage11_j2_s2(Path(args.j2_inventory))
        rows = pair_rows_stage11_1b(j1_complex, j2_complex) if j1_complex and j2_complex else []
        write_csv(out_dir / "lp_pair_candidates_stage11_1b.csv", rows, PAIR_FIELDS_STAGE11_1B)
        write_phase_summary(out_dir / "lp_phase_bin_summary_stage11_1b.md", rows)
        write_validation_stage11_1b(out_dir / "lp_pairing_static_validation_stage11_1b.md", len(rows))
        write_layout_png(out_dir / "lp_k6_layout_topview.png")
        print(f"lp_pair_candidates={len(rows)}")
        print("mode=stage11_1b_real_j1_real_j2_static")
        print(f"supercell_period_nm={SUPERCELL_PERIOD_NM:.6f}")
        print("no_lumerical=true")
        return 0

    if args.smoke:
        j1_rows = synthetic_j1()
        j2_rows = synthetic_j2()
    else:
        j1_rows = load_real_j1_candidates(Path(args.j1_results) if args.j1_results else None)
        j2_rows = load_real_j2_candidates(Path(args.j2_inventory) if args.j2_inventory else None)

    rows = pair_rows(j1_rows, j2_rows, smoke=args.smoke, pilot=args.pilot) if j1_rows and j2_rows else []
    if not rows and not args.smoke:
        rows = [
            {
                "pair_id": "LPPAIR_NONE_00000",
                "j1_candidate_id": "",
                "j2_candidate_id": "",
                "target_phase_bin_deg": "",
                "output_phase_deg": "",
                "phase_error_deg": "",
                "A1": "",
                "A2": "",
                "phi1_deg": "",
                "phi2_deg": "",
                "target_x_amp": "",
                "leak_y_amp": "",
                "target_x_power": "",
                "leak_y_power": "",
                "predicted_ratio": "",
                "amp_match_score": "",
                "phase_match_score": "",
                "geometry_legal": "",
                "pairing_status": "not_ready",
                "reason": "no real J1 tx/ty extraction rows and/or parseable J2 inventory rows available",
            }
        ]

    suffix = "_pilot" if args.pilot else ""
    write_csv(out_dir / f"lp_pair_candidates{suffix}.csv", rows, PAIR_FIELDS)
    write_phase_summary(out_dir / f"lp_phase_bin_summary{suffix}.md", rows)
    write_validation(out_dir / f"lp_pairing_static_validation{suffix}.md", args.smoke, len(rows), pilot=args.pilot)
    write_layout_png(out_dir / "lp_k6_layout_topview.png")
    print(f"lp_pair_candidates={len(rows)}")
    mode = "smoke_synthetic_only" if args.smoke else ("pilot_with_seed_j2_only" if args.pilot else "static_available_data")
    print(f"mode={mode}")
    print(f"supercell_period_nm={SUPERCELL_PERIOD_NM:.6f}")
    print("no_lumerical=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
