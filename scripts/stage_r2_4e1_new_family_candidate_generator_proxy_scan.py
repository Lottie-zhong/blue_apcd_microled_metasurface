from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = {
    "e0_family_table": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_new_design_family_table.csv",
    "e0_proxy_variables": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_proxy_variables_v2.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d9_scored": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_proxy_scored_candidates.csv",
    "d9_decision": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_no_pass_or_shortlist_decision.md",
    "d2_top20": ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize" / "r2_4d2_top20_candidate_metrics.csv",
    "d3_near_pass": ROOT / "outputs" / "r2_4d3_cavity_phase_design_space_reset" / "r2_4d3_near_pass_candidates.csv",
    "d4_spacers": ROOT / "outputs" / "r2_4d4_focused_cavity_phase_sweep" / "r2_4d4_best_phase_guided_spacers.csv",
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
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def gaussian(x: float, sigma: float) -> float:
    return math.exp(-0.5 * (x / sigma) ** 2)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


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


def family_configs() -> List[Dict[str, Any]]:
    return [
        {
            "family_id": "E0A_lower_Q_angle_stable_cavity",
            "top_pairs": [4, 5, 6],
            "bottom_pairs": [4, 6, 8],
            "cavity_nm": [220, 250, 280],
            "top_terms_nm": [0, 35],
            "bottom_terms_nm": [25, 65],
            "q_bias": -0.25,
        },
        {
            "family_id": "E0B_phase_balanced_DBR_30_40_reject",
            "top_pairs": [6, 8],
            "bottom_pairs": [8, 10, 12],
            "cavity_nm": [210, 240, 270],
            "top_terms_nm": [20, 60],
            "bottom_terms_nm": [40, 90],
            "q_bias": 0.05,
        },
        {
            "family_id": "E0C_MQW_lateral_extent_robust_cavity",
            "top_pairs": [4, 6, 7],
            "bottom_pairs": [4, 6, 8],
            "cavity_nm": [230, 260, 290],
            "top_terms_nm": [10, 45],
            "bottom_terms_nm": [30, 75],
            "q_bias": -0.10,
        },
        {
            "family_id": "E0D_reduced_center_contrast_control",
            "top_pairs": [3, 4, 5],
            "bottom_pairs": [4, 6, 8],
            "cavity_nm": [240, 270, 300],
            "top_terms_nm": [0, 50],
            "bottom_terms_nm": [50, 100],
            "q_bias": -0.35,
        },
    ]


def generate_candidates() -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seq = 1
    for fam in family_configs():
        for top in fam["top_pairs"]:
            for bottom in fam["bottom_pairs"]:
                for cavity in fam["cavity_nm"]:
                    for top_term in fam["top_terms_nm"]:
                        for bottom_term in fam["bottom_terms_nm"]:
                            cid = f"E1_{seq:04d}"
                            candidates.append({
                                "candidate_id": cid,
                                "family_id": fam["family_id"],
                                "top_pair_count": top,
                                "bottom_pair_count": bottom,
                                "top_termination_nm": top_term,
                                "bottom_termination_nm": bottom_term,
                                "cavity_physical_thickness_nm": cavity,
                                "cavity_optical_thickness_proxy_nm": round(cavity * 2.45, 3),
                                "spacer_or_cap_thickness_nm": top_term + bottom_term,
                                "target_wavelength_nm": 453,
                                "te_tm_angle_grid_deg": "0:0.5:60",
                                "wavelength_grid_nm": "445:0.5:460",
                                "source_position_status": "requires_tri_point_FDTD",
                                "negative_reference_excluded": "D5_BASE_13461",
                                "q_bias": fam["q_bias"],
                            })
                            seq += 1
    return candidates


def score_candidate(c: Dict[str, Any]) -> Dict[str, Any]:
    top = float(c["top_pair_count"])
    bottom = float(c["bottom_pair_count"])
    cavity = float(c["cavity_physical_thickness_nm"])
    top_term = float(c["top_termination_nm"])
    bottom_term = float(c["bottom_termination_nm"])
    q_bias = float(c["q_bias"])
    family = c["family_id"]

    balance = 1.0 - min(1.0, abs(top - bottom) / 10.0)
    q_proxy = clamp01(0.30 + 0.035 * (top + bottom) + q_bias)
    phase_center = 250.0 if family == "E0A_lower_Q_angle_stable_cavity" else 240.0
    if family == "E0C_MQW_lateral_extent_robust_cavity":
        phase_center = 260.0
    if family == "E0D_reduced_center_contrast_control":
        phase_center = 270.0
    cavity_phase_alignment = gaussian(cavity - phase_center, 35.0)
    termination_balance = gaussian((bottom_term - top_term) - 45.0, 45.0)
    rejection_phase = gaussian((bottom_term + 0.55 * top_term) - 100.0, 35.0)

    normal_strength_proxy = clamp01(0.25 + 0.35 * cavity_phase_alignment + 0.25 * balance + 0.15 * termination_balance)
    center_contrast_proxy = clamp01(normal_strength_proxy * (0.70 + 0.75 * q_proxy))
    offaxis_20_60_penalty = clamp01(0.60 * q_proxy + 0.25 * (1.0 - balance) + 0.15 * (1.0 - rejection_phase))
    offaxis_30_40_lobe_penalty = clamp01(0.55 * q_proxy + 0.35 * (1.0 - rejection_phase) + 0.20 * max(0.0, center_contrast_proxy - 0.78))

    if family == "E0A_lower_Q_angle_stable_cavity":
        offaxis_20_60_penalty *= 0.82
        offaxis_30_40_lobe_penalty *= 0.78
    elif family == "E0B_phase_balanced_DBR_30_40_reject":
        offaxis_30_40_lobe_penalty *= 0.68
    elif family == "E0C_MQW_lateral_extent_robust_cavity":
        offaxis_20_60_penalty *= 0.86
        offaxis_30_40_lobe_penalty *= 0.72
    elif family == "E0D_reduced_center_contrast_control":
        center_contrast_proxy *= 0.78
        normal_strength_proxy *= 0.92
        offaxis_30_40_lobe_penalty *= 0.80

    te_tm_mismatch_proxy = clamp01(abs(top_term - bottom_term) / 140.0 + abs(top - bottom) / 24.0)
    te_tm_offaxis_risk_guard = clamp01(0.55 * te_tm_mismatch_proxy + 0.45 * offaxis_30_40_lobe_penalty)
    spectral_center_nm_proxy = 453.0 + 0.010 * (cavity - phase_center) + 0.018 * (top_term - bottom_term)
    spectral_fwhm_nm_proxy = max(3.5, 10.5 - 5.0 * q_proxy + 1.5 * offaxis_30_40_lobe_penalty)
    angular_fwhm_deg_proxy = max(5.0, 7.0 + 22.0 * offaxis_20_60_penalty - 5.0 * normal_strength_proxy)
    normal_offaxis_proxy = normal_strength_proxy / max(0.05, 0.55 * offaxis_20_60_penalty + 0.75 * offaxis_30_40_lobe_penalty)

    center_only_false_positive_risk = "high" if normal_strength_proxy > 0.72 and offaxis_30_40_lobe_penalty > 0.34 else "medium"
    if normal_strength_proxy < 0.45:
        center_only_false_positive_risk = "low"
    d5_like_risk_flag = "high" if center_only_false_positive_risk == "high" else "low"
    if offaxis_30_40_lobe_penalty > 0.42:
        d5_like_risk_flag = "high"

    hard_fail_reasons: List[str] = []
    if offaxis_30_40_lobe_penalty > 0.33:
        hard_fail_reasons.append("30_40_lobe_penalty_above_E1_guard")
    if offaxis_20_60_penalty > 0.52:
        hard_fail_reasons.append("20_60_offaxis_penalty_above_guard")
    if te_tm_offaxis_risk_guard > 0.32:
        hard_fail_reasons.append("TE_TM_offaxis_risk_guard_fail")
    if spectral_fwhm_nm_proxy > 8.0:
        hard_fail_reasons.append("spectral_FWHM_proxy_above_8nm")
    if angular_fwhm_deg_proxy > 25.0:
        hard_fail_reasons.append("angular_FWHM_proxy_above_25deg")
    if normal_offaxis_proxy <= 1.0:
        hard_fail_reasons.append("normal_offaxis_proxy_not_above_1")
    if center_only_false_positive_risk == "high":
        hard_fail_reasons.append("center_only_false_positive_risk_high")
    if d5_like_risk_flag == "high":
        hard_fail_reasons.append("D5_like_risk_high")

    hard_pass = len(hard_fail_reasons) == 0
    v2_score = (
        2.0 * normal_offaxis_proxy
        + 0.8 * normal_strength_proxy
        - 1.0 * offaxis_20_60_penalty
        - 2.6 * offaxis_30_40_lobe_penalty
        - 1.4 * te_tm_offaxis_risk_guard
        - 0.25 * abs(spectral_center_nm_proxy - 453.0)
        - 0.10 * spectral_fwhm_nm_proxy
        - 0.04 * angular_fwhm_deg_proxy
    )

    return {
        **c,
        "normal_angle_resonance_strength_proxy": round(normal_strength_proxy, 6),
        "normal_offaxis_proxy": round(normal_offaxis_proxy, 6),
        "offaxis_20_60_penalty": round(offaxis_20_60_penalty, 6),
        "offaxis_30_40_lobe_penalty": round(offaxis_30_40_lobe_penalty, 6),
        "te_tm_mismatch_proxy": round(te_tm_mismatch_proxy, 6),
        "te_tm_offaxis_risk_guard": round(te_tm_offaxis_risk_guard, 6),
        "angular_fwhm_deg_proxy": round(angular_fwhm_deg_proxy, 6),
        "spectral_center_nm_proxy": round(spectral_center_nm_proxy, 6),
        "spectral_fwhm_nm_proxy": round(spectral_fwhm_nm_proxy, 6),
        "center_only_false_positive_risk": center_only_false_positive_risk,
        "source_position_stability_status": "requires_tri_point_FDTD",
        "d5_like_risk_flag": d5_like_risk_flag,
        "hard_pass": hard_pass,
        "hard_fail_reasons": "none" if hard_pass else ";".join(hard_fail_reasons),
        "v2_proxy_score": round(v2_score, 6),
    }


def make_shortlist(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    passed = [r for r in scored if r["hard_pass"]]
    passed.sort(key=lambda r: r["v2_proxy_score"], reverse=True)
    shortlist = []
    used_families = set()
    for r in passed:
        if r["family_id"] in used_families and len(shortlist) < 2:
            continue
        row = dict(r)
        row["shortlist_role"] = "primary" if not shortlist else "backup"
        row["minimum_fdtd_entry_plan"] = "tri-point x=[-0.7,0,+0.7] um; x-dipole only; 453 nm only; pass before 5-point; fail stops candidate; no y/z/broadband before pass"
        shortlist.append(row)
        used_families.add(r["family_id"])
        if len(shortlist) >= 3:
            break
    return shortlist


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file present in E1 output folder")
    audit = input_audit()
    candidates = generate_candidates()
    scored = [score_candidate(c) for c in candidates]
    scored.sort(key=lambda r: (r["hard_pass"], r["v2_proxy_score"]), reverse=True)
    shortlist = make_shortlist(scored)
    decision = "shortlist" if shortlist else "no-pass"

    inventory_fields = [
        "candidate_id", "family_id", "top_pair_count", "bottom_pair_count", "top_termination_nm", "bottom_termination_nm",
        "cavity_physical_thickness_nm", "cavity_optical_thickness_proxy_nm", "spacer_or_cap_thickness_nm",
        "target_wavelength_nm", "te_tm_angle_grid_deg", "wavelength_grid_nm", "source_position_status", "negative_reference_excluded",
    ]
    write_csv(OUT / "r2_4e1_candidate_inventory.csv", candidates, inventory_fields)

    score_fields = inventory_fields + [
        "normal_angle_resonance_strength_proxy", "normal_offaxis_proxy", "offaxis_20_60_penalty",
        "offaxis_30_40_lobe_penalty", "te_tm_mismatch_proxy", "te_tm_offaxis_risk_guard",
        "angular_fwhm_deg_proxy", "spectral_center_nm_proxy", "spectral_fwhm_nm_proxy",
        "center_only_false_positive_risk", "source_position_stability_status", "d5_like_risk_flag",
        "hard_pass", "hard_fail_reasons", "v2_proxy_score",
    ]
    write_csv(OUT / "r2_4e1_proxy_scored_candidates.csv", scored, score_fields)

    shortlist_fields = score_fields + ["shortlist_role", "minimum_fdtd_entry_plan"]
    write_csv(OUT / "r2_4e1_shortlist.csv", shortlist, shortlist_fields)

    config = {
        "stage": "R2-4E1_new_family_candidate_generator_proxy_scan",
        "candidate_count": len(candidates),
        "families": [f["family_id"] for f in family_configs()],
        "target_wavelength_nm": 453,
        "angle_grid_deg": "0:0.5:60",
        "wavelength_grid_nm": "445:0.5:460",
        "method": "Python-only analytic/TMM-style stack proxy; not FDTD-equivalent and not source-position validated",
        "hard_guards": {
            "offaxis_30_40_lobe_penalty_max": 0.33,
            "offaxis_20_60_penalty_max": 0.52,
            "te_tm_offaxis_risk_guard_max": 0.32,
            "spectral_fwhm_nm_proxy_max": 8.0,
            "angular_fwhm_deg_proxy_max": 25.0,
            "normal_offaxis_proxy_min": 1.0,
        },
    }
    (OUT / "r2_4e1_candidate_generation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    manifest = {
        "stage": "R2-4E1_new_family_candidate_generator_proxy_scan",
        "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd_or_fsp_generated": True,
        "input_audit": audit,
        "candidate_count": len(candidates),
        "hard_pass_count": sum(1 for r in scored if r["hard_pass"]),
        "decision": decision,
        "shortlist_count": len(shortlist),
    }
    (OUT / "r2_4e1_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    decision_lines = [
        "# R2-4E1 No-Pass Or Shortlist Decision",
        "",
        f"Decision: **{decision}**.",
        "",
        "No candidate is accepted from center/normal proxy alone. Source-position stability remains explicitly unverified and requires tri-point FDTD.",
    ]
    if shortlist:
        decision_lines += ["", "## Shortlist"]
        for r in shortlist:
            decision_lines.append(f"- {r['shortlist_role']}: {r['candidate_id']} ({r['family_id']}), score={r['v2_proxy_score']}, normal/offaxis={r['normal_offaxis_proxy']}, 30-40 penalty={r['offaxis_30_40_lobe_penalty']}")
    else:
        decision_lines += ["", "No candidate passed all E1 hard guards. Do not enter FDTD from this E1 run."]
    (OUT / "r2_4e1_no_pass_or_shortlist_decision.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

    entry_lines = [
        "# R2-4E1 Tri-Point FDTD Entry Plan",
        "",
        "E1 does not run FDTD. If a candidate is shortlisted, the only allowed first validation is:",
        "",
        "- x positions: [-0.7, 0.0, +0.7] um",
        "- dipole: x-oriented only",
        "- wavelength: 453 nm only",
        "- pass before 5-point x-line",
        "- fail stops that candidate immediately",
        "- no y-dipole, z-out-of-plane, or broadband before tri-point pass",
    ]
    if shortlist:
        entry_lines += ["", "## Candidate Plans"]
        for r in shortlist:
            entry_lines.append(f"- {r['candidate_id']}: {r['minimum_fdtd_entry_plan']}")
    (OUT / "r2_4e1_tri_point_fdtd_entry_plan.md").write_text("\n".join(entry_lines) + "\n", encoding="utf-8")

    summary = [
        "# R2-4E1 New-Family Candidate Generator / Proxy Scan",
        "",
        "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.",
        "",
        f"Generated candidates: {len(candidates)}",
        f"Hard-pass proxy candidates: {sum(1 for r in scored if r['hard_pass'])}",
        f"Decision: **{decision}**",
        "",
        "The proxy is an analytic/TMM-style screen for design-family triage. It is not a substitute for tri-point source-position FDTD.",
        "",
        "## Top Candidates",
        "| candidate_id | family_id | hard_pass | score | normal/offaxis | 30-40 penalty | TE/TM guard | spectral FWHM | angular FWHM |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in scored[:8]:
        summary.append(f"| {r['candidate_id']} | {r['family_id']} | {r['hard_pass']} | {r['v2_proxy_score']} | {r['normal_offaxis_proxy']} | {r['offaxis_30_40_lobe_penalty']} | {r['te_tm_offaxis_risk_guard']} | {r['spectral_fwhm_nm_proxy']} | {r['angular_fwhm_deg_proxy']} |")
    if shortlist:
        summary += ["", "## Shortlist"]
        for r in shortlist:
            summary.append(f"- {r['shortlist_role']}: {r['candidate_id']} / {r['family_id']} -> tri-point x-dipole 453 nm only.")
    else:
        summary += ["", "## No-Pass", "No candidate satisfied every hard guard; do not force FDTD from E1."]
    (OUT / "r2_4e1_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps({"decision": decision, "candidate_count": len(candidates), "shortlist_count": len(shortlist), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
