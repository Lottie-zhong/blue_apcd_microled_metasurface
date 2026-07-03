#!/usr/bin/env python3
"""R2-4F3 Python-only audit of F0 shortlist FDTD failures.

Reads only lightweight F0/F1/F2/D8/E3 artifacts. No Lumerical, lumapi, FSP, or FDTD.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4f3_f0_shortlist_fdtd_failure_audit_proxy_breakdown"

INPUTS = {
    "F0": ROOT / "outputs" / "r2_4f0_literature_seeded_relaxed_target_rcled_mdc_scan",
    "F1": ROOT / "outputs" / "r2_4f1_f0_0781_tri_point_xdipole_fdtd_guard",
    "F2": ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard",
    "E3": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction",
    "D8": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign",
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
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def f(row: dict[str, str], key: str) -> float | None:
    try:
        value = row.get(key, "")
        if value in {"", "missing", "n/a", None}:
            return None
        return float(value)
    except Exception:
        return None


def first(rows: list[dict[str, str]], **where: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(k) == v for k, v in where.items()):
            return row
    return {}


def classify(candidate_id: str, avg: dict[str, str]) -> tuple[str, str]:
    if candidate_id == "F0_0781":
        return "stable_off_normal_around_26deg_plus_broad_40_60_channel", "stable off-normal route; not primarily source-position instability"
    if candidate_id == "F0_0204":
        return "severe_far_offaxis_46_67deg_plus_broad_fwhm_source_position_mismatch", "far-offaxis and source-position mismatch; high-top-DBR route failed badly"
    return "unknown", "missing classification"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    missing = [f"{label}:{folder}" for label, folder in INPUTS.items() if not folder.exists()]

    f0_shortlist = read_csv(INPUTS["F0"] / "r2_4f0_shortlist.csv")
    f1_avg_rows = read_csv(INPUTS["F1"] / "r2_4f1_tri_point_incoherent_average.csv")
    f2_avg_rows = read_csv(INPUTS["F2"] / "r2_4f2_tri_point_incoherent_average.csv")
    measured = {
        "F0_0781": f1_avg_rows[0] if f1_avg_rows else {},
        "F0_0204": f2_avg_rows[0] if f2_avg_rows else {},
    }

    mismatch_rows: list[dict[str, Any]] = []
    taxonomy_rows: list[dict[str, Any]] = []
    for candidate_id in ["F0_0781", "F0_0204"]:
        proxy = first(f0_shortlist, candidate_id=candidate_id)
        avg = measured[candidate_id]
        failure_type, note = classify(candidate_id, avg)
        proxy_fwhm = f(proxy, "angular_FWHM_proxy_deg")
        fdtd_fwhm = f(avg, "tri_point_avg_fwhm_deg")
        proxy_peak = f(proxy, "peak_abs_angle_proxy_deg")
        fdtd_peak = f(avg, "tri_point_avg_peak_abs_angle_deg")
        mismatch_rows.append({
            "candidate_id": candidate_id,
            "route": proxy.get("route", "missing"),
            "route_name": proxy.get("route_name", "missing"),
            "proxy_angular_FWHM_deg": proxy.get("angular_FWHM_proxy_deg", "missing"),
            "fdtd_tri_point_FWHM_deg": avg.get("tri_point_avg_fwhm_deg", "missing"),
            "FWHM_error_fdtd_minus_proxy_deg": "missing" if proxy_fwhm is None or fdtd_fwhm is None else fdtd_fwhm - proxy_fwhm,
            "proxy_peak_abs_angle_deg": proxy.get("peak_abs_angle_proxy_deg", "missing"),
            "fdtd_tri_point_peak_abs_angle_deg": avg.get("tri_point_avg_peak_abs_angle_deg", "missing"),
            "peak_error_fdtd_minus_proxy_deg": "missing" if proxy_peak is None or fdtd_peak is None else fdtd_peak - proxy_peak,
            "proxy_30_40_penalty": proxy.get("offaxis_30_40_lobe_penalty", "missing"),
            "fdtd_30_40_fraction": avg.get("tri_point_avg_offaxis_30_40_fraction", "missing"),
            "proxy_45_55_penalty": proxy.get("faroffaxis_45_55_lobe_penalty", "missing"),
            "fdtd_45_55_fraction": avg.get("tri_point_avg_offaxis_45_55_fraction", "missing"),
            "proxy_40_60_penalty": proxy.get("broad_40_60_faroffaxis_penalty", "missing"),
            "fdtd_40_60_fraction": avg.get("tri_point_avg_offaxis_40_60_fraction", "missing"),
            "proxy_normal_offaxis": proxy.get("normal_offaxis_proxy", "missing"),
            "fdtd_normal_offaxis": avg.get("tri_point_avg_normal_offaxis_ratio", "missing"),
            "fdtd_verdict": avg.get("pass_fail_verdict", "missing"),
            "failure_type": failure_type,
        })
        taxonomy_rows.append({
            "candidate_id": candidate_id,
            "route_name": proxy.get("route_name", "missing"),
            "failure_type": failure_type,
            "peak_abs_angle_deg": avg.get("tri_point_avg_peak_abs_angle_deg", "missing"),
            "angular_fwhm_deg": avg.get("tri_point_avg_fwhm_deg", "missing"),
            "normal_offaxis_ratio": avg.get("tri_point_avg_normal_offaxis_ratio", "missing"),
            "offaxis_40_60_fraction": avg.get("tri_point_avg_offaxis_40_60_fraction", "missing"),
            "source_position_peak_abs_std_deg": avg.get("source_position_peak_abs_std_deg", "missing"),
            "classification_note": note,
        })

    route_options = [
        {"option": "A", "route": "dipole_aware_reduced_proxy_or_reciprocity_angular_coupling", "physical_rationale": "1D stack transmission is not enough; finite MQW dipoles couple into LDOS and leaky/guided channels.", "expected_benefit": "filters candidates before expensive FDTD using dipole-to-farfield physics", "cost": "medium Python/modeling work plus small calibration dataset", "risk": "proxy may still need empirical calibration", "recommended_next_task": "R2-4G0 Python-only dipole-aware proxy specification and minimal validation dataset plan", "immediate_FDTD_allowed": "no"},
        {"option": "B", "route": "literature_seeded_manufacturable_intermediate_25_30deg_target", "physical_rationale": "F0_0781 lands near 26 deg; could be treated as an intermediate relaxed source, not final normal RCLED.", "expected_benefit": "salvages a paper narrative milestone if normal target remains too hard", "cost": "low documentation and limited validation", "risk": "does not satisfy normal RCLED target", "recommended_next_task": "define intermediate milestone only after G0 audit", "immediate_FDTD_allowed": "no"},
        {"option": "C", "route": "explicit_top_outcoupler_or_metasurface_angular_extraction", "physical_rationale": "pure stack/MDC redirects or traps energy; explicit angular extraction may be needed.", "expected_benefit": "adds actual angular control degree of freedom", "cost": "high; may overlap later APCD/metasurface integration", "risk": "larger design space and fabrication constraints", "recommended_next_task": "scope after G0, not immediate FDTD", "immediate_FDTD_allowed": "no"},
        {"option": "D", "route": "pause_RCLED_MDC_optimization_use_literature_baseline_for_narrative", "physical_rationale": "current stack-only search repeatedly fails FDTD guard", "expected_benefit": "prevents compute burn", "cost": "may reduce novelty of source module", "risk": "less direct validation for integrated APCD source", "recommended_next_task": "decision checkpoint after G0 spec", "immediate_FDTD_allowed": "no"},
    ]

    write_csv(OUT / "r2_4f3_f0_proxy_vs_fdtd_mismatch.csv", mismatch_rows)
    write_csv(OUT / "r2_4f3_failure_taxonomy.csv", taxonomy_rows)
    write_csv(OUT / "r2_4f3_next_route_options.csv", route_options)

    write_text(OUT / "r2_4f3_proxy_breakdown_diagnosis.md", """
# R2-4F3 Proxy Breakdown Diagnosis

The full F0 relaxed-target shortlist failed tri-point x-dipole FDTD guard.

Current proxy breakdown:
- The Python-only 1D stack/MDC proxy estimates angular transmission/reflection, but it does not model finite MQW dipole emission coupling.
- It lacks Green-function / LDOS / dipole-to-farfield angular coupling, so it can miss leaky or guided-like high-angle channels.
- Source-position stability cannot be inferred from the current stack-only proxy.
- Spectral narrowing proxy does not guarantee angular narrowing.
- High top mirror or MDC layers can trap or redirect energy into high-angle channels instead of producing near-normal extraction.

Measured route failures:
- F0_0781: stable off-normal around 26 deg plus broad 40-60 deg channel.
- F0_0204: severe far-offaxis 46-67 deg, broad FWHM, and source-position mismatch.

Conclusion: do not keep blindly sweeping 1D stack parameters for normal RCLED source selection.
""")

    write_text(OUT / "r2_4f3_recommended_g0_plan.md", """
# R2-4F3 Recommended G0 Plan

Recommended task name:
`R2-4G0_dipole_aware_proxy_spec_and_minimal_validation_dataset_plan`

G0 should be Python-only. It should define a dipole-aware or reciprocity-aware reduced proxy before any new FDTD shortlist.

Minimum G0 content:
- identify the missing physics in the current stack-only proxy: dipole LDOS, source-position coupling, and dipole-to-farfield angular transfer;
- define the smallest validation dataset from existing D7/E2/F1/F2 negative samples;
- specify what proxy terms must predict before another candidate can enter FDTD;
- keep tri-point x-dipole 453 nm as the first FDTD gate after proxy redesign.

Immediate FDTD is not allowed from F0/F1/F2 failed routes.
""")

    write_text(OUT / "r2_4f3_stop_rules.md", """
# R2-4F3 Stop Rules

- Stop F0_0781.
- Stop F0_0204.
- The full F0 shortlist failed tri-point FDTD guard.
- Do not revive D5_BASE_13461.
- Do not revive E1_0236.
- Do not hard-pick another failed/no-pass stack-only candidate for FDTD.
- Do not run immediate FDTD until the proxy is updated to be dipole-aware or reciprocity-aware.
- No y/z/broadband validation is allowed for failed F0 candidates.
""")

    write_text(OUT / "r2_4f3_summary.md", f"""
# R2-4F3 F0 Shortlist FDTD Failure Audit

Result: the full F0 shortlist failed tri-point FDTD guard.

Key evidence:
- F0_0781 proxy predicted peak_abs 2.45 deg and angular FWHM 16.13 deg, but FDTD measured peak_abs 25.895 deg and FWHM 54.998 deg.
- F0_0204 proxy predicted peak_abs 1.85 deg and angular FWHM 18.41 deg, but FDTD measured peak_abs 65.499 deg and FWHM 138.446 deg.
- Both candidates have normal/offaxis < 1 in FDTD.

One-line conclusion: relaxed stack/MDC proxy still misses dipole-coupled off-axis channels, so R2-4G should upgrade the proxy physics before any new FDTD.

Missing optional inputs recorded: {', '.join(missing) if missing else 'none'}.
""")

    write_json(OUT / "r2_4f3_manifest.json", {
        "stage": "R2-4F3 F0 shortlist FDTD failure audit and proxy breakdown",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "inputs": {k: str(v) for k, v in INPUTS.items()},
        "missing_inputs": missing,
        "outputs": [
            "r2_4f3_summary.md",
            "r2_4f3_f0_proxy_vs_fdtd_mismatch.csv",
            "r2_4f3_failure_taxonomy.csv",
            "r2_4f3_proxy_breakdown_diagnosis.md",
            "r2_4f3_next_route_options.csv",
            "r2_4f3_recommended_g0_plan.md",
            "r2_4f3_stop_rules.md",
            "r2_4f3_manifest.json",
        ],
        "recommended_next_task": "R2-4G0_dipole_aware_proxy_spec_and_minimal_validation_dataset_plan",
        "immediate_fdtd_allowed": False,
    })

    print(json.dumps({"output": str(OUT), "mismatch_rows": len(mismatch_rows), "missing": missing}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
