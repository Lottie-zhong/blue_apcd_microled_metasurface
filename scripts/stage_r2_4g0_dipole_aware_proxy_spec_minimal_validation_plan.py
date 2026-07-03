#!/usr/bin/env python3
"""R2-4G0 dipole-aware proxy specification and minimal validation plan.

Python-only planning package. Reads only lightweight CSV/JSON/MD artifacts.
No Lumerical, lumapi, FDTD, FSP, training, or candidate generation.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4g0_dipole_aware_proxy_spec_minimal_validation_plan"

INPUTS = {
    "D7": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary",
    "D8": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign",
    "E2": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard",
    "E3": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction",
    "F0": ROOT / "outputs" / "r2_4f0_literature_seeded_relaxed_target_rcled_mdc_scan",
    "F1": ROOT / "outputs" / "r2_4f1_f0_0781_tri_point_xdipole_fdtd_guard",
    "F2": ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard",
    "F3": ROOT / "outputs" / "r2_4f3_f0_shortlist_fdtd_failure_audit_proxy_breakdown",
}


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


def val(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return "missing"


def negative_dataset() -> list[dict[str, Any]]:
    f0 = read_csv(INPUTS["F0"] / "r2_4f0_shortlist.csv")
    d7_avg = first(read_csv(INPUTS["D7"] / "r2_4d7_xline_average_metrics.csv"))
    e2_avg = first(read_csv(INPUTS["E2"] / "r2_4e2_tri_point_incoherent_average.csv"))
    f1_avg = first(read_csv(INPUTS["F1"] / "r2_4f1_tri_point_incoherent_average.csv"))
    f2_avg = first(read_csv(INPUTS["F2"] / "r2_4f2_tri_point_incoherent_average.csv"))
    f0_0781_proxy = first(f0, "F0_0781")
    f0_0204_proxy = first(f0, "F0_0204")

    rows = [
        {
            "candidate_id": "D5_BASE_13461",
            "route_or_family": "D5_PRIMARY variable DBR stack",
            "proxy_prediction_summary": "old proxy/center-oriented candidate; D7 showed x-line failure",
            "measured_tri_point_peak_abs_deg": val(d7_avg, "xline_avg_peak_abs_angle_deg", "peak_abs_angle_deg"),
            "measured_FWHM_deg": val(d7_avg, "xline_avg_angular_FWHM_deg", "angular_FWHM_deg"),
            "normal_offaxis_ratio": val(d7_avg, "xline_avg_normal_offaxis_ratio", "normal_offaxis_ratio"),
            "offaxis_30_40_fraction": val(d7_avg, "xline_avg_offaxis_30_40_fraction", "offaxis_30_40_fraction"),
            "offaxis_45_55_fraction": val(d7_avg, "xline_avg_offaxis_45_55_fraction", "offaxis_45_55_fraction"),
            "offaxis_40_60_fraction": val(d7_avg, "xline_avg_offaxis_40_60_fraction", "offaxis_40_60_fraction"),
            "source_position_std_deg": val(d7_avg, "source_position_peak_abs_std_deg"),
            "failure_type": "center-only false positive + source-position instability + 30-40 deg lobe",
            "stop_status": "stopped; no D5 revival",
        },
        {
            "candidate_id": "E1_0236",
            "route_or_family": "E0C_MQW_lateral_extent_robust_cavity",
            "proxy_prediction_summary": "normal/offaxis=2.58, angular FWHM=9.08 deg, spectral FWHM=7.82 nm",
            "measured_tri_point_peak_abs_deg": val(e2_avg, "tri_point_avg_peak_abs_angle_deg"),
            "measured_FWHM_deg": val(e2_avg, "tri_point_avg_fwhm_deg"),
            "normal_offaxis_ratio": val(e2_avg, "tri_point_avg_normal_offaxis_ratio"),
            "offaxis_30_40_fraction": val(e2_avg, "tri_point_avg_offaxis_30_40_fraction"),
            "offaxis_45_55_fraction": val(e2_avg, "tri_point_avg_offaxis_45_55_fraction"),
            "offaxis_40_60_fraction": val(e2_avg, "tri_point_avg_offaxis_40_60_fraction"),
            "source_position_std_deg": val(e2_avg, "source_position_peak_abs_std_deg"),
            "failure_type": "stable 49-52 deg far-offaxis / leaky-guided-like channel",
            "stop_status": "stopped; no E1_0236 retry",
        },
        {
            "candidate_id": "F0_0781",
            "route_or_family": val(f0_0781_proxy, "route_name"),
            "proxy_prediction_summary": f"peak={val(f0_0781_proxy, 'peak_abs_angle_proxy_deg')} deg; angular FWHM={val(f0_0781_proxy, 'angular_FWHM_proxy_deg')} deg; spectral FWHM={val(f0_0781_proxy, 'spectral_FWHM_proxy_nm')} nm",
            "measured_tri_point_peak_abs_deg": val(f1_avg, "tri_point_avg_peak_abs_angle_deg"),
            "measured_FWHM_deg": val(f1_avg, "tri_point_avg_fwhm_deg"),
            "normal_offaxis_ratio": val(f1_avg, "tri_point_avg_normal_offaxis_ratio"),
            "offaxis_30_40_fraction": val(f1_avg, "tri_point_avg_offaxis_30_40_fraction"),
            "offaxis_45_55_fraction": val(f1_avg, "tri_point_avg_offaxis_45_55_fraction"),
            "offaxis_40_60_fraction": val(f1_avg, "tri_point_avg_offaxis_40_60_fraction"),
            "source_position_std_deg": val(f1_avg, "source_position_peak_abs_std_deg"),
            "failure_type": "stable off-normal around 26 deg + broad 40-60 deg channel",
            "stop_status": "stopped; no F0_0781 continuation",
        },
        {
            "candidate_id": "F0_0204",
            "route_or_family": val(f0_0204_proxy, "route_name"),
            "proxy_prediction_summary": f"peak={val(f0_0204_proxy, 'peak_abs_angle_proxy_deg')} deg; angular FWHM={val(f0_0204_proxy, 'angular_FWHM_proxy_deg')} deg; spectral FWHM={val(f0_0204_proxy, 'spectral_FWHM_proxy_nm')} nm",
            "measured_tri_point_peak_abs_deg": val(f2_avg, "tri_point_avg_peak_abs_angle_deg"),
            "measured_FWHM_deg": val(f2_avg, "tri_point_avg_fwhm_deg"),
            "normal_offaxis_ratio": val(f2_avg, "tri_point_avg_normal_offaxis_ratio"),
            "offaxis_30_40_fraction": val(f2_avg, "tri_point_avg_offaxis_30_40_fraction"),
            "offaxis_45_55_fraction": val(f2_avg, "tri_point_avg_offaxis_45_55_fraction"),
            "offaxis_40_60_fraction": val(f2_avg, "tri_point_avg_offaxis_40_60_fraction"),
            "source_position_std_deg": val(f2_avg, "source_position_peak_abs_std_deg"),
            "failure_type": "severe far-offaxis 46-67 deg + broad FWHM + source-position mismatch",
            "stop_status": "stopped; full F0 shortlist failed",
        },
    ]
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [f"{k}:{v}" for k, v in INPUTS.items() if not v.exists()]
    dataset = negative_dataset()
    write_csv(OUT / "r2_4g0_existing_negative_dataset.csv", dataset)

    proxy_terms = [
        {"term": "dipole_orientation", "v0_requirement": "x/y initially; z optional later", "why_needed": "dipole radiation and cavity coupling are orientation dependent", "status": "spec_only"},
        {"term": "source_position_tri_point", "v0_requirement": "x=[-0.7,0,+0.7] um required before claiming stability", "why_needed": "D5 proved center-only can be false positive", "status": "requires_calibration"},
        {"term": "normal_cone_weight", "v0_requirement": "track |theta|<=5 and <=10 deg energy", "why_needed": "normal RCLED target needs energy in air cone", "status": "spec_only"},
        {"term": "offaxis_window_weights", "v0_requirement": "20-30, 30-40, 40-60, 45-55, >60 deg windows", "why_needed": "D5/E1/F0 failures appear in different off-axis windows", "status": "spec_only"},
        {"term": "guided_leaky_channel_risk", "v0_requirement": "penalize high-k or high-angle energy transfer risk", "why_needed": "E1_0236 and F0_0204 revived far-offaxis channels", "status": "needs_physics_helper"},
        {"term": "reciprocity_angle_weighting", "v0_requirement": "use incident-angle weighting if Python helper supports it", "why_needed": "reciprocity can approximate dipole-to-air angular extraction", "status": "optional_helper"},
        {"term": "source_position_stability_score", "v0_requirement": "output requires_tri_point_FDTD until calibrated", "why_needed": "Python-only cannot honestly claim stability yet", "status": "do_not_claim_pass"},
        {"term": "risk_score_not_pass_claim", "v0_requirement": "proxy emits risk ranking and FDTD entry flags, not final pass", "why_needed": "all previous proxy passes produced FDTD failures", "status": "mandatory"},
    ]
    write_csv(OUT / "r2_4g0_dipole_aware_proxy_v0_spec.csv", proxy_terms)

    write_text(OUT / "r2_4g0_proxy_gap_analysis.md", """
# R2-4G0 Proxy Gap Analysis

Current 1D stack/MDC proxy gaps:
- missing finite MQW dipole angular coupling;
- missing LDOS / Green-function-like source-to-farfield response;
- missing reciprocity-based angular coupling from high-k guided/leaky channels to the air cone;
- missing source-position response;
- spectral narrowing is not equivalent to angular narrowing;
- high top mirror/MDC can redirect or trap energy into off-axis channels.

Consequence: plane-wave angular transmission/reflection is not enough to rank normal RCLED source candidates. The next proxy should be dipole-aware or reciprocity-aware and should output risk scores, not pass claims.
""")

    write_text(OUT / "r2_4g0_minimal_validation_dataset_plan.md", """
# R2-4G0 Minimal Validation Dataset Plan

Purpose: calibrate the next proxy with the fewest possible FDTD cases, not run another blind sweep.

Dataset stages:
- G1: Python-only assemble existing negative dataset and feature table. No FDTD.
- G2: minimal calibration FDTD only if explicitly approved, maximum 2 new candidates x 3 tri-point cases, x-dipole only, 453 nm only.
- G3: fit/threshold/update proxy using negatives plus any calibration results.
- G4: candidate generation using calibrated proxy.

G0 does not execute G1/G2. It only defines the boundary.
""")

    write_text(OUT / "r2_4g0_next_stage_g1_g2_plan.md", """
# R2-4G0 Next Stage G1/G2 Plan

Recommended G1 task name:
`R2-4G1_python_only_negative_dataset_feature_table_for_dipole_aware_proxy`

G1 should:
- build one lightweight feature table from D5, E1_0236, F0_0781, and F0_0204;
- include proxy features, measured FDTD failure windows, source-position metrics, and stop labels;
- define candidate entry thresholds for G2;
- remain Python-only.

G2 is not allowed until G1 is reviewed. If approved, G2 should be capped at 2 candidates x 3 tri-point x-dipole 453 nm cases.
""")

    write_text(OUT / "r2_4g0_stop_allow_rules.md", """
# R2-4G0 Stop / Allow Rules

Stop:
- D5_BASE_13461
- E1_0236
- F0_0781
- F0_0204

Do not:
- run FDTD immediately after G0;
- run FDTD from the current 1D proxy shortlist;
- use center-only verdicts;
- run y/z/broadband before tri-point x-dipole pass;
- claim source-position stability from Python-only proxy.

Allow:
- G1 Python-only negative dataset and feature table;
- reviewed G2 minimal calibration only after G1;
- retain relaxed target: spectral FWHM <=10 nm and angular FWHM <=20 deg;
- accept 25-30 deg only as literature-aligned intermediate baseline, not final pass.
""")

    write_text(OUT / "r2_4g0_summary.md", """
# R2-4G0 Dipole-Aware Proxy Specification and Minimal Validation Plan

G0 creates the boundary for the next RCLED/MDC route after D5, E1_0236, F0_0781, and F0_0204 all failed FDTD guards.

One-line conclusion: the next route must upgrade from a 1D stack/MDC proxy to a dipole-aware or reciprocity-aware risk proxy before any new FDTD shortlist.

Immediate FDTD: no.

Recommended next task: `R2-4G1_python_only_negative_dataset_feature_table_for_dipole_aware_proxy`.
""")

    manifest = {
        "stage": "R2-4G0 dipole-aware proxy spec and minimal validation dataset plan",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "no_fsp_generated": True,
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "missing_inputs": missing,
        "negative_samples": [row["candidate_id"] for row in dataset],
        "recommended_G1_task": "R2-4G1_python_only_negative_dataset_feature_table_for_dipole_aware_proxy",
        "immediate_fdtd_allowed": False,
        "outputs": [
            "r2_4g0_summary.md",
            "r2_4g0_existing_negative_dataset.csv",
            "r2_4g0_proxy_gap_analysis.md",
            "r2_4g0_dipole_aware_proxy_v0_spec.csv",
            "r2_4g0_minimal_validation_dataset_plan.md",
            "r2_4g0_next_stage_g1_g2_plan.md",
            "r2_4g0_stop_allow_rules.md",
            "r2_4g0_manifest.json",
        ],
    }
    write_json(OUT / "r2_4g0_manifest.json", manifest)
    print(json.dumps({"output": str(OUT), "negative_samples": len(dataset), "missing": missing}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
