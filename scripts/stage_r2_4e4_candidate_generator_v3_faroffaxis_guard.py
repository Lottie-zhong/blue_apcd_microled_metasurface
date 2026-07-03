from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4e4_candidate_generator_v3_faroffaxis_guard"
OUT.mkdir(parents=True, exist_ok=True)
FORBIDDEN_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}

INPUTS = {
    "e3_terms": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction" / "r2_4e3_proxy_correction_terms.csv",
    "e3_mismatch": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction" / "r2_4e3_e1_proxy_vs_e2_fdtd_mismatch.csv",
    "e2_average": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_tri_point_incoherent_average.csv",
    "e2_cases": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_case_results.csv",
    "e1_shortlist": ROOT / "outputs" / "r2_4e1_new_family_candidate_generator_proxy_scan" / "r2_4e1_shortlist.csv",
    "e0_families": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_new_design_family_table.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d9_scored": ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2" / "r2_4d9_proxy_scored_candidates.csv",
}


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


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def gaussian(x: float, sigma: float) -> float:
    return math.exp(-0.5 * (x / sigma) ** 2)


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
        {"family_id": "E0A_lower_Q_angle_stable_cavity", "top_pairs": [3, 4, 5], "bottom_pairs": [3, 4, 5, 6], "cavity_nm": [220, 245, 270], "top_terms_nm": [0, 25, 50], "bottom_terms_nm": [20, 45, 70], "contrast_bias": -0.25},
        {"family_id": "E0B_phase_balanced_DBR_30_40_reject", "top_pairs": [5, 6, 7], "bottom_pairs": [7, 8, 9], "cavity_nm": [210, 240, 270], "top_terms_nm": [20, 55], "bottom_terms_nm": [45, 85], "contrast_bias": 0.0},
        {"family_id": "E0C_MQW_lateral_extent_robust_cavity", "top_pairs": [4, 5, 7], "bottom_pairs": [4, 5, 7], "cavity_nm": [225, 250, 285], "top_terms_nm": [15, 60], "bottom_terms_nm": [25, 95], "contrast_bias": -0.15},
        {"family_id": "E0D_reduced_center_contrast_control", "top_pairs": [2, 3, 4], "bottom_pairs": [3, 4, 5, 6], "cavity_nm": [235, 265, 295], "top_terms_nm": [0, 40], "bottom_terms_nm": [35, 80], "contrast_bias": -0.38},
    ]


def is_e1_like(top: int, bottom: int, cavity: float, top_term: float, bottom_term: float) -> bool:
    return abs(top - 6) <= 1 and abs(bottom - 6) <= 1 and abs(cavity - 260) <= 20 and abs(top_term - 45) <= 20 and abs(bottom_term - 75) <= 25


def is_d5_like(top: int, bottom: int, cavity: float, top_term: float, bottom_term: float) -> bool:
    return top >= 9 and bottom >= 10 and abs(cavity - 182) <= 45 and top_term <= 20 and abs(bottom_term - 113) <= 40


def generate_candidates() -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    seq = 1
    excluded = 0
    for fam in family_configs():
        for top in fam["top_pairs"]:
            for bottom in fam["bottom_pairs"]:
                for cavity in fam["cavity_nm"]:
                    for top_term in fam["top_terms_nm"]:
                        for bottom_term in fam["bottom_terms_nm"]:
                            e1_like = is_e1_like(top, bottom, cavity, top_term, bottom_term)
                            d5_like = is_d5_like(top, bottom, cavity, top_term, bottom_term)
                            if e1_like or d5_like:
                                excluded += 1
                                continue
                            candidates.append({
                                "candidate_id": f"E4_{seq:04d}",
                                "family_id": fam["family_id"],
                                "top_pair_count": top,
                                "bottom_pair_count": bottom,
                                "top_termination_nm": top_term,
                                "bottom_termination_nm": bottom_term,
                                "cavity_physical_thickness_nm": cavity,
                                "spacer_cap_total_nm": top_term + bottom_term,
                                "target_wavelength_nm": 453,
                                "te_tm_angle_grid_deg": "0:0.5:60",
                                "wavelength_grid_nm": "445:0.5:460",
                                "negative_reference_distance_flags": "not_E1_0236_like;not_D5_BASE_13461_like",
                                "source_position_stability_status": "requires_tri_point_FDTD",
                                "contrast_bias": fam["contrast_bias"],
                            })
                            seq += 1
    return candidates[:480]

def score_candidate(c: Dict[str, Any]) -> Dict[str, Any]:
    top = float(c["top_pair_count"]); bottom = float(c["bottom_pair_count"])
    cavity = float(c["cavity_physical_thickness_nm"]); top_term = float(c["top_termination_nm"]); bottom_term = float(c["bottom_termination_nm"])
    family = c["family_id"]; contrast_bias = float(c["contrast_bias"])

    pair_balance = 1.0 - min(1.0, abs(top - bottom) / 8.0)
    reflectivity_proxy = clamp01(0.18 + 0.045 * (top + bottom) + contrast_bias)
    if family == "E0A_lower_Q_angle_stable_cavity": phase_center = 245.0
    elif family == "E0B_phase_balanced_DBR_30_40_reject": phase_center = 238.0
    elif family == "E0C_MQW_lateral_extent_robust_cavity": phase_center = 250.0
    else: phase_center = 270.0
    normal_alignment = gaussian(cavity - phase_center, 38.0)
    termination_phase = gaussian((bottom_term - 0.6 * top_term) - 45.0, 35.0)
    faroffaxis_rejector = gaussian((bottom_term + top_term) - 105.0, 35.0) * gaussian(cavity - phase_center, 55.0)
    leaky_mode_distance = min(1.0, (abs(cavity - 260.0) / 45.0 + abs(top_term - 45.0) / 45.0 + abs(bottom_term - 75.0) / 55.0 + abs(top - 6) / 4.0 + abs(bottom - 6) / 4.0) / 3.0)

    normal_strength = clamp01(0.22 + 0.36 * normal_alignment + 0.22 * pair_balance + 0.18 * termination_phase - 0.10 * max(0, reflectivity_proxy - 0.72))
    normal_cone_lower_bound_proxy = clamp01(normal_strength * (0.75 + 0.25 * pair_balance) - 0.12 * reflectivity_proxy)
    off20_60 = clamp01(0.35 * reflectivity_proxy + 0.25 * (1 - pair_balance) + 0.22 * (1 - faroffaxis_rejector) + 0.18 * (1 - leaky_mode_distance))
    penalty30_40 = clamp01(0.32 * reflectivity_proxy + 0.22 * (1 - termination_phase) + 0.18 * (1 - pair_balance) + 0.10 * max(0, normal_strength - 0.78))
    penalty45_55 = clamp01(0.38 * reflectivity_proxy + 0.34 * (1 - leaky_mode_distance) + 0.22 * (1 - faroffaxis_rejector) + 0.18 * max(0, normal_strength - 0.72))
    penalty40_60 = clamp01(0.45 * penalty45_55 + 0.35 * off20_60 + 0.20 * reflectivity_proxy)

    if family == "E0A_lower_Q_angle_stable_cavity":
        penalty45_55 *= 0.88; penalty40_60 *= 0.88; off20_60 *= 0.92
    if family == "E0B_phase_balanced_DBR_30_40_reject":
        penalty30_40 *= 0.72; penalty45_55 *= 0.92
    if family == "E0C_MQW_lateral_extent_robust_cavity":
        penalty30_40 *= 0.86; penalty45_55 *= 0.84; penalty40_60 *= 0.86
    if family == "E0D_reduced_center_contrast_control":
        normal_strength *= 0.90; penalty45_55 *= 0.82; penalty40_60 *= 0.84; penalty30_40 *= 0.92

    te_tm_mismatch = clamp01(abs(top_term - bottom_term) / 150.0 + abs(top - bottom) / 24.0 + 0.20 * penalty45_55)
    te_tm_guard = clamp01(0.45 * te_tm_mismatch + 0.30 * penalty45_55 + 0.25 * penalty30_40)
    spectral_center = 453.0 + 0.012 * (cavity - phase_center) + 0.014 * (top_term - bottom_term)
    spectral_fwhm = max(3.5, 9.6 - 4.2 * reflectivity_proxy + 1.8 * penalty40_60)
    angular_fwhm = max(5.0, 8.0 + 22.0 * penalty40_60 + 12.0 * penalty45_55 - 6.0 * normal_strength)
    broad_fwhm_risk = clamp01(max(0.0, angular_fwhm - 20.0) / 20.0)
    normal_offaxis = normal_strength / max(0.05, 0.50 * off20_60 + 0.80 * penalty45_55 + 0.45 * penalty30_40)

    center_false_positive = "high" if normal_strength > 0.72 and (penalty45_55 > 0.26 or penalty40_60 > 0.32) else "medium"
    if normal_strength < 0.48: center_false_positive = "low"
    d5_like_risk = "high" if is_d5_like(int(top), int(bottom), cavity, top_term, bottom_term) else "low"
    e1_like_risk = "high" if is_e1_like(int(top), int(bottom), cavity, top_term, bottom_term) or leaky_mode_distance < 0.25 else "low"

    hard_reasons: List[str] = []
    if penalty30_40 > 0.28: hard_reasons.append("30_40_penalty_high")
    if penalty45_55 > 0.25: hard_reasons.append("45_55_faroffaxis_penalty_high")
    if penalty40_60 > 0.32: hard_reasons.append("40_60_broad_faroffaxis_penalty_high")
    if normal_cone_lower_bound_proxy < 0.42: hard_reasons.append("normal_cone_lower_bound_fails")
    if broad_fwhm_risk > 0.25: hard_reasons.append("broad_FWHM_risk_high")
    if te_tm_guard > 0.30: hard_reasons.append("TE_TM_offaxis_risk_high")
    if d5_like_risk == "high": hard_reasons.append("D5_like_risk_high")
    if e1_like_risk == "high": hard_reasons.append("E1_0236_like_risk_high")
    if center_false_positive == "high": hard_reasons.append("center_only_false_positive_risk_high")
    if normal_offaxis <= 1.0: hard_reasons.append("normal_offaxis_proxy_not_above_1")
    if spectral_fwhm > 8.0: hard_reasons.append("spectral_FWHM_proxy_above_8nm")
    hard_pass = len(hard_reasons) == 0

    score = 2.0 * normal_offaxis + 1.0 * normal_cone_lower_bound_proxy - 1.2 * off20_60 - 2.2 * penalty30_40 - 3.0 * penalty45_55 - 2.0 * penalty40_60 - 1.2 * te_tm_guard - 0.06 * angular_fwhm - 0.10 * spectral_fwhm - 0.20 * abs(spectral_center - 453.0)

    return {**c,
        "normal_angle_resonance_strength_proxy": round(normal_strength, 6),
        "normal_cone_energy_lower_bound_proxy": round(normal_cone_lower_bound_proxy, 6),
        "normal_offaxis_proxy": round(normal_offaxis, 6),
        "offaxis_20_60_penalty": round(off20_60, 6),
        "offaxis_30_40_lobe_penalty": round(penalty30_40, 6),
        "faroffaxis_45_55_lobe_penalty": round(penalty45_55, 6),
        "broad_40_60_faroffaxis_penalty": round(penalty40_60, 6),
        "te_tm_mismatch_proxy": round(te_tm_mismatch, 6),
        "te_tm_offaxis_risk_guard": round(te_tm_guard, 6),
        "angular_fwhm_deg_proxy": round(angular_fwhm, 6),
        "spectral_center_nm_proxy": round(spectral_center, 6),
        "spectral_fwhm_nm_proxy": round(spectral_fwhm, 6),
        "broad_fwhm_risk_guard": round(broad_fwhm_risk, 6),
        "center_only_false_positive_risk": center_false_positive,
        "d5_like_risk_flag": d5_like_risk,
        "e1_0236_like_risk_flag": e1_like_risk,
        "source_position_stability_status": "requires_tri_point_FDTD",
        "hard_pass": hard_pass,
        "hard_fail_reasons": "none" if hard_pass else ";".join(hard_reasons),
        "v3_proxy_score": round(score, 6)}


def make_shortlist(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    passed = [r for r in scored if r["hard_pass"]]
    passed.sort(key=lambda r: r["v3_proxy_score"], reverse=True)
    out = []
    used = set()
    for r in passed:
        if r["family_id"] in used:
            continue
        row = dict(r)
        row["shortlist_role"] = "primary" if not out else "backup"
        row["minimum_fdtd_entry_plan"] = "tri-point x=[-0.7,0,+0.7] um; x-dipole only; 453 nm only; pass before 5-point; fail stops candidate; no y/z/broadband before pass"
        out.append(row); used.add(r["family_id"])
        if len(out) >= 2: break
    return out


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file present in E4 output")
    audit = input_audit()
    candidates = generate_candidates()
    scored = [score_candidate(c) for c in candidates]
    scored.sort(key=lambda r: (r["hard_pass"], r["v3_proxy_score"]), reverse=True)
    shortlist = make_shortlist(scored)
    decision = "shortlist" if shortlist else "no-pass"

    inventory_fields = ["candidate_id","family_id","top_pair_count","bottom_pair_count","top_termination_nm","bottom_termination_nm","cavity_physical_thickness_nm","spacer_cap_total_nm","target_wavelength_nm","te_tm_angle_grid_deg","wavelength_grid_nm","negative_reference_distance_flags","source_position_stability_status"]
    write_csv(OUT / "r2_4e4_candidate_inventory.csv", candidates, inventory_fields)
    score_fields = inventory_fields + ["normal_angle_resonance_strength_proxy","normal_cone_energy_lower_bound_proxy","normal_offaxis_proxy","offaxis_20_60_penalty","offaxis_30_40_lobe_penalty","faroffaxis_45_55_lobe_penalty","broad_40_60_faroffaxis_penalty","te_tm_mismatch_proxy","te_tm_offaxis_risk_guard","angular_fwhm_deg_proxy","spectral_center_nm_proxy","spectral_fwhm_nm_proxy","broad_fwhm_risk_guard","center_only_false_positive_risk","d5_like_risk_flag","e1_0236_like_risk_flag","hard_pass","hard_fail_reasons","v3_proxy_score"]
    write_csv(OUT / "r2_4e4_proxy_scored_candidates_v3.csv", scored, score_fields)
    write_csv(OUT / "r2_4e4_shortlist.csv", shortlist, score_fields + ["shortlist_role", "minimum_fdtd_entry_plan"])

    config = {"stage": "R2-4E4_candidate_generator_v3_faroffaxis_guard", "candidate_count": len(candidates), "families": [f["family_id"] for f in family_configs()], "method": "Python-only analytic/TMM-style proxy; not FDTD-equivalent", "excluded_negative_references": ["E1_0236", "D5_BASE_13461", "D9 high-risk candidates"], "hard_guards": {"30_40_penalty_max": 0.28, "45_55_penalty_max": 0.25, "40_60_penalty_max": 0.32, "normal_cone_lower_bound_min": 0.42, "te_tm_guard_max": 0.30, "normal_offaxis_min": 1.0, "spectral_fwhm_max_nm": 8.0}}
    (OUT / "r2_4e4_candidate_generation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    manifest = {"stage": "R2-4E4_candidate_generator_v3_faroffaxis_guard", "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "python_only": True, "no_lumerical": True, "no_lumapi": True, "no_fdtd_or_fsp_generated": True, "input_audit": audit, "candidate_count": len(candidates), "hard_pass_count": sum(1 for r in scored if r["hard_pass"]), "decision": decision, "shortlist_count": len(shortlist)}
    (OUT / "r2_4e4_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    neg = ["# R2-4E4 Negative Reference Exclusion Report", "", "Excluded/blocked regions:", "- E1_0236 exact candidate and E1_0236-like neighborhood: top/bottom near 6/6, cavity near 260 nm, terms near 45/75 nm.", "- D5_BASE_13461 and D5-like high-reflectivity old-route neighborhood.", "- D9 no-pass high-risk candidates are not reused as shortlist candidates.", "", "E4 uses E3 far-offaxis feedback: candidates must pass both 30-40 and 45-55 deg penalties plus 40-60 broad far-offaxis guard."]
    (OUT / "r2_4e4_negative_reference_exclusion_report.md").write_text("\n".join(neg) + "\n", encoding="utf-8")

    decision_lines = ["# R2-4E4 No-Pass Or Shortlist Decision", "", f"Decision: **{decision}**.", "", "No candidate is accepted from center/normal proxy alone. Source-position stability remains requires_tri_point_FDTD."]
    if shortlist:
        decision_lines += ["", "## Shortlist"]
        for r in shortlist:
            decision_lines.append(f"- {r['shortlist_role']}: {r['candidate_id']} ({r['family_id']}), score={r['v3_proxy_score']}, normal/offaxis={r['normal_offaxis_proxy']}, 30-40={r['offaxis_30_40_lobe_penalty']}, 45-55={r['faroffaxis_45_55_lobe_penalty']}, 40-60={r['broad_40_60_faroffaxis_penalty']}")
    else:
        decision_lines += ["", "No candidate passed all v3 hard guards. Do not enter FDTD from E4."]
    (OUT / "r2_4e4_no_pass_or_shortlist_decision.md").write_text("\n".join(decision_lines) + "\n", encoding="utf-8")

    entry = ["# R2-4E4 Tri-Point FDTD Entry Plan", "", "E4 itself does not run FDTD. If a candidate is shortlisted, the only allowed first validation is:", "", "- x positions: [-0.7, 0.0, +0.7] um", "- dipole: x-oriented only", "- wavelength: 453 nm only", "- pass before 5-point x-line", "- fail stops that candidate immediately", "- no y-dipole, z-out-of-plane, or broadband before tri-point pass"]
    if shortlist:
        entry += ["", "## Candidate Plans"]
        for r in shortlist:
            entry.append(f"- {r['candidate_id']}: {r['minimum_fdtd_entry_plan']}")
    (OUT / "r2_4e4_tri_point_fdtd_entry_plan.md").write_text("\n".join(entry) + "\n", encoding="utf-8")

    summary = ["# R2-4E4 Candidate Generator V3 Far-Offaxis Guard", "", "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.", "", f"Generated candidates: {len(candidates)}", f"Hard-pass proxy candidates: {sum(1 for r in scored if r['hard_pass'])}", f"Decision: **{decision}**", "", "E4 adds E3-derived 45-55 deg and 40-60 deg far-offaxis guards to avoid E1_0236-like false positives.", "", "## Top Candidates", "| candidate_id | family_id | hard_pass | score | normal/offaxis | 30-40 | 45-55 | 40-60 | FWHM |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in scored[:8]:
        summary.append(f"| {r['candidate_id']} | {r['family_id']} | {r['hard_pass']} | {r['v3_proxy_score']} | {r['normal_offaxis_proxy']} | {r['offaxis_30_40_lobe_penalty']} | {r['faroffaxis_45_55_lobe_penalty']} | {r['broad_40_60_faroffaxis_penalty']} | {r['angular_fwhm_deg_proxy']} |")
    if shortlist:
        summary += ["", "## Shortlist"]
        for r in shortlist:
            summary.append(f"- {r['shortlist_role']}: {r['candidate_id']} / {r['family_id']} -> tri-point x-dipole 453 nm only.")
    else:
        summary += ["", "## No-Pass", "No candidate satisfied every v3 hard guard; do not force FDTD from E4."]
    (OUT / "r2_4e4_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(json.dumps({"decision": decision, "candidate_count": len(candidates), "shortlist_count": len(shortlist), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()

