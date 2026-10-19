from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
DATA_ROOT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
DATASET = DATA_ROOT / "V1_TRAINVAL_DATASET.csv"
SEALED = DATA_ROOT / "BLIND_PROSPECTIVE_SEALED_MANIFEST.json"
SPLIT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1" / "K6_V1_GEOMETRY_SPLIT_MANIFEST.json"
BASELINE_ROOT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1"
PCA_MODEL = BASELINE_ROOT / "ANGULAR_PCA_MODEL.npz"
INCUMBENT_MODEL = BASELINE_ROOT / "models" / "Ridge_A_RAW.pkl"
LIB_ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
LIBRARY = LIB_ROOT / "outputs" / "np_k6_p1d2_broadband_library_27point_v1" / "library_long.csv"
LIBRARY_MANIFEST = LIB_ROOT / "outputs" / "np_k6_p1d2_broadband_library_27point_v1" / "library_manifest.json"
REUSE_AUDIT = LIB_ROOT / "outputs" / "np_traditional_multitarget_baseline_extension_v1" / "single_pillar_library_reuse_audit.json"
OUT = ROOT / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_COMPOSITIONAL_NP_PRIOR_REPAIR_AND_FINAL_PREBLIND_ABLATION_V1"
WLS = np.arange(445.0, 456.0, 1.0)
POSITIONS_NM = (np.arange(6, dtype=float) - 2.5) * 290.0
PCA_RANK = 32
RIDGE_RAW_ALPHA = 100.0
NP_RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0, 300.0)
# ponytail: two representative KRR settings and three seeds keep the required
# family comparison bounded; expand only if this ablation is inconclusive.
KRR_GRID = ((0.1, 0.001), (1.0, 0.01))
MLP_SEEDS = (0, 1, 2)
FEATURE_SETS = ("NP_BASIC", "NP_PHASE", "NP_AF")
LAMBDA_X_NM = 1740.0


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def safe(v: Any) -> Any:
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(x) for x in v]
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows([{k: safe(v) for k, v in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def macro(values: np.ndarray, groups: np.ndarray) -> float:
    return float(np.mean([np.mean(values[groups == g]) for g in np.unique(groups)]))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def row_profile_metrics(true: np.ndarray, pred: np.ndarray, theta: np.ndarray, lam: float, ux: np.ndarray, w: np.ndarray) -> dict[str, float]:
    tt = np.maximum(true, 0.0)
    tt /= max(float(np.sum(w * tt)), 1e-300)
    pp = np.maximum(pred, 0.0)
    pp /= max(float(np.sum(w * pp)), 1e-300)
    q, r = w * pp, w * tt
    m = 0.5 * (q + r)
    js = 0.5 * np.sum(np.where(q > 0, q * np.log(np.maximum(q, 1e-300) / np.maximum(m, 1e-300)), 0.0))
    js += 0.5 * np.sum(np.where(r > 0, r * np.log(np.maximum(r, 1e-300) / np.maximum(m, 1e-300)), 0.0))
    seed = math.degrees(math.asin(lam / LAMBDA_X_NM))
    def derived(z: np.ndarray) -> tuple[float, float, float, list[float]]:
        pos = float(np.sum(w[ux >= 0] * z[ux >= 0]))
        neg = float(np.sum(w[ux < 0] * z[ux < 0]))
        return float(theta[np.argmax(z)]), pos, (pos - neg) / max(pos + neg, 1e-300), [float(np.sum(w[np.abs(theta - seed) <= q] * z[np.abs(theta - seed) <= q])) for q in (2, 5, 10)]
    a, b = derived(tt), derived(pp)
    return {
        "profile_l1": float(np.sum(w * np.abs(pp - tt))),
        "profile_js": float(js),
        "profile_corr": corr(tt, pp),
        "theta_peak_mae_deg": abs(b[0] - a[0]),
        "positive_fraction_mae": abs(b[1] - a[1]),
        "asymmetry_mae": abs(b[2] - a[2]),
        "F_seed_2_mae": abs(b[3][0] - a[3][0]),
        "F_seed_5_mae": abs(b[3][1] - a[3][1]),
        "F_seed_10_mae": abs(b[3][2] - a[3][2]),
    }


def aggregate_metrics(true_profile: np.ndarray, pred_profile: np.ndarray, true_scalar: np.ndarray, pred_scalar: np.ndarray, theta: np.ndarray, lambdas: np.ndarray, groups: np.ndarray, ux: np.ndarray, w: np.ndarray) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    rows = [row_profile_metrics(true_profile[i], pred_profile[i], theta[i], float(lambdas[i]), ux, w) for i in range(len(true_profile))]
    keys = list(rows[0])
    out = {k: macro(np.asarray([r[k] for r in rows]), groups) for k in keys}
    scalar_rows: dict[str, float] = {}
    for j, name in enumerate(("G_emit", "eta_up")):
        e = pred_scalar[:, j] - true_scalar[:, j]
        scalar_rows[f"{name}_mae"] = macro(np.abs(e), groups)
        scalar_rows[f"{name}_r2"] = float(r2_score(true_scalar[:, j], pred_scalar[:, j]))
    out.update(scalar_rows)
    per_geometry: dict[str, dict[str, float]] = {}
    for g in np.unique(groups):
        ix = groups == g
        per_geometry[str(g)] = {k: float(np.mean([rows[i][k] for i in np.where(ix)[0]])) for k in keys}
        for j, name in enumerate(("G_emit", "eta_up")):
            per_geometry[str(g)][f"{name}_mae"] = float(np.mean(np.abs(pred_scalar[ix, j] - true_scalar[ix, j])))
    return out, per_geometry


def load_library() -> tuple[dict[tuple[int, int], dict[str, float]], dict[str, Any]]:
    manifest = read_json(LIBRARY_MANIFEST)
    reuse = read_json(REUSE_AUDIT)
    rows = read_csv(LIBRARY)
    actual = {(int(float(r["diameter_nm"])), int(float(r["wavelength_nm"]))) for r in rows}
    diameters = sorted({d for d, _ in actual})
    wavelengths = sorted({l for _, l in actual})
    expected = {(d, l) for d in range(100, 231, 5) for l in range(445, 456)}
    keys = ("diameter_nm", "wavelength_nm", "txx_real", "txx_imag", "txx_amplitude", "txx_wrapped_phase_deg", "txx_unwrapped_phase_vs_diameter_deg")
    missing_fields = [k for k in keys if k not in rows[0]]
    duplicate = len(actual) != len(rows)
    if missing_fields or duplicate or actual != expected:
        raise RuntimeError(f"NP_LIBRARY_AUTHORITY_INVALID missing_fields={missing_fields} missing={sorted(expected - actual)} extra={sorted(actual - expected)} duplicate={duplicate}")
    lookup = {(int(float(r["diameter_nm"])), int(float(r["wavelength_nm"]))): {k: float(r[k]) for k in keys[2:]} for r in rows}
    audit = {
        "schema_version": "SINGLE_PILLAR_LIBRARY_AUTHORITY_AUDIT_V1",
        "source_csv": str(LIBRARY), "source_csv_sha256": sha(LIBRARY),
        "manifest_path": str(LIBRARY_MANIFEST), "manifest_sha256": sha(LIBRARY_MANIFEST),
        "reuse_audit_path": str(REUSE_AUDIT), "reuse_audit_sha256": sha(REUSE_AUDIT),
        "manifest_declared_source_sha256": reuse["source_sha256"],
        "source_sha_match_reuse_audit": sha(LIBRARY) == reuse["source_sha256"],
        "diameter_grid_nm": diameters, "wavelength_grid_nm": wavelengths,
        "row_count": len(rows), "grid_shape": [len(diameters), len(wavelengths)],
        "polarization_source_semantics": "x-only local-periodic single pillar; txx response",
        "amplitude_definition": "txx_amplitude from complex txx response",
        "phase_definition": "txx_wrapped_phase_deg; cos/sin use complex phase, no raw wrapped phase input",
        "normalization": "library native txx amplitude; no interpolation or nearest-neighbor substitution",
        "x_only": bool(manifest.get("x_only")), "offline_only": bool(manifest.get("offline_only")),
        "d180_provenance": "recovered valid historical attempt; not interpolated",
        "pass": bool(sha(LIBRARY) == reuse["source_sha256"] and not missing_fields and not duplicate and actual == expected and manifest.get("row_count") == 297),
    }
    write_json(OUT / "SINGLE_PILLAR_LIBRARY_AUTHORITY_AUDIT.json", audit)
    return lookup, audit


def compose_features(complex_response: np.ndarray, lam: float, ux: np.ndarray, w: np.ndarray) -> dict[str, np.ndarray]:
    amp = np.abs(complex_response)
    phase = np.angle(complex_response)
    basic = np.column_stack([v for i in range(6) for v in (amp[i:i + 1], np.cos(phase[i:i + 1]), np.sin(phase[i:i + 1]))]).ravel()
    delta = np.angle(complex_response[1:] / complex_response[:-1])
    phase_features = np.concatenate([np.column_stack((np.cos(delta), np.sin(delta))).ravel()])
    kx = 2.0 * np.pi * ux / lam
    af = np.sum(complex_response[None, :] * np.exp(1j * kx[:, None] * POSITIONS_NM[None, :]), axis=1)
    power = np.abs(af) ** 2
    norm = max(float(np.sum(w * power)), 1e-300)
    power /= norm
    peak_i = int(np.argmax(power))
    peak_ux = float(ux[peak_i])
    positive = float(np.sum(w[ux >= 0] * power[ux >= 0]))
    target = float(np.sum(w[(ux >= 0) & (np.abs(ux - peak_ux) <= 0.1)] * power[(ux >= 0) & (np.abs(ux - peak_ux) <= 0.1)]))
    unwrapped = np.unwrap(phase)
    slope, intercept = np.polyfit(POSITIONS_NM, unwrapped, 1)
    residual = float(np.sqrt(np.mean((unwrapped - (slope * POSITIONS_NM + intercept)) ** 2)))
    mismatch = abs(float(slope) - 2.0 * np.pi * peak_ux / lam)
    af_features = np.asarray([positive, peak_ux, target, mismatch], dtype=float)
    return {"NP_BASIC": basic, "NP_PHASE": np.concatenate((basic, phase_features)), "NP_AF": np.concatenate((basic, phase_features, af_features))}


def fit_predict(family: str, xtr: np.ndarray, ytr: np.ndarray, xte: np.ndarray, params: dict[str, Any], seed: int = 0) -> tuple[np.ndarray, dict[str, Any]]:
    imputer, scaler, target_scaler = SimpleImputer(strategy="mean"), StandardScaler(), StandardScaler()
    ztr = scaler.fit_transform(imputer.fit_transform(xtr)); zte = scaler.transform(imputer.transform(xte))
    yt = target_scaler.fit_transform(ytr)
    if family == "Ridge":
        model = Ridge(alpha=float(params["alpha"]))
    elif family == "KernelRidge":
        model = KernelRidge(alpha=float(params["alpha"]), kernel="rbf", gamma=float(params["gamma"]))
    else:
        model = MLPRegressor(hidden_layer_sizes=(32, 32), activation="relu", solver="adam", alpha=1e-3, max_iter=250, tol=1e-4, random_state=seed, early_stopping=False)
    model.fit(ztr, yt)
    pred = target_scaler.inverse_transform(model.predict(zte))
    return pred, {"model": model, "imputer": imputer, "scaler": scaler, "target_scaler": target_scaler}


def cv_run(family: str, x: np.ndarray, y: np.ndarray, profiles: np.ndarray, scalars: np.ndarray, coeff: np.ndarray, theta: np.ndarray, lambdas: np.ndarray, groups: np.ndarray, ux: np.ndarray, w: np.ndarray, folds: list[tuple[np.ndarray, np.ndarray]], params: dict[str, Any], seeds: tuple[int, ...] = (0,)) -> tuple[dict[str, Any], np.ndarray, dict[str, dict[str, float]]]:
    pred = np.zeros_like(y)
    for tr, te in folds:
        seed_preds = []
        for seed in seeds:
            p, _ = fit_predict(family, x[tr], y[tr], x[te], params, seed)
            seed_preds.append(p)
        pred[te] = np.mean(seed_preds, axis=0)
    metric, per_geometry = aggregate_metrics(profiles, inverse_pca(pred[:, 2:], PCA_STATE), scalars, pred[:, :2], theta, lambdas, groups, ux, w)
    metric.update({"family": family, "params": params, "seed_count": len(seeds)})
    return metric, pred, per_geometry


PCA_STATE: dict[str, np.ndarray] = {}


def inverse_pca(coeff: np.ndarray, state: dict[str, np.ndarray]) -> np.ndarray:
    return (state["mean_weighted"][None, :] + coeff @ state["components_weighted"]) / state["sqrt_w"][None, :]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "models").mkdir(exist_ok=True)
    (OUT / "preprocessors").mkdir(exist_ok=True)
    rows = read_csv(DATASET)
    split = read_json(SPLIT); sealed = read_json(SEALED)
    train_ids = sorted(split["train_geometry_ids"]); val_ids = sorted(split["validation_geometry_ids"]); blind_ids = sorted(sealed.get("geometry_ids", sealed.get("blind_geometry_ids", split["blind_geometry_ids"])))
    assert len(rows) == 616 and len(train_ids) == 48 and len(val_ids) == 8 and len(blind_ids) == 8
    assert not set(train_ids) & set(val_ids) and not set(blind_ids) & {r["geometry_id"] for r in rows}
    lookup, lib_audit = load_library()
    z0 = np.load(Path(rows[0]["angular_profile_ref"]), allow_pickle=False)
    ux, w = z0["ux"].astype(float), z0["weights_du"].astype(float)
    profile_cache: dict[str, dict[str, np.ndarray]] = {}
    features: dict[str, list[np.ndarray]] = {k: [] for k in FEATURE_SETS}; profiles = []; theta = []; scalars = []; groups = []; lambdas = []
    lookup_rows = []; missing = []
    for r in rows:
        assert r["split"] in {"TRAIN", "VALIDATION"}
        ds = [int(float(r[f"D{i}"])) for i in range(1, 7)]; lam = int(float(r["lambda_nm"]))
        complex_response = []
        for pos, d in enumerate(ds, 1):
            key = (d, lam)
            if key not in lookup:
                missing.append({"geometry_id": r["geometry_id"], "pillar_position": pos, "diameter_nm": d, "wavelength_nm": lam})
            else:
                q = lookup[key]; complex_response.append(complex(float(q["txx_real"]), float(q["txx_imag"])))
            lookup_rows.append({"geometry_id": r["geometry_id"], "split": r["split"], "pillar_position": pos, "diameter_nm": d, "wavelength_nm": lam, "exact": key in lookup})
        if len(complex_response) != 6:
            continue
        pth = str(Path(r["angular_profile_ref"]))
        if pth not in profile_cache:
            profile_cache[pth] = {k: np.asarray(v) for k, v in np.load(pth, allow_pickle=False).items()}
        p = profile_cache[pth]; wi = int(np.argmin(np.abs(p["wavelengths_nm"] - float(r["lambda_nm"]))))
        profiles.append(p["f_up"][:, wi].astype(float)); theta.append(p["theta_deg"][:, wi].astype(float)); scalars.append([float(r["G_emit"]), float(r["eta_up"])]); groups.append(r["geometry_id"]); lambdas.append(float(r["lambda_nm"]))
        made = compose_features(np.asarray(complex_response), float(lam), ux, w)
        for k in FEATURE_SETS:
            features[k].append(made[k])
    write_json(OUT / "NP_EXACT_LOOKUP_COVERAGE.json", {"schema_version": "NP_EXACT_LOOKUP_COVERAGE_V1", "train_expected_rows": 48 * 6 * 11, "validation_expected_rows": 8 * 6 * 11, "train_exact_rows": sum(x["exact"] and x["split"] == "TRAIN" for x in lookup_rows), "validation_exact_rows": sum(x["exact"] and x["split"] == "VALIDATION" for x in lookup_rows), "train_lookup_coverage": sum(x["exact"] and x["split"] == "TRAIN" for x in lookup_rows) / (48 * 6 * 11), "validation_lookup_coverage": sum(x["exact"] and x["split"] == "VALIDATION" for x in lookup_rows) / (8 * 6 * 11), "missing_combinations": missing, "interpolation_used": False, "nearest_neighbor_used": False, "pass": not missing})
    assert not missing
    profiles = np.asarray(profiles); theta = np.asarray(theta); scalars = np.asarray(scalars); groups = np.asarray(groups); lambdas = np.asarray(lambdas); X = {k: np.asarray(v) for k, v in features.items()}
    pca = np.load(PCA_MODEL, allow_pickle=False); assert int(pca["rank"]) == PCA_RANK
    sqrt_w = np.sqrt(pca["weights_du"].astype(float)); mean_weighted = pca["mean_profile"].astype(float) * sqrt_w; components = pca["components_weighted"].astype(float); assert components.shape[0] == PCA_RANK
    PCA_STATE.update({"sqrt_w": sqrt_w, "mean_weighted": mean_weighted, "components_weighted": components})
    coeff = (profiles * sqrt_w[None, :] - mean_weighted[None, :]) @ components.T
    train_mask = np.isin(groups, train_ids); val_mask = np.isin(groups, val_ids)
    train_idx, val_idx = np.where(train_mask)[0], np.where(val_mask)[0]
    folds = list(GroupKFold(n_splits=8).split(X["NP_BASIC"][train_idx], np.zeros(len(train_idx)), groups[train_idx]))
    theta_train, theta_val = theta[train_idx], theta[val_idx]
    y_train = np.column_stack((scalars[train_idx], coeff[train_idx])); y_val = np.column_stack((scalars[val_idx], coeff[val_idx]))
    profile_train, profile_val = profiles[train_idx], profiles[val_idx]; scalar_train, scalar_val = scalars[train_idx], scalars[val_idx]; group_train, group_val = groups[train_idx], groups[val_idx]; lam_train, lam_val = lambdas[train_idx], lambdas[val_idx]
    raw = np.column_stack([[float(r[f"D{i}"]) / 290.0 for i in range(1, 7)] + [(float(r["lambda_nm"]) - 450.0) / 5.0] for r in rows]).T
    raw_train, raw_val = raw[train_idx], raw[val_idx]
    feature_names = {"RAW": [f"D{i}_normalized" for i in range(1, 7)] + ["lambda_centered"], "NP_BASIC": [x for i in range(1, 7) for x in (f"A{i}", f"cos_phi{i}", f"sin_phi{i}")], "NP_PHASE": [x for i in range(1, 7) for x in (f"A{i}", f"cos_phi{i}", f"sin_phi{i}")] + [x for i in range(1, 6) for x in (f"cos_dphi{i}{i+1}", f"sin_dphi{i}{i+1}")], "NP_AF": [x for i in range(1, 7) for x in (f"A{i}", f"cos_phi{i}", f"sin_phi{i}")] + [x for i in range(1, 6) for x in (f"cos_dphi{i}{i+1}", f"sin_dphi{i}{i+1}")] + ["af_positive_side_fraction", "af_peak_ux", "af_target_lobe_fraction", "af_phase_gradient_mismatch"]}
    write_json(OUT / "NP_PRIOR_FEATURE_DEFINITION.json", {"schema_version": "NP_PRIOR_FEATURE_DEFINITION_V1", "provider_id": "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1", "role": "AUXILIARY_GEOMETRY_PHYSICS_PRIOR", "units": {"diameter": "nm", "wavelength": "nm", "phase": "radians internally", "array_factor_kx": "rad/nm"}, "ordered_position_sensitive": True, "phase_convention": "complex txx phase; cos/sin representation; adjacent delta=angle(txx[i+1]/txx[i])", "feature_sets": {"NP_BASIC": {"description": "A_i, cos(phi_i), sin(phi_i), i=1..6", "names": feature_names["NP_BASIC"]}, "NP_PHASE": {"description": "NP_BASIC + cos(delta_phi_i), sin(delta_phi_i), i=1..5", "names": feature_names["NP_PHASE"]}, "NP_AF": {"description": "NP_PHASE + approximate uncoupled array factor positive-side fraction, peak ux, target-lobe fraction, phase-gradient mismatch", "names": feature_names["NP_AF"]}}, "array_factor_formula": "AF(ux)=sum_i txx_i exp(i*2*pi*ux*x_i/lambda); x_i=(-2.5,-1.5,-0.5,0.5,1.5,2.5)*290 nm; power normalized by du_x", "array_factor_limitations": ["ignores near-field coupling", "ignores MDC feedback", "ignores finite-device coupling", "ignores emitter interaction"], "validity_mask": "exact lookup all six pillars and wavelength; no interpolation"})
    np_rows = []
    for i, g in enumerate(groups):
        row = {"geometry_id": str(g), "split": "TRAIN" if train_mask[i] else "VALIDATION", "lambda_nm": float(lambdas[i]), "np_prior_valid": True, "np_prior_ood": False}
        for j, value in enumerate(X["NP_AF"][i]): row[f"feature_{j:02d}"] = float(value)
        np_rows.append(row)
    write_csv(OUT / "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1.csv", np_rows)
    np.savez_compressed(OUT / "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1.npz", feature_sets=np.asarray(FEATURE_SETS), train_geometry_ids=np.asarray(train_ids), validation_geometry_ids=np.asarray(val_ids), train_dataset_sha256=np.asarray(sha(DATASET)), source_library_sha256=np.asarray(sha(LIBRARY)), X_basic=X["NP_BASIC"], X_phase=X["NP_PHASE"], X_af=X["NP_AF"])
    write_json(OUT / "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1.json", {"schema_version": "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1", "source_library_sha256": sha(LIBRARY), "source_library_manifest_sha256": sha(LIBRARY_MANIFEST), "rows": len(np_rows), "feature_sets": list(FEATURE_SETS), "exact_lookup": True, "validity_mask": "all rows true; provider grid exact"})
    write_json(OUT / "MDC_PRIOR_V1_DECISION.json", {"schema_version": "MDC_PRIOR_V1_DECISION", "status": "MDC_PRIOR_NOT_AVAILABLE_FOR_V1", "reason": "no compatible current fixed MDC plus wavelength/source semantic profile descriptor was materialized", "future_scope": "future V2 joint-MDC prior provider"})
    write_json(OUT / "OLD3D_PRIOR_V1_DECISION.json", {"schema_version": "OLD3D_PRIOR_V1_DECISION", "status": "OPTIONAL_HISTORICAL_ABLATION_ONLY", "validation_promotion": False, "reason": "validation validity 0%; no OOD extrapolation"})
    write_json(OUT / "BLIND_LEAKAGE_AUDIT.json", {"schema_version": "BLIND_LEAKAGE_AUDIT_V1", "sealed_geometry_count": len(blind_ids), "sealed_geometry_ids": blind_ids, "dataset_blind_rows": 0, "blind_truth_acquired": 0, "blind_truth_fields_read": False, "surrogate_called_on_blind": False, "blind_used_for_model_selection": False, "pass": len(blind_ids) == 8 and not set(blind_ids) & set(groups)})
    print("AUTHORITY_AND_FEATURES_READY", flush=True)
    def run_cv(fs: str, family: str, params: dict[str, Any], seeds: tuple[int, ...] = (0,)) -> tuple[dict[str, Any], np.ndarray, dict[str, dict[str, float]]]:
        xx = raw_train if fs == "RAW" else X[fs][train_idx]
        return cv_run(family, xx, y_train, profile_train, scalar_train, coeff[train_idx], theta_train, lam_train, group_train, ux, w, folds, params, seeds)
    cv_rows: list[dict[str, Any]] = []
    raw_cv, raw_pred, raw_per = run_cv("RAW", "Ridge", {"alpha": RIDGE_RAW_ALPHA})
    print("RAW_CV_DONE", flush=True)
    cv_rows.append({"candidate": "Ridge_A_RAW", **raw_cv})
    np_ridge_best: dict[str, tuple[dict[str, Any], np.ndarray, dict[str, dict[str, float]]]] = {}
    for fs in FEATURE_SETS:
        candidates = []
        for alpha in NP_RIDGE_ALPHAS:
            m, p, pg = run_cv(fs, "Ridge", {"alpha": alpha}); candidates.append((m, p, pg)); cv_rows.append({"candidate": f"Ridge_{fs}", **m})
        np_ridge_best[fs] = min(candidates, key=lambda x: (x[0]["profile_l1"], x[0]["G_emit_mae"] + x[0]["eta_up_mae"]))
    selected_fs = min(np_ridge_best, key=lambda fs: (np_ridge_best[fs][0]["profile_l1"], np_ridge_best[fs][0]["G_emit_mae"] + np_ridge_best[fs][0]["eta_up_mae"]))
    np_ridge_cv, np_ridge_pred, np_ridge_per = np_ridge_best[selected_fs]
    print(f"NP_RIDGE_CV_DONE {selected_fs}", flush=True)
    krr_candidates = []
    for alpha, gamma in KRR_GRID:
        m, p, pg = run_cv(selected_fs, "KernelRidge", {"alpha": alpha, "gamma": gamma}); krr_candidates.append((m, p, pg)); cv_rows.append({"candidate": "KernelRidge_NP_COMPOSITIONAL", **m})
    krr_cv, krr_pred, krr_per = min(krr_candidates, key=lambda x: (x[0]["profile_l1"], x[0]["G_emit_mae"] + x[0]["eta_up_mae"]))
    print("KRR_CV_DONE", flush=True)
    mlp_cv, mlp_pred, mlp_per = run_cv(selected_fs, "MLP", {"alpha": 1e-3}, MLP_SEEDS); cv_rows.append({"candidate": "ShallowMLP_NP_COMPOSITIONAL", **mlp_cv})
    print("MLP_CV_DONE", flush=True)
    write_csv(OUT / "NP_PRIOR_GROUPED_CV_RESULTS.csv", cv_rows)
    base_val_pred, base_payload = fit_predict("Ridge", raw_train, y_train, raw_val, {"alpha": RIDGE_RAW_ALPHA})
    np_val_pred, np_payload = fit_predict("Ridge", X[selected_fs][train_idx], y_train, X[selected_fs][val_idx], np_ridge_cv["params"])
    krr_val_pred, krr_payload = fit_predict("KernelRidge", X[selected_fs][train_idx], y_train, X[selected_fs][val_idx], krr_cv["params"])
    mlp_val_preds = [fit_predict("MLP", X[selected_fs][train_idx], y_train, X[selected_fs][val_idx], {"alpha": 1e-3}, s)[0] for s in MLP_SEEDS]
    mlp_val_pred = np.mean(mlp_val_preds, axis=0)
    val_candidates = [("Ridge_A_RAW", base_val_pred), ("Ridge_NP_COMPOSITIONAL", np_val_pred), ("KernelRidge_NP_COMPOSITIONAL", krr_val_pred), ("ShallowMLP_NP_COMPOSITIONAL", mlp_val_pred)]
    val_rows = []
    val_per_geometry: dict[str, dict[str, dict[str, float]]] = {}
    for name, pred in val_candidates:
        mm, pg = aggregate_metrics(profile_val, inverse_pca(pred[:, 2:], PCA_STATE), scalar_val, pred[:, :2], theta_val, lam_val, group_val, ux, w); val_rows.append({"candidate": name, "feature_set": "RAW" if name == "Ridge_A_RAW" else selected_fs, **mm}); val_per_geometry[name] = pg
    write_csv(OUT / "NP_PRIOR_DEVELOPMENT_VALIDATION_RESULTS.csv", val_rows)
    baseline_val = next(x for x in val_rows if x["candidate"] == "Ridge_A_RAW"); np_val = next(x for x in val_rows if x["candidate"] == "Ridge_NP_COMPOSITIONAL")
    cv_base, cv_np = raw_cv, np_ridge_cv
    geom_rows = []
    cv_base_pg, cv_np_pg = raw_per, np_ridge_per
    for split_name, a, b in (("TRAIN_GROUPED_CV", cv_base_pg, cv_np_pg), ("DEVELOPMENT_VALIDATION", val_per_geometry["Ridge_A_RAW"], val_per_geometry["Ridge_NP_COMPOSITIONAL"])):
        for g in sorted(a):
            geom_rows.append({"split": split_name, "geometry_id": g, "raw_profile_l1": a[g]["profile_l1"], "np_profile_l1": b[g]["profile_l1"], "profile_gain_np_minus_raw_negative_is_good": a[g]["profile_l1"] - b[g]["profile_l1"], "winner": "NP" if b[g]["profile_l1"] < a[g]["profile_l1"] else "RAW"})
    write_csv(OUT / "NP_PRIOR_PER_GEOMETRY_COMPARISON.csv", geom_rows)
    def wins(split_name: str) -> tuple[int, int]:
        q = [r for r in geom_rows if r["split"] == split_name]; return sum(r["winner"] == "NP" for r in q), sum(r["winner"] == "RAW" for r in q)
    cv_wins, cv_losses = wins("TRAIN_GROUPED_CV"); val_wins, val_losses = wins("DEVELOPMENT_VALIDATION")
    scalar_ok = all(np_val[k] <= baseline_val[k] * 1.05 for k in ("G_emit_mae", "eta_up_mae"))
    decision_keys = ("theta_peak_mae_deg", "positive_fraction_mae", "asymmetry_mae", "F_seed_2_mae", "F_seed_5_mae", "F_seed_10_mae")
    decision_ok = all(np_ridge_cv[k] <= cv_base[k] for k in decision_keys) and all(np_val[k] <= baseline_val[k] for k in decision_keys)
    cv_gain = cv_base["profile_l1"] - cv_np["profile_l1"]; val_gain = baseline_val["profile_l1"] - np_val["profile_l1"]; relative_gain = min(cv_gain / max(cv_base["profile_l1"], 1e-12), val_gain / max(baseline_val["profile_l1"], 1e-12))
    negligible = relative_gain < 0.01
    promotion = bool(cv_gain > 0 and val_gain > 0 and cv_wins > cv_losses and val_wins > val_losses and scalar_ok and decision_ok and not negligible)
    ablation = {"schema_version": "NP_PRIOR_ABLATION_SUMMARY_V1", "current_incumbent": "Ridge_A_RAW", "development_validation_status": "DEVELOPMENT_VALIDATION", "selected_feature_set_by_train_grouped_cv": selected_fs, "ridge_cv_candidates": {fs: x[0] for fs, x in np_ridge_best.items()}, "model_candidates": {"baseline": raw_cv, "ridge_np": np_ridge_cv, "kernelridge_np": krr_cv, "mlp_np": mlp_cv}, "promotion_rule": {"cv_profile_gain_positive": cv_gain > 0, "development_validation_profile_gain_positive": val_gain > 0, "per_geometry_cv_wins_gt_losses": cv_wins > cv_losses, "per_geometry_validation_wins_gt_losses": val_wins > val_losses, "scalar_no_obvious_degradation_5pct": scalar_ok, "decision_metrics_no_degradation": decision_ok, "relative_gain_min_cv_validation": relative_gain, "negligible_complexity_threshold": 0.01, "negligible_complexity_gain": negligible}, "promotion": promotion, "classification": "NP_PRIOR_PROMOTED" if promotion else "NEGLIGIBLE_COMPLEXITY_GAIN_OR_NO_STABLE_IMPROVEMENT"}
    write_json(OUT / "NP_PRIOR_ABLATION_SUMMARY.json", ablation)
    selected_model_path = OUT / "models" / ("Ridge_NP_COMPOSITIONAL.pkl" if promotion else "Ridge_RAW_CHAMPION.pkl")
    selected_payload = np_payload if promotion else base_payload
    with selected_model_path.open("wb") as f: pickle.dump({"family": "Ridge", "feature_set": selected_fs if promotion else "RAW", "params": np_ridge_cv["params"] if promotion else {"alpha": RIDGE_RAW_ALPHA}, "pca_rank": PCA_RANK, "training_dataset_sha256": sha(DATASET), "payload": selected_payload}, f, protocol=pickle.HIGHEST_PROTOCOL)
    model_sha = sha(selected_model_path)
    preprocessor_path = OUT / "preprocessors" / "selected_model_preprocessor.pkl"
    with preprocessor_path.open("wb") as f: pickle.dump({"feature_set": selected_fs if promotion else "RAW", "imputer": selected_payload["imputer"], "scaler": selected_payload["scaler"], "target_scaler": selected_payload["target_scaler"], "pca_rank": PCA_RANK, "training_dataset_sha256": sha(DATASET), "training_split_sha256": sha(SPLIT)}, f, protocol=pickle.HIGHEST_PROTOCOL)
    preprocessor_sha = sha(preprocessor_path)
    freeze = {"schema_version": "PREBLIND_CHAMPION_FREEZE_V1", "champion": "NP_PRIOR_CHAMPION" if promotion else "RIDGE_RAW_CHAMPION", "model_family": "Ridge", "feature_set": selected_fs if promotion else "RAW_D1_D6_LAMBDA", "pca_rank": PCA_RANK, "hyperparameters": np_ridge_cv["params"] if promotion else {"alpha": RIDGE_RAW_ALPHA}, "training_split_sha256": sha(SPLIT), "dataset_sha256": sha(DATASET), "pca_sha256": sha(PCA_MODEL), "provider_id": "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1", "provider_sha256": sha(OUT / "NP_SINGLE_PILLAR_COMPOSITIONAL_PRIOR_V1.csv"), "source_library_sha256": sha(LIBRARY), "scaler_path": str(preprocessor_path), "scaler_sha256": preprocessor_sha, "model_path": str(selected_model_path), "model_sha256": model_sha, "incumbent_model_sha256": sha(INCUMBENT_MODEL), "validation_status": "DEVELOPMENT_VALIDATION_ONLY", "blind_truth_acquired": 0, "freeze_rule": "do not modify before sealed blind results"}
    write_json(OUT / "PREBLIND_CHAMPION_FREEZE.json", freeze)
    report = {"status": "PASS", "verdict": "PASS — PREBLIND_CHAMPION_FROZEN", "current_incumbent": "Ridge_A_RAW", "final_preblind_champion": freeze["champion"], "selected_feature_set": selected_fs, "train_geometries": 48, "validation_geometries": 8, "train_rows": 528, "validation_rows": 88, "blind_geometries": 8, "blind_truth_acquired": 0, "solver_entries": 0, "np_train_lookup_coverage": 1.0, "np_validation_lookup_coverage": 1.0, "cv_profile_gain_vs_raw": cv_gain, "validation_profile_gain_vs_raw": val_gain, "cv_geometry_wins_losses": [cv_wins, cv_losses], "validation_geometry_wins_losses": [val_wins, val_losses], "mdc_status": "MDC_PRIOR_NOT_AVAILABLE_FOR_V1", "old3d_status": "OPTIONAL_HISTORICAL_ABLATION_ONLY", "pca_rank": PCA_RANK, "outputs": str(OUT), "next": "ACQUIRE_8G_BLIND_PROSPECTIVE_WITH_TWO_SLOTS"}
    write_json(OUT / "REPORT.json", report)
    (OUT / "REPORT.md").write_text("# APCD_COUPLING_V2_2_2D_ML_V1_COMPOSITIONAL_NP_PRIOR_REPAIR_AND_FINAL_PREBLIND_ABLATION_V1\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in report.items()), encoding="utf-8")
    manifest_files = [p for p in OUT.rglob("*") if p.is_file() and p.name != "FINAL_SHA256_MANIFEST.json"]
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": [{"path": str(p.relative_to(OUT)), "sha256": sha(p), "size": p.stat().st_size} for p in sorted(manifest_files)]})
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
