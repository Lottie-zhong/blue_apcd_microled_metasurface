from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1k4_manual_gui_audit_record_h1j4"
SCRIPT = ROOT / "scripts" / "stage_r2_4h1k4_manual_gui_audit_record_h1j4.py"
H1J4_DIR = ROOT / "outputs" / "r2_4h1j4_fmm2b0_integer_dbr_and_lumerical_rcwa_audit_no_run"
H1K_DIR = ROOT / "outputs" / "r2_4h1k_fmm2a2_joint_gui_audit_and_fmm_env_plan"
FMM2A_DIR = ROOT / "outputs" / "r2_fmm2a_solver_inventory_and_validation_protocol"
H1H_DIR = ROOT / "outputs" / "r2_4h1h_corrected_metric_freeze_and_physics_decision"
H1J4_FSP = ROOT / "runtime" / "r2_4h1j4_rcled_mdc_integer_dbr_derived_fsp_DO_NOT_COMMIT" / "MDC_blue_oujizi_RCLED_QWinteger453_10pair_H1J4.fsp"
H1J3_FSP = ROOT / "runtime" / "r2_4h1j3_rcled_mdc_corrected_derived_fsp_DO_NOT_COMMIT" / "MDC_blue_oujizi_RCLED_QWexact453_10pair_H1J3.fsp"

GUI_ITEMS = [
    ("bottom_dbr_group_exists", "H1J4_bottom_DBR_QWinteger453_10pair group exists"),
    ("bottom_dbr_group_layer_count", "group contains 20 layers"),
    ("bottom_dbr_layer_order", "TiO2 then SiO2 repeated 10 times"),
    ("tio2_thickness", "TiO2 layers are 45 nm"),
    ("sio2_thickness", "SiO2 layers are 79 nm"),
    ("bottom_dbr_y_range", "bottom DBR y range is about -2190 nm to -950 nm"),
    ("mesh_order", "all bottom DBR layers have mesh order 1 and DBR-over-GaN priority appears correct"),
    ("source_position", "source_1 is x=0 nm, y=-800 nm, z=0 nm"),
    ("source_wavelength", "source_1 wavelength is 453 nm"),
    ("source_orientation", "source_1 x-dipole theta=90 deg, phi=0 deg"),
    ("source_enabled", "source_1 enabled=true"),
    ("planesource_disabled", "PlaneSource source disabled=true"),
    ("fdtd_y_range", "FDTD y range is about -2800 to +1400 nm"),
    ("monitor_position", "monitor y about 1100 nm on output side of top MDC"),
    ("monitor_not_in_stack", "monitor is not inside TiO2/SiO2 layer stack"),
    ("monitor_pml_spacing", "monitor spacing from upper PML is reasonable"),
    ("farfield_projection", "projection direction = auto"),
    ("farfield_material_index", "material index = auto"),
    ("farfield_filter", "far field filter = 1"),
    ("farfield_2d_resolution", "2D resolution = 1001"),
    ("farfield_3d_resolution", "3D resolution = 1001"),
    ("farfield_periodic", "Assume structure is periodic unchecked"),
    ("farfield_near_mesh", "override near field mesh unchecked"),
    ("no_simulation", "no simulation was run during GUI inspection"),
    ("not_overwritten", "derived FSP was not accidentally overwritten after inspection"),
]


def sh(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": str(exc), "path": str(path)}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}; current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    h1j4 = read_json(H1J4_DIR / "r2_4h1j4_fmm2b0_manifest.json")
    fsp_exists = H1J4_FSP.exists()
    fsp_stat = H1J4_FSP.stat() if fsp_exists else None
    h1k4_gui_decision = "h1j4_manual_gui_audit_passed_simulation_planning_allowed"

    write_csv(OUT / "r2_4h1k4_manual_gui_audit_record.csv", [{
        "stage": "R2-4H1K4",
        "audit_source": "user_manual_gui_report_in_codex_request",
        "audit_recorded_at": datetime.now().isoformat(timespec="seconds"),
        "h1k4_gui_decision": h1k4_gui_decision,
        "preferred_runtime_fsp": str(H1J4_FSP),
        "h1j4_derived_fsp_exists_by_filesystem_stat": fsp_exists,
        "h1j4_derived_fsp_size_bytes": fsp_stat.st_size if fsp_stat else "missing",
        "h1j4_simulation_template_status": "gui_audited_preferred_template",
        "immediate_FDTD_allowed_in_H1K4": "no",
        "immediate_RCWA_allowed_in_H1K4": "no",
        "y_dipole_allowed": "no",
        "broadband_allowed": "no",
        "APCD_coupling_allowed": "no",
    }])

    write_csv(OUT / "r2_4h1k4_confirmed_gui_items.csv", [
        {"item_id": item_id, "confirmed": True, "confirmation_source": "user_manual_gui_report", "description": desc}
        for item_id, desc in GUI_ITEMS
    ])
    write_csv(OUT / "r2_4h1k4_preferred_template_record.csv", [{
        "preferred_template": "H1J4 integer DBR RCLED-MDC derived runtime FSP",
        "preferred_runtime_fsp": str(H1J4_FSP),
        "exists_by_filesystem_stat": fsp_exists,
        "status": "gui_audited_preferred_template",
        "bottom_dbr_group": "H1J4_bottom_DBR_QWinteger453_10pair",
        "bottom_dbr_layer_count": h1j4.get("bottom_dbr_layer_count", 20),
        "tio2_thickness_nm": h1j4.get("tio2_thickness_nm", 45.0),
        "sio2_thickness_nm": h1j4.get("sio2_thickness_nm", 79.0),
        "source_y_nm": -800,
        "wavelength_nm": 453,
        "rcwa_audit_decision": h1j4.get("rcwa_audit_decision", "lumerical_rcwa_available_for_minimal_probe"),
        "fmm_ready_for_minimal_probe": h1j4.get("fmm_ready_for_minimal_probe", True),
    }])
    write_csv(OUT / "r2_4h1k4_h1j3_vs_h1j4_status.csv", [
        {"template": "H1J3", "runtime_fsp": str(H1J3_FSP), "dbr_name": "QWexact453_10pair", "tio2_nm": 44.7, "sio2_nm": 79.4, "status": "previous_exact_quarter_wave_reference_not_preferred_unless_requested"},
        {"template": "H1J4", "runtime_fsp": str(H1J4_FSP), "dbr_name": "QWinteger453_10pair", "tio2_nm": 45.0, "sio2_nm": 79.0, "status": "preferred_integer_dbr_gui_audited_forward_template"},
    ])
    write_csv(OUT / "r2_4h1k4_simulation_gate_rules.csv", [
        {"gate": "H1L FDTD", "allowed_now": "no", "future_condition": "explicit user approval after H1K4", "constraints": "x-only, 453 nm, three x positions, incoherent averaging, no center-only"},
        {"gate": "FMM2B1 RCWA", "allowed_now": "no", "future_condition": "explicit user approval", "constraints": "tiny Lumerical RCWA/addrcwa API smoke test only, no heavy sweep"},
        {"gate": "y-dipole", "allowed_now": "no", "future_condition": "deferred until structure frozen", "constraints": "not part of current stage"},
        {"gate": "broadband", "allowed_now": "no", "future_condition": "deferred", "constraints": "not before single-wavelength source validation"},
        {"gate": "APCD coupling", "allowed_now": "no", "future_condition": "after RCLED-MDC template and validation are frozen", "constraints": "not part of H1K4"},
    ])

    write_md(OUT / "r2_4h1k4_future_h1l_fdtd_validation_constraints.md", """
# Future H1L FDTD Validation Constraints

H1L is allowed only after explicit user approval. H1K4 itself does not run FDTD.

Required H1L constraints:

- x-only / x-dipole
- wavelength = 453 nm
- source-isolated
- PlaneSource disabled
- source_1 positions at least x = -2500 nm, 0 nm, +2500 nm
- y fixed at -800 nm unless explicitly changed
- incoherent intensity/power averaging across source positions
- no center-only validation
- no y-dipole
- no broadband
- no APCD coupling

Required metrics:

- peak_angle_deg
- angular_FWHM_deg
- eta5, eta10, eta20
- leakage20_40
- leakage40_60
- normal_to_40_60_ratio
- double_lobe_flag if applicable
- comparison to H1H corrected MDC-only benchmark
""")
    write_md(OUT / "r2_4h1k4_future_fmm2b1_rcwa_constraints.md", """
# Future FMM2B1 RCWA Constraints

FMM2B1 is allowed only after explicit user approval. H1K4 itself does not run RCWA/FMM.

Required FMM2B1 constraints:

- use Lumerical built-in RCWA/addrcwa path
- start with tiny API smoke test / minimal calculation
- no heavy sweep
- no large dataset
- x-polarized only at current stage
- target 453 nm first
- periodic RCLED-MDC source module / stack proxy only
- compare qualitative trend to H1H/H1J4 goals before using RCWA as ranking layer
""")
    write_md(OUT / "r2_4h1k4_next_stage_recommendation.md", """
# R2-4H1K4 Next Stage Recommendation

H1J4 is now the preferred integer-DBR RCLED-MDC simulation template, based on the user-reported manual GUI pass.

Next possible actions, both requiring explicit user approval:

1. H1L x-only three-position 453 nm FDTD validation.
2. FMM2B1 tiny Lumerical RCWA/addrcwa API smoke test.

No automatic FDTD or RCWA follows H1K4.
""")
    write_md(OUT / "r2_4h1k4_stop_allow_rules.md", """
# R2-4H1K4 Stop / Allow Rules

Stop:

- no FDTD in H1K4
- no RCWA/FMM in H1K4
- no lumapi
- no FSP open/modify
- no y-dipole
- no broadband
- no APCD coupling
- no center-only validation
- no committing heavy files

Allow:

- record user manual GUI audit pass
- stat the H1J4 FSP path without opening it
- commit lightweight CSV/JSON/MD/script reports
""")
    write_md(OUT / "r2_4h1k4_summary.md", f"""
# R2-4H1K4 Summary

`h1k4_gui_decision = {h1k4_gui_decision}`

The user manually inspected the H1J4 derived runtime FSP in the GUI and reported no issues. H1K4 records that manual pass and freezes H1J4 as the preferred integer-DBR RCLED-MDC template for future planning.

Preferred runtime FSP:

`{H1J4_FSP}`

Derived FSP exists by filesystem stat: `{fsp_exists}`

Immediate FDTD in H1K4: `no`
Immediate RCWA in H1K4: `no`

Next stage requires explicit user approval: H1L x-only three-position FDTD validation or FMM2B1 tiny RCWA API smoke test.
""")

    manifest = {
        "stage": "R2-4H1K4 manual GUI audit record for H1J4",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "branch": sh(["branch", "--show-current"]),
        "git_status_short_at_generation": sh(["status", "--short"]),
        "prior_dirs": {"h1j4": str(H1J4_DIR), "h1k": str(H1K_DIR), "fmm2a": str(FMM2A_DIR), "h1h": str(H1H_DIR)},
        "h1k4_gui_decision": h1k4_gui_decision,
        "preferred_runtime_fsp": str(H1J4_FSP),
        "h1j4_derived_fsp_exists_by_filesystem_stat": fsp_exists,
        "h1j4_derived_fsp_size_bytes": fsp_stat.st_size if fsp_stat else None,
        "h1j4_simulation_template_status": "gui_audited_preferred_template",
        "h1j3_status": "previous_exact_quarter_wave_reference_not_preferred_unless_requested",
        "rcwa_audit_decision": h1j4.get("rcwa_audit_decision", "lumerical_rcwa_available_for_minimal_probe"),
        "fmm_ready_for_minimal_probe": h1j4.get("fmm_ready_for_minimal_probe", True),
        "immediate_FDTD_allowed_in_H1K4": False,
        "immediate_RCWA_allowed_in_H1K4": False,
        "y_dipole_allowed": False,
        "broadband_allowed": False,
        "APCD_coupling_allowed": False,
        "next_stage_recommendation": "explicit approval required for H1L x-only three-position FDTD or FMM2B1 tiny RCWA API smoke test",
        "outputs": sorted(p.name for p in OUT.iterdir() if p.is_file()),
    }
    (OUT / "r2_4h1k4_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "h1k4_gui_decision": h1k4_gui_decision,
        "preferred_runtime_fsp": str(H1J4_FSP),
        "h1j4_fsp_exists": fsp_exists,
        "h1j4_simulation_template_status": "gui_audited_preferred_template",
        "immediate_FDTD_allowed_in_H1K4": False,
        "immediate_RCWA_allowed_in_H1K4": False,
    }, indent=2))


if __name__ == "__main__":
    main()
