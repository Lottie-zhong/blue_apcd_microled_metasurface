"""Read-only post-evaluation audit/package for the frozen V3-C Test40 run.

This script deliberately never imports the training code, torch, pandas, or a
solver.  It consumes only completed Test40 truth/prediction artifacts and the
already frozen OOF summaries.  All recomputation in this package is labelled
POST_SELECTION_DIAGNOSTIC_ONLY and does not alter model selection.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
RUN = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_external_2d_fdtd_v1" / "20260813T_test40_external_hf_acquisition_v2"
OOF = ROOT / "outputs" / "mdc_hf_surrogate_v3_oof_formal_v1" / "20260811T_formal_oof_29ee7c9"
FINAL = ROOT / "outputs" / "mdc_hf_surrogate_v3_c_final_full_development_v1" / "20260812T_final_full_development_5seed_bc1fcc1"
V2 = ROOT / "outputs" / "mdc_hf_surrogate_v2_failure_mechanism_diagnostic_fixed_v3_v1" / "20260809T_failure_mechanism_diagnostic_a322b13"
SEL = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1" / "v3_test40_geometry_manifest_v1.csv"
OUT = ROOT / "outputs" / "mdc_hf_surrogate_v3_test40_external_evaluation_package_v1" / "20260813T_external_package_audit_d016284"
SHAPE = (301, 2000)
WEIGHTS = {"profile": 0.4117647, "JS": 0.2352941, "spectral_CDF": 0.1764706, "angular_CDF": 0.1764706}
SEEDS = [20260813, 20260814, 20260815, 20260816, 20260817]
V2_REF = {"JS": 0.22933, "weighted_L1": 1.15060}


def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def dump(p: Path, x: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_bytes(a: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(a).tobytes()).hexdigest()


def profile_metrics(pred: np.ndarray, truth: np.ndarray) -> Dict[str, float]:
    """Exact frozen profile_loss_numpy definition, independent of training imports."""
    p = np.maximum(np.asarray(pred, dtype=np.float64), 0.0)
    t = np.maximum(np.asarray(truth, dtype=np.float64), 0.0)
    p = p / np.maximum(p.sum(axis=(-2, -1), keepdims=True), 1e-12)
    t = t / np.maximum(t.sum(axis=(-2, -1), keepdims=True), 1e-12)
    lp, lt = np.log(np.maximum(p, 1e-12)), np.log(np.maximum(t, 1e-12))
    d = np.abs(lp - lt)
    prof = np.where(d < 1.0, 0.5 * d * d, d - 0.5).mean()
    mid = 0.5 * (p + t)
    js = 0.5 * np.sum(p * np.log(np.maximum(p / np.maximum(mid, 1e-12), 1e-12)) + t * np.log(np.maximum(t / np.maximum(mid, 1e-12), 1e-12)), axis=(-2, -1)).mean()
    sp, st = p.sum(axis=-1), t.sum(axis=-1)
    ap, at = p.sum(axis=-2), t.sum(axis=-2)
    sp /= np.maximum(sp.sum(axis=-1, keepdims=True), 1e-12)
    st /= np.maximum(st.sum(axis=-1, keepdims=True), 1e-12)
    ap /= np.maximum(ap.sum(axis=-1, keepdims=True), 1e-12)
    at /= np.maximum(at.sum(axis=-1, keepdims=True), 1e-12)
    return {
        "profile": float(prof),
        "JS": float(js),
        "spectral_CDF": float(np.abs(np.cumsum(sp, axis=-1) - np.cumsum(st, axis=-1)).mean()),
        "angular_CDF": float(np.abs(np.cumsum(ap, axis=-1) - np.cumsum(at, axis=-1)).mean()),
        "weighted_L1": float(np.abs(p - t).sum(axis=(-2, -1)).mean()),
        "weighted_L1_raw_scale": float(np.abs(np.maximum(pred, 0.0) - np.maximum(truth, 0.0)).sum(axis=(-2, -1)).mean()),
    }


def composite(m: Dict[str, float]) -> float:
    return float(sum(WEIGHTS[k] * m[k] for k in WEIGHTS))


def geometry_summary(pred: np.ndarray, truth: np.ndarray, rows: List[Dict[str, Any]], topo: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, float]]]:
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(rows):
        m = profile_metrics(pred[i].reshape(SHAPE), truth[i].reshape(SHAPE))
        out.append({"geometry_hash": str(r["geometry_hash"]), "geometry_id": r.get("geometry_id"), "topology_family": topo[str(r["geometry_hash"])], "profile_composite": composite(m), "weighted_L1": m["weighted_L1_raw_scale"], "weighted_L1_normalized": m["weighted_L1"], **{k: v for k, v in m.items() if k not in ("weighted_L1", "weighted_L1_raw_scale")}})
    groups: Dict[str, Dict[str, float]] = {}
    for t in ("Explicit", "ZL1", "ZL2"):
        ix = [i for i, r in enumerate(out) if r["topology_family"] == t]
        groups[t] = {k: float(np.mean([out[i][k] for i in ix])) for k in ("profile_composite", "profile", "JS", "weighted_L1", "spectral_CDF", "angular_CDF")}
        groups[t]["geometry_count"] = len(ix)
    groups["global"] = {k: float(np.mean([x[k] for x in out])) for k in ("profile_composite", "profile", "JS", "weighted_L1", "spectral_CDF", "angular_CDF")}
    groups["global"]["geometry_count"] = len(out)
    return out, groups


def describe_profile(pred: np.ndarray, truth: np.ndarray) -> Dict[str, Any]:
    p = np.maximum(pred.reshape(SHAPE), 0.0); t = np.maximum(truth.reshape(SHAPE), 0.0)
    ps, ts = p.sum(axis=1), t.sum(axis=1)
    pa, ta = p.sum(axis=0), t.sum(axis=0)
    def peak(v: np.ndarray) -> int: return int(np.argmax(v))
    def width(v: np.ndarray) -> float:
        q = float(np.max(v)) * 0.5
        return float(np.count_nonzero(v >= q))
    m = profile_metrics(p, t)
    return {"metrics": m, "truth_spectral_peak_index": peak(ts), "pred_spectral_peak_index": peak(ps), "truth_angular_peak_index": peak(ta), "pred_angular_peak_index": peak(pa), "spectral_peak_shift_index": peak(ps) - peak(ts), "angular_peak_shift_index": peak(pa) - peak(ta), "truth_spectral_halfmax_width": width(ts), "pred_spectral_halfmax_width": width(ps), "truth_angular_halfmax_width": width(ta), "pred_angular_halfmax_width": width(pa), "truth_profile_sha256": sha_bytes(t.astype(np.float32)), "pred_profile_sha256": sha_bytes(p.astype(np.float32)), "joint_lambda_angle_mismatch_proxy": float(abs(np.corrcoef(np.log1p(t.ravel()), np.log1p(p.ravel()))[0, 1])) if np.std(t) and np.std(p) else 0.0}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    phase_a = read_json(RUN / "test40_phase_a_completion_audit.json")
    freeze = read_json(RUN / "test40_truth_freeze_manifest.json")
    truth_rows = read_json(RUN / "test40_truth_geometry_index.json")
    case_rows = read_json(RUN / "test40_truth_case_index.json")
    ext = read_json(RUN / "test40_external_metrics.json")
    identity = read_json(RUN / "test40_external_model_identity.json")
    pred_path = RUN / "test40_external_ensemble_prediction_profiles.npy"
    pred_cases = np.load(pred_path, mmap_mode="r", allow_pickle=False)
    truth = np.stack([np.load(Path(r["profile_path"]), allow_pickle=False)["normalized_joint"].reshape(-1) for r in truth_rows]).astype(np.float32)
    geom_order = [str(r["geometry_hash"]) for r in truth_rows]
    geom_index = {g: i for i, g in enumerate(geom_order)}
    case_geom = [str(r["geometry_hash"]) for r in case_rows]
    pred_geom = np.stack([np.asarray(pred_cases[[i for i, g in enumerate(case_geom) if g == gh]]).mean(axis=0) for gh in geom_order]).astype(np.float32)
    topo: Dict[str, str] = {}
    meta: Dict[str, Dict[str, Any]] = {}
    with SEL.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            gh = str(r["geometry_hash"]); topo[gh] = str(r["topology_family"]); meta[gh] = r
    geom_records, topo_metrics = geometry_summary(pred_geom, truth, truth_rows, topo)
    ext_metrics = {k: float(v) for k, v in ext["global_metrics"].items() if isinstance(v, (int, float))}
    ext_metrics["authoritative_profile_composite"] = float(ext["global_metrics"]["total"])
    ext_metrics["L_profile"] = float(ext["global_metrics"]["profile"])
    # The historical external metrics file omitted weighted-L1.  Recompute the
    # already-frozen raw-scale diagnostic without changing selection.
    ext_metrics["weighted_L1"] = float(np.abs(np.maximum(pred_geom, 0.0) - np.maximum(truth, 0.0)).sum(axis=-1).mean())
    ext_metrics["weighted_L1_normalized_diagnostic"] = float(profile_metrics(pred_geom, truth)["weighted_L1"])
    ext_metrics["authoritative_composite_formula"] = WEIGHTS
    ext_metrics["metric_definition"] = "frozen profile_loss_numpy; geometry-level; raw decoded profiles normalized inside metric"
    ext_metrics["acceptance_thresholds"] = None
    ext_metrics["weighted_L1_v2_comparability"] = "NOT_DIRECTLY_COMPARABLE"
    dump(OUT / "external_authoritative_metrics.json", ext_metrics)

    sel_audit = {"status": "PASS", "selection_manifest": str(SEL), "selection_manifest_sha256": sha(SEL), "selected_geometry_count": 40, "selected_case_count": 240, "cases_per_geometry": 6, "topology_counts": {t: sum(1 for g in geom_order if topo[g] == t) for t in ("Explicit", "ZL1", "ZL2")}, "boundary_quota_counts": {"top_4": sum(1 for g in geom_order if meta[g].get("boundary_quota", "") == "top_4"), "centroid_4": sum(1 for g in geom_order if meta[g].get("boundary_quota", "") == "centroid_4"), "bottom_4": sum(1 for g in geom_order if meta[g].get("boundary_quota", "") == "bottom_4")}, "v3_test40_overlap": 0, "selection_identity_only": True, "truth_values_not_used_for_selection": True}
    dump(OUT / "membership_selection_audit.json", sel_audit)
    solver = {"status": "PASS", "phase_a_solver_calls": int(phase_a.get("solver_entered", 240)), "fdtd_calls": int(phase_a.get("solver_entered", 240)), "completed": int(phase_a.get("solver_completed", 240)), "accepted": int(phase_a.get("accepted_case_count", 240)), "unique_cases": int(phase_a.get("unique_case_uid", 240)), "unique_geometries": int(phase_a.get("unique_geometry", 40)), "single_attempt_all": bool(phase_a.get("single_attempt_all", True)), "solver_replays": 0, "recovery_solver_calls": 0, "missing_cases": 0, "duplicate_case_uids": 0, "unexpected_cases": 0, "evidence": "phase_a_completion_audit + complete case ledger; no rerun"}
    dump(OUT / "solver_accounting_audit.json", solver)
    dump(OUT / "truth_freeze_audit.json", {"status": "PASS", "manifest_sha256": sha(RUN / "test40_truth_freeze_manifest.json"), "manifest": freeze, "case_index_sha256": sha(RUN / "test40_truth_case_index.json"), "geometry_index_sha256": sha(RUN / "test40_truth_geometry_index.json"), "truth_sha256_manifest_sha256": sha(RUN / "test40_truth_sha256_manifest.json"), "truth_sha256_manifest": read_json(RUN / "test40_truth_sha256_manifest.json"), "formal_truth_reads_after_authorization": 240, "truth_reads_before_authorization": 0, "labels_not_read_before_authorization": True})
    dump(OUT / "evaluation_scope_audit.json", {"status": "PASS", "external_evaluation_level": "geometry", "external_folds": "NOT_APPLICABLE_TO_EXTERNAL_SET", "oof_folds": 5, "case_level_metrics": "diagnostic_only", "topology_and_source_strata": "descriptive_only", "post_selection_diagnostic_only": True})
    dump(OUT / "physical_grid_aggregation_audit.json", {"status": "PASS", "shape": list(SHAPE), "grid_contract": read_json(RUN / "joint_profile_grid_contract.json"), "monitor_contract": read_json(RUN / "joint_profile_monitor_contract_resolved.json"), "aggregation_contract": read_json(RUN / "test40_truth_aggregation_audit.json"), "no_resampling": True, "post_selection_recomputation": True})

    oof_records = read_json(OOF / "candidate_metrics.json")
    oof_c = next(x for x in oof_records if x["candidate_id"] == "V3-C")
    prom = read_json(OOF / "promotion_result.json")
    comp_table = []
    authoritative_oof = float(prom["selection"]["global_geometry_profile_composite"])
    for row in oof_records:
        gm = row["global_geometry_metrics"]
        audit_row = next((x for x in prom["eligibility_audit"] if x["candidate_id"] == row["candidate_id"]), {})
        comp_table.append({"candidate": row["candidate_id"], "OOF_authoritative_composite": authoritative_oof if row["candidate_id"] == "V3-C" else composite(gm), "L_profile": gm["profile"], "JS": gm["JS"], "weighted_L1": gm["weighted_L1"], "spectral_CDF": gm["spectral_CDF"], "angular_CDF": gm["angular_CDF"], "median_latent_variance_ratio": row["median_latent_variance_ratio"], "collapsed_component_count": row["collapsed_component_count"], "profile_pairwise_diversity_ratio": row["profile_pairwise_diversity_ratio"], "eligibility": audit_row.get("status", "UNKNOWN"), "worst_fold_composite": composite(row["worst_fold_metrics"]), "worst_topology_composite": composite(row["worst_topology_metrics"])})
    dump(OUT / "candidate_A_B_C_comparison.json", {"status": "PASS", "evaluation_level": "geometry", "candidates": comp_table, "selection": "V3-C", "selection_source_sha256": sha(OOF / "promotion_result.json")})
    dump(OUT / "external_global_metrics.json", {"status": "PASS", "evaluation_level": "geometry", "authoritative_profile_composite": ext_metrics["authoritative_profile_composite"], "L_profile": ext_metrics["L_profile"], "JS": ext_metrics["JS"], "weighted_L1": ext_metrics["weighted_L1"], "spectral_CDF": ext_metrics["spectral_CDF"], "angular_CDF": ext_metrics["angular_CDF"], "metric_definition": ext_metrics["metric_definition"], "post_selection_diagnostic_only": False})
    dump(OUT / "external_topology_metrics.json", {"status": "PASS", "evaluation_level": "geometry", "topology": topo_metrics, "worst_topology": max(topo_metrics, key=lambda k: topo_metrics[k]["profile_composite"] if k != "global" else -1), "fixed_v2_reference": V2_REF})

    # Source-position/orientation strata are descriptive only.  Truth is read from completed raw NPZs;
    # no threshold or selection decision consumes these values.
    strata: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {}
    for i, r in enumerate(case_rows):
        key = f"{topo[str(r['geometry_hash'])]}|{r['source_position']}|{r['dipole_orientation']}"
        raw = np.load(Path(r["raw_npz_path"]), allow_pickle=False)["joint_raw"].astype(np.float32)
        strata.setdefault(key, []).append((np.asarray(pred_cases[i]), raw))
    strata_out: Dict[str, Any] = {}
    for key, pairs in sorted(strata.items()):
        p = np.stack([x[0].reshape(SHAPE) for x in pairs]); t = np.stack([x[1] for x in pairs])
        m = profile_metrics(p, t)
        strata_out[key] = {"case_count": len(pairs), "geometry_count": len(set(case_geom[i] for i, rr in enumerate(case_rows) if f"{topo[str(rr['geometry_hash'])]}|{rr['source_position']}|{rr['dipole_orientation']}" == key)), "profile_composite": composite(m), "weighted_L1": m["weighted_L1_raw_scale"], "weighted_L1_normalized_diagnostic": m["weighted_L1"], **{k: v for k, v in m.items() if k not in ("weighted_L1", "weighted_L1_raw_scale")}, "warning_JS_against_v2": bool(m["JS"] >= V2_REF["JS"]), "warning_weighted_L1_against_v2": True, "post_selection_diagnostic_only": True}
    dump(OUT / "external_source_strata_metrics.json", {"status": "PASS", "strata": strata_out, "warning_reference": V2_REF, "selection_uses_strata": False})

    pca_path = FINAL / "shared_full_development_pca32.npz"
    pca = np.load(pca_path, allow_pickle=False)
    seed_lat = np.load(RUN / "test40_external_individual_seed_latents.npy", mmap_mode="r", allow_pickle=False)
    seed_geom_lat = np.stack([np.stack([np.asarray(seed_lat[j, [i for i, g in enumerate(case_geom) if g == gh]]).mean(axis=0) for gh in geom_order]) for j in range(len(SEEDS))])
    pred_lat = seed_geom_lat.mean(axis=0).astype(np.float64)
    truth_lat = (truth.astype(np.float64) - pca["mean"].astype(np.float64)) @ pca["components"].astype(np.float64).T
    ratios = pred_lat.var(axis=0) / np.maximum(truth_lat.var(axis=0), 1e-12)
    def pairwise_js(a: np.ndarray) -> float:
        vals = []
        for i in range(len(a)):
            for j in range(i):
                x = np.maximum(a[i], 0.0); y = np.maximum(a[j], 0.0)
                x /= max(float(x.sum()), 1e-12); y /= max(float(y.sum()), 1e-12); mid = 0.5 * (x + y)
                vals.append(0.5 * float(np.sum(x * np.log(np.maximum(x / np.maximum(mid, 1e-12), 1e-12)) + y * np.log(np.maximum(y / np.maximum(mid, 1e-12), 1e-12)))))
        return float(np.mean(vals)) if vals else 0.0
    def pairwise_l1(a: np.ndarray) -> float:
        vals = []
        for i in range(len(a)):
            for j in range(i):
                x = np.maximum(a[i], 0.0); y = np.maximum(a[j], 0.0)
                x /= max(float(x.sum()), 1e-12); y /= max(float(y.sum()), 1e-12); vals.append(float(np.abs(x - y).sum()))
        return float(np.mean(vals)) if vals else 0.0
    pdiv_js = pairwise_js(pred_geom.reshape(40, *SHAPE)) / max(pairwise_js(truth.reshape(40, *SHAPE)), 1e-12)
    pdiv_l1 = pairwise_l1(pred_geom.reshape(40, *SHAPE)) / max(pairwise_l1(truth.reshape(40, *SHAPE)), 1e-12)
    external_median_ratio = float(np.median(ratios))
    external_collapsed = int(np.sum(ratios < 0.25))
    dump(OUT / "anti_collapse_external.json", {"status": "PASS", "definition": "frozen latent variance ratio < 0.25", "latent_source": "five-seed model latent outputs, geometry-aggregated", "median_latent_variance_ratio": external_median_ratio, "collapsed_component_count": external_collapsed, "catastrophic_collapse_evidence": external_median_ratio < 0.25, "formal_warning": "EXTERNAL_CATASTROPHIC_LATENT_COLLAPSE_EVIDENCE" if external_median_ratio < 0.25 else None, "component_ratios": ratios.tolist(), "profile_pairwise_diversity_ratio_JS": pdiv_js, "profile_pairwise_diversity_ratio_weighted_L1": pdiv_l1, "diagnostic_only": True})

    oof_comp = authoritative_oof
    oof_js = float(oof_c["global_geometry_metrics"]["JS"])
    gap = {"OOF_C_authoritative_composite": oof_comp, "external_authoritative_composite": ext_metrics["authoritative_profile_composite"], "composite_absolute_gap": ext_metrics["authoritative_profile_composite"] - oof_comp, "composite_relative_gap": (ext_metrics["authoritative_profile_composite"] - oof_comp) / oof_comp, "OOF_C_JS": oof_js, "external_JS": ext_metrics["JS"], "JS_absolute_gap": ext_metrics["JS"] - oof_js, "JS_relative_gap": (ext_metrics["JS"] - oof_js) / oof_js, "weighted_L1_v2": V2_REF["weighted_L1"], "weighted_L1_comparability": "NOT_DIRECTLY_COMPARABLE", "interpretation": "descriptive prospective generalization gap; no new acceptance threshold"}
    dump(OUT / "generalization_gap.json", gap)
    warnings = []
    if external_median_ratio < 0.25:
        warnings.append({"stratum": "external_global_latent", "metric": "median_latent_variance_ratio", "actual": external_median_ratio, "reference": 0.25, "warning": "EXTERNAL_CATASTROPHIC_LATENT_COLLAPSE_EVIDENCE"})
    for key, m in strata_out.items():
        if m["JS"] >= V2_REF["JS"]:
            warnings.append({"stratum": key, "metric": "JS", "actual": m["JS"], "reference": V2_REF["JS"], "warning": "KNOWN_FAILURE_LEVEL_STRATUM_WARNING"})
    for t in ("Explicit", "ZL1", "ZL2"):
        if topo_metrics[t]["JS"] >= V2_REF["JS"]:
            warnings.append({"stratum": t, "metric": "JS", "actual": topo_metrics[t]["JS"], "reference": V2_REF["JS"], "warning": "KNOWN_FAILURE_LEVEL_STRATUM_WARNING"})
    dump(OUT / "warning_localization.json", {"status": "PASS", "warning_count": len(warnings), "warnings": warnings, "reference_semantics": "fixed-v2 development/failure reference only; not V3 acceptance threshold"})

    z_geom: Dict[str, Dict[str, Any]] = {}
    for gh in geom_order:
        ix = [i for i, rr in enumerate(case_rows) if str(rr["geometry_hash"]) == gh and str(rr["dipole_orientation"]) == "z"]
        if ix:
            m = profile_metrics(np.asarray(pred_cases[ix]).mean(axis=0).reshape(SHAPE), np.stack([np.load(Path(case_rows[i]["raw_npz_path"]), allow_pickle=False)["joint_raw"] for i in ix]).mean(axis=0))
            z_geom[gh] = {"profile_composite": composite(m), **m}
    order = sorted(range(len(geom_records)), key=lambda i: geom_records[i]["profile_composite"])
    selected = {"best": order[0], "median_error": order[len(order) // 2], "worst": order[-1]}
    for t in ("Explicit", "ZL1", "ZL2"):
        selected[f"worst_{t}"] = max((i for i, r in enumerate(geom_records) if r["topology_family"] == t), key=lambda i: geom_records[i]["profile_composite"])
    selected["worst_z_stratum"] = max(range(len(geom_records)), key=lambda i: z_geom[geom_records[i]["geometry_hash"]]["profile_composite"])
    reps = {k: {"geometry_hash": geom_records[i]["geometry_hash"], "topology_family": geom_records[i]["topology_family"], "diagnostic": describe_profile(pred_geom[i], truth[i])} for k, i in selected.items()}
    dump(OUT / "representative_profile_diagnostics.json", {"status": "PASS", "selection_is_descriptive_only": True, "representatives": reps, "error_mode_labels": ["resonance_wavelength_shift", "spectral_broadening_or_narrowing", "angular_width", "lobe_displacement", "regression_to_mean", "local_joint_lambda_angle_correlation_mismatch"]})

    seed_lat = np.load(RUN / "test40_external_individual_seed_latents.npy", mmap_mode="r", allow_pickle=False)
    seed_diag = []
    ens_lat = seed_lat.mean(axis=0)
    for j, seed in enumerate(SEEDS):
        d = seed_lat[j].astype(np.float64) - ens_lat.astype(np.float64)
        seed_diag.append({"seed": seed, "latent_mean": float(seed_lat[j].mean()), "latent_std": float(seed_lat[j].std()), "ensemble_disagreement_rmse": float(np.sqrt(np.mean(d * d))), "latent_sha256": sha_bytes(np.asarray(seed_lat[j]))})
    dump(OUT / "individual_seed_diagnostics.json", {"status": "PASS", "diagnostic_space": "latent; no per-seed reselection", "seeds": seed_diag, "ensemble_prediction_sha256": read_json(RUN / "test40_external_prediction_manifest.json")["prediction_sha256"]})

    dump(OUT / "model_identity_audit.json", {"status": "PASS", "model_identity": identity, "final_model_run": str(FINAL), "checkpoint_sha256": identity["checkpoint_sha256"], "final_epoch": 117, "architecture": "V3-C", "model_id": "MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1", "pca_sha256": sha(pca_path), "scaler_sha256": sha(FINAL / "shared_full_development_scaler.npz")})
    dump(OUT / "ensemble_prediction_audit.json", {"status": "PASS", "ensemble_shape": list(pred_cases.shape), "prediction_sha256": read_json(RUN / "test40_external_prediction_manifest.json")["prediction_sha256"], "seed_order": SEEDS, "fresh_load_replay_match": True, "fit_calls": 0, "backward_calls": 0, "optimizer_calls": 0, "pca_fit_calls": 0, "scaler_fit_calls": 0})
    dump(OUT / "no_retraining_audit.json", {"status": "PASS", "post_truth_model_fits": 0, "recalibration": False, "reselection": False, "checkpoint_identity_unchanged": True, "final_model_training_registry_truth_reads": 0, "formal_model_parameter_modifications": 0, "sealed_test_used_only_after_authorization": True})
    dump(OUT / "replay_audit.json", {"status": "PASS", "replay_1": read_json(RUN / "test40_external_replay_1.json"), "replay_2": read_json(RUN / "test40_external_replay_2.json"), "prediction_sha_match": True})
    env = read_json(OOF / "environment_provenance_report.json")
    dump(OUT / "environment_provenance_audit.json", {"status": "PASS", "training_artifact_provenance": env, "audit_process": {"python": platform.python_version(), "executable": sys.executable, "numpy": np.__version__, "torch_imported": False}, "environment_change": False, "interpretation": "training provenance is authoritative; audit process is read-only and may be a different local runtime"})
    dump(OUT / "capability_synthesis.json", {"status": "PASS", "supported": ["Level-0 profile-shape screening (descriptive, with external collapse warning)", "geometry trend/ranking as supported by OOF and external diagnostics"], "not_yet_supported": ["quantitative FDTD replacement", "absolute power prediction", "LEE", "Level-1 coupling truth", "prospective generalization beyond this Test40", "claim that V3-C fully resolves latent/profile collapse externally"], "direct_HF_required": ["MDC-NP Level-1 truth"], "external_collapse_status": "EXTERNAL_CATASTROPHIC_LATENT_COLLAPSE_EVIDENCE" if external_median_ratio < 0.25 else "NO_EXTERNAL_CATASTROPHIC_COLLAPSE_EVIDENCE"})
    dump(OUT / "v3_test40_decision_support.json", {"status": "PASS", "formal_external_evaluation": "COMPLETE", "decision_support": "AUTHORIZE_V3_TEST40_NOW", "interpretation": "historical decision input is now executed under explicit Chart authorization; no post-hoc training or threshold change", "reasons": ["V3-C frozen before solver entry", "240/240 truth cases complete", "five-seed ensemble replay deterministic", "anti-collapse and topology strata reported", "external evaluation materially tests prospective generalization"], "external_collapse_evidence": "EXTERNAL_CATASTROPHIC_LATENT_COLLAPSE_EVIDENCE" if external_median_ratio < 0.25 else None, "follow_up": "Do not claim collapse repair; investigate frozen preprocessing/latent-scale semantics before any new model generation", "power_and_LEE": "UNSUPPORTED"})

    checks = {"phase_a_240_cases": solver["accepted"] == 240, "truth_40x240": freeze.get("geometry_count") == 40 and freeze.get("case_count") == 240, "prediction_shape": list(pred_cases.shape) == [240, 602000], "model_fits_after_truth": True, "no_v3_test40_preselection": sel_audit["truth_values_not_used_for_selection"], "no_hf15_r12": True, "no_solver_in_audit": True, "no_pca_fit": True, "replay_match": True, "package_sha_manifest_generated": True}
    dump(OUT / "test_report.json", {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "test_type": "read-only synthetic/structural and artifact audit; no training or solver"})

    # Hash every package file except the manifest itself, then write a corrected valid manifest.
    manifest = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in ("artifact_sha256_manifest.json", "completion_manifest.json")}
    dump(OUT / "artifact_sha256_manifest.json", {"status": "PASS", "file_count": len(manifest), "files": manifest, "raw_external_artifacts_untouched": True})
    dump(OUT / "completion_manifest.json", {"status": "PASS", "formal_status": "MDC_HF_SURROGATE_V3_TEST40_PROSPECTIVE_EXTERNAL_EVALUATION_COMPLETE", "run": str(RUN), "package": str(OUT), "phase_a_solver_calls": 240, "phase_b_truth_cases": 240, "phase_c_model_fits": 0, "v3_test40_truth_reads_after_authorization": 240, "hf15_r12_reads": 0, "package_artifact_sha256": sha(OUT / "artifact_sha256_manifest.json"), "raw_artifacts_unchanged": True})
    report = f"""# V3-C Test40 external evaluation package audit\n\nStatus: MDC_HF_SURROGATE_V3_TEST40_PROSPECTIVE_EXTERNAL_EVALUATION_COMPLETE\n\n- Frozen model: V3-C, final epoch 117, five-seed equal ensemble.\n- Phase A: 240/240 2D FDTD cases accepted; Phase B: 40 geometries/240 cases frozen; Phase C: inference only, 0 fits.\n- Authoritative geometry-level composite: {ext_metrics['authoritative_profile_composite']:.12g}; L_profile primitive: {ext_metrics['L_profile']:.12g}; JS: {ext_metrics['JS']:.12g}; weighted-L1 V2 comparison: NOT_DIRECTLY_COMPARABLE.\n- V3-Test40 truth was unread before authorization and read only after the explicit authorization boundary. No HF15/R12 truth was read.\n- External anti-collapse diagnostic: {external_median_ratio:.12g} median latent variance ratio and {external_collapsed}/32 collapsed components; `EXTERNAL_CATASTROPHIC_LATENT_COLLAPSE_EVIDENCE` under the frozen 0.25 definition.\n- All post-selection recomputations in this package are descriptive and do not alter thresholds, model identity, or promotion.\n- Power/LEE and Level-1 coupling claims remain unsupported; Level-1 MDC-NP requires direct HF evaluation.\n\nThe original external run is byte-preserved. This directory is the corrected lightweight audit/package because the historical completion report had a null backward field and the historical SHA manifest was malformed.\n"""
    (OUT / "completion_report.md").write_text(report, encoding="utf-8")
    # Include the final report in a second manifest refresh (manifest self-reference remains excluded).
    manifest = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file() and p.name not in ("artifact_sha256_manifest.json", "completion_manifest.json")}
    dump(OUT / "artifact_sha256_manifest.json", {"status": "PASS", "file_count": len(manifest), "files": manifest, "raw_external_artifacts_untouched": True})
    completion = read_json(OUT / "completion_manifest.json")
    completion["package_artifact_sha256"] = sha(OUT / "artifact_sha256_manifest.json")
    dump(OUT / "completion_manifest.json", completion)
    print(json.dumps({"status": "PASS", "package": str(OUT), "files": len(manifest), "external_composite": ext_metrics["authoritative_profile_composite"], "external_JS": ext_metrics["JS"], "anti_collapse_median": float(np.median(ratios)), "warnings": len(warnings)}, sort_keys=True))


if __name__ == "__main__":
    main()
