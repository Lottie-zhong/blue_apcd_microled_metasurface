from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4h1k_fmm2a2_joint_gui_audit_and_fmm_env_plan"
DERIVED_FSP = ROOT / "runtime" / "r2_4h1j3_rcled_mdc_corrected_derived_fsp_DO_NOT_COMMIT" / "MDC_blue_oujizi_RCLED_QWexact453_10pair_H1J3.fsp"
INPUT_DIRS = {
    "h1j3": ROOT / "outputs" / "r2_4h1j3_create_corrected_derived_rcled_mdc_fsp_no_run",
    "fmm2a": ROOT / "outputs" / "r2_fmm2a_solver_inventory_and_validation_protocol",
    "h1h": ROOT / "outputs" / "r2_4h1h_corrected_metric_freeze_and_physics_decision",
    "h1i": ROOT / "outputs" / "r2_4h1i_rcled_mdc_bottom_reflector_design_plan",
}
FARFIELD_SETTINGS = [
    ("projection direction", "auto"),
    ("material index", "auto"),
    ("far field filter", "1"),
    ("2D resolution", "1001"),
    ("3D resolution", "1001"),
    ("Assume structure is periodic", "unchecked / false"),
    ("override near field mesh", "unchecked / false"),
]


def run_git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"parse_error": str(exc), "path": str(path)}


def input_status() -> dict[str, object]:
    status = {}
    for key, path in INPUT_DIRS.items():
        status[key] = {
            "path": str(path),
            "exists": path.exists(),
            "file_count": len(list(path.glob("*"))) if path.exists() else 0,
        }
    return status


def main() -> None:
    if Path.cwd().resolve() != ROOT.resolve():
        raise SystemExit(f"Run from {ROOT}, current cwd is {Path.cwd()}")
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    branch = run_git(["branch", "--show-current"])
    git_status = run_git(["status", "--short"])
    h1j3_manifest = read_json(INPUT_DIRS["h1j3"] / "r2_4h1j3_manifest.json")
    fmm2a_manifest = read_json(INPUT_DIRS["fmm2a"] / "r2_fmm2a_manifest.json")

    gui_rows = [
        {"section": "bottom_dbr_group", "item": "group name", "expected": "H1J3_bottom_DBR_QWexact453_10pair", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Confirm group exists in GUI."},
        {"section": "bottom_dbr_group", "item": "layer count", "expected": "20 layers", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "10 TiO2/SiO2 pairs."},
        {"section": "bottom_dbr_group", "item": "layer order from cavity side downward", "expected": "TiO2 then SiO2 repeated 10 times", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Visual stack check only."},
        {"section": "bottom_dbr_group", "item": "TiO2 thickness", "expected": "about 44.7 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Quarter-wave at 453 nm."},
        {"section": "bottom_dbr_group", "item": "SiO2 thickness", "expected": "about 79.4 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Quarter-wave at 453 nm."},
        {"section": "bottom_dbr_group", "item": "bottom DBR y range", "expected": "about -2191 nm to -950 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Coordinates from H1J3 record."},
        {"section": "mesh_order_overlap", "item": "GaN overlap handling", "expected": "DBR may overlap large GaN rectangle", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "Overlap is acceptable only if DBR mesh order override is verified."},
        {"section": "mesh_order_overlap", "item": "object-level mesh order override", "expected": "true for all bottom DBR layers", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "No FDTD if not visually confirmed."},
        {"section": "mesh_order_overlap", "item": "mesh order value", "expected": "1 for all bottom DBR layers", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_mesh_order_fix", "notes": "DBR must override GaN in overlap regions."},
        {"section": "source_setup", "item": "source_1 x", "expected": "0 nm default", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "Later validation must not be center-only."},
        {"section": "source_setup", "item": "source_1 y", "expected": "-800 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "Inside cavity."},
        {"section": "source_setup", "item": "source_1 wavelength", "expected": "453 nm start/stop", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "Single wavelength planning."},
        {"section": "source_setup", "item": "source type", "expected": "electric dipole", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "x-polarized validation only."},
        {"section": "source_setup", "item": "theta", "expected": "90 deg", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "Physical x dipole."},
        {"section": "source_setup", "item": "phi", "expected": "0 deg", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "Physical x dipole."},
        {"section": "source_setup", "item": "source_1 enabled", "expected": "true", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "PlaneSource must be disabled."},
        {"section": "source_setup", "item": "PlaneSource enabled", "expected": "false", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_source_fix", "notes": "No plane-wave run."},
        {"section": "fdtd_region", "item": "y min", "expected": "about -2800 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_manual_review", "notes": "Bottom DBR inside FDTD."},
        {"section": "fdtd_region", "item": "y max", "expected": "about 1400 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_manual_review", "notes": "Top MDC and monitor inside FDTD."},
        {"section": "fdtd_region", "item": "PML margin below bottom DBR", "expected": "visually reasonable", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_manual_review", "notes": "Do not run if cramped."},
        {"section": "monitor", "item": "monitor y", "expected": "about 1100 nm", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_monitor_fix", "notes": "Do not compare to local group coordinates blindly."},
        {"section": "monitor", "item": "output side", "expected": "visually above top MDC", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_monitor_fix", "notes": "Global/effective coordinate safety required."},
        {"section": "monitor", "item": "not inside layer stack", "expected": "not inside TiO2/SiO2", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_monitor_fix", "notes": "If ambiguous, fail to monitor fix."},
        {"section": "monitor", "item": "upper PML spacing", "expected": "reasonable", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_monitor_fix", "notes": "Confirm visually."},
        {"section": "no_simulation", "item": "no FDTD run during GUI audit", "expected": "confirmed", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_process_restart", "notes": "H1K is planning only."},
        {"section": "no_simulation", "item": "derived FSP not overwritten", "expected": "confirmed", "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_process_restart", "notes": "Keep runtime FSP uncommitted."},
    ]
    write_csv(OUT / "r2_4h1k_h1j3_manual_gui_audit_form.csv", gui_rows)

    write_csv(OUT / "r2_4h1k_h1j3_farfield_settings_checklist.csv", [
        {"setting": k, "expected_value": v, "user_result": "pending", "failure_decision_if_not_pass": "failed_requires_farfield_setting_fix"}
        for k, v in FARFIELD_SETTINGS
    ])
    write_csv(OUT / "r2_4h1k_h1j3_gui_decision_rules.csv", [
        {"condition": "all H1J3 GUI audit items pass", "h1k_gui_decision": "h1j3_manual_gui_audit_passed_simulation_planning_allowed", "immediate_fdtd": "no"},
        {"condition": "mesh order not confirmed", "h1k_gui_decision": "failed_requires_mesh_order_fix", "immediate_fdtd": "no"},
        {"condition": "monitor unsafe or ambiguous", "h1k_gui_decision": "failed_requires_monitor_fix", "immediate_fdtd": "no"},
        {"condition": "far-field settings not confirmed", "h1k_gui_decision": "failed_requires_farfield_setting_fix", "immediate_fdtd": "no"},
        {"condition": "source setup wrong", "h1k_gui_decision": "failed_requires_source_fix", "immediate_fdtd": "no"},
    ])
    write_csv(OUT / "r2_fmm2a2_environment_option_matrix.csv", [
        {"route": "Pure-Python RCWA/FMM package", "installation_required": "yes", "setup_difficulty": "low_to_medium_if_package_available", "periodic_rcled_mdc_suitability": "good_for_angle_wavelength_sweeps", "source_averaged_screening_suitability": "limited_without_dipole_coupling_model", "risks": "API maturity; Windows compatibility; polarization/order conventions", "recommended_next_action": "install/select package only after user approval; then FMM2B minimal API probe"},
        {"route": "MATLAB Reticolo", "installation_required": "yes", "setup_difficulty": "medium_to_high", "periodic_rcled_mdc_suitability": "strong_if_MATLAB_and_Reticolo_available", "source_averaged_screening_suitability": "limited_without_extra_dipole_mapping", "risks": "license; path setup; Python integration overhead", "recommended_next_action": "confirm MATLAB/Reticolo availability before planning bridge"},
        {"route": "S4", "installation_required": "yes", "setup_difficulty": "high_on_windows_server", "periodic_rcled_mdc_suitability": "strong_for_RCWA_like_periodic_structures", "source_averaged_screening_suitability": "limited_without_dipole_mapping", "risks": "installation complexity; binary compatibility", "recommended_next_action": "consider only if install route is already known"},
        {"route": "Custom minimal 1D/2D FMM prototype", "installation_required": "no_or_small", "setup_difficulty": "medium", "periodic_rcled_mdc_suitability": "learning_calibration_only", "source_averaged_screening_suitability": "not_reliable_for_ranking_without_validation", "risks": "implementation errors; convention bugs; false confidence", "recommended_next_action": "do not use for candidate ranking"},
        {"route": "Fallback TMM + limited FDTD", "installation_required": "no", "setup_difficulty": "low", "periodic_rcled_mdc_suitability": "TMM_only_for_1D_stack_trends", "source_averaged_screening_suitability": "requires_explicit_tri_position_FDTD_for_candidates", "risks": "TMM proxy misses dipole/far-field coupling", "recommended_next_action": "continue H1K/H1L path while FMM remains unavailable"},
    ])
    write_csv(OUT / "r2_fmm2a2_solver_installation_risk_register.csv", [
        {"risk": "no importable FMM/RCWA solver", "status": "current", "impact": "FMM2B cannot proceed", "mitigation": "environment option review before install"},
        {"risk": "solver convention mismatch", "status": "future", "impact": "wrong polarization/order interpretation", "mitigation": "minimal API probe and benchmark against simple stack"},
        {"risk": "source averaging not represented in FMM", "status": "current", "impact": "candidate false positives", "mitigation": "keep FDTD tri-position gate for validation"},
        {"risk": "heavy sweep too early", "status": "blocked", "impact": "wasted runtime and misleading ranking", "mitigation": "no heavy FMM sweep in H1K/FMM2A2"},
    ])
    write_csv(OUT / "r2_4h1k_fmm2a2_stop_allow_rules.csv", [
        {"action": "Run FDTD immediately", "allowed": "no", "reason": "H1J3 manual GUI audit pending"},
        {"action": "Run FMM/RCWA immediately", "allowed": "no", "reason": "no solver available from FMM2A"},
        {"action": "Run heavy FMM sweep", "allowed": "no", "reason": "environment not ready and no minimal probe"},
        {"action": "Run y-dipole", "allowed": "no", "reason": "current validation is x-only; XY deferred"},
        {"action": "Run broadband FDTD", "allowed": "no", "reason": "single-wavelength 453 nm gate first"},
        {"action": "APCD coupling", "allowed": "no", "reason": "RCLED/MDC source module not frozen"},
        {"action": "Manual GUI audit of H1J3 runtime FSP", "allowed": "yes", "reason": "required next user action"},
        {"action": "H1L x-only three-position FDTD plan/run", "allowed": "only_after_explicit_user_approval_and_H1K_GUI_pass", "reason": "no automatic simulation"},
        {"action": "FMM2B minimal solver probe", "allowed": "only_after_solver_available_and_explicit_user_approval", "reason": "FMM2A found no solver"},
    ])

    write_text(OUT / "r2_4h1k_h1j3_manual_gui_audit_protocol.md", f"""
# R2-4H1K H1J3 Manual GUI Audit Protocol

Target runtime FSP, not committed:

`{DERIVED_FSP}`

This protocol records what the user must confirm manually in the Lumerical GUI before any H1L FDTD validation is planned. H1K itself performs no simulation, does not open or modify the FSP, and does not use lumapi.

Required GUI confirmations:

1. Bottom DBR group `H1J3_bottom_DBR_QWexact453_10pair` exists, contains 20 layers, and is ordered from the cavity side downward as TiO2 then SiO2 repeated 10 times.
2. TiO2 layers are about 44.7 nm, SiO2 layers are about 79.4 nm, and the bottom DBR y range is about -2191 nm to -950 nm.
3. The bottom DBR may overlap the large GaN rectangle, but every bottom DBR layer must have object-level mesh order override enabled and mesh order = 1. No FDTD is allowed if this is not visually confirmed.
4. `source_1` is an electric x-dipole at x = 0 nm, y = -800 nm, wavelength = 453 nm, theta = 90 deg, phi = 0 deg, and enabled. `PlaneSource` must be disabled.
5. FDTD y min/y max are about -2800 nm / 1400 nm, and the bottom DBR, source, and top MDC are inside the region with reasonable PML margin.
6. The DFT monitor remains about y = 1100 nm and is visually on the output side of the top MDC, not inside TiO2/SiO2, and not too close to the upper PML.
7. Far-field settings match the checklist exactly.
8. No FDTD run is performed during this GUI audit and the derived runtime FSP is not accidentally overwritten.

Decision: pass only if every required item is confirmed. If monitor, source, far-field, or mesh-order status is ambiguous, H1K fails into the corresponding fix stage rather than FDTD.
""")
    write_text(OUT / "r2_fmm2a2_next_solver_probe_plan.md", """
# R2-FMM2A2 Next Solver Probe Plan

FMM2A found no importable FMM/RCWA package in the current server Python environment. Therefore FMM2B is not allowed yet.

Allowed next FMM path, after explicit user approval only:

1. Select an environment route: pure-Python RCWA/FMM package, MATLAB/Reticolo, S4, or fallback TMM + limited FDTD.
2. Install or expose exactly one solver environment outside this stage.
3. Run a tiny API smoke test in FMM2B, not a design sweep.
4. Bind the solver output to simple known stack behavior and then to H1H/H1L style metrics.

No heavy FMM sweep is allowed until a minimal solver probe succeeds and conventions are documented.
""")
    write_text(OUT / "r2_4h1k_fmm2a2_joint_gate_decision.md", """
# R2-4H1K / FMM2A2 Joint Gate Decision

`joint_gate_decision = gui_audit_required_and_fmm_env_not_ready`

Immediate FDTD is not allowed because the H1J3 derived FSP still requires manual GUI confirmation of mesh order, source setup, monitor placement, and far-field settings.

Immediate FMM/RCWA is not allowed because FMM2A found no importable FMM/RCWA solver in the current environment.

Immediate heavy FMM sweep, y-dipole validation, broadband FDTD, and APCD coupling are all blocked.

Next user action: manually open the uncommitted H1J3 derived FSP and complete the H1K GUI audit form.

Next Codex action after the user GUI audit: record the H1K audit if it passes, or create a corrected derived FSP fix stage if it fails.
""")
    write_text(OUT / "r2_4h1k_fmm2a2_next_stage_recommendation.md", """
# R2-4H1K / FMM2A2 Next Stage Recommendation

Recommended next user action: complete the manual GUI audit for the H1J3 runtime FSP.

If the GUI audit passes, the next possible simulation stage is an explicitly approved H1L x-only 453 nm source-isolated FDTD validation using at least three x-axis source positions and incoherent intensity/power averaging.

If the GUI audit fails due to mesh order, monitor position, source settings, or far-field settings, perform a corrected derived FSP fix stage first. Do not run FDTD.

For FMM, do not proceed to FMM2B until an FMM/RCWA solver is installed or otherwise made available. The first FMM2B action should be a tiny API probe, not a sweep.
""")
    write_text(OUT / "r2_4h1k_fmm2a2_summary.md", """
# R2-4H1K FMM2A2 Summary

H1K/FMM2A2 is a no-run joint gate. It prepares the manual GUI audit package for the H1J3 derived RCLED-MDC FSP and records FMM/RCWA environment options after FMM2A found no available solver.

Key decisions:

- `joint_gate_decision = gui_audit_required_and_fmm_env_not_ready`
- `immediate_fdtd_allowed = false`
- `immediate_fmm_allowed = false`
- `immediate_heavy_fmm_sweep_allowed = false`
- `fmm_ready_for_minimal_probe = false`
- `y_dipole_allowed = false`
- `broadband_allowed = false`
- `apcd_coupling_allowed = false`

The H1J3 runtime FSP must be manually inspected before any H1L simulation is planned. FMM2B must wait until a solver environment exists and the user explicitly approves a minimal probe.
""")

    manifest = {
        "stage": "R2-4H1K_FMM2A2_joint_gui_audit_and_fmm_env_plan",
        "created_at": now,
        "cwd": str(ROOT),
        "branch": branch,
        "git_status_short_at_generation": git_status,
        "input_status": input_status(),
        "h1j3_runtime_fsp": str(DERIVED_FSP),
        "h1j3_runtime_fsp_exists": DERIVED_FSP.exists(),
        "h1j3_manifest_decision": h1j3_manifest.get("h1j3_decision", "unknown"),
        "fmm2a_decision": fmm2a_manifest.get("fmm2a_decision", "unknown"),
        "joint_gate_decision": "gui_audit_required_and_fmm_env_not_ready",
        "h1k_gui_decision": "pending_manual_gui_audit",
        "fmm2a2_decision": "environment_options_recorded_no_solver_ready",
        "fmm_ready_for_minimal_probe": False,
        "immediate_fdtd_allowed": False,
        "immediate_fmm_allowed": False,
        "immediate_heavy_fmm_sweep_allowed": False,
        "y_dipole_allowed": False,
        "broadband_allowed": False,
        "apcd_coupling_allowed": False,
        "next_user_action": "manually open H1J3 derived FSP and complete H1K GUI audit form",
        "next_codex_action_after_gui_audit": "record H1K pass or create corrected FSP fix stage",
        "outputs": sorted(p.name for p in OUT.glob("*")),
    }
    (OUT / "r2_4h1k_fmm2a2_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({
        "joint_gate_decision": manifest["joint_gate_decision"],
        "fmm_ready_for_minimal_probe": manifest["fmm_ready_for_minimal_probe"],
        "immediate_fdtd_allowed": manifest["immediate_fdtd_allowed"],
        "immediate_fmm_allowed": manifest["immediate_fmm_allowed"],
        "output_dir": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
