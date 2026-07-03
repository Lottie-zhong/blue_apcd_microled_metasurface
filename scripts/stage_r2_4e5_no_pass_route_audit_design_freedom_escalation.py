from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4e5_no_pass_route_audit_design_freedom_escalation"
OUT.mkdir(parents=True, exist_ok=True)
FORBIDDEN_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}

INPUTS = {
    "d7_case_metrics": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_case_metrics.csv",
    "d7_average": ROOT / "outputs" / "r2_4d7_xline_xdipole_fdtd_scout_d5_primary" / "r2_4d7_xline_average_metrics.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d9_scored": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_proxy_scored_candidates.csv",
    "e0_families": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_new_design_family_table.csv",
    "e1_shortlist": ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan" / "r2_4e1_shortlist.csv",
    "e2_case_results": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_case_results.csv",
    "e2_average": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_tri_point_incoherent_average.csv",
    "e3_terms": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction" / "r2_4e3_proxy_correction_terms.csv",
    "e4_manifest": ROOT / "outputs" / "r2_4e4_candidate_generator_v3_faroffaxis_guard" / "r2_4e4_manifest.json",
    "e4_scored": ROOT / "outputs" / "r2_4e4_candidate_generator_v3_faroffaxis_guard" / "r2_4e4_proxy_scored_candidates_v3.csv",
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def input_audit() -> List[Dict[str, Any]]:
    rows = []
    for name, path in INPUTS.items():
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise RuntimeError(f"Forbidden heavy input configured: {path}")
        row_count: Any = "n/a"
        if path.suffix.lower() == ".csv":
            row_count = len(read_csv(path))
        rows.append({
            "input_name": name,
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "kind": path.suffix.lower().lstrip("."),
            "row_count": row_count,
            "status": "loaded" if path.exists() else "missing",
        })
    return rows


def first(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return rows[0] if rows else {}


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file already present in E5 output")
    d7_avg = first(read_csv(INPUTS["d7_average"]))
    e2_avg = first(read_csv(INPUTS["e2_average"]))
    e4_manifest = read_json(INPUTS["e4_manifest"])

    taxonomy = [
        {
            "negative_sample": "D5_BASE_13461",
            "stage_evidence": "R2-4D7 / R2-4D8 / R2-4D9",
            "failure_class": "center-only false positive + source-position instability + 30-40 deg lobe",
            "key_metric_summary": f"D7 x-line avg peak_abs={d7_avg.get('peak_abs_angle_deg','missing')} deg; normal/offaxis={d7_avg.get('normal_offaxis_ratio','missing')}; verdict={d7_avg.get('verdict', d7_avg.get('status','missing'))}",
            "route_decision": "old D5 / old candidate-pool route closed; no D5 revival",
        },
        {
            "negative_sample": "E1_0236",
            "stage_evidence": "R2-4E1 / R2-4E2 / R2-4E3",
            "failure_class": "stable far-offaxis 49-52 deg leaky/guided-like channel + proxy false positive",
            "key_metric_summary": f"E2 tri-point avg peak_abs={e2_avg.get('tri_point_avg_peak_abs_angle_deg','missing')} deg; normal/offaxis={e2_avg.get('tri_point_avg_normal_offaxis_ratio','missing')}; FWHM={e2_avg.get('tri_point_avg_fwhm_deg','missing')} deg",
            "route_decision": "stop E1_0236; no 5-point/9-point/y/z/broadband",
        },
        {
            "negative_sample": "E4_v3_candidate_pool",
            "stage_evidence": "R2-4E4",
            "failure_class": "small-range new-family scan no-pass after 30-40, 45-55 and 40-60 guards",
            "key_metric_summary": f"E4 generated {e4_manifest.get('candidate_count','missing')} candidates; hard_pass={e4_manifest.get('hard_pass_count','missing')}; shortlist={e4_manifest.get('shortlist_count','missing')}; decision={e4_manifest.get('decision','missing')}",
            "route_decision": "do not hard-pick from E4 no-pass; escalate design freedom",
        },
    ]
    write_csv(OUT / "r2_4e5_negative_sample_taxonomy.csv", taxonomy, ["negative_sample", "stage_evidence", "failure_class", "key_metric_summary", "route_decision"])

    gap_rows = [
        {"gap_id": "G1", "current_limitation": "Python-only stack proxy cannot truly verify source-position stability", "evidence": "D5 and E1 show proxy/FDTD mismatch under x-line or tri-point source positions", "needed_design_freedom": "finite-source-aware prefilter and minimal FDTD-in-loop gate only after stronger analytic filtering", "priority": "P0"},
        {"gap_id": "G2", "current_limitation": "candidate variables are mostly DBR pair count, termination, and cavity thickness", "evidence": "E4 no-pass after 480 candidates with far-offaxis guards", "needed_design_freedom": "top angular outcoupler/MDC concept, lateral aperture control, phase/absorbing terminations", "priority": "P0"},
        {"gap_id": "G3", "current_limitation": "off-axis suppression is not explicitly designed as an angular stopband", "evidence": "E1_0236 stable 49-52 deg channel survived proxy", "needed_design_freedom": "explicit 30-40, 40-60, 45-55 angular stopband design objectives", "priority": "P0"},
        {"gap_id": "G4", "current_limitation": "high-Q/center resonance proxies can create false positives", "evidence": "D5 and E1 both looked attractive in proxy/center metrics before FDTD failure", "needed_design_freedom": "lower-Q variants and center-contrast caps with normal-cone lower-bound", "priority": "P1"},
        {"gap_id": "G5", "current_limitation": "manufacturability and literature MDC constraints are not yet folded into expanded route", "evidence": "blind E-series scans exhausted local stack family", "needed_design_freedom": "literature/experimental MDC constraints and simpler multilayer targets", "priority": "P1"},
    ]
    write_csv(OUT / "r2_4e5_design_freedom_gap_table.csv", gap_rows, ["gap_id", "current_limitation", "evidence", "needed_design_freedom", "priority"])

    route_rows = [
        {"route_id": "A", "route_name": "Expand 1D stack design freedom", "physical_rationale": "The local pair-count/termination/cavity window is exhausted; broader asymmetric mirrors and lower-Q variants may shift or suppress far-offaxis modes.", "expected_benefit": "Find stacks with lower far-offaxis risk before FDTD", "cost": "low to medium Python-only scan cost", "risk": "may still miss finite-source/lateral effects", "recommended_next_task": "R2-4F0 expanded design-space specification", "fdtd_allowed_immediately": "no"},
        {"route_id": "B", "route_name": "Add MDC/top angular filter concept", "physical_rationale": "Bare RCLED stack lacks enough angular selectivity; top angular-selective multilayer/outcoupler can target normal passband and off-axis stopband.", "expected_benefit": "More direct control of 30-60 deg rejection", "cost": "medium design/spec effort before FDTD", "risk": "more variables and manufacturability constraints", "recommended_next_task": "R2-4F0 RCLED-MDC angular filter / stack-plus-MDC concept specification", "fdtd_allowed_immediately": "no"},
        {"route_id": "C", "route_name": "Finite-source-aware reduced FDTD-in-loop", "physical_rationale": "Python proxy cannot prove source-position stability; FDTD can be used only as a tiny guard after stricter prefiltering.", "expected_benefit": "Avoid long false-positive chains", "cost": "limited FDTD after Python shortlist only", "risk": "can become expensive if shortlist rules loosen", "recommended_next_task": "later F-stage tri-point guard after F0/F1 review", "fdtd_allowed_immediately": "no"},
        {"route_id": "D", "route_name": "Pause stack-only route and use literature/experimental MDC constraints", "physical_rationale": "A simpler manufacturable multilayer target may be more reliable than unconstrained proxy search", "expected_benefit": "Grounds route in known MDC behavior and fabrication realism", "cost": "literature/model audit effort", "risk": "may narrow solution space too early", "recommended_next_task": "R2-4F0 include literature/experimental constraint table", "fdtd_allowed_immediately": "no"},
    ]
    write_csv(OUT / "r2_4e5_next_route_options.csv", route_rows, ["route_id", "route_name", "physical_rationale", "expected_benefit", "cost", "risk", "recommended_next_task", "fdtd_allowed_immediately"])

    route_audit = [
        "# R2-4E5 Route Audit",
        "",
        "D7/D8/D9 closed the old D5/old-candidate route. E1/E2/E3 closed the first new-family shortlist because E1_0236 was a severe proxy false positive with a stable 49-52 deg far-offaxis channel. E4 then applied far-offaxis guards and found no hard-pass candidates in the local new-family scan.",
        "",
        "The issue is no longer just threshold tuning. The current design freedom is too narrow: mostly DBR pair counts, terminations, and cavity thickness. The next route needs explicit angular stopband/outcoupler freedom and finite-source-aware validation gates.",
        "",
        "Do not select an E4 no-pass candidate for FDTD. Do not revive D5 or E1_0236.",
    ]
    (OUT / "r2_4e5_route_audit.md").write_text("\n".join(route_audit) + "\n", encoding="utf-8")

    f0_plan = [
        "# R2-4E5 Recommended F0 Plan",
        "",
        "Recommended task name: **R2-4F0_Python_only_expanded_design_space_spec_RCLED_MDC_angular_filter**.",
        "",
        "F0 should not run FDTD. It should define the expanded design space before more candidate generation.",
        "",
        "Required F0 scope:",
        "- RCLED-MDC as cavity + angular-selective top multilayer, not bare RCLED stack only.",
        "- explicit 30-40, 45-55, and broad 40-60 deg angular stopband requirements.",
        "- expanded terminations, asymmetric DBR pairs, wider cavity/spacer/cap ranges, lower-Q variants.",
        "- possible lateral aperture / finite-source constraints.",
        "- literature or experimental MDC constraints for manufacturable multilayer targets.",
        "",
        "F0 output should be a design-space specification and candidate-generation rules for a later F1 Python-only scan.",
    ]
    (OUT / "r2_4e5_recommended_f0_plan.md").write_text("\n".join(f0_plan) + "\n", encoding="utf-8")

    gate = [
        "# R2-4E5 FDTD Gate Rules",
        "",
        "FDTD is not allowed immediately after E5.",
        "",
        "When a future candidate is reviewed and cleared:",
        "1. first FDTD must be tri-point x-dipole at 453 nm only; x = [-0.7, 0.0, +0.7] um",
        "2. pass tri-point before any 5-point x-line",
        "3. pass 5-point before any 9-point x-line",
        "4. fail stops that candidate immediately",
        "5. no y-dipole, z-out-of-plane, or broadband before tri-point pass",
        "6. no FDTD from E4 no-pass or old D5/E1_0236 candidates",
    ]
    (OUT / "r2_4e5_fdtd_gate_rules.md").write_text("\n".join(gate) + "\n", encoding="utf-8")

    summary = [
        "# R2-4E5 No-Pass Route Audit And Design-Freedom Escalation",
        "",
        "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.",
        "",
        "## One-Line Conclusion",
        "R2-4D/E has exhausted the current stack-only local design freedom; do not hard-pick from E4 no-pass, and move to R2-4F0 to specify an expanded RCLED-MDC angular-filter design space before any further FDTD.",
        "",
        "## Recommendation",
        "Prioritize **R2-4F0_Python_only_expanded_design_space_spec_RCLED_MDC_angular_filter** over continued E-series blind scanning.",
        "",
        "Immediate FDTD allowed: **no**.",
    ]
    (OUT / "r2_4e5_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    manifest = {
        "stage": "R2-4E5_no_pass_route_audit_design_freedom_escalation",
        "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd_or_fsp_generated": True,
        "input_audit": input_audit(),
        "recommended_F0_task": "R2-4F0_Python_only_expanded_design_space_spec_RCLED_MDC_angular_filter",
        "immediate_FDTD_allowed": False,
        "do_not_hard_pick_E4_no_pass": True,
        "do_not_revive_D5_or_E1_0236": True,
    }
    (OUT / "r2_4e5_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "output": str(OUT),
        "recommended_F0_task": manifest["recommended_F0_task"],
        "immediate_FDTD_allowed": manifest["immediate_FDTD_allowed"],
    }, indent=2))


if __name__ == "__main__":
    main()
