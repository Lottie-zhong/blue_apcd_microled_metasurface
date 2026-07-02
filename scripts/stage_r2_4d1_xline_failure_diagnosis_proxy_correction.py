from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "r2_4d1_xline_failure_diagnosis_proxy_correction"
REPORT = ROOT / "reports" / "rcled_mdc_workspace_index.md"

P2D = ROOT / "outputs" / "r2_2d_rcled_fdtd_smoke_solve" / "r2_2d_incoherent_average_metrics.csv"
P4B = ROOT / "outputs" / "r2_4b_normal_rcled_variable_dbr_tmm_optimize" / "r2_4b_all_candidate_metrics.csv"
P4D0_AVG = ROOT / "outputs" / "r2_4d0_variable_dbr_xline_xdipole_position_scout" / "r2_4d0_xline_xdipole_average_metrics.csv"
P4D0_ROB = ROOT / "outputs" / "r2_4d0_variable_dbr_xline_xdipole_position_scout" / "r2_4d0_source_position_robustness.csv"
P4D0_COMP = ROOT / "outputs" / "r2_4d0_variable_dbr_xline_xdipole_position_scout" / "r2_4d0_proxy_vs_fdtd_comparison.csv"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pick(table: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    return next((r for r in table if r.get(key) == value), {})


def write_csv(path: Path, data: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)


def f(row: dict[str, str], key: str) -> float | None:
    try:
        return float(row.get(key, ""))
    except ValueError:
        return None


def fmt(x: object) -> str:
    if x is None or x == "":
        return "n/a"
    if isinstance(x, float):
        return f"{x:.6g}"
    return str(x)


def md_table(data: list[dict[str, object]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for r in data:
        lines.append("| " + " | ".join(fmt(r.get(k, "")) for k in fields) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t2d = rows(P2D)
    t4b = rows(P4B)
    t4d0_avg = rows(P4D0_AVG)
    t4d0_rob = rows(P4D0_ROB)
    t4d0_comp = rows(P4D0_COMP)

    r223 = pick(t2d, "candidate_id", "R2_1_00223")
    r06361_proxy = pick(t4b, "candidate_id", "R2_4B_OPT_06361")
    r06176_proxy = pick(t4b, "candidate_id", "R2_4B_OPT_06176")
    r06361_avg = pick(t4d0_avg, "candidate_id", "R2_4B_OPT_06361")
    r06176_avg = pick(t4d0_avg, "candidate_id", "R2_4B_OPT_06176")

    negative = [
        {
            "sample_id": "R2_1_00223",
            "evidence_source": str(P2D.relative_to(ROOT)),
            "proxy_peak_abs_angle_deg": "",
            "proxy_angular_FWHM_deg": "",
            "proxy_normal_offaxis_ratio": "",
            "fdtd_peak_abs_angle_deg": r223.get("incoherent_peak_abs_angle_deg_at_453", ""),
            "fdtd_angular_FWHM_deg": r223.get("incoherent_angular_FWHM_deg_at_453", ""),
            "fdtd_normal_offaxis_ratio": r223.get("incoherent_normal_offaxis_ratio", ""),
            "failure_mode": "symmetric +/-36 deg off-axis double-lobe; diagnostic only",
            "why_old_proxy_is_fooled": "single smoke result shows a narrow directional lobe, but it is centered far off normal and normal-window power is weak",
        },
        {
            "sample_id": "R2_4B_OPT_06361",
            "evidence_source": str(P4D0_AVG.relative_to(ROOT)),
            "proxy_peak_abs_angle_deg": r06361_proxy.get("peak_angle_abs_deg_453", ""),
            "proxy_angular_FWHM_deg": r06361_proxy.get("angular_fwhm_deg_453", ""),
            "proxy_normal_offaxis_ratio": r06361_proxy.get("normal_offaxis_ratio", ""),
            "fdtd_peak_abs_angle_deg": r06361_avg.get("xline_xdipole_peak_abs_angle_deg", ""),
            "fdtd_angular_FWHM_deg": r06361_avg.get("xline_xdipole_angular_FWHM_deg", ""),
            "fdtd_normal_offaxis_ratio": r06361_avg.get("xline_xdipole_normal_offaxis_ratio", ""),
            "failure_mode": "narrow but strongly off-axis x-line x-dipole lobe near 37 deg",
            "why_old_proxy_is_fooled": "TMM proxy rewards a low plane-wave off-axis term, but FDTD dipole aperture/cavity response creates a strong 30-40 deg lobe",
        },
        {
            "sample_id": "R2_4B_OPT_06176",
            "evidence_source": str(P4D0_AVG.relative_to(ROOT)),
            "proxy_peak_abs_angle_deg": r06176_proxy.get("peak_angle_abs_deg_453", ""),
            "proxy_angular_FWHM_deg": r06176_proxy.get("angular_fwhm_deg_453", ""),
            "proxy_normal_offaxis_ratio": r06176_proxy.get("normal_offaxis_ratio", ""),
            "fdtd_peak_abs_angle_deg": r06176_avg.get("xline_xdipole_peak_abs_angle_deg", ""),
            "fdtd_angular_FWHM_deg": r06176_avg.get("xline_xdipole_angular_FWHM_deg", ""),
            "fdtd_normal_offaxis_ratio": r06176_avg.get("xline_xdipole_normal_offaxis_ratio", ""),
            "failure_mode": "near-normal-looking peak angle, but normal-window power collapses and off-axis background dominates",
            "why_old_proxy_is_fooled": "peak angle and FWHM look acceptable, but integrated normal power is too weak relative to 20-60 deg response",
        },
    ]
    write_csv(OUT / "r2_4d1_negative_sample_table.csv", negative, list(negative[0].keys()))

    contradiction = []
    for cid in ["R2_4B_OPT_06361", "R2_4B_OPT_06176"]:
        c = pick(t4d0_comp, "candidate_id", cid)
        contradiction.append({
            "candidate_id": cid,
            "proxy_peak_abs_angle_deg": c.get("proxy_peak_abs_angle_deg", ""),
            "fdtd_peak_abs_angle_deg": c.get("fdtd_xline_peak_abs_angle_deg", ""),
            "delta_peak_abs_angle_deg": (f(c, "fdtd_xline_peak_abs_angle_deg") or 0) - (f(c, "proxy_peak_abs_angle_deg") or 0),
            "proxy_angular_FWHM_deg": c.get("proxy_angular_FWHM_deg", ""),
            "fdtd_angular_FWHM_deg": c.get("fdtd_xline_angular_FWHM_deg", ""),
            "proxy_normal_offaxis_ratio": c.get("proxy_normal_offaxis_ratio", ""),
            "fdtd_normal_offaxis_ratio": c.get("fdtd_xline_normal_offaxis_ratio", ""),
            "normal_offaxis_ratio_collapse_factor": (f(c, "fdtd_xline_normal_offaxis_ratio") or 0) / (f(c, "proxy_normal_offaxis_ratio") or 1),
            "proxy_spectral_FWHM_nm": c.get("proxy_spectral_FWHM_nm", ""),
            "spectral_validation_justified": "no",
            "diagnosis": "proxy normal/offaxis is not predictive for x-line x-dipole FDTD normal/offaxis",
        })
    write_csv(OUT / "r2_4d1_proxy_vs_fdtd_contradiction.csv", contradiction, list(contradiction[0].keys()))

    source = []
    for cid in ["R2_4B_OPT_06361", "R2_4B_OPT_06176"]:
        r = pick(t4d0_rob, "candidate_id", cid)
        source.append({
            "candidate_id": cid,
            "peak_angle_mean_deg": r.get("peak_angle_mean_deg", ""),
            "peak_angle_std_deg": r.get("peak_angle_std_deg", ""),
            "peak_angle_min_deg": r.get("peak_angle_min_deg", ""),
            "peak_angle_max_deg": r.get("peak_angle_max_deg", ""),
            "normal_offaxis_ratio_min": r.get("normal_offaxis_ratio_min", ""),
            "normal_offaxis_ratio_mean": r.get("normal_offaxis_ratio_mean", ""),
            "edge_positions_degrade_normal_directionality": r.get("edge_positions_degrade_normal_directionality", ""),
            "xline_average_dominated_by_edge_offaxis_positions": r.get("xline_average_dominated_by_edge_offaxis_positions", ""),
            "xline_effect": "reveals hidden off-axis failure" if cid == "R2_4B_OPT_06361" else "reveals source-position instability and weak normal-window power",
        })
    write_csv(OUT / "r2_4d1_source_position_failure_analysis.csv", source, list(source[0].keys()))

    terms = [
        {"term": "penalize_20_60deg_response", "purpose": "suppress broad and narrow off-axis leakage beyond the old 20-30 deg window", "priority": "required"},
        {"term": "minimum_normal_window_power", "purpose": "reject candidates whose peak angle is near normal but integrated normal power is low", "priority": "required"},
        {"term": "narrow_offaxis_peak_penalty", "purpose": "catch high-Q off-axis lobes even when angular FWHM is small", "priority": "required"},
        {"term": "multi_peak_competition_penalty", "purpose": "reject competing normal and off-axis lobes", "priority": "required"},
        {"term": "30_40deg_resonance_signature_penalty", "purpose": "directly target the repeated failed lobe family", "priority": "required"},
        {"term": "top_mirror_extraction_risk_penalty", "purpose": "avoid too-low outcoupling masked by reflectance-like proxy scores", "priority": "required"},
        {"term": "xline_position_risk_surrogate", "purpose": "optional proxy for finite-aperture source-position sensitivity", "priority": "optional"},
    ]
    write_csv(OUT / "r2_4d1_corrected_proxy_terms.csv", terms, ["term", "purpose", "priority"])

    (OUT / "r2_4d1_old_proxy_failure_modes.md").write_text(
        "# R2-4D1 Old Proxy Failure Modes\n\n"
        "- R2-4B proxy normal/offaxis is not predictive for x-line x-dipole FDTD normal/offaxis.\n"
        "- Peak angle and FWHM alone are insufficient. A narrow lobe can be a bad off-axis lobe.\n"
        "- Candidates must be rejected when normal-window power collapses, even if peak_abs and FWHM look acceptable.\n"
        "- The old proxy underweighted absolute 20-60 deg response, 30-40 deg resonances, finite-aperture effects, and outcoupling risk.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d1_corrected_proxy_objective.md").write_text(
        "# R2-4D1 Corrected Proxy Objective\n\n"
        "The next optimizer should be conservative and dipole-risk-aware. Add these objective terms:\n\n"
        "1. Stronger penalty for integrated response in |theta| = 20 to 60 deg.\n"
        "2. Minimum integrated normal-window response in |theta| <= 5 deg and <= 10 deg.\n"
        "3. Explicit penalty for narrow off-axis peaks.\n"
        "4. Multi-peak competition penalty.\n"
        "5. Explicit 30 to 40 deg resonance-signature penalty.\n"
        "6. Penalty for high top-mirror extraction risk or too-low outcoupling.\n"
        "7. Optional x-line source-position risk surrogate.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d1_conservative_shortlist_rules.md").write_text(
        "# R2-4D1 Conservative Shortlist Rules\n\n"
        "Only generate setup-only FSPs when all first-pass rules are met:\n\n"
        "- proxy peak_abs_angle_deg <= 5 preferred, <= 7 maximum for the first shortlist.\n"
        "- proxy angular_FWHM_deg <= 15.\n"
        "- proxy normal/offaxis ratio is very high only because off-axis absolute response is low.\n"
        "- integrated 20 to 60 deg off-axis response is below a strict threshold.\n"
        "- normal-window integrated response exceeds a minimum threshold.\n"
        "- no strong 30 to 40 deg resonance signature.\n"
        "- shortlist includes different cavity families, not only repeats of one failure family.\n",
        encoding="utf-8",
    )
    (OUT / "r2_4d1_next_stage_recommendation.md").write_text(
        "# R2-4D1 Next Stage Recommendation\n\n"
        "Recommended: R2-4D2 corrected TMM/STACK optimization with negative-sample-informed penalties, followed by setup-only FSP generation for only 2 to 3 candidates.\n\n"
        "Do not run z_outofplane for R2_4B_OPT_06361 or R2_4B_OPT_06176 now.\n"
        "Do not run broadband spectral FWHM for failed candidates.\n"
        "Do not continue the R2-4B top5 backup blindly.\n"
        "Do not optimize only DBR reflectance or only plane-wave cavity response.\n",
        encoding="utf-8",
    )

    summary = "# R2-4D1 X-line Failure Diagnosis and Proxy Correction\n\n"
    summary += "No new FDTD, Lumerical launch, lumapi use, optimization rerun, or heavy file generation was performed.\n\n"
    summary += "## Negative Samples\n\n" + md_table(negative, ["sample_id", "fdtd_peak_abs_angle_deg", "fdtd_angular_FWHM_deg", "fdtd_normal_offaxis_ratio", "failure_mode"]) + "\n\n"
    summary += "## Proxy vs FDTD Contradiction\n\n" + md_table(contradiction, ["candidate_id", "proxy_peak_abs_angle_deg", "fdtd_peak_abs_angle_deg", "proxy_normal_offaxis_ratio", "fdtd_normal_offaxis_ratio", "normal_offaxis_ratio_collapse_factor"]) + "\n\n"
    summary += "## Source-position Diagnosis\n\n" + md_table(source, ["candidate_id", "peak_angle_mean_deg", "peak_angle_std_deg", "normal_offaxis_ratio_min", "normal_offaxis_ratio_mean", "xline_effect"]) + "\n\n"
    summary += "## Conclusion\n\nR2-4B proxy over-selected candidates because its normal/offaxis metric did not predict finite-aperture x-line x-dipole behavior. R2-4D2 should rerun the proxy optimization with explicit off-axis, normal-power, multi-peak, and extraction-risk penalties, then generate only 2 to 3 setup-only FSP candidates.\n"
    (OUT / "r2_4d1_summary.md").write_text(summary, encoding="utf-8")

    debug = {
        "stage": "R2-4D1_xline_failure_diagnosis_proxy_correction",
        "no_fdtd_run": True,
        "no_lumerical_launch": True,
        "inputs": [str(p.relative_to(ROOT)) for p in [P2D, P4B, P4D0_AVG, P4D0_ROB, P4D0_COMP]],
        "negative_samples": [r["sample_id"] for r in negative],
        "recommended_next_stage": "R2-4D2 corrected TMM/STACK optimization with negative-sample-informed penalties",
        "do_not_recommend": [
            "z_outofplane for failed R2-4B candidates now",
            "broadband spectral FWHM for failed candidates",
            "blind R2-4B top5 backup continuation",
            "reflectance-only or plane-wave-only optimization",
        ],
    }
    (OUT / "r2_4d1_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")

    marker = "## R2-4D1 x-line failure diagnosis"
    block = (
        f"\n{marker}\n"
        "- Output: `outputs/r2_4d1_xline_failure_diagnosis_proxy_correction`\n"
        "- Negative samples: R2_1_00223, R2_4B_OPT_06361, R2_4B_OPT_06176.\n"
        "- Decision: do not run z_outofplane or spectral FWHM for failed R2-4B candidates; next step is R2-4D2 corrected TMM/STACK optimization.\n"
    )
    if REPORT.exists():
        text = REPORT.read_text(encoding="utf-8")
        if marker not in text:
            REPORT.write_text(text.rstrip() + "\n" + block, encoding="utf-8")
    else:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text("# RCLED MDC Workspace Index\n" + block, encoding="utf-8")

    print("Wrote", OUT)
    print("Negative samples:", ", ".join(r["sample_id"] for r in negative))
    print("Recommendation: R2-4D2 corrected TMM/STACK optimization with negative-sample-informed penalties")


if __name__ == "__main__":
    main()
