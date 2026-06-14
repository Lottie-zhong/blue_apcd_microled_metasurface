from __future__ import annotations

import cmath
import csv
import math
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1e_h500_gap_closure"

J1_FILES = [
    ("stage11_1a_pilot", REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_fdtd_results_pilot.csv"),
    ("stage11_1d_patch", REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j1_identity_patch_fdtd_results_stage11_1d.csv"),
    ("stage11_1e_gap", OUT_DIR / "h500_j1_gap_closure_fdtd_results_stage11_1e.csv"),
]
J2_FILES = [
    ("stage11_1b_pilot", REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"),
    ("stage11_1d_patch", REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j2_hwp_patch_fdtd_results_stage11_1d.csv"),
    ("stage11_1e_gap", OUT_DIR / "h500_j2_gap_closure_fdtd_results_stage11_1e.csv"),
]
GEOM_FILES = [
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_plan.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j1_identity_patch_plan_stage11_1d.csv",
    OUT_DIR / "h500_j1_gap_closure_plan_stage11_1e.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_plan.csv",
    REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch" / "j2_hwp_patch_plan_stage11_1d.csv",
    OUT_DIR / "h500_j2_gap_closure_plan_stage11_1e.csv",
]

PAIR_CSV = OUT_DIR / "lp_pair_candidates_h500_stage11_1e_merged_reranked.csv"
SUMMARY_MD = OUT_DIR / "lp_h500_6bin_summary_stage11_1e.md"
LIB_CSV = OUT_DIR / "lp_h500_best_6bin_library_stage11_1e.csv"
GAP_MD = OUT_DIR / "lp_h500_gap_diagnosis_stage11_1e.md"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

PAIR_FIELDS = [
    "pair_id", "j1_candidate_id", "j2_candidate_id", "target_phase_bin_deg", "output_phase_deg", "phase_error_deg",
    "j1_height_nm", "j2_height_nm", "height_class", "same_height_pair", "fabrication_compatible_pair",
    "s1_amp", "s2_amp", "s1_phase_deg", "s2_phase_deg", "s1_s2_amp_ratio", "s1_s2_phase_mismatch_deg",
    "target_x_amp", "leak_y_amp", "target_x_power", "leak_y_power", "predicted_ratio",
    "phase_hit_loose", "phase_hit_strict", "ratio_pass_loose", "ratio_pass_strict", "ratio_pass_strong",
    "excellent_candidate", "target_power_pass", "j1_valid_loose", "j1_valid_strict", "j2_valid_loose",
    "j2_valid_strict", "pair_quality", "reason", "j1_source_stage", "j2_source_stage",
]

LIB_FIELDS = [
    "bin_deg", "pair_id", "j1_candidate_id", "j2_candidate_id", "height_nm", "j1_shape_family",
    "j2_length_nm", "j2_width_nm", "predicted_ratio", "phase_error_deg", "output_phase_deg",
    "target_x_power", "leak_y_power", "s1_amp", "s2_amp", "s1_phase_deg", "s2_phase_deg",
    "s1_s2_amp_ratio", "s1_s2_phase_mismatch_deg",
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


def b(value: bool) -> str:
    return "true" if value else "false"


def wrap180(value: float) -> float:
    return (value + 180.0) % 360.0 - 180.0


def wrap360(value: float) -> float:
    return value % 360.0


def angle_err(a: float, bin_deg: int) -> float:
    return abs(wrap180(a - bin_deg))


def cplx(amp: float, phase_deg: float) -> complex:
    return amp * cmath.exp(1j * math.radians(phase_deg))


def h500(row: dict[str, str]) -> bool:
    return abs(f(row.get("height_nm", row.get("j1_height_nm", ""))) - 500.0) <= 1.0


def geom_map() -> dict[str, dict[str, str]]:
    out = {}
    for path in GEOM_FILES:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if cid:
                out[cid] = row
    return out


def load_j1(geom: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    seen = set()
    for source, path in J1_FILES:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok" or not h500(row):
                continue
            seen.add(cid)
            tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
            ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
            s = (tx + ty) / 2.0
            g = geom.get(cid, {})
            rows.append({
                "id": cid,
                "source": source,
                "height": 500.0,
                "s": s,
                "valid_loose": row.get("identity_like_pass_loose") == "true",
                "valid_strict": row.get("identity_like_pass_strict") == "true",
                "shape": row.get("shape_family") or g.get("shape_family", ""),
            })
    return rows


def load_j2(geom: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    rows = []
    seen = set()
    for source, path in J2_FILES:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok" or not h500(row):
                continue
            seen.add(cid)
            tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
            ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
            s = (tx - ty) / 2.0
            g = geom.get(cid, {})
            rows.append({
                "id": cid,
                "source": source,
                "height": 500.0,
                "s": s,
                "valid_loose": row.get("hwp_like_pass_loose") == "true",
                "valid_strict": row.get("hwp_like_pass_strict") == "true",
                "length": row.get("length_nm", g.get("length_nm", "")),
                "width": row.get("width_nm", g.get("width_nm", "")),
            })
    return rows


def audit_pair(idx: int, j1: dict[str, object], j2: dict[str, object]) -> dict[str, str]:
    s1 = complex(j1["s"])
    s2 = complex(j2["s"])
    target = s1 + s2
    leak = s1 - s2
    target_amp = abs(target)
    leak_amp = abs(leak)
    target_power = target_amp * target_amp
    leak_power = leak_amp * leak_amp
    ratio = target_power / max(leak_power, EPS)
    out_phase = wrap360(math.degrees(cmath.phase(target))) if target_amp > EPS else math.nan
    nearest = min(PHASE_BINS, key=lambda x: angle_err(out_phase, x))
    phase_error = angle_err(out_phase, nearest)
    s1_amp = abs(s1)
    s2_amp = abs(s2)
    s1_phase = wrap360(math.degrees(cmath.phase(s1))) if s1_amp > EPS else math.nan
    s2_phase = wrap360(math.degrees(cmath.phase(s2))) if s2_amp > EPS else math.nan
    amp_ratio = min(s1_amp, s2_amp) / max(s1_amp, s2_amp, EPS)
    phase_mismatch = abs(wrap180(s2_phase - s1_phase))

    phase_loose = phase_error <= 15
    phase_strict = phase_error <= 8
    ratio_loose = ratio >= 3
    ratio_strict = ratio >= 6
    ratio_strong = ratio >= 10
    excellent = ratio >= 20 and phase_error <= 5 and target_power >= 0.20
    target_pass = target_power >= 0.20
    j1_loose = bool(j1["valid_loose"])
    j1_strict = bool(j1["valid_strict"])
    j2_loose = bool(j2["valid_loose"])
    j2_strict = bool(j2["valid_strict"])

    if j1_loose and j2_loose and phase_strict and ratio_strict and target_pass:
        quality = "strong_fab_candidate"
        reason = "H500 same-height, J1/J2 loose pass, strict phase, strict ratio, target power pass"
    elif phase_strict and not ratio_loose:
        quality = "weak_phase_only"
        reason = "phase bin hit but predicted ratio below loose threshold"
    else:
        quality = "rejected"
        reason = "fails phase, ratio, target power, or J1/J2 loose validity"

    return {
        "pair_id": f"LPPAIR1E_H500_{idx:06d}",
        "j1_candidate_id": str(j1["id"]),
        "j2_candidate_id": str(j2["id"]),
        "target_phase_bin_deg": str(nearest),
        "output_phase_deg": fmt(out_phase),
        "phase_error_deg": fmt(phase_error),
        "j1_height_nm": "500.000000",
        "j2_height_nm": "500.000000",
        "height_class": "fab_main",
        "same_height_pair": "true",
        "fabrication_compatible_pair": "true",
        "s1_amp": fmt(s1_amp),
        "s2_amp": fmt(s2_amp),
        "s1_phase_deg": fmt(s1_phase),
        "s2_phase_deg": fmt(s2_phase),
        "s1_s2_amp_ratio": fmt(amp_ratio),
        "s1_s2_phase_mismatch_deg": fmt(phase_mismatch),
        "target_x_amp": fmt(target_amp),
        "leak_y_amp": fmt(leak_amp),
        "target_x_power": fmt(target_power),
        "leak_y_power": fmt(leak_power),
        "predicted_ratio": fmt(ratio),
        "phase_hit_loose": b(phase_loose),
        "phase_hit_strict": b(phase_strict),
        "ratio_pass_loose": b(ratio_loose),
        "ratio_pass_strict": b(ratio_strict),
        "ratio_pass_strong": b(ratio_strong),
        "excellent_candidate": b(excellent),
        "target_power_pass": b(target_pass),
        "j1_valid_loose": b(j1_loose),
        "j1_valid_strict": b(j1_strict),
        "j2_valid_loose": b(j2_loose),
        "j2_valid_strict": b(j2_strict),
        "pair_quality": quality,
        "reason": reason,
        "j1_source_stage": str(j1["source"]),
        "j2_source_stage": str(j2["source"]),
    }


def audit() -> list[dict[str, str]]:
    geom = geom_map()
    j1_rows = load_j1(geom)
    j2_rows = load_j2(geom)
    rows = [audit_pair(i + 1, j1, j2) for i, (j1, j2) in enumerate((a, b) for a in j1_rows for b in j2_rows)]
    rows.sort(key=lambda r: (-f(r["predicted_ratio"]), f(r["phase_error_deg"]), -f(r["target_x_power"])))
    return rows


def best_strong(rows: list[dict[str, str]], bin_deg: int) -> dict[str, str] | None:
    sub = [r for r in rows if int(f(r["target_phase_bin_deg"])) == bin_deg and r["pair_quality"] == "strong_fab_candidate"]
    sub.sort(key=lambda r: (-f(r["predicted_ratio"]), f(r["phase_error_deg"]), -f(r["target_x_power"])))
    return sub[0] if sub else None


def best_any(rows: list[dict[str, str]], bin_deg: int) -> dict[str, str] | None:
    sub = [r for r in rows if int(f(r["target_phase_bin_deg"])) == bin_deg]
    sub.sort(key=lambda r: (-f(r["predicted_ratio"]), f(r["phase_error_deg"]), -f(r["target_x_power"])))
    return sub[0] if sub else None


def write_outputs(rows: list[dict[str, str]]) -> None:
    write_csv(PAIR_CSV, rows, PAIR_FIELDS)
    geom = geom_map()
    lib_rows = []
    lines = [
        "# Stage11-1E H500-Only 6-Bin Summary",
        "",
        "Evidence boundary: H500 same-height static Jones/phasor library candidates only. No dimer FDTD and no K=6 full FDTD.",
        "",
        "| bin_deg | candidate_count | best_strong_pair_id | best_ratio | phase_error_deg | target_x_power | leak_y_power | amp_ratio | phase_mismatch | pair_quality | status |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for bin_deg in PHASE_BINS:
        subset = [r for r in rows if int(f(r["target_phase_bin_deg"])) == bin_deg]
        r = best_strong(rows, bin_deg)
        status = "strong" if r else "missing_strong"
        if r is None:
            r = best_any(rows, bin_deg)
        if r is None:
            lines.append(f"| {bin_deg} | 0 |  |  |  |  |  |  |  |  | missing |")
            continue
        lines.append(
            f"| {bin_deg} | {len(subset)} | {r['pair_id'] if status == 'strong' else ''} | {r['predicted_ratio']} | {r['phase_error_deg']} | {r['target_x_power']} | {r['leak_y_power']} | {r['s1_s2_amp_ratio']} | {r['s1_s2_phase_mismatch_deg']} | {r['pair_quality']} | {status} |"
        )
        if status == "strong":
            j1g = geom.get(r["j1_candidate_id"], {})
            j2g = geom.get(r["j2_candidate_id"], {})
            lib_rows.append(
                {
                    "bin_deg": str(bin_deg),
                    "pair_id": r["pair_id"],
                    "j1_candidate_id": r["j1_candidate_id"],
                    "j2_candidate_id": r["j2_candidate_id"],
                    "height_nm": "500",
                    "j1_shape_family": j1g.get("shape_family", ""),
                    "j2_length_nm": j2g.get("length_nm", ""),
                    "j2_width_nm": j2g.get("width_nm", ""),
                    "predicted_ratio": r["predicted_ratio"],
                    "phase_error_deg": r["phase_error_deg"],
                    "output_phase_deg": r["output_phase_deg"],
                    "target_x_power": r["target_x_power"],
                    "leak_y_power": r["leak_y_power"],
                    "s1_amp": r["s1_amp"],
                    "s2_amp": r["s2_amp"],
                    "s1_phase_deg": r["s1_phase_deg"],
                    "s2_phase_deg": r["s2_phase_deg"],
                    "s1_s2_amp_ratio": r["s1_s2_amp_ratio"],
                    "s1_s2_phase_mismatch_deg": r["s1_s2_phase_mismatch_deg"],
                }
            )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(lib_rows) == 6:
        write_csv(LIB_CSV, lib_rows, LIB_FIELDS)
    else:
        write_csv(LIB_CSV, lib_rows, LIB_FIELDS)

    counts = Counter(r["pair_quality"] for r in rows)
    gap_lines = [
        "# Stage11-1E H500 Gap Diagnosis",
        "",
        f"strong_fab_candidate = {counts.get('strong_fab_candidate', 0)}",
        f"weak_phase_only = {counts.get('weak_phase_only', 0)}",
        f"ratio_pass_strict = {sum(1 for r in rows if r['ratio_pass_strict'] == 'true')}",
        f"ratio_pass_strong = {sum(1 for r in rows if r['ratio_pass_strong'] == 'true')}",
        "",
    ]
    for bin_deg in PHASE_BINS:
        strong = best_strong(rows, bin_deg)
        any_best = best_any(rows, bin_deg)
        if strong:
            gap_lines.append(f"- {bin_deg} deg: strong, pair={strong['pair_id']}, ratio={strong['predicted_ratio']}, phase_error={strong['phase_error_deg']}")
        elif any_best:
            gap_lines.append(
                f"- {bin_deg} deg: missing strong; best_raw={any_best['pair_id']}, ratio={any_best['predicted_ratio']}, phase_error={any_best['phase_error_deg']}, quality={any_best['pair_quality']}, amp_ratio={any_best['s1_s2_amp_ratio']}, phase_mismatch={any_best['s1_s2_phase_mismatch_deg']}"
            )
        else:
            gap_lines.append(f"- {bin_deg} deg: no candidate")
    GAP_MD.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")


def main() -> int:
    for _, path in J1_FILES + J2_FILES:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    rows = audit()
    write_outputs(rows)
    counts = Counter(r["pair_quality"] for r in rows)
    print(f"pair_count={len(rows)}")
    print(f"strong_fab_candidate={counts.get('strong_fab_candidate', 0)}")
    print(f"weak_phase_only={counts.get('weak_phase_only', 0)}")
    print(f"ratio_pass_strict={sum(1 for r in rows if r['ratio_pass_strict'] == 'true')}")
    print(f"ratio_pass_strong={sum(1 for r in rows if r['ratio_pass_strong'] == 'true')}")
    print(f"library_bins={sum(1 for b0 in PHASE_BINS if best_strong(rows, b0) is not None)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
