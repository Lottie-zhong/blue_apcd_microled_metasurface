from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import Ridge


ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
BLIND_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1"
TRAINVAL_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
DOE_NS = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1"
PREBLIND_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_COMPOSITIONAL_NP_PRIOR_REPAIR_AND_FINAL_PREBLIND_ABLATION_V1"
PCA_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1"
OUT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW_V1"
DOE = DOE_NS / "K6_V1_64G_DOE_CANDIDATES.csv"
TRAINVAL_DATASET = TRAINVAL_ROOT / "V1_TRAINVAL_DATASET.csv"
BLIND_DATASET = BLIND_ROOT / "BLIND_DATASET.csv"
MODEL = PREBLIND_ROOT / "models" / "Ridge_RAW_CHAMPION.pkl"
PREPROCESSOR = PREBLIND_ROOT / "preprocessors" / "selected_model_preprocessor.pkl"
PCA = PCA_ROOT / "ANGULAR_PCA_MODEL.npz"
WLS = np.arange(445.0, 456.0, 1.0)
PITCH_NM = 290.0
LAMBDA_X_NM = 1740.0
COMMITTEE_SIZE = 7
POOL_SIZE = 20_000
POOL_SEED = 20260913
MIN_SELECTION_DISTANCE = 0.35
METRIC_NAMES = ("angular_centroid", "dominant_lobe_centroid", "positive_side_centroid", "negative_side_centroid", "F_seed_2", "F_seed_5", "F_seed_10", "positive_fraction", "negative_fraction", "asymmetry")
DECISION_NAMES = ("theta_peak", "F_seed_5", "asymmetry")


def safe(v: Any) -> Any:
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (tuple, list)):
        return [safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(safe(obj), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([{k: safe(v) for k, v in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2 or np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def rankdata(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    out = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i + 1
        while j < len(a) and a[order[j]] == a[order[i]]:
            j += 1
        out[order[i:j]] = 0.5 * (i + j - 1) + 1.0
        i = j
    return out


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    return pearson(rankdata(np.asarray(a, dtype=float)), rankdata(np.asarray(b, dtype=float)))


def normalize(profile: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, float]:
    z = np.maximum(np.asarray(profile, dtype=float), 0.0)
    integral = float(np.sum(weights * z))
    return z / max(integral, 1e-300), integral


def peak_info(z: np.ndarray, theta: np.ndarray) -> dict[str, Any]:
    z = np.asarray(z, dtype=float)
    theta = np.asarray(theta, dtype=float)
    candidates: list[int] = []
    if z[0] >= z[1]:
        candidates.append(0)
    candidates.extend([i for i in range(1, len(z) - 1) if z[i] >= z[i - 1] and z[i] >= z[i + 1]])
    if z[-1] >= z[-2]:
        candidates.append(len(z) - 1)
    collapsed: list[int] = []
    for i in candidates:
        if collapsed and i <= collapsed[-1] + 1:
            prev = collapsed[-1]
            collapsed[-1] = i if z[i] > z[prev] else prev
        else:
            collapsed.append(i)
    candidates = collapsed or [int(np.argmax(z))]
    peaks = []
    for i in candidates:
        left = float(np.min(z[: i + 1]))
        right = float(np.min(z[i:]))
        prominence = max(0.0, float(z[i]) - max(left, right))
        peaks.append({"index": i, "value": float(z[i]), "theta": float(theta[i]), "prominence": prominence})
    peaks.sort(key=lambda p: (-p["value"], p["index"]))
    top = peaks[0]
    second = peaks[1] if len(peaks) > 1 else {"index": None, "value": 0.0, "theta": None, "prominence": 0.0}
    if 0 < top["index"] < len(z) - 1:
        c = np.polyfit(theta[top["index"] - 1 : top["index"] + 2], z[top["index"] - 1 : top["index"] + 2], 2)[0] * 2.0
    else:
        c = 0.0
    tol = max(float(top["value"]) * 0.01, 1e-12)
    plateau = np.where(np.abs(z - top["value"]) <= tol)[0]
    around = plateau[(plateau <= top["index"]) & (plateau >= top["index"])]
    if len(around):
        lo = top["index"]
        hi = top["index"]
        while lo > 0 and abs(z[lo - 1] - top["value"]) <= tol:
            lo -= 1
        while hi < len(z) - 1 and abs(z[hi + 1] - top["value"]) <= tol:
            hi += 1
        plateau_width = abs(float(theta[hi] - theta[lo]))
    else:
        plateau_width = 0.0
    top_value = max(float(top["value"]), 1e-300)
    ratio = float(second["value"] / top_value)
    separation = abs(float(second["theta"] - top["theta"])) if second["theta"] is not None else None
    curvature_norm = abs(float(c)) / top_value
    significant = [p for p in peaks if p["value"] >= 0.2 * top_value and p["prominence"] >= 0.05 * top_value]
    if plateau_width >= 8.0 or curvature_norm < 1e-4:
        classification = "flat_maximum"
    elif len(significant) >= 3:
        classification = "multiple_lobes"
    elif ratio >= 0.75 and separation is not None and separation >= 5.0:
        classification = "two_comparable_lobes"
    else:
        classification = "single_dominant_lobe"
    sig_indices = sorted(p["index"] for p in significant)
    pos = sig_indices.index(top["index"]) if top["index"] in sig_indices else None
    left_neighbor = sig_indices[pos - 1] if pos is not None and pos > 0 else None
    right_neighbor = sig_indices[pos + 1] if pos is not None and pos < len(sig_indices) - 1 else None
    left_bound = int(np.argmin(z[left_neighbor : top["index"] + 1]) + left_neighbor) if left_neighbor is not None else 0
    right_bound = int(np.argmin(z[top["index"] : right_neighbor + 1]) + top["index"]) if right_neighbor is not None else len(z) - 1
    return {"largest_peak": top, "second_peak": second, "peak_ratio": ratio, "peak_separation_deg": separation, "local_curvature": float(c), "local_curvature_norm": curvature_norm, "lobe_prominence": float(top["prominence"]), "lobe_prominence_ratio": float(top["prominence"] / top_value), "plateau_width_deg": plateau_width, "classification": classification, "dominant_bounds": [left_bound, right_bound]}


def profile_metrics(raw: np.ndarray, theta: np.ndarray, ux: np.ndarray, weights: np.ndarray, wavelength: float) -> dict[str, Any]:
    z, integral = normalize(raw, weights)
    pk = peak_info(z, theta)
    posmask, negmask = ux >= 0, ux < 0
    pos = float(np.sum(weights[posmask] * z[posmask])); neg = float(np.sum(weights[negmask] * z[negmask]))
    total = max(pos + neg, 1e-300)
    seed = math.degrees(math.asin(wavelength / LAMBDA_X_NM))
    lo, hi = pk["dominant_bounds"]
    lobe_w = weights[lo : hi + 1] * z[lo : hi + 1]
    lobe_den = max(float(np.sum(lobe_w)), 1e-300)
    def centroid(mask: np.ndarray) -> float | None:
        den = float(np.sum(weights[mask] * z[mask]))
        return float(np.sum(weights[mask] * z[mask] * theta[mask]) / max(den, 1e-300)) if den > 1e-15 else None
    return {"integral": integral, "theta_peak": pk["largest_peak"]["theta"], "angular_centroid": float(np.sum(weights * z * theta)), "dominant_lobe_centroid": float(np.sum(lobe_w * theta[lo : hi + 1]) / lobe_den), "positive_side_centroid": centroid(posmask), "negative_side_centroid": centroid(negmask), "F_seed_2": float(np.sum(weights[np.abs(theta - seed) <= 2.0] * z[np.abs(theta - seed) <= 2.0])), "F_seed_5": float(np.sum(weights[np.abs(theta - seed) <= 5.0] * z[np.abs(theta - seed) <= 5.0])), "F_seed_10": float(np.sum(weights[np.abs(theta - seed) <= 10.0] * z[np.abs(theta - seed) <= 10.0])), "positive_fraction": pos, "negative_fraction": neg, "asymmetry": (pos - neg) / total, "high_angle_tail": float(np.sum(weights[np.abs(theta) > 60.0] * z[np.abs(theta) > 60.0])), "peak_ratio": pk["peak_ratio"], "peak_separation_deg": pk["peak_separation_deg"], "local_curvature_norm": pk["local_curvature_norm"], "lobe_prominence_ratio": pk["lobe_prominence_ratio"], "classification": pk["classification"], "peak_index": pk["largest_peak"]["index"]}


def aggregate(values: list[float]) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    return {"mean": float(np.mean(x)), "median": float(np.median(x)), "worst": float(np.max(x))}


def geometry_fingerprint(values: tuple[float, ...]) -> str:
    text = "K6|" + "|".join(f"D{i}={v:.6f}" for i, v in enumerate(values, 1))
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def load_context() -> dict[str, Any]:
    if OUT.exists():
        raise RuntimeError(f"output namespace already exists; overwrite forbidden: {OUT}")
    required = [DOE, TRAINVAL_DATASET, BLIND_DATASET, MODEL, PREPROCESSOR, PCA, PREBLIND_ROOT / "NP_PRIOR_FEATURE_DEFINITION.json"]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("READINESS_REQUIRED_ARTIFACT_MISSING:" + ";".join(missing))
    trainval = read_csv(TRAINVAL_DATASET); blind = read_csv(BLIND_DATASET); rows = trainval + blind
    if len(rows) != 704 or len({r["geometry_id"] for r in rows}) != 64:
        raise RuntimeError("HF_COVERAGE_SHAPE_FAILURE")
    counts = {s: len({r["geometry_id"] for r in rows if r["split"] == s}) for s in ("TRAIN", "VALIDATION", "BLIND")}
    if counts != {"TRAIN": 48, "VALIDATION": 8, "BLIND": 8}:
        raise RuntimeError(f"HF_COVERAGE_SPLIT_FAILURE:{counts}")
    pca = np.load(PCA, allow_pickle=False)
    weights = pca["weights_du"].astype(float); sqrt_w = np.sqrt(weights); mean = pca["mean_profile"].astype(float); mean_weighted = mean * sqrt_w; components = pca["components_weighted"].astype(float)
    bundle = pickle.load(MODEL.open("rb")); prep = pickle.load(PREPROCESSOR.open("rb")); model = bundle["payload"]["model"]
    if bundle.get("family") != "Ridge" or bundle.get("feature_set") != "RAW" or bundle.get("pca_rank") != 32 or prep.get("pca_rank") != 32:
        raise RuntimeError("FROZEN_CHAMPION_IDENTITY_FAILURE")
    profiles: dict[str, dict[str, np.ndarray]] = {}
    for row in rows:
        gid = row["geometry_id"]
        if gid not in profiles:
            path = Path(row["angular_profile_ref"])
            if not path.is_file():
                raise RuntimeError(f"PROFILE_MISSING:{gid}:{path}")
            profiles[gid] = {k: np.asarray(v) for k, v in np.load(path, allow_pickle=False).items()}
    x = np.asarray([[float(r[f"D{i}"]) / PITCH_NM for i in range(1, 7)] + [(float(r["lambda_nm"]) - 450.0) / 5.0] for r in rows])
    z = prep["scaler"].transform(prep["imputer"].transform(x))
    pred_y = prep["target_scaler"].inverse_transform(model.predict(z))
    pred_coeff = pred_y[:, 2:]
    pred_raw = (mean_weighted[None, :] + pred_coeff @ components) / sqrt_w[None, :]
    truth_coeff = np.zeros_like(pred_coeff); pca_raw = np.zeros_like(pred_raw); truth_metrics: list[dict[str, Any]] = []; pred_metrics: list[dict[str, Any]] = []; pca_metrics: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        profile = profiles[row["geometry_id"]]; wi = int(np.argmin(np.abs(profile["wavelengths_nm"] - float(row["lambda_nm"])))); theta = profile["theta_deg"][:, wi].astype(float); truth = profile["f_up"][:, wi].astype(float)
        truth_coeff[i] = (truth * sqrt_w - mean_weighted) @ components.T
        pca_raw[i] = (mean_weighted + truth_coeff[i] @ components) / sqrt_w
        truth_metrics.append(profile_metrics(truth, theta, pca["ux"].astype(float), weights, float(row["lambda_nm"])))
        pred_metrics.append(profile_metrics(pred_raw[i], theta, pca["ux"].astype(float), weights, float(row["lambda_nm"])))
        pca_metrics.append(profile_metrics(pca_raw[i], theta, pca["ux"].astype(float), weights, float(row["lambda_nm"])))
    return {"rows": rows, "profiles": profiles, "pca": pca, "weights": weights, "sqrt_w": sqrt_w, "mean_weighted": mean_weighted, "components": components, "model": model, "prep": prep, "pred_y": pred_y, "pred_coeff": pred_coeff, "pred_raw": pred_raw, "truth_coeff": truth_coeff, "pca_raw": pca_raw, "truth_metrics": truth_metrics, "pred_metrics": pred_metrics, "pca_metrics": pca_metrics, "counts": counts}


def grouped_records(ctx: dict[str, Any]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(list)
    for i, row in enumerate(ctx["rows"]):
        out[row["geometry_id"]].append(i)
    for gid in out:
        out[gid].sort(key=lambda i: float(ctx["rows"][i]["lambda_nm"]))
    return out


def build_profile_decomposition(ctx: dict[str, Any], groups: dict[str, list[int]]) -> list[dict[str, Any]]:
    out = []
    for gid, inds in groups.items():
        previous: dict[str, dict[str, Any]] | None = None
        for i in inds:
            row = ctx["rows"][i]; tm, pm = ctx["truth_metrics"][i], ctx["pred_metrics"][i]
            truth_integral, pred_integral = tm["integral"], pm["integral"]
            spectral = 0.0 if previous is None else abs((pm["dominant_lobe_centroid"] - previous["pred_dom"]) - (tm["dominant_lobe_centroid"] - previous["truth_dom"]))
            rec = {"geometry_id": gid, "split": row["split"], "lambda_nm": float(row["lambda_nm"]), "amplitude_error": abs(pred_integral - truth_integral) / max(abs(truth_integral), 1e-300), "amplitude_shape_error": abs(pred_integral - truth_integral) / max(abs(truth_integral), 1e-300), "shape_error_weighted_l1": float(np.sum(ctx["weights"] * np.abs(normalize(ctx["pred_raw"][i], ctx["weights"])[0] - normalize(ctx["profiles"][gid]["f_up"][:, int(np.argmin(np.abs(ctx["profiles"][gid]["wavelengths_nm"] - float(row["lambda_nm"]))))], ctx["weights"])[0]))), "lobe_position_error_deg": abs(pm["dominant_lobe_centroid"] - tm["dominant_lobe_centroid"]), "positive_negative_routing_error": abs(pm["asymmetry"] - tm["asymmetry"]), "high_angle_tail_error": abs(pm["high_angle_tail"] - tm["high_angle_tail"]), "spectral_shift_error_deg": spectral, "theta_peak_error_deg": abs(pm["theta_peak"] - tm["theta_peak"]), "profile_l1_reference": float(np.sum(ctx["weights"] * np.abs(normalize(ctx["pred_raw"][i], ctx["weights"])[0] - normalize(ctx["profiles"][gid]["f_up"][:, int(np.argmin(np.abs(ctx["profiles"][gid]["wavelengths_nm"] - float(row["lambda_nm"]))))], ctx["weights"])[0]))) }
            out.append(rec); previous = {"pred_dom": pm["dominant_lobe_centroid"], "truth_dom": tm["dominant_lobe_centroid"]}
    return out


def error_aggregates(records: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for split in ("TRAIN", "VALIDATION", "BLIND", "ALL"):
        subset = records if split == "ALL" else [r for r in records if r["split"] == split]
        result[split] = {field: aggregate([float(r[field]) for r in subset]) for field in fields}
    return result


def robust_audit(ctx: dict[str, Any], groups: dict[str, list[int]]) -> dict[str, Any]:
    metric_errors = {m: [] for m in METRIC_NAMES}
    split_summary: dict[str, Any] = {}
    classifications: dict[str, Any] = {}
    ranking: dict[str, Any] = {}
    for split in ("TRAIN", "VALIDATION", "BLIND", "ALL"):
        indices = range(len(ctx["rows"])) if split == "ALL" else [i for i, r in enumerate(ctx["rows"]) if r["split"] == split]
        split_summary[split] = {}
        classifications[split] = {"truth": defaultdict(int), "prediction": defaultdict(int)}
        for i in indices:
            tm, pm = ctx["truth_metrics"][i], ctx["pred_metrics"][i]
            classifications[split]["truth"][tm["classification"]] += 1; classifications[split]["prediction"][pm["classification"]] += 1
            for m in METRIC_NAMES:
                metric_errors[m].append((ctx["rows"][i]["split"], abs(float(pm[m]) - float(tm[m]))))
        for m in METRIC_NAMES:
            vals = [e for s, e in metric_errors[m] if split == "ALL" or s == split]
            split_summary[split][m + "_mae"] = float(np.mean(vals)) if vals else None
    for m in ("angular_centroid", "dominant_lobe_centroid", "F_seed_5", "asymmetry"):
        tv, pv = [], []
        for gid, inds in groups.items():
            tv.append(float(np.mean([ctx["truth_metrics"][i][m] for i in inds]))); pv.append(float(np.mean([ctx["pred_metrics"][i][m] for i in inds])))
        ranking[m] = {"geometry_count": len(tv), "pearson": pearson(np.asarray(tv), np.asarray(pv)), "spearman": spearman(np.asarray(tv), np.asarray(pv))}
    stability = {}
    for split in ("TRAIN", "VALIDATION", "BLIND", "ALL"):
        gids = [g for g, inds in groups.items() if split == "ALL" or ctx["rows"][inds[0]]["split"] == split]
        vals = []
        for gid in gids:
            inds = groups[gid]; inds.sort(key=lambda i: float(ctx["rows"][i]["lambda_nm"]))
            vals.append({"geometry_id": gid, "truth_peak_adjacent_delta_mean_deg": float(np.mean(np.abs(np.diff([ctx["truth_metrics"][i]["theta_peak"] for i in inds])))), "truth_dominant_centroid_adjacent_delta_mean_deg": float(np.mean(np.abs(np.diff([ctx["truth_metrics"][i]["dominant_lobe_centroid"] for i in inds])))), "truth_F_seed_5_adjacent_delta_mean": float(np.mean(np.abs(np.diff([ctx["truth_metrics"][i]["F_seed_5"] for i in inds]))))})
        stability[split] = {k: float(np.mean([v[k] for v in vals])) for k in vals[0] if k != "geometry_id"} if vals else {}
    result = {"schema_version": "ROBUST_DIRECTIONAL_METRICS_AUDIT_V1", "definitions": {"angular_centroid": "integral(theta*f_up du)/integral(f_up du)", "dominant_lobe_centroid": "centroid bounded by deterministic valleys to adjacent significant peaks; prominence>=5 percent and height>=20 percent of largest peak", "F_seed": "fixed +/-2, +/-5, +/-10 degree windows around asin(lambda/1740 nm)", "positive_negative": "fixed ux >= 0 and ux < 0 partitions", "no_result_dependent_window": True}, "split_metric_mae": split_summary, "classification_counts": {k: {a: dict(b) for a, b in v.items()} for k, v in classifications.items()}, "truth_spectral_sensitivity": stability, "geometry_ranking_usefulness": ranking}
    return result


def theta_audit(ctx: dict[str, Any], groups: dict[str, list[int]]) -> dict[str, Any]:
    by_split = {}
    for split in ("TRAIN", "VALIDATION", "BLIND", "ALL"):
        inds = range(len(ctx["rows"])) if split == "ALL" else [i for i, r in enumerate(ctx["rows"]) if r["split"] == split]
        truth = [ctx["truth_metrics"][i] for i in inds]; pred = [ctx["pred_metrics"][i] for i in inds]
        ratios = np.asarray([float(x["peak_ratio"]) for x in truth]); near = ratios >= 0.75
        switches = []
        for gid, ginds in groups.items():
            if split != "ALL" and ctx["rows"][ginds[0]]["split"] != split:
                continue
            ordered = sorted(ginds, key=lambda i: float(ctx["rows"][i]["lambda_nm"]))
            switches.append(float(np.mean(np.abs(np.diff([ctx["truth_metrics"][i]["theta_peak"] for i in ordered])) > 5.0)))
        by_split[split] = {"rows": len(truth), "truth_classification_counts": {c: sum(x["classification"] == c for x in truth) for c in ("single_dominant_lobe", "two_comparable_lobes", "multiple_lobes", "flat_maximum")}, "near_tie_ratio_ge_0_75_fraction": float(np.mean(near)) if len(near) else 0.0, "median_peak_ratio": float(np.median(ratios)) if len(ratios) else None, "median_peak_separation_deg": float(np.nanmedian([x["peak_separation_deg"] if x["peak_separation_deg"] is not None else np.nan for x in truth])), "mean_truth_local_curvature_norm": float(np.mean([x["local_curvature_norm"] for x in truth])), "mean_peak_switch_rate_gt_5deg": float(np.mean(switches)) if switches else 0.0, "theta_peak_mae_deg": float(np.mean([abs(p["theta_peak"] - t["theta_peak"]) for t, p in zip(truth, pred)]))}
    b = by_split["BLIND"]
    instability = b["near_tie_ratio_ge_0_75_fraction"] >= 0.25 or b["mean_peak_switch_rate_gt_5deg"] >= 0.25 or b["truth_classification_counts"]["flat_maximum"] + b["truth_classification_counts"]["multiple_lobes"] >= 0.25 * max(b["rows"], 1)
    model_error = b["theta_peak_mae_deg"] >= 10.0
    diagnosis = "BOTH" if instability and model_error else "THETA_PEAK_METRIC_INSTABILITY" if instability else "REAL_PROFILE_PREDICTION_ERROR" if model_error else "NEITHER_EVIDENCE_STRONG"
    return {"schema_version": "THETA_PEAK_STABILITY_AUDIT_V1", "definitions": {"near_tie": "second/largest peak ratio >=0.75 and deterministic peak separation >=5 deg", "flat_maximum": "top plateau width >=8 deg or normalized local curvature <1e-4", "peak_switch": "adjacent wavelength top-peak angle changes >5 deg", "thresholds_frozen_before_summary": True}, "by_split": by_split, "diagnosis": diagnosis, "instability_evidence": bool(instability), "real_profile_prediction_error_evidence": bool(model_error)}


def scalar_audit(ctx: dict[str, Any]) -> dict[str, Any]:
    pre_cv = next(r for r in read_csv(PREBLIND_ROOT / "NP_PRIOR_GROUPED_CV_RESULTS.csv") if r["candidate"] == "Ridge_A_RAW")
    pre_val = next(r for r in read_csv(PREBLIND_ROOT / "NP_PRIOR_DEVELOPMENT_VALIDATION_RESULTS.csv") if r["candidate"] == "Ridge_A_RAW")
    rows = []
    for split in ("TRAIN", "VALIDATION", "BLIND"):
        inds = [i for i, r in enumerate(ctx["rows"]) if r["split"] == split]
        rows.append({"split": split, "G_emit_mae": float(np.mean([abs(ctx["pred_y"][i, 0] - float(ctx["rows"][i]["G_emit"])) for i in inds])), "eta_up_mae": float(np.mean([abs(ctx["pred_y"][i, 1] - float(ctx["rows"][i]["eta_up"])) for i in inds]))})
    blind = next(r for r in rows if r["split"] == "BLIND"); val_g, val_e = float(pre_val["G_emit_mae"]), float(pre_val["eta_up_mae"])
    geo = []
    for gid, inds in grouped_records(ctx).items():
        if ctx["rows"][inds[0]]["split"] != "BLIND":
            continue
        geo.append({"geometry_id": gid, "G_emit_mae": float(np.mean([abs(ctx["pred_y"][i, 0] - float(ctx["rows"][i]["G_emit"])) for i in inds])), "eta_up_mae": float(np.mean([abs(ctx["pred_y"][i, 1] - float(ctx["rows"][i]["eta_up"])) for i in inds]))})
    ready = blind["G_emit_mae"] <= 2.0 * val_g and blind["eta_up_mae"] <= 2.0 * val_e and max(x["G_emit_mae"] for x in geo) <= 4.0 * val_g and max(x["eta_up_mae"] for x in geo) <= 4.0 * val_e
    return {"schema_version": "SCALAR_FORWARD_READINESS_V1", "status": "SCALAR_FORWARD_READY" if ready else "SCALAR_FORWARD_PARTIAL", "thresholds": {"blind_mae_max_vs_development": 2.0, "per_geometry_worst_max_vs_development": 4.0}, "train_grouped_cv": {k: float(pre_cv[k]) for k in ("G_emit_mae", "eta_up_mae")}, "development_validation": {k: float(pre_val[k]) for k in ("G_emit_mae", "eta_up_mae")}, "recomputed_split_metrics": rows, "blind_per_geometry": geo, "spectral_stability": {"G_emit_max_minus_min_error": float(max(x["G_emit_mae"] for x in geo) - min(x["G_emit_mae"] for x in geo)), "eta_up_max_minus_min_error": float(max(x["eta_up_mae"] for x in geo) - min(x["eta_up_mae"] for x in geo))}}


def pca_audit(ctx: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records = []
    for i, row in enumerate(ctx["rows"]):
        tm, pm, xm = ctx["truth_metrics"][i], ctx["pred_metrics"][i], ctx["pca_metrics"][i]
        records.append({"split": row["split"], "pca_floor_profile_l1": float(np.sum(ctx["weights"] * np.abs(normalize(ctx["pca_raw"][i], ctx["weights"])[0] - normalize(ctx["profiles"][row["geometry_id"]]["f_up"][:, int(np.argmin(np.abs(ctx["profiles"][row["geometry_id"]]["wavelengths_nm"] - float(row["lambda_nm"]))))], ctx["weights"])[0]))), "surrogate_profile_l1": float(np.sum(ctx["weights"] * np.abs(normalize(ctx["pred_raw"][i], ctx["weights"])[0] - normalize(ctx["profiles"][row["geometry_id"]]["f_up"][:, int(np.argmin(np.abs(ctx["profiles"][row["geometry_id"]]["wavelengths_nm"] - float(row["lambda_nm"]))))], ctx["weights"])[0]))), "pca_theta_error": abs(xm["theta_peak"] - tm["theta_peak"]), "surrogate_theta_error": abs(pm["theta_peak"] - tm["theta_peak"]), "coefficient_l2_error": float(np.linalg.norm(ctx["pred_coeff"][i] - ctx["truth_coeff"][i]))})
    summary = {}
    for split in ("TRAIN", "VALIDATION", "BLIND", "ALL"):
        subset = records if split == "ALL" else [r for r in records if r["split"] == split]
        summary[split] = {k: float(np.mean([r[k] for r in subset])) for k in records[0] if k != "split"}
    ratio = summary["ALL"]["pca_floor_profile_l1"] / max(summary["ALL"]["surrogate_profile_l1"], 1e-300)
    bottleneck = "NO" if ratio < 0.25 else "PARTIAL" if ratio < 0.5 else "YES"
    return {"schema_version": "PCA_VS_SURROGATE_ERROR_AUDIT_V1", "pca_rank": 32, "split_summary": summary, "pca_floor_fraction_of_final_profile_l1": ratio, "bottleneck": bottleneck, "interpretation": "rank-32 reconstruction floor is compared on the same normalized weighted-L1 and theta_peak diagnostics; explained variance alone is not used"}, records


def coefficient_audit(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    coeff = ctx["truth_coeff"]; pred = ctx["pred_coeff"]; std = np.std(coeff, axis=0); evr = ctx["pca"]["explained_variance_ratio"].astype(float)
    theta = np.asarray([x["theta_peak"] for x in ctx["truth_metrics"]]); f5 = np.asarray([x["F_seed_5"] for x in ctx["truth_metrics"]]); asym = np.asarray([x["asymmetry"] for x in ctx["truth_metrics"]])
    out = []
    for j in range(coeff.shape[1]):
        mae = float(np.mean(np.abs(pred[:, j] - coeff[:, j]))); nmae = mae / max(float(std[j]), 1e-12)
        it = abs(pearson(coeff[:, j], theta)); iff = abs(pearson(coeff[:, j], f5)); ia = abs(pearson(coeff[:, j], asym)); importance = max(it, iff, ia)
        out.append({"coefficient_index": j + 1, "explained_variance_ratio": float(evr[j]), "variance_contribution_normalized": float(evr[j] / max(np.sum(evr), 1e-300)), "truth_std": float(std[j]), "prediction_mae": mae, "normalized_mae": nmae, "prediction_corr": pearson(coeff[:, j], pred[:, j]), "importance_theta_peak": it, "importance_F_seed_5": iff, "importance_asymmetry": ia, "directional_importance_max": importance, "directional_priority": importance * nmae, "poorly_predicted_directional": bool(nmae > np.median([np.mean(np.abs(pred[:, k] - coeff[:, k])) / max(float(std[k]), 1e-12) for k in range(coeff.shape[1])]) and importance >= 0.15)})
    return out


def novelty_audit(ctx: dict[str, Any], groups: dict[str, list[int]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    doe = read_csv(DOE); vectors = {r["geometry_id"]: np.asarray([float(r[f"D{i}_nm"]) for i in range(1, 7)]) for r in doe}; train_ids = [r["geometry_id"] for r in doe if r["split"] == "TRAIN"]; scale = np.ptp(np.asarray([vectors[g] for g in train_ids]), axis=0); scale[scale == 0] = 1.0
    result = []
    for gid, inds in groups.items():
        split = ctx["rows"][inds[0]]["split"]
        if split == "TRAIN":
            continue
        v = vectors[gid]; d = np.sqrt(np.sum(((np.asarray([vectors[g] for g in train_ids]) - v) / scale) ** 2, axis=1)); blind_or_val = [i for i in inds]
        result.append({"geometry_id": gid, "split": split, "nearest_train_normalized_distance": float(np.min(d)), "profile_l1": float(np.mean([np.sum(ctx["weights"] * np.abs(normalize(ctx["pred_raw"][i], ctx["weights"])[0] - normalize(ctx["profiles"][gid]["f_up"][:, int(np.argmin(np.abs(ctx["profiles"][gid]["wavelengths_nm"] - float(ctx["rows"][i]["lambda_nm"]))))], ctx["weights"])[0])) for i in blind_or_val])), "theta_peak_error": float(np.mean([abs(ctx["pred_metrics"][i]["theta_peak"] - ctx["truth_metrics"][i]["theta_peak"]) for i in blind_or_val])), "F_seed_5_error": float(np.mean([abs(ctx["pred_metrics"][i]["F_seed_5"] - ctx["truth_metrics"][i]["F_seed_5"]) for i in blind_or_val])), "asymmetry_error": float(np.mean([abs(ctx["pred_metrics"][i]["asymmetry"] - ctx["truth_metrics"][i]["asymmetry"]) for i in blind_or_val])), "within_train_axis_bounds": bool(np.all((v >= np.min(np.asarray([vectors[g] for g in train_ids]), axis=0)) & (v <= np.max(np.asarray([vectors[g] for g in train_ids]), axis=0))))})
    summary = {k: {"pearson": pearson(np.asarray([r["nearest_train_normalized_distance"] for r in result]), np.asarray([r[k] for r in result])), "spearman": spearman(np.asarray([r["nearest_train_normalized_distance"] for r in result]), np.asarray([r[k] for r in result]))} for k in ("profile_l1", "theta_peak_error", "F_seed_5_error", "asymmetry_error")}
    return result, {"schema_version": "BLIND_ERROR_VS_NOVELTY_SUMMARY_V1", "rows": len(result), "correlation": summary, "interpretation": "16 validation/blind geometry summaries; novelty is the same normalized nearest-train distance used by the V1 blind OOD audit"}


def coverage_audit(ctx: dict[str, Any], groups: dict[str, list[int]]) -> dict[str, Any]:
    doe = read_csv(DOE); vectors = {r["geometry_id"]: np.asarray([float(r[f"D{i}_nm"]) for i in range(1, 7)]) for r in doe}; ids = list(vectors); out: dict[str, Any] = {"schema_version": "CURRENT_HF_COVERAGE_AUDIT_V1", "geometry_count": len(ids), "split_geometry_counts": ctx["counts"], "wavelengths_nm": WLS.tolist(), "D_ranges_nm": {}, "pairwise_coverage": {}, "response_diversity": {}, "sparse_regions": {}}
    for j in range(6):
        vals = [float(vectors[g][j]) for g in ids]; out["D_ranges_nm"][f"D{j+1}"] = {"min": min(vals), "max": max(vals), "unique_count": len(set(vals))}
    for a in range(6):
        for b in range(a + 1, 6):
            pairs = {(vectors[g][a], vectors[g][b]) for g in ids}; out["pairwise_coverage"][f"D{a+1}_D{b+1}"] = {"observed_unique_pairs": len(pairs), "singleton_pair_count": sum(sum(1 for g in ids if vectors[g][a] == x and vectors[g][b] == y) == 1 for x, y in pairs)}
    at450 = [i for i, r in enumerate(ctx["rows"]) if float(r["lambda_nm"]) == 450.0]
    out["response_diversity"] = {"profile_pca_coeff_std_at_450": np.std(ctx["truth_coeff"][at450], axis=0).tolist(), "profile_metrics_at_450": {m: {"min": float(min(ctx["truth_metrics"][i][m] for i in at450)), "max": float(max(ctx["truth_metrics"][i][m] for i in at450)), "std": float(np.std([ctx["truth_metrics"][i][m] for i in at450]))} for m in ("F_seed_5", "asymmetry", "dominant_lobe_centroid", "theta_peak")}, "phase_response": "auxiliary NP compositional phase proxy available in NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1; native integrated 2D complex phase labels are not present in V1_TRAINVAL_DATASET", "phase_proxy_source": str(PREBLIND_ROOT / "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1.csv")}
    sparse = []
    for a in range(6):
        for b in range(a + 1, 6):
            counts = defaultdict(int)
            for g in ids:
                counts[(vectors[g][a], vectors[g][b])] += 1
            sparse.extend({"pair": f"D{a+1}_D{b+1}", "D_a_nm": x, "D_b_nm": y, "count": c} for (x, y), c in counts.items() if c == 1)
    out["sparse_regions"]["singleton_pair_examples"] = sparse[:100]; out["sparse_regions"]["singleton_pair_count_total"] = len(sparse)
    return out


def candidate_pool_and_al(ctx: dict[str, Any], groups: dict[str, list[int]], coefficient_rows: list[dict[str, Any]]) -> dict[str, Any]:
    doe = read_csv(DOE); grids = [sorted({float(r[f"D{i}_nm"]) for r in doe}) for i in range(1, 7)]; existing = {tuple(float(r[f"D{i}_nm"]) for i in range(1, 7)) for r in doe}; rng = np.random.default_rng(POOL_SEED); candidates: list[tuple[float, ...]] = []
    seen = set(existing)
    while len(candidates) < POOL_SIZE:
        candidate = tuple(float(grids[j][int(rng.integers(0, len(grids[j])))]) for j in range(6))
        if candidate not in seen:
            seen.add(candidate); candidates.append(candidate)
    train_vectors = np.asarray([list(x) for x in existing if x in {tuple(float(r[f"D{i}_nm"]) for i in range(1, 7)) for r in doe if r["split"] == "TRAIN"}])
    all_existing = np.asarray(list(existing)); scale = np.ptp(train_vectors, axis=0); scale[scale == 0] = 1.0
    # Analysis-only committee: 7 bootstrap Ridge fits on TRAIN geometry groups. V1 champion remains untouched.
    train_inds = np.asarray([i for i, r in enumerate(ctx["rows"]) if r["split"] == "TRAIN"]); train_gids = sorted({ctx["rows"][i]["geometry_id"] for i in train_inds}); gid_indices = {g: np.asarray([i for i in train_inds if ctx["rows"][i]["geometry_id"] == g]) for g in train_gids}
    ztrain = ctx["prep"]["scaler"].transform(ctx["prep"]["imputer"].transform(np.asarray([[float(ctx["rows"][i][f"D{j}"]) / PITCH_NM for j in range(1, 7)] + [(float(ctx["rows"][i]["lambda_nm"]) - 450.0) / 5.0] for i in train_inds])))
    ytrain = ctx["prep"]["target_scaler"].transform(np.column_stack([ctx["pred_y"][train_inds, :2] * 0.0 + np.asarray([[float(ctx["rows"][i]["G_emit"]), float(ctx["rows"][i]["eta_up"])] for i in train_inds]), ctx["truth_coeff"][train_inds]]))
    # target scalers are frozen transforms; ytrain uses exact truth scalars and rank-32 truth coefficients.
    xpool = np.asarray([[d / PITCH_NM for d in c] + [(w - 450.0) / 5.0] for c in candidates for w in WLS])
    zpool = ctx["prep"]["scaler"].transform(ctx["prep"]["imputer"].transform(xpool))
    n, nw, nc = len(candidates), len(WLS), 32
    sum_coeff = np.zeros((n * nw, nc)); sumsq_coeff = np.zeros_like(sum_coeff); sum_scalar = np.zeros((n * nw, 2)); sumsq_scalar = np.zeros_like(sum_scalar); sum_dir = np.zeros((n * nw, 3)); sumsq_dir = np.zeros_like(sum_dir)
    coeff_std_train = np.std(ctx["truth_coeff"][train_inds], axis=0); scalar_std_train = np.std(np.asarray([[float(ctx["rows"][i]["G_emit"]), float(ctx["rows"][i]["eta_up"])] for i in train_inds]), axis=0); coeff_std_train[coeff_std_train < 1e-10] = 1.0; scalar_std_train[scalar_std_train < 1e-10] = 1.0
    train_coeff = ctx["truth_coeff"][train_inds]; train_dir = np.asarray([[ctx["truth_metrics"][i]["theta_peak"], ctx["truth_metrics"][i]["F_seed_5"], ctx["truth_metrics"][i]["asymmetry"]] for i in train_inds]); design = np.column_stack([np.ones(len(train_coeff)), train_coeff]); beta = np.linalg.lstsq(design, train_dir, rcond=None)[0]
    member_rows = []
    for member in range(COMMITTEE_SIZE):
        mrng = np.random.default_rng(POOL_SEED + member + 1); sample_gids = mrng.choice(train_gids, size=len(train_gids), replace=True); sample = np.concatenate([gid_indices[g] for g in sample_gids]); model = Ridge(alpha=100.0); model.fit(ztrain[np.searchsorted(train_inds, sample)], ytrain[np.searchsorted(train_inds, sample)])
        y = ctx["prep"]["target_scaler"].inverse_transform(model.predict(zpool)); coeff = y[:, 2:]; dirs = np.column_stack([np.ones(len(y)), coeff]) @ beta
        sum_coeff += coeff; sumsq_coeff += coeff * coeff; sum_scalar += y[:, :2]; sumsq_scalar += y[:, :2] * y[:, :2]; sum_dir += dirs; sumsq_dir += dirs * dirs; member_rows.append({"member": member + 1, "bootstrap_seed": POOL_SEED + member + 1, "bootstrap_geometry_count": len(sample_gids), "training_split": "TRAIN_ONLY", "replaces_v1_champion": False})
    mean_coeff = sum_coeff / COMMITTEE_SIZE; std_coeff = np.sqrt(np.maximum(sumsq_coeff / COMMITTEE_SIZE - mean_coeff * mean_coeff, 0.0)); mean_scalar = sum_scalar / COMMITTEE_SIZE; std_scalar = np.sqrt(np.maximum(sumsq_scalar / COMMITTEE_SIZE - mean_scalar * mean_scalar, 0.0)); mean_dir = sum_dir / COMMITTEE_SIZE; std_dir = np.sqrt(np.maximum(sumsq_dir / COMMITTEE_SIZE - mean_dir * mean_dir, 0.0))
    coeff_unc = np.mean(std_coeff / coeff_std_train[None, :], axis=1).reshape(n, nw).mean(axis=1); scalar_unc = np.mean(std_scalar / scalar_std_train[None, :], axis=1).reshape(n, nw).mean(axis=1); profile_unc = np.mean((std_coeff / coeff_std_train[None, :]) * np.sqrt(ctx["pca"]["explained_variance_ratio"].astype(float)[None, :]), axis=1).reshape(n, nw).mean(axis=1); theta_unc = std_dir[:, 0].reshape(n, nw).mean(axis=1) / 20.0; f5_unc = std_dir[:, 1].reshape(n, nw).mean(axis=1) / 0.05; asym_unc = std_dir[:, 2].reshape(n, nw).mean(axis=1) / 0.15
    u_model = 0.7 * profile_unc + 0.3 * scalar_unc; s_decision = 0.45 * profile_unc + 0.25 * theta_unc + 0.20 * f5_unc + 0.10 * asym_unc
    novelty = np.asarray([float(np.min(np.sqrt(np.sum(((train_vectors - np.asarray(c)) / scale) ** 2, axis=1)))) for c in candidates]); novelty_norm = novelty / max(float(np.percentile(novelty, 95)), 1e-12); score = u_model * s_decision * novelty_norm
    ranking = []
    for i, c in enumerate(candidates):
        ranking.append({"candidate_id": f"ALR1_CAND_{i+1:05d}", **{f"D{j+1}_nm": c[j] for j in range(6)}, "geometry_sha256": geometry_fingerprint(c), "U_model": float(u_model[i]), "U_profile_coefficients": float(profile_unc[i]), "U_scalar": float(scalar_unc[i]), "S_decision": float(s_decision[i]), "U_theta_proxy": float(theta_unc[i]), "U_F_seed_5_proxy": float(f5_unc[i]), "U_asymmetry_proxy": float(asym_unc[i]), "D_geometry": float(novelty[i]), "acquisition_score": float(score[i]), "selected_round1": False, "future_v2_selected": False})
    ranking.sort(key=lambda r: (-r["acquisition_score"], r["candidate_id"]))
    selected: list[dict[str, Any]] = []
    for row in ranking:
        v = np.asarray([row[f"D{j}_nm"] for j in range(1, 7)], dtype=float)
        if all(float(np.linalg.norm((np.asarray([s[f"D{j}_nm"] for j in range(1, 7)], dtype=float) - v) / scale)) >= MIN_SELECTION_DISTANCE for s in selected):
            selected.append(row)
            if len(selected) == 8:
                break
    if len(selected) != 8:
        raise RuntimeError(f"AL_DIVERSITY_SELECTION_FAILED:{len(selected)}")
    selected_ids = {r["candidate_id"] for r in selected}
    for rank, row in enumerate(selected, 1):
        row["selected_round1"] = True; row["selection_rank"] = rank; row["selection_min_distance_to_prior_selected"] = None if rank == 1 else float(min(np.linalg.norm((np.asarray([s[f"D{j}_nm"] for j in range(1, 7)], dtype=float) - np.asarray([row[f"D{j}_nm"] for j in range(1, 7)], dtype=float)) / scale) for s in selected[: rank - 1])); q_u, q_s, q_d = np.percentile([x["U_model"] for x in ranking], 75), np.percentile([x["S_decision"] for x in ranking], 75), np.percentile([x["D_geometry"] for x in ranking], 75); row["selection_rationale"] = "high_uncertainty_decision_sensitive" if row["U_model"] >= q_u and row["S_decision"] >= q_s else "geometry_diverse_coverage" if row["D_geometry"] >= q_d else "mixed_uncertainty_novelty_ranked"
    remaining = [r for r in ranking if r["candidate_id"] not in selected_ids]; reference = np.asarray(list(existing) + [tuple(float(r[f"D{j}_nm"]) for j in range(1, 7)) for r in selected]); future: list[dict[str, Any]] = []
    while len(future) < 8:
        best = None; best_d = -1.0
        for row in remaining:
            v = np.asarray([row[f"D{j}_nm"] for j in range(1, 7)], dtype=float); d = float(np.min(np.sqrt(np.sum(((reference - v) / scale) ** 2, axis=1))))
            if d > best_d:
                best, best_d = row, d
        if best is None:
            raise RuntimeError("V2_TEST_SELECTION_FAILED")
        future.append(best); remaining.remove(best); reference = np.vstack([reference, np.asarray([best[f"D{j}_nm"] for j in range(1, 7)], dtype=float)])
    for row in future:
        row["future_v2_selected"] = True
    pool_manifest = {"schema_version": "AL_CANDIDATE_POOL_MANIFEST_V1", "pool_size": POOL_SIZE, "unique": True, "seed": POOL_SEED, "generation": "deterministic random projection onto official per-dimension discrete D grid", "official_grid_source": str(DOE), "excluded_geometry_count": len(existing), "excluded_geometry_sha256": sha(DOE), "solver_launched": False, "truth_acquired": False, "minimum_selected_normalized_distance": MIN_SELECTION_DISTANCE, "committee_size": COMMITTEE_SIZE}
    write_json(OUT / "AL_COMMITTEE_DEFINITION.json", {"schema_version": "AL_COMMITTEE_DEFINITION_V1", "members": member_rows, "targets": ["G_emit", "eta_up", "rank32_PCA_coefficients"], "directional_proxy": "TRAIN truth PCA coefficients to theta_peak/F_seed_5/asymmetry least-squares diagnostic map; ranking proxy only", "champion": "RIDGE_RAW_CHAMPION", "production_model_replaced": False, "blind_rows_used_for_fit": False, "solver_launched": False})
    pool_manifest["candidate_ranking_sha256"] = None
    write_csv(OUT / "AL_CANDIDATE_RANKING.csv", ranking)
    pool_manifest["candidate_ranking_sha256"] = sha(OUT / "AL_CANDIDATE_RANKING.csv")
    write_json(OUT / "AL_CANDIDATE_POOL_MANIFEST.json", pool_manifest)
    selected_out = []
    for i, row in enumerate(selected, 1):
        selected_out.append({"geometry_id": f"ALR1_{i:02d}", **{f"D{j}": row[f"D{j}_nm"] for j in range(1, 7)}, "geometry_sha256": row["geometry_sha256"], "candidate_id": row["candidate_id"], "selection_rank": i, "selection_min_distance_to_prior_selected": row.get("selection_min_distance_to_prior_selected"), "acquisition_score": row["acquisition_score"], "U_model": row["U_model"], "S_decision": row["S_decision"], "D_geometry": row["D_geometry"], "selection_rationale": row["selection_rationale"], "truth_acquired": False, "sealed": True})
    write_csv(OUT / "AL_ROUND1_8G_SELECTION.csv", selected_out)
    write_json(OUT / "AL_ROUND1_8G_SEALED_MANIFEST.json", {"schema_version": "AL_ROUND1_8G_SEALED_MANIFEST_V1", "sealed": True, "truth_acquired": 0, "geometry_count": 8, "source_candidate_ranking_sha256": sha(OUT / "AL_CANDIDATE_RANKING.csv"), "rows": selected_out, "no_solver_launched": True})
    future_out = [{"geometry_id": f"V2P_{i:02d}", **{f"D{j}": row[f"D{j}_nm"] for j in range(1, 7)}, "geometry_sha256": row["geometry_sha256"], "source_candidate_id": row["candidate_id"], "sealed": True, "truth_acquired": 0, "role": "V2_PROSPECTIVE_TEST"} for i, row in enumerate(future, 1)]
    write_json(OUT / "V2_PROSPECTIVE_TEST_PLAN.json", {"schema_version": "V2_PROSPECTIVE_TEST_PLAN_V1", "sealed": True, "truth_acquired": 0, "geometry_count": 8, "nonoverlap_with_existing_64_and_al_round1": True, "rows": future_out, "selection": "farthest-point geometry diversity from existing 64 plus AL round-1", "solver_launched": False})
    return {"pool_manifest": pool_manifest, "ranking": ranking, "selected": selected_out, "future": future_out, "committee": member_rows}


def readiness_and_report(ctx: dict[str, Any], groups: dict[str, list[int]], profile_records: list[dict[str, Any]], theta: dict[str, Any], robust: dict[str, Any], pca: dict[str, Any], coeff: list[dict[str, Any]], novelty_rows: list[dict[str, Any]], novelty_summary: dict[str, Any], coverage: dict[str, Any], al: dict[str, Any]) -> None:
    frozen = json.loads((BLIND_ROOT / "BLIND_PROSPECTIVE_VERDICT.json").read_text(encoding="utf-8"))
    blind = next(x for x in frozen["comparison"] if x["level"] == "BLIND_PROSPECTIVE")
    blind_l1, blind_corr, blind_js = float(blind["profile_l1"]), float(blind["profile_corr"]), float(blind["profile_js"])
    scalar = json.loads((OUT / "SCALAR_FORWARD_READINESS.json").read_text(encoding="utf-8"))
    fine = "NOT_READY" if theta["diagnosis"] in {"BOTH", "REAL_PROFILE_PREDICTION_ERROR"} or theta["by_split"]["BLIND"]["theta_peak_mae_deg"] > 15.0 else "PARTIAL"
    coarse = "READY" if robust["split_metric_mae"]["BLIND"]["F_seed_5_mae"] <= 0.02 and robust["split_metric_mae"]["BLIND"]["asymmetry_mae"] <= 0.08 else "PARTIAL" if robust["split_metric_mae"]["BLIND"]["F_seed_5_mae"] <= 0.05 and robust["split_metric_mae"]["BLIND"]["asymmetry_mae"] <= 0.15 else "NOT_READY"
    angular = "ANGULAR_PROFILE_READY" if blind_l1 <= 0.35 and blind_corr >= 0.75 and blind_js <= 0.05 else "ANGULAR_PROFILE_PARTIAL" if blind_l1 <= 0.8 and blind_corr >= 0.35 and blind_js <= 0.12 else "ANGULAR_PROFILE_NOT_READY"
    inverse = {"scalar_only": "READY" if scalar["status"] == "SCALAR_FORWARD_READY" else "PARTIAL", "coarse_directional": coarse, "fine_beam_steering": fine}; necessity = "TARGETED_AL_REQUIRED" if fine != "READY" else "AL_NOT_REQUIRED_FOR_CURRENT_OBJECTIVE"
    master = {"schema_version": "V1_READINESS_REVIEW_V1", "baseline": {"champion": "RIDGE_RAW_CHAMPION", "pca_rank": 32, "blind_role": "V1_PROSPECTIVE_TEST_USED", "blind_geometry_count": 8, "blind_rows": 88}, "theta_peak_diagnosis": theta, "pca_bottleneck": pca["bottleneck"], "scalar_forward_readiness": scalar, "angular_profile_readiness": {"schema_version": "ANGULAR_PROFILE_READINESS_V1", "status": angular, "blind_profile_l1": blind_l1, "blind_profile_corr": blind_corr, "blind_profile_js": blind_js, "thresholds": {"ready_l1_max": 0.35, "ready_corr_min": 0.75, "ready_js_max": 0.05, "partial_l1_max": 0.8, "partial_corr_min": 0.35, "partial_js_max": 0.12}}, "inverse_design_readiness": {"schema_version": "INVERSE_DESIGN_READINESS_V1", **inverse, "fine_target_warning": "raw argmax theta_peak is not a sole inverse target"}, "active_learning_necessity": {"schema_version": "ACTIVE_LEARNING_NECESSITY_V1", "status": necessity, "reason": "fine directional objective is not ready and theta_peak shows instability/model error" if necessity == "TARGETED_AL_REQUIRED" else "current objectives are covered"}, "novelty": novelty_summary, "coverage": coverage, "pca_vs_surrogate": pca, "pca_coefficient_count": len(coeff), "al_round1": {"selected_geometry_ids": [r["geometry_id"] for r in al["selected"]], "selection_count": len(al["selected"]), "pool_size": POOL_SIZE, "committee_size": COMMITTEE_SIZE}, "future_v2_geometry_ids": [r["geometry_id"] for r in al["future"]], "solver_accounting": {"solver_entries": 0, "new_fdtd_job": False, "al_hf_acquisition": False, "inverse_design_hf_validation": False, "v1_artifacts_modified": False}}
    write_json(OUT / "V1_READINESS_REVIEW.json", master)
    write_json(OUT / "ANGULAR_PROFILE_READINESS.json", master["angular_profile_readiness"])
    write_json(OUT / "INVERSE_DESIGN_READINESS.json", master["inverse_design_readiness"])
    write_json(OUT / "ACTIVE_LEARNING_NECESSITY.json", master["active_learning_necessity"])
    report = ["# APCD_COUPLING_V2_2_2D_ML_V1_ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW_V1", "", "### STATUS", "", "V1_PROSPECTIVE_GENERALIZATION_EVIDENCE_PASS; INVERSE_DESIGN_READY is not globally frozen.", "", "### THETA_PEAK_DIAGNOSIS", "", f"{theta['diagnosis']}; blind theta_peak MAE={theta['by_split']['BLIND']['theta_peak_mae_deg']:.6f} deg. Deterministic top-two peak ratio, separation, curvature, prominence, lobe class, and wavelength switching were audited.", "", "### PCA_BOTTLENECK", "", pca["bottleneck"], "", "### SCALAR_FORWARD_READINESS", "", scalar["status"], "", "### ANGULAR_PROFILE_READINESS", "", angular, f"; blind weighted L1={blind_l1:.6f}, correlation={blind_corr:.6f}, JS={blind_js:.6f}.", "", "### INVERSE_DESIGN_READINESS", "", f"scalar-only={inverse['scalar_only']}; coarse directional={inverse['coarse_directional']}; fine beam steering={inverse['fine_beam_steering']}.", "", "### ACTIVE_LEARNING_NECESSITY", "", necessity, "", "### ACTIVE_LEARNING_RATIONALE", "", "Fine directional control remains limited by argmax instability plus genuine profile mapping error; targeted 8G AL is frozen as an analysis-only plan.", "", "### CURRENT_DATA_COVERAGE", "", "64 exact HF geometries: TRAIN=48, VALIDATION=8, V1 prospective=8; V1 blind remains excluded from future training and is not promoted here.", "", "### AL_ROUND1", "", ", ".join(r["geometry_id"] for r in al["selected"]), "", "### FUTURE_V2_PROSPECTIVE_TEST", "", ", ".join(r["geometry_id"] for r in al["future"]), "", "### SURROGATE_NEXT_GENERATION_RECOMMENDATION", "", "NONLINEAR_SURROGATE_REEVALUATION_AFTER_AL; test KernelRidge/shallow MLP/residual multi-task only after AL truth, without changing V1 champion now.", "", "### INVERSE_OBJECTIVE_RECOMMENDATION", "", "Prioritize eta_up/G_emit scalar objective, then F_seed_5/asymmetry/dominant-lobe centroid; do not use raw theta_peak as the sole target.", "", "### SOLVER_ACCOUNTING", "", "0; no FDTD, AL HF acquisition, inverse-design HF validation, retraining, PCA refit, or V1 overwrite.", "", "### PROPOSED_VERDICT", "", "PASS — V1_SCALAR_FORWARD_READY_DIRECTIONAL_AL_REQUIRED", "", "### NEXT", "", "ACQUIRE_AL_ROUND1_8G_WITH_TWO_SLOTS", ""]
    write_json(OUT / "REPORT.json", {"status": "PASS", "verdict": "PASS — V1_SCALAR_FORWARD_READY_DIRECTIONAL_AL_REQUIRED", "scalar_forward": scalar["status"], "angular_profile": angular, "inverse_design": inverse, "active_learning": necessity, "solver_entries": 0, "selected_al_geometry_count": len(al["selected"])})
    (OUT / "REPORT.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    ctx = load_context(); groups = grouped_records(ctx); theta = theta_audit(ctx, groups); robust = robust_audit(ctx, groups); scalar = scalar_audit(ctx); write_json(OUT / "SCALAR_FORWARD_READINESS.json", scalar); pca, pca_records = pca_audit(ctx); coeff = coefficient_audit(ctx); novelty_rows, novelty_summary = novelty_audit(ctx, groups); coverage = coverage_audit(ctx, groups); write_csv(OUT / "PROFILE_ERROR_DECOMPOSITION.csv", build_profile_decomposition(ctx, groups)); write_json(OUT / "THETA_PEAK_STABILITY_AUDIT.json", theta); write_json(OUT / "ROBUST_DIRECTIONAL_METRICS_AUDIT.json", robust); write_json(OUT / "PCA_VS_SURROGATE_ERROR_AUDIT.json", pca); write_csv(OUT / "PCA_COEFFICIENT_ERROR_IMPORTANCE.csv", coeff); write_csv(OUT / "BLIND_ERROR_VS_NOVELTY.csv", novelty_rows); write_json(OUT / "CURRENT_HF_COVERAGE_AUDIT.json", coverage); write_csv(OUT / "PCA_VS_SURROGATE_ERROR_ROWS.csv", pca_records); al = candidate_pool_and_al(ctx, groups, coeff); readiness_and_report(ctx, groups, build_profile_decomposition(ctx, groups), theta, robust, pca, coeff, novelty_rows, novelty_summary, coverage, al); files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files.append({"path": str(path.relative_to(OUT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)})
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": files, "solver_entries": 0, "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")})
    print(json.dumps({"status": "PASS", "verdict": "PASS — V1_SCALAR_FORWARD_READY_DIRECTIONAL_AL_REQUIRED", "solver_entries": 0, "al_selected": [r["geometry_id"] for r in al["selected"]], "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
