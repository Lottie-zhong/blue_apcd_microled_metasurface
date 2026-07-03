from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = {
    "d7_case_metrics": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_case_metrics.csv",
    "d7_average_metrics": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_xline_average_metrics.csv",
    "d7_robustness": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_source_position_robustness.csv",
    "d7_summary": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_summary.md",
    "d8_failure_table": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_source_position_failure_table.csv",
    "d8_proxy_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d8_decision": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_next_route_decision.md",
    "d9_scored": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_proxy_scored_candidates.csv",
    "d9_shortlist": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_shortlist.csv",
    "d9_decision": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_no_pass_or_shortlist_decision.md",
    "d2_top20": ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize" / "r2_4d2_top20_candidate_metrics.csv",
    "d3_near_pass": ROOT / "outputs" / "r2_4d3_cavity_phase_design_space_reset" / "r2_4d3_near_pass_candidates.csv",
    "d4_best_spacers": ROOT / "outputs" / "r2_4d4_focused_cavity_phase_sweep" / "r2_4d4_best_phase_guided_spacers.csv",
    "d5_top20": ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization" / "r2_4d5_top20_phase_guided_candidates.csv",
    "d5a_risk": ROOT / "outputs" / "r2_4d5a_shortlist_te_tm_offaxis_risk_review" / "r2_4d5a_normal_vs_offaxis_margin.csv",
}

FORBIDDEN_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "missing"):
            return None
        return float(value)
    except Exception:
        return None


def summarize_inputs() -> List[Dict[str, Any]]:
    audit = []
    for name, path in INPUTS.items():
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError(f"Forbidden heavy input configured: {path}")
        rows = read_csv(path) if path.suffix.lower() == ".csv" else []
        audit.append({
            "input_name": name,
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "kind": path.suffix.lower().lstrip("."),
            "row_count": len(rows) if path.suffix.lower() == ".csv" else "n/a",
            "status": "loaded" if path.exists() else "missing",
        })
    return audit


def derive_d7_evidence() -> Dict[str, Any]:
    avg = read_csv(INPUTS["d7_average_metrics"])
    rob = read_csv(INPUTS["d7_robustness"])
    scored = read_csv(INPUTS["d9_scored"])
    row = avg[0] if avg else {}
    rob_row = rob[0] if rob else {}
    d9_no_pass_count = 0
    for r in scored:
        if str(r.get("hard_pass", "")).lower() != "true":
            d9_no_pass_count += 1
    return {
        "d7_xline_avg_peak_abs_angle_deg": row.get("peak_abs_angle_deg", "missing"),
        "d7_xline_avg_angular_FWHM_deg": row.get("angular_FWHM_deg", "missing"),
        "d7_xline_avg_eta20": row.get("eta20", "missing"),
        "d7_xline_avg_normal_offaxis_ratio": row.get("normal_offaxis_ratio", "missing"),
        "d7_xline_avg_verdict": row.get("verdict", row.get("status", "missing")),
        "d7_peak_abs_min_deg": rob_row.get("peak_abs_min_deg", "missing"),
        "d7_peak_abs_max_deg": rob_row.get("peak_abs_max_deg", "missing"),
        "d7_peak_abs_std_deg": rob_row.get("peak_abs_std_deg", "missing"),
        "d7_edge_or_unstable_flag": rob_row.get("edge_or_unstable_flag", "missing"),
        "d9_scored_candidate_count": len(scored),
        "d9_hard_pass_count": len(scored) - d9_no_pass_count,
    }


def design_families() -> List[Dict[str, str]]:
    return [
        {
            "family_id": "E0A_lower_Q_angle_stable_cavity",
            "family_name": "lower-Q / broader but more angle-stable cavity family",
            "physical_rationale": "Reduce excessive center-only resonance contrast so small source-position shifts do not couple into narrow off-axis cavity modes.",
            "expected_benefit": "More uniform center and bilateral source response; lower chance of 30-40 deg lobe revival.",
            "main_risk": "Lower Q may broaden spectrum or reduce peak normal power, so spectral FWHM and extraction proxy must be guarded.",
            "python_only_proxy_variables": "top/bottom reflectivity balance; cavity Q proxy; normal/offaxis lower bound; spectral FWHM proxy; 30-40 lobe penalty; center contrast cap",
            "minimum_FDTD_entry_condition": "proxy passes TE/TM 30-40 rejection, normal/offaxis lower bound, angular/spectral FWHM guards, and marks source stability as requires_tri_point_FDTD",
            "stop_condition": "stop if 30-40 lobe proxy is high, center contrast is excessive, or tri-point x-dipole 453 nm fails",
        },
        {
            "family_id": "E0B_phase_balanced_DBR_30_40_reject",
            "family_name": "stronger top/bottom phase-balanced DBR family with explicit 30-40 deg rejection",
            "physical_rationale": "Treat 20-40 deg modes as phase constraints, not incidental side effects; design mirror phase so 453 nm normal resonance is favored over 30-40 deg resonance.",
            "expected_benefit": "Better normal/offaxis separation while retaining useful spectral selectivity near 453 nm.",
            "main_risk": "May recreate D5-style false positives if only center/normal phase is optimized; TE/TM off-axis guard is mandatory.",
            "python_only_proxy_variables": "TE/TM roundtrip phase at 0-10 and 30-40 deg; normal/offaxis ratio; phase margin to 30-40 deg; mirror outcoupling asymmetry; spectral FWHM proxy",
            "minimum_FDTD_entry_condition": "both TE and TM show low 30-40 risk and normal/offaxis > lower bound before tri-point FDTD",
            "stop_condition": "stop if TM off-axis resonance crosses 453 nm or phase margin to 30-40 deg is small",
        },
        {
            "family_id": "E0C_MQW_lateral_extent_robust_cavity",
            "family_name": "source-position robust cavity family optimized for MQW finite lateral extent",
            "physical_rationale": "Optimize for finite lateral source ensemble from the start instead of a single central dipole.",
            "expected_benefit": "Directly targets the D7/D8 failure mode: center response cannot dominate the design decision.",
            "main_risk": "Python-only proxy cannot prove source-position stability; every candidate still needs tri-point FDTD guard.",
            "python_only_proxy_variables": "bilateral source stability placeholder; edge sensitivity penalty; lateral aperture proxy; 30-40 lobe penalty; center-vs-xline mismatch risk",
            "minimum_FDTD_entry_condition": "candidate must have no high center-only false-positive risk and must reserve tri-point x positions [-0.7,0,+0.7] as first FDTD",
            "stop_condition": "stop immediately if either off-center tri-point case revives 30-40 deg lobe or normal/offaxis falls below 1",
        },
        {
            "family_id": "E0D_reduced_center_contrast_control",
            "family_name": "deliberately reduced center resonance contrast to avoid center-only false positive",
            "physical_rationale": "Cap center-only normal resonance strength so score cannot be dominated by one source position.",
            "expected_benefit": "May reduce D5-like overfitting and improve robustness at x = +/-0.7 um.",
            "main_risk": "Can underperform if contrast is reduced too far; may become a weak source module rather than a useful RCLED.",
            "python_only_proxy_variables": "center contrast cap; ensemble-weighted proxy; top outcoupling proxy; spectral FWHM proxy; angular FWHM proxy",
            "minimum_FDTD_entry_condition": "same as E0A-C, with added requirement that center contrast cap is not violated",
            "stop_condition": "stop if P/extraction proxy collapses or if tri-point average remains off-axis dominated",
        },
    ]


def proxy_variables() -> List[Dict[str, str]]:
    return [
        {"proxy_variable": "normal_offaxis_lower_bound", "purpose": "Require normal response to beat off-axis response before FDTD.", "source": "D8/D9 rule", "required": "true"},
        {"proxy_variable": "offaxis_20_60_penalty", "purpose": "Penalize broad off-axis energy away from normal.", "source": "D9 scoring", "required": "true"},
        {"proxy_variable": "offaxis_30_40_lobe_penalty", "purpose": "High-priority suppression of the D7 failure lobe band.", "source": "D7/D8 negative sample", "required": "true, higher weight than 20-60"},
        {"proxy_variable": "TE_TM_offaxis_risk_guard", "purpose": "Reject TE/TM phase cases where either polarization can create an off-axis resonance.", "source": "D5A/D9", "required": "true"},
        {"proxy_variable": "angular_FWHM_guard", "purpose": "Avoid broad angular output even if peak is near normal.", "source": "R2 target", "required": "true"},
        {"proxy_variable": "spectral_FWHM_guard", "purpose": "Keep source-module spectrum compatible with 453 nm target.", "source": "R2 target", "required": "true"},
        {"proxy_variable": "center_only_false_positive_flag", "purpose": "Prevent center-only normal resonance from driving shortlist selection.", "source": "D8/D9", "required": "true"},
        {"proxy_variable": "source_position_stability_required", "purpose": "Mark unvalidated source-position stability as requiring tri-point FDTD; never pretend it is proven by Python-only proxy.", "source": "D8", "required": "true"},
        {"proxy_variable": "edge_sensitivity_penalty", "purpose": "Penalize expected off-center source degradation.", "source": "D7 source-position failure", "required": "true"},
    ]


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file present in E0 output folder")

    input_audit = summarize_inputs()
    evidence = derive_d7_evidence()
    families = design_families()
    proxies = proxy_variables()

    write_csv(OUT / "r2_4e0_new_design_family_table.csv", families, [
        "family_id", "family_name", "physical_rationale", "expected_benefit", "main_risk",
        "python_only_proxy_variables", "minimum_FDTD_entry_condition", "stop_condition",
    ])
    write_csv(OUT / "r2_4e0_proxy_variables_v2.csv", proxies, ["proxy_variable", "purpose", "source", "required"])

    manifest = {
        "stage": "R2-4E0_new_design_family_reset_after_D9_no_pass",
        "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd_or_fsp_generated": True,
        "input_audit": input_audit,
        "evidence_summary": evidence,
        "family_count": len(families),
        "recommended_E1_task": "R2-4E1_Python_only_new_family_candidate_generator_proxy_scan",
        "route_decision": "Do not continue old D9 no-pass candidates into FDTD; reset to new design-family generation with D8 guards baked in.",
    }
    (OUT / "r2_4e0_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    reset = [
        "# R2-4E0 D9 No-Pass Route Reset",
        "",
        "D9 returned no-pass: the old candidate pool did not satisfy the D8-derived conservative guards. Therefore no old candidate should be hard-picked for more FDTD.",
        "",
        "## Why old-candidate FDTD is blocked",
        "- D7 proved D5_BASE_13461 fails the x-line x-dipole scout at 453 nm.",
        "- D8 diagnosed the failure mode: center-only near-normal emission does not represent the x-line source-position ensemble.",
        "- Off-center source positions can revive the 30-40 deg off-axis lobe.",
        "- D9 applied these guards to the old pool and found no justified shortlist.",
        "",
        "Continuing old candidates would repeat the center-only false-positive pattern instead of testing a corrected design hypothesis.",
    ]
    (OUT / "r2_4e0_d9_nopass_route_reset.md").write_text("\n".join(reset) + "\n", encoding="utf-8")

    entry_rules = [
        "# R2-4E0 FDTD Entry Rules",
        "",
        "These rules apply after Python-only E1 candidate generation. E0 itself runs no FDTD.",
        "",
        "1. No center-only FDTD verdict is allowed.",
        "2. First FDTD must be tri-point x-dipole at 453 nm only.",
        "3. Tri-point positions are x = [-0.7, 0.0, +0.7] um.",
        "4. Pass tri-point before any 5-point x-line.",
        "5. Pass 5-point before any 9-point x-line.",
        "6. Fail at any stage stops that candidate immediately.",
        "7. No y-dipole, z-out-of-plane, or broadband validation before tri-point pass.",
        "8. The tri-point guard must check normal/off-axis lower bound, 30-40 deg lobe revival, angular FWHM, and source-position consistency.",
    ]
    (OUT / "r2_4e0_fdtd_entry_rules.md").write_text("\n".join(entry_rules) + "\n", encoding="utf-8")

    e1_plan = [
        "# Recommended R2-4E1 Plan",
        "",
        "Recommended task name: **R2-4E1_Python_only_new_family_candidate_generator_proxy_scan**.",
        "",
        "E1 should be a Python-only candidate generator and proxy scan, not FDTD.",
        "",
        "## E1 Scope",
        "- Generate candidates from the E0 new design families instead of reusing the D9 no-pass pool.",
        "- Include lower-Q angle-stable, phase-balanced 30-40 rejection, finite-MQW source-position robust, and reduced-center-contrast families.",
        "- Score candidates with D8/D9 proxy terms baked in from the start.",
        "- Explicitly mark source-position stability as requires_tri_point_FDTD; do not claim it is proven by Python-only proxy.",
        "- Produce at most a tiny FDTD-ready shortlist, preferably 0-2 candidates.",
        "",
        "## E1 Must Not Do",
        "- Do not launch Lumerical.",
        "- Do not generate setup-only FSPs.",
        "- Do not run tri-point FDTD; that belongs to a later stage after E1 review.",
    ]
    (OUT / "r2_4e0_recommended_e1_plan.md").write_text("\n".join(e1_plan) + "\n", encoding="utf-8")

    summary = [
        "# R2-4E0 New Design-Family Reset After D9 No-Pass",
        "",
        "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.",
        "",
        "## One-Line Conclusion",
        "D9 no-pass closes the old candidate-pool route; R2-4E should reset to new design families that include source-position stability and 30-40 deg lobe suppression from the first proxy screen.",
        "",
        "## Evidence Snapshot",
        f"- D7 x-line average peak_abs_angle_deg: {evidence['d7_xline_avg_peak_abs_angle_deg']}",
        f"- D7 x-line average normal/offaxis ratio: {evidence['d7_xline_avg_normal_offaxis_ratio']}",
        f"- D7 x-line verdict/status: {evidence['d7_xline_avg_verdict']}",
        f"- D7 source-position peak_abs range/std: {evidence['d7_peak_abs_min_deg']} to {evidence['d7_peak_abs_max_deg']} / {evidence['d7_peak_abs_std_deg']}",
        f"- D9 hard pass count: {evidence['d9_hard_pass_count']} of {evidence['d9_scored_candidate_count']} scored candidates",
        "",
        "## New Family Directions",
    ]
    for f in families:
        summary.append(f"- **{f['family_id']}**: {f['family_name']}")
    summary += [
        "",
        "## Mandatory Guards From Start",
        "- center + bilateral source stability required",
        "- tri-point guard first: x = [-0.7, 0.0, +0.7] um",
        "- 30-40 deg off-axis lobe suppression",
        "- TE/TM off-axis risk guard",
        "- normal/offaxis lower-bound",
        "- angular FWHM guard",
        "- spectral FWHM guard",
        "",
        "## Recommended Next Task",
        "R2-4E1_Python_only_new_family_candidate_generator_proxy_scan",
    ]
    (OUT / "r2_4e0_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps({
        "output": str(OUT),
        "family_count": len(families),
        "recommended_E1_task": "R2-4E1_Python_only_new_family_candidate_generator_proxy_scan",
    }, indent=2))


if __name__ == "__main__":
    main()
