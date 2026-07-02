from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4d3_cavity_phase_design_space_reset"
FIG = OUT / "figures"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"
D2 = ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize"
D1 = ROOT / "outputs" / "r2_4d1_xline_failure_diagnosis_proxy_correction"
D0 = ROOT / "outputs" / "r2_4d0_variable_dbr_xline_xdipole_position_scout"
OLD = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize"

REQUIRED = [
    D2 / "r2_4d2_all_candidate_metrics.csv",
    D2 / "r2_4d2_top20_candidate_metrics.csv",
    D2 / "r2_4d2_objective_term_breakdown.csv",
    D2 / "r2_4d2_corrected_proxy_thresholds.csv",
    D2 / "r2_4d2_rejected_candidate_failure_modes.csv",
    D2 / "r2_4d2_old_vs_corrected_proxy_comparison.csv",
    D2 / "r2_4d2_proxy_limitations.md",
    D2 / "r2_4d2_summary.md",
]

RULE_MAP = {
    "spectral_peak_outside_450_456": "spectral peak outside 450-456 nm",
    "spectral_fwhm_gt8": "spectral FWHM too broad",
    "spectral_fwhm_rule": "spectral FWHM too broad",
    "spectral_peak_rule": "spectral peak outside 450-456 nm",
    "peak_angle_gt7": "peak_abs_angle above threshold",
    "peak_angle_rule": "peak_abs_angle above threshold",
    "angular_fwhm_gt15": "angular FWHM too broad",
    "angular_fwhm_rule": "angular FWHM too broad",
    "normal5_below_population_threshold": "normal-window response too low",
    "normal10_below_population_threshold": "normal-window response too low",
    "offaxis20_60_above_threshold": "20-60 deg off-axis response too high",
    "offaxis30_40_above_threshold": "30-40 deg resonance risk too high",
    "30_40_resonance_risk": "30-40 deg resonance risk too high",
    "30_40_to_normal_above_threshold": "30-40 deg resonance risk too high",
    "multi_peak_risk": "multi-peak risk",
    "multi_peak_above_threshold": "multi-peak risk",
    "near_failed_family": "negative-sample similarity",
    "failed_family_distance_rule": "negative-sample similarity",
    "invalid_thickness_or_stack_height": "layer/fabrication constraint issue",
}
VAR_COLS = [
    "top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "top_termination_nm", "bottom_termination_nm",
    "top_high_scale", "top_low_scale", "bottom_high_scale", "bottom_low_scale", "top_chirp", "bottom_chirp",
]


def ensure_inputs() -> None:
    missing = [str(p) for p in REQUIRED if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required R2-4D2 files: " + "; ".join(missing))


def split_rules(value: str) -> list[str]:
    if not isinstance(value, str) or not value or value == "none":
        return []
    return [x for x in value.split(";") if x]


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    rows = list(rows)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def md_table(rows: list[dict], fields: list[str], max_rows: int = 20) -> str:
    if not rows:
        return "No rows."
    out = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in rows[:max_rows]:
        out.append("| " + " | ".join(str(r.get(f, "")) for f in fields) + " |")
    return "\n".join(out)


def strip_svg(path: Path) -> None:
    if path.suffix.lower() == ".svg":
        path.write_text(re.sub(r"[ \t]+(?=\n)", "", path.read_text(encoding="utf-8")), encoding="utf-8")


def fail_categories(rules: list[str]) -> set[str]:
    cats = set()
    for r in rules:
        cats.add(RULE_MAP.get(r, r))
    return cats


def cause_breakdown(df: pd.DataFrame) -> list[dict]:
    total = len(df)
    counter = Counter()
    for rules in df["failure_mode"].fillna("").map(split_rules):
        for cat in fail_categories(rules):
            counter[cat] += 1
    rows = []
    for cause, count in counter.most_common():
        rows.append({"cause": cause, "count": count, "percent_of_candidates": round(100 * count / max(total, 1), 3)})
    return rows


def near_pass(df: pd.DataFrame) -> pd.DataFrame:
    work = df[df.get("valid", True) == True].copy()
    work["failed_rule_count"] = work["failure_mode"].fillna("").map(lambda x: 0 if x == "none" else len(split_rules(x)))
    cols = [
        "candidate_id", "failed_rule_count", "failure_mode", "corrected_proxy_peak_abs_angle_deg",
        "corrected_proxy_angular_FWHM_deg", "normal_window_response_0_10", "offaxis_20_60_response",
        "offaxis_30_40_response", "corrected_normal_offaxis_ratio", "spectral_peak_nm_normal_window",
        "spectral_fwhm_nm_normal_window", "top_pair_count", "bottom_pair_count", "cavity_spacer_nm",
        "top_termination_nm", "bottom_termination_nm", "score",
    ]
    near = work.sort_values(["failed_rule_count", "score"], ascending=[True, False]).loc[:, cols].head(30)
    return near


def coverage_rows(df: pd.DataFrame, near: pd.DataFrame) -> list[dict]:
    specs = {
        "top_pair_count": (4, 10), "bottom_pair_count": (4, 12), "cavity_spacer_nm": (180, 360),
        "top_termination_nm": (0, 90), "bottom_termination_nm": (0, 90),
        "top_high_scale": (0.75, 1.25), "top_low_scale": (0.75, 1.25),
        "bottom_high_scale": (0.75, 1.25), "bottom_low_scale": (0.75, 1.25),
        "top_chirp": (-0.15, 0.15), "bottom_chirp": (-0.15, 0.15),
    }
    rows = []
    for col, (lo, hi) in specs.items():
        s = pd.to_numeric(df[col], errors="coerce")
        n = pd.to_numeric(near[col], errors="coerce") if col in near else pd.Series(dtype=float)
        width = hi - lo
        low_hit = float((s <= lo + 0.05 * width).mean())
        high_hit = float((s >= hi - 0.05 * width).mean())
        nmean = float(n.mean()) if len(n) else math.nan
        recommendation = "keep"
        if col == "cavity_spacer_nm":
            recommendation = "shift or expand cavity_spacer_nm; near-pass spectral peaks cluster away from 453"
        elif "termination" in col:
            recommendation = "allow independent termination material/thickness choices"
        elif "chirp" in col:
            recommendation = "allow stronger chirp/apodization only with off-axis guard"
        elif "pair_count" in col:
            recommendation = "constrain only after next focused phase sweep"
        elif "scale" in col:
            recommendation = "keep scale bounds but add phase/source-position surrogate"
        rows.append({
            "variable": col, "range_min": lo, "range_max": hi, "all_mean": round(float(s.mean()), 4),
            "all_min": round(float(s.min()), 4), "all_max": round(float(s.max()), 4),
            "near_pass_mean": round(nmean, 4) if not math.isnan(nmean) else "",
            "low_boundary_fraction": round(low_hit, 4), "high_boundary_fraction": round(high_hit, 4),
            "recommendation": recommendation,
        })
    rows.append({"variable": "source_position_fraction", "range_min": "not included", "range_max": "not included", "all_mean": "", "all_min": "", "all_max": "", "near_pass_mean": "", "low_boundary_fraction": "", "high_boundary_fraction": "", "recommendation": "add as an optimization variable or surrogate before FDTD shortlist"})
    rows.append({"variable": "aperture/source-position surrogate", "range_min": "not included", "range_max": "not included", "all_mean": "", "all_min": "", "all_max": "", "near_pass_mean": "", "low_boundary_fraction": "", "high_boundary_fraction": "", "recommendation": "add explicit x-line source-position risk surrogate"})
    return rows


def boundary_hit_summary(df: pd.DataFrame) -> list[dict]:
    rows = []
    for col in VAR_COLS:
        s = pd.to_numeric(df[col], errors="coerce")
        q = s.quantile([0.05, 0.5, 0.95]).to_dict()
        rows.append({"variable": col, "p05": round(float(q[0.05]), 4), "median": round(float(q[0.5]), 4), "p95": round(float(q[0.95]), 4)})
    return rows


def failure_rule_correlation(df: pd.DataFrame) -> list[dict]:
    rows = []
    for rule in sorted({r for x in df["failure_mode"].fillna("") for r in split_rules(x)}):
        mask = df["failure_mode"].fillna("").str.contains(re.escape(rule), regex=True)
        rows.append({
            "rule": rule, "count": int(mask.sum()),
            "mean_peak_abs": round(float(df.loc[mask, "corrected_proxy_peak_abs_angle_deg"].mean()), 4) if mask.any() else "",
            "mean_spectral_peak": round(float(df.loc[mask, "spectral_peak_nm_normal_window"].mean()), 4) if mask.any() else "",
            "mean_offaxis_20_60": round(float(df.loc[mask, "offaxis_20_60_response"].mean()), 8) if mask.any() else "",
        })
    return rows


def representative_phase(df: pd.DataFrame) -> list[dict]:
    reps = []
    best = df.iloc[0]
    reps.append(("best_R2_4D2", best))
    npass = near_pass(df)
    if len(npass):
        reps.append(("top_near_pass", df[df["candidate_id"] == npass.iloc[0]["candidate_id"]].iloc[0]))
    old_csv = OLD / "r2_4b_all_candidate_metrics.csv"
    if old_csv.exists():
        old = pd.read_csv(old_csv)
        for cid in ["R2_4B_OPT_06361", "R2_4B_OPT_06176"]:
            sub = old[old["candidate_id"] == cid]
            if len(sub):
                reps.append(("failed_old_proxy", sub.iloc[0]))
    rows = []
    for kind, r in reps:
        lam0 = float(r.get("model_lam0_nm", r.get("spectral_peak_nm_normal_window", math.nan)))
        spec_peak = float(r.get("spectral_peak_nm_normal_window", math.nan))
        peak = float(r.get("corrected_proxy_peak_abs_angle_deg", r.get("peak_angle_abs_deg_453", math.nan)))
        phase_cycles = (453.0 / lam0 - 1.0) if lam0 and not math.isnan(lam0) else math.nan
        rows.append({
            "representative": kind, "candidate_id": r.get("candidate_id", ""),
            "model_lam0_nm": round(lam0, 4) if not math.isnan(lam0) else "",
            "spectral_peak_nm": round(spec_peak, 4) if not math.isnan(spec_peak) else "",
            "peak_abs_angle_deg": round(peak, 4) if not math.isnan(peak) else "",
            "phase_proxy_cycles_at_453": round(phase_cycles, 6) if not math.isnan(phase_cycles) else "",
            "reachability_note": "metric-space phase proxy only; exact angle-dependent reflection phase was not stored in R2-4D2 CSV",
        })
    return rows


def make_figs(breakdown: list[dict], near: pd.DataFrame, coverage: list[dict], phase: list[dict]) -> list[str]:
    if plt is None:
        return []
    FIG.mkdir(parents=True, exist_ok=True)
    made = []
    def save(name):
        for ext in ["png", "svg"]:
            p = FIG / f"{name}.{ext}"
            plt.tight_layout(); plt.savefig(p, dpi=180); strip_svg(p); made.append(str(p))
        plt.close()
    if breakdown:
        labels = [r["cause"] for r in breakdown]
        vals = [r["count"] for r in breakdown]
        plt.figure(figsize=(8, 4)); plt.bar(range(len(vals)), vals); plt.xticks(range(len(vals)), labels, rotation=35, ha="right"); plt.ylabel("count"); save("r2_4d3_no_pass_cause_breakdown")
    if len(near):
        plt.figure(figsize=(6, 4)); plt.scatter(near["offaxis_20_60_response"], near["normal_window_response_0_10"], c=near["failed_rule_count"], s=35, cmap="viridis"); plt.xlabel("offaxis 20-60 response"); plt.ylabel("normal 0-10 response"); plt.colorbar(label="failed rules"); save("r2_4d3_near_pass_metric_scatter")
    cov = [r for r in coverage if isinstance(r.get("low_boundary_fraction"), float)]
    if cov:
        xs = np.arange(len(cov)); low = [r["low_boundary_fraction"] for r in cov]; high = [r["high_boundary_fraction"] for r in cov]
        plt.figure(figsize=(8, 4)); plt.bar(xs - .2, low, .4, label="low boundary"); plt.bar(xs + .2, high, .4, label="high boundary"); plt.xticks(xs, [r["variable"] for r in cov], rotation=35, ha="right"); plt.ylabel("fraction"); plt.legend(); save("r2_4d3_design_variable_coverage")
    if phase:
        plt.figure(figsize=(6, 4)); plt.scatter([r["peak_abs_angle_deg"] for r in phase if r["peak_abs_angle_deg"] != ""], [r["spectral_peak_nm"] for r in phase if r["spectral_peak_nm"] != ""], s=45); plt.xlabel("peak abs angle (deg)"); plt.ylabel("spectral/model peak (nm)"); save("r2_4d3_phase_reachability_map")
    return made


def update_index(route: str) -> None:
    marker = "## R2-4D3 cavity-phase and design-space reset"
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else "# RCLED MDC Workspace Index\n"
    block = f"""
{marker}
- Output: `outputs/r2_4d3_cavity_phase_design_space_reset`
- FDTD/Lumerical/lumapi: not run.
- Decision: {route}
- Stop: no R2-4D2 setup-only FSPs or FDTD for no-pass candidates.
"""
    if marker not in text:
        REPORT.write_text(text.rstrip() + "\n" + block, encoding="utf-8")


def main() -> None:
    ensure_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(D2 / "r2_4d2_all_candidate_metrics.csv")
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    breakdown = cause_breakdown(df)
    near = near_pass(df)
    coverage = coverage_rows(df, near)
    boundary = boundary_hit_summary(df)
    corr = failure_rule_correlation(df)
    phase = representative_phase(df)
    figs = make_figs(breakdown, near, coverage, phase)

    write_csv(OUT / "r2_4d3_no_pass_cause_breakdown.csv", breakdown, ["cause", "count", "percent_of_candidates"])
    near.to_csv(OUT / "r2_4d3_near_pass_candidates.csv", index=False)
    write_csv(OUT / "r2_4d3_design_variable_coverage.csv", coverage)
    write_csv(OUT / "r2_4d3_representative_candidate_phase_proxy.csv", phase)
    write_csv(OUT / "r2_4d3_variable_boundary_hit_summary.csv", boundary)
    write_csv(OUT / "r2_4d3_failure_rule_correlation.csv", corr)

    top_causes = breakdown[:5]
    dominant = top_causes[0]["cause"] if top_causes else "unknown"
    if any("spectral peak" in r["cause"] and r["percent_of_candidates"] > 40 for r in breakdown):
        route = "R2-4D4 focused cavity-phase sweep around normal-mode condition"
    elif any("off-axis" in r["cause"] and r["percent_of_candidates"] > 40 for r in breakdown):
        route = "R2-4D4 revised design-space optimization with stronger top-outcoupling/source-position surrogate"
    else:
        route = "R2-4D4 calibrated threshold and variable-space reset; keep negative-sample protections"

    (OUT / "r2_4d3_cavity_phase_reachability.md").write_text(
        "# R2-4D3 Cavity-phase Reachability\n\n"
        "Exact angle-dependent DeltaPhi(lambda, theta) cannot be reconstructed from the saved R2-4D2 CSV alone because phi_top(lambda, theta) and phi_bottom(lambda, theta) were not stored. "
        "I therefore used metric-space evidence plus the stored model_lam0/spectral peak as a simplified phase proxy.\n\n"
        + md_table(phase, ["representative", "candidate_id", "model_lam0_nm", "spectral_peak_nm", "peak_abs_angle_deg", "phase_proxy_cycles_at_453"]) +
        "\n\nEvidence: the best R2-4D2 candidates still drift away from the 450-456 nm target or retain 30-40 deg resonance risk. The current variable space can place narrow responses near 6-8 deg, but not with the required spectral centering and off-axis suppression simultaneously.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d3_threshold_sanity_analysis.md").write_text(
        "# R2-4D3 Threshold Sanity Analysis\n\n"
        "Essential protections to keep:\n"
        "\n- 20-60 deg off-axis penalty.\n- 30-40 deg resonance penalty.\n- minimum normal-window response.\n- no strong multi-peak behavior.\n\n"
        "Thresholds that may be too strict for proxy-only screening:\n"
        "\n- peak_abs <= 5 can remain preferred, but <= 7 is a practical first-screen maximum.\n- spectral peak 450-456 is physically motivated, but a temporary 448-458 scout band may diagnose phase reachability.\n- population-relative normal/off-axis thresholds rejected all candidates and should be calibrated with negative samples, not used blindly.\n\n"
        "Recommendation: do not relax the negative-sample protections; instead run a focused cavity-phase/variable-space reset to move spectral centering and angular risk together.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d3_next_route_decision.md").write_text(
        f"# R2-4D3 Next Route Decision\n\nPreferred next route: {route}.\n\n"
        "Reason: R2-4D2 no-pass is not a mere bookkeeping issue. The top candidates fail through spectral centering and residual off-axis-risk rules, so setup-only FSP generation would likely waste FDTD runtime.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d3_stop_decisions.md").write_text(
        "# R2-4D3 Stop Decisions\n\n"
        "- Do not generate R2-4D2 setup-only FSPs.\n"
        "- Do not run FDTD for R2-4D2 no-pass candidates.\n"
        "- Do not run z_outofplane or broadband spectral validation for rejected R2-4B/R2-4D2 candidates.\n"
        "- Do not continue old R2-4B top5 backup blindly.\n",
        encoding="utf-8",
    )
    summary = f"""# R2-4D3 Cavity-phase and Design-space Reset Analysis

No FDTD, Lumerical, lumapi, heavy files, or new large optimization was run.

## No-pass Cause Breakdown

{md_table(breakdown, ["cause", "count", "percent_of_candidates"], 12)}

## Near-pass Candidates

{md_table(near.to_dict('records'), ["candidate_id", "failed_rule_count", "failure_mode", "corrected_proxy_peak_abs_angle_deg", "corrected_proxy_angular_FWHM_deg", "spectral_peak_nm_normal_window", "spectral_fwhm_nm_normal_window", "score"], 10)}

## Design-variable Coverage

{md_table(coverage, ["variable", "all_mean", "near_pass_mean", "low_boundary_fraction", "high_boundary_fraction", "recommendation"], 14)}

## Threshold Sanity

Keep the negative-sample protections. The most suspicious proxy-only strictness is population-relative thresholding and too-narrow spectral centering during exploratory diagnosis.

## Decision

Preferred next route: {route}.

## Stop

No R2-4D2 FSP setup or FDTD should be run from the no-pass list.
"""
    (OUT / "r2_4d3_summary.md").write_text(summary, encoding="utf-8")
    debug = {
        "stage": "R2-4D3_cavity_phase_design_space_reset",
        "candidate_count": int(len(df)),
        "top_cause": dominant,
        "near_pass_count_exported": int(len(near)),
        "recommended_route": route,
        "figures": figs,
        "created_heavy_files": False,
    }
    (OUT / "r2_4d3_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    update_index(route)
    print(json.dumps(debug, indent=2))


if __name__ == "__main__":
    main()
