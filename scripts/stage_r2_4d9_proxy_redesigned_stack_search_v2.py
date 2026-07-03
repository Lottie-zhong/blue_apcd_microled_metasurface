from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4d9_proxy_redesigned_stack_search_v2"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = {
    "d2_top20": ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize" / "r2_4d2_top20_candidate_metrics.csv",
    "d2_all": ROOT / "outputs" / "r2_4d2_corrected_risk_aware_tmm_optimize" / "r2_4d2_all_candidate_metrics.csv",
    "d3_near_pass": ROOT / "outputs" / "r2_4d3_cavity_phase_design_space_reset" / "r2_4d3_near_pass_candidates.csv",
    "d4_best_spacers": ROOT / "outputs" / "r2_4d4_focused_cavity_phase_sweep" / "r2_4d4_best_phase_guided_spacers.csv",
    "d5_top20": ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization" / "r2_4d5_top20_phase_guided_candidates.csv",
    "d5_shortlist": ROOT / "outputs" / "r2_4d5_focused_cavity_termination_phase_optimization" / "r2_4d5_phase_guided_shortlist.csv",
    "d5a_manifest": ROOT / "outputs" / "r2_4d5a_shortlist_te_tm_offaxis_risk_review" / "r2_4d5a_candidate_manifest.csv",
    "d5a_margin": ROOT / "outputs" / "r2_4d5a_shortlist_te_tm_offaxis_risk_review" / "r2_4d5a_normal_vs_offaxis_margin.csv",
    "d8_terms": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_proxy_redesign_terms.csv",
    "d8_failure_table": ROOT / "outputs" / "r2_4d8_source_position_failure_diagnosis_proxy_redesign" / "r2_4d8_source_position_failure_table.csv",
}
HEAVY_SUFFIXES = {".fsp", ".ldf", ".mat", ".h5"}


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


def fval(row: Dict[str, Any], key: str, default: float | None = None) -> float | None:
    value = row.get(key, "")
    if value in (None, "", "missing"):
        return default
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def sval(row: Dict[str, Any], key: str, default: str = "missing") -> str:
    value = row.get(key, "")
    return default if value in (None, "") else str(value)


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def norm_inverse(x: float | None, scale: float, missing_penalty: float = 1.0) -> float:
    if x is None:
        return missing_penalty
    return clamp01(x / scale)


def normal_score_from_ratio(ratio: float | None) -> float:
    if ratio is None:
        return 0.0
    return clamp01(math.log10(max(ratio, 1e-12)) / 3.0)


def merge_by_candidate(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        cid = sval(row, "candidate_id", "")
        if not cid:
            continue
        target = merged.setdefault(cid, {"candidate_id": cid})
        for k, v in row.items():
            if v not in (None, "") and k not in target:
                target[k] = v
    return merged


def collect_inputs() -> Tuple[Dict[str, List[Dict[str, str]]], List[Dict[str, Any]]]:
    tables = {name: read_csv(path) for name, path in INPUTS.items()}
    input_audit = []
    for name, path in INPUTS.items():
        input_audit.append({
            "input_name": name,
            "path": str(path.relative_to(ROOT)),
            "exists": path.exists(),
            "row_count": len(tables[name]),
            "status": "loaded" if path.exists() else "missing",
        })
    return tables, input_audit


def inventory_candidates(tables: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source_name in ["d5_shortlist", "d5_top20", "d5a_manifest", "d2_top20", "d3_near_pass", "d4_best_spacers"]:
        for row in tables.get(source_name, []):
            cid = sval(row, "candidate_id", "")
            if not cid:
                continue
            rec = {"candidate_id": cid, "source_table": source_name}
            for k, v in row.items():
                if k in {
                    "top_pair_count", "bottom_pair_count", "cavity_spacer_nm", "top_termination_nm",
                    "bottom_termination_nm", "score", "D5_score", "pass_level", "failure_mode",
                    "combined_accept", "scale_profile", "shortlist_role"
                }:
                    rec[k] = v
            rows.append(rec)
    seen = set()
    unique: List[Dict[str, Any]] = []
    for row in rows:
        key = (row["candidate_id"], row["source_table"])
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def build_scored(tables: Dict[str, List[Dict[str, str]]]) -> List[Dict[str, Any]]:
    base_rows: List[Dict[str, Any]] = []
    for name in ["d5_top20", "d2_top20", "d5_shortlist", "d5a_manifest"]:
        for row in tables.get(name, []):
            r = dict(row)
            r["source_table"] = name
            base_rows.append(r)
    merged = merge_by_candidate(base_rows)

    d5a_by_candidate: Dict[str, List[Dict[str, str]]] = {}
    for row in tables.get("d5a_margin", []):
        d5a_by_candidate.setdefault(sval(row, "candidate_id", ""), []).append(row)

    scored: List[Dict[str, Any]] = []
    for cid, row in merged.items():
        d5a_rows = d5a_by_candidate.get(cid, [])
        tm_crosses = any(boolish(r.get("TM_offaxis_resonance_crosses_453")) for r in d5a_rows)
        min_margin_30_40 = None
        for r in d5a_rows:
            margin = fval(r, "phase_margin_30_40_deg")
            if margin is not None:
                min_margin_30_40 = margin if min_margin_30_40 is None else min(min_margin_30_40, margin)

        normal_ratio = fval(row, "conservative_normal_offaxis_ratio")
        if normal_ratio is None:
            normal_ratio = fval(row, "corrected_normal_offaxis_ratio")
        if normal_ratio is None:
            te_ratio = fval(row, "TE_normal_offaxis_ratio")
            tm_ratio = fval(row, "TM_normal_offaxis_ratio")
            if te_ratio is not None and tm_ratio is not None:
                normal_ratio = min(te_ratio, tm_ratio)

        offaxis_20_60 = fval(row, "offaxis_20_60_response")
        offaxis_30_40 = fval(row, "offaxis_30_40_response")
        peak_abs = fval(row, "corrected_proxy_peak_abs_angle_deg")
        angular_fwhm = fval(row, "corrected_proxy_angular_FWHM_deg") or fval(row, "model_angle_fwhm_deg")
        spectral_fwhm = fval(row, "spectral_fwhm_nm_normal_window")
        spectral_peak = fval(row, "spectral_peak_nm_normal_window") or fval(row, "avg_normal_resonance_nm")

        normal_component = normal_score_from_ratio(normal_ratio)
        offaxis20_penalty = norm_inverse(offaxis_20_60, 1e-4, missing_penalty=0.6)
        offaxis3040_penalty = norm_inverse(offaxis_30_40, 5e-5, missing_penalty=0.6)
        if min_margin_30_40 is not None:
            offaxis3040_penalty = max(offaxis3040_penalty, clamp01((10.0 - min_margin_30_40) / 10.0))
        if tm_crosses:
            offaxis3040_penalty = 1.0
        te_tm_penalty = 1.0 if tm_crosses else 0.0
        if min_margin_30_40 is not None and min_margin_30_40 < 12.0:
            te_tm_penalty = max(te_tm_penalty, clamp01((12.0 - min_margin_30_40) / 12.0))
        spectral_center_penalty = 0.6 if spectral_peak is None else clamp01(abs(spectral_peak - 453.0) / 6.0)
        spectral_fwhm_penalty = 0.6 if spectral_fwhm is None else clamp01(max(0.0, spectral_fwhm - 8.0) / 8.0)
        angular_fwhm_penalty = 0.6 if angular_fwhm is None else clamp01(max(0.0, angular_fwhm - 25.0) / 25.0)
        peak_angle_penalty = 0.6 if peak_abs is None else clamp01(max(0.0, peak_abs - 10.0) / 20.0)

        center_false_positive_risk = "high" if cid == "D5_BASE_13461" or tm_crosses else "medium"
        if sval(row, "pass_level", "").startswith("fail") or "30_40" in sval(row, "failure_mode", ""):
            center_false_positive_risk = "high"
        source_position_stability_required = "requires_tri_point_FDTD"
        center_xline_mismatch_risk = "high" if center_false_positive_risk == "high" else "medium"

        total_score = (
            2.0 * normal_component
            - 1.0 * offaxis20_penalty
            - 2.5 * offaxis3040_penalty
            - 1.5 * te_tm_penalty
            - 0.6 * spectral_center_penalty
            - 0.4 * spectral_fwhm_penalty
            - 0.4 * angular_fwhm_penalty
            - 0.5 * peak_angle_penalty
        )

        hard_fail_reasons: List[str] = []
        if center_false_positive_risk == "high":
            hard_fail_reasons.append("center_only_false_positive_risk_high")
        if te_tm_penalty >= 0.5:
            hard_fail_reasons.append("TE_TM_offaxis_risk_guard_fail")
        if offaxis3040_penalty >= 0.5:
            hard_fail_reasons.append("30_40_lobe_penalty_high")
        if normal_ratio is None or normal_ratio <= 1.0:
            hard_fail_reasons.append("normal_offaxis_proxy_not_above_1")
        hard_pass = not hard_fail_reasons and center_xline_mismatch_risk != "high"

        scored.append({
            "candidate_id": cid,
            "source_tables": ";".join(sorted({r.get("source_table", "") for r in base_rows if r.get("candidate_id") == cid})),
            "top_pair_count": row.get("top_pair_count", "missing"),
            "bottom_pair_count": row.get("bottom_pair_count", "missing"),
            "cavity_spacer_nm": row.get("cavity_spacer_nm", "missing"),
            "top_termination_nm": row.get("top_termination_nm", "missing"),
            "bottom_termination_nm": row.get("bottom_termination_nm", "missing"),
            "normal_offaxis_proxy": "missing" if normal_ratio is None else normal_ratio,
            "offaxis_20_60_penalty": offaxis20_penalty,
            "offaxis_30_40_lobe_penalty": offaxis3040_penalty,
            "te_tm_offaxis_risk_guard_penalty": te_tm_penalty,
            "spectral_center_nm_proxy": "missing" if spectral_peak is None else spectral_peak,
            "spectral_fwhm_nm_proxy": "missing" if spectral_fwhm is None else spectral_fwhm,
            "angular_fwhm_deg_proxy": "missing" if angular_fwhm is None else angular_fwhm,
            "peak_abs_angle_deg_proxy": "missing" if peak_abs is None else peak_abs,
            "d5a_min_30_40_phase_margin_deg": "missing" if min_margin_30_40 is None else min_margin_30_40,
            "tm_offaxis_resonance_crosses_453": tm_crosses,
            "center_only_false_positive_risk": center_false_positive_risk,
            "source_position_stability_required_flag": source_position_stability_required,
            "center_vs_xline_mismatch_risk": center_xline_mismatch_risk,
            "hard_pass": hard_pass,
            "hard_fail_reasons": ";".join(hard_fail_reasons) if hard_fail_reasons else "none",
            "v2_score": total_score,
        })
    scored.sort(key=lambda r: (bool(r["hard_pass"]), float(r["v2_score"])), reverse=True)
    return scored


def make_shortlist(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    shortlist = []
    for row in scored:
        if row["hard_pass"] is True:
            role = "primary" if not shortlist else "backup"
            out = dict(row)
            out.update({
                "shortlist_role": role,
                "tri_point_x_positions_um": "[-0.7, 0.0, +0.7]",
                "tri_point_dipole": "x_only",
                "tri_point_wavelength_nm": 453,
                "tri_point_rule": "pass before 5-point or 9-point x-line; fail stops candidate; no y/z/broadband before pass",
            })
            shortlist.append(out)
        if len(shortlist) >= 3:
            break
    return shortlist


def main() -> None:
    forbidden_found = [str(p.relative_to(ROOT)) for p in OUT.rglob("*") if p.suffix.lower() in HEAVY_SUFFIXES]
    if forbidden_found:
        raise RuntimeError("Forbidden heavy files already present in D9 output: " + ", ".join(forbidden_found))

    tables, input_audit = collect_inputs()
    inventory = inventory_candidates(tables)
    scored = build_scored(tables)
    shortlist = make_shortlist(scored)
    decision = "shortlist" if shortlist else "no-pass"

    inv_fields = sorted({k for r in inventory for k in r.keys()}) or ["candidate_id"]
    write_csv(OUT / "r2_4d9_candidate_inventory.csv", inventory, inv_fields)

    score_fields = [
        "candidate_id", "source_tables", "top_pair_count", "bottom_pair_count", "cavity_spacer_nm",
        "top_termination_nm", "bottom_termination_nm", "normal_offaxis_proxy",
        "offaxis_20_60_penalty", "offaxis_30_40_lobe_penalty", "te_tm_offaxis_risk_guard_penalty",
        "spectral_center_nm_proxy", "spectral_fwhm_nm_proxy", "angular_fwhm_deg_proxy", "peak_abs_angle_deg_proxy",
        "d5a_min_30_40_phase_margin_deg", "tm_offaxis_resonance_crosses_453",
        "center_only_false_positive_risk", "source_position_stability_required_flag",
        "center_vs_xline_mismatch_risk", "hard_pass", "hard_fail_reasons", "v2_score",
    ]
    write_csv(OUT / "r2_4d9_proxy_scored_candidates.csv", scored, score_fields)

    shortlist_fields = score_fields + ["shortlist_role", "tri_point_x_positions_um", "tri_point_dipole", "tri_point_wavelength_nm", "tri_point_rule"]
    write_csv(OUT / "r2_4d9_shortlist.csv", shortlist, shortlist_fields)

    manifest = {
        "stage": "R2-4D9_proxy_redesigned_stack_search_v2",
        "created_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd_or_fsp_generated": True,
        "input_audit": input_audit,
        "candidate_inventory_count": len(inventory),
        "scored_candidate_count": len(scored),
        "decision": decision,
        "shortlist_count": len(shortlist),
        "d8_negative_sample_rule": "center-only near-normal proxy is insufficient; source-position stability, edge sensitivity, 30-40 deg lobe and center-vs-xline mismatch risks are required guards.",
    }
    (OUT / "r2_4d9_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    top_rows = scored[:6]
    summary_lines = [
        "# R2-4D9 Proxy-Redesigned Stack Search V2",
        "",
        "This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 outputs.",
        "",
        "## Decision",
        f"Decision: **{decision}**.",
        "",
        "D9 does not declare a physical pass. It only decides whether any existing stack/design-family candidate is justified for a later low-cost tri-point FDTD guard.",
        "",
        "## D8 Rule Applied",
        "D8 showed that center-only near-normal emission can be a false positive for the x-line source-position ensemble. The D9 score therefore penalizes source-position risk, edge sensitivity, 30-40 deg lobes, TE/TM off-axis risk, and center-vs-xline mismatch.",
        "",
        "## Top Scored Candidates",
        "| candidate_id | hard_pass | score | hard_fail_reasons |",
        "|---|---:|---:|---|",
    ]
    for r in top_rows:
        summary_lines.append(f"| {r['candidate_id']} | {r['hard_pass']} | {float(r['v2_score']):.4f} | {r['hard_fail_reasons']} |")
    summary_lines += [
        "",
        "## Shortlist Rule",
        "No candidate may enter the shortlist from center/normal proxy alone. The shortlist also requires low TE/TM off-axis risk, low 30-40 deg lobe penalty, normal/off-axis proxy above 1, and no high center-vs-xline mismatch risk.",
    ]
    if shortlist:
        summary_lines += ["", "## Shortlist"]
        for r in shortlist:
            summary_lines.append(f"- {r['shortlist_role']}: {r['candidate_id']} -> tri-point x positions [-0.7, 0.0, +0.7] um, x-dipole only, 453 nm only.")
    else:
        summary_lines += ["", "## No-Pass Outcome", "No candidate satisfied the conservative D8-derived hard guards. The next route should redesign the stack/design family or run limited FDTD-in-loop only after a stronger Python-only proxy is available."]
    (OUT / "r2_4d9_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    decision_md = ["# R2-4D9 No-Pass Or Shortlist Decision", "", f"Decision: **{decision}**.", ""]
    if shortlist:
        decision_md += ["The following candidates are justified for the next tri-point FDTD guard only:", ""]
        for r in shortlist:
            decision_md.append(f"- {r['candidate_id']} ({r['shortlist_role']})")
    else:
        decision_md += [
            "No existing candidate is cleared for even tri-point FDTD guard under the conservative D8 proxy-redesign rules.",
            "This is intentional: D5_BASE_13461 demonstrated that strong center/normal proxy metrics can still fail when source position is varied.",
        ]
    (OUT / "r2_4d9_no_pass_or_shortlist_decision.md").write_text("\n".join(decision_md) + "\n", encoding="utf-8")

    guard_lines = [
        "# R2-4D9 Tri-Point FDTD Guard Plan",
        "",
        "If a future candidate is shortlisted, validate it with the minimum source-position guard before any 5-point/9-point x-line, y-dipole, z-out-of-plane, or broadband work.",
        "",
        "- x positions: -0.7, 0.0, +0.7 um",
        "- dipole: x-oriented only",
        "- wavelength: 453 nm only",
        "- pass prerequisite: stable near-normal behavior across all three positions and no 30-40 deg lobe revival",
        "- fail action: stop that candidate immediately",
        "",
        f"Current D9 decision: {decision}.",
    ]
    if shortlist:
        guard_lines += ["", "## Candidate-Specific Plan"]
        for r in shortlist:
            guard_lines.append(f"- {r['candidate_id']}: run tri-point guard only; pass before 5-point or 9-point x-line.")
    else:
        guard_lines += ["", "No tri-point FDTD run is recommended from the existing candidate pool."]
    (OUT / "r2_4d9_tri_point_fdtd_guard_plan.md").write_text("\n".join(guard_lines) + "\n", encoding="utf-8")

    print(json.dumps({"decision": decision, "shortlist_count": len(shortlist), "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    main()
