from __future__ import annotations

import csv
import importlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_fmm2a_solver_inventory_and_validation_protocol"
OUT.mkdir(parents=True, exist_ok=True)

PYTHON_PACKAGES = [
    "numpy", "scipy", "pandas", "matplotlib",
    "rcwa", "grcwa", "S4", "reticolo", "meent", "torcwa", "tidy3d", "legume", "inkstone",
]
CLI_TOOLS = ["python", "pip", "conda"]
FMM_NAMES = {"rcwa", "grcwa", "S4", "reticolo", "meent", "torcwa", "tidy3d", "legume", "inkstone"}


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


def run_text(args: list[str], timeout: int = 10) -> str:
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        text = (cp.stdout or cp.stderr or "").strip().splitlines()
        return text[0] if text else f"returncode={cp.returncode}"
    except Exception as exc:
        return f"unavailable: {exc}"


def get_version(name: str):
    for candidate in [name, name.lower(), name.replace("_", "-")]:
        try:
            return importlib.metadata.version(candidate)
        except Exception:
            pass
    return "unknown"


def classify_solver(name: str, import_ok: bool) -> str:
    if name not in FMM_NAMES:
        return "not_preferred_for_this_branch"
    if not import_ok:
        return "unavailable"
    if name in {"grcwa", "rcwa", "meent", "torcwa", "S4", "inkstone"}:
        return "import_available_but_needs_api_probe"
    if name in {"tidy3d", "legume", "reticolo"}:
        return "not_preferred_for_this_branch"
    return "import_available_but_needs_api_probe"


def solver_notes(name: str) -> dict:
    # Conservative, no overclaiming. Unknown means unverified in this environment.
    base = {
        "1d_multilayer_dbr_mdc": "unknown",
        "2d_periodic_rcled_mdc_stack": "unknown",
        "angle_wavelength_sweep": "unknown",
        "polarization_resolved_rt": "unknown",
        "diffraction_order_extraction": "unknown",
        "field_source_expansion_support": "unknown",
        "gpu_support": "unknown",
        "windows_server_compatibility_uncertainty": "unknown",
    }
    if name == "grcwa":
        base.update({"2d_periodic_rcled_mdc_stack": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "diffraction_order_extraction": "likely", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "rcwa":
        base.update({"1d_multilayer_dbr_mdc": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "meent":
        base.update({"2d_periodic_rcled_mdc_stack": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "diffraction_order_extraction": "likely", "gpu_support": "possible_via_backend_unknown", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "torcwa":
        base.update({"2d_periodic_rcled_mdc_stack": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "diffraction_order_extraction": "likely", "gpu_support": "likely_torch_cuda_if_available", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "S4":
        base.update({"2d_periodic_rcled_mdc_stack": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "diffraction_order_extraction": "likely", "windows_server_compatibility_uncertainty": "high_needs_probe"})
    elif name == "inkstone":
        base.update({"2d_periodic_rcled_mdc_stack": "likely", "angle_wavelength_sweep": "likely", "polarization_resolved_rt": "likely", "diffraction_order_extraction": "likely", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "tidy3d":
        base.update({"2d_periodic_rcled_mdc_stack": "possible_but_not_fmm_local", "angle_wavelength_sweep": "possible", "windows_server_compatibility_uncertainty": "cloud_workflow_not_preferred_here"})
    elif name == "legume":
        base.update({"2d_periodic_rcled_mdc_stack": "not_primary_rcwa", "windows_server_compatibility_uncertainty": "needs_probe"})
    elif name == "reticolo":
        base.update({"2d_periodic_rcled_mdc_stack": "possible_if_python_binding_exists", "windows_server_compatibility_uncertainty": "high_unknown"})
    return base

# Sanity and environment.
branch = run_text(["git", "branch", "--show-current"])
git_status = run_text(["git", "status", "--short"])
cwd_ok = Path.cwd().resolve() == ROOT.resolve()

inventory_rows = []
for name in PYTHON_PACKAGES:
    row = {"kind": "python_import", "name": name, "available": False, "version": "", "classification": "", "detail": ""}
    try:
        mod = importlib.import_module(name)
        row["available"] = True
        row["version"] = getattr(mod, "__version__", None) or get_version(name)
        row["detail"] = "import succeeded"
    except Exception as exc:
        row["available"] = False
        row["version"] = "unavailable"
        row["detail"] = str(exc).splitlines()[0]
    row["classification"] = classify_solver(name, bool(row["available"]))
    inventory_rows.append(row)

for tool in CLI_TOOLS:
    path = shutil.which(tool)
    inventory_rows.append({
        "kind": "cli_path",
        "name": tool,
        "available": bool(path),
        "version": run_text([tool, "--version"]) if path else "unavailable",
        "classification": "environment_tool" if path else "unavailable",
        "detail": path or "not found on PATH",
    })

write_csv(OUT / "r2_fmm2a_solver_inventory.csv", inventory_rows)

suitability_rows = []
for row in inventory_rows:
    if row["kind"] != "python_import" or row["name"] not in FMM_NAMES:
        continue
    notes = solver_notes(row["name"])
    suitability_rows.append({
        "solver": row["name"],
        "import_available": row["available"],
        "classification": row["classification"],
        **notes,
        "branch_note": "mid-fidelity screening only; not a final FDTD replacement",
    })
write_csv(OUT / "r2_fmm2a_solver_suitability_matrix.csv", suitability_rows)

scoring_rows = []
for layer, fields in {
    "TMM_score": ["stopband_center_nm", "stopband_width_nm", "cavity_resonance_nm", "resonance_detuning_from_453_nm", "spectral_FWHM_proxy_nm", "TMM_score_total", "TMM_pass_flag"],
    "FMM_score": ["source_averaged_peak_nm", "source_averaged_spectral_FWHM_nm", "source_averaged_angular_FWHM_deg", "DA_deg", "eta5", "eta10", "eta20", "leakage20_40", "leakage40_60", "normal_to_40_60_ratio", "peak_shift_proxy_nm", "source_grid_sensitivity", "double_lobe_flag", "FMM_score_total", "FMM_pass_flag"],
    "FDTD_score": ["x_axis_positions_nm", "source_isolation_confirmed", "source_position_confirmed", "source_wavelength_nm", "individual_peak_angles_deg", "incoherent_average_peak_angle_deg", "incoherent_average_angular_FWHM_deg", "incoherent_average_eta10", "incoherent_average_eta20", "incoherent_average_leakage40_60", "trend_consistency_with_FMM", "FDTD_score_total", "FDTD_pass_flag"],
}.items():
    for field in fields:
        scoring_rows.append({"score_layer": layer, "field": field, "required_for_freeze": "yes" if field.endswith("pass_flag") or field.endswith("score_total") else "supporting_metric"})
write_csv(OUT / "r2_fmm2a_three_layer_scoring_protocol.csv", scoring_rows)

freeze_rows = [
    {"rule": "candidate_freeze_allowed", "condition": "TMM_pass_flag=true AND FMM_pass_flag=true AND (FDTD_pass_flag=true OR not_failed_top_validation)", "allowed": "only_if_all_conditions_met"},
    {"rule": "no_TMM_only_freeze", "condition": "TMM_pass_flag=true but FMM/FDTD missing", "allowed": False},
    {"rule": "no_FMM_only_freeze", "condition": "FMM_pass_flag=true but FDTD top validation missing or failed", "allowed": False},
    {"rule": "FDTD_final_required", "condition": "finite mesa/final paper figures", "allowed": "FDTD remains required"},
]
write_csv(OUT / "r2_fmm2a_candidate_freeze_rules.csv", freeze_rows)

h1h_rows = [{
    "baseline_name": "MDC_blue_oujizi_MDC_only_H1H_corrected",
    "source_model": "x-dipole, 2D, source-isolated",
    "wavelength_nm": 450,
    "peak_angle_deg": 12.35,
    "FWHM_deg": 22.14,
    "eta10": 0.2935,
    "eta20": 0.6796,
    "leakage20_40": 0.1659,
    "leakage40_60": 0.0775,
    "normal_to_40_60_ratio": 3.7852,
    "use": "calibration/reference benchmark only; future RCLED-MDC target is 453 nm",
    "future_note": "MDC-only 453 nm x-axis three-position reference may be useful but is not allowed in FMM2A",
}]
write_csv(OUT / "r2_fmm2a_h1h_benchmark_binding.csv", h1h_rows)

acceptance_rows = [
    {"metric": "spectral_FWHM_nm", "initial": "<15", "preferred": "<10", "ideal": "5-6"},
    {"metric": "angular_DA_or_FWHM_deg", "initial": "<30", "preferred": "<20", "ideal": "10-15"},
    {"metric": "peak_shift_nm", "initial": "<5", "preferred": "<3", "ideal": "near_zero"},
    {"metric": "normal_offaxis_ratio", "initial": "clearly improved", "preferred": "high_ratio_no_double_lobe", "ideal": "high_and_stable"},
    {"metric": "source_grid_sensitivity", "initial": "acceptable", "preferred": "stable", "ideal": "low"},
    {"metric": "FDTD_top_validation", "initial": "trend_consistent", "preferred": "numerically_close", "ideal": "passes_three_position_validation"},
]
write_csv(OUT / "r2_fmm2a_acceptance_targets.csv", acceptance_rows)

scope_rows = [
    {"category": "suitable", "item": "periodic RCLED source module"},
    {"category": "suitable", "item": "periodic DBR/MDC"},
    {"category": "suitable", "item": "periodic metasurface layer"},
    {"category": "suitable", "item": "plane-wave angle/wavelength sweeps"},
    {"category": "suitable", "item": "MQW source-plane average approximated by angle/source averaging"},
    {"category": "suitable", "item": "early ranking and rejection"},
    {"category": "not_sufficient", "item": "real finite mesa"},
    {"category": "not_sufficient", "item": "sidewall leakage"},
    {"category": "not_sufficient", "item": "metal electrodes and complex boundaries"},
    {"category": "not_sufficient", "item": "non-periodic defects"},
    {"category": "not_sufficient", "item": "actual final device validation"},
    {"category": "not_sufficient", "item": "final paper figures"},
]
write_csv(OUT / "r2_fmm2a_fmm_scope_and_limits.csv", scope_rows)

available_fmm = [r for r in inventory_rows if r["name"] in FMM_NAMES and r["available"]]
plausible = [r for r in available_fmm if r["classification"] == "import_available_but_needs_api_probe"]
fmm_ready = bool(plausible)
recommended_solver = plausible[0]["name"] if plausible else "none"
fmm2a_decision = "solver_inventory_and_protocol_complete" if fmm_ready else "no_available_fmm_solver_protocol_only"

write_md(OUT / "r2_fmm2a_future_fmm2b_minimal_calculation_plan.md", """
# R2-FMM2B minimal calculation plan

No FDTD in FMM2B. The first FMM/RCWA calculation should be tiny and periodic.

Candidate structure: start with MDC-only Wan baseline if the solver API can represent it cleanly; otherwise use a simplified RCLED-MDC periodic stack.

Coarse grids first:

- wavelength: 445-461 nm or 443-463 nm
- angle: -60 to +60 deg coarse samples
- polarization: x-polarized only at this branch stage
- source averaging: approximate MQW source-plane emission by weighted angular spectrum, not a single normal-incidence plane wave only

Outputs: spectral FWHM, angular FWHM/DA, eta10/eta20, normal/offaxis ratio, and peak-shift proxy.

Stop condition: if the solver cannot reproduce the qualitative H1H MDC-only trend, do not use FMM as a ranking layer.
""")

write_md(OUT / "r2_fmm2a_literature_rationale.md", """
# R2-FMM2A literature/project rationale

FMM/RCWA is introduced as a mid-fidelity screening layer, not as a replacement for FDTD. TMM remains useful for fast thin-film stopband and cavity proxies, while FMM/RCWA can handle periodic layered structures with angle, wavelength, and polarization sweeps. FDTD remains required for finite mesa validation and final paper figures.

RC-micro-LED literature is used as a source-preconditioning benchmark only, not as an epitaxial stack to copy. The branch keeps ordinary InGaN/GaN MQW Micro-LED source modeling and does not require staggered MQW or NP-GaN/GaN DBR.

Benchmark values to preserve: DA = 39.04 deg; peak wavelength shifts from 456.16 nm to 449.18 nm as current density changes from 1.77 A/cm^2 to 54 A/cm^2; peak blue shift = 6.98 nm; spectral FWHM from 14.56 nm to 26.31 nm. Wan TiO2/SiO2 MDC remains the experimentally realistic multilayer/MDC reference.
""")

write_md(OUT / "r2_fmm2a_risk_register.md", """
# R2-FMM2A risk register

| risk | impact | mitigation |
|---|---|---|
| No FMM/RCWA package importable | Cannot run FMM2B probe | Discuss environment/install options; do not simulate in FMM2A |
| Import works but API unsuitable | False confidence from package availability | FMM2B must be a tiny API probe before ranking |
| FMM fails to reproduce H1H qualitative trend | Ranking layer invalid | Stop FMM route or recalibrate before candidate ranking |
| Periodic FMM misses finite-mesa leakage | False positives | Keep FDTD finite-mesa validation mandatory |
| Source averaging proxy too crude | Bad source-position stability prediction | Keep x-axis three-position FDTD for top candidates |
""")

next_text = "FMM2B minimal solver API probe / tiny no-heavy computation, only after user approval" if fmm_ready else "Discuss FMM/RCWA installation/environment options before any simulation"
write_md(OUT / "r2_fmm2a_next_stage_recommendation.md", f"""
# R2-FMM2A next-stage recommendation

Decision: `{fmm2a_decision}`.

Recommended solver candidate: `{recommended_solver}`.

FMM ready for minimal probe: `{fmm_ready}`.

Next allowed stage: {next_text}.

Immediate FDTD is not allowed. Heavy FMM sweeps are not allowed. y-dipole, broadband FDTD, and APCD coupling remain disallowed.
""")

write_md(OUT / "r2_fmm2a_stop_allow_rules.md", """
# R2-FMM2A stop / allow rules

Stop:
- no FDTD
- no lumapi
- no FSP open/modify/copy
- no heavy FMM/RCWA runs
- no solver installation or download
- no package manager changes
- no large datasets
- no y-dipole, broadband FDTD, or APCD coupling

Allow:
- Python import inventory
- CLI path/version inventory
- protocol and scoring documentation
- FMM2B planning only
""")

write_md(OUT / "r2_fmm2a_summary.md", f"""
# R2-FMM2A summary

Decision: `{fmm2a_decision}`.

Current worktree sanity:

- cwd ok: `{cwd_ok}`
- branch: `{branch}`
- git status short: `{git_status}`

Importable FMM/RCWA-like packages: {', '.join(r['name'] for r in available_fmm) if available_fmm else 'none'}.

Recommended solver candidate for a later minimal API probe: `{recommended_solver}`.

FMM is only a calibrated mid-fidelity screening layer between TMM and FDTD. It is not accepted as a full FDTD replacement. Candidate freeze requires TMM good + FMM good + FDTD top validation not failed.
""")

manifest = {
    "stage": "R2-FMM2A solver inventory and validation protocol",
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "cwd": str(Path.cwd()),
    "cwd_expected": str(ROOT),
    "cwd_ok": cwd_ok,
    "branch": branch,
    "git_status_short": git_status,
    "fmm2a_decision": fmm2a_decision,
    "available_importable_fmm_rcwa_packages": [r["name"] for r in available_fmm],
    "recommended_solver_candidate": recommended_solver,
    "fmm_ready_for_minimal_probe": fmm_ready,
    "immediate_fdtd_allowed": False,
    "immediate_heavy_fmm_sweep_allowed": False,
    "y_dipole_allowed": False,
    "broadband_fdtd_allowed": False,
    "apcd_coupling_allowed": False,
    "next_stage_recommendation": next_text,
    "outputs": sorted(set([p.name for p in OUT.iterdir() if p.is_file()] + ["r2_fmm2a_manifest.json"])),
}
(OUT / "r2_fmm2a_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print(json.dumps({
    "fmm2a_decision": fmm2a_decision,
    "available_fmm_rcwa": [r["name"] for r in available_fmm],
    "recommended_solver_candidate": recommended_solver,
    "fmm_ready_for_minimal_probe": fmm_ready,
    "immediate_fdtd_allowed": False,
    "immediate_heavy_fmm_sweep_allowed": False,
}, indent=2))
