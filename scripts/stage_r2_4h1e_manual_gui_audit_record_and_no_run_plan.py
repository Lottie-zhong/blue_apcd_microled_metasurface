from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1e_manual_gui_audit_record_and_no_run_plan"
TARGET_FSP = r"F:\wc_312\MDC_blue_oujizi.fsp"
BASELINE_STATUS = "manual_metadata_supported_primary_baseline_for_no_run_plan"


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    object_tree = [
        {"object_name": "model", "object_type": "Model", "manual_role": "root model", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "dbr", "object_type": "Structure Group", "manual_role": "MDC/DBR stack group", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "GaN", "object_type": "Rectangle", "manual_role": "GaN region", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "FDTD", "object_type": "FDTD", "manual_role": "simulation region", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "source", "object_type": "PlaneSource", "manual_role": "plane-wave source, must disable for dipole validation", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "monitor", "object_type": "DFTMonitor", "manual_role": "linear X monitor with farfield result", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "monitor_1", "object_type": "TimeMonitor", "manual_role": "time monitor", "audit_source": "manual GUI screenshot observation"},
        {"object_name": "source_1", "object_type": "DipoleSource", "manual_role": "electric dipole source for future isolated x-dipole check", "audit_source": "manual GUI screenshot observation"},
    ]
    write_csv(OUT / "r2_4h1e_manual_gui_object_tree_record.csv", object_tree, ["object_name", "object_type", "manual_role", "audit_source"])

    sources = [
        {
            "source_name": "source", "source_object_type": "PlaneSource", "source_shape_or_type": "Plane wave", "plane_wave_type": "Bloch/periodic",
            "amplitude": "1", "phase_deg": "0", "injection_axis": "y-axis", "direction": "Forward", "theta_deg": "0",
            "phi_deg": "", "polarization_angle_deg": "0", "wavelength_start_nm": "438", "wavelength_stop_nm": "468",
            "x_nm": "0", "x_span_nm": "1000", "x_min_nm": "-500", "x_max_nm": "500", "y_nm": "-800", "z_nm": "0",
            "z_span_nm": "1020", "z_min_nm": "-510", "z_max_nm": "510", "use_relative_coordinates": "checked",
            "future_action": "disable in memory before future dipole validation; do not save original FSP",
        },
        {
            "source_name": "source_1", "source_object_type": "DipoleSource", "source_shape_or_type": "Electric dipole", "plane_wave_type": "not applicable",
            "amplitude": "1", "phase_deg": "0", "injection_axis": "", "direction": "", "theta_deg": "90", "phi_deg": "0",
            "polarization_angle_deg": "", "wavelength_start_nm": "450", "wavelength_stop_nm": "450",
            "x_nm": "0", "x_span_nm": "", "x_min_nm": "", "x_max_nm": "", "y_nm": "-800", "z_nm": "0",
            "z_span_nm": "", "z_min_nm": "", "z_max_nm": "", "use_relative_coordinates": "checked",
            "future_action": "enable/isolate for future x-dipole validation planning only",
        },
    ]
    write_csv(OUT / "r2_4h1e_manual_gui_source_record.csv", sources, [
        "source_name", "source_object_type", "source_shape_or_type", "plane_wave_type", "amplitude", "phase_deg", "injection_axis",
        "direction", "theta_deg", "phi_deg", "polarization_angle_deg", "wavelength_start_nm", "wavelength_stop_nm", "x_nm", "x_span_nm",
        "x_min_nm", "x_max_nm", "y_nm", "z_nm", "z_span_nm", "z_min_nm", "z_max_nm", "use_relative_coordinates", "future_action",
    ])

    fdtd_monitor = [
        {"record_type": "FDTD", "name": "FDTD", "property": "dimension", "value": "2D", "units": "", "notes": "manual GUI observation"},
        {"record_type": "FDTD", "name": "FDTD", "property": "simulation_time", "value": "1000", "units": "fs", "notes": "manual GUI observation"},
        {"record_type": "FDTD", "name": "FDTD", "property": "simulation_temperature", "value": "300", "units": "K", "notes": "manual GUI observation"},
        {"record_type": "FDTD", "name": "FDTD", "property": "background_material", "value": "Object defined dielectric", "units": "", "notes": "background index 1.0"},
        {"record_type": "FDTD", "name": "FDTD", "property": "x_span", "value": "20000", "units": "nm", "notes": "x min -10000 nm, x max 10000 nm"},
        {"record_type": "FDTD", "name": "FDTD", "property": "y_span", "value": "2900", "units": "nm", "notes": "y=-50 nm, y min -1500 nm, y max 1400 nm"},
        {"record_type": "FDTD", "name": "FDTD", "property": "z_span", "value": "1020", "units": "nm", "notes": "z min -510 nm, z max 510 nm"},
        {"record_type": "FDTD", "name": "FDTD", "property": "mesh", "value": "auto non-uniform, accuracy 3, conformal variant 0", "units": "", "notes": "minimum mesh step 0.25 nm, dt stability factor 0.99"},
        {"record_type": "FDTD", "name": "FDTD", "property": "boundaries", "value": "x/y PML all sides", "units": "", "notes": "stretched-coordinate PML, standard profile, 8 layers"},
        {"record_type": "DFTMonitor", "name": "monitor", "property": "monitor_type", "value": "Linear X", "units": "", "notes": "manual GUI observation"},
        {"record_type": "DFTMonitor", "name": "monitor", "property": "x_span", "value": "200000", "units": "nm", "notes": "x min -100000 nm, x max 100000 nm"},
        {"record_type": "DFTMonitor", "name": "monitor", "property": "position", "value": "x=0, y=1100, z=0", "units": "nm", "notes": "relative coordinates checked"},
        {"record_type": "DFTMonitor", "name": "monitor", "property": "fields", "value": "Ex,Ey,Ez,Hx,Hy,Hz", "units": "", "notes": "output power checked; apodization None"},
        {"record_type": "DFTMonitor", "name": "monitor", "property": "existing_results", "value": "rawdata Ex/Ey 915 spectral samples; farfield result available", "units": "", "notes": "do not use existing results as validation"},
    ]
    write_csv(OUT / "r2_4h1e_manual_gui_fdtd_monitor_record.csv", fdtd_monitor, ["record_type", "name", "property", "value", "units", "notes"])

    material_layer = [
        {"record_type": "material", "name": "tio22", "material_or_layer": "TiO2-like sampled material", "property": "Re(index)", "value": "2.5356558", "units": "around 450.8516 nm", "notes": "Im(index)=0; sampled 3D data; anisotropy None; mesh order 2"},
        {"record_type": "material", "name": "sio222", "material_or_layer": "SiO2-like sampled material", "property": "Re(index)", "value": "1.4261394", "units": "around 450.8516 nm", "notes": "Im(index)=0; sampled 3D data; anisotropy None; mesh order 2"},
        {"record_type": "layer", "name": "TiO2-like rectangle", "material_or_layer": "tio22", "property": "geometry", "value": "x span 6000; y min 100; y max 152; y span 52; z span 5000", "units": "nm", "notes": "52 nm TiO2 layer matches Wan blue MDC parameter"},
        {"record_type": "layer", "name": "SiO2-like rectangle", "material_or_layer": "sio222", "property": "geometry", "value": "x span 6000; y min 1216; y max 1316; y span 100; z span 5000", "units": "nm", "notes": "100 nm SiO2 layer matches Wan blue MDC parameter"},
        {"record_type": "inference", "name": "MDC stack", "material_or_layer": "sio222/tio22", "property": "pair_count", "value": "m about 8 strongly inferred", "units": "", "notes": "1316 nm top coordinate consistent with 9*100 nm SiO2 + 8*52 nm TiO2; exact object count still not recorded"},
    ]
    write_csv(OUT / "r2_4h1e_manual_gui_material_layer_record.csv", material_layer, ["record_type", "name", "material_or_layer", "property", "value", "units", "notes"])

    summary = f"""
# R2-4H1E Manual GUI Audit Record and No-run Plan

Primary baseline target: `{TARGET_FSP}`

Baseline status: `{BASELINE_STATUS}`

Manual GUI audit confirms:
- TiO2/SiO2 MDC interpretation through custom materials `tio22` and `sio222`.
- TiO2-like layer thickness: 52 nm.
- SiO2-like layer thickness: 100 nm.
- Blue source settings are present: plane source 438-468 nm and dipole source fixed at 450 nm.
- Dipole source `source_1` is present and set as electric dipole with theta=90 deg, phi=0 deg.
- m about 8 is strongly inferred from stack geometry, but exact object count remains to be recorded if needed.

Critical risks:
- File is in ANALYSIS mode and has existing results; those results must not be used as validation.
- Both PlaneSource `source` and DipoleSource `source_1` exist. Future dipole FDTD must disable `source` and isolate `source_1` in memory.
- Do not save changes back to the original FSP.

This is not optical validation.
Immediate FDTD allowed in H1E: `false`.
"""
    write_md(OUT / "r2_4h1e_manual_gui_audit_summary.md", summary)

    decision = f"""
# R2-4H1E Baseline Freeze Decision

Baseline status: `{BASELINE_STATUS}`
Primary baseline target: `{TARGET_FSP}`

Decision:
Manual GUI metadata supports using `MDC_blue_oujizi.fsp` as the primary baseline for a future no-run simulation plan. This does not validate optical performance.

Confirmed by manual GUI audit:
- SiO2/TiO2 material system: yes (`sio222`, `tio22`).
- 100/52 nm layer evidence: yes.
- Blue wavelength evidence: yes, 438-468 nm plane source and 450 nm dipole source.
- Dipole-source presence: yes, `source_1`.
- m about 8: strongly inferred from layer geometry, exact object count not yet formally recorded.

Immediate FDTD allowed: no.
Next allowed stage: separately approved minimal no-run/dry-run planning or tri-point x-dipole validation plan after discussion.
"""
    write_md(OUT / "r2_4h1e_baseline_freeze_decision.md", decision)

    source_rules = """
# R2-4H1E Source Isolation Rules

Future dipole validation must:
- Load `F:\wc_312\MDC_blue_oujizi.fsp`.
- Switch to layout in memory only.
- Disable PlaneSource `source` in memory.
- Enable DipoleSource `source_1` in memory.
- Start with 450 nm x-dipole only.
- Avoid saving or overwriting the original FSP.
- Mark any run invalid if both plane and dipole sources are active.
- Keep y-dipole, z-dipole, and broadband disallowed until x-dipole passes.
"""
    write_md(OUT / "r2_4h1e_source_isolation_rules.md", source_rules)

    existing_note = """
# R2-4H1E Existing Results Do Not Use Note

The FSP is in ANALYSIS mode and contains existing rawdata/farfield results. These results must not be used as validation because the active source configuration is unknown. Any future result must be generated from a controlled, isolated source configuration and reported with source isolation status.
"""
    write_md(OUT / "r2_4h1e_existing_results_do_not_use_note.md", existing_note)

    plan = """
# R2-4H1E No-run Tri-point X-dipole Plan

Plan only. Do not run in H1E.

Future first validation, if separately approved:
- Candidate: `F:\wc_312\MDC_blue_oujizi.fsp`.
- Source: `source_1` only, electric x-dipole orientation theta=90 deg, phi=0 deg.
- Disable `source` PlaneSource in memory.
- Wavelength: start with 450 nm because the audited dipole source is fixed at 450 nm.
- Positions: begin with center x=0 first, then tri-point x=[-0.7, 0, +0.7] um only if source isolation is verified.
- Do not save the original FSP.
- Ignore all pre-existing analysis-mode results.

Future metrics:
- total transmitted power through monitor
- near-normal cone power if angular farfield can be extracted
- peak angle
- angular FWHM
- normal/off-axis ratio
- 40-60 deg off-axis leakage
- source isolation status
- valid/invalid flag for mixed-source risk

Disallowed until x-dipole passes:
- y-dipole
- z-dipole
- broadband validation
- 5-point or 9-point position sweep
"""
    write_md(OUT / "r2_4h1e_no_run_tri_point_xdipole_plan.md", plan)

    next_stage = """
# R2-4H1E Next Stage Recommendation

Recommended next stage: discuss and approve a minimal no-run/dry-run H1F setup plan, or a separately approved minimal x-dipole validation plan.

Do not proceed directly to FDTD from H1E. The next task should explicitly define source isolation commands, result invalidation rules, and lightweight output-only commit rules before any solve is attempted.
"""
    write_md(OUT / "r2_4h1e_next_stage_recommendation.md", next_stage)

    stop_allow = """
# R2-4H1E Stop / Allow Rules

Stop:
- Do not run FDTD in H1E.
- Do not call run, runanalysis, mesh, optimize, or sweep.
- Do not save or overwrite original FSP.
- Do not commit screenshots/images/videos or FSP/LDF/MAT/H5 files.
- Do not use existing analysis-mode results as validation.

Allow:
- Commit lightweight manual audit records and no-run planning files.
- Use H1E as baseline metadata support for future separately approved planning.
- Discuss H1F no-run/dry-run or minimal x-dipole validation plan.
"""
    write_md(OUT / "r2_4h1e_stop_allow_rules.md", stop_allow)

    manifest = {
        "stage": "R2-4H1E manual GUI audit record and no-run plan",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "python_only": True,
        "no_lumerical": True,
        "no_lumapi": True,
        "no_fdtd": True,
        "target_fsp": TARGET_FSP,
        "baseline_status": BASELINE_STATUS,
        "primary_baseline_target": TARGET_FSP,
        "manual_gui_confirms": {
            "object_tree_recorded": True,
            "plane_source_present": True,
            "dipole_source_present": True,
            "dipole_theta_phi": "theta=90 deg, phi=0 deg",
            "plane_source_wavelength_nm": "438-468",
            "dipole_wavelength_nm": "450-450",
            "fdtd_2d": True,
            "monitor_farfield_available_in_result_tree": True,
            "existing_results_do_not_use": True,
            "tio2_material_tio22": True,
            "sio2_material_sio222": True,
            "tio2_52_nm_layer": True,
            "sio2_100_nm_layer": True,
            "m_about_8_strongly_inferred": True,
            "m_exact_object_count_recorded": False,
        },
        "immediate_fdtd_allowed": False,
        "next_stage": "separately approved minimal no-run/dry-run or x-dipole validation planning only",
        "heavy_files_copied": False,
        "screenshots_committed": False,
    }
    (OUT / "r2_4h1e_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUT),
        "baseline_status": BASELINE_STATUS,
        "primary_baseline_target": TARGET_FSP,
        "immediate_fdtd_allowed": False,
        "next_stage": manifest["next_stage"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
