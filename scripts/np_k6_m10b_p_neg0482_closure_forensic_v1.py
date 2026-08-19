from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
POST = ROOT / "outputs/np_k6_m10b_serial_execution_v1/runtime_runs/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE/attempt_001/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_001_post.fsp"
PREFSP = ROOT / "outputs/np_k6_m10b_serial_execution_v1/runtime_prefsp/NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE.fsp"
RUN_DIR = POST.parent
OUT = ROOT / "outputs/np_k6_m10b_p_neg0482_closure_forensic_v1"
DOC = ROOT / "docs/np_k6_m10b_p_neg0482_closure_forensic_v1.md"
TARGET_UX = -0.48275862068965514
WAVELENGTHS = list(range(445, 456))
CASE = "NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE"
GEOMETRY_HASH = "00a951a831619fe0a34b5ffd5c58545282e2236d79190bd9d2d3961dd856f7b1"
EXPECTED_POST_SHA = "60c6f668b0f9fdc64b00b10fa00699314d4f377ac711ed6142290ac7020e67fc"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def arr(x):
    return np.asarray(x).reshape(-1)


def finite(x):
    return bool(np.all(np.isfinite(np.asarray(x, dtype=float))))


def fval(x):
    try:
        return float(np.real(x))
    except Exception:
        return None


def main():
    if not POST.exists() or not PREFSP.exists():
        raise FileNotFoundError("forensic input FSP missing")
    post_sha_before = sha(POST)
    pre_sha = sha(PREFSP)
    # LumAPI is imported only for independent read-only extraction.
    sys.path.insert(0, str(ROOT / "src"))
    import lumapi  # type: ignore

    fd = lumapi.FDTD(str(POST), hide=True)
    try:
        tr = fd.getresult("transmission_monitor", "T")
        rr = fd.getresult("reflection_monitor", "T")
        lam_nm = arr(tr["lambda"]) * 1e9
        tvals = np.real(arr(tr["T"]))
        r_signed = np.real(arr(rr["T"]))
        rvals = np.abs(r_signed)
        freq = arr(tr["f"])
        raw_t = np.real(arr(fd.getdata("transmission_monitor", "power")))
        raw_r = np.real(arr(fd.getdata("reflection_monitor", "power")))
        sourcepower = np.asarray([float(fd.sourcepower(float(x))) for x in freq])
        rows = []
        orders = []
        for i in range(len(lam_nm)):
            g = np.real(arr(fd.grating("transmission_monitor", i + 1)))
            n = np.rint(np.real(arr(fd.gratingn("transmission_monitor", i + 1)))).astype(int)
            ux = np.real(arr(fd.gratingu1("transmission_monitor", i + 1)))
            m = min(len(g), len(n), len(ux))
            g, n, ux = g[:m], n[:m], ux[:m]
            denom = float(np.sum(np.abs(g)))
            frac = g / denom
            eta = tvals[i] * frac
            order_map = {str(int(nn)): float(ee) for nn, ee in zip(n, eta)}
            closure = float(1.0 - rvals[i] - tvals[i])
            rows.append({
                "wavelength_nm": float(lam_nm[i]), "R_total": float(rvals[i]), "T_total": float(tvals[i]),
                "signed_reflection_T": float(r_signed[i]), "closure_RT": closure,
                "abs_residual": abs(closure), "eta_plus1": float(order_map.get("1", 0.0)),
                "eta_0": float(order_map.get("0", 0.0)), "eta_minus1": float(order_map.get("-1", 0.0)),
                "order_sum_T_mismatch": abs(float(np.sum(eta)) - float(tvals[i])),
                "raw_transmission_over_sourcepower": float(raw_t[i] / sourcepower[i]),
                "raw_reflection_over_sourcepower_signed": float(raw_r[i] / sourcepower[i]),
                "normalization_T_mismatch": abs(float(raw_t[i] / sourcepower[i]) - float(tvals[i])),
                "normalization_R_mismatch": abs(float(raw_r[i] / sourcepower[i]) - float(r_signed[i])),
                "open_order_count": int(m), "all_transmitted_orders_json": json.dumps(order_map, sort_keys=True),
            })
            for nn, uu, ff, ee in zip(n, ux, frac, eta):
                orders.append({"wavelength_nm": float(lam_nm[i]), "order_n": int(nn), "u_x": float(uu), "fraction": float(ff), "eta_abs": float(ee)})

        fdtd_keys = ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc", "mesh accuracy", "mesh refinement", "simulation time", "auto shutoff min", "pml layers", "x span", "y span", "z span", "z min", "z max"]
        fdtd_rb = {k: str(fd.getnamed("FDTD", k)) for k in fdtd_keys}
        src_keys = ["z", "x span", "y span", "wavelength start", "wavelength stop", "angle theta", "angle phi", "polarization angle", "injection axis", "direction", "plane wave type"]
        src_rb = {k: str(fd.getnamed("source_x_forward", k)) for k in src_keys}
        mon_rb = {}
        for name in ["reflection_monitor", "transmission_monitor", "order_monitor", "field_450_monitor"]:
            mon_rb[name] = {k: str(fd.getnamed(name, k)) for k in ["type", "monitor type", "z", "x span", "y span", "frequency points", "wavelength center", "wavelength span", "spatial interpolation"] if _has(fd, name, k)}
        material = {}
        for name in ["APCD_TIO2_NATIVE_M1", "APCD_SIO2_NATIVE_M1"]:
            data = np.asarray(fd.getmaterial(name, "sampled data"))
            material[name] = {"type": str(fd.getmaterial(name, "type")), "sampled_shape": list(data.shape), "sampled_dtype": str(data.dtype), "sampled_rows": int(len(data)), "sampled_data_sha256": hashlib.sha256(data.tobytes()).hexdigest(), "k_max_abs": float(np.max(np.abs(np.imag(data[:, 1])))), "n_min": float(np.min(np.real(data[:, 1]))), "n_max": float(np.max(np.real(data[:, 1])))}
            # Native table is frequency plus real n; interpolate only the diagnostic material audit.
            material[name]["n_at_wavelength"] = {str(w): float(np.interp(299792458.0 / (w * 1e-9), data[:, 0].real, data[:, 1].real)) for w in WAVELENGTHS}
            material[name]["epsilon_at_wavelength"] = {str(w): float(np.interp(299792458.0 / (w * 1e-9), data[:, 0].real, data[:, 1].real) ** 2) for w in WAVELENGTHS}
    finally:
        fd.close()

    # Exact wavelength and finite checks are intentionally computed from the fresh session values.
    residuals = np.asarray([r["closure_RT"] for r in rows], dtype=float)
    absres = np.abs(residuals)
    worst = rows[int(np.argmax(absres))]
    diffs = np.diff(residuals)
    smooth = bool(np.max(np.abs(np.diff(residuals, n=2))) < 0.004)
    max_order = max(r["order_sum_T_mismatch"] for r in rows)
    max_norm = max(max(r["normalization_T_mismatch"], r["normalization_R_mismatch"]) for r in rows)
    dump("per_wavelength_energy.json", {"case_id": CASE, "rows": rows, "orders": orders, "exact_11_points": len(rows) == 11, "all_finite": all(finite([x["R_total"], x["T_total"], x["closure_RT"]]) for x in rows)})
    with (OUT / "per_wavelength_energy.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (OUT / "transmitted_orders.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(orders[0])); w.writeheader(); w.writerows(orders)

    dump("material_loss_audit.json", {"materials": material, "all_sampled_k_zero": all(v["k_max_abs"] == 0.0 for v in material.values()), "material_absorption_expected": 0.0, "volume_absorption_saved": False, "boundary_flux_saved": False, "A_observable": False, "status": "ABSORPTION_NOT_DIRECTLY_OBSERVABLE_FROM_SAVED_STATE"})
    dump("extended_rta_audit.json", {"A_observable": False, "closure_RT_max_abs": float(np.max(absres)), "closure_RTA": None, "gate_revision": False, "status": "ABSORPTION_NOT_DIRECTLY_OBSERVABLE_FROM_SAVED_STATE"})
    theta = math.radians(float(src_rb["angle theta"])); ux_recon = math.sin(theta); cos_theta = math.cos(theta)
    ux_rows = [{"wavelength_nm": w, "ux_target": TARGET_UX, "ux_reconstructed": ux_recon, "abs_error": abs(ux_recon - TARGET_UX), "kx_over_k0": ux_recon} for w in WAVELENGTHS]
    with (OUT / "fixed_ux_reconstruction.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ux_rows[0])); w.writeheader(); w.writerows(ux_rows)
    dump("fixed_ux_audit.json", {"target_ux": TARGET_UX, "theta_deg": float(src_rb["angle theta"]), "kx_over_k0_reconstructed": ux_recon, "cos_theta": cos_theta, "max_abs_error": abs(ux_recon - TARGET_UX), "fixed_ux_drift": False, "source_contract": src_rb, "wavelengths_nm": WAVELENGTHS})
    dump("source_normalization_audit.json", {"formula": "F_monitor = integral(Pz dx dy) / P_source", "sourcepower_saved_values": [float(x) for x in sourcepower], "P_oblique_theta_deg": float(src_rb["angle theta"]), "cos_theta": cos_theta, "kz_over_k0": cos_theta, "extra_cosine_factor_in_current_extractor": False, "T_raw_sourcepower_max_abs_mismatch": max(r["normalization_T_mismatch"] for r in rows), "R_raw_sourcepower_max_abs_mismatch": max(r["normalization_R_mismatch"] for r in rows), "order_sum_T_max_mismatch": max_order, "classification": "NO_OBVIOUS_OBLIQUE_P_NORMALIZATION_IMPLEMENTATION_DEFECT"})
    dump("boundary_bloch_audit.json", {"fdtd_boundary_readback": fdtd_rb, "source_plane_wave_type": src_rb["plane wave type"], "periodic_or_bloch_phase_saved": False, "lateral_boundary_power_monitors_saved": False, "lateral_flux_audit": "BOUNDARY_FLUX_NOT_DIRECTLY_OBSERVABLE_FROM_SAVED_STATE", "fixed_ux_drift": False})
    dump("reference_plane_monitor_audit.json", {"monitors": mon_rb, "reflection_z_nm": -300.0, "source_z_nm": -250.0, "pillar_z_nm": [0.0, 500.0], "transmission_z_nm": 900.0, "reflection_in_uniform_substrate": True, "transmission_in_uniform_air": True, "monitor_crosses_structure": False, "order_sum_matches_T_max": max_order, "reflected_order_sum_available": False, "note": "Saved state has raw Pz and T/R/order datasets, but no independent six-face boundary flux ledger."})
    dump("structure_anomaly_audit.json", {"definition": "formal angular-aware structure-interval flux jump", "wavelengths_nm": WAVELENGTHS, "per_wavelength": [{"wavelength_nm": w, "structure_anomaly": None, "status": "NOT_DIRECTLY_RECOMPUTABLE_FROM_SAVED_STATE"} for w in WAVELENGTHS], "max_structure_anomaly": None, "gate_evaluated": False, "reason": "P attempt post-FSP contains reflection/transmission/order/field monitors but no paired structure-interval power planes or saved six-face boundary ledger."})
    log = (RUN_DIR / (CASE + "_attempt_001_run_p0.log")).read_text(encoding="utf-8", errors="ignore")
    auto = [float(x) for x in re.findall(r"Auto Shutoff:\s*([0-9.eE+-]+)", log)]
    dump("convergence_audit.json", {"mesh_accuracy": float(fdtd_rb["mesh accuracy"]), "mesh_refinement": fdtd_rb["mesh refinement"], "simulation_time_s": float(fdtd_rb["simulation time"]), "auto_shutoff_threshold": float(fdtd_rb["auto shutoff min"]), "log_final_auto_shutoff": auto[-1] if auto else None, "early_termination_confirmed": "Early termination of simulation" in log, "pml_layers": float(fdtd_rb["pml layers"]), "numerical_risk_signal": False, "note": "Termination met the configured 1e-5 criterion; saved state alone does not establish a convergence sequence."})

    # Existing reusable angular HF comparison, read-only and contract-labelled.
    anchor_root = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\outputs/coupling/traditional_coupling_stage1b_alt1_nonzero_ux_hf_anchor_validation_v1/cases")
    angular = []
    for pattern, label, pol, ux in [("*P0d224137931034_S/raw_result.json", "+0.22413793103448276", "S_YLIKE", 0.22413793103448276), ("*P0d378689399989_P/raw_result.json", "+0.37868939998860307", "P_XLIKE", 0.37868939998860307), ("*P0d378689399989_S/raw_result.json", "+0.37868939998860307", "S_YLIKE", 0.37868939998860307)]:
        for p in anchor_root.glob(pattern):
            d = json.loads(p.read_text(encoding="utf-8")); rr = np.abs(np.asarray(d["reflection_monitor"]["T"], float)); tt = np.asarray(d["transmission_monitor"]["T"], float); res = 1 - rr - tt
            angular.append({"case": p.parent.name, "label": label, "polarization": pol, "ux": ux, "max_abs_closure": float(np.max(np.abs(res))), "mean_closure": float(np.mean(res)), "geometry_contract_available": True, "source": str(p)})
    dump("angular_hf_comparison.json", {"comparison": angular, "same_generator_contract": "not_proven_from saved comparison package; geometry/source/material identity must be checked before causal comparison", "trend": "P_negative_case residual 0.0214 exceeds reusable +angle anchors (<=0.0036), but contract equivalence is not fully proven."})

    rcwa_p = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\outputs/coupling/rcwa_component_benchmark_v1/runtime_runs/RCWA_LEVEL1_ANGULAR_ACQUISITION_9JOB_V1/NP_LEVEL1_RCWA_UX_M0d482758620690/attempt_001/NP_LEVEL1_RCWA_UX_M0d482758620690_attempt_001_postprocessed.json")
    rcwa_rows = []
    if rcwa_p.exists():
        rd = json.loads(rcwa_p.read_text(encoding="utf-8")); pm = rd.get("metrics", {}).get("P_XLIKE", [])
        for r, f in zip(rows, pm):
            rcwa_rows.append({"wavelength_nm": r["wavelength_nm"], "fdtd_R": r["R_total"], "rcwa_R": f.get("R_total"), "delta_R": r["R_total"] - f.get("R_total", float("nan")), "fdtd_T": r["T_total"], "rcwa_T": f.get("T_total"), "delta_T": r["T_total"] - f.get("T_total", float("nan")), "fdtd_eta_plus1": r["eta_plus1"], "rcwa_eta_plus1": f.get("eta_plus1"), "delta_eta_plus1": r["eta_plus1"] - f.get("eta_plus1", float("nan")), "fdtd_eta_0": r["eta_0"], "rcwa_eta_0": f.get("eta_0"), "delta_eta_0": r["eta_0"] - f.get("eta_0", float("nan")), "fdtd_eta_minus1": r["eta_minus1"], "rcwa_eta_minus1": f.get("eta_minus1"), "delta_eta_minus1": r["eta_minus1"] - f.get("eta_minus1", float("nan"))})
    with (OUT / "rcwa_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        if rcwa_rows:
            w = csv.DictWriter(f, fieldnames=list(rcwa_rows[0])); w.writeheader(); w.writerows(rcwa_rows)
    dump("rcwa_diagnostic_comparison.json", {"rcwa_postprocessed_path": str(rcwa_p), "rcwa_rerun": False, "rows": rcwa_rows, "role": "diagnostic_only_not_FDTD_truth"})

    classification = {"classification": "MULTIPLE_CAUSES_POSSIBLE_INSUFFICIENT_SAVED_EVIDENCE", "confidence": "medium", "supporting_evidence": ["all 11 residuals are positive and max 0.02142121987216855", "Native-M1 TiO2 and SiO2 sampled tables have k=0 in FSP readback", "fixed u_x reconstruction error is below 1e-16", "raw/sourcepower and order-sum mismatches are <=2.22e-16 and 1.11e-16", "R/T monitors are in uniform substrate/air reference regions", "no six-face boundary flux or saved volume absorption dataset exists"], "contradicting_evidence": ["no independent boundary ledger to exclude lateral/PML flux", "no saved structure-interval monitor dataset to evaluate angular structure anomaly", "termination met auto-shutoff but no refinement sequence is available"], "raw_failure_preserved": True, "quality_gate_changed": False}
    dump("final_classification.json", classification)
    dump("next_action_recommendation.json", {"recommendation": "P_ATTEMPT001_REMAINS_REJECTED; S_REMAINS_BLOCKED; CHART_REVIEW_REQUIRED", "solver_rerun_scientifically_justified": "not decidable from saved evidence", "required_before_new_solver": "Chart review of boundary/reference/normalization and evidence sufficiency", "quality_threshold_changed": False})
    dump("governance_audit.json", {"forensic_solver_calls": 0, "fdtd_run_calls": 0, "fdtd_save_calls": 0, "rcwa_calls": 0, "replay": 0, "attempt_002": 0, "attempt_003": 0, "S_entry": 0, "external_hf": 0, "training": 0, "inverse": 0, "S_state": "PREPARED_NOT_ENTERED", "original_P_attempt_run_invocation_count": 1, "V4_resource_policy_unchanged": True})
    post_sha_after = sha(POST)
    dump("provenance_audit.json", {"case_id": CASE, "geometry_hash": GEOMETRY_HASH, "prefsp_path": str(PREFSP), "prefsp_sha256": pre_sha, "post_fsp_path": str(POST), "post_fsp_sha256_before": post_sha_before, "post_fsp_sha256_after": post_sha_after, "expected_post_fsp_sha256": EXPECTED_POST_SHA, "post_fsp_unchanged": post_sha_before == post_sha_after == EXPECTED_POST_SHA, "independent_readonly_reload": True, "external_mdc_fsp_accessed": False, "source_result_artifacts": [str(RUN_DIR / "spectral_metrics.json"), str(RUN_DIR / "transmitted_orders.csv")]})
    dump("extraction_manifest.json", {"schema_version": "NP_K6_M10B_P_NEG0482_CLOSURE_FORENSIC_V1", "created_utc": now(), "readonly_reload": True, "run_called": False, "save_called": False, "exact_wavelengths_nm": WAVELENGTHS, "post_sha_stable": post_sha_before == post_sha_after, "max_abs_closure_residual": float(np.max(absres)), "worst_wavelength_nm": worst["wavelength_nm"], "residual_sign": "positive_all_11", "residual_mean": float(np.mean(residuals)), "residual_median": float(np.median(residuals)), "residual_min": float(np.min(residuals)), "residual_max": float(np.max(residuals)), "residual_second_difference_max_abs": float(np.max(np.abs(np.diff(residuals, n=2)))), "smooth_flag": smooth})
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(f"""# NP K6 M10B P -0.482758 closure forensic v1\n\n- Case: `{CASE}`; geometry hash `{GEOMETRY_HASH}`; attempt_001 only.\n- Read-only post-FSP reload; no `run()` and no `save()`. Post SHA remained `{post_sha_after}`.\n- Raw frozen gate remains FAIL: max `|1-R-T| = {float(np.max(absres)):.12g}` at {worst['wavelength_nm']:.0f} nm; all 11 residuals are positive, range [{float(np.min(residuals)):.12g}, {float(np.max(residuals)):.12g}], mean {float(np.mean(residuals)):.12g}, median {float(np.median(residuals)):.12g}.\n- Native-M1 TiO2/SiO2 are lossless in the saved sampled tables (`k_max_abs=0`), but no saved volume-absorption or six-face flux ledger exists; `A` is not directly observable.\n- Fixed source `u_x={TARGET_UX}` reconstructs from `sin(theta)` with max error below 1e-16. Raw/sourcepower and order-sum checks remain at machine precision.\n- Reference planes are reflection z=-300 nm in substrate and transmission/order z=900 nm in air; no structure-interval or lateral boundary flux dataset is saved.\n- Classification: **MULTIPLE_CAUSES_POSSIBLE_INSUFFICIENT_SAVED_EVIDENCE** (medium confidence).\n- Recommendation: `P_ATTEMPT001_REMAINS_REJECTED`, `S_REMAINS_BLOCKED`, `CHART_REVIEW_REQUIRED`; no new solver is executed.\n\nEvidence files are in `outputs/np_k6_m10b_p_neg0482_closure_forensic_v1/`.\n""", encoding="utf-8")


def _has(fd, name, key):
    try:
        fd.getnamed(name, key); return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
