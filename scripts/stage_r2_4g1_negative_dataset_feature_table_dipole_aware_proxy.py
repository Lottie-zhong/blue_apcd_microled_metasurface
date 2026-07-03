#!/usr/bin/env python3
"""R2-4G1 negative dataset feature table for dipole-aware proxy.

Python-only. Reads lightweight CSV/JSON/MD artifacts only. No Lumerical/lumapi/FDTD/FSP.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4g1_negative_dataset_feature_table_dipole_aware_proxy"
INPUTS = {
    "G0": ROOT / "outputs" / "r2_4g0_dipole_aware_proxy_spec_minimal_validation_plan",
    "D7": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary",
    "D8": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign",
    "E1": ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan",
    "E2": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard",
    "E3": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction",
    "F0": ROOT / "outputs" / "r2_4f0_literature_seeded_relaxed_target_rcled_mdc_scan",
    "F1": ROOT / "outputs" / "r2_4f1_f0_0781_tri_point_xdipole_fdtd_guard",
    "F2": ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard",
    "F3": ROOT / "outputs" / "r2_4f3_f0_shortlist_fdtd_failure_audit_proxy_breakdown",
}
CANDIDATES = ["D5_BASE_13461", "E1_0236", "F0_0781", "F0_0204"]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def first(rows: list[dict[str, str]], candidate_id: str | None = None) -> dict[str, str]:
    if candidate_id is None:
        return rows[0] if rows else {}
    for row in rows:
        if row.get("candidate_id") == candidate_id:
            return row
    return {}


def num(row: dict[str, str], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", "missing", "n/a"):
            try:
                return float(value)
            except Exception:
                pass
    return None


def text(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return "missing"


def ratio(a: float | None, b: float | None) -> str:
    if a is None or b is None or abs(b) < 1e-15:
        return "missing"
    return f"{a / b:.6g}"


def delta(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "missing"
    return f"{a - b:.6g}"


def flag(v: bool) -> str:
    return "true" if v else "false"


def build_dataset() -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    f0 = read_csv(INPUTS["F0"] / "r2_4f0_shortlist.csv")
    e1 = read_csv(INPUTS["E1"] / "r2_4e1_shortlist.csv")
    f3_tax = read_csv(INPUTS["F3"] / "r2_4f3_failure_taxonomy.csv")
    g0_neg = read_csv(INPUTS["G0"] / "r2_4g0_existing_negative_dataset.csv")

    measured = {
        "D5_BASE_13461": first(read_csv(INPUTS["D7"] / "r2_4d7_xline_average_metrics.csv")),
        "E1_0236": first(read_csv(INPUTS["E2"] / "r2_4e2_tri_point_incoherent_average.csv")),
        "F0_0781": first(read_csv(INPUTS["F1"] / "r2_4f1_tri_point_incoherent_average.csv")),
        "F0_0204": first(read_csv(INPUTS["F2"] / "r2_4f2_tri_point_incoherent_average.csv")),
    }
    proxy = {
        "D5_BASE_13461": {},
        "E1_0236": first(e1, "E1_0236"),
        "F0_0781": first(f0, "F0_0781"),
        "F0_0204": first(f0, "F0_0204"),
    }
    g0 = {r.get("candidate_id", ""): r for r in g0_neg}
    tax = {r.get("candidate_id", ""): r for r in f3_tax}

    rows: list[dict[str, Any]] = []
    missing_by_candidate: dict[str, list[str]] = {}
    for cid in CANDIDATES:
        m = measured[cid]
        p = proxy[cid]
        g = g0.get(cid, {})
        t = tax.get(cid, {})
        source_stage = "D-series" if cid.startswith("D5") else "E1" if cid.startswith("E1") else "F0"
        fdtd_stage = {"D5_BASE_13461": "R2-4D7", "E1_0236": "R2-4E2", "F0_0781": "R2-4F1", "F0_0204": "R2-4F2"}[cid]
        measured_peak = num(m, "tri_point_avg_peak_abs_angle_deg", "xline_avg_peak_abs_angle_deg", "peak_abs_angle_deg")
        measured_fwhm = num(m, "tri_point_avg_fwhm_deg", "xline_avg_angular_FWHM_deg", "angular_FWHM_deg")
        normal_offaxis = num(m, "tri_point_avg_normal_offaxis_ratio", "xline_avg_normal_offaxis_ratio", "normal_offaxis_ratio")
        eta5 = num(m, "tri_point_avg_eta_5deg", "eta5")
        eta10 = num(m, "tri_point_avg_eta_10deg", "eta10")
        eta20 = num(m, "tri_point_avg_eta_20deg", "eta20")
        eta30 = num(m, "tri_point_avg_eta_30deg", "eta30")
        off30 = num(m, "tri_point_avg_offaxis_30_40_fraction", "xline_avg_offaxis_30_40_fraction", "offaxis_30_40_fraction")
        off45 = num(m, "tri_point_avg_offaxis_45_55_fraction", "xline_avg_offaxis_45_55_fraction", "offaxis_45_55_fraction")
        off40 = num(m, "tri_point_avg_offaxis_40_60_fraction", "xline_avg_offaxis_40_60_fraction", "offaxis_40_60_fraction")
        std = num(m, "source_position_peak_abs_std_deg")
        row = {
            "candidate_id": cid,
            "route_or_family": text(p, "route_name", "family_id") if p else text(g, "route_or_family"),
            "source_of_candidate": source_stage,
            "proxy_source_stage": "not_available" if not p else source_stage,
            "fdtd_validation_stage": fdtd_stage,
            "proxy_spectral_fwhm_nm": text(p, "spectral_FWHM_proxy_nm", "spectral_fwhm_proxy_nm"),
            "proxy_angular_fwhm_deg": text(p, "angular_FWHM_proxy_deg", "angular_fwhm_proxy_deg"),
            "proxy_peak_abs_angle_deg": text(p, "peak_abs_angle_proxy_deg", "peak_abs_angle_deg"),
            "proxy_normal_offaxis": text(p, "normal_offaxis_proxy"),
            "proxy_30_40_penalty": text(p, "offaxis_30_40_lobe_penalty"),
            "proxy_45_55_penalty": text(p, "faroffaxis_45_55_lobe_penalty"),
            "proxy_40_60_penalty": text(p, "broad_40_60_faroffaxis_penalty"),
            "measured_tri_point_peak_abs_angle_deg": "missing" if measured_peak is None else measured_peak,
            "measured_tri_point_fwhm_deg": "missing" if measured_fwhm is None else measured_fwhm,
            "measured_normal_offaxis": "missing" if normal_offaxis is None else normal_offaxis,
            "measured_eta5": "missing" if eta5 is None else eta5,
            "measured_eta10": "missing" if eta10 is None else eta10,
            "measured_eta20": "missing" if eta20 is None else eta20,
            "measured_eta30": "missing" if eta30 is None else eta30,
            "measured_30_40_fraction": "missing" if off30 is None else off30,
            "measured_45_55_fraction": "missing" if off45 is None else off45,
            "measured_40_60_fraction": "missing" if off40 is None else off40,
            "source_position_peak_std_deg": "missing" if std is None else std,
            "bilateral_asymmetry_metric": text(m, "bilateral_asymmetry_metric"),
            "center_vs_bilateral_mismatch_metric": text(m, "center_vs_bilateral_mismatch_metric"),
            "failure_type_primary": text(t, "failure_type") if t else text(g, "failure_type"),
            "failure_type_secondary": secondary_failure(cid, measured_peak, measured_fwhm, normal_offaxis, off30, off45, off40, std),
            "stopped_status": text(g, "stop_status") if g else "stopped",
            "do_not_rerun_reason": do_not_rerun_reason(cid),
        }
        missing_by_candidate[cid] = [k for k, v in row.items() if v == "missing"]
        rows.append(row)
    return rows, missing_by_candidate


def secondary_failure(cid: str, peak: float | None, fwhm: float | None, ratio_v: float | None, off30: float | None, off45: float | None, off40: float | None, std: float | None) -> str:
    tags = []
    if peak is not None and peak > 8: tags.append("near_normal_failure")
    if fwhm is not None and fwhm > 20: tags.append("broad_fwhm")
    if ratio_v is not None and ratio_v <= 1: tags.append("normal_offaxis_le_1")
    if off30 is not None and off30 >= 0.25: tags.append("30_40_lobe")
    if off45 is not None and off45 >= 0.25: tags.append("45_55_lobe")
    if off40 is not None and off40 >= 0.30: tags.append("40_60_broad_lobe")
    if std is not None and std > 5: tags.append("source_position_instability")
    if cid in {"D5_BASE_13461", "F0_0204"}: tags.append("center_vs_xline_mismatch")
    return ";".join(tags) if tags else "missing"


def do_not_rerun_reason(cid: str) -> str:
    return {
        "D5_BASE_13461": "D7/D8 show center-only false positive and x-line instability; old D5 route stopped",
        "E1_0236": "E2/E3 show stable 49-52 deg far-offaxis channel; no retry",
        "F0_0781": "F1 shows off-normal around 26 deg and broad 40-60 channel; no 5/9-point continuation",
        "F0_0204": "F2 shows severe 46-67 deg faroffaxis and broad FWHM; F0 shortlist fully failed",
    }[cid]


def build_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        peak = as_float(r["measured_tri_point_peak_abs_angle_deg"])
        fwhm = as_float(r["measured_tri_point_fwhm_deg"])
        ratio_v = as_float(r["measured_normal_offaxis"])
        off30 = as_float(r["measured_30_40_fraction"])
        off45 = as_float(r["measured_45_55_fraction"])
        off40 = as_float(r["measured_40_60_fraction"])
        std = as_float(r["source_position_peak_std_deg"])
        cid = str(r["candidate_id"])
        thirty = off30 is not None and off30 >= 0.25
        fortyfive = off45 is not None and off45 >= 0.25
        broad = off40 is not None and off40 >= 0.30
        source_instability = std is not None and std > 5
        center_false = cid == "D5_BASE_13461" or (cid == "F0_0204" and source_instability)
        stable_far = cid in {"E1_0236", "F0_0204"} or (peak is not None and peak >= 40 and not source_instability)
        proxy_false = cid in {"E1_0236", "F0_0781", "F0_0204"}
        spectral_success_angular_fail = str(r["proxy_spectral_fwhm_nm"]) not in {"missing", "n/a"} and peak is not None and peak > 8
        guards = []
        if peak is not None and peak > 8: guards.append("peak_abs_guard")
        if fwhm is not None and fwhm > 20: guards.append("angular_fwhm_guard")
        if ratio_v is not None and ratio_v <= 1: guards.append("normal_offaxis_lower_bound")
        if thirty: guards.append("30_40_window_penalty")
        if fortyfive: guards.append("45_55_window_penalty")
        if broad: guards.append("40_60_broad_window_penalty")
        if source_instability: guards.append("source_position_stability_penalty")
        out.append({
            "candidate_id": cid,
            "near_normal_failure_flag": flag(peak is not None and peak > 8),
            "broad_fwhm_failure_flag": flag(fwhm is not None and fwhm > 20),
            "thirty_forty_lobe_failure_flag": flag(thirty),
            "fortyfive_fiftyfive_lobe_failure_flag": flag(fortyfive),
            "broad_40_60_failure_flag": flag(broad),
            "source_position_instability_flag": flag(source_instability),
            "center_only_false_positive_flag": flag(center_false),
            "stable_faroffaxis_channel_flag": flag(stable_far),
            "proxy_false_positive_flag": flag(proxy_false),
            "spectral_proxy_success_but_angular_failure_flag": flag(spectral_success_angular_fail),
            "route_risk_label": route_risk_label(peak, fwhm, ratio_v, off40, source_instability),
            "recommended_proxy_guard_update": ";".join(guards) if guards else "missing",
        })
    return out


def as_float(v: Any) -> float | None:
    try:
        if v in (None, "", "missing", "n/a"):
            return None
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def route_risk_label(peak: float | None, fwhm: float | None, ratio_v: float | None, off40: float | None, source_instability: bool) -> str:
    if peak is not None and peak >= 40:
        return "severe_faroffaxis_high_risk"
    if off40 is not None and off40 >= 0.30:
        return "broad_offaxis_high_risk"
    if source_instability:
        return "source_position_high_risk"
    if ratio_v is not None and ratio_v <= 1:
        return "normal_offaxis_high_risk"
    return "negative_sample"


def build_mismatch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        proxy_peak = as_float(r["proxy_peak_abs_angle_deg"])
        proxy_fwhm = as_float(r["proxy_angular_fwhm_deg"])
        proxy_ratio = as_float(r["proxy_normal_offaxis"])
        meas_peak = as_float(r["measured_tri_point_peak_abs_angle_deg"])
        meas_fwhm = as_float(r["measured_tri_point_fwhm_deg"])
        meas_ratio = as_float(r["measured_normal_offaxis"])
        flags = []
        for label, pkey, mkey in [
            ("30_40", "proxy_30_40_penalty", "measured_30_40_fraction"),
            ("45_55", "proxy_45_55_penalty", "measured_45_55_fraction"),
            ("40_60", "proxy_40_60_penalty", "measured_40_60_fraction"),
        ]:
            p = as_float(r[pkey]); m = as_float(r[mkey])
            if p is not None and m is not None and m > p:
                flags.append(f"{label}_underpredicted")
        out.append({
            "candidate_id": r["candidate_id"],
            "delta_peak_abs_angle": delta(meas_peak, proxy_peak),
            "fwhm_ratio_measured_over_proxy": ratio(meas_fwhm, proxy_fwhm),
            "normal_offaxis_ratio_measured_over_proxy": ratio(meas_ratio, proxy_ratio),
            "offaxis_penalty_underprediction_flags": ";".join(flags) if flags else "none_or_proxy_missing",
            "qualitative_mismatch_summary": mismatch_summary(r["candidate_id"]),
        })
    return out


def mismatch_summary(cid: str) -> str:
    return {
        "D5_BASE_13461": "no comparable complete proxy; center-only/x-line mismatch dominates",
        "E1_0236": "proxy predicted near-normal but FDTD found stable 49-52 deg faroffaxis channel",
        "F0_0781": "proxy predicted relaxed near-normal but FDTD found stable 26 deg off-normal broad channel",
        "F0_0204": "proxy predicted near-normal but FDTD found severe 46-67 deg faroffaxis and broad FWHM",
    }[cid]


def data_quality(rows: list[dict[str, Any]], missing_by_candidate: dict[str, list[str]]) -> str:
    lines = ["# R2-4G1 Data Quality Report", ""]
    critical = ["measured_tri_point_peak_abs_angle_deg", "measured_tri_point_fwhm_deg", "measured_normal_offaxis"]
    for r in rows:
        cid = str(r["candidate_id"])
        missing = missing_by_candidate[cid]
        critical_missing = [k for k in critical if r.get(k) == "missing"]
        exclude = "yes" if critical_missing else "no"
        lines += [
            f"## {cid}",
            f"- measured critical fields missing: {', '.join(critical_missing) if critical_missing else 'none'}",
            f"- all missing fields: {', '.join(missing) if missing else 'none'}",
            "- measured vs inferred: FDTD metrics are measured from existing lightweight result CSVs; failure labels are inferred from prior stage conclusions and measured thresholds; unavailable fields are marked missing.",
            f"- exclude from calibration: {exclude}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing_inputs = [f"{k}:{v}" for k, v in INPUTS.items() if not v.exists()]
    rows, missing_by_candidate = build_dataset()
    features = build_features(rows)
    mismatch = build_mismatch(rows)
    write_csv(OUT / "r2_4g1_unified_negative_dataset.csv", rows)
    write_csv(OUT / "r2_4g1_dipole_aware_feature_table.csv", features)
    write_csv(OUT / "r2_4g1_proxy_vs_fdtd_mismatch_table.csv", mismatch)
    write_text(OUT / "r2_4g1_data_quality_report.md", data_quality(rows, missing_by_candidate))
    write_text(OUT / "r2_4g1_g2_g3_planning.md", """
# R2-4G1 G2/G3 Planning

G2 is optional and not immediate. It requires explicit review/approval after G1.

G2 boundary:
- maximum 2 new candidates;
- tri-point x-dipole only;
- 453 nm only;
- no y/z/broadband;
- fail stops the candidate.

G3 boundary:
- update threshold/risk-score rules using G1 negatives plus any approved G2 calibration results;
- no new candidate generation until proxy thresholds are updated;
- output calibrated guards before G4 candidate generation.

Recommended G2 task name:
`R2-4G2_optional_minimal_dipole_proxy_calibration_fdtd_plan`

Recommended G3 task name:
`R2-4G3_update_dipole_aware_proxy_thresholds_from_negative_dataset`
""")
    write_text(OUT / "r2_4g1_stop_rules.md", """
# R2-4G1 Stop Rules

- Keep D5_BASE_13461 stopped.
- Keep E1_0236 stopped.
- Keep F0_0781 stopped.
- Keep F0_0204 stopped.
- No immediate FDTD after G1.
- No FDTD from current 1D stack/MDC proxy shortlist.
- No new candidate generation until G3 updates proxy thresholds.
- No y/z/broadband before tri-point x-dipole pass in any future route.
""")
    write_text(OUT / "r2_4g1_summary.md", f"""
# R2-4G1 Negative Dataset Feature Table

G1 unified {len(rows)} stopped negative samples into one calibration-oriented table and derived dipole-aware proxy failure flags.

One-line conclusion: the existing failures are usable as a small negative calibration set, but they do not justify immediate FDTD or new candidate generation.

Immediate FDTD allowed: no.

Recommended next tasks:
- `R2-4G2_optional_minimal_dipole_proxy_calibration_fdtd_plan` only after review;
- `R2-4G3_update_dipole_aware_proxy_thresholds_from_negative_dataset` before any G4 candidate generation.
""")
    write_json(OUT / "r2_4g1_manifest.json", {
        "stage": "R2-4G1 negative dataset feature table for dipole-aware proxy",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "missing_inputs": missing_inputs,
        "negative_sample_count": len(rows),
        "candidates": CANDIDATES,
        "immediate_fdtd_allowed": False,
        "recommended_G2_task": "R2-4G2_optional_minimal_dipole_proxy_calibration_fdtd_plan",
        "recommended_G3_task": "R2-4G3_update_dipole_aware_proxy_thresholds_from_negative_dataset",
    })
    print(json.dumps({"output": str(OUT), "negative_sample_count": len(rows), "missing_inputs": missing_inputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
