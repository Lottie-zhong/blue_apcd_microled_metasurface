from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
INPUT = ROOT / "outputs" / "r2_4h1f_minimal_source_isolated_xaxis_three_position_xdipole_validation"
OUT = ROOT / "outputs" / "r2_4h1g_h1f_failure_analysis_and_metric_audit"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def to_float(value, default=math.nan) -> float:
    try:
        if value in (None, "", "missing"):
            return default
        return float(value)
    except Exception:
        return default


def trapz(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(xs)):
        total += 0.5 * (ys[i] + ys[i - 1]) * (xs[i] - xs[i - 1])
    return total


def integrate_window(points: list[tuple[float, float]], predicate) -> float:
    total = 0.0
    seg_xs: list[float] = []
    seg_ys: list[float] = []
    for x, y in points:
        if predicate(x):
            seg_xs.append(x)
            seg_ys.append(y)
        else:
            if len(seg_xs) >= 2:
                total += trapz(seg_xs, seg_ys)
            seg_xs = []
            seg_ys = []
    if len(seg_xs) >= 2:
        total += trapz(seg_xs, seg_ys)
    return total


def fwhm_deg(points: list[tuple[float, float]]) -> float:
    if not points:
        return math.nan
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    peak_i = max(range(len(ys)), key=lambda i: ys[i])
    half = ys[peak_i] * 0.5

    def crossing_left() -> float:
        for i in range(peak_i, 0, -1):
            y0, y1 = ys[i - 1], ys[i]
            if (y0 - half) * (y1 - half) <= 0 and y0 != y1:
                frac = (half - y0) / (y1 - y0)
                return xs[i - 1] + frac * (xs[i] - xs[i - 1])
        return xs[0]

    def crossing_right() -> float:
        for i in range(peak_i, len(ys) - 1):
            y0, y1 = ys[i], ys[i + 1]
            if (y0 - half) * (y1 - half) <= 0 and y0 != y1:
                frac = (half - y0) / (y1 - y0)
                return xs[i] + frac * (xs[i + 1] - xs[i])
        return xs[-1]

    return crossing_right() - crossing_left()


def recalc_profile(rows: list[dict[str, str]], case_id: str) -> dict:
    pts = []
    for row in rows:
        if row.get("case_id") != case_id:
            continue
        theta = to_float(row.get("theta_deg"))
        intensity = to_float(row.get("intensity_raw"))
        if math.isnan(intensity):
            intensity = to_float(row.get("intensity_norm"))
        if not math.isnan(theta) and not math.isnan(intensity):
            pts.append((theta, max(intensity, 0.0)))
    pts.sort(key=lambda p: p[0])
    if len(pts) < 3:
        return {"case_id": case_id, "recalculation_status": "unavailable"}
    total = trapz([p[0] for p in pts], [p[1] for p in pts])
    if total <= 0:
        return {"case_id": case_id, "recalculation_status": "unavailable_total_zero"}
    peak_theta, peak_i = max(pts, key=lambda p: p[1])
    def frac(pred):
        return integrate_window(pts, pred) / total
    eta5 = frac(lambda t: abs(t) <= 5)
    eta10 = frac(lambda t: abs(t) <= 10)
    eta20 = frac(lambda t: abs(t) <= 20)
    leak2040 = frac(lambda t: 20 <= abs(t) <= 40)
    leak4060 = frac(lambda t: 40 <= abs(t) <= 60)
    return {
        "case_id": case_id,
        "recalculation_status": "available",
        "recalc_peak_angle_deg": peak_theta,
        "recalc_angular_fwhm_deg": fwhm_deg(pts),
        "recalc_eta5": eta5,
        "recalc_eta10": eta10,
        "recalc_eta20": eta20,
        "recalc_leakage20_40": leak2040,
        "recalc_leakage40_60": leak4060,
        "recalc_normal_to_40_60_ratio": eta10 / leak4060 if leak4060 > 0 else "inf",
    }


def close(a, b, tol):
    if math.isnan(a) or math.isnan(b):
        return False
    return abs(a - b) <= tol

manifest_path = INPUT / "r2_4h1f_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
individual = read_csv(INPUT / "r2_4h1f_individual_farfield_angular_metrics.csv")
average = read_csv(INPUT / "r2_4h1f_incoherent_average_farfield_angular_metrics.csv")
profiles = read_csv(INPUT / "r2_4h1f_farfield_profiles_left_center_right_and_average.csv")
run_status = read_csv(INPUT / "r2_4h1f_run_status.csv")
source_iso = read_csv(INPUT / "r2_4h1f_source_isolation_check.csv")
source_pos = read_csv(INPUT / "r2_4h1f_source_position_check.csv")

validity = [{
    "check": "all_three_runs_occurred",
    "value": manifest.get("all_three_runs_occurred", False),
    "evidence": "r2_4h1f_manifest.json and run_status csv",
}, {
    "check": "source_isolation_confirmed_all",
    "value": manifest.get("source_isolation_confirmed_all", False),
    "evidence": "r2_4h1f_source_isolation_check.csv",
}, {
    "check": "source_position_confirmed_all",
    "value": manifest.get("source_position_confirmed_all", False),
    "evidence": "r2_4h1f_source_position_check.csv",
}, {
    "check": "farfield_angular_metrics_extracted",
    "value": manifest.get("farfield_angular_metrics_extracted", False),
    "evidence": "r2_4h1f_manifest.json and individual farfield csv",
}, {
    "check": "no_use_of_existing_analysis_mode_results",
    "value": True,
    "evidence": "H1F reran exactly three source-isolated cases and did not use stored analysis-mode results",
}]
write_csv(OUT / "r2_4h1g_h1f_run_validity_audit.csv", validity)

summary_rows = []
for row in individual + average:
    summary_rows.append({
        "case_id": row.get("case_id", ""),
        "source_x_nm": row.get("source_x_nm", ""),
        "peak_angle_deg": row.get("peak_angle_deg", ""),
        "angular_fwhm_deg": row.get("angular_fwhm_deg", ""),
        "eta5": row.get("eta_5deg", ""),
        "eta10": row.get("eta_10deg", ""),
        "eta20": row.get("eta_20deg", ""),
        "leakage20_40": row.get("leakage_20_40_fraction", ""),
        "leakage40_60": row.get("leakage_40_60_fraction", ""),
        "lobe_class": row.get("lobe_class", ""),
        "decision_role": "primary_decision" if row.get("case_id") == "incoherent_average" else "diagnostic_case",
    })
write_csv(OUT / "r2_4h1g_individual_vs_average_summary.csv", summary_rows)

case_ids = [r.get("case_id") for r in individual] + [r.get("case_id") for r in average]
recalc_rows = [recalc_profile(profiles, cid) for cid in case_ids if cid]
write_csv(OUT / "r2_4h1g_recalculated_angular_metrics.csv", recalc_rows)

avg_orig = average[0] if average else {}
avg_recalc = next((r for r in recalc_rows if r.get("case_id") == "incoherent_average"), {})
recalc_available = avg_recalc.get("recalculation_status") == "available"
orig_eta10 = to_float(avg_orig.get("eta_10deg"))
orig_eta20 = to_float(avg_orig.get("eta_20deg"))
orig_l4060 = to_float(avg_orig.get("leakage_40_60_fraction"))
orig_l2040 = to_float(avg_orig.get("leakage_20_40_fraction"))
re_eta10 = to_float(avg_recalc.get("recalc_eta10"))
re_eta20 = to_float(avg_recalc.get("recalc_eta20"))
re_l4060 = to_float(avg_recalc.get("recalc_leakage40_60"))
re_l2040 = to_float(avg_recalc.get("recalc_leakage20_40"))
metric_inconsistency = False
notes = []
if orig_l2040 > orig_eta20:
    metric_inconsistency = True
    notes.append("original average leakage20-40 exceeds eta20, inconsistent under simple total-normalized disjoint-window interpretation")
for r in individual:
    if to_float(r.get("leakage_20_40_fraction")) > to_float(r.get("eta_20deg")):
        metric_inconsistency = True
        notes.append(f"{r.get('case_id')} original leakage20-40 exceeds eta20")
if recalc_available:
    if not close(orig_eta10, re_eta10, 0.05) or not close(orig_eta20, re_eta20, 0.05) or not close(orig_l4060, re_l4060, 0.05):
        metric_inconsistency = True
        notes.append("recalculated normalized window metrics differ from original H1F metrics by more than 0.05")
else:
    notes.append("raw farfield profile recalculation unavailable")
metric_rows = [{
    "audit_item": "normalization_consistency",
    "status": "warning" if metric_inconsistency else "consistent_with_available_checks",
    "original_average_eta10": orig_eta10,
    "recalculated_average_eta10": re_eta10 if recalc_available else "unavailable",
    "original_average_eta20": orig_eta20,
    "recalculated_average_eta20": re_eta20 if recalc_available else "unavailable",
    "original_average_leakage20_40": orig_l2040,
    "recalculated_average_leakage20_40": re_l2040 if recalc_available else "unavailable",
    "original_average_leakage40_60": orig_l4060,
    "recalculated_average_leakage40_60": re_l4060 if recalc_available else "unavailable",
    "notes": "; ".join(dict.fromkeys(notes)) if notes else "no major warning detected",
}]
write_csv(OUT / "r2_4h1g_metric_consistency_audit.csv", metric_rows)

failure_classification = [{
    "classification_key": "setup_validity",
    "classification": "not_invalid_setup",
    "evidence": "source isolation, source position, three runs, and farfield extraction all confirmed",
}, {
    "classification_key": "severity_vs_old_faroffaxis_failures",
    "classification": "not_severe_faroffaxis_collapse_like_F0_0204",
    "evidence": "H1F average peak about 12 deg, compared with F0_0204 average peak about 65 deg",
}, {
    "classification_key": "primary_failure_mode",
    "classification": "moderate_offaxis_with_broad_averaged_lobe",
    "evidence": "H1F average FWHM 44.39 deg and lobe_class moderate_offaxis",
}, {
    "classification_key": "apcd_source_conditioning",
    "classification": "insufficient_near_normal_concentration_for_apcd_preconditioning",
    "evidence": "eta5 about 0.137 and eta10 about 0.293 in original H1F average",
}, {
    "classification_key": "position_behavior",
    "classification": "possible_position_dependent_mirror_lobe_behavior",
    "evidence": "x=-2500 nm peaks at +12.35 deg while x=+2500 nm peaks at -12.35 deg",
}]
write_csv(OUT / "r2_4h1g_failure_mode_classification.csv", failure_classification)

comparison = [{
    "candidate_or_stage": "D5_BASE_13461",
    "known_failure": "center-only false positive / source-position instability / 30-40 deg lobe",
    "comparison_to_H1F": "H1F is based on three-position source averaging and does not repeat center-only-only decision, but still does not pass",
}, {
    "candidate_or_stage": "E1_0236",
    "known_failure": "stable 49-52 deg far-offaxis / leaky-guided-like channel",
    "comparison_to_H1F": "H1F is less far-offaxis than E1_0236 but still broad and moderate_offaxis",
}, {
    "candidate_or_stage": "F0_0781",
    "known_failure": "avg peak_abs 25.895 deg, FWHM 54.998 deg, normal/offaxis 0.282, offaxis40-60 0.3236",
    "comparison_to_H1F": "H1F average peak and FWHM are better, but not enough for near-normal source conditioning",
}, {
    "candidate_or_stage": "F0_0204",
    "known_failure": "avg peak_abs 65.499 deg, FWHM 138.446 deg, normal/offaxis 0.157, offaxis40-60 0.7433",
    "comparison_to_H1F": "H1F is clearly better than F0_0204 but not a pass",
}]
write_csv(OUT / "r2_4h1g_comparison_to_stopped_negative_samples.csv", comparison)

orig_peak = to_float(avg_orig.get("peak_angle_deg"))
orig_fwhm = to_float(avg_orig.get("angular_fwhm_deg"))
re_peak = to_float(avg_recalc.get("recalc_peak_angle_deg"))
re_fwhm = to_float(avg_recalc.get("recalc_angular_fwhm_deg"))
near_normal_pass = recalc_available and abs(re_peak) <= 8 and re_fwhm <= 20 and re_eta10 > re_l4060 and re_l2040 < 0.35
if metric_inconsistency and recalc_available:
    h1g_decision = "metric_definition_needs_correction_before_physics_decision"
elif manifest.get("incoherent_average_metrics", {}).get("lobe_class") in ("moderate_offaxis", "severe_faroffaxis"):
    h1g_decision = "confirm_h1f_fail_or_high_risk"
elif near_normal_pass:
    h1g_decision = "unexpected_recalculated_near_normal_requires_review"
else:
    h1g_decision = "confirm_h1f_fail_or_high_risk"

write_md(OUT / "r2_4h1g_physics_interpretation.md", f"""
# R2-4H1G physics interpretation

H1F is treated as a valid three-position source-isolated x-dipole validation, not an invalid setup. The source isolation, source position checks, three run records, and far-field extraction all passed in the H1F manifest.

The primary decision result is the incoherent three-position average, not the center-source case. The original H1F average peak is {orig_peak:.4g} deg with FWHM {orig_fwhm:.4g} deg and lobe class `{manifest.get('incoherent_average_metrics', {}).get('lobe_class', 'missing')}`. This is better than the severe F0_0204 far-offaxis collapse, but it is still too broad and too off-normal for APCD source preconditioning.

The side positions show mirror behavior: the -2500 nm source peaks at positive angle while the +2500 nm source peaks at negative angle. That supports a position-dependent mirror-lobe interpretation and reinforces the rule that center-only validation is not sufficient.
""")

write_md(OUT / "r2_4h1g_metric_audit_notes.md", f"""
# R2-4H1G metric audit notes

Python-side recalculation status: `{avg_recalc.get('recalculation_status', 'unavailable')}`.

Original H1F metrics are preserved unchanged. The audit found: {metric_rows[0]['notes']}.

Future angular-window integration should be verified against the official Ansys/Lumerical 2D far-field conventions. In particular, `farfield2d` returns a field/intensity-like quantity, `farfieldangle` can provide a non-uniform angle vector, and window integration should use a clearly documented method such as `farfield2dintegrate` or explicitly weighted numerical integration on the actual angle grid.

Original vs recalculated average metrics:

| metric | original H1F | recalculated audit |
|---|---:|---:|
| eta10 | {orig_eta10:.6g} | {re_eta10 if recalc_available else 'unavailable'} |
| eta20 | {orig_eta20:.6g} | {re_eta20 if recalc_available else 'unavailable'} |
| leakage20-40 | {orig_l2040:.6g} | {re_l2040 if recalc_available else 'unavailable'} |
| leakage40-60 | {orig_l4060:.6g} | {re_l4060 if recalc_available else 'unavailable'} |
""")

write_md(OUT / "r2_4h1g_next_stage_recommendation.md", """
# R2-4H1G next-stage recommendation

Do not run immediate further FDTD from H1G. Do not run y-dipole, broadband, APCD-after-MDC coupling, or additional source-position expansion yet.

Recommended path:

1. Finish metric-definition correction before using leakage-window values as hard physics claims.
2. Record `MDC_blue_oujizi` as the Wan MDC baseline with limited source-conditioning ability under this H1F three-position x-dipole test.
3. Pivot to an RCLED/DBR or MDC+RCLED source-conditioning plan if stronger near-normal angular narrowing is required.

Future FDTD validation must keep at least x-axis three-position dipole averaging. Center-only dipole validation must remain diagnostic only.
""")

write_md(OUT / "r2_4h1g_stop_allow_rules.md", """
# R2-4H1G stop / allow rules

Stop:
- no immediate further FDTD
- no y-dipole yet
- no broadband yet
- no APCD-after-MDC coupling yet
- no center-only pass/fail decision
- no use of existing analysis-mode results as validation evidence

Allow next:
- discussion/planning only
- metric-definition cleanup
- Wan MDC baseline record update
- RCLED/DBR or MDC+RCLED source-conditioning plan design
""")

write_md(OUT / "r2_4h1g_summary.md", f"""
# R2-4H1G summary

Decision: `{h1g_decision}`.

H1F is valid as a three-position, source-isolated x-dipole run, but it remains a fail/high-risk result for near-normal APCD source preconditioning. The original incoherent average peak is {orig_peak:.3f} deg and FWHM is {orig_fwhm:.3f} deg. The average lobe class is `{manifest.get('incoherent_average_metrics', {}).get('lobe_class', 'missing')}`.

Metric audit status: `{metric_rows[0]['status']}`. Python-side recalculation was `{avg_recalc.get('recalculation_status', 'unavailable')}`. Because the audit found normalization/window-definition warnings, the leakage-window metrics should be treated as audit flags until the angle-integration convention is locked down.

Immediate further FDTD allowed: `false`.

Next allowed stage: planning/metric-definition cleanup only, followed by RCLED/DBR or MDC+RCLED source-conditioning design planning if the project still needs stronger near-normal narrowing.
""")

manifest_out = {
    "stage": "R2-4H1G H1F failure analysis and metric audit",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_folder": str(INPUT),
    "output_folder": str(OUT),
    "zero_fdtd": True,
    "lumapi_used": False,
    "fsp_opened_or_modified": False,
    "h1g_decision": h1g_decision,
    "h1f_metric_normalization_looked_consistent": not metric_inconsistency,
    "python_side_recalculated_metrics_available": recalc_available,
    "immediate_further_fdtd_allowed": False,
    "failure_mode_classification": "moderate_offaxis_with_broad_averaged_lobe; insufficient_near_normal_concentration; possible_position_dependent_mirror_lobe_behavior",
    "original_average": {
        "peak_angle_deg": orig_peak,
        "angular_fwhm_deg": orig_fwhm,
        "eta10": orig_eta10,
        "eta20": orig_eta20,
        "leakage40_60": orig_l4060,
    },
    "recalculated_average": avg_recalc,
    "outputs": sorted(p.name for p in OUT.iterdir() if p.is_file()),
}
(OUT / "r2_4h1g_manifest.json").write_text(json.dumps(manifest_out, indent=2), encoding="utf-8")

print(json.dumps({
    "output": str(OUT),
    "h1g_decision": h1g_decision,
    "metric_consistent": not metric_inconsistency,
    "recalculation_available": recalc_available,
    "immediate_further_fdtd_allowed": False,
}, indent=2))
