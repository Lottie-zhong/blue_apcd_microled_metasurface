from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = {
    "e1_shortlist": ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan" / "r2_4e1_shortlist.csv",
    "e1_scored": ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan" / "r2_4e1_proxy_scored_candidates.csv",
    "e2_case_results": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_case_results.csv",
    "e2_average": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_tri_point_incoherent_average.csv",
    "e2_verdict": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_pass_fail_verdict.md",
    "e0_proxy_variables": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_proxy_variables_v2.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d9_scored": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_proxy_scored_candidates.csv",
}
FORBIDDEN_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}
CANDIDATE_ID = "E1_0236"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def f(row: Dict[str, Any], key: str) -> float | None:
    try:
        value = row.get(key, "")
        if value in (None, "", "missing"):
            return None
        return float(value)
    except Exception:
        return None


def s(row: Dict[str, Any], key: str, default: str = "missing") -> str:
    value = row.get(key, "")
    return default if value in (None, "") else str(value)


def input_audit() -> List[Dict[str, Any]]:
    rows = []
    for name, path in INPUTS.items():
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError(f"Forbidden heavy input configured: {path}")
        csv_rows = read_csv(path) if path.suffix.lower() == ".csv" else []
        rows.append({
            "input_name": name,
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "kind": path.suffix.lower().lstrip("."),
            "row_count": len(csv_rows) if path.suffix.lower() == ".csv" else "n/a",
            "status": "loaded" if path.exists() else "missing",
        })
    return rows


def first_candidate(rows: List[Dict[str, str]]) -> Dict[str, str]:
    for row in rows:
        if row.get("candidate_id") == CANDIDATE_ID:
            return row
    return rows[0] if rows else {}


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file already present in E3 output")

    audit = input_audit()
    e1 = first_candidate(read_csv(INPUTS["e1_shortlist"]))
    e2_avg = first_candidate(read_csv(INPUTS["e2_average"]))
    e2_cases = read_csv(INPUTS["e2_case_results"])
    ok_cases = [r for r in e2_cases if r.get("status") == "ok"]

    predicted_normal_offaxis = f(e1, "normal_offaxis_proxy")
    measured_normal_offaxis = f(e2_avg, "tri_point_avg_normal_offaxis_ratio")
    predicted_fwhm = f(e1, "angular_fwhm_deg_proxy")
    measured_fwhm = f(e2_avg, "tri_point_avg_fwhm_deg")
    predicted_30_40 = f(e1, "offaxis_30_40_lobe_penalty")
    measured_30_40 = f(e2_avg, "tri_point_avg_offaxis_30_40_fraction")
    measured_peak = f(e2_avg, "tri_point_avg_peak_abs_angle_deg")
    case_peak_values = [f(r, "peak_abs_angle_deg") for r in ok_cases]
    case_peak_values = [x for x in case_peak_values if x is not None]

    mismatch_rows = [{
        "candidate_id": CANDIDATE_ID,
        "family_id": s(e1, "family_id"),
        "predicted_normal_offaxis_proxy": predicted_normal_offaxis if predicted_normal_offaxis is not None else "missing",
        "measured_tri_point_normal_offaxis": measured_normal_offaxis if measured_normal_offaxis is not None else "missing",
        "normal_offaxis_ratio_measured_over_predicted": (measured_normal_offaxis / predicted_normal_offaxis) if predicted_normal_offaxis and measured_normal_offaxis is not None else "missing",
        "predicted_angular_fwhm_deg": predicted_fwhm if predicted_fwhm is not None else "missing",
        "measured_tri_point_fwhm_deg": measured_fwhm if measured_fwhm is not None else "missing",
        "fwhm_delta_measured_minus_predicted_deg": (measured_fwhm - predicted_fwhm) if predicted_fwhm is not None and measured_fwhm is not None else "missing",
        "predicted_30_40_penalty": predicted_30_40 if predicted_30_40 is not None else "missing",
        "measured_tri_point_30_40_fraction": measured_30_40 if measured_30_40 is not None else "missing",
        "measured_avg_peak_abs_angle_deg": measured_peak if measured_peak is not None else "missing",
        "measured_case_peak_abs_angles_deg": ";".join(f"{x:.6g}" for x in case_peak_values) if case_peak_values else "missing",
        "predicted_near_normal_expectation": "near-normal from proxy shortlist",
        "measured_peak_zone": "45-55 deg far-offaxis" if measured_peak is not None and 45 <= measured_peak <= 55 else "other",
        "mismatch_class": "severe_proxy_false_positive",
    }]
    write_csv(OUT / "r2_4e3_e1_proxy_vs_e2_fdtd_mismatch.csv", mismatch_rows, list(mismatch_rows[0].keys()))

    correction_terms = [
        {
            "term": "far_offaxis_45_55_lobe_penalty",
            "purpose": "Reject candidates likely to couple into the stable 49-52 deg channel seen in E2.",
            "trigger_from_E2": "E1_0236 tri-point peaks at about 49-52 deg for all source positions.",
            "priority": "P0",
            "recommended_proxy_rule": "scan/estimate 45-55 deg response and hard-fail if it can dominate normal cone",
        },
        {
            "term": "broad_40_60_lobe_penalty",
            "purpose": "Expand off-axis guard beyond the old 30-40 deg window.",
            "trigger_from_E2": "E2 failure peak lies outside 30-40 deg, so 30-40-only rejection is insufficient.",
            "priority": "P0",
            "recommended_proxy_rule": "penalize integrated 40-60 deg response separately from 20-60 aggregate",
        },
        {
            "term": "peak_angle_risk_guard",
            "purpose": "Reject any proxy candidate with a dominant resonance/lobe outside 10 deg.",
            "trigger_from_E2": "measured dominant peak is about 51.5 deg despite E1 near-normal proxy pass.",
            "priority": "P0",
            "recommended_proxy_rule": "candidate cannot pass if any predicted dominant angular channel is >10 deg",
        },
        {
            "term": "normal_cone_energy_lower_bound_proxy",
            "purpose": "Require enough absolute normal-cone energy, not just a ratio from a simplified proxy.",
            "trigger_from_E2": "tri-point eta10 is about 0.061 and normal/offaxis ratio is about 0.076.",
            "priority": "P0",
            "recommended_proxy_rule": "hard-fail if normal cone proxy falls below population-derived floor",
        },
        {
            "term": "broad_FWHM_risk_guard",
            "purpose": "Reject candidates with risk of a broad/multilobe angular response.",
            "trigger_from_E2": "tri-point average FWHM is about 108 deg while proxy predicted about 9 deg.",
            "priority": "P0",
            "recommended_proxy_rule": "hard-fail if proxy detects broad or multi-peak angular response",
        },
        {
            "term": "E1_0236_like_risk_flag",
            "purpose": "Block candidates resembling E1_0236: balanced 6/6 pair stack, medium terminations, strong proxy pass but missing far-offaxis guard.",
            "trigger_from_E2": "E1_0236 was the only E1 shortlist candidate and failed tri-point hard rules.",
            "priority": "P0",
            "recommended_proxy_rule": "flag high unless 45-55 and 40-60 guards are explicitly low",
        },
        {
            "term": "keep_30_40_penalty_as_local_guard",
            "purpose": "Retain D8/D9 30-40 deg penalty but treat it as one off-axis window, not the only danger zone.",
            "trigger_from_E2": "E2 shows dangerous far-offaxis channel can occur at 49-52 deg.",
            "priority": "P1",
            "recommended_proxy_rule": "use alongside 40-60 and 45-55 penalties",
        },
        {
            "term": "proxy_FDTD_mismatch_guard",
            "purpose": "Down-rank design families/regions where proxy says pass but tri-point FDTD gives far-offaxis failure.",
            "trigger_from_E2": "E1 proxy predicted normal/offaxis 2.58; FDTD measured 0.076.",
            "priority": "P0",
            "recommended_proxy_rule": "negative-sample distance to E1_0236 must be included in E4 scoring",
        },
    ]
    write_csv(OUT / "r2_4e3_proxy_correction_terms.csv", correction_terms, ["term", "purpose", "trigger_from_E2", "priority", "recommended_proxy_rule"])

    failure_md = [
        "# R2-4E3 Failure Classification",
        "",
        "Classification:",
        "- not_source_position_instability",
        "- stable_far_offaxis_peak",
        "- leaky/guided-mode-like offaxis channel suspected",
        "- proxy_false_positive",
        "",
        "Rationale:",
        f"- E2 completed {len(ok_cases)} / 3 cases successfully.",
        f"- Case peak_abs angles: {', '.join(f'{x:.4f}' for x in case_peak_values) if case_peak_values else 'missing'} deg.",
        f"- Tri-point average peak_abs angle: {measured_peak if measured_peak is not None else 'missing'} deg.",
        f"- Source-position peak std: {e2_avg.get('source_position_peak_abs_std_deg', 'missing')} deg.",
        f"- Bilateral asymmetry: {e2_avg.get('bilateral_asymmetry_metric', 'missing')}.",
        "",
        "The failure is stable and bilateral, not a noisy or edge-only source-position instability. The dominant channel is far off normal around 49-52 deg.",
    ]
    (OUT / "r2_4e3_failure_classification.md").write_text("\n".join(failure_md) + "\n", encoding="utf-8")

    e4_plan = [
        "# R2-4E4 Candidate Generator V3 Plan",
        "",
        "Recommended task name: **R2-4E4_Python_only_candidate_generator_v3_faroffaxis_guard**.",
        "",
        "E4 must remain Python-only: no Lumerical, no lumapi, no FDTD, no FSP generation.",
        "",
        "Mandatory E4 changes:",
        "- no E1_0236 retry",
        "- shortlist max 2 candidates",
        "- candidate must pass both 30-40 deg and 45-55 deg off-axis penalties",
        "- include 40-60 deg broad lobe penalty",
        "- include normal-cone energy lower-bound proxy",
        "- include broad-FWHM/multilobe risk guard",
        "- include E1_0236-like risk flag and proxy-FDTD mismatch guard",
        "- candidate must be marked requires_tri_point_FDTD before validation",
        "",
        "FDTD is not allowed until after E4 review. If E4 produces a candidate, the first validation remains tri-point x-dipole 453 nm only.",
    ]
    (OUT / "r2_4e3_e4_candidate_generator_v3_plan.md").write_text("\n".join(e4_plan) + "\n", encoding="utf-8")

    stop_rules = [
        "# R2-4E3 Stop Rules",
        "",
        "- Stop E1_0236.",
        "- No 5-point x-line for E1_0236.",
        "- No 9-point x-line for E1_0236.",
        "- No y-dipole, z-out-of-plane, or broadband validation for E1_0236.",
        "- No old D5 revival.",
        "- Do not run more FDTD until E4 Python-only candidate generator v3 produces a reviewed shortlist.",
    ]
    (OUT / "r2_4e3_stop_rules.md").write_text("\n".join(stop_rules) + "\n", encoding="utf-8")

    summary = [
        "# R2-4E3 E1_0236 FDTD Failure Diagnosis And Proxy Correction",
        "",
        "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.",
        "",
        "## One-Line Conclusion",
        "E1_0236 is a severe Python-proxy false positive: tri-point FDTD shows a stable 49-52 deg far-offaxis channel, so E4 must add 45-55 deg and 40-60 deg lobe guards before any further shortlist can be trusted.",
        "",
        "## Proxy vs FDTD",
        f"- Predicted normal/offaxis: {predicted_normal_offaxis if predicted_normal_offaxis is not None else 'missing'}",
        f"- Measured tri-point normal/offaxis: {measured_normal_offaxis if measured_normal_offaxis is not None else 'missing'}",
        f"- Predicted angular FWHM: {predicted_fwhm if predicted_fwhm is not None else 'missing'} deg",
        f"- Measured tri-point FWHM: {measured_fwhm if measured_fwhm is not None else 'missing'} deg",
        f"- Predicted 30-40 penalty: {predicted_30_40 if predicted_30_40 is not None else 'missing'}",
        f"- Measured 30-40 fraction: {measured_30_40 if measured_30_40 is not None else 'missing'}",
        f"- Measured peak zone: {mismatch_rows[0]['measured_peak_zone']}",
        "",
        "## E4 Recommendation",
        "R2-4E4_Python_only_candidate_generator_v3_faroffaxis_guard",
    ]
    (OUT / "r2_4e3_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    manifest = {
        "stage": "R2-4E3_E1_0236_FDTD_failure_diagnosis_proxy_correction",
        "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd_or_fsp_generated": True,
        "candidate_id": CANDIDATE_ID,
        "input_audit": input_audit(),
        "classification": ["not_source_position_instability", "stable_far_offaxis_peak", "leaky/guided-mode-like offaxis channel suspected", "proxy_false_positive"],
        "recommended_E4_task": "R2-4E4_Python_only_candidate_generator_v3_faroffaxis_guard",
        "stop_E1_0236": True,
    }
    (OUT / "r2_4e3_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "output": str(OUT),
        "classification": manifest["classification"],
        "recommended_E4_task": manifest["recommended_E4_task"],
    }, indent=2))


if __name__ == "__main__":
    main()
