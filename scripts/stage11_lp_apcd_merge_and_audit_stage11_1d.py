from __future__ import annotations

import cmath
import csv
import math
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_stage11_1d_targeted_patch"
OLD_J1 = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_fdtd_results_pilot.csv"
OLD_J2 = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"
PATCH_J1 = OUT_DIR / "j1_identity_patch_fdtd_results_stage11_1d.csv"
PATCH_J2 = OUT_DIR / "j2_hwp_patch_fdtd_results_stage11_1d.csv"

PAIR_CSV = OUT_DIR / "lp_pair_candidates_stage11_1d_merged_reranked.csv"
SUMMARY_MD = OUT_DIR / "lp_phase_bin_summary_stage11_1d_by_height.md"
GAP_MD = OUT_DIR / "lp_gap_diagnosis_stage11_1d.md"
BEST_FAB_CSV = OUT_DIR / "lp_best_fab_candidates_stage11_1d.csv"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

FIELDS = [
    "pair_id", "j1_candidate_id", "j2_candidate_id", "target_phase_bin_deg", "output_phase_deg", "phase_error_deg",
    "j1_height_nm", "j2_height_nm", "height_class", "same_height_pair", "fabrication_compatible_pair",
    "cross_height_pair", "s1_amp", "s2_amp", "s1_phase_deg", "s2_phase_deg", "s1_s2_amp_ratio",
    "s1_s2_phase_mismatch_deg", "target_x_amp", "leak_y_amp", "target_x_power", "leak_y_power",
    "predicted_ratio", "phase_hit_loose", "phase_hit_strict", "ratio_pass_loose", "ratio_pass_strict",
    "ratio_pass_strong", "target_power_pass", "j1_valid_loose", "j1_valid_strict", "j2_valid_loose",
    "j2_valid_strict", "pair_quality", "reason", "j1_source_stage", "j2_source_stage",
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


def height_class(height_nm: float) -> str:
    if height_nm <= 500.0 + 1e-6:
        return "fab_main"
    if abs(height_nm - 600.0) <= 1e-6:
        return "fab_compromise"
    return "sim_upper_bound"


def load_j1() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for source, path in [("stage11_1a_pilot", OLD_J1), ("stage11_1d_patch", PATCH_J1)]:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok":
                continue
            seen.add(cid)
            h = f(row.get("height_nm"))
            if height_class(h) == "sim_upper_bound":
                continue
            tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
            ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
            s = (tx + ty) / 2.0
            rows.append(
                {
                    "id": cid,
                    "source": source,
                    "height": h,
                    "s": s,
                    "valid_loose": row.get("identity_like_pass_loose") == "true",
                    "valid_strict": row.get("identity_like_pass_strict") == "true",
                }
            )
    return rows


def load_j2() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for source, path in [("stage11_1b_pilot", OLD_J2), ("stage11_1d_patch", PATCH_J2)]:
        for row in read_csv(path):
            cid = row.get("candidate_id", "")
            if not cid or cid in seen or row.get("extraction_status") != "ok":
                continue
            seen.add(cid)
            h = f(row.get("height_nm"))
            if height_class(h) == "sim_upper_bound":
                continue
            tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
            ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
            s = (tx - ty) / 2.0
            rows.append(
                {
                    "id": cid,
                    "source": source,
                    "height": h,
                    "s": s,
                    "valid_loose": row.get("hwp_like_pass_loose") == "true",
                    "valid_strict": row.get("hwp_like_pass_strict") == "true",
                }
            )
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
    h1 = float(j1["height"])
    h2 = float(j2["height"])
    same = abs(h1 - h2) <= 1.0
    hc = height_class(h1) if same else "cross_height"
    fab = same and hc in {"fab_main", "fab_compromise"}

    phase_loose = phase_error <= 15
    phase_strict = phase_error <= 8
    ratio_loose = ratio >= 3
    ratio_strict = ratio >= 6
    ratio_strong = ratio >= 10
    target_pass = target_power >= 0.20
    j1_loose = bool(j1["valid_loose"])
    j1_strict = bool(j1["valid_strict"])
    j2_loose = bool(j2["valid_loose"])
    j2_strict = bool(j2["valid_strict"])

    if fab and j1_loose and j2_loose and phase_strict and ratio_strict and target_pass:
        quality = "strong_fab_candidate"
        reason = "same-height H500/H600, J1/J2 loose pass, strict phase, strict ratio, target power pass"
    elif phase_strict and not ratio_loose:
        quality = "weak_phase_only"
        reason = "phase bin hit but predicted LP-APCD ratio is below loose threshold"
    elif (not fab) and phase_strict and ratio_loose:
        quality = "sim_trend_candidate"
        reason = "not fabrication-compatible; diagnostic only"
    else:
        quality = "rejected"
        reason = "fails one or more phase, ratio, target power, J1/J2 validity, or height constraints"

    return {
        "pair_id": f"LPPAIR1D_{idx:06d}",
        "j1_candidate_id": str(j1["id"]),
        "j2_candidate_id": str(j2["id"]),
        "target_phase_bin_deg": str(nearest),
        "output_phase_deg": fmt(out_phase),
        "phase_error_deg": fmt(phase_error),
        "j1_height_nm": fmt(h1),
        "j2_height_nm": fmt(h2),
        "height_class": hc,
        "same_height_pair": b(same),
        "fabrication_compatible_pair": b(fab),
        "cross_height_pair": b(not same),
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
    j1_rows = load_j1()
    j2_rows = load_j2()
    out: list[dict[str, str]] = []
    idx = 1
    for j1 in j1_rows:
        for j2 in j2_rows:
            if abs(float(j1["height"]) - float(j2["height"])) > 1.0:
                continue
            out.append(audit_pair(idx, j1, j2))
            idx += 1
    out.sort(key=lambda r: (-f(r["predicted_ratio"]), f(r["phase_error_deg"]), -f(r["target_x_power"])))
    return out


def best_by_bin(rows: list[dict[str, str]], height_nm: int | None = None) -> dict[int, dict[str, str] | None]:
    out: dict[int, dict[str, str] | None] = {}
    for bin_deg in PHASE_BINS:
        subset = [r for r in rows if int(f(r["target_phase_bin_deg"])) == bin_deg]
        if height_nm is not None:
            subset = [r for r in subset if abs(f(r["j1_height_nm"]) - height_nm) <= 1 and abs(f(r["j2_height_nm"]) - height_nm) <= 1]
        subset.sort(key=lambda r: (-f(r["predicted_ratio"]), f(r["phase_error_deg"]), -f(r["target_x_power"])))
        out[bin_deg] = subset[0] if subset else None
    return out


def append_summary_table(lines: list[str], title: str, rows: list[dict[str, str]], height_nm: int | None) -> None:
    lines += [
        f"## {title}",
        "",
        "| bin_deg | candidate_count | best_pair_id | J1 | J2 | H | ratio | phase_error | target_power | leak_power | amp_ratio | phase_mismatch | pair_quality | status |",
        "|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    best = best_by_bin(rows, height_nm)
    for bin_deg in PHASE_BINS:
        subset = [r for r in rows if int(f(r["target_phase_bin_deg"])) == bin_deg]
        if height_nm is not None:
            subset = [r for r in subset if abs(f(r["j1_height_nm"]) - height_nm) <= 1 and abs(f(r["j2_height_nm"]) - height_nm) <= 1]
        r = best[bin_deg]
        if r is None:
            lines.append(f"| {bin_deg} | 0 |  |  |  | {height_nm or ''} |  |  |  |  |  |  |  | missing |")
        else:
            status = "ratio_pass" if r["ratio_pass_loose"] == "true" else ("phase_only" if r["phase_hit_strict"] == "true" else "best_available")
            lines.append(
                f"| {bin_deg} | {len(subset)} | {r['pair_id']} | {r['j1_candidate_id']} | {r['j2_candidate_id']} | {r['j1_height_nm']} | {r['predicted_ratio']} | {r['phase_error_deg']} | {r['target_x_power']} | {r['leak_y_power']} | {r['s1_s2_amp_ratio']} | {r['s1_s2_phase_mismatch_deg']} | {r['pair_quality']} | {status} |"
            )
    lines.append("")


def write_outputs(rows: list[dict[str, str]]) -> None:
    write_csv(PAIR_CSV, rows, FIELDS)
    fab = [r for r in rows if r["fabrication_compatible_pair"] == "true"]
    write_csv(BEST_FAB_CSV, fab[:200], FIELDS)
    counts = Counter(r["pair_quality"] for r in rows)
    ratio_loose = sum(1 for r in rows if r["ratio_pass_loose"] == "true")
    ratio_strict = sum(1 for r in rows if r["ratio_pass_strict"] == "true")
    ratio_strong = sum(1 for r in rows if r["ratio_pass_strong"] == "true")
    lines = [
        "# Stage11-1D Same-Height Merged Pairing Summary",
        "",
        "Only H500/H600 same-height pairs are ranked for fabrication-compatible candidates.",
        "",
        f"pair_count = {len(rows)}",
        f"strong_fab_candidate = {counts.get('strong_fab_candidate', 0)}",
        f"weak_phase_only = {counts.get('weak_phase_only', 0)}",
        f"rejected = {counts.get('rejected', 0)}",
        f"ratio_pass_loose = {ratio_loose}",
        f"ratio_pass_strict = {ratio_strict}",
        f"ratio_pass_strong = {ratio_strong}",
        "",
    ]
    append_summary_table(lines, "H500_only", rows, 500)
    append_summary_table(lines, "H600_only", rows, 600)
    append_summary_table(lines, "fabrication-compatible H500/H600", rows, None)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    old_h500_60 = 0.110504
    old_h600_60 = 0.232297
    h500_60 = best_by_bin(rows, 500)[60]
    h600_60 = best_by_bin(rows, 600)[60]
    gap_lines = [
        "# Stage11-1D Gap Diagnosis",
        "",
        "Stage11-1D evaluates ratio improvement, not phase-bin hit alone.",
        "",
        f"old H500 60deg best ratio = {old_h500_60:.6f}",
        f"new H500 60deg best ratio = {h500_60['predicted_ratio'] if h500_60 else 'missing'}",
        f"old H600 60deg best ratio = {old_h600_60:.6f}",
        f"new H600 60deg best ratio = {h600_60['predicted_ratio'] if h600_60 else 'missing'}",
        "",
        "High predicted_ratio requires s1_amp approximately s2_amp and s1_phase approximately s2_phase.",
        "A strict phase-bin hit without ratio pass remains a weak_phase_only candidate.",
    ]
    for label, r in [("H500 60deg", h500_60), ("H600 60deg", h600_60)]:
        if r:
            gap_lines += [
                "",
                f"## {label} best",
                f"- pair_id = {r['pair_id']}",
                f"- ratio = {r['predicted_ratio']}",
                f"- phase_error_deg = {r['phase_error_deg']}",
                f"- s1_s2_amp_ratio = {r['s1_s2_amp_ratio']}",
                f"- s1_s2_phase_mismatch_deg = {r['s1_s2_phase_mismatch_deg']}",
                f"- pair_quality = {r['pair_quality']}",
            ]
    GAP_MD.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")


def main() -> int:
    for path in [OLD_J1, OLD_J2, PATCH_J1, PATCH_J2]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    rows = audit()
    write_outputs(rows)
    counts = Counter(r["pair_quality"] for r in rows)
    print(f"pair_count={len(rows)}")
    print(f"strong_fab_candidate={counts.get('strong_fab_candidate', 0)}")
    print(f"weak_phase_only={counts.get('weak_phase_only', 0)}")
    print(f"ratio_pass_loose={sum(1 for r in rows if r['ratio_pass_loose'] == 'true')}")
    print(f"ratio_pass_strict={sum(1 for r in rows if r['ratio_pass_strict'] == 'true')}")
    print(f"ratio_pass_strong={sum(1 for r in rows if r['ratio_pass_strong'] == 'true')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
