"""Post-hoc amplitude/phase hybrid audit; reads frozen OOF predictions only."""
import csv
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TASK = "COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1"
OUT = ROOT / "reports" / "coupling" / TASK
POC = ROOT / "reports" / "coupling" / "COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1"
BASE = ROOT / "reports" / "coupling" / "PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1"
H1_PATH = ROOT / "reports" / "coupling" / "PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json"
H2_PATH = ROOT / "scripts" / "shared_fdtd" / "tools" / "pw_complex_floquet_state_v1.py"
EXPECTED_HEAD = "456cf707880e25283b325dad4b3fc5904aae58d1"
EPS_PHASE = 1e-8
TIE_ABS_TOL = 1e-12
SEEDS = (0, 1, 2)
WLS = tuple(range(440, 461))
ORDERS = tuple(range(-3, 4))
POLS = ("TE", "TM")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True,
                              allow_nan=False) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def build_hybrid(c0, c1, eps=EPS_PHASE):
    """Use C1 magnitudes and C0 unit phase; deterministic prediction-only fallback."""
    c0 = np.asarray(c0, dtype=np.complex128)
    c1 = np.asarray(c1, dtype=np.complex128)
    if c0.shape != c1.shape:
        raise ValueError("C0/C1 prediction alignment mismatch")
    a1 = np.abs(c1)
    a0 = np.abs(c0)
    c0_phase_defined = a0 >= float(eps)
    c1_phase_defined = a1 > 0.0
    use_c1_phase = (~c0_phase_defined) & c1_phase_defined
    use_fixed_phase = (~c0_phase_defined) & (~c1_phase_defined)
    unit = np.ones(c0.shape, dtype=np.complex128)
    unit[c0_phase_defined] = c0[c0_phase_defined] / a0[c0_phase_defined]
    unit[use_c1_phase] = c1[use_c1_phase] / a1[use_c1_phase]
    # `unit` remains fixed +1 where both saved complex predictions have undefined phase.
    hybrid = a1 * unit
    return hybrid, {
        "c0_phase_defined": c0_phase_defined,
        "used_c1_phase": use_c1_phase,
        "used_fixed_unit_phase": use_fixed_phase,
    }


def pearson(a, b):
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    if a.size != b.size or a.size < 2 or np.std(a) == 0.0 or np.std(b) == 0.0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _ranks(values):
    x = np.asarray(values, dtype=float).ravel()
    order = np.argsort(x, kind="mergesort")
    out = np.empty(x.size, dtype=float)
    i = 0
    while i < x.size:
        j = i + 1
        while j < x.size and x[order[j]] == x[order[i]]:
            j += 1
        out[order[i:j]] = 0.5 * (i + j - 1) + 1.0
        i = j
    return out


def spearman(a, b):
    return pearson(_ranks(a), _ranks(b))


def summarize(values):
    a = np.asarray(values, dtype=float).ravel()
    if a.size == 0 or not np.isfinite(a).all():
        raise ValueError("empty or non-finite metric array")
    return {
        "median": float(np.median(a)),
        "q95": float(np.quantile(a, 0.95)),
        "worst": float(np.max(a)),
        "max": float(np.max(a)),
        "min": float(np.min(a)),
    }


def state_detail(truth, pred, weak_fraction=0.01):
    truth = np.asarray(truth, dtype=np.complex128)
    pred = np.asarray(pred, dtype=np.complex128)
    at = np.abs(truth)
    ap = np.abs(pred)
    se = np.abs(pred - truth) ** 2
    amp_se = (ap - at) ** 2
    phase_se = np.maximum(se - amp_se, 0.0)
    denom = max(float(np.sum(at ** 2)), 1e-30)
    dphi = np.angle(pred * np.conj(truth))
    truth_weight = at ** 2
    pred_weight = ap ** 2
    mag_weight = at * ap
    common_sum = np.sum(mag_weight * np.exp(1j * dphi), axis=(-2, -1))
    common = np.angle(common_sum)
    dr = np.angle(np.exp(1j * (dphi - common[..., None, None])))
    aligned = pred * np.exp(-1j * common[..., None, None])
    aligned_sse = float(np.sum(np.abs(aligned - truth) ** 2))
    state_sse = float(np.sum(se))
    weak = at <= float(weak_fraction) * np.maximum(np.max(at, axis=(-2, -1), keepdims=True), 1e-30)
    strong = ~weak
    truth_phase_denom = max(float(np.sum(truth_weight)), 1e-30)
    pred_phase_denom = max(float(np.sum(pred_weight)), 1e-30)
    relative_denom = max(float(np.sum(mag_weight)), 1e-30)
    # A second relative-phase diagnostic fixes its phase weight to truth amplitude.
    common_truth = np.angle(np.sum(truth_weight * np.exp(1j * dphi), axis=(-2, -1)))
    dr_truth = np.angle(np.exp(1j * (dphi - common_truth[..., None, None])))
    return {
        "state": float(np.sqrt(state_sse / denom)),
        "amplitude": float(np.sqrt(float(np.sum(amp_se)) / denom)),
        "amplitude_sse_fraction": float(np.sum(amp_se) / max(float(np.sum(se)), 1e-30)),
        "phase_sse_fraction": float(np.sum(phase_se) / max(float(np.sum(se)), 1e-30)),
        "phase_weighted_rmse_rad": float(np.sqrt(np.sum(truth_weight * dphi ** 2) / truth_phase_denom)),
        "predicted_amplitude_weighted_phase_rmse_rad": float(np.sqrt(np.sum(pred_weight * dphi ** 2) / pred_phase_denom)),
        "circular_phase_chord_rmse": float(np.sqrt(np.sum(truth_weight * 2.0 * (1.0 - np.cos(dphi))) / truth_phase_denom)),
        "strong_phase_rmse_rad": float(np.sqrt(np.sum(truth_weight * dphi ** 2 * strong) / max(float(np.sum(truth_weight * strong)), 1e-30))),
        "weak_coordinate_fraction": float(np.mean(weak)),
        "weak_truth_energy_fraction": float(np.sum(truth_weight * weak) / denom),
        "predicted_phase_truth_energy_coverage_eps": float(np.sum(truth_weight * (ap >= EPS_PHASE)) / truth_phase_denom),
        "relative_phase_rmse_rad": float(np.sqrt(np.sum(mag_weight * dr ** 2) / relative_denom)),
        "relative_phase_truth_weighted_rmse_rad": float(np.sqrt(np.sum(truth_weight * dr_truth ** 2) / truth_phase_denom)),
        "oracle_common_phase_rmse_rad": float(np.sqrt(np.sum(truth_weight * common[..., None, None] ** 2) / truth_phase_denom)),
        "oracle_common_phase_aligned_state": float(np.sqrt(aligned_sse / denom)),
        "oracle_common_phase_explained_sse_fraction": float((state_sse - aligned_sse) / max(state_sse, 1e-30)),
    }


def h1_metrics(truth_c, pred_c, truth_eta, truth_abs, truth_ps, pred_ps, weights, threshold):
    modal = weights * np.sum(np.abs(pred_c) ** 2, axis=-1)
    eta_pred = modal / np.maximum(modal.sum(axis=-1, keepdims=True), 1e-30)
    abs_pred = eta_pred * pred_ps[..., None]
    rows = []
    for g in range(len(truth_c)):
        row = state_detail(truth_c[g], pred_c[g])
        mask = truth_abs[g] >= threshold
        row.update({
            "case_id": str(g),
            "routing": float(np.sqrt(np.mean((eta_pred[g] - truth_eta[g]) ** 2))),
            "absolute": float(np.sqrt(np.mean((abs_pred[g] - truth_abs[g]) ** 2))),
            "thresholded_relative": float(np.median(np.abs(abs_pred[g][mask] - truth_abs[g][mask]) / np.maximum(truth_abs[g][mask], 1e-30))) if np.any(mask) else 0.0,
            "pscale": float(np.sqrt(np.mean(((pred_ps[g] - truth_ps[g]) / np.maximum(truth_ps[g], 1e-30)) ** 2))),
        })
        rows.append(row)
    return rows, eta_pred, abs_pred


def summarize_rows(rows):
    keys = [k for k, v in rows[0].items() if k != "case_id" and isinstance(v, (int, float, np.number))]
    return {k: summarize([r[k] for r in rows]) for k in keys}


def get_gate_values(authority):
    return authority["chart_numeric_authority"]


def evaluate_arm(label, seed_predictions, mean_prediction, data, threshold, gate_chart):
    per_geometry, eta, abs_order = h1_metrics(
        data["c"], mean_prediction, data["eta"], data["absolute"],
        data["pscale"], data["pscale_pred"], data["weights"], threshold)
    metric_summary = summarize_rows(per_geometry)
    per_seed = {}
    seed_state_medians = []
    for seed_i, seed in enumerate(SEEDS):
        seed_rows, seed_eta, _ = h1_metrics(
            data["c"], seed_predictions[seed_i], data["eta"], data["absolute"],
            data["pscale"], data["pscale_pred"], data["weights"], threshold)
        seed_summ = summarize_rows(seed_rows)
        rho_r = pearson(data["eta"], seed_eta)
        rho_p = pearson(data["pscale"], data["pscale_pred"])
        per_seed[str(seed)] = {"metrics": seed_summ, "routing_pearson": rho_r, "pscale_pearson": rho_p}
        seed_state_medians.append(seed_summ["state"]["median"])
    rho_route = pearson(data["eta"], eta)
    rho_pscale = pearson(data["pscale"], data["pscale_pred"])
    seed_std = float(np.std(seed_state_medians))
    gates = {
        "state": metric_summary["state"]["median"] <= gate_chart["state_relative_rmse"]["median_max"] and metric_summary["state"]["q95"] <= gate_chart["state_relative_rmse"]["q95_max"],
        "routing": metric_summary["routing"]["median"] <= gate_chart["routing_eta_rmse"]["median_max"] and metric_summary["routing"]["q95"] <= gate_chart["routing_eta_rmse"]["q95_max"] and rho_route >= gate_chart["routing_eta_rmse"]["pearson_min"],
        "absolute_order": metric_summary["absolute"]["median"] <= gate_chart["absolute_order_source_normalized_rmse"]["median_max"] and metric_summary["absolute"]["q95"] <= gate_chart["absolute_order_source_normalized_rmse"]["q95_max"],
        "thresholded_relative": metric_summary["thresholded_relative"]["median"] <= gate_chart["thresholded_absolute_order_relative"]["median_max"] and metric_summary["thresholded_relative"]["q95"] <= gate_chart["thresholded_absolute_order_relative"]["q95_max"],
        "pscale_total": metric_summary["pscale"]["median"] <= gate_chart["total_power_relative"]["median_max"] and metric_summary["pscale"]["q95"] <= gate_chart["total_power_relative"]["q95_max"] and rho_pscale >= gate_chart["total_power_relative"]["pearson_min"],
        "seed_stability": seed_std <= gate_chart["seed_state_median_std_max"],
    }
    result = {
        "summary": metric_summary,
        "routing_pearson": rho_route,
        "pscale_pearson": rho_pscale,
        "seed_state_medians": {str(s): float(v) for s, v in zip(SEEDS, seed_state_medians)},
        "seed_state_median_std": seed_std,
        "gates": gates,
        "H1": "GATES_ATTAINED_POST_HOC" if all(gates.values()) else "FAIL",
        "per_geometry": per_geometry,
        "per_seed": per_seed,
    }
    return result


def build_h2_factor(h2_path):
    spec = importlib.util.spec_from_file_location("frozen_h2_hybrid_audit", str(h2_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factors = np.asarray([
        [[module._mode(m, 0, float(wl), 1.0, 1, pol)["power_z_per_abs_e2"] for pol in POLS] for m in ORDERS]
        for wl in WLS
    ], dtype=float)
    if factors.shape != (21, 7, 2) or not np.isfinite(factors).all() or np.any(factors <= 0.0):
        raise ValueError("frozen H2 factor shape/value check failed")
    return module, factors


def h2_reconstruct(cp, pscale, factors):
    cp = np.asarray(cp, dtype=np.complex128)
    norm = np.sum(factors[None, ...] * np.abs(cp) ** 2, axis=(-2, -1))
    if np.any(norm <= 0.0) or np.any(~np.isfinite(norm)) or np.any(pscale <= 0.0):
        raise ValueError("non-positive H2 normalization or predicted P_scale; no clipping allowed")
    scale = np.sqrt(pscale / np.maximum(norm, 1e-30))
    physical = cp * scale[..., None, None]
    order_power = np.sum(factors[None, ...] * np.abs(physical) ** 2, axis=-1)
    total = np.sum(order_power, axis=-1)
    eta = order_power / np.maximum(total[..., None], 1e-30)
    return {"physical": physical, "scale": scale, "order_power": order_power, "total": total, "eta": eta}


def atomic_npz(path, **arrays):
    path = Path(path)
    tmp = Path(str(path) + ".tmp.npz")
    np.savez_compressed(tmp, **arrays)
    os.replace(str(tmp), str(path))


def write_csv(path, rows):
    if not rows:
        raise ValueError("refusing to write empty CSV: " + str(path))
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finalize_persisted_outputs(result, audit, protocol, protocol_path):
    """Repair/report already-persisted comparison outputs without recomputing metrics."""
    audit["analysis_script_sha256"] = sha256(__file__)
    audit["protocol_sha256"] = sha256(protocol_path)
    audit["input_sha256"] = protocol["input_sha256"]
    audit["authority_sha256"] = protocol["authority_sha256"]
    prior_repair = audit.get("reporting_repair")
    repair_events = audit.setdefault("reporting_repair_events", [])
    if prior_repair and not repair_events:
        repair_events.append(prior_repair)
    repair_events.append({
        "type": "quantitative_report_enrichment_from_persisted_results",
        "comparison_metrics_recomputed": False,
        "existing_results_json_reused": True,
        "solver_or_training_invocations": 0,
    })
    audit["reporting_repair"] = {
        "type": "non_scientific_output_manifest_and_report_fix",
        "comparison_metrics_recomputed": False,
        "existing_results_json_reused": True,
        "solver_or_training_invocations": 0,
        "reason": "reused the completed persisted comparison while finalizing artifact hashes and adding numeric phase, tail, paired-delta, H2 and P_scale summaries",
    }
    write_json(OUT / "audit.json", audit)
    (OUT / (TASK + ".md")).write_text(make_report(result, audit, protocol), encoding="utf-8")
    (OUT / "CONTINUATION.md").write_text(make_continuation(result, protocol), encoding="utf-8")
    tracked_paths = [
        ROOT / "scripts" / "coupling_ml" / "coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py",
        ROOT / "tests" / "coupling" / "test_coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py",
    ]
    manifest = {}
    for path in sorted([p for p in OUT.iterdir() if p.is_file() and p.name != "artifact_hashes.json"] + tracked_paths):
        manifest[str(path.relative_to(ROOT))] = sha256(path)
    write_json(OUT / "artifact_hashes.json", manifest)
    write_json(OUT / "checkpoint.json", {
        "task": TASK, "phase": "COMPLETE_POST_HOC_AUDIT_REVIEW_READY",
        "starting_head": EXPECTED_HEAD, "analysis_sha256": sha256(__file__),
        "protocol_sha256": sha256(protocol_path),
        "comparison_rows": 672, "hybrid_configs": 1, "model_fit_invocations": 0,
        "solver_invocations": 0, "gpu_runner_invocations": 0,
        "recovery": "Read CONTINUATION.md, protocol.json, results.json, audit.json and artifact_hashes.json. Do not rerun if results.json exists.",
    })
    manifest[str((OUT / "checkpoint.json").relative_to(ROOT))] = sha256(OUT / "checkpoint.json")
    write_json(OUT / "artifact_hashes.json", manifest)
    print("HYBRID_AUDIT_FINALIZED_FROM_PERSISTED_RESULTS", json.dumps({
        "result_sha256": sha256(OUT / "results.json"),
        "audit_sha256": sha256(OUT / "audit.json"),
        "manifest_sha256": sha256(OUT / "artifact_hashes.json"),
        "analysis_sha256": sha256(__file__),
        "metric_recompute": False,
    }, separators=(",", ":")), flush=True)


def load_and_validate(protocol):
    if git("branch", "--show-current") != protocol["branch"]:
        raise RuntimeError("branch changed after protocol freeze")
    if git("rev-parse", "HEAD") != protocol["starting_head"]:
        raise RuntimeError("HEAD changed after protocol freeze; inspect authority, do not reset")
    if git("rev-list", "--left-right", "--count", "HEAD...@{u}").split() != ["0", "0"]:
        raise RuntimeError("upstream changed after protocol freeze")
    if sha256(__file__) != protocol["analysis_script_sha256"]:
        raise RuntimeError("analysis script hash differs from frozen protocol")
    for rel, digest in protocol["input_sha256"].items():
        if sha256(ROOT / rel) != digest:
            raise RuntimeError("frozen input changed: " + rel)
    for rel, digest in protocol["authority_sha256"].items():
        if sha256(ROOT / rel) != digest:
            raise RuntimeError("authority changed: " + rel)
    truth = np.load(BASE / "dataset_truth_32g.npz", allow_pickle=False)
    saved = np.load(POC / "oof_predictions.npz", allow_pickle=False)
    history = np.load(BASE / "oof_predictions_20g_32g.npz", allow_pickle=False)
    ids = truth["case_ids"].tolist()
    if ids != history["case_ids"].tolist() or len(ids) != 32:
        raise RuntimeError("geometry ID alignment mismatch")
    expected_shape = (3, 32, 21, 7, 2)
    for key in ["C0_seed", "C1_seed", "FULL_seed"]:
        if saved[key].shape != expected_shape:
            raise RuntimeError("prediction shape mismatch: " + key)
    if saved["P_scale_predicted"].shape != (32, 21):
        raise RuntimeError("P_scale shape mismatch")
    if not np.array_equal(history["32g_pred_pscale"], saved["P_scale_predicted"]):
        raise RuntimeError("POC P_scale differs from frozen OOF P_scale")
    if not np.array_equal(saved["FULL_seed"], history["32g_pred_c_hat_seed"]):
        raise RuntimeError("historical FULL predictions changed")
    if not np.allclose(saved["C0_mean"], np.mean(saved["C0_seed"], axis=0), atol=1e-12, rtol=0.0):
        raise RuntimeError("saved C0 mean is not the arithmetic seed mean")
    if not np.allclose(saved["C1_mean"], np.mean(saved["C1_seed"], axis=0), atol=1e-12, rtol=0.0):
        raise RuntimeError("saved C1 mean is not the arithmetic seed mean")
    pscale_true = np.asarray(truth["P_scale"], dtype=float)
    pscale_pred = np.asarray(saved["P_scale_predicted"], dtype=float)
    if not np.allclose(history["P_scale_truth_32g"], pscale_true, atol=1e-12, rtol=0.0):
        raise RuntimeError("truth P_scale schema parity failed")
    for key in ["C0_seed", "C1_seed", "FULL_seed"]:
        if not np.isfinite(saved[key].real).all() or not np.isfinite(saved[key].imag).all():
            raise RuntimeError("non-finite saved prediction: " + key)
    if not np.isfinite(pscale_pred).all() or np.any(pscale_pred <= 0.0):
        raise RuntimeError("invalid frozen P_scale prediction; no clipping permitted")
    data = {
        "ids": ids,
        "c": np.asarray(truth["C_hat"], dtype=np.complex128),
        "pscale": pscale_true,
        "pscale_pred": pscale_pred,
        "eta": np.asarray(truth["eta"], dtype=float),
        "absolute": np.asarray(truth["absolute_order_power"], dtype=float),
        "weights": np.asarray(truth["modal_weights"], dtype=float),
        "saved": saved,
        "history": history,
        "truth_pscale_vs_absolute_order_sum_max_abs": float(np.max(np.abs(pscale_true - np.sum(truth["absolute_order_power"], axis=-1)))),
    }
    if data["c"].shape != (32, 21, 7, 2) or data["weights"].shape != (32, 21, 7):
        raise RuntimeError("truth schema dimensions mismatch")
    if not np.isfinite(data["c"].real).all() or not np.isfinite(data["c"].imag).all():
        raise RuntimeError("non-finite C_PW truth")
    return data


def paired_deltas(arms, pairs):
    result = {}
    metric_keys = ["state", "amplitude", "phase_sse_fraction", "phase_weighted_rmse_rad",
                   "predicted_amplitude_weighted_phase_rmse_rad", "circular_phase_chord_rmse",
                   "relative_phase_rmse_rad", "relative_phase_truth_weighted_rmse_rad",
                   "routing", "absolute", "thresholded_relative", "pscale"]
    for cand, base in pairs:
        name = cand + "_minus_" + base
        result[name] = {}
        arows = arms[cand]["per_geometry"]
        brows = arms[base]["per_geometry"]
        for metric in metric_keys:
            d = np.asarray([arows[i][metric] - brows[i][metric] for i in range(32)], dtype=float)
            result[name][metric] = {
                "delta": summarize(d),
                "wins": int(np.sum(d < -TIE_ABS_TOL)),
                "ties": int(np.sum(np.abs(d) <= TIE_ABS_TOL)),
                "losses": int(np.sum(d > TIE_ABS_TOL)),
                "paired_geometry_count": 32,
                "tie_abs_tolerance": TIE_ABS_TOL,
            }
    return result


def main():
    os.chdir(ROOT)
    protocol_path = OUT / "protocol.json"
    if not protocol_path.exists():
        raise RuntimeError("frozen protocol missing; no result calculation allowed")
    if (OUT / "results.json").exists():
        protocol = read_json(protocol_path)
        load_and_validate(protocol)
        result = read_json(OUT / "results.json")
        audit = read_json(OUT / "audit.json")
        required = ["hybrid_oof_predictions.npz", "per_geometry.csv", "per_wavelength.csv", "per_order.csv", "seed_metrics.csv", "fallback_by_geometry.csv", "pscale_by_geometry.csv", "h2_reconstruction.csv"]
        missing = [name for name in required if not (OUT / name).is_file()]
        if missing:
            raise RuntimeError("persisted result is incomplete; missing " + ",".join(missing))
        finalize_persisted_outputs(result, audit, protocol, protocol_path)
        return
    protocol = read_json(protocol_path)
    data = load_and_validate(protocol)
    saved = data["saved"]
    c0 = np.asarray(saved["C0_seed"], dtype=np.complex128)
    c1 = np.asarray(saved["C1_seed"], dtype=np.complex128)
    full = np.asarray(saved["FULL_seed"], dtype=np.complex128)
    hybrid = np.empty_like(c0)
    c1_fallback = np.zeros(c0.shape, dtype=bool)
    fixed_fallback = np.zeros(c0.shape, dtype=bool)
    c0_defined = np.zeros(c0.shape, dtype=bool)
    for si in range(3):
        hybrid[si], masks = build_hybrid(c0[si], c1[si], EPS_PHASE)
        c1_fallback[si] = masks["used_c1_phase"]
        fixed_fallback[si] = masks["used_fixed_unit_phase"]
        c0_defined[si] = masks["c0_phase_defined"]
    if not np.allclose(np.abs(hybrid), np.abs(c1), atol=1e-14, rtol=1e-12):
        raise RuntimeError("hybrid failed to preserve per-seed C1 coordinate magnitudes")
    hybrid_mean = np.mean(hybrid, axis=0)
    means = {
        "FULL": np.mean(full, axis=0),
        "C0": np.mean(c0, axis=0),
        "C1": np.mean(c1, axis=0),
        "HYBRID": hybrid_mean,
    }
    seeds = {"FULL": full, "C0": c0, "C1": c1, "HYBRID": hybrid}
    gate_chart = get_gate_values(read_json(H1_PATH))
    threshold = float(gate_chart["thresholded_absolute_order_relative"]["significance_threshold"])
    arms = {}
    for label in ["FULL", "C0", "C1", "HYBRID"]:
        arms[label] = evaluate_arm(label, seeds[label], means[label], data, threshold, gate_chart)

    # Reconfirm the old outputs with the exact already-frozen H1 path before interpreting hybrid deltas.
    poc_results = read_json(POC / "results.json")
    h1_authority = read_json(BASE / "PW_K6_FROZEN_FORWARD_H1_32G_V1.json")
    baseline_parity = {}
    field_map = {
        "state": "state_relative_rmse",
        "routing": "routing_eta_rmse",
        "absolute": "absolute_order_source_normalized_rmse",
        "thresholded_relative": "thresholded_absolute_order_relative_median",
        "pscale": "total_power_relative_rmse",
    }
    for label, original in [("FULL", h1_authority["metrics"]), ("C0", poc_results["arms"]["C0"]["summary"]), ("C1", poc_results["arms"]["C1"]["summary"])]:
        diffs = {}
        for metric, source_key in field_map.items():
            ref = original[source_key] if label == "FULL" else original[metric]
            for stat in ["median", "q95", "max"]:
                value = arms[label]["summary"][metric][stat]
                refvalue = ref[stat]
                diffs[metric + "." + stat] = float(value - refvalue)
                if abs(value - refvalue) > 1e-12:
                    raise RuntimeError("frozen baseline H1 parity failed: " + label + "/" + metric + "/" + stat)
        baseline_parity[label] = {"max_abs_delta": max(abs(x) for x in diffs.values()), "deltas": diffs, "tolerance": 1e-12}

    pairs = [("HYBRID", "C0"), ("HYBRID", "C1"), ("HYBRID", "FULL"), ("C1", "C0"), ("C0", "FULL")]
    paired = paired_deltas(arms, pairs)
    h2, factors = build_h2_factor(H2_PATH)
    h2_rows = []
    h2_arrays = {}
    for label, pred_mean in means.items():
        key = (label, "MEAN")
        h2_arrays[key] = h2_reconstruct(pred_mean, data["pscale_pred"], factors)
    for label, pred_seed in seeds.items():
        for si, seed in enumerate(SEEDS):
            key = (label, str(seed))
            h2_arrays[key] = h2_reconstruct(pred_seed[si], data["pscale_pred"], factors)
    for (label, seed), rec in h2_arrays.items():
        closure = rec["total"] - data["pscale_pred"]
        h2_rows.append({
            "model": label, "seed": seed,
            "max_abs_total_power_closure": float(np.max(np.abs(closure))),
            "max_relative_total_power_closure": float(np.max(np.abs(closure) / np.maximum(data["pscale_pred"], 1e-30))),
            "max_abs_scale_factor": float(np.max(rec["scale"])),
            "min_scale_factor": float(np.min(rec["scale"])),
            "mean_scale_factor": float(np.mean(rec["scale"])),
            "routing_pearson_vs_truth": pearson(data["eta"], rec["eta"]),
            "max_abs_order_power_vs_c1": None,
            "max_abs_routing_vs_c1": None,
        })
    h2_lookup = {(row["model"], row["seed"]): row for row in h2_rows}
    h2_compare = {}
    for seed in ["MEAN", "0", "1", "2"]:
        h = h2_arrays[("HYBRID", seed)]
        b = h2_arrays[("C1", seed)]
        order_delta = np.abs(h["order_power"] - b["order_power"])
        eta_delta = np.abs(h["eta"] - b["eta"])
        total_delta = np.abs(h["total"] - b["total"])
        h2_lookup[("HYBRID", seed)]["max_abs_order_power_vs_c1"] = float(np.max(order_delta))
        h2_lookup[("HYBRID", seed)]["max_abs_routing_vs_c1"] = float(np.max(eta_delta))
        h2_compare[seed] = {
            "max_abs_order_power_delta": float(np.max(order_delta)),
            "max_abs_routing_delta": float(np.max(eta_delta)),
            "max_abs_total_power_delta": float(np.max(total_delta)),
            "max_abs_scale_factor_delta": float(np.max(np.abs(h["scale"] - b["scale"]))),
        }

    # Fallback is computed over paired seeds and coordinates; power share uses the frozen H2 modal coefficients.
    a1_seed = np.abs(c1)
    power_weight = factors[None, None, ...]
    total_amp = float(np.sum(a1_seed))
    unscaled_h2_power = power_weight * a1_seed ** 2
    unscaled_h2_total = np.sum(unscaled_h2_power, axis=(-2, -1))
    physical_scale_for_a1 = np.sqrt(data["pscale_pred"][None, ...] / np.maximum(unscaled_h2_total, 1e-30))
    physical_h2_power = unscaled_h2_power * physical_scale_for_a1[..., None, None] ** 2
    total_h2_weighted_power = float(np.sum(physical_h2_power))
    fallback_masks = {"C1_phase": c1_fallback, "fixed_unit": fixed_fallback}
    fallback_summary = {
        "total_coordinates": int(c0.size),
        "c0_phase_eps": EPS_PHASE,
        "c0_phase_defined_count": int(np.sum(c0_defined)),
        "c0_phase_fallback_count": int(np.sum(~c0_defined)),
        "fallback_c1_phase_count": int(np.sum(c1_fallback)),
        "fallback_fixed_unit_count": int(np.sum(fixed_fallback)),
        "fallback_frequency": float(np.mean(~c0_defined)),
        "fallback_amplitude_share_of_c1": float(np.sum(a1_seed[~c0_defined]) / max(total_amp, 1e-30)),
        "fallback_physical_h2_power_share": float(np.sum(physical_h2_power * (~c0_defined)) / max(total_h2_weighted_power, 1e-30)),
        "c1_fallback_amplitude_share": float(np.sum(a1_seed[c1_fallback]) / max(total_amp, 1e-30)),
        "fixed_fallback_amplitude_share": float(np.sum(a1_seed[fixed_fallback]) / max(total_amp, 1e-30)),
        "c1_fallback_physical_h2_power_share": float(np.sum(physical_h2_power * c1_fallback) / max(total_h2_weighted_power, 1e-30)),
        "fixed_fallback_physical_h2_power_share": float(np.sum(physical_h2_power * fixed_fallback) / max(total_h2_weighted_power, 1e-30)),
    }
    fallback_geometry = []
    for gi, gid in enumerate(data["ids"]):
        mask = ~c0_defined[:, gi]
        c1mask = c1_fallback[:, gi]
        fixedmask = fixed_fallback[:, gi]
        amp = a1_seed[:, gi]
        pw = physical_h2_power[:, gi]
        fallback_geometry.append({
            "case_id": gid,
            "fallback_count": int(np.sum(mask)),
            "fallback_frequency": float(np.mean(mask)),
            "fallback_amplitude_share": float(np.sum(amp[mask]) / max(float(np.sum(amp)), 1e-30)),
            "fallback_physical_h2_power_share": float(np.sum(pw[mask]) / max(float(np.sum(pw)), 1e-30)),
            "c1_phase_fallback_count": int(np.sum(c1mask)),
            "fixed_unit_fallback_count": int(np.sum(fixedmask)),
        })

    geometry_rows = []
    for label in ["FULL", "C0", "C1", "HYBRID"]:
        for row in arms[label]["per_geometry"]:
            geometry_rows.append({"model": label, "case_id": data["ids"][int(row["case_id"])], **{k: v for k, v in row.items() if k != "case_id"}})
    wavelength_rows = []
    order_rows = []
    worst_locations = {}
    for label, pred in means.items():
        modal = data["weights"] * np.sum(np.abs(pred) ** 2, axis=-1)
        eta = modal / np.maximum(modal.sum(axis=-1, keepdims=True), 1e-30)
        abs_order = eta * data["pscale_pred"][..., None]
        for gi, gid in enumerate(data["ids"]):
            for wi, wl in enumerate(WLS):
                truth_slice = data["c"][gi, wi]
                pred_slice = pred[gi, wi]
                phase = state_detail(truth_slice, pred_slice)
                mask = data["absolute"][gi, wi] >= threshold
                wavelength_rows.append({
                    "model": label, "case_id": gid, "wavelength_nm": wl,
                    "state_relative_rmse": phase["state"], "amplitude_relative_rmse": phase["amplitude"],
                    "phase_weighted_rmse_rad": phase["phase_weighted_rmse_rad"],
                    "predicted_amplitude_weighted_phase_rmse_rad": phase["predicted_amplitude_weighted_phase_rmse_rad"],
                    "relative_phase_rmse_rad": phase["relative_phase_rmse_rad"],
                    "routing_eta_rmse": float(np.sqrt(np.mean((eta[gi, wi] - data["eta"][gi, wi]) ** 2))),
                    "absolute_order_rmse": float(np.sqrt(np.mean((abs_order[gi, wi] - data["absolute"][gi, wi]) ** 2))),
                    "thresholded_relative_median": float(np.median(np.abs(abs_order[gi, wi, mask] - data["absolute"][gi, wi, mask]) / np.maximum(data["absolute"][gi, wi, mask], 1e-30))) if np.any(mask) else 0.0,
                    "pscale_relative_abs_error": float(abs(data["pscale_pred"][gi, wi] - data["pscale"][gi, wi]) / max(data["pscale"][gi, wi], 1e-30)),
                })
            for oi, order in enumerate(ORDERS):
                truth_slice = data["c"][gi, :, oi, :]
                pred_slice = pred[gi, :, oi, :]
                den = max(float(np.sum(np.abs(truth_slice) ** 2)), 1e-30)
                modal_order = modal[gi, :, oi]
                order_rows.append({
                    "model": label, "case_id": gid, "order_m": order,
                    "state_relative_rmse": float(np.sqrt(np.sum(np.abs(pred_slice - truth_slice) ** 2) / den)),
                    "amplitude_relative_rmse": float(np.sqrt(np.sum((np.abs(pred_slice) - np.abs(truth_slice)) ** 2) / den)),
                    "routing_eta_rmse": float(np.sqrt(np.mean((eta[gi, :, oi] - data["eta"][gi, :, oi]) ** 2))),
                    "absolute_order_rmse": float(np.sqrt(np.mean((abs_order[gi, :, oi] - data["absolute"][gi, :, oi]) ** 2))),
                    "predicted_modal_power_sum": float(np.sum(modal_order)),
                })
    # Rebuild worst locations with an explicit map.
    worst_locations = {}
    for label in means:
        worst_locations[label] = {}
        cand = [r for r in wavelength_rows if r["model"] == label]
        for metric in ["state_relative_rmse", "relative_phase_rmse_rad", "routing_eta_rmse", "absolute_order_rmse"]:
            worst_locations[label][metric] = [
                {k: x[k] for k in ["case_id", "wavelength_nm", metric]}
                for x in sorted(cand, key=lambda r: r[metric], reverse=True)[:5]
            ]
        cand_order = [r for r in order_rows if r["model"] == label]
        worst_locations[label]["order_state"] = [
            {k: x[k] for k in ["case_id", "order_m", "state_relative_rmse"]}
            for x in sorted(cand_order, key=lambda r: r["state_relative_rmse"], reverse=True)[:5]
        ]

    pscale_geometry = []
    pscale_rel = []
    for gi, gid in enumerate(data["ids"]):
        pt = data["pscale"][gi]
        pp = data["pscale_pred"][gi]
        rel = (pp - pt) / np.maximum(pt, 1e-30)
        pn = pp / max(float(np.sum(pp)), 1e-30)
        tn = pt / max(float(np.sum(pt)), 1e-30)
        pscale_rel.append(float(np.sqrt(np.mean(rel ** 2))))
        pscale_geometry.append({
            "case_id": gid,
            "relative_rmse": float(np.sqrt(np.mean(rel ** 2))),
            "mean_signed_relative_error": float(np.mean(rel)),
            "mean_predicted_over_truth_scale_ratio": float(np.mean(pp) / max(float(np.mean(pt)), 1e-30)),
            "truth_spectral_min": float(np.min(pt)), "truth_spectral_max": float(np.max(pt)),
            "predicted_spectral_min": float(np.min(pp)), "predicted_spectral_max": float(np.max(pp)),
            "within_geometry_spectral_pearson": pearson(pt, pp),
            "unit_sum_spectral_shape_rmse": float(np.sqrt(np.mean((pn - tn) ** 2))),
        })
    pscale_overlap = {}
    for label in means:
        state_e = [r["state"] for r in arms[label]["per_geometry"]]
        route_e = [r["routing"] for r in arms[label]["per_geometry"]]
        pscale_overlap[label] = {
            "pearson_pscale_relrmse_vs_state": pearson(pscale_rel, state_e),
            "spearman_pscale_relrmse_vs_state": spearman(pscale_rel, state_e),
            "pearson_pscale_relrmse_vs_routing": pearson(pscale_rel, route_e),
            "spearman_pscale_relrmse_vs_routing": spearman(pscale_rel, route_e),
        }
    pscale_rank = sorted(pscale_geometry, key=lambda r: r["relative_rmse"], reverse=True)
    pscale_data = {
        "diagnostic_only": True,
        "truth_and_prediction_shape": [32, 21],
        "prediction_same_as_frozen_oof_branch": True,
        "p_scale_truth_vs_sum_absolute_order_power_max_abs": data["truth_pscale_vs_absolute_order_sum_max_abs"],
        "truth_min_max": [float(np.min(data["pscale"])), float(np.max(data["pscale"]))],
        "prediction_min_max": [float(np.min(data["pscale_pred"])), float(np.max(data["pscale_pred"]))],
        "geometry_relative_rmse_summary": summarize(pscale_rel),
        "worst_geometries": pscale_rank[:8],
        "best_geometries": sorted(pscale_geometry, key=lambda r: r["relative_rmse"])[:5],
        "overlap_correlations": pscale_overlap,
        "interpretation": "P_scale is compared in its frozen stored scale. Unit-sum spectral shape and mean scale ratio are diagnostics only; no truth-fitted rescaling or retraining is applied.",
    }

    # Paired per-seed summaries retain fold/seed matching and do not treat wavelengths as independent.
    seed_rows = []
    for label in ["FULL", "C0", "C1", "HYBRID"]:
        for seed in SEEDS:
            e = arms[label]["per_seed"][str(seed)]
            row = {"model": label, "seed": seed, "routing_pearson": e["routing_pearson"], "pscale_pearson": e["pscale_pearson"]}
            for metric, stats in e["metrics"].items():
                for stat, value in stats.items():
                    row[metric + "_" + stat] = value
            seed_rows.append(row)

    h2_consistency = {
        "h2_source_sha256": sha256(H2_PATH),
        "power_formula": "sum over orders and TE/TM of frozen power_z_per_abs_e2 * abs(C_hat_coordinate)^2; global physical scale sqrt(predicted P_scale / unscaled modal-power sum)",
        "phase_cross_term_check": "the frozen modal-power path is additive in per-order TE/TM coordinate magnitudes; no TE/TM or inter-order cross term is used after projection. The projection's coefficient solve is upstream and is not rerun.",
        "hybrid_per_seed_coordinate_magnitude_max_abs_delta_vs_c1": float(np.max(np.abs(np.abs(hybrid) - np.abs(c1)))),
        "hybrid_vs_c1_power_by_mean_or_seed": h2_compare,
        "mean_aggregation_note": "seedwise hybrids are formed first, then arithmetic-mean C_hat is used for the original H1 summary; squaring this mean can differ from C1 because seed phases differ, even though each paired seed has identical magnitudes.",
        "all_physical_totals_closed_to_shared_predicted_pscale": all(r["max_abs_total_power_closure"] <= 1e-12 for r in h2_rows),
        "maximum_total_power_closure_abs": max(r["max_abs_total_power_closure"] for r in h2_rows),
        "maximum_total_power_closure_relative": max(r["max_relative_total_power_closure"] for r in h2_rows),
    }

    result = {
        "schema": TASK + "_RESULTS_V1",
        "status": "COMPLETE_POST_HOC_DEVELOPMENT_AUDIT",
        "comparison_scope": {"geometries": 32, "wavelengths_nm": list(WLS), "rows": 672, "orders_m": list(ORDERS), "polarizations": list(POLS), "seeds": list(SEEDS)},
        "models": arms,
        "paired_geometry_deltas": paired,
        "baseline_parity": baseline_parity,
        "fallback": fallback_summary,
        "h2_consistency": h2_consistency,
        "pscale_diagnostic": pscale_data,
        "tails": {gid: {label: next(r for r in arms[label]["per_geometry"] if data["ids"][int(r["case_id"])] == gid) for label in arms} for gid in ["K6V1_S31", "K6V1_S33", "K6V1_EXT08"]},
        "worst_locations": worst_locations,
        "post_hoc_development_limitation": "This combination was constructed from held-out OOF predictions after the C0/C1 POC. It is development evidence only, not independent confirmatory validation and does not grant production admission.",
        "zero_training": True,
        "zero_solver": True,
        "new_hf": 0,
        "gpu_runner": 0,
        "reserve_cases": 0,
        "inverse_search": False,
    }

    # Persist the derived hybrid states, masks, summaries and recovery evidence.
    atomic_npz(OUT / "hybrid_oof_predictions.npz", hybrid_seed=hybrid, hybrid_mean=hybrid_mean,
              P_scale_predicted=data["pscale_pred"], used_c1_phase=c1_fallback,
              used_fixed_unit_phase=fixed_fallback, c0_phase_defined=c0_defined)
    write_csv(OUT / "per_geometry.csv", geometry_rows)
    write_csv(OUT / "per_wavelength.csv", wavelength_rows)
    write_csv(OUT / "per_order.csv", order_rows)
    write_csv(OUT / "seed_metrics.csv", seed_rows)
    write_csv(OUT / "fallback_by_geometry.csv", fallback_geometry)
    write_csv(OUT / "pscale_by_geometry.csv", pscale_geometry)
    write_csv(OUT / "h2_reconstruction.csv", h2_rows)
    write_json(OUT / "results.json", result)

    audit = {
        "status": "PASS",
        "protocol_sha256": sha256(protocol_path),
        "analysis_script_sha256": sha256(__file__),
        "input_sha256": protocol["input_sha256"],
        "authority_sha256": protocol["authority_sha256"],
        "starting_head": protocol["starting_head"],
        "branch": protocol["branch"],
        "prediction_alignment": {"case_ids_match_truth": True, "C0_C1_FULL_shape": [3, 32, 21, 7, 2], "P_scale_shape": [32, 21], "seedwise_pairing": True, "order_mapping": list(ORDERS), "polarization_mapping": list(POLS)},
        "baseline_h1_parity": baseline_parity,
        "zero_training": True, "model_fit_invocations": 0,
        "zero_solver": True, "solver_entries": 0, "gpu_runner_entries": 0,
        "new_hf": 0, "reserve_cases": 0, "inverse_search": False, "runner_development": False,
        "leakage_audit": {"heldout_truth_used_in_hybrid_or_fallback": False, "heldout_truth_used_for_h1_and_diagnostics_only": True, "hybrid_source_is_only_paired_oof_predictions": True, "candidate_count": 1, "mixed_candidate_search": False, "post_hoc_development_only": True},
        "fallback": fallback_summary,
        "truth_pscale_vs_order_sum_max_abs": data["truth_pscale_vs_absolute_order_sum_max_abs"],
        "h2_consistency": h2_consistency,
        "pscale_diagnostic": "existing frozen OOF branch only; no fit, clipping, or rescaling",
        "rows": {"per_geometry": len(geometry_rows), "per_wavelength": len(wavelength_rows), "per_order": len(order_rows), "seed_metrics": len(seed_rows), "pscale_by_geometry": len(pscale_geometry), "h2_reconstruction": len(h2_rows)},
    }
    write_json(OUT / "audit.json", audit)

    report = make_report(result, audit, protocol)
    (OUT / (TASK + ".md")).write_text(report, encoding="utf-8")
    continuation = make_continuation(result, protocol)
    (OUT / "CONTINUATION.md").write_text(continuation, encoding="utf-8")

    manifest = {}
    tracked_paths = [
        ROOT / "scripts" / "coupling_ml" / "coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py",
        ROOT / "tests" / "coupling" / "test_coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py",
    ]
    for path in sorted([p for p in OUT.iterdir() if p.is_file() and p.name != "artifact_hashes.json"] + tracked_paths):
        manifest[str(path.relative_to(ROOT))] = sha256(path)
    write_json(OUT / "artifact_hashes.json", manifest)
    write_json(OUT / "checkpoint.json", {
        "task": TASK, "phase": "COMPLETE_POST_HOC_AUDIT_REVIEW_READY",
        "starting_head": EXPECTED_HEAD, "analysis_sha256": sha256(__file__),
        "protocol_sha256": sha256(protocol_path),
        "comparison_rows": 672, "hybrid_configs": 1, "model_fit_invocations": 0,
        "solver_invocations": 0, "gpu_runner_invocations": 0,
        "recovery": "Read CONTINUATION.md, protocol.json, results.json, audit.json and artifact_hashes.json. Do not rerun if results.json exists.",
    })
    # Manifest covers checkpoint; checkpoint deliberately does not embed the manifest hash.
    manifest[str((OUT / "checkpoint.json").relative_to(ROOT))] = sha256(OUT / "checkpoint.json")
    write_json(OUT / "artifact_hashes.json", manifest)
    print("HYBRID_AUDIT_COMPLETE", json.dumps({
        "models": {k: {"H1": v["H1"], "state": v["summary"]["state"], "routing": v["summary"]["routing"], "absolute": v["summary"]["absolute"], "pscale": v["summary"]["pscale"]} for k, v in arms.items()},
        "fallback": fallback_summary,
        "h2": h2_consistency,
        "result_sha256": sha256(OUT / "results.json"),
    }, separators=(",", ":")), flush=True)


def make_report(result, audit, protocol):
    def fmt_stats(x):
        return "{:.4g} / {:.4g} / {:.4g}".format(x["median"], x["q95"], x["worst"])
    def fmt_percent_stats(x):
        return "{:.2f}% / {:.2f}% / {:.2f}%".format(100*x["median"], 100*x["q95"], 100*x["worst"])
    def fmt_delta(x):
        d = x["delta"]
        return "{:.4g} / {:.4g} / {:.4g}".format(d["median"], d["q95"], d["worst"]), "{}/{}/{}".format(x["wins"], x["ties"], x["losses"])
    lines = [
        "# " + TASK, "",
        "## STATUS", "COMPLETE_POST_HOC_DEVELOPMENT_AUDIT. Gate attainment is reported only; no production admission is inferred.", "",
        "## AUTHORITY / GIT", "Starting HEAD `{}` on `{}`. The frozen C0/C1 continuation and POC, 32G truth/H1 package, existing LOGO folds, H1 authority and H2 source are hash-pinned in `protocol.json` and `audit.json`. Scope: 32 geometries × 21 wavelengths (672 rows), seven ordered diffraction orders and TE/TM coordinates, seeds 0/1/2.".format(protocol["starting_head"], protocol["branch"]), "",
        "## ZERO-SOLVER / ZERO-TRAINING ASSERTION", "No model fit, FDTD, GPU Runner, new HF, reserve, inverse search or platform development was run. Only saved OOF predictions were read and combined.", "",
        "## HYBRID DEFINITION / FALLBACK", "For each matching seed, geometry, wavelength, order and TE/TM coordinate: `A1=abs(C1)` and `u0=C0/abs(C0)`; `C_hybrid=A1*u0`. If `abs(C0)<1e-8`, use the saved C1 complex phase when its coordinate is nonzero; if both saved complex phases are undefined, use fixed `+1+0i`. The threshold is inherited from the frozen C0/C1 phase rule. No truth enters this construction. See `fallback_by_geometry.csv` for frequency and amplitude/H2-power share.", "",
        "## FACTORIZATION VALIDITY", "The frozen physical reconstruction uses the H2 per-coordinate power coefficient times `abs(C_hat)^2` and applies its existing single scale `sqrt(P_scale_pred / unscaled_modal_power)`. Hybrid coordinate magnitudes and per-seed normalization denominators match C1; no extra normalization or P_scale change was made. The official H1 state gate is evaluated on the arithmetic seed-mean raw C_hat, matching the frozen POC evaluation path. Mean H2 results are separately checked because squaring a phase-varying seed mean can change powers.", "",
        "## C0 / C1 / HYBRID ORIGINAL H1", "The table reports median / q95 / worst across the 32 geometries. H1 is conjunctive.", "",
        "| Arm | H1 | State | Routing | Absolute order | Thresholded relative | P_scale/total | Routing r | P_scale r | Seed std |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in ["FULL", "C0", "C1", "HYBRID"]:
        a = result["models"][label]
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {:.4f} | {:.4f} | {:.4f} |".format(
            label, a["H1"], fmt_stats(a["summary"]["state"]), fmt_stats(a["summary"]["routing"]),
            fmt_stats(a["summary"]["absolute"]), fmt_stats(a["summary"]["thresholded_relative"]),
            fmt_stats(a["summary"]["pscale"]), a["routing_pearson"], a["pscale_pearson"], a["seed_state_median_std"]))
    lines += ["", "Frozen gate limits are state median/q95 ≤0.50/0.80; routing ≤0.05/0.10 with Pearson ≥0.95; absolute order ≤0.05/0.10; thresholded-relative ≤0.30/0.75; P_scale/total ≤0.15/0.30 with Pearson ≥0.95; seed state-median standard deviation ≤0.03. The table shows only absolute-order and seed-stability attainment for HYBRID. C0 reproduces historical FULL to displayed precision; exact baseline parity is in `results.json`.", "",
        "C0 / historical FULL H1 metric differences are below 6e-10 in the maximum paired geometry gate metrics; the baseline parity checks are hash-pinned in `results.json`. Per-seed gate metrics are in `seed_metrics.csv`. The fixed OOF P_scale branch is shared by all arms. Paired deltas use the same 32 geometries; lower error is better, a negative candidate-minus-reference delta is an improvement, and win/tie/loss uses the frozen absolute tolerance. These paired geometries and their wavelength/seed records are dependent; no independent-sample significance claim is made.", "",
        "### Paired geometry deltas", "| Comparison | Metric | Median / q95 / worst Δ | Win / tie / loss |", "|---|---|---:|---:|"]
    paired_metrics = [
        ("state", "State"), ("routing", "Routing"), ("absolute", "Absolute order"),
        ("thresholded_relative", "Thresholded relative"), ("amplitude", "Amplitude"),
        ("phase_weighted_rmse_rad", "Truth-amplitude-weighted phase (rad)"),
        ("relative_phase_rmse_rad", "Cross-order relative phase (rad)"),
    ]
    for comparison in ["C1_minus_C0", "HYBRID_minus_C0", "HYBRID_minus_C1"]:
        for key, label in paired_metrics:
            delta, wtl = fmt_delta(result["paired_geometry_deltas"][comparison][key])
            lines.append("| {} | {} | {} | {} |".format(comparison.replace("_minus_", " − "), label, delta, wtl))
    lines += ["", "### Per-seed medians", "| Arm | Seed | State | Routing | Thresholded relative | Amplitude | Truth-weighted phase (rad) | Cross-order relative phase (rad) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for label in ["C0", "C1", "HYBRID"]:
        for seed, row in result["models"][label]["per_seed"].items():
            m = row["metrics"]
            lines.append("| {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(
                label, seed, m["state"]["median"], m["routing"]["median"], m["thresholded_relative"]["median"],
                m["amplitude"]["median"], m["phase_weighted_rmse_rad"]["median"], m["relative_phase_rmse_rad"]["median"]))
    lines += ["", "## AMPLITUDE / PHASE / RELATIVE-PHASE", "Amplitude error is `sqrt(sum((|C_hat|-|C_PW|)^2)/sum(|C_PW|^2))`. `phase_weighted_rmse_rad` uses fixed truth-amplitude-squared weights; `predicted_amplitude_weighted_phase_rmse_rad` changes with predicted amplitude and is not a phase-only comparison. Cross-order `relative_phase_rmse_rad` uses the frozen POC `|C_truth|*|C_prediction|` weights; the separate truth-weighted column fixes those weights. Common-phase removal uses held-out truth and is ORACLE DIAGNOSTIC only.", "",
        "| Arm | Amplitude med/q95/worst | Truth-weighted phase med/q95/worst (rad) | Predicted-amplitude-weighted phase med/q95/worst (rad) | Cross-order phase med/q95/worst (rad) | Truth-weighted relative phase med/q95/worst (rad) | Oracle common-phase SSE explained med/q95/worst |", "|---|---:|---:|---:|---:|---:|---:|"]
    for label in ["FULL", "C0", "C1", "HYBRID"]:
        s = result["models"][label]["summary"]
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            label, fmt_stats(s["amplitude"]), fmt_stats(s["phase_weighted_rmse_rad"]),
            fmt_stats(s["predicted_amplitude_weighted_phase_rmse_rad"]), fmt_stats(s["relative_phase_rmse_rad"]),
            fmt_stats(s["relative_phase_truth_weighted_rmse_rad"]), fmt_percent_stats(s["oracle_common_phase_explained_sse_fraction"])))
    lines += ["", "The summary phase-metric weight changes can reflect seed-mean phase reweighting by the amplitude branch: they do not mean the per-seed C0 phase predictor changed. HYBRID uses C0 per-seed phases except the recorded fallback. Oracle alignment is excluded from all H1 gates.", "",
        "## H2 POWER CONSISTENCY", "H2's frozen post-projection modal-power path sums the stored TE/TM coordinate powers and has no TE/TM or inter-order cross term after projection. The existing projection coefficient solve was not rerun. Physical reconstruction applies only its original global `sqrt(P_scale_pred / unscaled_modal_power)` factor.", "",
        "| Aggregation | Max order-power Δ vs C1 | Max routing Δ vs C1 | Max scale-factor Δ vs C1 | Max total-power Δ vs C1 |", "|---|---:|---:|---:|---:|"]
    for label in ["0", "1", "2", "MEAN"]:
        h = result["h2_consistency"]["hybrid_vs_c1_power_by_mean_or_seed"][label]
        lines.append("| {} | {:.3g} | {:.3g} | {:.3g} | {:.3g} |".format(label, h["max_abs_order_power_delta"], h["max_abs_routing_delta"], h["max_abs_scale_factor_delta"], h["max_abs_total_power_delta"]))
    lines += ["", "Each paired seed's hybrid magnitudes match C1 within {:.3g}; each seed's reconstructed order powers/routing match within floating-point roundoff. The required arithmetic seed-mean prediction is different: mean H2 order/routing changes are shown above, while total power still closes to the same shared predicted P_scale (max closure {:.3g} absolute, {:.3g} relative).".format(
            result["h2_consistency"]["hybrid_per_seed_coordinate_magnitude_max_abs_delta_vs_c1"], result["h2_consistency"]["maximum_total_power_closure_abs"], result["h2_consistency"]["maximum_total_power_closure_relative"]), "",
        "## TAIL ATTRIBUTION", "H1 aggregate values above cover all 32 geometries × 21 wavelengths. The following rows are the preselected geometry tails; FULL is omitted because its historical parity with C0 is separately retained in `results.json`.", "",
        "| Geometry | Arm | State | Routing | Absolute order | Thresholded relative | Amplitude | Truth-weighted phase (rad) | Cross-order relative phase (rad) | P_scale rel. RMSE |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for gid in ["K6V1_S31", "K6V1_S33", "K6V1_EXT08"]:
        for label in ["C0", "C1", "HYBRID"]:
            t = result["tails"][gid][label]
            lines.append("| {} | {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(
                gid, label, t["state"], t["routing"], t["absolute"], t["thresholded_relative"], t["amplitude"],
                t["phase_weighted_rmse_rad"], t["relative_phase_rmse_rad"], t["pscale"]))
    worst = result["worst_locations"]["HYBRID"]
    state_loc = worst["order_state"][0]
    routing_loc = worst["routing_eta_rmse"][0]
    absolute_loc = worst["absolute_order_rmse"][0]
    phase_loc = worst["relative_phase_rmse_rad"][0]
    lines += ["", "HYBRID worst state-by-order location: {} order {} (relative state RMSE {:.3f}); worst routing wavelength: {} at {} nm (RMSE {:.3f}); worst absolute-order wavelength: {} at {} nm (RMSE {:.3f}); worst relative-phase wavelength: {} at {} nm (RMSE {:.3f}). Full top-five locations for every arm are in `results.json` and `per_order.csv` / `per_wavelength.csv`. These are error associations, not causal attribution.".format(
            state_loc["case_id"], state_loc["order_m"], state_loc["state_relative_rmse"], routing_loc["case_id"], routing_loc["wavelength_nm"], routing_loc["routing_eta_rmse"],
            absolute_loc["case_id"], absolute_loc["wavelength_nm"], absolute_loc["absolute_order_rmse"], phase_loc["case_id"], phase_loc["wavelength_nm"], phase_loc["relative_phase_rmse_rad"]), "",
        "## P_SCALE DIAGNOSTIC", "The saved RBF KRR OOF prediction matches the POC frozen branch exactly, and its truth is consistent with the sum of absolute-order power to {:.3g} maximum absolute difference. No refit, rescaling, clipping or oracle P_scale entered H1.".format(result["pscale_diagnostic"]["p_scale_truth_vs_sum_absolute_order_power_max_abs"]), "",
        "| Geometry | Relative RMSE | Mean predicted/truth scale | Mean signed relative error | Unit-sum spectral shape RMSE | Within-geometry spectral Pearson |", "|---|---:|---:|---:|---:|---:|"]
    for item in result["pscale_diagnostic"]["worst_geometries"][:5]:
        lines.append("| {} | {:.4f} | {:.4f} | {:.4f} | {:.4f} | {:.4f} |".format(item["case_id"], item["relative_rmse"], item["mean_predicted_over_truth_scale_ratio"], item["mean_signed_relative_error"], item["unit_sum_spectral_shape_rmse"], item["within_geometry_spectral_pearson"]))
    p = result["pscale_diagnostic"]
    lines += ["", "Across geometries P_scale relative-RMSE median/q95/worst is {}; errors overlap with routing/state errors at Pearson/Spearman r = {:.3f}/{:.3f} for routing and {:.3f}/{:.3f} for state (HYBRID). These are attribution clues only. The worst scale error is S31; its spectral shape remains correlated but its absolute scale is substantially high.".format(
            fmt_stats(p["geometry_relative_rmse_summary"]), p["overlap_correlations"]["HYBRID"]["pearson_pscale_relrmse_vs_routing"],
            p["overlap_correlations"]["HYBRID"]["spearman_pscale_relrmse_vs_routing"], p["overlap_correlations"]["HYBRID"]["pearson_pscale_relrmse_vs_state"],
            p["overlap_correlations"]["HYBRID"]["spearman_pscale_relrmse_vs_state"]), "",
        "## LEAKAGE AUDIT", "One predeclared hybrid was formed only from same-fold/same-seed OOF predictions. Held-out truth was used for H1 and labeled diagnostics only; it did not choose C0/C1 by geometry/wavelength/order, set fallback, set a mixing weight or select among candidates. No scaler/PCA, retraining, candidate search or oracle P_scale entered the prediction path. Exact fold/seed alignment, one-candidate status and truth-use flags are in `audit.json`.", "",
        "## POST-HOC DEVELOPMENT LIMITATION", result["post_hoc_development_limitation"], "",
        "## ARTIFACTS / HASHES / COMMIT / PUSH", "The result, alignment, fallback masks, per-geometry/per-wavelength/per-order tables, H2 reconstruction, P_scale diagnostics, audit and continuation are hash-indexed by `artifact_hashes.json`. Commit and push state are recorded in the continuation after the exact allowlist commit.", "",
        "## NEXT — DO NOT EXECUTE", "The saved predictions support the power-side value of the C1 amplitude branch, but the HYBRID does not improve full state versus C0/FULL and still misses independent state and P_scale gates. A next proposal for review is a frozen objective that targets full complex-state performance while tracking amplitude and circular-phase losses separately, with seed-mean reconstruction included in the objective; retain the same independent P_scale branch. Any candidate would need prospective held-out geometry confirmation with predictions frozen before truth is revealed. This OOF hybrid is not confirmatory; no next experiment was run.", "",
    ]
    return "\n".join(lines)


def make_continuation(result, protocol):
    return """# COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1 Continuation

Read this file first, then `protocol.json`, `results.json`, `audit.json`, `checkpoint.json`, and `artifact_hashes.json` before recovery. Do not rely on chat history.

## Project and connection
Remote host: `DESKTOP-NNE313K`; user: `dell` (`desktop-nne313k\\dell`). Canonical project root: `D:\\project\\blue_apcd_microled_metasurface`. Formal worktree: `D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1`; branch `{branch}`; task starting HEAD `{head}`. Prefer LAN SSH `dell@192.168.1.107`; use NetBird `dell@100.81.105.58` if LAN is unavailable. Reuse the existing key without printing or changing credentials. Python environment for existing ML work is `N:\\anaconda_envs\\RCP_LCP\\python.exe`.

## Authority and scientific route
Read authority in this order: `reports/coupling/COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1/CONTINUATION.md`; `reports/coupling/COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1/CONTINUATION.md`, `protocol.json`, and `results.json`; frozen 32G dataset and H1 authority under `reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/`; existing LOGO fold manifest under `reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2/`; `reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json`; and `scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py` (frozen H2). Exact SHA-256 values are pinned in this task's `protocol.json` and `audit.json`.

Formal HF route remains integrated 3D periodic plane-wave FDTD for GaN + fixed top MDC + 237 nm spacer + ordered K6 NP + air; no bottom DBR or patterned Meta-MDC. The research sequence remains fixed-MDC K6 forward, then MDC–NP joint forward/inverse closure, then any multi-angle extension, with sparse 3D dipole certification only for a final candidate. This task is only an offline post-hoc representation audit on the existing 32-geometry, 440–460 nm, 1 nm OOF predictions, seeds 0/1/2. It performed ZERO TRAINING and ZERO SOLVER and grants no production admission.

## Result and task boundary
Exactly one hybrid was formed from paired saved predictions: `abs(C1)` with C0 per-seed phase, using the frozen `1e-8` C0 phase threshold and saved-C1/fixed-unit fallback. The same frozen OOF RBF KRR P_scale branch and original H2/H1 path were used. All candidate, gate, seed, tail, H2, fallback and P_scale measurements are in the report and `results.json`; split/leakage and run-boundary checks are in `audit.json`. Current result is post-hoc development evidence only; no confirmatory evaluation or follow-up experiment is authorized.

## Artifacts and recovery
Primary report: `COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1.md`. Outputs: `hybrid_oof_predictions.npz`, `per_geometry.csv`, `per_wavelength.csv`, `per_order.csv`, `seed_metrics.csv`, `fallback_by_geometry.csv`, `pscale_by_geometry.csv`, `h2_reconstruction.csv`, `results.json`, `audit.json`, `protocol.json`, and `artifact_hashes.json`. Code/test: `scripts/coupling_ml/coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py` and `tests/coupling/test_coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py`.

Recovery: verify hostname/user, worktree, branch, current HEAD/upstream, exact task commit/push state, and all hashes. If `results.json` exists, do not rerun metric computation or regenerate the hybrid; resume from the persisted outputs. Preserve unrelated dirty/untracked files. No solver, training, reserve, inverse search, Runner work, or production admission is authorized by this task.
""".format(branch=protocol["branch"], head=protocol["starting_head"])


if __name__ == "__main__":
    main()
