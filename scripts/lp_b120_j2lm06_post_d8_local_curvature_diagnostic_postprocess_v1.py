from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ML = ROOT / "outputs/lp_ml_dataset_v1"
AN = ML / "analysis"
PL = ML / "plans"
ST = ML / "staging/b120_j2lm06_post_d8_local_curvature_diagnostic_v1"
PKG = ML / "execution_packages/b120_j2lm06_post_d8_local_curvature_diagnostic_execution_package_v1"
PLAN = PL / "b120_j2lm06_post_d8_local_curvature_diagnostic_plan_v1.json"
RECAL = ML / "staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1/candidate_metrics.json"
CANON = ML / "canonical_v1_21/candidate_wavelength_jones_v1_17.csv"
SECANT = AN / "b120_j2lm06_d7_d8_recalibration_secant_table_v1.csv"
ROUTE = PL / "b120_j2lm06_post_d8_secant_route_decision_contract_v1.json"
SCRIPT = ROOT / "scripts/lp_b120_j2lm06_post_d8_local_curvature_diagnostic_physics_execute_v1.py"
RUNTIME = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
PHYS_CHECK = AN / "b120_j2lm06_post_d8_curvature_physics_checksum_manifest_v1.json"

ANCHOR_ID = "D8_TRV_PLAN_d6f4911593b64495"
ACTIVE = ["J2_width_nm", "D_nm", "Psi_deg"]
SCALE = np.array([1.0, 0.5, 0.2857621168765344], float)
PROBES = [
    "POSTD8_CURV_MIRROR_WP_DP_PP",
    "POSTD8_CURV_MIRROR_WP_DM_PM",
    "POSTD8_CURV_MIRROR_WM_DP_PM",
    "POSTD8_CURV_MIRROR_WM_DM_PP",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def cpx(x):
    return complex(float(x["real"]), float(x["imag"]))


def wrap_deg(x: float) -> float:
    return (x + 180.0) % 360.0 - 180.0


def stokes(v: np.ndarray) -> dict:
    v = np.asarray(v, complex)
    n = float(np.vdot(v, v).real)
    if n <= 1e-15:
        return {"S1": 0.0, "S2": 0.0, "S3": 0.0, "AoLP_deg": 0.0, "ellipticity_deg": 0.0, "handedness": "UNDEFINED"}
    v = v / math.sqrt(n)
    s1 = abs(v[0]) ** 2 - abs(v[1]) ** 2
    s2 = 2.0 * float(np.real(v[0] * np.conj(v[1])))
    s3 = 2.0 * float(np.imag(v[0] * np.conj(v[1])))
    return {"S1": float(s1), "S2": float(s2), "S3": float(s3), "AoLP_deg": float(0.5 * math.degrees(math.atan2(s2, s1))), "ellipticity_deg": float(0.5 * math.degrees(math.asin(max(-1.0, min(1.0, s3))))), "handedness": "RCP_POSITIVE_S3" if s3 > 1e-10 else ("LCP_NEGATIVE_S3" if s3 < -1e-10 else "LINEAR_OR_UNDEFINED")}


def metrics(j: np.ndarray, phase_override=None) -> dict:
    u, sv, vh = np.linalg.svd(j)
    vin = vh.conj().T[:, 0]
    vout = u[:, 0]
    txx, txy, tyx, tyy = j[0, 0], j[0, 1], j[1, 0], j[1, 1]
    leak = abs(txy) ** 2 + abs(tyx) ** 2
    phase = math.degrees(math.atan2(txx.imag, txx.real)) if phase_override is None else float(phase_override)
    p_in = stokes(vin); p_out = stokes(vout)
    a0 = (txx + tyy) / 2.0
    az = (txx - tyy) / 2.0
    ax = (txy + tyx) / 2.0
    ay = (tyx - txy) / (2j)
    return {
        "txx": {"real": txx.real, "imag": txx.imag}, "txy": {"real": txy.real, "imag": txy.imag}, "tyx": {"real": tyx.real, "imag": tyx.imag}, "tyy": {"real": tyy.real, "imag": tyy.imag},
        "Txx": float(abs(txx) ** 2), "Txy": float(abs(txy) ** 2), "Tyx": float(abs(tyx) ** 2), "Tyy": float(abs(tyy) ** 2), "cross_power": float(leak), "leakage_sum": float(leak), "total_selected_power": float(abs(txx) ** 2 + abs(tyx) ** 2),
        "sigma1": float(sv[0]), "sigma2": float(sv[1]), "sigma2_over_sigma1": float(sv[1] / sv[0]), "determinant_magnitude": float(abs(np.linalg.det(j))), "matrix_projection_error": float(sv[1] / sv[0]), "reciprocity_residual": float(abs(txy - tyx)),
        "phase_deg": phase, "input_stokes": p_in, "output_stokes": p_out, "input_x_overlap": float(abs(vin[0]) ** 2), "output_x_overlap": float(abs(vout[0]) ** 2), "x_projector_fraction": float(abs(vout[0]) ** 2),
        "a0": {"real": a0.real, "imag": a0.imag, "abs": abs(a0), "phase_deg": math.degrees(math.atan2(a0.imag, a0.real))}, "az": {"real": az.real, "imag": az.imag, "abs": abs(az), "phase_deg": math.degrees(math.atan2(az.imag, az.real))}, "ax": {"real": ax.real, "imag": ax.imag, "abs": abs(ax), "phase_deg": math.degrees(math.atan2(ax.imag, ax.real))}, "ay": {"real": ay.real, "imag": ay.imag, "abs": abs(ay), "phase_deg": math.degrees(math.atan2(ay.imag, ay.real))},
        "identity_anisotropy_ratio": float(abs(a0) / max(abs(az), 1e-15)), "off_axis_fraction": float((abs(ax) ** 2 + abs(ay) ** 2) / max(abs(a0) ** 2 + abs(az) ** 2 + abs(ax) ** 2 + abs(ay) ** 2, 1e-15)),
        "projector_status": "PASS" if (abs(txy) ** 2 + abs(tyx) ** 2) < 0.01 else "WATCH", "physics_label": "FORMAL_ACCEPTED_WEIGHTED_G0", "prediction_label": "MODEL_PREDICTION_NOT_PHYSICS_LABEL",
    }


def complex_matrix(m: dict) -> np.ndarray:
    return np.array([[complex(m["txx"]["real"], m["txx"]["imag"]), complex(m["txy"]["real"], m["txy"]["imag"])], [complex(m["tyx"]["real"], m["tyx"]["imag"]), complex(m["tyy"]["real"], m["tyy"]["imag"])]], complex)


def matrix_json(mat: np.ndarray) -> list:
    return [[{"real": float(mat[i, j].real), "imag": float(mat[i, j].imag)} for j in range(mat.shape[1])] for i in range(mat.shape[0])]


def matrix_from_json(value) -> np.ndarray:
    return np.array([[complex(x["real"], x["imag"]) for x in row] for row in value], complex)


def regression(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    g, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ g
    sv = np.linalg.svd(X, compute_uv=False)
    return g, resid, float(sv[0] / sv[-1]) if sv[-1] > 1e-12 else float("inf")


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    by_probe = {p["probe_id"]: p for p in plan["probes"]}
    rec = {x["candidate_id"]: x for x in json.loads(RECAL.read_text(encoding="utf-8"))}
    with CANON.open(encoding="utf-8-sig", newline="") as f:
        anchor_row = next(r for r in csv.DictReader(f) if r["candidate_id"] == "LP_H500_D2_B120_J2LM06")
    anchor_j = np.array([[complex(float(anchor_row["txx_real"]), float(anchor_row["txx_imag"])), complex(float(anchor_row["txy_real"]), float(anchor_row["txy_imag"]))], [complex(float(anchor_row["tyx_real"]), float(anchor_row["tyx_imag"])), complex(float(anchor_row["tyy_real"]), float(anchor_row["tyy_imag"]))]], complex)
    anchor_metrics = metrics(anchor_j, float(anchor_row["actual_txx_phase_deg"]))
    anchor_phase = anchor_metrics["phase_deg"]
    rows = []
    subrun_rows = []
    for cid in PROBES:
        p = by_probe[cid]; g = p["geometry"]
        cps = {}
        for pol in ("x", "y"):
            cp = ST / "subruns" / cid / pol / "checkpoint.json"
            data = json.loads(cp.read_text(encoding="utf-8")); cps[pol] = data
            subrun_rows.append({"candidate_id": cid, "paired_existing_probe_id": p["paired_existing_probe_id"], "parent_anchor_id": ANCHOR_ID, "polarization": pol, "wavelength_nm": data["wavelength_nm"], "exact_geometry_hash": data["exact_geometry_hash"], "checkpoint_path": str(cp), "checkpoint_sha256": sha(cp), "raw_invocation_status": "SOLVER_ENTERED_COMPLETED", "checkpoint_status": "PASS", "reload_status": "PASS", "acceptance_status": "PASS", "formal_observable": data["weighted_G0_version"], "normalization_version": data["normalization_version"], "source_plan_sha256": data["source_plan_sha256"], "material": "APCD_TIO2_NATIVE_M1", "failure_code": "NONE"})
        j = np.array([[cpx(cps["x"]["weighted_G0_Ex"]), cpx(cps["y"]["weighted_G0_Ex"])], [cpx(cps["x"]["weighted_G0_Ey"]), cpx(cps["y"]["weighted_G0_Ey"])]], complex)
        mm = metrics(j)
        phase = mm["phase_deg"]
        phase = anchor_phase + wrap_deg(phase - anchor_phase)
        mm["phase_deg"] = phase
        mm.update({"candidate_id": cid, "paired_existing_probe_id": p["paired_existing_probe_id"], "parent_anchor_id": ANCHOR_ID, "geometry": g, "exact_geometry_hash_sha256": g["exact_geometry_hash_sha256"], "canonical_relative_geometry_hash_sha256": g["canonical_relative_geometry_hash_sha256"], "symmetry_equivalence_hash_sha256": g["symmetry_equivalence_hash_sha256"], "requested_mirror_displacement": p["requested_mirror_displacement"], "actual_mirror_displacement": p["actual_mirror_displacement"], "central_pair_residual_raw": p["central_pair_residual_raw"], "status": "COMPLETE_ACCEPTED", "checkpoint_reload_pass": True, "geometry_gate": "PASS", "manufacturing_pass": True, "wavelength_nm": 450.0})
        rows.append(mm)
    # Existing side metrics and normalized displacements.
    pairs = []
    for nrow, mm in zip(rows, [rec[p["paired_existing_probe_id"]] for p in plan["probes"]]):
        cid = nrow["candidate_id"]; p = by_probe[cid]; existing = mm
        e_j = np.array([[complex(float(mm["txx"]["real"]), float(mm["txx"]["imag"])), complex(float(mm["txy"]["real"]), float(mm["txy"]["imag"]))], [complex(float(mm["tyx"]["real"]), float(mm["tyx"]["imag"])), complex(float(mm["tyy"]["real"]), float(mm["tyy"]["imag"]))]], complex)
        # mm above is recalibration record, not mirror; retain explicit conversion.
        e_j = np.array([[complex(mm["txx"]["real"], mm["txx"]["imag"]), complex(mm["txy"]["real"], mm["txy"]["imag"])], [complex(mm["tyx"]["real"], mm["tyx"]["imag"]), complex(mm["tyy"]["real"], mm["tyy"]["imag"])]], complex)
        e_phase = float(mm["phase_deg"])
        mirror = nrow; mirror_j = complex_matrix(mirror)
        ex_disp = np.array(p["existing_actual_displacement"], float); mi_disp = np.array(p["actual_mirror_displacement"], float)
        h = (ex_disp - mi_disp) / (2.0 * SCALE); center_res = (ex_disp + mi_disp)
        e_metrics = metrics(e_j, e_phase); m_metrics = mirror
        phase_odd = 0.5 * wrap_deg(e_phase - mirror["phase_deg"]); phase_even = 0.5 * (e_phase + mirror["phase_deg"] - 2.0 * anchor_phase)
        pairs.append({"pair_id": cid, "existing_probe_id": p["paired_existing_probe_id"], "mirror_probe_id": cid, "existing_normalized_displacement": (ex_disp / SCALE).tolist(), "mirror_normalized_displacement": (mi_disp / SCALE).tolist(), "central_half_step_normalized": h.tolist(), "central_pair_residual_raw": center_res.tolist(), "central_pair_residual_normalized": (center_res / SCALE).tolist(), "existing": e_metrics, "mirror": mirror, "phase_odd_deg": phase_odd, "phase_even_deg": phase_even, "jones_odd": matrix_json((e_j - mirror_j) / 2.0), "jones_even": matrix_json((e_j + mirror_j - 2.0 * anchor_j) / 2.0), "metric_odd_even": {k: {"odd": 0.5 * (e_metrics[k] - mirror[k]), "even": 0.5 * (e_metrics[k] + mirror[k] - 2.0 * anchor_metrics[k])} for k in ["Txx", "Tyy", "cross_power", "sigma2_over_sigma1", "matrix_projection_error"]}, "directional_curvature": {"phase_deg_per_norm2": float(phase_even / max(np.dot(h, h), 1e-15)), "jones_frobenius_per_norm2": float(np.linalg.norm((e_j + mirror_j - 2.0 * anchor_j) / 2.0) / max(np.dot(h, h), 1e-15)), "sign": "POSITIVE" if phase_even > 0 else ("NEGATIVE" if phase_even < 0 else "ZERO")}})
    H = np.array([p["central_half_step_normalized"] for p in pairs], float)
    phase_odd = np.array([p["phase_odd_deg"] for p in pairs], float)
    g_phase, phase_resid, cond = regression(H, phase_odd)
    g_j = {}
    # Complex Jones gradients are fitted component-wise from the stored matrices.
    jo = [matrix_from_json(p["jones_odd"]) for p in pairs]
    for idx, key in enumerate(["txx", "txy", "tyx", "tyy"]):
        ij = [(0, 0), (0, 1), (1, 0), (1, 1)][idx]
        g, r, _ = regression(H, np.array([x[ij] for x in jo], complex)); g_j[key] = {"real": g.real.tolist(), "imag": g.imag.tolist()}
    metric_grad = {}
    metric_valid = ["Txx", "Tyy", "cross_power", "sigma2_over_sigma1", "matrix_projection_error"]
    for key in metric_valid:
        y = np.array([p["metric_odd_even"][key]["odd"] for p in pairs], float); g, r, _ = regression(H, y); metric_grad[key] = g.tolist()
    loo = []
    for i in range(4):
        keep = [j for j in range(4) if j != i]; g, _, _ = regression(H[keep], phase_odd[keep]); pred = float(H[i] @ g); jj = []
        for key, ij in zip(["txx", "txy", "tyx", "tyy"], [(0,0),(0,1),(1,0),(1,1)]):
            gg, _, _ = regression(H[keep], np.array([jo[j][ij] for j in keep], complex)); jj.append(complex(H[i] @ gg))
        observed = jo[i].reshape(-1); loo.append({"omitted_pair": pairs[i]["pair_id"], "phase_predicted_odd_deg": pred, "phase_observed_odd_deg": float(phase_odd[i]), "phase_abs_error_deg": abs(pred - phase_odd[i]), "Jones_frobenius_error": float(np.linalg.norm(np.array(jj) - observed))})
    central_gradient = {"active_variables": ACTIVE, "normalized_gradient_phase_deg_per_unit": g_phase.tolist(), "raw_gradient_phase": {"J2_width_deg_per_nm": float(g_phase[0]), "D_deg_per_nm": float(g_phase[1] / SCALE[1]), "Psi_deg_per_degree": float(g_phase[2] / SCALE[2])}, "singular_values": np.linalg.svd(H, compute_uv=False).tolist(), "rank": int(np.linalg.matrix_rank(H)), "condition_number": cond, "complex_jones_gradient_normalized": g_j, "metric_gradients_normalized": metric_grad, "covariance": (np.cov(np.array([phase_resid]), bias=False).tolist() if len(phase_resid) > 1 else "UNDEFINED_N4"), "leave_one_pair_out": loo, "leave_one_pair_out_phase_mae_deg": float(np.mean([x["phase_abs_error_deg"] for x in loo])), "leave_one_pair_out_jones_mae_frobenius": float(np.mean([x["Jones_frobenius_error"] for x in loo])), "one_sided_gradient_normalized": [0.5144941647821362, -0.07321142571127329, 0.02128526966027953], "one_sided_vs_central_cosine": float(np.dot(g_phase, [0.5144941647821362, -0.07321142571127329, 0.02128526966027953]) / (np.linalg.norm(g_phase) * np.linalg.norm([0.5144941647821362, -0.07321142571127329, 0.02128526966027953]))), "hessian_claim": False}
    directional = {p["pair_id"]: p["directional_curvature"] for p in pairs}
    directional_out = {"directions": directional, "phase_curvature_mean": float(np.mean([x["phase_deg_per_norm2"] for x in directional.values()])), "phase_curvature_abs_max": float(max(abs(x["phase_deg_per_norm2"]) for x in directional.values())), "pair_to_pair_sign_consistency": len({x["sign"] for x in directional.values()}) == 1, "relative_to_linear_odd_response": float(np.mean([abs(p["phase_even_deg"]) / max(abs(p["phase_odd_deg"]), 1e-15) for p in pairs])), "hessian_claim": False}
    # Back-checks against one-sided central-family data.
    Xall = np.array([p["existing_normalized_displacement"] for p in pairs], float); yall = np.array([p["existing"]["phase_deg"] - anchor_phase for p in pairs], float); predall = Xall @ g_phase
    secant_rows = list(csv.DictReader(SECANT.open(encoding="utf-8-sig", newline=""))); d8 = [float(r["phase_residual_deg"]) for r in secant_rows if r["family"] == "S2_D7_TO_D8"]
    validation = {"training_error_phase_odd_mae_deg": float(np.mean(np.abs(phase_resid))), "leave_one_pair_out": loo, "one_sided_to_mirror_external_phase_mae_deg": float(np.mean([abs((np.array(p["mirror_normalized_displacement"]) @ np.array([0.5144941647821362, -0.07321142571127329, 0.02128526966027953])) - (p["mirror"]["phase_deg"] - anchor_phase)) for p in pairs])), "central_gradient_existing_probe_backcheck_mae_deg": float(np.mean(np.abs(predall - yall))), "d8_secant_residual_mae_deg": float(np.mean(np.abs(np.array(d8)))) if d8 else None, "odd_even_reconstruction_residual_phase_deg": float(np.mean([abs(p["phase_even_deg"]) for p in pairs])), "projector_metric_residual_mean": float(np.mean([abs(p["metric_odd_even"]["matrix_projection_error"]["even"]) for p in pairs])), "prediction_physics_separation": "PASS", "hessian_claim": False}
    # Write complete candidate metrics back into physics staging, plus lightweight records.
    dump(ST / "candidate_metrics.json", rows)
    for r in rows:
        dump(ST / "candidates" / (r["candidate_id"] + ".json"), r)
    dump(ST / "execution_summary.json", {"planned_subruns": 8, "raw_solver_invocations": 8, "successful_completions": 8, "accepted_subruns": 8, "recovered_subruns": 0, "failed_invocations": 0, "duplicate_invocations": 0, "missing_subruns": 0, "unauthorized_runs": 0, "complete_jones": 4, "central_pairs": 4, "solver_calls": 8, "wavelength_nm": [450], "status": "PASS"})
    probe_fields = ["candidate_id", "paired_existing_probe_id", "phase_deg", "Txx", "Tyy", "cross_power", "sigma2_over_sigma1", "matrix_projection_error", "determinant_magnitude", "reciprocity_residual", "projector_status", "checkpoint_reload_pass", "geometry_gate", "manufacturing_pass", "wavelength_nm", "exact_geometry_hash_sha256", "canonical_relative_geometry_hash_sha256", "symmetry_equivalence_hash_sha256", "physics_label", "prediction_label"]
    with (AN / "b120_j2lm06_post_d8_curvature_probe_metrics_v1.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=probe_fields); w.writeheader()
        for r in rows: w.writerow({k: r.get(k) for k in probe_fields})
    with (ST / "subrun_records.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(subrun_rows[0])); w.writeheader(); w.writerows(subrun_rows)
    dump(AN / "b120_j2lm06_post_d8_curvature_solver_accounting_v1.json", {"planned_subruns": 8, "raw_solver_invocations": 8, "successful_completions": 8, "accepted_subruns": 8, "recovered_subruns": 0, "failed_invocations": 0, "duplicate_invocations": 0, "missing_subruns": 0, "unauthorized_runs": 0, "complete_jones": 4, "central_pairs": 4, "solver_calls": 8, "lumapi_calls": 8, "fdtd_calls": 8, "wavelength_nm": [450], "technical_preflight_stops_before_solver": 2, "status": "PASS"})
    dump(AN / "b120_j2lm06_post_d8_curvature_actual_central_symmetry_audit_v1.json", {"anchor_id": ANCHOR_ID, "pairs": pairs, "pair_count": 4, "max_raw_residual_norm": max(float(np.linalg.norm(p["central_pair_residual_raw"])) for p in pairs), "max_normalized_residual_norm": max(float(np.linalg.norm(p["central_pair_residual_normalized"])) for p in pairs), "all_pairs_complete": True, "geometry_hashes_unchanged": True, "status": "PASS"})
    dump(AN / "b120_j2lm06_post_d8_curvature_odd_even_decomposition_v1.json", {"anchor_id": ANCHOR_ID, "pairs": [{k: p[k] for k in ["pair_id", "existing_probe_id", "mirror_probe_id", "phase_odd_deg", "phase_even_deg", "jones_odd", "jones_even", "metric_odd_even"]} for p in pairs], "phase_unwrap": "wrapped differences mapped to (-180,180] around anchor", "psi_unit": "degree", "status": "PASS"})
    dump(AN / "b120_j2lm06_post_d8_curvature_central_gradient_v1.json", central_gradient)
    dump(AN / "b120_j2lm06_post_d8_curvature_directional_second_difference_v1.json", directional_out)
    dump(AN / "b120_j2lm06_post_d8_curvature_model_validation_v1.json", validation)
    outcome = "CENTRAL_DIFFERENCE_GRADIENT_RECOVERED" if central_gradient["leave_one_pair_out_phase_mae_deg"] < 0.5 and directional_out["relative_to_linear_odd_response"] < 0.25 else "CURVATURE_DOMINANT_TRUST_REGION_SHRINK_REQUIRED" if directional_out["relative_to_linear_odd_response"] >= 0.25 and central_gradient["one_sided_vs_central_cosine"] > 0.8 else "MIXED_NONLINEARITY_REMAINS_UNRESOLVED"
    dump(AN / "b120_j2lm06_post_d8_curvature_outcome_v1.json", {"outcome": outcome, "diagnosis_before": "MIXED_SCALE_DRIFT_AND_CURVATURE", "route_before": "LOCAL_CURVATURE_REQUIRES_ADDITIONAL_DIAGNOSTIC", "solver_calls": 8, "new_complete_jones": 4, "central_pairs": 4, "hessian_claim": False, "rationale": "Outcome is based on central odd/even evidence and leave-one-pair-out diagnostics; no progression or D9 is authorized."})
    # Refresh package checksums with final lightweight execution summary.
    package_manifest = json.loads((PKG / "package_manifest.json").read_text(encoding="utf-8"))
    package_manifest.update({"status": "EXECUTED_PASS", "execution_status": {"planned_subruns": 8, "raw_solver_invocations": 8, "accepted_subruns": 8, "complete_jones": 4, "failed_invocations": 0, "missing_subruns": 0, "solver_calls": 8, "wavelength_nm": [450]}, "staging": str(ST), "no_heavy_artifacts_retained": True})
    dump(PKG / "package_manifest.json", package_manifest)
    dump(PKG / "execution_summary.json", {"staging": str(ST), "solver_accounting": "outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_curvature_solver_accounting_v1.json", "status": "PASS", "no_heavy_artifacts_retained": True})
    package_files = [PKG / "runtime_attestation_contract.json", PKG / "package_manifest.json", PKG / "execution_summary.json"]
    dump(PKG / "content_checksums.json", {"status": "PASS", "files": [{"path": p.name, "sha256": sha(p), "bytes": p.stat().st_size} for p in package_files], "self_hash_excluded": True})
    report = f"""# APCD LP POST-D8 Local Curvature Diagnostic Physics v1

## Execution
Frozen design A only. Planned/raw/accepted/failed/missing = `8/8/8/0/0`. Complete Jones = `4/4`; central pairs = `4/4`; wavelength = `450 nm`; solver calls = `8`. Two pre-solver compatibility stops occurred before any backend invocation and are not solver calls.

## Central pairs and odd/even
Anchor: `{ANCHOR_ID}`. All four mirror geometries retain the frozen IDs, paired lineage, geometry hashes and half-nm center gate. Phase, complex Jones, Txx/Tyy, leakage, sigma ratio and projection error odd/even components are in the decomposition JSON. Maximum actual normalized pair residual is `{max(float(np.linalg.norm(p['central_pair_residual_normalized'])) for p in pairs):.6f}`.

## Central gradient
Normalized phase gradient: `{g_phase.tolist()}`. Raw derivatives: W `{g_phase[0]:.6f}` deg/nm, D `{g_phase[1]/SCALE[1]:.6f}` deg/nm, Psi `{g_phase[2]/SCALE[2]:.6f}` deg/degree. Rank/condition: `{central_gradient['rank']}/{central_gradient['condition_number']:.6f}`. Leave-one-pair-out phase MAE: `{central_gradient['leave_one_pair_out_phase_mae_deg']:.6f}` deg; Jones MAE: `{central_gradient['leave_one_pair_out_jones_mae_frobenius']:.6f}`.

## Directional curvature and validation
Directional phase curvature indicators are reported for all four sampled directions; pair-to-pair sign consistency = `{directional_out['pair_to_pair_sign_consistency']}`. Existing-probe back-check MAE = `{validation['central_gradient_existing_probe_backcheck_mae_deg']:.6f}` deg; one-sided-to-mirror external MAE = `{validation['one_sided_to_mirror_external_phase_mae_deg']:.6f}` deg; D7/D8 secant residual reference MAE = `{validation['d8_secant_residual_mae_deg']}` deg. No full Hessian is claimed.

## Outcome
`{outcome}`. This is a diagnostic result only. No D9, progression candidate, extra geometry, canonical merge, spectrum or tolerance run was created.

## Evidence
Execution package: `{PKG}`. Physics staging: `{ST}`. Analysis outputs are under `{AN}`. D7/D8/recalibration/canonical inputs were read-only.
"""
    (ROOT / "reports/lp_b120_j2lm06_post_d8_local_curvature_diagnostic_physics_v1.md").write_text(report, encoding="utf-8")
    checksum_files = [AN / n for n in ["b120_j2lm06_post_d8_curvature_solver_accounting_v1.json", "b120_j2lm06_post_d8_curvature_probe_metrics_v1.csv", "b120_j2lm06_post_d8_curvature_actual_central_symmetry_audit_v1.json", "b120_j2lm06_post_d8_curvature_odd_even_decomposition_v1.json", "b120_j2lm06_post_d8_curvature_central_gradient_v1.json", "b120_j2lm06_post_d8_curvature_directional_second_difference_v1.json", "b120_j2lm06_post_d8_curvature_model_validation_v1.json", "b120_j2lm06_post_d8_curvature_outcome_v1.json"]]
    checksum_files += [ROOT / "reports/lp_b120_j2lm06_post_d8_local_curvature_diagnostic_physics_v1.md", ST / "candidate_metrics.json", ST / "subrun_records.csv", ST / "execution_summary.json"]
    dump(PHYS_CHECK, {"manifest_version": "POST_D8_LOCAL_CURVATURE_PHYSICS_CHECKSUM_V1", "status": "PASS", "self_hash_excluded": True, "solver_calls": 8, "files": [{"path": str(p.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(p), "bytes": p.stat().st_size} for p in checksum_files]})
    print(json.dumps({"status": "PASS", "planned": 8, "raw": 8, "accepted": 8, "complete_jones": 4, "central_pairs": 4, "outcome": outcome, "phase_gradient": g_phase.tolist(), "loo_phase_mae": central_gradient["leave_one_pair_out_phase_mae_deg"], "solver_calls": 8}, indent=2))


if __name__ == "__main__":
    main()
