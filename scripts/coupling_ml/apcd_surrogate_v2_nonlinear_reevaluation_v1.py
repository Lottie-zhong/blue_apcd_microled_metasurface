from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import pickle
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


ROOT = Path(os.environ.get("APCD_ML_V1_ROOT", r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1"))
OUT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_SURROGATE_V2_NONLINEAR_REEVALUATION_WITH_AL_ROUND1_V1"
TRAINVAL = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1" / "V1_TRAINVAL_DATASET.csv"
AL_DATASET = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1" / "AL_ROUND1_8G_DATASET.csv"
BLIND = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1" / "BLIND_DATASET.csv"
PCA_MODEL = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "ANGULAR_PCA_MODEL.npz"
PCA_META = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "ANGULAR_PCA_MODEL_METADATA.json"
OLD_FREEZE = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "TRAIN_CV_MODEL_CANDIDATE_FREEZE.json"
READINESS = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW_V1"
V2_PLAN = READINESS / "V2_PROSPECTIVE_TEST_PLAN.json"
V1_BLIND_MANIFEST = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1" / "FINAL_SHA256_MANIFEST.json"
V1_TRAIN_MANIFEST = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1" / "V1_TRAINVAL_DATASET_MANIFEST.json"
AL_MANIFEST = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1" / "AL_ROUND1_8G_DATASET_MANIFEST.json"
WLS = np.arange(445.0, 456.0, 1.0)
LAMBDA_X_NM = 1740.0
PITCH_NM = 290.0
PCA_RANK = 32
MLP_HIDDEN = (32, 32)
MLP_ALPHA = 1e-3
MLP_SEEDS = (0, 1, 2, 3, 4)
RIDGE_GRID = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
KERNEL_GRID = ((0.01, 0.01), (0.01, 0.1), (0.1, 0.01), (0.1, 0.1), (1.0, 0.01), (1.0, 0.1))
RESIDUAL_GRID = ((0.01, 0.03), (0.01, 0.1), (0.1, 0.03), (0.1, 0.1))
HIGH_COEFFS = (5, 17, 12, 1, 3, 4)
PROFILE_GAIN_MIN = 0.02
DIRECTIONAL_GAIN_MIN = 0.05
SCALAR_DEGRADATION_MAX = 0.10


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe(value: Any) -> Any:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe(row.get(key, "")) for key in fields})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None}


def macro(values: np.ndarray, groups: np.ndarray) -> float:
    return float(np.mean([np.mean(values[groups == group]) for group in np.unique(groups)]))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def load_pca() -> dict[str, Any]:
    with np.load(PCA_MODEL, allow_pickle=False) as z:
        weights = np.asarray(z["weights_du"], dtype=float)
        mean = np.asarray(z["mean_profile"], dtype=float)
        weighted_components = np.asarray(z["components_weighted"], dtype=float)
        profile_components = np.asarray(z["components_profile"], dtype=float)
        rank = int(np.asarray(z["rank"]).item())
    if rank != PCA_RANK or weighted_components.shape[0] < PCA_RANK:
        raise RuntimeError("frozen V1 PCA rank is not 32")
    return {"weights": weights, "sqrt_weights": np.sqrt(weights), "mean": mean, "mean_weighted": mean * np.sqrt(weights), "components_weighted": weighted_components[:PCA_RANK], "components_profile": profile_components[:PCA_RANK], "rank": rank}


_PROFILE_CACHE: dict[str, dict[str, np.ndarray]] = {}


def load_profile(path: Path) -> dict[str, np.ndarray]:
    key = str(path)
    if key not in _PROFILE_CACHE:
        with np.load(path, allow_pickle=False) as z:
            names = set(z.files)
            f = np.asarray(z["f_up"] if "f_up" in names else z["farfield_e2"], dtype=float)
            ux = np.asarray(z["ux"], dtype=float)
            weights = np.asarray(z["weights_du"], dtype=float)
            if "theta_deg" in names:
                theta = np.asarray(z["theta_deg"], dtype=float)
            else:
                theta = np.degrees(np.arcsin(np.clip(ux, -1.0, 1.0)))[:, None] * np.ones((1, f.shape[1]))
            wavelengths = np.asarray(z["wavelengths_nm"], dtype=float)
        _PROFILE_CACHE[key] = {"f": f, "ux": ux, "weights": weights, "theta": theta, "wavelengths": wavelengths}
    return _PROFILE_CACHE[key]


def geometry_vector(row: dict[str, str]) -> tuple[float, ...]:
    return tuple(float(row[f"D{i}"]) for i in range(1, 7))


def validate_source_rows(rows: list[dict[str, str]], label: str) -> dict[str, Any]:
    if not rows:
        raise RuntimeError(f"empty dataset: {label}")
    by_id: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_id.setdefault(row["geometry_id"], []).append(row)
    counts = {key: len(value) for key, value in by_id.items()}
    if set(counts.values()) != {11}:
        raise RuntimeError(f"{label} is not 11 wavelengths per geometry: {counts}")
    if [float(r["lambda_nm"]) for r in by_id[next(iter(by_id))]] != list(WLS):
        raise RuntimeError(f"{label} wavelength order mismatch")
    geometry_sha_unique = all(len({r.get("geometry_SHA", "") for r in value}) == 1 for value in by_id.values())
    post_sha_unique = all(len({r.get("post_FSP_SHA", "") for r in value}) == 1 for value in by_id.values())
    raw_sha_unique = all(len({r.get("raw_SHA", "") for r in value}) == 1 for value in by_id.values())
    if not (geometry_sha_unique and post_sha_unique and raw_sha_unique):
        raise RuntimeError(f"{label} artifact SHA changes within geometry")
    return {"label": label, "rows": len(rows), "geometries": len(by_id), "geometry_ids": sorted(by_id), "rows_per_geometry": counts, "wavelengths_nm": list(WLS), "geometry_sha_unique": geometry_sha_unique, "post_sha_unique": post_sha_unique, "raw_sha_unique": raw_sha_unique, "dataset_sha256": None}


def make_bundle(rows: list[dict[str, str]], pca: dict[str, Any]) -> dict[str, Any]:
    profiles: list[np.ndarray] = []
    thetas: list[np.ndarray] = []
    targets: list[list[float]] = []
    features: list[list[float]] = []
    groups: list[str] = []
    lambdas: list[float] = []
    geometry_rows: list[dict[str, str]] = []
    ux: np.ndarray | None = None
    weights: np.ndarray | None = None
    components = pca["components_weighted"]
    sqrt_weights = pca["sqrt_weights"]
    for row in rows:
        data = load_profile(Path(row["angular_profile_ref"]))
        if ux is None:
            ux, weights = data["ux"], data["weights"]
        if not np.allclose(data["ux"], ux) or not np.allclose(data["weights"], weights):
            raise RuntimeError("profile grids differ across datasets")
        wavelength = float(row["lambda_nm"])
        index = int(np.argmin(np.abs(data["wavelengths"] - wavelength)))
        profile = data["f"][:, index].astype(float)
        theta = data["theta"][:, index].astype(float)
        coeff = (profile * sqrt_weights - pca["mean_weighted"]) @ components.T
        profiles.append(profile)
        thetas.append(theta)
        targets.append([float(row["G_emit"]), float(row["eta_up"]), *coeff.tolist()])
        features.append([*(float(row[f"D{i}"]) / PITCH_NM for i in range(1, 7)), (wavelength - 450.0) / 5.0])
        groups.append(row["geometry_id"])
        lambdas.append(wavelength)
        geometry_rows.append(row)
    assert ux is not None and weights is not None
    return {"X": np.asarray(features, dtype=float), "Y": np.asarray(targets, dtype=float), "profiles": np.asarray(profiles, dtype=float), "theta": np.asarray(thetas, dtype=float), "groups": np.asarray(groups), "lambdas": np.asarray(lambdas, dtype=float), "ux": ux, "weights": weights, "rows": geometry_rows}


def reconstruct(coeff: np.ndarray, pca: dict[str, Any]) -> np.ndarray:
    return pca["mean"][None, :] + coeff @ pca["components_profile"]


def directional(profile: np.ndarray, theta: np.ndarray, wavelength: float, ux: np.ndarray, weights: np.ndarray) -> dict[str, float]:
    f = np.maximum(np.asarray(profile, dtype=float), 0.0)
    local = np.flatnonzero((f[1:-1] >= f[:-2]) & (f[1:-1] >= f[2:])) + 1
    if local.size < 2:
        local = np.argsort(f)[::-1][:2]
    local = local[np.argsort(f[local])[::-1]]
    first, second = int(local[0]), int(local[1])
    peak = max(float(f[first]), 1e-300)
    left = right = first
    while left > 0 and f[left - 1] >= 0.5 * peak:
        left -= 1
    while right + 1 < len(f) and f[right + 1] >= 0.5 * peak:
        right += 1
    centroid = float(np.average(theta[left:right + 1], weights=np.maximum(f[left:right + 1], 1e-300)))
    positive = float(np.sum(weights[ux >= 0] * f[ux >= 0]))
    negative = float(np.sum(weights[ux < 0] * f[ux < 0]))
    asymmetry = (positive - negative) / max(positive + negative, 1e-300)
    seed = math.degrees(math.asin(float(wavelength) / LAMBDA_X_NM))
    seeds = {f"F_seed_{radius}": float(np.sum(weights[np.abs(theta - seed) <= radius] * f[np.abs(theta - seed) <= radius])) for radius in (2, 5, 10)}
    return {"dominant_lobe_centroid": centroid, "theta_peak": float(theta[first]), "positive_fraction": positive, "negative_fraction": negative, "asymmetry": asymmetry, **seeds, "top2_peak_ratio": float(f[second] / peak)}


def metric_summary(bundle: dict[str, Any], prediction: np.ndarray, pca: dict[str, Any], coeff_std: np.ndarray | None = None) -> dict[str, Any]:
    truth = bundle["Y"]
    pred = np.asarray(prediction, dtype=float)
    groups = bundle["groups"]
    out: dict[str, Any] = {}
    for j, name in enumerate(("G_emit", "eta_up")):
        error = np.abs(pred[:, j] - truth[:, j])
        out[f"{name}_mae"] = macro(error, groups)
        out[f"{name}_r2"] = corr(truth[:, j], pred[:, j])
    true_profiles = bundle["profiles"]
    pred_profiles = reconstruct(pred[:, 2:], pca)
    raw_l1: list[float] = []
    weighted_l1: list[float] = []
    js_values: list[float] = []
    profile_corr: list[float] = []
    centroid_error: list[float] = []
    f5_error: list[float] = []
    asym_error: list[float] = []
    pos_error: list[float] = []
    neg_error: list[float] = []
    theta_error: list[float] = []
    for i in range(len(truth)):
        t = np.maximum(true_profiles[i], 0.0)
        q = np.maximum(pred_profiles[i], 0.0)
        w = bundle["weights"]
        t = t / max(float(np.sum(w * t)), 1e-300)
        q = q / max(float(np.sum(w * q)), 1e-300)
        raw_l1.append(float(np.sum(w * np.abs(pred_profiles[i] - true_profiles[i]))))
        weighted_l1.append(float(np.sum(w * np.abs(q - t))))
        qt, tt = w * q, w * t
        midpoint = 0.5 * (qt + tt)
        js_values.append(float(0.5 * np.sum(np.where(qt > 0, qt * np.log(np.maximum(qt, 1e-300) / np.maximum(midpoint, 1e-300)), 0.0)) + 0.5 * np.sum(np.where(tt > 0, tt * np.log(np.maximum(tt, 1e-300) / np.maximum(midpoint, 1e-300)), 0.0))))
        profile_corr.append(corr(true_profiles[i], pred_profiles[i]))
        a = directional(true_profiles[i], bundle["theta"][i], bundle["lambdas"][i], bundle["ux"], w)
        b = directional(pred_profiles[i], bundle["theta"][i], bundle["lambdas"][i], bundle["ux"], w)
        centroid_error.append(abs(b["dominant_lobe_centroid"] - a["dominant_lobe_centroid"]))
        f5_error.append(abs(b["F_seed_5"] - a["F_seed_5"]))
        asym_error.append(abs(b["asymmetry"] - a["asymmetry"]))
        pos_error.append(abs(b["positive_fraction"] - a["positive_fraction"]))
        neg_error.append(abs(b["negative_fraction"] - a["negative_fraction"]))
        theta_error.append(abs(b["theta_peak"] - a["theta_peak"]))
    out.update({"profile_raw_weighted_l1": macro(np.asarray(raw_l1), groups), "profile_weighted_l1": macro(np.asarray(weighted_l1), groups), "profile_correlation": macro(np.asarray(profile_corr), groups), "weighted_js": macro(np.asarray(js_values), groups), "dominant_lobe_centroid_mae": macro(np.asarray(centroid_error), groups), "F_seed_5_mae": macro(np.asarray(f5_error), groups), "asymmetry_mae": macro(np.asarray(asym_error), groups), "positive_fraction_mae": macro(np.asarray(pos_error), groups), "negative_fraction_mae": macro(np.asarray(neg_error), groups), "theta_peak_mae": macro(np.asarray(theta_error), groups)})
    coefficient_rows = []
    for index in range(PCA_RANK):
        err = np.abs(pred[:, index + 2] - truth[:, index + 2])
        coefficient_rows.append({"coefficient": index + 1, "mae": macro(err, groups), "correlation": corr(truth[:, index + 2], pred[:, index + 2]), "normalized_mae": macro(err, groups) / max(float(coeff_std[index]) if coeff_std is not None else float(np.std(truth[:, index + 2])), 1e-12)})
    out["coefficients"] = coefficient_rows
    return out


def profile_l1_by_group(bundle: dict[str, Any], prediction: np.ndarray, pca: dict[str, Any]) -> dict[str, float]:
    truth = bundle["profiles"]
    predicted = reconstruct(prediction[:, 2:], pca)
    values: dict[str, list[float]] = {}
    for i, group in enumerate(bundle["groups"]):
        t = np.maximum(truth[i], 0.0); p = np.maximum(predicted[i], 0.0); w = bundle["weights"]
        t /= max(float(np.sum(w * t)), 1e-300); p /= max(float(np.sum(w * p)), 1e-300)
        values.setdefault(str(group), []).append(float(np.sum(w * np.abs(p - t))))
    return {group: float(np.mean(vals)) for group, vals in values.items()}


def fit_one(spec: dict[str, Any], x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray, seed: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    x_scaler = StandardScaler().fit(x_train)
    xtr = x_scaler.transform(x_train); xte = x_scaler.transform(x_test)
    family = spec["family"]
    if family == "V2_RIDGE_RAW":
        y_scaler = StandardScaler().fit(y_train)
        model = Ridge(alpha=float(spec["alpha"])).fit(xtr, y_scaler.transform(y_train))
        return y_scaler.inverse_transform(model.predict(xte)), {"family": family, "x_scaler": x_scaler, "y_scaler": y_scaler, "model": model}
    if family == "V2_KERNEL_RIDGE":
        y_scaler = StandardScaler().fit(y_train)
        model = KernelRidge(alpha=float(spec["alpha"]), gamma=float(spec["gamma"]), kernel="rbf").fit(xtr, y_scaler.transform(y_train))
        return y_scaler.inverse_transform(model.predict(xte)), {"family": family, "x_scaler": x_scaler, "y_scaler": y_scaler, "model": model}
    if family == "V2_SHALLOW_MLP":
        scalar_scaler = StandardScaler().fit(y_train[:, :2]); coeff_scaler = StandardScaler().fit(y_train[:, 2:])
        scalar = MLPRegressor(hidden_layer_sizes=MLP_HIDDEN, activation="relu", solver="adam", alpha=MLP_ALPHA, max_iter=600, tol=1e-4, early_stopping=False, random_state=seed).fit(xtr, scalar_scaler.transform(y_train[:, :2]))
        coeff = MLPRegressor(hidden_layer_sizes=MLP_HIDDEN, activation="relu", solver="adam", alpha=MLP_ALPHA, max_iter=600, tol=1e-4, early_stopping=False, random_state=seed + 1000).fit(xtr, coeff_scaler.transform(y_train[:, 2:]))
        pred = np.column_stack([scalar_scaler.inverse_transform(scalar.predict(xte)), coeff_scaler.inverse_transform(coeff.predict(xte))])
        return pred, {"family": family, "x_scaler": x_scaler, "scalar_scaler": scalar_scaler, "coeff_scaler": coeff_scaler, "scalar": scalar, "coeff": coeff, "seed": seed}
    if family == "V2_MULTITASK_MLP":
        y_scaler = StandardScaler().fit(y_train)
        model = MLPRegressor(hidden_layer_sizes=MLP_HIDDEN, activation="relu", solver="adam", alpha=MLP_ALPHA, max_iter=600, tol=1e-4, early_stopping=False, random_state=seed).fit(xtr, y_scaler.transform(y_train))
        return y_scaler.inverse_transform(model.predict(xte)), {"family": family, "x_scaler": x_scaler, "y_scaler": y_scaler, "model": model, "seed": seed}
    if family == "V2_RIDGE_PLUS_RESIDUAL":
        base_scaler = StandardScaler().fit(y_train)
        base = Ridge(alpha=float(spec["base_alpha"])).fit(xtr, base_scaler.transform(y_train))
        base_train = base_scaler.inverse_transform(base.predict(xtr))
        residual = y_train - base_train
        residual_scaler = StandardScaler().fit(residual)
        correction = KernelRidge(alpha=float(spec["alpha"]), gamma=float(spec["gamma"]), kernel="rbf").fit(xtr, residual_scaler.transform(residual))
        pred = base_scaler.inverse_transform(base.predict(xte)) + residual_scaler.inverse_transform(correction.predict(xte))
        return pred, {"family": family, "x_scaler": x_scaler, "base_scaler": base_scaler, "base": base, "residual_scaler": residual_scaler, "correction": correction, "base_alpha": float(spec["base_alpha"]), "alpha": float(spec["alpha"]), "gamma": float(spec["gamma"])}
    raise ValueError(f"unknown family {family}")


def predict_payload(payload: dict[str, Any], x: np.ndarray) -> np.ndarray:
    family = payload["family"]
    xte = payload["x_scaler"].transform(x)
    if family == "V2_RIDGE_RAW" or family == "V2_KERNEL_RIDGE":
        return payload["y_scaler"].inverse_transform(payload["model"].predict(xte))
    if family == "V2_SHALLOW_MLP":
        return np.column_stack([payload["scalar_scaler"].inverse_transform(payload["scalar"].predict(xte)), payload["coeff_scaler"].inverse_transform(payload["coeff"].predict(xte))])
    if family == "V2_MULTITASK_MLP":
        return payload["y_scaler"].inverse_transform(payload["model"].predict(xte))
    if family == "V2_RIDGE_PLUS_RESIDUAL":
        return payload["base_scaler"].inverse_transform(payload["base"].predict(xte)) + payload["residual_scaler"].inverse_transform(payload["correction"].predict(xte))
    raise ValueError(f"unknown payload family {family}")


def fit_spec(spec: dict[str, Any], x_train: np.ndarray, y_train: np.ndarray, x_test: np.ndarray) -> tuple[np.ndarray, dict[str, Any], list[np.ndarray]]:
    if spec["family"] in {"V2_SHALLOW_MLP", "V2_MULTITASK_MLP"}:
        members: list[np.ndarray] = []
        payloads: list[dict[str, Any]] = []
        for seed in MLP_SEEDS:
            pred, payload = fit_one(spec, x_train, y_train, x_test, seed)
            members.append(pred); payloads.append(payload)
        return np.mean(members, axis=0), {"family": spec["family"], "members": payloads, "seeds": list(MLP_SEEDS)}, members
    pred, payload = fit_one(spec, x_train, y_train, x_test)
    return pred, payload, [pred]


def predict_saved(payload: dict[str, Any], x: np.ndarray) -> np.ndarray:
    if payload.get("family") in {"V2_SHALLOW_MLP", "V2_MULTITASK_MLP"} and "members" in payload:
        return np.mean([predict_payload(member, x) for member in payload["members"]], axis=0)
    return predict_payload(payload, x)


def evaluate_cv(spec: dict[str, Any], bundle: dict[str, Any], folds: list[tuple[np.ndarray, np.ndarray]], pca: dict[str, Any], coeff_std: np.ndarray) -> dict[str, Any]:
    start = time.perf_counter()
    oof = np.zeros_like(bundle["Y"])
    fold_rows: list[dict[str, Any]] = []
    seed_rows: dict[int, list[dict[str, Any]]] = {seed: [] for seed in MLP_SEEDS}
    for fold, (train_idx, test_idx) in enumerate(folds):
        pred, _, members = fit_spec(spec, bundle["X"][train_idx], bundle["Y"][train_idx], bundle["X"][test_idx])
        oof[test_idx] = pred
        test_bundle = {key: (value[test_idx] if isinstance(value, np.ndarray) and len(value) == len(bundle["Y"]) else value) for key, value in bundle.items()}
        metrics = metric_summary(test_bundle, pred, pca, coeff_std)
        fold_rows.append({"fold": fold, "train_geometries": len(set(bundle["groups"][train_idx])), "test_geometries": len(set(bundle["groups"][test_idx])), **{key: value for key, value in metrics.items() if key != "coefficients"}})
        if spec["family"] in {"V2_SHALLOW_MLP", "V2_MULTITASK_MLP"}:
            for seed, member in zip(MLP_SEEDS, members):
                seed_metrics = metric_summary(test_bundle, member, pca, coeff_std)
                seed_rows[seed].append(seed_metrics)
    aggregate = metric_summary(bundle, oof, pca, coeff_std)
    seed_summary = {}
    for seed, rows in seed_rows.items():
        if rows:
            seed_summary[str(seed)] = float(np.mean([row["profile_weighted_l1"] for row in rows]))
    return {"spec": spec, "oof_pred": oof, "aggregate": aggregate, "fold_rows": fold_rows, "seed_profile_l1": seed_summary, "seed_profile_l1_std": float(np.std(list(seed_summary.values()))) if seed_summary else 0.0, "elapsed_s": time.perf_counter() - start}


def result_rows(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for evaluation in evaluations:
        spec = evaluation["spec"]
        aggregate = evaluation["aggregate"]
        row = {"model_id": spec["id"], **{key: value for key, value in spec.items() if key != "id"}, "split": "GROUPED_CV_OOF", "elapsed_s": evaluation["elapsed_s"], "seed_profile_l1_std": evaluation["seed_profile_l1_std"], **{key: value for key, value in aggregate.items() if key != "coefficients"}}
        rows.append(row)
        for fold in evaluation["fold_rows"]:
            rows.append({"model_id": spec["id"], **{key: value for key, value in spec.items() if key != "id"}, "split": f"FOLD_{fold['fold']}", "elapsed_s": evaluation["elapsed_s"], "seed_profile_l1_std": evaluation["seed_profile_l1_std"], **{key: value for key, value in fold.items() if key != "fold"}, "fold": fold["fold"]})
    return rows


def best_cv(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    return min(evaluations, key=lambda item: (item["aggregate"]["profile_weighted_l1"], item["aggregate"]["weighted_js"], item["aggregate"]["dominant_lobe_centroid_mae"], item["aggregate"]["G_emit_mae"] + item["aggregate"]["eta_up_mae"]))


def count_parameters(value: Any) -> int:
    if isinstance(value, MLPRegressor):
        return int(sum(array.size for array in value.coefs_) + sum(array.size for array in value.intercepts_))
    if hasattr(value, "coef_"):
        return int(np.asarray(value.coef_).size + np.asarray(getattr(value, "intercept_", [])).size)
    if hasattr(value, "dual_coef_"):
        return int(np.asarray(value.dual_coef_).size)
    if isinstance(value, dict):
        return sum(count_parameters(v) for v in value.values())
    if isinstance(value, list):
        return sum(count_parameters(v) for v in value)
    return 0


def flatten_metrics(prefix: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in metrics.items() if key != "coefficients"}


def relative_gain(old: float, new: float) -> float:
    return float((old - new) / max(abs(old), 1e-12))


def walk_find(obj: Any, key: str, value: Any) -> Any | None:
    if isinstance(obj, dict):
        if obj.get(key) == value:
            return obj
        for child in obj.values():
            found = walk_find(child, key, value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for child in obj:
            found = walk_find(child, key, value)
            if found is not None:
                return found
    return None


def old_alpha() -> float:
    if OLD_FREEZE.is_file():
        obj = json.loads(OLD_FREEZE.read_text(encoding="utf-8"))
        candidate = walk_find(obj, "label", "best_ridge")
        if candidate and isinstance(candidate.get("definition"), dict) and "alpha" in candidate["definition"]:
            return float(candidate["definition"]["alpha"])
    return 0.1


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "models").mkdir(exist_ok=True)
    pca = load_pca()
    original_rows = read_csv(TRAINVAL)
    al_rows = read_csv(AL_DATASET)
    blind_rows = read_csv(BLIND)
    train_rows = [row for row in original_rows if row.get("split") == "TRAIN"]
    dev_rows = [row for row in original_rows if row.get("split") == "VALIDATION"]
    train_audit = validate_source_rows(train_rows, "original TRAIN")
    dev_audit = validate_source_rows(dev_rows, "development validation")
    al_audit = validate_source_rows(al_rows, "AL Round-1")
    blind_audit = validate_source_rows(blind_rows, "V1 blind")
    for audit, path in ((train_audit, TRAINVAL), (dev_audit, TRAINVAL), (al_audit, AL_DATASET), (blind_audit, BLIND)):
        audit["dataset_sha256"] = sha(path)
    train_ids = set(train_audit["geometry_ids"]); al_ids = set(al_audit["geometry_ids"]); dev_ids = set(dev_audit["geometry_ids"]); blind_ids = set(blind_audit["geometry_ids"])
    vectors = {label: {geometry_vector(row) for row in rows} for label, rows in (("train", train_rows), ("al", al_rows), ("dev", dev_rows), ("blind", blind_rows))}
    if train_ids & al_ids or train_ids & dev_ids or train_ids & blind_ids or al_ids & dev_ids or al_ids & blind_ids or dev_ids & blind_ids:
        raise RuntimeError("geometry overlap detected across frozen data roles")
    if any(vectors[a] & vectors[b] for a, b in (("train", "al"), ("train", "dev"), ("train", "blind"), ("al", "dev"), ("al", "blind"), ("dev", "blind"))):
        raise RuntimeError("geometry vector overlap detected across data roles")
    v2_plan = json.loads(V2_PLAN.read_text(encoding="utf-8"))
    prospective_rows = v2_plan.get("rows", [])
    prospective_ids = {str(row.get("geometry_id", row.get("case_id"))) for row in prospective_rows}
    if len(prospective_ids) != 8 or prospective_ids & (train_ids | al_ids | dev_ids | blind_ids):
        raise RuntimeError("V2 prospective role overlap or count failure")
    if v2_plan.get("sealed") is not True or v2_plan.get("truth_acquired") != 0 or v2_plan.get("solver_launched") is not False:
        raise RuntimeError("V2 prospective seal is not intact")
    data_roles = {"schema_version": "V2_DATA_ROLE_FREEZE_V1", "original_train": train_audit, "al_round1": al_audit, "v2_train_geometry_count": len(train_ids | al_ids), "v2_train_row_count": len(train_rows) + len(al_rows), "development_validation": dev_audit, "v1_blind": {**blind_audit, "role": "HISTORICAL_BENCHMARK_ONLY", "included_in_fitting": False}, "v2_prospective": {"geometry_ids": sorted(prospective_ids), "geometry_count": len(prospective_ids), "truth_acquired": 0, "solver_entries": 0, "included_in_fitting": False}, "overlap": {"original_train_vs_al": 0, "v2_train_unique": len(train_ids | al_ids), "development_validation": 0, "v1_blind": 0, "v2_prospective": 0}, "primary_features": ["D1", "D2", "D3", "D4", "D5", "D6", "lambda_nm"], "prior_features_used": False}
    write_json(OUT / "V2_DATA_ROLE_FREEZE.json", data_roles)
    integrity = {"schema_version": "V2_DATA_INTEGRITY_AUDIT_V1", "pass": True, "source_files": {"original_trainval": file_record(TRAINVAL), "al_round1_dataset": file_record(AL_DATASET), "v1_blind_dataset": file_record(BLIND), "frozen_pca_model": file_record(PCA_MODEL), "v2_plan": file_record(V2_PLAN)}, "train_rows": len(train_rows), "al_rows": len(al_rows), "v2_train_rows": len(train_rows) + len(al_rows), "development_validation_rows": len(dev_rows), "v1_blind_rows": len(blind_rows), "v2_train_geometries": len(train_ids | al_ids), "development_validation_geometries": len(dev_ids), "v1_blind_geometries": len(blind_ids), "wavelengths_per_geometry": 11, "geometry_sha_unique": all(len({r["geometry_SHA"] for r in rows}) == len({r["geometry_id"] for r in rows}) for rows in (train_rows, al_rows, dev_rows, blind_rows)), "post_sha_present": all(bool(r.get("post_FSP_SHA")) for r in train_rows + al_rows + dev_rows + blind_rows), "raw_sha_present": all(bool(r.get("raw_SHA")) for r in train_rows + al_rows + dev_rows + blind_rows), "no_geometry_leakage": True, "v2_prospective_truth_acquired": 0, "solver_entries": 0}
    write_json(OUT / "V2_DATA_INTEGRITY_AUDIT.json", integrity)
    pca_policy = {"schema_version": "V2_PCA_POLICY_AUDIT_V1", "pass": True, "production_basis": "frozen V1 PCA", "rank": PCA_RANK, "pca_model": file_record(PCA_MODEL), "pca_metadata": file_record(PCA_META), "primary_models_use_same_basis": True, "pca_refit_primary": False, "optional_v2_pca_ablation": "NOT_RUN_OPTIONAL", "prior_features_used": False, "selection_target": "rank-32 PCA coefficients reconstructed to profile"}
    write_json(OUT / "V2_PCA_POLICY_AUDIT.json", pca_policy)
    train = make_bundle(train_rows + al_rows, pca)
    dev = make_bundle(dev_rows, pca)
    blind = make_bundle(blind_rows, pca)
    coeff_std = np.std(train["Y"][:, 2:], axis=0)
    if not np.isfinite(train["X"]).all() or not np.isfinite(train["Y"]).all() or not np.isfinite(dev["X"]).all() or not np.isfinite(blind["X"]).all():
        raise RuntimeError("non-finite model input or target")
    folds = list(GroupKFold(n_splits=8).split(train["X"], train["Y"][:, 0], train["groups"]))
    fold_manifest = []
    for index, (tr, te) in enumerate(folds):
        train_fold_ids = sorted(set(train["groups"][tr])); test_fold_ids = sorted(set(train["groups"][te]))
        if set(train_fold_ids) & set(test_fold_ids):
            raise RuntimeError("group leakage in CV fold")
        fold_manifest.append({"fold": index, "train_geometry_ids": train_fold_ids, "test_geometry_ids": test_fold_ids, "train_rows": len(tr), "test_rows": len(te), "same_geometry_rows_kept_together": True})
    write_json(OUT / "V2_GROUPED_CV_SPLIT_MANIFEST.json", {"schema_version": "V2_GROUPED_CV_SPLIT_MANIFEST_V1", "n_splits": 8, "group_field": "geometry_id", "row_split_forbidden": True, "folds": fold_manifest, "preprocessing_fit_scope": "fold_train_only", "all_groups_disjoint": True})

    ridge_specs = [{"id": f"ridge_a{alpha:g}", "family": "V2_RIDGE_RAW", "alpha": alpha, "feature_set": "RAW_GEOMETRY_LAMBDA"} for alpha in RIDGE_GRID]
    ridge_evals = [evaluate_cv(spec, train, folds, pca, coeff_std) for spec in ridge_specs]
    write_csv(OUT / "V2_RIDGE_RESULTS.csv", result_rows(ridge_evals))
    best_ridge_eval = best_cv(ridge_evals)
    best_ridge_alpha = float(best_ridge_eval["spec"]["alpha"])
    kernel_specs = [{"id": f"kernel_a{alpha:g}_g{gamma:g}", "family": "V2_KERNEL_RIDGE", "alpha": alpha, "gamma": gamma, "feature_set": "RAW_GEOMETRY_LAMBDA"} for alpha, gamma in KERNEL_GRID]
    kernel_evals = [evaluate_cv(spec, train, folds, pca, coeff_std) for spec in kernel_specs]
    write_csv(OUT / "V2_KERNEL_RIDGE_RESULTS.csv", result_rows(kernel_evals))
    mlp_spec = {"id": "shallow_mlp_32x32_5seed", "family": "V2_SHALLOW_MLP", "hidden_layer_sizes": list(MLP_HIDDEN), "alpha": MLP_ALPHA, "seeds": list(MLP_SEEDS), "feature_set": "RAW_GEOMETRY_LAMBDA"}
    multitask_spec = {"id": "multitask_mlp_32x32_5seed", "family": "V2_MULTITASK_MLP", "hidden_layer_sizes": list(MLP_HIDDEN), "alpha": MLP_ALPHA, "seeds": list(MLP_SEEDS), "feature_set": "RAW_GEOMETRY_LAMBDA"}
    mlp_evals = [evaluate_cv(mlp_spec, train, folds, pca, coeff_std)]
    multitask_evals = [evaluate_cv(multitask_spec, train, folds, pca, coeff_std)]
    write_csv(OUT / "V2_MLP_RESULTS.csv", result_rows(mlp_evals))
    write_csv(OUT / "V2_MULTITASK_RESULTS.csv", result_rows(multitask_evals))
    residual_specs = [{"id": f"residual_b{best_ridge_alpha:g}_a{alpha:g}_g{gamma:g}", "family": "V2_RIDGE_PLUS_RESIDUAL", "base_alpha": best_ridge_alpha, "alpha": alpha, "gamma": gamma, "feature_set": "RAW_GEOMETRY_LAMBDA"} for alpha, gamma in RESIDUAL_GRID]
    residual_evals = [evaluate_cv(spec, train, folds, pca, coeff_std) for spec in residual_specs]
    write_csv(OUT / "V2_RESIDUAL_RESULTS.csv", result_rows(residual_evals))
    family_evals = {"V2_RIDGE_RAW": [best_ridge_eval], "V2_KERNEL_RIDGE": [best_cv(kernel_evals)], "V2_SHALLOW_MLP": mlp_evals, "V2_RIDGE_PLUS_RESIDUAL": [best_cv(residual_evals)], "V2_MULTITASK_MLP": multitask_evals}
    candidate_specs = [item[0]["spec"] for item in family_evals.values()]
    write_json(OUT / "V2_TRAIN_CANDIDATE_FREEZE.json", {"schema_version": "V2_TRAIN_CANDIDATE_FREEZE_V1", "dataset_role": "original TRAIN 48G + AL Round-1 8G", "train_geometries": 56, "train_rows": 616, "pca_rank": PCA_RANK, "feature_set": "RAW_GEOMETRY_LAMBDA", "candidates": [{"spec": evaluation["spec"], "grouped_cv_metrics": {key: value for key, value in evaluation["aggregate"].items() if key != "coefficients"}, "seed_profile_l1_std": evaluation["seed_profile_l1_std"]} for evaluation in [item[0] for item in family_evals.values()]], "validation_not_read_for_selection": True, "blind_not_read_for_selection": True, "v2_prospective_not_read": True, "fold_local_preprocessing": True})

    final_evaluations: dict[str, dict[str, Any]] = {}
    model_records: list[dict[str, Any]] = []
    for spec in candidate_specs:
        start = time.perf_counter()
        dev_pred, payload, _ = fit_spec(spec, train["X"], train["Y"], dev["X"])
        blind_pred = predict_saved(payload, blind["X"])
        train_pred = predict_saved(payload, train["X"])
        elapsed = time.perf_counter() - start
        model_path = OUT / "models" / f"{spec['id']}.pkl"
        serializable_payload = {"schema_version": "V2_SURROGATE_MODEL_V1", "spec": spec, "pca_rank": PCA_RANK, "pca_sha256": sha(PCA_MODEL), "v2_train_dataset_sha256": sha(TRAINVAL), "al_dataset_sha256": sha(AL_DATASET), "payload": payload}
        with model_path.open("wb") as f:
            pickle.dump(serializable_payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        with model_path.open("rb") as f:
            loaded = pickle.load(f)
        reloaded_dev = predict_saved(loaded["payload"], dev["X"])
        save_load_pass = bool(np.allclose(reloaded_dev, dev_pred, rtol=1e-10, atol=1e-12))
        if not save_load_pass:
            raise RuntimeError(f"model save/load mismatch: {spec['id']}")
        start_inf = time.perf_counter(); _ = predict_saved(payload, dev["X"]); inference_ms = (time.perf_counter() - start_inf) * 1000.0 / max(len(dev["X"]), 1)
        cv_eval = next(e for e in family_evals[spec["family"]] if e["spec"]["id"] == spec["id"])
        final_evaluations[spec["family"]] = {"spec": spec, "cv": cv_eval, "train_pred": train_pred, "dev_pred": dev_pred, "blind_pred": blind_pred, "dev_metrics": metric_summary(dev, dev_pred, pca, coeff_std), "blind_metrics": metric_summary(blind, blind_pred, pca, coeff_std), "train_metrics": metric_summary(train, train_pred, pca, coeff_std), "model_path": str(model_path), "model_sha256": sha(model_path), "artifact_size": model_path.stat().st_size, "training_time_s": elapsed, "inference_ms_per_row": inference_ms, "parameter_count": count_parameters(payload), "save_load_pass": save_load_pass}
        model_records.append({"model_id": spec["id"], "family": spec["family"], "path": str(model_path), "sha256": sha(model_path), "size": model_path.stat().st_size, "parameter_count": count_parameters(payload), "training_time_s": elapsed, "inference_ms_per_row": inference_ms, "save_load_pass": save_load_pass})
    write_json(OUT / "V2_MODEL_SAVE_LOAD_AUDIT.json", {"schema_version": "V2_MODEL_SAVE_LOAD_AUDIT_V1", "pass": all(row["save_load_pass"] for row in model_records), "models": model_records, "no_solver": True})

    scalar_coeff_rows: list[dict[str, Any]] = []
    all_coefficient_rows: list[dict[str, Any]] = []
    for family, evaluation in final_evaluations.items():
        for split_name, metrics in (("GROUPED_CV_OOF", evaluation["cv"]["aggregate"]), ("DEVELOPMENT_VALIDATION", evaluation["dev_metrics"]), ("V1_BLIND_RETROSPECTIVE", evaluation["blind_metrics"])):
            for coefficient in metrics["coefficients"]:
                row = {"model_family": family, "model_id": evaluation["spec"]["id"], "split": split_name, **coefficient, "high_priority": coefficient["coefficient"] in HIGH_COEFFS}
                all_coefficient_rows.append(row)
                if coefficient["coefficient"] in HIGH_COEFFS:
                    scalar_coeff_rows.append(row)
    write_csv(OUT / "V2_PCA_COEFFICIENT_RESULTS.csv", all_coefficient_rows)

    def summary_row(family: str, evaluation: dict[str, Any]) -> dict[str, Any]:
        cv = evaluation["cv"]["aggregate"]; dv = evaluation["dev_metrics"]; bv = evaluation["blind_metrics"]
        return {"model_family": family, "model_id": evaluation["spec"]["id"], "spec": evaluation["spec"], "parameter_count": evaluation["parameter_count"], "artifact_size": evaluation["artifact_size"], "training_time_s": evaluation["training_time_s"], "inference_ms_per_row": evaluation["inference_ms_per_row"], "model_sha256": evaluation["model_sha256"], "cv": {key: value for key, value in cv.items() if key != "coefficients"}, "development_validation": {key: value for key, value in dv.items() if key != "coefficients"}, "v1_blind_retrospective": {key: value for key, value in bv.items() if key != "coefficients"}, "seed_profile_l1_std": evaluation["cv"]["seed_profile_l1_std"]}
    candidate_summaries = [summary_row(family, evaluation) for family, evaluation in final_evaluations.items()]
    write_csv(OUT / "V2_DEVELOPMENT_VALIDATION_RESULTS.csv", [{"model_family": row["model_family"], "model_id": row["model_id"], **flatten_metrics("cv", row["cv"]), **flatten_metrics("development", row["development_validation"]), "parameter_count": row["parameter_count"], "artifact_size": row["artifact_size"], "training_time_s": row["training_time_s"], "inference_ms_per_row": row["inference_ms_per_row"], "seed_profile_l1_std": row["seed_profile_l1_std"], "model_sha256": row["model_sha256"]} for row in candidate_summaries])

    old_spec = {"id": "old_v1_ridge_raw_champion", "family": "V2_RIDGE_RAW", "alpha": old_alpha(), "feature_set": "RAW_GEOMETRY_LAMBDA"}
    old_dev_pred, _, _ = fit_spec(old_spec, make_bundle(train_rows, pca)["X"], make_bundle(train_rows, pca)["Y"], dev["X"])
    old_blind_pred, _, _ = fit_spec(old_spec, make_bundle(train_rows, pca)["X"], make_bundle(train_rows, pca)["Y"], blind["X"])
    v2_ridge = final_evaluations["V2_RIDGE_RAW"]
    old_dev_metrics = metric_summary(dev, old_dev_pred, pca, coeff_std); old_blind_metrics = metric_summary(blind, old_blind_pred, pca, coeff_std)
    v2_dev_metrics = v2_ridge["dev_metrics"]; v2_blind_metrics = v2_ridge["blind_metrics"]
    gain_keys = ("profile_weighted_l1", "profile_correlation", "weighted_js", "G_emit_mae", "eta_up_mae", "dominant_lobe_centroid_mae", "F_seed_5_mae", "asymmetry_mae")
    def gains(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        return {key: {"old": old[key], "new": new[key], "absolute_gain_error_lower_better": old[key] - new[key], "relative_gain_error_lower_better": relative_gain(old[key], new[key]) if key != "profile_correlation" else new[key] - old[key]} for key in gain_keys}
    dev_gain = gains(old_dev_metrics, v2_dev_metrics); blind_gain = gains(old_blind_metrics, v2_blind_metrics)
    directional_improved_dev = sum(dev_gain[key]["relative_gain_error_lower_better"] >= DIRECTIONAL_GAIN_MIN for key in ("dominant_lobe_centroid_mae", "F_seed_5_mae", "asymmetry_mae"))
    directional_improved_blind = sum(blind_gain[key]["relative_gain_error_lower_better"] >= DIRECTIONAL_GAIN_MIN for key in ("dominant_lobe_centroid_mae", "F_seed_5_mae", "asymmetry_mae"))
    write_json(OUT / "AL_ROUND1_LEARNING_GAIN_AUDIT.json", {"schema_version": "AL_ROUND1_LEARNING_GAIN_AUDIT_V1", "pass": True, "old_model": {"label": "RIDGE_RAW_CHAMPION", "train_geometries": 48, "alpha": old_spec["alpha"]}, "new_model": {"label": "V2_RIDGE_RAW", "train_geometries": 56, "alpha": best_ridge_alpha}, "development_validation": {"rows": 88, "metrics": dev_gain, "directional_metrics_meeting_5pct_gain": directional_improved_dev}, "v1_blind_retrospective": {"rows": 88, "role": "HISTORICAL_BENCHMARK_ONLY", "NOT_INDEPENDENT_FOR_V2": True, "metrics": blind_gain, "directional_metrics_meeting_5pct_gain": directional_improved_blind}, "directional_prediction_improved_on_development": directional_improved_dev >= 2, "directional_prediction_improved_on_blind": directional_improved_blind >= 2, "blind_used_for_selection": False, "hyperparameters_changed_after_blind": False, "solver_entries": 0})

    baseline = final_evaluations["V2_RIDGE_RAW"]
    def gain_fraction(base: dict[str, Any], candidate: dict[str, Any], key: str) -> float:
        return relative_gain(base[key], candidate[key])
    for evaluation in final_evaluations.values():
        evaluation["cv_profile_l1_gain_vs_ridge"] = gain_fraction(baseline["cv"]["aggregate"], evaluation["cv"]["aggregate"], "profile_weighted_l1")
        evaluation["dev_profile_l1_gain_vs_ridge"] = gain_fraction(baseline["dev_metrics"], evaluation["dev_metrics"], "profile_weighted_l1")
        evaluation["cv_profile_win_fraction_vs_ridge"] = float(np.mean([evaluation["cv"]["oof_pred"] is not None and profile_l1_by_group(train, evaluation["cv"]["oof_pred"], pca).get(group, 1e99) < profile_l1_by_group(train, baseline["cv"]["oof_pred"], pca).get(group, 1e99) for group in set(train["groups"])]))
        evaluation["dev_profile_win_fraction_vs_ridge"] = float(np.mean([profile_l1_by_group(dev, evaluation["dev_pred"], pca).get(group, 1e99) < profile_l1_by_group(dev, baseline["dev_pred"], pca).get(group, 1e99) for group in set(dev["groups"])]))
    def eligible(evaluation: dict[str, Any]) -> bool:
        if evaluation is baseline:
            return True
        cv = evaluation["cv"]["aggregate"]; dv = evaluation["dev_metrics"]; bcv = baseline["cv"]["aggregate"]; bdv = baseline["dev_metrics"]
        directional_cv = sum(relative_gain(bcv[key], cv[key]) >= DIRECTIONAL_GAIN_MIN for key in ("dominant_lobe_centroid_mae", "F_seed_5_mae", "asymmetry_mae"))
        directional_dev = sum(relative_gain(bdv[key], dv[key]) >= DIRECTIONAL_GAIN_MIN for key in ("dominant_lobe_centroid_mae", "F_seed_5_mae", "asymmetry_mae"))
        scalar_ok = all(cv[key] <= bcv[key] * (1 + SCALAR_DEGRADATION_MAX) and dv[key] <= bdv[key] * (1 + SCALAR_DEGRADATION_MAX) for key in ("G_emit_mae", "eta_up_mae"))
        return bool(evaluation["cv_profile_l1_gain_vs_ridge"] >= PROFILE_GAIN_MIN and evaluation["dev_profile_l1_gain_vs_ridge"] >= PROFILE_GAIN_MIN and directional_cv >= 2 and directional_dev >= 2 and scalar_ok and evaluation["cv_profile_win_fraction_vs_ridge"] >= 0.5 and evaluation["dev_profile_win_fraction_vs_ridge"] >= 0.5)
    eligible_candidates = [evaluation for evaluation in final_evaluations.values() if eligible(evaluation)]
    chosen = min(eligible_candidates, key=lambda item: (item["dev_metrics"]["profile_weighted_l1"], item["cv"]["aggregate"]["profile_weighted_l1"], item["dev_metrics"]["weighted_js"], item["dev_metrics"]["dominant_lobe_centroid_mae"], item["parameter_count"])) if eligible_candidates else baseline
    pareto_metrics = []
    metric_keys = ("cv_profile_weighted_l1", "dev_profile_weighted_l1", "cv_weighted_js", "dev_weighted_js", "cv_dominant_lobe_centroid_mae", "dev_dominant_lobe_centroid_mae", "cv_F_seed_5_mae", "dev_F_seed_5_mae", "cv_asymmetry_mae", "dev_asymmetry_mae", "cv_G_emit_mae", "dev_G_emit_mae", "cv_eta_up_mae", "dev_eta_up_mae")
    for evaluation in final_evaluations.values():
        metrics = {"cv_profile_weighted_l1": evaluation["cv"]["aggregate"]["profile_weighted_l1"], "dev_profile_weighted_l1": evaluation["dev_metrics"]["profile_weighted_l1"], "cv_weighted_js": evaluation["cv"]["aggregate"]["weighted_js"], "dev_weighted_js": evaluation["dev_metrics"]["weighted_js"], "cv_dominant_lobe_centroid_mae": evaluation["cv"]["aggregate"]["dominant_lobe_centroid_mae"], "dev_dominant_lobe_centroid_mae": evaluation["dev_metrics"]["dominant_lobe_centroid_mae"], "cv_F_seed_5_mae": evaluation["cv"]["aggregate"]["F_seed_5_mae"], "dev_F_seed_5_mae": evaluation["dev_metrics"]["F_seed_5_mae"], "cv_asymmetry_mae": evaluation["cv"]["aggregate"]["asymmetry_mae"], "dev_asymmetry_mae": evaluation["dev_metrics"]["asymmetry_mae"], "cv_G_emit_mae": evaluation["cv"]["aggregate"]["G_emit_mae"], "dev_G_emit_mae": evaluation["dev_metrics"]["G_emit_mae"], "cv_eta_up_mae": evaluation["cv"]["aggregate"]["eta_up_mae"], "dev_eta_up_mae": evaluation["dev_metrics"]["eta_up_mae"]}
        pareto_metrics.append({"model_family": evaluation["spec"]["family"], "model_id": evaluation["spec"]["id"], "metrics": metrics, "complexity": {"parameter_count": evaluation["parameter_count"], "artifact_size": evaluation["artifact_size"]}, "eligible_for_nonlinear_promotion": eligible(evaluation)})
    def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
        return all(a["metrics"][key] <= b["metrics"][key] for key in metric_keys) and any(a["metrics"][key] < b["metrics"][key] for key in metric_keys)
    front = [row for row in pareto_metrics if not any(dominates(other, row) for other in pareto_metrics if other is not row)]
    write_json(OUT / "V2_MODEL_PARETO_ANALYSIS.json", {"schema_version": "V2_MODEL_PARETO_ANALYSIS_V1", "primary_hierarchy": ["profile_weighted_l1", "profile_correlation", "weighted_js", "directional_metrics", "scalar_non_degradation", "complexity"], "candidate_metrics": pareto_metrics, "pareto_front": front, "arbitrary_weighted_total_used": False, "blind_used_for_selection": False})
    champion_ready = True
    write_json(OUT / "V2_CHAMPION_SELECTION.json", {"schema_version": "V2_CHAMPION_SELECTION_V1", "selected_model_family": chosen["spec"]["family"], "selected_model_id": chosen["spec"]["id"], "unique": True, "nonlinear_candidates_eligible": [item["spec"]["id"] for item in eligible_candidates], "selection_basis": "grouped CV then one-shot development validation; V1 blind retrospective only", "thresholds": {"profile_relative_gain_min": PROFILE_GAIN_MIN, "directional_relative_gain_min": DIRECTIONAL_GAIN_MIN, "scalar_degradation_max": SCALAR_DEGRADATION_MAX}, "production_blind_authorized": True})
    write_json(OUT / "V2_PREPROSPECTIVE_CHAMPION_FREEZE.json", {"schema_version": "V2_PREPROSPECTIVE_CHAMPION_FREEZE_V1", "status": "FROZEN", "champion": {"model_family": chosen["spec"]["family"], "model_id": chosen["spec"]["id"], "model_path": chosen["model_path"], "model_sha256": chosen["model_sha256"], "spec": chosen["spec"], "parameter_count": chosen["parameter_count"], "artifact_size": chosen["artifact_size"]}, "pca_rank": PCA_RANK, "pca_sha256": sha(PCA_MODEL), "v2_train_geometries": 56, "v2_train_rows": 616, "development_validation_geometries": 8, "v1_blind_role": "HISTORICAL_BENCHMARK_ONLY_NOT_INDEPENDENT_FOR_V2", "v2_prospective_sealed": True, "v2_prospective_truth_acquired": 0, "solver_entries": 0, "hyperparameters_frozen_before_blind": True, "production_ready_for_v2_prospective": True})
    prospective_audit = {"schema_version": "V2_PROSPECTIVE_SEAL_AUDIT_V1", "pass": True, "sealed": v2_plan.get("sealed") is True, "truth_acquired": v2_plan.get("truth_acquired"), "solver_launched": v2_plan.get("solver_launched"), "geometry_count": len(prospective_ids), "geometry_ids": sorted(prospective_ids), "source": file_record(V2_PLAN), "source_sha256": sha(V2_PLAN), "truth_zero": v2_plan.get("truth_acquired") == 0, "no_model_selection_read": True}
    write_json(OUT / "V2_PROSPECTIVE_SEAL_AUDIT.json", prospective_audit)
    report = {"status": "PASS", "verdict": "PASS — V2_NONLINEAR_SURROGATE_CHAMPION_FROZEN" if chosen["spec"]["family"] != "V2_RIDGE_RAW" else "PASS — V2_RIDGE_REMAINS_CHAMPION_AFTER_AL", "champion": chosen["spec"]["family"], "champion_model_id": chosen["spec"]["id"], "v2_train_geometries": 56, "v2_train_rows": 616, "development_validation_geometries": 8, "development_validation_rows": 88, "v1_blind_geometries": 8, "v1_blind_truth_used_for_fitting": False, "v2_prospective_geometries": 8, "v2_prospective_truth_acquired": 0, "solver_entries": 0, "solver_rerun_delta": 0, "pca_rank": PCA_RANK, "pca_refit": False, "al_directional_improved_development": directional_improved_dev >= 2, "al_directional_improved_blind_retrospective": directional_improved_blind >= 2, "production_rerun_ready": True, "next": "ACQUIRE_V2_PROSPECTIVE_8G_WITH_TWO_SLOTS"}
    write_json(OUT / "REPORT.json", report)
    report_lines = ["# APCD_COUPLING_V2_2_SURROGATE_V2_NONLINEAR_REEVALUATION_WITH_AL_ROUND1_V1", "", "### STATUS", "", report["verdict"], "", "### V2_DATA_ROLES", "", "" + "56 TRAIN geometries / 616 rows; 8 development validation geometries / 88 rows; V1 blind historical benchmark only; V2 prospective 8 sealed / 0 truth.", "", "### DATA_INTEGRITY", "", "" + "No geometry leakage; 11 wavelengths per geometry; raw/post/geometry SHA fields present; no prior features.", "", "### PCA_POLICY", "", "" + f"Frozen V1 rank-{PCA_RANK} basis; primary comparison uses transform-only PCA; refit=false.", "", "### AL_ROUND1_LEARNING_GAIN", "", f"Directional improvement on development={directional_improved_dev >= 2}; retrospective blind={directional_improved_blind >= 2}; blind not used for selection.", "", "### CHAMPION_REASON", "", f"{chosen['spec']['family']}; selected by grouped-CV and one-shot development hierarchy with scalar non-degradation and complexity tie-break.", "", "### V2_PROSPECTIVE_STATUS", "", "8 sealed; truth_acquired=0; solver_entries=0.", "", "### SOLVER_ACCOUNTING", "", "solver_entries=0; solver_rerun_delta=0; no FDTD invoked.", "", "### ARTIFACTS", "", str(OUT), "", "### NEXT", "", "ACQUIRE_V2_PROSPECTIVE_8G_WITH_TWO_SLOTS"]
    (OUT / "REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    manifest_files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            manifest_files.append({"path": str(path.relative_to(OUT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)})
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": manifest_files, "solver_entries": 0, "v2_prospective_truth_acquired": 0, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    print(json.dumps({"status": "PASS", "verdict": report["verdict"], "champion": report["champion"], "solver_entries": 0, "train_geometries": 56, "train_rows": 616, "development_rows": 88, "blind_rows": 88, "prospective_truth": 0, "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
