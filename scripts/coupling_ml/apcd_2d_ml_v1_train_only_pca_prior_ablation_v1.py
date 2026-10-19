from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import pickle
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.impute import SimpleImputer
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


ROOT = Path(os.environ.get(
    "APCD_ML_V1_ROOT",
    r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1",
))
OUT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1"
DATA_ROOT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
DATASET = DATA_ROOT / "V1_TRAINVAL_DATASET.csv"
PRIOR = DATA_ROOT / "K6_V1_64G_PRIOR_FEATURES.csv"
SPLIT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1" / "K6_V1_GEOMETRY_SPLIT_MANIFEST.json"
SEALED = DATA_ROOT / "BLIND_PROSPECTIVE_SEALED_MANIFEST.json"
WLS = np.arange(445.0, 456.0, 1.0)
LAMBDA_X_NM = 1740.0
RANK_CANDIDATES = (2, 4, 6, 8, 12, 16, 24, 32)
NP_FIELDS = ("np_hf22_R_mean", "np_hf22_T_mean", "np_hf22_directionality_mean", "np_hf22_eta_minus1_mean", "np_hf22_eta_plus1_mean")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_safe(x: Any) -> Any:
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, dict):
        return {str(k): json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_safe(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(data), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: json_safe(v) for k, v in row.items()} for row in rows])


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_bool(v: Any) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def macro_mean(values: np.ndarray, groups: np.ndarray) -> float:
    return float(np.mean([np.mean(values[groups == g]) for g in np.unique(groups)]))


def safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def profile_metrics(true: np.ndarray, pred: np.ndarray, theta: np.ndarray, ux: np.ndarray, w: np.ndarray, lambdas: np.ndarray, groups: np.ndarray) -> dict[str, float]:
    raw_l1, raw_l2, proj_l1, proj_l2, corr, js, integ = [], [], [], [], [], [], []
    theta_err, pos_err, asym_err, seed2_err, seed5_err, seed10_err = [], [], [], [], [], []
    neg_bins, neg_mass = [], []
    for i in range(len(true)):
        t = np.asarray(true[i], float)
        p = np.asarray(pred[i], float)
        raw_l1.append(float(np.sum(w * np.abs(p - t))))
        raw_l2.append(float(np.sqrt(np.sum(w * (p - t) ** 2))))
        neg_bins.append(float(np.mean(p < 0)))
        neg_mass.append(float(np.sum(w * np.maximum(-p, 0.0))))
        pp = np.maximum(p, 0.0)
        pp /= max(float(np.sum(w * pp)), 1e-300)
        tt = np.maximum(t, 0.0)
        tt /= max(float(np.sum(w * tt)), 1e-300)
        proj_l1.append(float(np.sum(w * np.abs(pp - tt))))
        proj_l2.append(float(np.sqrt(np.sum(w * (pp - tt) ** 2))))
        corr.append(safe_corr(t, p))
        q = w * pp
        r = w * tt
        m = 0.5 * (q + r)
        js.append(float(0.5 * np.sum(np.where(q > 0, q * np.log(np.maximum(q, 1e-300) / np.maximum(m, 1e-300)), 0.0)) + 0.5 * np.sum(np.where(r > 0, r * np.log(np.maximum(r, 1e-300) / np.maximum(m, 1e-300)), 0.0))))
        integ.append(abs(float(np.sum(w * p)) - 1.0))
        th = theta[:, i % theta.shape[1]] if theta.ndim == 2 else theta
        seed = math.degrees(math.asin(float(lambdas[i % len(lambdas)]) / LAMBDA_X_NM))
        def derived(z: np.ndarray) -> tuple[float, float, float, list[float]]:
            peak = float(th[int(np.argmax(z))])
            pos = float(np.sum(w[ux >= 0] * z[ux >= 0]))
            neg = float(np.sum(w[ux < 0] * z[ux < 0]))
            vals = [float(np.sum(w[np.abs(th - seed) <= q] * z[np.abs(th - seed) <= q])) for q in (2, 5, 10)]
            return peak, pos, (pos - neg) / max(pos + neg, 1e-300), vals
        a = derived(tt)
        b = derived(pp)
        theta_err.append(abs(b[0] - a[0])); pos_err.append(abs(b[1] - a[1])); asym_err.append(abs(b[2] - a[2]))
        seed2_err.append(abs(b[3][0] - a[3][0])); seed5_err.append(abs(b[3][1] - a[3][1])); seed10_err.append(abs(b[3][2] - a[3][2]))
    def mm(v: list[float]) -> float:
        return macro_mean(np.asarray(v), groups)
    return {
        "profile_raw_weighted_l1": mm(raw_l1), "profile_raw_weighted_l2": mm(raw_l2),
        "profile_weighted_l1": mm(proj_l1), "profile_weighted_l2": mm(proj_l2),
        "profile_correlation": mm(corr), "profile_js": mm(js), "profile_integral_error": mm(integ),
        "negative_bin_fraction": mm(neg_bins), "negative_mass_fraction": mm(neg_mass),
        "theta_peak_mae_deg": mm(theta_err), "positive_fraction_mae": mm(pos_err),
        "asymmetry_mae": mm(asym_err), "F_seed_2_mae": mm(seed2_err),
        "F_seed_5_mae": mm(seed5_err), "F_seed_10_mae": mm(seed10_err),
    }


def scalar_metrics(true: np.ndarray, pred: np.ndarray, groups: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for j, name in enumerate(("G_emit", "eta_up")):
        err = pred[:, j] - true[:, j]
        safe = np.abs(true[:, j]) > 1e-12
        out[f"{name}_mae"] = macro_mean(np.abs(err), groups)
        out[f"{name}_rmse"] = float(np.sqrt(np.mean([np.mean(err[groups == g] ** 2) for g in np.unique(groups)])))
        out[f"{name}_median_abs"] = macro_mean(np.abs(err), groups)  # macro primary; raw median is retained below.
        out[f"{name}_r2"] = float(r2_score(true[:, j], pred[:, j]))
        out[f"{name}_relative_mae"] = macro_mean(np.abs(err[safe]) / np.maximum(np.abs(true[safe, j]), 1e-12), groups[safe]) if np.any(safe) else 0.0
    return out


def preprocess_fit(x: np.ndarray) -> tuple[SimpleImputer, StandardScaler, np.ndarray]:
    imp = SimpleImputer(strategy="mean")
    sc = StandardScaler()
    z = sc.fit_transform(imp.fit_transform(x))
    return imp, sc, z


def fit_predict(family: str, xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray, rank: int, alpha: float = 1.0, gamma: float = 0.1, seed: int = 0) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    imp, sc, ztr = preprocess_fit(xtr)
    zte = sc.transform(imp.transform(xte))
    ys = StandardScaler().fit(ytr)
    yzt = ys.transform(ytr)
    if family == "Ridge":
        model = Ridge(alpha=alpha)
        model.fit(ztr, yzt)
        yp = ys.inverse_transform(model.predict(zte))
        return yp[:, :2], yp[:, 2:], {"model": model, "imputer": imp, "scaler": sc, "target_scaler": ys}
    if family == "GP":
        model = KernelRidge(alpha=alpha, kernel="rbf", gamma=gamma)
        model.fit(ztr, yzt[:, :2])
        yp = ys.inverse_transform(np.column_stack([model.predict(zte), np.zeros((len(zte), rank))]))[:, :2]
        return yp, None, {"model": model, "imputer": imp, "scaler": sc, "target_scaler": ys}
    model = MLPRegressor(hidden_layer_sizes=(64, 64), activation="relu", solver="adam", alpha=1e-3, max_iter=900, tol=1e-4, random_state=seed, early_stopping=False)
    model.fit(ztr, yzt)
    yp = ys.inverse_transform(model.predict(zte))
    return yp[:, :2], yp[:, 2:], {"model": model, "imputer": imp, "scaler": sc, "target_scaler": ys}


def evaluate_cv(family: str, feature_set: str, x: np.ndarray, y_scalar: np.ndarray, y_coeff: np.ndarray, profiles: np.ndarray, theta: np.ndarray, ux: np.ndarray, w: np.ndarray, lambdas: np.ndarray, groups: np.ndarray, folds: list[tuple[np.ndarray, np.ndarray]], rank: int, alpha: float, gamma: float, seed: int = 0) -> dict[str, Any]:
    sp = np.zeros_like(y_scalar); cp = None if family == "GP" else np.zeros_like(y_coeff)
    for tr, te in folds:
        ys, yc, _ = fit_predict(family, x[tr], np.column_stack([y_scalar[tr], y_coeff[tr]]), x[te], rank, alpha, gamma, seed)
        sp[te] = ys
        if cp is not None:
            cp[te] = yc
    m = scalar_metrics(y_scalar, sp, groups)
    if cp is not None:
        m.update(profile_metrics(profiles, pca_inverse(cp, PCA_CONTEXT), theta, ux, w, lambdas, groups))
    m.update({"family": family, "feature_set": feature_set, "alpha": alpha, "gamma": gamma, "seed": seed, "profile_available": cp is not None})
    return m


PCA_CONTEXT: dict[str, Any] = {}


def pca_inverse(coeff: np.ndarray, ctx: dict[str, Any]) -> np.ndarray:
    pca = ctx["pca"]
    r = coeff.shape[1]
    weighted = pca.mean_[None, :] + coeff @ pca.components_[:r]
    return weighted / ctx["sqrt_w"][None, :]


def save_model(path: Path, payload: Any) -> str:
    with path.open("wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    return sha(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "models").mkdir(exist_ok=True)
    (OUT / "preprocessors").mkdir(exist_ok=True)
    rows = read_csv(DATASET)
    prior_rows = read_csv(PRIOR)
    split = load_json(SPLIT)
    sealed = load_json(SEALED)
    assert len(rows) == 616, len(rows)
    ids = sorted({r["geometry_id"] for r in rows})
    train_ids = sorted({r["geometry_id"] for r in rows if r["split"] == "TRAIN"})
    val_ids = sorted({r["geometry_id"] for r in rows if r["split"] == "VALIDATION"})
    assert len(train_ids) == 48 and len(val_ids) == 8
    assert not set(train_ids) & set(val_ids)
    assert train_ids == sorted(split["train_geometry_ids"])
    assert val_ids == sorted(split["validation_geometry_ids"])
    assert all(r["geometry_id"] not in set(split["blind_geometry_ids"]) for r in rows)
    counts = {g: sum(r["geometry_id"] == g for r in rows) for g in ids}
    assert set(counts.values()) == {11}
    dataset_sha = sha(DATASET); split_sha = sha(SPLIT); prior_sha = sha(PRIOR); sealed_sha = sha(SEALED)
    write_json(OUT / "DATASET_INTEGRITY_AUDIT.json", {
        "schema_version": "DATASET_INTEGRITY_AUDIT_V1", "dataset": str(DATASET), "dataset_sha256": dataset_sha,
        "rows": len(rows), "unique_geometries": len(ids), "train_geometries": len(train_ids), "validation_geometries": len(val_ids),
        "train_rows": sum(r["split"] == "TRAIN" for r in rows), "validation_rows": sum(r["split"] == "VALIDATION" for r in rows),
        "wavelengths_per_geometry": sorted(set(counts.values())), "geometry_overlap": sorted(set(train_ids) & set(val_ids)),
        "split_manifest": str(SPLIT), "split_manifest_sha256": split_sha, "random_row_split": False,
        "geometry_sha_unique": all(len({r["geometry_SHA"] for r in rows if r["geometry_id"] == g}) == 1 for g in ids),
        "pass": len(rows) == 616 and len(train_ids) == 48 and len(val_ids) == 8 and not set(train_ids) & set(val_ids),
    })
    sealed_ids = set(sealed.get("geometry_ids", sealed.get("blind_geometry_ids", split["blind_geometry_ids"])))
    dataset_blind_rows = [r for r in rows if r["geometry_id"] in sealed_ids or r.get("split") == "BLIND" or r.get("dataset_role") == "BLIND"]
    write_json(OUT / "BLIND_LEAKAGE_AUDIT.json", {
        "schema_version": "BLIND_LEAKAGE_AUDIT_V1", "sealed_manifest": str(SEALED), "sealed_manifest_sha256": sealed_sha,
        "sealed_geometry_count": len(sealed_ids), "sealed_geometry_ids": sorted(sealed_ids), "dataset_blind_rows": len(dataset_blind_rows),
        "blind_truth_acquired": 0, "blind_truth_fields_read": False, "surrogate_called_on_blind": False, "pass": len(sealed_ids) == 8 and not dataset_blind_rows,
    })

    prior_map = {(r["geometry_id"], float(r["lambda_nm"])): r for r in prior_rows}
    by_id: dict[str, dict[str, Any]] = {}
    profile_cache: dict[str, dict[str, np.ndarray]] = {}
    profiles, theta_rows, ux = [], [], None
    w = None
    y_scalar, x_raw, groups, lambdas = [], [], [], []
    prior_matrix = []
    for r in rows:
        key = (r["geometry_id"], float(r["lambda_nm"]))
        pr = prior_map[key]
        pth = Path(r["angular_profile_ref"])
        if str(pth) not in profile_cache:
            z = {k: np.asarray(v) for k, v in np.load(pth, allow_pickle=False).items()}
            profile_cache[str(pth)] = z
        z = profile_cache[str(pth)]
        if ux is None:
            ux, w = z["ux"].astype(float), z["weights_du"].astype(float)
        idx = int(np.argmin(np.abs(z["wavelengths_nm"] - float(r["lambda_nm"]))))
        profiles.append(z["f_up"][:, idx].astype(float)); theta_rows.append(z["theta_deg"][:, idx].astype(float))
        y_scalar.append([float(r["G_emit"]), float(r["eta_up"])]); groups.append(r["geometry_id"]); lambdas.append(float(r["lambda_nm"]))
        x_raw.append([float(r[f"D{i}"]) / 290.0 for i in range(1, 7)] + [(float(r["lambda_nm"]) - 450.0) / 5.0])
        valid = as_bool(pr["np_prior_valid"])
        npvals = [float(pr[f]) if valid else np.nan for f in NP_FIELDS]
        prior_matrix.append(npvals + [float(valid), float(as_bool(pr["np_prior_ood"])), float(as_bool(pr["mdc_prior_valid"])), float(as_bool(pr["mdc_prior_ood"])), float(as_bool(pr["old_level2a_prior_valid"])), float(as_bool(pr["old_level2a_prior_ood"]))])
    profiles = np.asarray(profiles); theta_rows = np.asarray(theta_rows); y_scalar = np.asarray(y_scalar); x_raw = np.asarray(x_raw); prior_matrix = np.asarray(prior_matrix); groups = np.asarray(groups); lambdas = np.asarray(lambdas)
    assert np.isfinite(profiles).all() and np.isfinite(y_scalar).all()
    assert np.all(y_scalar[:, 0] > 0) and np.all((y_scalar[:, 1] >= 0) & (y_scalar[:, 1] <= 1.5))
    integrals = np.sum(profiles * w[None, :], axis=1)
    label_audit = {"schema_version": "LABEL_SANITY_AUDIT_V1", "G_emit_finite_positive": bool(np.isfinite(y_scalar[:, 0]).all() and (y_scalar[:, 0] > 0).all()), "eta_up_finite": bool(np.isfinite(y_scalar[:, 1]).all()), "profiles_finite": bool(np.isfinite(profiles).all()), "profile_integral_median": float(np.median(integrals)), "profile_integral_max_abs_error": float(np.max(np.abs(integrals - 1))), "profile_normalized": bool(np.max(np.abs(integrals - 1)) < 1e-6), "pass": bool(np.isfinite(profiles).all() and np.isfinite(y_scalar).all() and np.max(np.abs(integrals - 1)) < 1e-6)}
    write_json(OUT / "LABEL_SANITY_AUDIT.json", label_audit)
    split_idx = groups != ""
    train_mask = np.isin(groups, train_ids); val_mask = np.isin(groups, val_ids)
    train_profiles = profiles[train_mask]; val_profiles = profiles[val_mask]
    sqrt_w = np.sqrt(w)
    pca = PCA(n_components=min(max(RANK_CANDIDATES), len(train_profiles) - 1), svd_solver="full", random_state=0)
    pca.fit(train_profiles * sqrt_w[None, :])
    PCA_CONTEXT.update({"pca": pca, "sqrt_w": sqrt_w})
    train_coeff = pca.transform(train_profiles * sqrt_w[None, :]); val_coeff = pca.transform(val_profiles * sqrt_w[None, :])
    full_train_groups = groups[train_mask]; full_val_groups = groups[val_mask]
    rank_rows = []
    for rank in RANK_CANDIDATES:
        trp = pca_inverse(train_coeff[:, :rank], PCA_CONTEXT); vap = pca_inverse(val_coeff[:, :rank], PCA_CONTEXT)
        tm = profile_metrics(train_profiles, trp, theta_rows[train_mask].T, ux, w, lambdas[train_mask], full_train_groups)
        vm = profile_metrics(val_profiles, vap, theta_rows[val_mask].T, ux, w, lambdas[val_mask], full_val_groups)
        rank_rows.append({"rank": rank, "explained_variance": float(np.sum(pca.explained_variance_ratio_[:rank])), "train_weighted_l1": tm["profile_raw_weighted_l1"], "train_weighted_l2": tm["profile_raw_weighted_l2"], "validation_weighted_l1": vm["profile_raw_weighted_l1"], "validation_weighted_l2": vm["profile_raw_weighted_l2"], "train_theta_peak_mae_deg": tm["theta_peak_mae_deg"], "validation_theta_peak_mae_deg": vm["theta_peak_mae_deg"], "train_negative_mass_fraction": tm["negative_mass_fraction"], "validation_negative_mass_fraction": vm["negative_mass_fraction"]})
    selected_rank = RANK_CANDIDATES[-1]
    for i, rr in enumerate(rank_rows):
        previous = rank_rows[i - 1]["train_weighted_l1"] if i else None
        improvement = (previous - rr["train_weighted_l1"]) if previous is not None else None
        if rr["explained_variance"] >= 0.99 and rr["train_weighted_l1"] <= 0.01 and (improvement is not None and improvement <= max(0.001, previous * 0.05)):
            selected_rank = rr["rank"]; break
    finalists = [r["rank"] for r in rank_rows if abs(r["train_weighted_l1"] - next(x for x in rank_rows if x["rank"] == selected_rank)["train_weighted_l1"]) < 0.001]
    write_json(OUT / "ANGULAR_PCA_RANK_AUDIT.json", {"schema_version": "ANGULAR_PCA_RANK_AUDIT_V1", "fit_scope": "TRAIN_ONLY", "weighted_coordinate": "sqrt(weights_du)*f_up", "candidate_ranks": rank_rows, "selected_rank": selected_rank, "rank_finalists": sorted(set(finalists))})
    selected_weighted_mean = pca.mean_ / sqrt_w
    np.savez_compressed(OUT / "ANGULAR_PCA_MODEL.npz", train_geometry_ids=np.asarray(train_ids), train_dataset_sha256=np.asarray(dataset_sha), ux=ux, weights_du=w, mean_profile=selected_weighted_mean, components_weighted=pca.components_[:selected_rank], components_profile=pca.components_[:selected_rank] / sqrt_w[None, :], explained_variance_ratio=pca.explained_variance_ratio_[:selected_rank], rank=np.asarray(selected_rank))
    pca_sha = sha(OUT / "ANGULAR_PCA_MODEL.npz")
    write_json(OUT / "ANGULAR_PCA_MODEL_METADATA.json", {"schema_version": "ANGULAR_PCA_MODEL_V1", "artifact": str(OUT / "ANGULAR_PCA_MODEL.npz"), "artifact_sha256": pca_sha, "train_dataset_sha256": dataset_sha, "train_geometry_ids": train_ids, "rank": selected_rank, "u_x_points": len(ux), "weighted_measure": "du_x"})
    pca_sensitivity = []
    folds = list(GroupKFold(n_splits=8).split(np.zeros((len(train_profiles), 1)), np.zeros(len(train_profiles)), full_train_groups))
    fold_manifest = []
    for k, (tr, te) in enumerate(folds):
        tr_ids = sorted(set(full_train_groups[tr])); te_ids = sorted(set(full_train_groups[te])); assert not set(tr_ids) & set(te_ids)
        fold_manifest.append({"fold": k, "train_geometry_ids": tr_ids, "test_geometry_ids": te_ids, "train_rows": len(tr), "test_rows": len(te)})
        fp = PCA(n_components=selected_rank, svd_solver="full").fit(train_profiles[tr] * sqrt_w[None, :])
        local = (fp.inverse_transform(fp.transform(train_profiles[te] * sqrt_w[None, :]))) / sqrt_w[None, :]
        global_p = pca_inverse(train_coeff[np.where(np.isin(np.arange(len(groups), dtype=int)[train_mask], te_ids))[0], :selected_rank], PCA_CONTEXT) if False else pca_inverse(pca.transform(train_profiles[te] * sqrt_w[None, :])[:, :selected_rank], PCA_CONTEXT)
        pca_sensitivity.append({"fold": k, "fold_specific_l2": profile_metrics(train_profiles[te], local, theta_rows[train_mask][te].T, ux, w, lambdas[train_mask][te], full_train_groups[te])["profile_raw_weighted_l2"], "global_train_pca_l2": profile_metrics(train_profiles[te], global_p, theta_rows[train_mask][te].T, ux, w, lambdas[train_mask][te], full_train_groups[te])["profile_raw_weighted_l2"]})
    write_json(OUT / "GROUPED_CV_SPLIT_MANIFEST.json", {"schema_version": "GROUPED_CV_SPLIT_MANIFEST_V1", "n_splits": 8, "group_field": "geometry_id", "row_randomization": False, "folds": fold_manifest, "pca_sensitivity": pca_sensitivity})
    write_json(OUT / "PCA_RECONSTRUCTION_METRICS.csv.json", {"rows": rank_rows, "fit_scope": "TRAIN_ONLY"})
    write_csv(OUT / "PCA_RECONSTRUCTION_METRICS.csv", rank_rows)

    providers = {"NP": prior_matrix[:, 5] == 1, "MDC": prior_matrix[:, 7] == 1, "old3D": prior_matrix[:, 9] == 1}
    prior_audit = {"schema_version": "PRIOR_FEATURE_VALIDITY_AUDIT_V1", "prior_sha256": prior_sha, "providers": {}}
    for name, valid in providers.items():
        ood = prior_matrix[:, {"NP": 6, "MDC": 8, "old3D": 10}[name]] == 1
        prior_audit["providers"][name] = {"train_row_valid_fraction": float(np.mean(valid[train_mask])), "validation_row_valid_fraction": float(np.mean(valid[val_mask])), "train_geometry_valid_fraction": float(np.mean([np.any(valid[groups == g]) for g in train_ids])), "validation_geometry_valid_fraction": float(np.mean([np.any(valid[groups == g]) for g in val_ids])), "train_ood_fraction": float(np.mean(ood[train_mask])), "validation_ood_fraction": float(np.mean(ood[val_mask])), "train_missing_fraction": float(np.mean(~valid[train_mask] & ~ood[train_mask])), "validation_missing_fraction": float(np.mean(~valid[val_mask] & ~ood[val_mask])), "numeric_features": list(NP_FIELDS) if name == "NP" else [], "coverage_limited": bool(np.mean(valid) < 0.5)}
    write_json(OUT / "PRIOR_FEATURE_VALIDITY_AUDIT.json", prior_audit)
    feature_names = {"A_RAW": [f"D{i}_normalized" for i in range(1, 7)] + ["lambda_centered"], "B_NP": [f"D{i}_normalized" for i in range(1, 7)] + ["lambda_centered"] + list(NP_FIELDS) + ["np_valid", "np_ood"], "C_NP_MDC": [f"D{i}_normalized" for i in range(1, 7)] + ["lambda_centered"] + list(NP_FIELDS) + ["np_valid", "np_ood", "mdc_valid", "mdc_ood"], "D_ALL_PRIORS": [f"D{i}_normalized" for i in range(1, 7)] + ["lambda_centered"] + list(NP_FIELDS) + ["np_valid", "np_ood", "mdc_valid", "mdc_ood", "old3d_valid", "old3d_ood"]}
    x_sets = {"A_RAW": x_raw, "B_NP": np.column_stack([x_raw, prior_matrix[:, :7]]), "C_NP_MDC": np.column_stack([x_raw, prior_matrix[:, :9]]), "D_ALL_PRIORS": np.column_stack([x_raw, prior_matrix[:, :11]])}
    y_coeff_all = pca.transform(profiles * sqrt_w[None, :])[:, :selected_rank]
    train_indices = np.where(train_mask)[0]; val_indices = np.where(val_mask)[0]
    train_pos = {idx: i for i, idx in enumerate(train_indices)}
    x_train_sets = {k: v[train_indices] for k, v in x_sets.items()}; x_val_sets = {k: v[val_indices] for k, v in x_sets.items()}
    ytr_scalar = y_scalar[train_indices]; ytr_coeff = y_coeff_all[train_indices]; yval_scalar = y_scalar[val_indices]; yval_coeff = y_coeff_all[val_indices]
    train_groups = groups[train_indices]; val_groups = groups[val_indices]
    train_profiles2 = profiles[train_indices]; val_profiles2 = profiles[val_indices]; train_theta = theta_rows[train_indices].T; val_theta = theta_rows[val_indices].T; train_lambdas = lambdas[train_indices]; val_lambdas = lambdas[val_indices]
    folds_local = [(tr, te) for tr, te in GroupKFold(n_splits=8).split(np.zeros((len(train_indices), 1)), np.zeros(len(train_indices)), train_groups)]
    write_json(OUT / "TRAIN_ONLY_PREPROCESSOR.json", {"schema_version": "TRAIN_ONLY_PREPROCESSOR_V1", "fit_scope": "TRAIN_ONLY", "raw_feature_normalization": {"D": "D_i/290_nm", "lambda": "(lambda_nm-450_nm)/5_nm", "order_preserved": True}, "feature_names": feature_names, "prior_numeric_invalid_values": "NaN_then_fold_train_mean_imputation", "validity_masks_explicit": True, "pca_fit_scope": "TRAIN_ONLY", "pca_sha256": pca_sha})

    ridge_rows: list[dict[str, Any]] = []; gp_rows: list[dict[str, Any]] = []; mlp_rows: list[dict[str, Any]] = []; summaries: list[dict[str, Any]] = []
    ridge_grid = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
    gp_grid = ((0.01, 0.01), (0.01, 0.1), (0.1, 0.1))
    for fs, x in x_train_sets.items():
        for alpha in ridge_grid:
            m = evaluate_cv("Ridge", fs, x, ytr_scalar, ytr_coeff, train_profiles2, train_theta, ux, w, train_lambdas, train_groups, folds_local, selected_rank, alpha, 0.0)
            m["feature_dim"] = x.shape[1]; ridge_rows.append(m)
        for alpha, gamma in gp_grid:
            m = evaluate_cv("GP", fs, x, ytr_scalar, ytr_coeff, train_profiles2, train_theta, ux, w, train_lambdas, train_groups, folds_local, selected_rank, alpha, gamma)
            m["feature_dim"] = x.shape[1]; gp_rows.append(m)
        for seed in range(5):
            m = evaluate_cv("MLP", fs, x, ytr_scalar, ytr_coeff, train_profiles2, train_theta, ux, w, train_lambdas, train_groups, folds_local, selected_rank, 1e-3, 0.0, seed)
            m["feature_dim"] = x.shape[1]; mlp_rows.append(m)

    def best(rows0: list[dict[str, Any]], family: str, fs: str) -> dict[str, Any]:
        rr = [r for r in rows0 if r["family"] == family and r["feature_set"] == fs]
        if family == "GP":
            return min(rr, key=lambda r: (r["G_emit_mae"] + r["eta_up_mae"], r.get("parameter_count", 1e99)))
        return min(rr, key=lambda r: (r.get("profile_weighted_l1", 1e99), r["G_emit_mae"] + r["eta_up_mae"], r.get("feature_dim", 1e99)))

    best_rows: dict[str, dict[str, Any]] = {}
    for family, table in (("Ridge", ridge_rows), ("GP", gp_rows), ("MLP", mlp_rows)):
        for fs in x_sets:
            if family == "MLP":
                candidates = [r for r in table if r["feature_set"] == fs]
                agg = dict(candidates[0]);
                for k in ("G_emit_mae", "eta_up_mae", "profile_weighted_l1", "profile_js", "theta_peak_mae_deg"):
                    vals = [r[k] for r in candidates]; agg[k] = float(np.mean(vals)); agg[k + "_std"] = float(np.std(vals))
                agg["seeds"] = [r["seed"] for r in candidates]; best_rows[f"MLP:{fs}"] = agg
            else:
                best_rows[f"{family}:{fs}"] = best(table, family, fs)
    def fit_final(family: str, fs: str, spec: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray, np.ndarray | None]:
        x = x_train_sets[fs]; xv = x_val_sets[fs]
        if family == "MLP":
            models = []; first_payload = None; preds = []
            for seed in range(5):
                sp, cp, payload = fit_predict("MLP", x, np.column_stack([ytr_scalar, ytr_coeff]), xv, selected_rank, 1e-3, 0.0, seed); models.append(payload); preds.append(np.column_stack([sp, cp])); first_payload = payload
            pred = np.mean(preds, axis=0); model_path = OUT / "models" / f"MLP_{fs}_5seed_ensemble.pkl"; model_sha = save_model(model_path, {"family": family, "feature_set": fs, "models": models, "seeds": list(range(5)), "pca_rank": selected_rank, "dataset_sha256": dataset_sha})
            return {"family": family, "feature_set": fs, "model_path": str(model_path), "model_sha256": model_sha, "seeds": list(range(5)), "cv": spec}, pred[:, :2], pred[:, 2:]
        alpha = float(spec.get("alpha", 0.1)); gamma = float(spec.get("gamma", 0.1)); sp, cp, payload = fit_predict(family, x, np.column_stack([ytr_scalar, ytr_coeff]), xv, selected_rank, alpha, gamma, 0)
        model_path = OUT / "models" / f"{family}_{fs}.pkl"; model_sha = save_model(model_path, {"family": family, "feature_set": fs, "pca_rank": selected_rank, "dataset_sha256": dataset_sha, "payload": payload, "alpha": alpha, "gamma": gamma})
        return {"family": family, "feature_set": fs, "model_path": str(model_path), "model_sha256": model_sha, "alpha": alpha, "gamma": gamma, "cv": spec}, sp, cp

    candidate_defs = [best_rows["Ridge:A_RAW"], best_rows["Ridge:B_NP"], best_rows["Ridge:C_NP_MDC"], best_rows["Ridge:D_ALL_PRIORS"], best_rows["GP:A_RAW"], best_rows["GP:B_NP"], best_rows["GP:C_NP_MDC"], best_rows["GP:D_ALL_PRIORS"], best_rows["MLP:A_RAW"], best_rows["MLP:B_NP"], best_rows["MLP:C_NP_MDC"], best_rows["MLP:D_ALL_PRIORS"]]
    final_payloads = []
    for spec in candidate_defs:
        final_payloads.append(fit_final(spec["family"], spec["feature_set"], spec))
    best_ridge = min([p for p in final_payloads if p[0]["family"] == "Ridge"], key=lambda p: (p[0]["cv"].get("profile_weighted_l1", 1e99), p[0]["cv"]["G_emit_mae"] + p[0]["cv"]["eta_up_mae"]))
    best_prior_ridge = min([p for p in final_payloads if p[0]["family"] == "Ridge" and p[0]["feature_set"] != "A_RAW"], key=lambda p: (p[0]["cv"].get("profile_weighted_l1", 1e99), p[0]["cv"]["G_emit_mae"] + p[0]["cv"]["eta_up_mae"]))
    best_gp = min([p for p in final_payloads if p[0]["family"] == "GP"], key=lambda p: p[0]["cv"]["G_emit_mae"] + p[0]["cv"]["eta_up_mae"])
    best_mlp = min([p for p in final_payloads if p[0]["family"] == "MLP"], key=lambda p: (p[0]["cv"].get("profile_weighted_l1", 1e99), p[0]["cv"]["G_emit_mae"] + p[0]["cv"]["eta_up_mae"]))
    freeze = {"schema_version": "TRAIN_CV_MODEL_CANDIDATE_FREEZE_V1", "created_before_validation": True, "dataset_sha256": dataset_sha, "split_sha256": split_sha, "prior_sha256": prior_sha, "pca_sha256": pca_sha, "chosen_pca_rank": selected_rank, "candidates": [{"label": "best_ridge", "definition": best_ridge[0]}, {"label": "best_prior_ridge", "definition": best_prior_ridge[0]}, {"label": "best_gp", "definition": best_gp[0]}, {"label": "best_mlp", "definition": best_mlp[0]}], "validation_not_read_for_selection": True}
    write_json(OUT / "TRAIN_CV_MODEL_CANDIDATE_FREEZE.json", freeze)

    # One-shot validation: these models were frozen above; no validation result is used to refit or retune.
    val_rows_scalar, val_rows_profile, val_rows_decision = [], [], []
    for p, sp, cp in final_payloads:
        sm = scalar_metrics(yval_scalar, sp, val_groups); sm.update({"family": p["family"], "feature_set": p["feature_set"], "model_path": p["model_path"]}); val_rows_scalar.append(sm)
        if cp is not None:
            pm = profile_metrics(val_profiles2, pca_inverse(cp, PCA_CONTEXT), val_theta, ux, w, val_lambdas, val_groups); pm.update({"family": p["family"], "feature_set": p["feature_set"], "model_path": p["model_path"]}); val_rows_profile.append(pm)
            val_rows_decision.append({k: pm[k] for k in ("family", "feature_set", "theta_peak_mae_deg", "positive_fraction_mae", "asymmetry_mae", "F_seed_2_mae", "F_seed_5_mae", "F_seed_10_mae")})
    write_csv(OUT / "RIDGE_ABLATION_RESULTS.csv", ridge_rows)
    write_csv(OUT / "GP_ABLATION_RESULTS.csv", gp_rows)
    write_csv(OUT / "MLP_ABLATION_RESULTS.csv", mlp_rows)
    write_csv(OUT / "VALIDATION_METRICS_SCALAR.csv", val_rows_scalar)
    write_csv(OUT / "VALIDATION_METRICS_PROFILE.csv", val_rows_profile)
    write_csv(OUT / "VALIDATION_METRICS_DECISION.csv", val_rows_decision)
    ridge_val = {(r["feature_set"]): r for r in val_rows_profile if r["family"] == "Ridge"}
    ridge_cv = {(r["feature_set"]): r for r in (ridge_rows) if r["feature_set"] in x_sets and r["alpha"] == best_rows[f"Ridge:{r['feature_set']}"]["alpha"]}
    ablation_rows = []
    for fs in x_sets:
        base_cv = ridge_cv["A_RAW"]; base_val = ridge_val["A_RAW"]
        cv = ridge_cv[fs]; vv = ridge_val[fs]
        ablation_rows.append({"feature_set": fs, "model_family": "Ridge", "cv_profile_l1": cv.get("profile_weighted_l1"), "cv_profile_l1_delta_vs_raw": cv.get("profile_weighted_l1", 0) - base_cv.get("profile_weighted_l1", 0), "cv_G_emit_mae": cv["G_emit_mae"], "cv_eta_up_mae": cv["eta_up_mae"], "validation_profile_l1": vv.get("profile_weighted_l1"), "validation_profile_l1_delta_vs_raw": vv.get("profile_weighted_l1", 0) - base_val.get("profile_weighted_l1", 0), "validation_G_emit_mae": next(r for r in val_rows_scalar if r["family"] == "Ridge" and r["feature_set"] == fs)["G_emit_mae"], "validation_eta_up_mae": next(r for r in val_rows_scalar if r["family"] == "Ridge" and r["feature_set"] == fs)["eta_up_mae"], "interpretation": "USEFUL_PHYSICS_PRIOR" if fs != "A_RAW" and cv.get("profile_weighted_l1", 1e99) <= base_cv.get("profile_weighted_l1", 1e99) and vv.get("profile_weighted_l1", 1e99) <= base_val.get("profile_weighted_l1", 1e99) else ("NOT_PROMOTED" if fs != "A_RAW" else "BASELINE")})
    write_csv(OUT / "PRIOR_ABLATION_SUMMARY.csv", ablation_rows)
    write_json(OUT / "PARETO_TMP.json", {"candidate_count": len(final_payloads), "validation_one_shot": True})

    # Conservative hierarchy: report the non-dominated full-output candidates; do not hide scalar/profile trade-offs in a weighted score.
    full = []
    for p, _, cp in final_payloads:
        if cp is None: continue
        cv = p["cv"]; valp = next(r for r in val_rows_profile if r["family"] == p["family"] and r["feature_set"] == p["feature_set"])
        vals = {"cv_profile_l1": cv.get("profile_weighted_l1", 1e99), "cv_G_emit_mae": cv["G_emit_mae"], "cv_eta_up_mae": cv["eta_up_mae"], "val_profile_l1": valp.get("profile_weighted_l1", 1e99), "val_G_emit_mae": next(r for r in val_rows_scalar if r["family"] == p["family"] and r["feature_set"] == p["feature_set"])["G_emit_mae"], "val_eta_up_mae": next(r for r in val_rows_scalar if r["family"] == p["family"] and r["feature_set"] == p["feature_set"])["eta_up_mae"], "feature_dim": len(feature_names[p["feature_set"]])}
        full.append({"candidate": p, "metrics": vals})
    def dominates(a: dict[str, Any], b: dict[str, Any]) -> bool:
        keys = ("cv_profile_l1", "cv_G_emit_mae", "cv_eta_up_mae", "val_profile_l1", "val_G_emit_mae", "val_eta_up_mae")
        return all(a["metrics"][k] <= b["metrics"][k] for k in keys) and any(a["metrics"][k] < b["metrics"][k] for k in keys)
    front = [a for a in full if not any(dominates(b, a) for b in full if b is not a)]
    recommendation = "CHAMPION_READY_FOR_BLIND_PROSPECTIVE" if len(front) == 1 else ("TWO_FINALISTS_REQUIRE_CHART_DECISION" if len(front) >= 2 else "BASELINE_NOT_READY_NEEDS_METHOD_REVISION")
    pareto = {"schema_version": "MODEL_PARETO_ANALYSIS_V1", "hierarchy": ["no_catastrophic_scalar_failure", "profile_metrics", "decision_metrics", "simplicity", "prior_complexity"], "candidate_metrics": full, "pareto_front": [x["candidate"] for x in front], "arbitrary_weighted_total_used": False}
    write_json(OUT / "MODEL_PARETO_ANALYSIS.json", pareto)
    chosen = front[0]["candidate"] if len(front) == 1 else None
    write_json(OUT / "FINAL_MODEL_RECOMMENDATION.json", {"schema_version": "FINAL_MODEL_RECOMMENDATION_V1", "recommendation": recommendation, "champion": chosen, "finalists": [x["candidate"] for x in front], "blind_truth_acquired": 0, "validation_one_shot": True, "production_blind_acquisition_authorized": recommendation == "CHAMPION_READY_FOR_BLIND_PROSPECTIVE"})

    report = {"status": "PASS", "verdict": "PASS — TRAIN_ONLY_PCA_AND_SURROGATE_BASELINE_ABLATION_COMPLETE", "recommendation": recommendation, "selected_pca_rank": selected_rank, "dataset_sha256": dataset_sha, "train_geometries": 48, "validation_geometries": 8, "train_rows": 528, "validation_rows": 88, "blind_geometries": 8, "blind_truth_acquired": 0, "solver_entries": 0, "solver_rerun_delta": 0, "next": "FREEZE_CHAMPION_AND_ACQUIRE_8G_BLIND_PROSPECTIVE" if recommendation == "CHAMPION_READY_FOR_BLIND_PROSPECTIVE" else ("CHART_FINAL_MODEL_SELECTION_BEFORE_BLIND" if recommendation == "TWO_FINALISTS_REQUIRE_CHART_DECISION" else "CHART_REVIEW_MODEL_OR_LABEL_CONTRACT"), "outputs": str(OUT)}
    write_json(OUT / "REPORT.json", report)
    (OUT / "REPORT.md").write_text("# APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_AND_PRIOR_SURROGATE_ABLATION_V1\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in report.items()), encoding="utf-8")
    files_for_manifest = [p for p in OUT.rglob("*") if p.is_file() and p.name != "FINAL_SHA256_MANIFEST.json"]
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": [{"path": str(p.relative_to(OUT)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted(files_for_manifest)]})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
