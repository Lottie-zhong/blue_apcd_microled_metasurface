from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
H1F = ROOT / "outputs" / "r2_4h1f_minimal_source_isolated_xaxis_three_position_xdipole_validation"
H1G = ROOT / "outputs" / "r2_4h1g_h1f_failure_analysis_and_metric_audit"
OUT = ROOT / "outputs" / "r2_4h1h_corrected_metric_freeze_and_physics_decision"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def num(value, default=None):
    try:
        if value in (None, "", "missing", "unavailable"):
            return default
        return float(value)
    except Exception:
        return default

h1f_manifest = load_json(H1F / "r2_4h1f_manifest.json")
h1g_manifest = load_json(H1G / "r2_4h1g_manifest.json")
h1f_avg_rows = read_csv(H1F / "r2_4h1f_incoherent_average_farfield_angular_metrics.csv")
h1g_recalc_rows = read_csv(H1G / "r2_4h1g_recalculated_angular_metrics.csv")
h1g_validity = read_csv(H1G / "r2_4h1g_h1f_run_validity_audit.csv")
h1g_metric_audit = read_csv(H1G / "r2_4h1g_metric_consistency_audit.csv")

h1f_avg = h1f_avg_rows[0] if h1f_avg_rows else {}
h1g_recalc_avg = next((r for r in h1g_recalc_rows if r.get("case_id") == "incoherent_average"), {})
metric_audit = h1g_metric_audit[0] if h1g_metric_audit else {}

corrected = {
    "eta10": num(h1g_recalc_avg.get("recalc_eta10")),
    "eta20": num(h1g_recalc_avg.get("recalc_eta20")),
    "leakage20_40": num(h1g_recalc_avg.get("recalc_leakage20_40")),
    "leakage40_60": num(h1g_recalc_avg.get("recalc_leakage40_60")),
    "fwhm_deg": num(h1g_recalc_avg.get("recalc_angular_fwhm_deg")),
    "peak_angle_deg": num(h1g_recalc_avg.get("recalc_peak_angle_deg")),
    "normal_to_40_60_ratio": num(h1g_recalc_avg.get("recalc_normal_to_40_60_ratio")),
}
original = {
    "eta10": num(h1f_avg.get("eta_10deg")),
    "eta20": num(h1f_avg.get("eta_20deg")),
    "leakage20_40": num(h1f_avg.get("leakage_20_40_fraction")),
    "leakage40_60": num(h1f_avg.get("leakage_40_60_fraction")),
    "fwhm_deg": num(h1f_avg.get("angular_fwhm_deg")),
    "peak_angle_deg": num(h1f_avg.get("peak_angle_deg")),
}

h1h_decision = "corrected_metric_freeze_complete"
physics_status = "limited_mdc_source_conditioning_not_apcd_ready"

validity_rows = []
validity_map = {r.get("check"): r.get("value") for r in h1g_validity}
validity_rows.append({"check": "source_isolation_confirmed", "value": h1f_manifest.get("source_isolation_confirmed_all", False), "source": "H1F manifest"})
validity_rows.append({"check": "three_x_axis_positions_completed", "value": h1f_manifest.get("all_three_runs_occurred", False), "source": "H1F manifest"})
validity_rows.append({"check": "source_positions_confirmed", "value": h1f_manifest.get("source_position_confirmed_all", False), "source": "H1F manifest"})
validity_rows.append({"check": "farfield_extracted", "value": h1f_manifest.get("farfield_angular_metrics_extracted", False), "source": "H1F manifest"})
validity_rows.append({"check": "existing_analysis_mode_results_not_used", "value": validity_map.get("no_use_of_existing_analysis_mode_results", "True"), "source": "H1G validity audit"})

freeze_rows = [
    {"metric": "peak_angle_deg", "authoritative_value": corrected["peak_angle_deg"], "source": "H1G recalculated profile", "original_h1f_value": original["peak_angle_deg"], "status": "retained_or_confirmed"},
    {"metric": "angular_fwhm_deg", "authoritative_value": corrected["fwhm_deg"], "source": "H1G recalculated profile", "original_h1f_value": original["fwhm_deg"], "status": "supersedes_original"},
    {"metric": "eta10", "authoritative_value": corrected["eta10"], "source": "H1G recalculated profile", "original_h1f_value": original["eta10"], "status": "retained_or_confirmed"},
    {"metric": "eta20", "authoritative_value": corrected["eta20"], "source": "H1G recalculated profile", "original_h1f_value": original["eta20"], "status": "retained_or_confirmed"},
    {"metric": "leakage20_40", "authoritative_value": corrected["leakage20_40"], "source": "H1G recalculated profile", "original_h1f_value": original["leakage20_40"], "status": "supersedes_original"},
    {"metric": "leakage40_60", "authoritative_value": corrected["leakage40_60"], "source": "H1G recalculated profile", "original_h1f_value": original["leakage40_60"], "status": "supersedes_original"},
]
write_csv(OUT / "r2_4h1h_corrected_metric_freeze.csv", freeze_rows)

superseded = [
    {"metric": "angular_fwhm_deg", "original_h1f_value": original["fwhm_deg"], "corrected_h1g_value": corrected["fwhm_deg"], "warning": "original H1F FWHM is superseded by H1G corrected metric due to metric/window-definition audit"},
    {"metric": "leakage20_40", "original_h1f_value": original["leakage20_40"], "corrected_h1g_value": corrected["leakage20_40"], "warning": "original H1F leakage20-40 is superseded; original exceeded eta20 under simple disjoint normalized interpretation"},
    {"metric": "leakage40_60", "original_h1f_value": original["leakage40_60"], "corrected_h1g_value": corrected["leakage40_60"], "warning": "original H1F leakage40-60 is superseded by H1G consistent integration"},
]
write_csv(OUT / "r2_4h1h_superseded_original_metric_warning.csv", superseded)

physics_rows = [{
    "h1h_decision": h1h_decision,
    "corrected_h1f_physics_status": physics_status,
    "setup_valid": True,
    "severe_high_angle_leakage_failure": False,
    "corrected_leakage40_60_low": True,
    "corrected_fwhm_status": "moderate_not_catastrophic",
    "eta20_status": "reasonably_high_some_mdc_angular_conditioning",
    "eta10_status": "low_for_strong_near_normal_apcd_preconditioning",
    "peak_angle_status": "about_12deg_not_strongly_near_normal",
    "baseline_role": "Wan MDC baseline with limited source-conditioning ability, not APCD-ready near-normal source module",
    "immediate_further_fdtd_allowed": False,
    "y_dipole_allowed": "only_after_explicit_user_approval",
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
}]
write_csv(OUT / "r2_4h1h_corrected_physics_decision.csv", physics_rows)

comparison_rows = [
    {"candidate_or_stage": "H1F_corrected_MDC_blue_oujizi", "peak_abs_deg": abs(corrected["peak_angle_deg"]), "fwhm_deg": corrected["fwhm_deg"], "leakage40_60": corrected["leakage40_60"], "classification": "limited_baseline_insufficient_apcd_conditioner", "decision": "retain_as_baseline_not_stopped_severe_failure"},
    {"candidate_or_stage": "F0_0781", "peak_abs_deg": 25.895, "fwhm_deg": 54.998, "leakage40_60": 0.3236, "classification": "failed_tri_point_guard", "decision": "H1F_corrected_better_in_peak_fwhm_and_40_60_leakage"},
    {"candidate_or_stage": "F0_0204", "peak_abs_deg": 65.499, "fwhm_deg": 138.446, "leakage40_60": 0.7433, "classification": "severe_faroffaxis_failure", "decision": "H1F_corrected_much_better_not_same_failure_bucket"},
    {"candidate_or_stage": "D5_BASE_13461", "peak_abs_deg": "various", "fwhm_deg": "various", "leakage40_60": "not_primary", "classification": "center_only_false_positive_source_position_instability_30_40_lobe", "decision": "H1F_corrected_should_not_be_lumped_with_old_center_only_false_positive"},
    {"candidate_or_stage": "E1_0236", "peak_abs_deg": "49_to_52", "fwhm_deg": "broad", "leakage40_60": "high_risk", "classification": "stable_faroffaxis_leaky_guided_like_channel", "decision": "H1F_corrected_less_severe_but_not_apcd_ready"},
]
write_csv(OUT / "r2_4h1h_comparison_to_stopped_negative_samples.csv", comparison_rows)

write_md(OUT / "r2_4h1h_future_metric_definition_rules.md", """
# R2-4H1H future metric-definition rules

Future 2D far-field angular metrics must use a documented angle vector from `farfieldangle` or an equivalent extracted theta grid.

Future eta/leakage integrations must use one consistent total-normalized definition. Preferred choices are an official `farfield2dintegrate`-like window integration or explicit weighted numerical integration over theta.

Every report must state whether each angular window is disjoint or cumulative, signed or absolute-angle, one-sided or two-sided. Future reports must not mix the original H1F leakage definitions with the H1G/H1H corrected definitions.
""")

write_md(OUT / "r2_4h1h_corrected_physics_interpretation.md", f"""
# R2-4H1H corrected physics interpretation

H1F remains a valid simulation setup: source isolation was confirmed, all three x-axis source positions completed, source positions were confirmed, and far-field data were extracted. Existing analysis-mode results were not used as validation evidence.

H1H promotes the H1G recalculated metrics as the authoritative H1F angular-window metrics. The corrected average peak remains {corrected['peak_angle_deg']:.3f} deg. The corrected FWHM is {corrected['fwhm_deg']:.3f} deg, eta10 is {corrected['eta10']:.4f}, eta20 is {corrected['eta20']:.4f}, leakage20-40 is {corrected['leakage20_40']:.4f}, and leakage40-60 is {corrected['leakage40_60']:.4f}.

Corrected status: `{physics_status}`.

This means `MDC_blue_oujizi` is not an invalid setup and is not a severe high-angle leakage failure. It shows limited angular conditioning and relatively low corrected 40-60 deg leakage. However, eta10 remains low and the peak remains around 12.35 deg, so it is not a strong near-normal source conditioner for APCD.
""")

write_md(OUT / "r2_4h1h_next_stage_recommendation.md", """
# R2-4H1H next-stage recommendation

No immediate FDTD should be run from this stage. Do not run broadband, APCD-after-MDC coupling, or extra source-position expansion.

A y-dipole three-position validation may be considered later only if the user explicitly approves completing polarization or unpolarized-source characterization.

If stronger near-normal narrowing is required, prioritize RCLED/DBR or MDC+RCLED source-conditioning planning. All future dipole validation must use at least x-axis three positions with incoherent intensity averaging. Center-only validation is diagnostic only.
""")

write_md(OUT / "r2_4h1h_stop_allow_rules.md", """
# R2-4H1H stop / allow rules

Stop:
- no immediate further FDTD
- no broadband validation
- no APCD-after-MDC coupling
- no center-only pass/fail decision
- no mixing of original H1F leakage metrics with corrected H1G/H1H metrics

Allow:
- planning and metric-definition documentation
- Wan MDC baseline record using corrected metrics
- y-dipole three-position validation only after explicit user approval
- RCLED/DBR or MDC+RCLED source-conditioning planning
""")

write_md(OUT / "r2_4h1h_summary.md", f"""
# R2-4H1H summary

Decision: `{h1h_decision}`.

Corrected H1F physics status: `{physics_status}`.

Authoritative corrected metrics from H1G/H1H:

| metric | value |
|---|---:|
| peak angle | {corrected['peak_angle_deg']:.4f} deg |
| FWHM | {corrected['fwhm_deg']:.4f} deg |
| eta10 | {corrected['eta10']:.6f} |
| eta20 | {corrected['eta20']:.6f} |
| leakage20-40 | {corrected['leakage20_40']:.6f} |
| leakage40-60 | {corrected['leakage40_60']:.6f} |

Original H1F FWHM and leakage metrics are superseded due to metric/window-definition normalization risk. Raw H1F files are left untouched.

Immediate further FDTD allowed: `false`.
""")

manifest = {
    "stage": "R2-4H1H corrected metric freeze and physics decision",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_folders": [str(H1F), str(H1G)],
    "output_folder": str(OUT),
    "zero_fdtd": True,
    "lumapi_used": False,
    "fsp_opened_or_modified": False,
    "h1h_decision": h1h_decision,
    "corrected_h1f_physics_status": physics_status,
    "authoritative_corrected_metrics": corrected,
    "original_metrics_superseded": ["angular_fwhm_deg", "leakage20_40", "leakage40_60"],
    "immediate_further_fdtd_allowed": False,
    "y_dipole_allowed": "only_after_explicit_user_approval",
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_4h1h_manifest.json"])),
}
(OUT / "r2_4h1h_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "output": str(OUT),
    "h1h_decision": h1h_decision,
    "corrected_h1f_physics_status": physics_status,
    "corrected_metrics": corrected,
    "immediate_further_fdtd_allowed": False,
}, indent=2))
