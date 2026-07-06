from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1i_rcled_mdc_bottom_reflector_design_plan"
OUT.mkdir(parents=True, exist_ok=True)

INPUTS = {
    "H1E": ROOT / "outputs" / "r2_4h1e_manual_gui_audit_record_and_no_run_plan",
    "H1F": ROOT / "outputs" / "r2_4h1f_minimal_source_isolated_xaxis_three_position_xdipole_validation",
    "H1G": ROOT / "outputs" / "r2_4h1g_h1f_failure_analysis_and_metric_audit",
    "H1H": ROOT / "outputs" / "r2_4h1h_corrected_metric_freeze_and_physics_decision",
}


def read_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


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

h1h_manifest = read_json(INPUTS["H1H"] / "r2_4h1h_manifest.json")
corrected = h1h_manifest.get("authoritative_corrected_metrics", {})

n_tio2 = 2.5356
n_sio2 = 1.4261
lambda_nm = 450.0
t_tio2_qw = lambda_nm / (4.0 * n_tio2)
t_sio2_qw = lambda_nm / (4.0 * n_sio2)
qw_pair_nm = t_tio2_qw + t_sio2_qw
qw_10pair_nm = 10.0 * qw_pair_nm
huang_pair_nm = 50.0 + 77.0
huang_10pair_nm = 10.0 * huang_pair_nm

h1i_decision = "direction_b_rcled_mdc_bottom_reflector_plan_frozen"
primary = "DBR_QW_exact_450_10pair"
secondary = "DBR_Huang_like_10pair"

write_csv(OUT / "r2_4h1i_design_direction_record.csv", [{
    "h1i_decision": h1i_decision,
    "direction": "Direction B: RCLED-MDC source module with bottom reflector / bottom DBR",
    "inherited_baseline_fsp": r"F:\wc_312\MDC_blue_oujizi.fsp",
    "top_filter_or_output_mirror": "existing Wan MDC_blue_oujizi top MDC, unchanged",
    "bottom_reflector_strategy": "add bottom DBR below LED/source region",
    "source_settings": "preserve source_1 x electric dipole theta=90 phi=0 wavelength 450 nm",
    "validation_protocol": "x-axis three-position validation at -2500, 0, +2500 nm with incoherent intensity/power averaging",
    "center_only_allowed": False,
    "y_dipole_allowed": False,
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
    "immediate_fdtd_allowed": False,
    "derived_fsp_creation_allowed_in_h1i": False,
}])

candidate_rows = [
    {
        "candidate_name": primary,
        "role": "primary_bottom_reflector_candidate",
        "material_pair": "TiO2/SiO2",
        "tio2_thickness_nm": f"{t_tio2_qw:.3f}",
        "sio2_thickness_nm": f"{t_sio2_qw:.3f}",
        "pair_count": 10,
        "estimated_total_thickness_nm": f"{qw_10pair_nm:.3f}",
        "basis": "quarter-wave exact at 450 nm using n_TiO2=2.5356 and n_SiO2=1.4261",
        "priority": "first derived-FSP design",
    },
    {
        "candidate_name": secondary,
        "role": "secondary_comparison_candidate",
        "material_pair": "TiO2/SiO2",
        "tio2_thickness_nm": "50.000",
        "sio2_thickness_nm": "77.000",
        "pair_count": 10,
        "estimated_total_thickness_nm": f"{huang_10pair_nm:.3f}",
        "basis": "Huang-like baseline thicknesses",
        "priority": "comparison only",
    },
    {
        "candidate_name": "DBR_QW_exact_5pair",
        "role": "optional_lower_cost_exploratory",
        "material_pair": "TiO2/SiO2",
        "tio2_thickness_nm": f"{t_tio2_qw:.3f}",
        "sio2_thickness_nm": f"{t_sio2_qw:.3f}",
        "pair_count": 5,
        "estimated_total_thickness_nm": f"{5.0 * qw_pair_nm:.3f}",
        "basis": "same quarter-wave layers as primary, fewer pairs",
        "priority": "exploratory only, not primary",
    },
    {
        "candidate_name": "DBR_Huang_like_5pair",
        "role": "optional_lower_cost_exploratory",
        "material_pair": "TiO2/SiO2",
        "tio2_thickness_nm": "50.000",
        "sio2_thickness_nm": "77.000",
        "pair_count": 5,
        "estimated_total_thickness_nm": f"{5.0 * huang_pair_nm:.3f}",
        "basis": "same Huang-like layers as secondary, fewer pairs",
        "priority": "exploratory only, not primary",
    },
]
write_csv(OUT / "r2_4h1i_bottom_reflector_candidate_table.csv", candidate_rows)

write_csv(OUT / "r2_4h1i_quarter_wave_thickness_calculation.csv", [
    {"material": "TiO2/tio22", "index_at_450nm": n_tio2, "formula": "450/(4*n)", "quarter_wave_thickness_nm": f"{t_tio2_qw:.6f}"},
    {"material": "SiO2/sio222", "index_at_450nm": n_sio2, "formula": "450/(4*n)", "quarter_wave_thickness_nm": f"{t_sio2_qw:.6f}"},
    {"material": "TiO2+SiO2 pair", "index_at_450nm": "mixed", "formula": "t_TiO2+t_SiO2", "quarter_wave_thickness_nm": f"{qw_pair_nm:.6f}"},
    {"material": "10 pairs", "index_at_450nm": "mixed", "formula": "10*(t_TiO2+t_SiO2)", "quarter_wave_thickness_nm": f"{qw_10pair_nm:.6f}"},
])

geometry_rows = [
    {"item": "top_mdc", "planned_value": "preserve existing MDC_blue_oujizi top structure unchanged", "rationale": "Wan MDC baseline already provides limited source conditioning and blue filtering", "status": "frozen_for_first_bottom_DBR_plan"},
    {"item": "existing_top_mdc_materials", "planned_value": "tio22 / sio222; TiO2-like 52 nm, SiO2-like 100 nm, m about 8 inferred", "rationale": "manual GUI audit H1E", "status": "inherited"},
    {"item": "source_1", "planned_value": "electric dipole theta=90 deg phi=0 deg, 450 nm, x positions -2500/0/+2500 nm", "rationale": "preserve previous LED/source settings and x-only validation", "status": "inherited"},
    {"item": "plane_source", "planned_value": "disable PlaneSource named source for dipole validation", "rationale": "source-isolated dipole validation only", "status": "required_future_derived_FSP_rule"},
    {"item": "bottom_DBR_location", "planned_value": "place below LED/source region on negative-y side", "rationale": "create RCLED-MDC cavity using top MDC as output mirror", "status": "planned_not_created"},
    {"item": "source_bottom_DBR_overlap", "planned_value": "do not overlap source_1 at y=-800 nm", "rationale": "source must remain between bottom DBR and top MDC", "status": "hard_constraint"},
    {"item": "estimated_primary_bottom_DBR_thickness_nm", "planned_value": f"{qw_10pair_nm:.3f}", "rationale": "10*(44.4+78.9) nm approximately", "status": "requires_ymin_expansion"},
    {"item": "fdtd_y_span", "planned_value": "expand y-min downward in future derived FSP", "rationale": "current y-min about -1500 nm is likely insufficient for 10-pair bottom DBR plus PML margin", "status": "future_H1J_geometry_audit"},
    {"item": "cavity_length", "planned_value": "do not finalize in H1I", "rationale": "cavity spacing must be audited before any FDTD", "status": "follow_up_variable_not_sweep"},
]
write_csv(OUT / "r2_4h1i_rcled_mdc_geometry_plan.csv", geometry_rows)

write_md(OUT / "r2_4h1i_future_derived_fsp_construction_spec.md", f"""
# R2-4H1I future derived-FSP construction specification

H1I is planning only. It does not open, modify, copy, or save any `.fsp` file.

Future H1J/H1K derived FSP construction should start from `F:\\wc_312\\MDC_blue_oujizi.fsp`, keep the existing top MDC unchanged, disable PlaneSource `source`, and keep DipoleSource `source_1` as the x-oriented electric dipole with theta=90 deg, phi=0 deg, wavelength 450 nm.

The first derived design should add a bottom DBR under the LED/source region on the negative-y side. The primary bottom reflector is `{primary}` using TiO2 {t_tio2_qw:.3f} nm / SiO2 {t_sio2_qw:.3f} nm for 10 pairs. The estimated DBR thickness is {qw_10pair_nm:.1f} nm. A secondary comparison is `{secondary}` using TiO2 50 nm / SiO2 77 nm for 10 pairs.

The source must remain between the bottom DBR and top MDC. The bottom DBR must not overlap source_1 at y=-800 nm. Because the 10-pair DBR is about 1.2-1.3 um thick, the FDTD y-min boundary will likely need to move downward with a PML safety margin.

Cavity length is not finalized in H1I. It should be recorded as a follow-up geometry variable after a no-run H1J geometry audit.
""")

write_md(OUT / "r2_4h1i_source_validation_protocol_x_only.md", """
# R2-4H1I x-only source validation protocol

Current stage uses x-polarized 2D validation only. Do not run y-dipole or broadband in H1I.

Future FDTD validation must use at least three x-axis positions: -2500 nm, 0 nm, and +2500 nm. The final decision must use incoherent intensity/power averaging over these positions. Center-only validation is diagnostic only and must never be used as pass/fail evidence.

PlaneSource `source` must be disabled. DipoleSource `source_1` must be enabled and configured as electric x-dipole with theta=90 deg and phi=0 deg at 450 nm.
""")

write_md(OUT / "r2_4h1i_lumerical_official_command_notes.md", """
# R2-4H1I Lumerical command notes for future H1J/H1K

H1I does not execute Lumerical or lumapi.

Future FSP modification scripts should follow the official command behavior assumed in the project workflow:

- use `layoutmode` to check whether the loaded file is in LAYOUT or ANALYSIS mode;
- call `switchtolayout` before modifying objects;
- use `getnamed`/`setnamed` for named-object property reads and writes;
- call `run` only in explicitly approved FDTD stages;
- never use existing analysis-mode results as validation evidence.

These notes are construction constraints for future approved scripts, not actions taken in H1I.
""")

write_md(OUT / "r2_4h1i_risk_register.md", f"""
# R2-4H1I risk register

| risk | impact | mitigation |
|---|---|---|
| Bottom DBR overlaps source or existing GaN/source region | invalid RCLED geometry | H1J must do no-run geometry audit before any solve |
| Existing y-span too small for ~{qw_10pair_nm:.0f} nm bottom DBR plus PML margin | PML/structure overlap or bad boundary behavior | expand y-min downward in derived FSP construction |
| Cavity length not tuned | bottom DBR can worsen angular emission | keep cavity length as follow-up variable, not a H1I sweep |
| Source validation center-only temptation | false positive risk | enforce three-position x-axis incoherent average |
| y-polarization unknown | incomplete unpolarized source evidence | defer y-dipole until structure is frozen and user explicitly approves |
| Existing top MDC filtering may not combine constructively with bottom DBR | RCLED-MDC may not improve near-normal emission | require future three-position FDTD validation before physics claims |
""")

write_md(OUT / "r2_4h1i_next_stage_recommendation.md", """
# R2-4H1I next-stage recommendation

Next allowed stage is planning or no-run derived-FSP construction planning only.

Recommended next task: `R2-4H1J no-run derived-FSP construction script planning and geometry audit`.

A future H1J may create a derived runtime FSP only after explicit user approval. H1I itself does not allow derived FSP creation and does not allow immediate FDTD.
""")

write_md(OUT / "r2_4h1i_stop_allow_rules.md", """
# R2-4H1I stop / allow rules

Stop:
- no FDTD
- no lumapi
- no FSP open/modify/copy/save
- no y-dipole
- no broadband
- no APCD coupling
- no sweep or optimization
- no center-only validation

Allow:
- lightweight planning files only
- bottom DBR candidate specification
- future derived-FSP construction plan
- future H1J no-run geometry audit after explicit approval
""")

write_md(OUT / "r2_4h1i_summary.md", f"""
# R2-4H1I summary

Decision: `{h1i_decision}`.

Direction B is frozen as the next planning route: build an RCLED-MDC source module by adding a bottom reflector / bottom DBR below the existing Wan MDC baseline, while using the existing MDC as the top filtering/output mirror.

Primary bottom reflector candidate: `{primary}`.

Secondary bottom reflector candidate: `{secondary}`.

Quarter-wave exact 450 nm layer thicknesses:

| material | n at 450 nm | thickness |
|---|---:|---:|
| TiO2/tio22 | {n_tio2:.4f} | {t_tio2_qw:.3f} nm |
| SiO2/sio222 | {n_sio2:.4f} | {t_sio2_qw:.3f} nm |

H1I does not create a derived FSP and does not allow immediate FDTD. It preserves x-only three-position validation and defers y-dipole and broadband validation.
""")

manifest = {
    "stage": "R2-4H1I RCLED-MDC bottom reflector design plan",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "input_folders": {k: str(v) for k, v in INPUTS.items()},
    "h1i_decision": h1i_decision,
    "primary_bottom_reflector_candidate": primary,
    "secondary_bottom_reflector_candidate": secondary,
    "quarter_wave_thickness_nm": {
        "TiO2": t_tio2_qw,
        "SiO2": t_sio2_qw,
        "pair": qw_pair_nm,
        "ten_pair_total": qw_10pair_nm,
    },
    "inherited_h1h_corrected_metrics": corrected,
    "zero_fdtd": True,
    "lumapi_used": False,
    "fsp_opened_or_modified": False,
    "derived_fsp_creation_allowed_in_h1i": False,
    "immediate_fdtd_allowed": False,
    "y_dipole_allowed": False,
    "broadband_allowed": False,
    "apcd_coupling_allowed": False,
    "next_allowed_stage": "H1J no-run derived-FSP construction script planning or derived runtime FSP creation only after explicit user approval",
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_4h1i_manifest.json"])),
}
(OUT / "r2_4h1i_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "output": str(OUT),
    "h1i_decision": h1i_decision,
    "primary": primary,
    "secondary": secondary,
    "tio2_qw_nm": t_tio2_qw,
    "sio2_qw_nm": t_sio2_qw,
    "immediate_fdtd_allowed": False,
    "derived_fsp_creation_allowed_in_h1i": False,
}, indent=2))
