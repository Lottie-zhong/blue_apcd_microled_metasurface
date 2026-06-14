from __future__ import annotations

import cmath
import csv
import json
import math
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PAIR_DIR = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_pairing"
J1_CSV = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j1_identity_scan" / "j1_identity_fdtd_results_pilot.csv"
J2_CSV = REPO_ROOT / "outputs" / "blue10k6_lp_apcd_j2_hwp_scan" / "j2_hwp_fdtd_results_pilot.csv"
PAIR_CSV = PAIR_DIR / "lp_pair_candidates_stage11_1b.csv"

RERANKED_CSV = PAIR_DIR / "lp_pair_candidates_stage11_1c_reranked.csv"
SUMMARY_MD = PAIR_DIR / "lp_phase_bin_summary_stage11_1c_by_height.md"
GAP_MD = PAIR_DIR / "lp_pair_gap_diagnosis_stage11_1c.md"
RECOMMEND_CSV = PAIR_DIR / "lp_targeted_scan_recommendations_stage11_1c.csv"
VALIDATION_MD = PAIR_DIR / "lp_pairing_height_constraint_validation_stage11_1c.md"

PHASE_BINS = [0, 60, 120, 180, 240, 300]
EPS = 1e-12

FIELDS = [
    "pair_id",
    "j1_candidate_id",
    "j2_candidate_id",
    "target_phase_bin_deg",
    "output_phase_deg",
    "phase_error_deg",
    "j1_height_nm",
    "j2_height_nm",
    "height_class",
    "same_height_pair",
    "fabrication_compatible_pair",
    "cross_height_pair",
    "s1_amp",
    "s2_amp",
    "s1_phase_deg",
    "s2_phase_deg",
    "s1_s2_amp_ratio",
    "s1_s2_phase_mismatch_deg",
    "target_x_amp",
    "leak_y_amp",
    "target_x_power",
    "leak_y_power",
    "predicted_ratio",
    "phase_hit_loose",
    "phase_hit_strict",
    "ratio_pass_loose",
    "ratio_pass_strict",
    "ratio_pass_strong",
    "target_power_pass",
    "j1_valid_loose",
    "j1_valid_strict",
    "j2_valid_loose",
    "j2_valid_strict",
    "pair_quality",
    "reason",
]

REC_FIELDS = [
    "target_bin_deg",
    "height_nm",
    "problem_type",
    "best_existing_j1",
    "best_existing_j2",
    "j1_common_phase_deg",
    "j2_common_phase_deg",
    "s1_s2_amp_ratio",
    "s1_s2_phase_mismatch_deg",
    "current_best_ratio",
    "recommendation_type",
    "recommended_scan_family",
    "recommended_center_geometry",
    "recommended_parameter_patch",
    "priority",
    "notes",
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
    if height_nm <= 500 + 1e-6:
        return "fab_main"
    if abs(height_nm - 600.0) <= 1e-6:
        return "fab_compromise"
    return "sim_upper_bound"


def load_j1() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for row in read_csv(J1_CSV):
        if row.get("extraction_status") != "ok":
            continue
        tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
        ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
        s1 = (tx + ty) / 2.0
        out[row["candidate_id"]] = {
            "row": row,
            "s": s1,
            "height": f(row["height_nm"]),
            "valid_loose": row.get("identity_like_pass_loose") == "true",
            "valid_strict": row.get("identity_like_pass_strict") == "true",
            "common_phase": f(row.get("common_phase_deg")),
        }
    return out


def load_j2() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for row in read_csv(J2_CSV):
        if row.get("extraction_status") != "ok":
            continue
        tx = cplx(f(row["tx_amp"]), f(row["tx_phase_deg"]))
        ty = cplx(f(row["ty_amp"]), f(row["ty_phase_deg"]))
        s2 = (tx - ty) / 2.0
        out[row["candidate_id"]] = {
            "row": row,
            "s": s2,
            "height": f(row["height_nm"]),
            "valid_loose": row.get("hwp_like_pass_loose") == "true",
            "valid_strict": row.get("hwp_like_pass_strict") == "true",
            "common_phase": f(row.get("common_phase_deg")),
            "length": row.get("length_nm", ""),
            "width": row.get("width_nm", ""),
        }
    return out


def audit_pairs() -> list[dict[str, str]]:
    j1 = load_j1()
    j2 = load_j2()
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pair in read_csv(PAIR_CSV):
        j1_id = pair.get("j1_candidate_id", "")
        j2_id = pair.get("j2_candidate_id", "")
        if (j1_id, j2_id) in seen or j1_id not in j1 or j2_id not in j2:
            continue
        seen.add((j1_id, j2_id))
        s1 = complex(j1[j1_id]["s"])
        s2 = complex(j2[j2_id]["s"])
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
        h1 = float(j1[j1_id]["height"])
        h2 = float(j2[j2_id]["height"])
        same_h = abs(h1 - h2) <= 1.0
        if same_h:
            hc = height_class(h1)
        else:
            hc = "cross_height"
        fab = same_h and hc in {"fab_main", "fab_compromise"}
        cross = not same_h

        phase_loose = phase_error <= 15
        phase_strict = phase_error <= 8
        ratio_loose = ratio >= 3
        ratio_strict = ratio >= 6
        ratio_strong = ratio >= 10
        target_pass = target_power >= 0.20
        j1_loose = bool(j1[j1_id]["valid_loose"])
        j1_strict = bool(j1[j1_id]["valid_strict"])
        j2_loose = bool(j2[j2_id]["valid_loose"])
        j2_strict = bool(j2[j2_id]["valid_strict"])

        if fab and j1_loose and j2_loose and phase_strict and ratio_strict and target_pass:
            quality = "strong_fab_candidate"
            reason = "fabrication-compatible, phase strict, ratio strict, and target power pass"
        elif phase_strict and not ratio_loose:
            quality = "weak_phase_only"
            reason = "phase bin hit but predicted LP-APCD ratio is below loose threshold"
        elif (not fab) and phase_strict and ratio_loose:
            quality = "sim_trend_candidate"
            reason = "cross-height or non-fabrication trend only; not final experimental dimer"
        else:
            quality = "rejected"
            reason = "fails one or more phase, ratio, target power, J1/J2 validity, or height constraints"

        rows.append(
            {
                "pair_id": f"LPPAIR1C_{len(rows)+1:05d}",
                "j1_candidate_id": j1_id,
                "j2_candidate_id": j2_id,
                "target_phase_bin_deg": str(nearest),
                "output_phase_deg": fmt(out_phase),
                "phase_error_deg": fmt(phase_error),
                "j1_height_nm": fmt(h1),
                "j2_height_nm": fmt(h2),
                "height_class": hc,
                "same_height_pair": b(same_h),
                "fabrication_compatible_pair": b(fab),
                "cross_height_pair": b(cross),
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
            }
        )
    rows.sort(key=lambda r: (quality_rank(r["pair_quality"]), int(r["target_phase_bin_deg"]), f(r["phase_error_deg"]), -f(r["predicted_ratio"])))
    return rows


def quality_rank(q: str) -> int:
    return {"strong_fab_candidate": 0, "sim_trend_candidate": 1, "weak_phase_only": 2, "rejected": 3}.get(q, 9)


def subset(rows: list[dict[str, str]], group: str) -> list[dict[str, str]]:
    if group == "all_height_any":
        return rows
    if group == "same_height_any":
        return [r for r in rows if r["same_height_pair"] == "true"]
    if group == "H500_only":
        return [r for r in rows if r["same_height_pair"] == "true" and f(r["j1_height_nm"]) == 500 and f(r["j2_height_nm"]) == 500]
    if group == "H600_only":
        return [r for r in rows if r["same_height_pair"] == "true" and f(r["j1_height_nm"]) == 600 and f(r["j2_height_nm"]) == 600]
    if group == "H700_only":
        return [r for r in rows if r["same_height_pair"] == "true" and f(r["j1_height_nm"]) == 700 and f(r["j2_height_nm"]) == 700]
    if group == "fabrication_compatible_H500_H600":
        return [r for r in rows if r["fabrication_compatible_pair"] == "true"]
    raise ValueError(group)


def best_for_bin(rows: list[dict[str, str]], bin_deg: int, require_ratio: bool = False) -> dict[str, str] | None:
    candidates = [r for r in rows if r["target_phase_bin_deg"] == str(bin_deg)]
    if require_ratio:
        candidates = [r for r in candidates if r["ratio_pass_loose"] == "true"]
    if not candidates:
        return None
    candidates.sort(key=lambda r: (quality_rank(r["pair_quality"]), f(r["phase_error_deg"]), -f(r["predicted_ratio"]), -f(r["target_x_power"])))
    return candidates[0]


def write_summary(rows: list[dict[str, str]]) -> None:
    groups = ["all_height_any", "same_height_any", "H500_only", "H600_only", "H700_only", "fabrication_compatible_H500_H600"]
    lines = ["# Stage11-1C Height-Constrained Phase Bin Summary", ""]
    for group in groups:
        data = subset(rows, group)
        lines += [
            f"## {group}",
            "",
            "| bin_deg | candidate_count | best_pair_id | j1_candidate_id | j2_candidate_id | j1_h | j2_h | ratio | phase_err | target_power | leak_power | amp_ratio | phase_mismatch | pair_quality | status |",
            "|---:|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
        for bin_deg in PHASE_BINS:
            candidates = [r for r in data if r["target_phase_bin_deg"] == str(bin_deg)]
            best = best_for_bin(data, bin_deg)
            if best is None:
                lines.append(f"| {bin_deg} | 0 |  |  |  |  |  |  |  |  |  |  |  |  | missing |")
                continue
            ratio_hits = sum(1 for r in candidates if r["ratio_pass_loose"] == "true")
            phase_hits = sum(1 for r in candidates if r["phase_hit_strict"] == "true")
            status = "ratio_and_phase" if ratio_hits else ("phase_only" if phase_hits else "phase_bin_nearest_only")
            lines.append(
                f"| {bin_deg} | {len(candidates)} | {best['pair_id']} | {best['j1_candidate_id']} | {best['j2_candidate_id']} | {best['j1_height_nm']} | {best['j2_height_nm']} | {best['predicted_ratio']} | {best['phase_error_deg']} | {best['target_x_power']} | {best['leak_y_power']} | {best['s1_s2_amp_ratio']} | {best['s1_s2_phase_mismatch_deg']} | {best['pair_quality']} | {status} |"
            )
        lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def problem_type(best: dict[str, str] | None, bin_deg: int, group: str) -> str:
    if best is None:
        return "missing_j2_phase_anchor" if group.startswith("H") else "missing_j1_phase_anchor"
    if best["cross_height_pair"] == "true":
        return "cross_height_only"
    if best["target_x_power"] and f(best["target_x_power"]) < 0.20:
        return "weak_j1_Tmean"
    if f(best["s1_s2_amp_ratio"]) < 0.65:
        return "amplitude_mismatch"
    if f(best["s1_s2_phase_mismatch_deg"]) > 35:
        return "phase_mismatch"
    if f(best["predicted_ratio"]) < 3:
        return "phase_mismatch"
    return "missing_j2_phase_anchor"


def recommendations(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    groups = [("H500_only", 500), ("H600_only", 600), ("fabrication_compatible_H500_H600", 500)]
    for group, default_h in groups:
        data = subset(rows, group)
        for bin_deg in PHASE_BINS:
            best = best_for_bin(data, bin_deg)
            needs = best is None or best["pair_quality"] != "strong_fab_candidate"
            if not needs:
                continue
            ptype = problem_type(best, bin_deg, group)
            h = int(f(best["j1_height_nm"], default_h)) if best else default_h
            if h >= 700:
                h = 600
            priority = "highest_priority_gap" if bin_deg == 60 else ("high" if group in {"H500_only", "fabrication_compatible_H500_H600"} else "medium")
            if best and best["cross_height_pair"] == "true":
                ptype = "cross_height_only"
                priority = "high"
            if ptype in {"amplitude_mismatch", "weak_j1_Tmean"}:
                family = "J1 identity-like around current high-T square/circle anchors"
                patch = "vary diameter/side +/-20 nm and height-local common phase near target bin"
            else:
                family = "J2 rectangle_nanofin HWP-like local patch"
                patch = "scan L/W around best J2 with +/-10 nm and +/-20 nm, same height only"
            recs.append(
                {
                    "target_bin_deg": str(bin_deg),
                    "height_nm": str(h),
                    "problem_type": ptype,
                    "best_existing_j1": "" if best is None else best["j1_candidate_id"],
                    "best_existing_j2": "" if best is None else best["j2_candidate_id"],
                    "j1_common_phase_deg": "" if best is None else best["s1_phase_deg"],
                    "j2_common_phase_deg": "" if best is None else best["s2_phase_deg"],
                    "s1_s2_amp_ratio": "" if best is None else best["s1_s2_amp_ratio"],
                    "s1_s2_phase_mismatch_deg": "" if best is None else best["s1_s2_phase_mismatch_deg"],
                    "current_best_ratio": "" if best is None else best["predicted_ratio"],
                    "recommendation_type": "same_height_targeted_patch",
                    "recommended_scan_family": family,
                    "recommended_center_geometry": "" if best is None else json.dumps({"j1": best["j1_candidate_id"], "j2": best["j2_candidate_id"]}),
                    "recommended_parameter_patch": patch,
                    "priority": priority,
                    "notes": "Do not run dimer or K=6 FDTD before same-height single-pillar gap is improved.",
                }
            )
    recs.sort(key=lambda r: (0 if r["priority"] == "highest_priority_gap" else 1 if r["priority"] == "high" else 2, int(r["target_bin_deg"]), int(r["height_nm"])))
    return recs


def write_gap(rows: list[dict[str, str]], recs: list[dict[str, str]]) -> None:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["pair_quality"]] = counts.get(r["pair_quality"], 0) + 1
    fab = subset(rows, "fabrication_compatible_H500_H600")
    missing = []
    weak = []
    ratio = []
    for bin_deg in PHASE_BINS:
        b = [r for r in fab if r["target_phase_bin_deg"] == str(bin_deg)]
        if not b:
            missing.append(bin_deg)
        elif not any(r["ratio_pass_loose"] == "true" for r in b):
            weak.append(bin_deg)
        else:
            ratio.append(bin_deg)
    lines = [
        "# Stage11-1C Pair Gap Diagnosis",
        "",
        f"pair_quality_counts = {counts}",
        f"fabrication_compatible_ratio_bins = {ratio}",
        f"fabrication_compatible_phase_only_or_weak_bins = {weak}",
        f"fabrication_compatible_missing_bins = {missing}",
        "",
        "Interpretation:",
        "- Phase-bin hit alone is not LP-APCD selectivity.",
        "- High predicted_ratio requires s1_amp ~= s2_amp and s1_phase ~= s2_phase.",
        "- Cross-height pairs are simulation trends only and cannot enter a final experimental dimer library.",
        "- H700 rows are sim_upper_bound and should not be prioritized for the experimental phase-gradient library.",
        "",
        "Top recommendations:",
    ]
    for r in recs[:10]:
        lines.append(f"- bin {r['target_bin_deg']} H{r['height_nm']} {r['problem_type']} priority={r['priority']} ratio={r['current_best_ratio']}")
    GAP_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation(rows: list[dict[str, str]]) -> None:
    lines = [
        "# Stage11-1C Height Constraint Validation",
        "",
        "- No new FDTD was run.",
        "- No dimer FDTD was run.",
        "- No K=6 full FDTD was run.",
        "- Pair metrics were recomputed from real J1/J2 single-pillar complex amplitudes.",
        "- J1: s1 = (tx_complex + ty_complex) / 2.",
        "- J2: s2 = (tx_complex - ty_complex) / 2.",
        "- cross_height_pair rows are diagnostic only.",
        "- strong_fab_candidate requires fabrication-compatible same-height H500/H600, valid J1/J2, strict phase hit, ratio >= 6, and target power >= 0.20.",
        f"- audited_pair_count = {len(rows)}.",
    ]
    VALIDATION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    for path in [J1_CSV, J2_CSV, PAIR_CSV]:
        if not path.exists():
            raise SystemExit(f"missing required input: {path}")
    rows = audit_pairs()
    recs = recommendations(rows)
    write_csv(RERANKED_CSV, rows, FIELDS)
    write_summary(rows)
    write_csv(RECOMMEND_CSV, recs, REC_FIELDS)
    write_gap(rows, recs)
    write_validation(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["pair_quality"]] = counts.get(r["pair_quality"], 0) + 1
    print(f"audited_pair_count={len(rows)}")
    print("pair_quality_counts=" + json.dumps(counts, sort_keys=True))
    print(f"recommendation_count={len(recs)}")
    print(f"output={RERANKED_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
