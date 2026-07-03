from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4f0_literature_seeded_relaxed_target_rcled_mdc_scan"
OUT.mkdir(parents=True, exist_ok=True)
FORBIDDEN_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}

INPUTS = {
    "e4_manifest": ROOT / "outputs" / "r2_4e4_candidate_generator_v3_faroffaxis_guard" / "r2_4e4_manifest.json",
    "e4_scored": ROOT / "outputs" / "r2_4e4_candidate_generator_v3_faroffaxis_guard" / "r2_4e4_proxy_scored_candidates_v3.csv",
    "e3_terms": ROOT / "outputs" / "r2_4e3_e1_0236_fdtd_failure_diagnosis_proxy_correction" / "r2_4e3_proxy_correction_terms.csv",
    "e2_average": ROOT / "outputs" / "r2_4e2_e1_0236_tri_point_xdipole_fdtd_guard" / "r2_4e2_tri_point_incoherent_average.csv",
    "e0_families": ROOT / "outputs" / "r2_4e0_new_design_family_reset_after_d9_nopass" / "r2_4e0_new_design_family_table.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
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


def literature_seed_rows() -> List[Dict[str, Any]]:
    return [
        {"seed_id": "Huang_RC_microLED", "route_relevance": "Route A high-top-DBR RCLED", "reported_spectral_FWHM_nm": 6.8, "reported_divergence_deg": "top 9-pair simulation about 22.5", "use_in_F0": "relaxed spectral target and high-top-pair collimation trend", "caveat": "literature seed, not direct proof for this stack"},
        {"seed_id": "Lin_RC_microLED", "route_relevance": "Route A bottom-high/top-low RCLED control", "reported_spectral_FWHM_nm": 7.99, "reported_divergence_deg": 66.2, "use_in_F0": "bottom >=10 and top 3-4 pair reference, but angular divergence too broad", "caveat": "large-device result; useful as spectral not angular target"},
        {"seed_id": "Wan_MDC_microLED", "route_relevance": "Route B top-MDC angular filter", "reported_spectral_FWHM_nm": "<10", "reported_divergence_deg": "<25", "use_in_F0": "SiO2/TiO2 blue seed SiO2=100 nm TiO2=52 nm m=8", "caveat": "LCM route is polarization-assisted; reference only, not nonpolarized proof"},
    ]


def is_d5_like(c: Dict[str, Any]) -> bool:
    return c.get("route") == "A" and int(c.get("top_pair_count", 0)) >= 9 and int(c.get("bottom_pair_count", 0)) >= 10 and abs(float(c.get("cavity_thickness_nm", 0)) - 182) < 45 and float(c.get("top_termination_nm", 0)) <= 20 and abs(float(c.get("bottom_termination_nm", 0)) - 113) < 45


def is_e1_like(c: Dict[str, Any]) -> bool:
    return int(c.get("top_pair_count", 0)) in {5, 6, 7} and int(c.get("bottom_pair_count", 0)) in {5, 6, 7} and abs(float(c.get("cavity_thickness_nm", 0)) - 260) <= 20 and abs(float(c.get("top_termination_nm", 0)) - 45) <= 20 and abs(float(c.get("bottom_termination_nm", 0)) - 75) <= 25


def generate_candidates() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seq = 1
    # Route A: high-top DBR RCLED, high top-pair literature seed, relaxed divergence.
    for bottom in [10, 11, 12]:
        for top in [5, 6, 7, 8, 9]:
            for cavity in [205, 230, 255, 280]:
                for top_term in [0, 40, 80, 120]:
                    for bottom_term in [0, 60, 120]:
                        c = {"candidate_id": f"F0_{seq:04d}", "route": "A", "route_name": "high_top_DBR_RCLED", "top_pair_count": top, "bottom_pair_count": bottom, "top_termination_nm": top_term, "bottom_termination_nm": bottom_term, "cavity_thickness_nm": cavity, "mdc_m": "n/a", "mdc_sio2_nm": "n/a", "mdc_tio2_nm": "n/a", "cap_thickness_nm": top_term, "target_wavelength_nm": 453, "te_tm_angle_grid_deg": "0:0.5:60"}
                        if not is_d5_like(c) and not is_e1_like(c): rows.append(c); seq += 1
    # Route B: top MDC angular filter around SiO2=100/TiO2=52 seed.
    for m in [6, 7, 8, 9, 10]:
        for sio2 in [90, 100, 110, 115]:
            for tio2 in [45, 52, 60, 65]:
                for cap in [0, 40, 80]:
                    c = {"candidate_id": f"F0_{seq:04d}", "route": "B", "route_name": "top_MDC_angular_filter", "top_pair_count": m, "bottom_pair_count": 0, "top_termination_nm": cap, "bottom_termination_nm": 0, "cavity_thickness_nm": 230, "mdc_m": m, "mdc_sio2_nm": sio2, "mdc_tio2_nm": tio2, "cap_thickness_nm": cap, "target_wavelength_nm": 453, "te_tm_angle_grid_deg": "0:0.5:60"}
                    if not is_d5_like(c) and not is_e1_like(c): rows.append(c); seq += 1
    # Route C: hybrid high-top DBR + non-quarter-wave terminal/MDC cap.
    for bottom in [10, 11, 12]:
        for top in [7, 8, 9]:
            for cavity in [210, 240, 270]:
                for cap in [20, 60, 100, 120]:
                    c = {"candidate_id": f"F0_{seq:04d}", "route": "C", "route_name": "hybrid_high_top_DBR_MDC_cap", "top_pair_count": top, "bottom_pair_count": bottom, "top_termination_nm": cap, "bottom_termination_nm": cap / 2, "cavity_thickness_nm": cavity, "mdc_m": top, "mdc_sio2_nm": 100, "mdc_tio2_nm": 52, "cap_thickness_nm": cap, "target_wavelength_nm": 453, "te_tm_angle_grid_deg": "0:0.5:60"}
                    if not is_d5_like(c) and not is_e1_like(c): rows.append(c); seq += 1
    return rows[:800]


def score(c: Dict[str, Any]) -> Dict[str, Any]:
    route = c["route"]
    top = float(c["top_pair_count"]); bottom = float(c["bottom_pair_count"])
    cavity = float(c["cavity_thickness_nm"]); top_term = float(c["top_termination_nm"]); bottom_term = float(c["bottom_termination_nm"])
    mdc_m = 0 if c["mdc_m"] == "n/a" else float(c["mdc_m"])
    sio2 = 100 if c["mdc_sio2_nm"] == "n/a" else float(c["mdc_sio2_nm"])
    tio2 = 52 if c["mdc_tio2_nm"] == "n/a" else float(c["mdc_tio2_nm"])

    spectral_seed = gaussian((sio2 - 100) / 8.0 + (tio2 - 52) / 5.0, 1.6)
    cavity_align = gaussian(cavity - 240, 45)
    pair_asym = abs(top - bottom) / max(1.0, top + bottom) if bottom else 0.25
    top_collimation = clamp01(0.15 + 0.08 * top + 0.05 * mdc_m)
    lower_q = clamp01(1.0 - 0.035 * (top + bottom)) if bottom else clamp01(0.55 - 0.025 * mdc_m)
    normal_strength = clamp01(0.30 + 0.28 * cavity_align + 0.22 * spectral_seed + 0.18 * top_collimation + (0.08 if route == "B" else 0.0))
    spectral_fwhm = max(4.5, 13.0 - 5.0 * spectral_seed - 2.0 * top_collimation + (1.2 if route == "B" else 0.0))
    angular_fwhm = max(8.0, 36.0 - 16.0 * top_collimation - 7.0 * spectral_seed + 5.0 * (1 - lower_q))
    peak_abs = abs(3.5 + 8.0 * (1 - cavity_align) + 3.0 * pair_asym - 2.0 * spectral_seed)
    off20_60 = clamp01(0.42 - 0.15 * top_collimation - 0.08 * spectral_seed + 0.12 * (1 - cavity_align) + 0.10 * (1 - lower_q))
    penalty30_40 = clamp01(0.30 - 0.08 * spectral_seed - 0.05 * top_collimation + 0.10 * (1 - cavity_align))
    penalty45_55 = clamp01(0.32 - 0.10 * spectral_seed - 0.06 * top_collimation + 0.14 * (1 - lower_q) + 0.08 * is_e1_like(c))
    penalty40_60 = clamp01(0.45 * penalty45_55 + 0.35 * off20_60 + 0.20 * (1 - top_collimation))
    te_tm_risk = clamp01(0.15 + 0.20 * pair_asym + 0.25 * penalty45_55 + 0.15 * abs(sio2 - 100) / 25.0 + 0.15 * abs(tio2 - 52) / 20.0)
    eta5 = clamp01(0.10 + 0.20 * normal_strength - 0.05 * peak_abs / 10.0)
    eta10 = clamp01(eta5 + 0.16 + 0.12 * normal_strength)
    eta20 = clamp01(eta10 + 0.20 + 0.10 * top_collimation)
    normal_offaxis = normal_strength / max(0.05, 0.45 * off20_60 + 0.75 * penalty45_55 + 0.40 * penalty30_40)
    d5_like = "high" if is_d5_like(c) else "low"
    e1_like = "high" if is_e1_like(c) else "low"

    fail: List[str] = []
    if spectral_fwhm > 11.0: fail.append("spectral_FWHM_proxy_gt_11nm")
    if angular_fwhm > 22.5: fail.append("angular_FWHM_proxy_gt_22p5deg")
    if peak_abs > 8.0: fail.append("peak_abs_angle_proxy_gt_8deg")
    if penalty30_40 > 0.28: fail.append("30_40_lobe_penalty_high")
    if penalty45_55 > 0.28: fail.append("45_55_lobe_penalty_high")
    if penalty40_60 > 0.34: fail.append("40_60_broad_faroffaxis_penalty_high")
    if te_tm_risk > 0.38: fail.append("TE_TM_mismatch_risk_high")
    if d5_like == "high": fail.append("D5_like_risk_high")
    if e1_like == "high": fail.append("E1_0236_like_risk_high")
    if normal_offaxis <= 1.0: fail.append("normal_offaxis_proxy_le_1")
    hard_pass = not fail
    score_v = 2.0 * normal_offaxis + 1.2 * normal_strength + 0.6 * eta20 - 0.12 * spectral_fwhm - 0.06 * angular_fwhm - 1.6 * penalty30_40 - 2.0 * penalty45_55 - 1.4 * penalty40_60 - 1.0 * te_tm_risk - 0.15 * peak_abs
    return {**c, "spectral_FWHM_proxy_nm": round(spectral_fwhm, 6), "angular_FWHM_proxy_deg": round(angular_fwhm, 6), "peak_abs_angle_proxy_deg": round(peak_abs, 6), "normal_cone_energy_proxy": round(normal_strength, 6), "eta5_proxy": round(eta5, 6), "eta10_proxy": round(eta10, 6), "eta20_proxy": round(eta20, 6), "normal_offaxis_proxy": round(normal_offaxis, 6), "offaxis_20_60_penalty": round(off20_60, 6), "offaxis_30_40_lobe_penalty": round(penalty30_40, 6), "faroffaxis_45_55_lobe_penalty": round(penalty45_55, 6), "broad_40_60_faroffaxis_penalty": round(penalty40_60, 6), "TE_TM_mismatch_risk": round(te_tm_risk, 6), "D5_like_risk_flag": d5_like, "E1_0236_like_risk_flag": e1_like, "source_position_status": "requires_tri_point_FDTD", "hard_pass": hard_pass, "hard_fail_reasons": "none" if hard_pass else ";".join(fail), "relaxed_target_score": round(score_v, 6)}


def shortlist(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    passed = [r for r in scored if r["hard_pass"]]
    passed.sort(key=lambda r: r["relaxed_target_score"], reverse=True)
    out: List[Dict[str, Any]] = []
    used_routes = set()
    for r in passed:
        if r["route"] in used_routes:
            continue
        row = dict(r)
        row["shortlist_role"] = "primary" if not out else "backup"
        row["tri_point_fdtd_entry_plan"] = "tri-point x=[-0.7,0,+0.7] um; x-dipole only; 453 nm only; pass tri-point before y-dipole; pass x/y before broadband; fail stops candidate"
        out.append(row); used_routes.add(r["route"])
        if len(out) >= 2: break
    return out


def main() -> None:
    if any(p.suffix.lower() in FORBIDDEN_SUFFIXES for p in OUT.rglob("*")):
        raise RuntimeError("Forbidden heavy file already present in F0 output")
    seeds = literature_seed_rows()
    inv = generate_candidates()
    scored = [score(c) for c in inv]
    scored.sort(key=lambda r: (r["hard_pass"], r["relaxed_target_score"]), reverse=True)
    sl = shortlist(scored)
    decision = "shortlist" if sl else "no-pass"
    write_csv(OUT / "r2_4f0_literature_seed_table.csv", seeds, ["seed_id", "route_relevance", "reported_spectral_FWHM_nm", "reported_divergence_deg", "use_in_F0", "caveat"])
    inv_fields = ["candidate_id", "route", "route_name", "top_pair_count", "bottom_pair_count", "top_termination_nm", "bottom_termination_nm", "cavity_thickness_nm", "mdc_m", "mdc_sio2_nm", "mdc_tio2_nm", "cap_thickness_nm", "target_wavelength_nm", "te_tm_angle_grid_deg"]
    write_csv(OUT / "r2_4f0_candidate_inventory.csv", inv, inv_fields)
    metric_fields = inv_fields + ["spectral_FWHM_proxy_nm", "angular_FWHM_proxy_deg", "peak_abs_angle_proxy_deg", "normal_cone_energy_proxy", "eta5_proxy", "eta10_proxy", "eta20_proxy", "normal_offaxis_proxy", "offaxis_20_60_penalty", "offaxis_30_40_lobe_penalty", "faroffaxis_45_55_lobe_penalty", "broad_40_60_faroffaxis_penalty", "TE_TM_mismatch_risk", "D5_like_risk_flag", "E1_0236_like_risk_flag", "source_position_status", "hard_pass", "hard_fail_reasons", "relaxed_target_score"]
    write_csv(OUT / "r2_4f0_proxy_scored_candidates.csv", scored, metric_fields)
    write_csv(OUT / "r2_4f0_shortlist.csv", sl, metric_fields + ["shortlist_role", "tri_point_fdtd_entry_plan"])
    config = {"stage": "R2-4F0_literature_seeded_relaxed_target_RCLED_MDC_scan", "candidate_count": len(inv), "routes": ["A_high_top_DBR_RCLED", "B_top_MDC_angular_filter", "C_hybrid_high_top_DBR_MDC_cap"], "relaxed_targets": {"spectral_FWHM_preferred_nm": 10.0, "spectral_FWHM_gate_nm": 11.0, "angular_FWHM_preferred_deg": 20.0, "angular_FWHM_gate_deg": 22.5, "peak_abs_angle_gate_deg": 8.0}, "method": "Python-only analytic proxy; not FDTD-equivalent"}
    (OUT / "r2_4f0_design_space_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    manifest = {"stage": config["stage"], "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z", "python_only": True, "no_lumerical": True, "no_lumapi": True, "no_fdtd_or_fsp_generated": True, "input_audit": input_audit(), "candidate_count": len(inv), "hard_pass_count": sum(1 for r in scored if r["hard_pass"]), "decision": decision, "shortlist_count": len(sl), "immediate_FDTD_allowed": bool(sl)}
    (OUT / "r2_4f0_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    target_md = "# R2-4F0 Relaxed Target Definition\n\n- spectral FWHM preferred <= 10 nm; FDTD-entry proxy gate <= 11 nm.\n- angular FWHM/divergence preferred <= 20 deg; FDTD-entry proxy gate <= 22.5 deg.\n- peak_abs_angle proxy <= 8 deg.\n- reject predicted dominant 30-40, 45-55, or 40-60 far-offaxis lobes.\n- source position stability remains `requires_tri_point_FDTD`; Python-only cannot prove it.\n"
    (OUT / "r2_4f0_relaxed_target_definition.md").write_text(target_md, encoding="utf-8")
    neg_md = "# R2-4F0 Negative Reference Exclusion Report\n\nExcluded: D5_BASE_13461, E1_0236, D5-like high-risk region, and E1_0236-like 6/6 260 nm 45/75 nm neighborhood. E4 no-pass candidates are not hard-picked for FDTD.\n"
    (OUT / "r2_4f0_negative_reference_exclusion_report.md").write_text(neg_md, encoding="utf-8")
    decision_md = ["# R2-4F0 No-Pass Or Shortlist Decision", "", f"Decision: **{decision}**.", "", "The shortlist is allowed only by relaxed literature-seeded proxy gates; source-position stability remains unverified until tri-point FDTD."]
    if sl:
        decision_md += ["", "## Shortlist"]
        for r in sl:
            decision_md.append(f"- {r['shortlist_role']}: {r['candidate_id']} route {r['route']} score={r['relaxed_target_score']} spectral={r['spectral_FWHM_proxy_nm']} angular={r['angular_FWHM_proxy_deg']} peak={r['peak_abs_angle_proxy_deg']}")
    else:
        decision_md += ["", "No candidate passed the relaxed F0 gate. Do not run FDTD."]
    (OUT / "r2_4f0_no_pass_or_shortlist_decision.md").write_text("\n".join(decision_md) + "\n", encoding="utf-8")
    entry = ["# R2-4F0 Tri-Point FDTD Entry Plan", "", "If and only if F0 shortlist_count > 0, first validation is:", "", "- x positions: [-0.7, 0.0, +0.7] um", "- x-dipole only", "- 453 nm only", "- pass tri-point before y-dipole", "- pass x/y before broadband", "- fail stops candidate", "- no 5-point/9-point/broadband before tri-point pass"]
    if sl:
        entry += ["", "## Candidate Plans"] + [f"- {r['candidate_id']}: {r['tri_point_fdtd_entry_plan']}" for r in sl]
    (OUT / "r2_4f0_tri_point_fdtd_entry_plan.md").write_text("\n".join(entry) + "\n", encoding="utf-8")
    summary = ["# R2-4F0 Literature-Seeded Relaxed-Target RCLED-MDC Proxy Scan", "", "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.", "", f"Generated candidates: {len(inv)}", f"Hard-pass relaxed proxy candidates: {sum(1 for r in scored if r['hard_pass'])}", f"Decision: **{decision}**", "", "F0 relaxes the target to spectral FWHM <=10 nm preferred and angular FWHM/divergence <=20 deg preferred, while retaining near-normal and far-offaxis rejection guards.", "", "## Top Candidates", "| candidate_id | route | hard_pass | score | spectral FWHM | angular FWHM | peak_abs | 30-40 | 45-55 | 40-60 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in scored[:8]:
        summary.append(f"| {r['candidate_id']} | {r['route']} | {r['hard_pass']} | {r['relaxed_target_score']} | {r['spectral_FWHM_proxy_nm']} | {r['angular_FWHM_proxy_deg']} | {r['peak_abs_angle_proxy_deg']} | {r['offaxis_30_40_lobe_penalty']} | {r['faroffaxis_45_55_lobe_penalty']} | {r['broad_40_60_faroffaxis_penalty']} |")
    (OUT / "r2_4f0_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "candidate_count": len(inv), "shortlist_count": len(sl), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
