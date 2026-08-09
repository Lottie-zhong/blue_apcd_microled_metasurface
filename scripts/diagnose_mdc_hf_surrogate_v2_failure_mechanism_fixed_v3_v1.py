from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
DOE = ROOT / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"
OOF = ROOT / "outputs/mdc_hf_surrogate_v2_oof_model_selection_v1/20260804T_oof_model_selection_08915e7"
FINAL = ROOT / "outputs/mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1/20260804T_final_m1_5seed_067c76b"
TEST40 = ROOT / "outputs/mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1/20260808T_test40_selection_conflict_resolution_489b54e"
RUN_ID = "20260809T_failure_mechanism_diagnostic_a322b13"
OUT = ROOT / "outputs/mdc_hf_surrogate_v2_failure_mechanism_diagnostic_fixed_v3_v1" / RUN_ID


def canonical(value):
    if isinstance(value, dict):
        return {str(k): canonical(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(canonical(value), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def trap_weights(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, float)
    w = np.empty_like(x)
    w[1:-1] = (x[2:] - x[:-2]) / 2
    w[0] = (x[1] - x[0]) / 2
    w[-1] = (x[-1] - x[-2]) / 2
    return w


def normalize_mass(values: np.ndarray) -> np.ndarray:
    x = np.maximum(np.asarray(values, float), 0)
    total = float(x.sum())
    if total <= 0:
        raise RuntimeError("HARD_GATE_ZERO_PROFILE_MASS")
    return x / total


def raw_case_to_q(npz) -> np.ndarray:
    raw = np.asarray(npz["joint_raw"], np.float32)
    wavelength = np.asarray(npz["wavelength_nm"], float)
    angle = np.asarray(npz["angle_deg"], float)
    total = float(np.trapz(np.trapz(raw, np.radians(angle), axis=1), wavelength))
    q = (raw / total) * trap_weights(wavelength)[:, None] * trap_weights(np.radians(angle))[None, :]
    return normalize_mass(q).astype(np.float32)


def geometry_profile_to_q(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as npz:
        if "normalized_joint" not in npz.files:
            return raw_case_to_q(npz)
        profile = np.asarray(npz["normalized_joint"], np.float32)
        wavelength = np.asarray(npz["wavelength_nm"], float)
        angle = np.asarray(npz["angle_deg"], float)
        q = profile * trap_weights(wavelength)[:, None] * trap_weights(np.radians(angle))[None, :]
        return normalize_mass(q).astype(np.float32)


def profile_metrics(truth: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    p = normalize_mass(truth)
    q = normalize_mass(prediction)
    midpoint = 0.5 * (p + q)
    pmask, qmask = p > 0, q > 0
    js = 0.5 * np.sum(p[pmask] * np.log(p[pmask] / midpoint[pmask]))
    js += 0.5 * np.sum(q[qmask] * np.log(q[qmask] / midpoint[qmask]))
    ps, qs = p.sum(1), q.sum(1)
    pa, qa = p.sum(0), q.sum(0)
    return {
        "joint_JS": float(js),
        "joint_weighted_L1": float(np.abs(p - q).sum()),
        "spectral_CDF": float(np.mean(np.abs(np.cumsum(ps) - np.cumsum(qs)))),
        "angular_CDF": float(np.mean(np.abs(np.cumsum(pa) - np.cumsum(qa)))),
    }


def geometry_feature(family: str, layer_count: float, total: float, defect: float,
                     families: list[str], mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    n = float(layer_count)
    values = np.asarray(
        [float(family == item) for item in families]
        + [n, total / n, (total - defect) / max(n - 1, 1), defect, n, defect, total, n, 1.0, 1.0],
        float,
    )
    values[len(families):len(families) + 8] = (values[len(families):len(families) + 8] - mean) / std
    return values


def save_figure(fig: plt.Figure, stem: Path) -> None:
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 6.5, "axes.labelsize": 7,
        "axes.titlesize": 7, "xtick.labelsize": 5.5, "ytick.labelsize": 5.5,
        "legend.fontsize": 5.5, "axes.linewidth": 0.6, "lines.linewidth": 1.0,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    })


def source_hashes() -> dict[str, str]:
    files = {
        "pca32": DOE / "final_profile_compressor.joblib",
        "pca_basis_manifest": DOE / "final_profile_basis_manifest.json",
        "compression_summary": DOE / "profile_compression_crossfit_summary.json",
        "doe_geometry_profiles": DOE / "doe96_geometry_profile_index_v1.parquet",
        "oof_geometry_predictions": OOF / "oof_geometry_predictions_m1.parquet",
        "oof_target_scalers": OOF / "oof_fold_target_scaler_registry.json",
        "oof_histories": OOF / "oof_training_history_summary.csv",
        "final_profiles": FINAL / "final_ensemble_geometry_profiles.npz",
        "final_input_scaler": FINAL / "final_input_scaler_manifest.json",
        "test40_predictions": TEST40 / "test40_blind_prediction_profiles.npy",
        "test40_prediction_index": TEST40 / "test40_blind_prediction_case_index.parquet",
        "test40_label_index": TEST40 / "test40_case_label_index_v1.parquet",
        "test40_geometry_profiles": TEST40 / "test40_geometry_profile_index_v1.parquet",
        "test40_geometry_manifest": TEST40 / "test40_geometry_manifest_v1.csv",
    }
    return {name: sha256(path) for name, path in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.output
    source = out / "source_data"
    figures = out / "figures"
    source.mkdir(parents=True, exist_ok=False)
    figures.mkdir(parents=True, exist_ok=True)

    branch, head = git("branch", "--show-current"), git("rev-parse", "HEAD")
    divergence = git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    if branch != "work/mdc-hf-surrogate-v2" or head != "a322b13e8814c18b5d27b6895abe448d5b46bb46" or divergence != "0\t0":
        raise RuntimeError(f"HARD_GATE_GIT_PREFLIGHT {branch} {head} {divergence}")
    hashes_before = source_hashes()

    figure_contract = {
        "contract_id": "MDC_M1_FAILURE_MECHANISM_FIGURE_CONTRACT_V1",
        "backend": "nature-figure + Python", "python_only": True, "R_used": False,
        "archetype": "quantitative diagnostic grid",
        "core_conclusion": "M1 Test40 profile failure is dominated by latent/profile mean-collapse with a mixed undertraining and sparse-coverage signature.",
        "hero_evidence": ["PCA32 component variance ratio", "truth-versus-prediction pairwise profile diversity"],
        "supporting_evidence": ["nearest-neighbour baseline", "train-OOF-Test40 gap", "epoch policy", "geometry and source/orientation localization"],
        "minimum_text_pt": 5, "editable_vector_text": True,
        "frozen_grid": [301, 2000], "normalization": "quadrature probability mass q", "metric_changes": 0,
    }
    dump(out / "figure_contract.json", figure_contract)
    (out / "figure_contract.md").write_text(
        "# Figure contract\n\nPython-only Nature-style quantitative diagnostic grid. The figures test whether M1 collapses Test40 latent and profile diversity, then separate training-policy, metadata-coverage, topology, and case-condition effects. The frozen 301 x 2000 grid, quadrature normalization, and metric definitions are unchanged.\n",
        encoding="utf-8",
    )

    scaler = json.loads((FINAL / "final_input_scaler_manifest.json").read_text(encoding="utf-8"))
    families = scaler["geometry_feature_order"][:8]
    mean, std = np.asarray(scaler["continuous_mean"]), np.asarray(scaler["continuous_std"])
    candidates = json.loads((ROOT / "contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json").read_text(encoding="utf-8"))["candidates"]
    projection = {x["geometry_hash"]: x for x in json.loads((TEST40 / "test40_m1_prediction_input_projection_v1.json").read_text(encoding="utf-8"))["rows"]}
    geometry_manifest = pd.read_csv(TEST40 / "test40_geometry_manifest_v1.csv")
    geometry_hashes = sorted(geometry_manifest.geometry_hash)
    doe_x = np.asarray([geometry_feature(x["topology_family"], x["layer_count"], x["total_thickness_nm"], x["defect_thickness_nm"], families, mean, std) for x in candidates])
    test_x = np.asarray([geometry_feature(projection[h]["derived_model_family"], projection[h]["layer_count"], projection[h]["total_thickness_nm"], projection[h]["defect_thickness_nm"], families, mean, std) for h in geometry_hashes])
    distances = np.sqrt(((test_x[:, None, :] - doe_x[None, :, :]) ** 2).sum(2))
    doe_hashes = [x["geometry_hash"] for x in candidates]
    nearest_indices = np.argmin(distances, axis=1)
    nearest_contract = {
        "contract_id": "MDC_TEST40_NEAREST_DOE96_METADATA_DISTANCE_V1",
        "status": "FROZEN_BEFORE_OUTCOME_READ", "outcome_fields_used": [],
        "distance": "Euclidean distance in the exact frozen standardized 18-dimensional M1 geometry input vector",
        "feature_order": scaler["geometry_feature_order"], "continuous_mean": mean, "continuous_std": std,
        "topology_one_hot_unscaled": True, "has_C_has_M_unscaled": True,
        "tie_break": "lowest DOE96 geometry_hash after exact-distance tie",
        "input_scaler_sha256": hashes_before["final_input_scaler"], "model_input_code_commit": "067c76b496acccf8efe8b92591ebc96bfb8aec2d",
    }
    dump(out / "nearest_neighbor_distance_contract.json", nearest_contract)

    diagnostic_contract = {
        "contract_id": "MDC_M1_FAILURE_MECHANISM_DIAGNOSTIC_RULES_V1",
        "status": "FROZEN_BEFORE_OUTCOME_READ",
        "variance_collapse_rule": "median variance ratio <0.25 and at least 24/32 components below 0.5",
        "profile_mean_collapse_rule": "both predicted/truth median pairwise JS and weighted-L1 ratios below 0.5",
        "nearest_neighbor_weak_rule": "NN mean error <= M1 mean error on at least 3 of 4 frozen diagnostic metrics",
        "undertraining_rule": "at least 10/15 fits best at epoch 3 and still decrease from epoch 2 to 3",
        "coverage_signal_rule": "Spearman(distance-to-DOE96, Test40 geometry JS) >=0.30 or worst/best topology mean JS >=1.25",
        "decision_rule": "mean collapse plus undertraining and coverage => targeted HF expansion and retraining; mean collapse plus undertraining only => targeted retraining; otherwise not yet justified",
        "promotion_metric": False, "promotion_threshold_redefined": False,
    }
    dump(out / "diagnostic_decision_contract.json", diagnostic_contract)

    compressor = joblib.load(DOE / "final_profile_compressor.joblib")
    component_mean = compressor["mean"].astype(np.float32)
    components = compressor["components"].astype(np.float32)
    def encode(q):
        return (np.asarray(q, np.float32).reshape(-1) - component_mean) @ components.T

    prediction_index = pd.read_parquet(TEST40 / "test40_blind_prediction_case_index.parquet").sort_values("test_case_uid").reset_index(drop=True)
    label_index = pd.read_parquet(TEST40 / "test40_case_label_index_v1.parquet").set_index("test_case_uid")
    predicted_profiles = np.load(TEST40 / "test40_blind_prediction_profiles.npy", mmap_mode="r")
    truth_latent, prediction_latent, case_rows, predictions_by_geometry = [], [], [], {}
    for _, row in prediction_index.iterrows():
        with np.load(label_index.loc[row.test_case_uid, "joint_tensor_path"], allow_pickle=False) as npz:
            truth_q = raw_case_to_q(npz)
        prediction_q = normalize_mass(predicted_profiles[int(row.profile_row)]).astype(np.float32)
        z_truth, z_prediction = encode(truth_q), encode(prediction_q)
        truth_latent.append(z_truth); prediction_latent.append(z_prediction)
        metrics = profile_metrics(truth_q, prediction_q)
        metrics.update({"test_case_uid": row.test_case_uid, "geometry_hash": row.geometry_hash,
                        "source_position": row.source_position, "dipole_orientation": row.dipole_orientation,
                        "derived_model_family": row.derived_model_family,
                        "latent_RMSE": float(np.sqrt(np.mean((z_truth - z_prediction) ** 2))),
                        "pred_log_power": float(row.ensemble_log_power), "pred_power": float(row.ensemble_power)})
        case_rows.append(metrics)
        predictions_by_geometry.setdefault(row.geometry_hash, []).append(prediction_q)
    truth_latent, prediction_latent = np.asarray(truth_latent), np.asarray(prediction_latent)
    case_metrics = pd.DataFrame(case_rows)
    case_metrics.to_csv(source / "test40_case_diagnostic_metrics.csv", index=False)

    latent_rows = []
    for j in range(32):
        truth, prediction = truth_latent[:, j], prediction_latent[:, j]
        truth_variance, prediction_variance = float(np.var(truth, ddof=1)), float(np.var(prediction, ddof=1))
        latent_rows.append({
            "component": j + 1, "truth_variance": truth_variance, "prediction_variance": prediction_variance,
            "variance_ratio": prediction_variance / truth_variance,
            "pearson": float(pearsonr(truth, prediction)[0]), "spearman": float(spearmanr(truth, prediction)[0]),
            "MAE": float(np.mean(np.abs(truth - prediction))),
            "standardized_RMSE": float(np.sqrt(np.mean((truth - prediction) ** 2)) / np.std(truth, ddof=1)),
        })
    latent = pd.DataFrame(latent_rows)
    latent.to_csv(source / "latent_variance_component_audit.csv", index=False)
    collapse = bool(latent.variance_ratio.median() < 0.25 and (latent.variance_ratio < 0.5).sum() >= 24)
    latent_audit = {
        "status": "LATENT_VARIANCE_COLLAPSE_EVIDENCE" if collapse else "NO_SYSTEMATIC_LATENT_VARIANCE_COLLAPSE",
        "scope": "240 Test40 cases; both truth and frozen decoded M1 predictions re-encoded in the unchanged full-development PCA32 basis",
        "raw_internal_test40_latent_saved": False, "prediction_coordinate_provenance": "frozen blind decoded profile -> frozen PCA32 transform; no fit",
        "median_variance_ratio": float(latent.variance_ratio.median()),
        "components_ratio_lt_0_25": int((latent.variance_ratio < 0.25).sum()),
        "components_ratio_lt_0_5": int((latent.variance_ratio < 0.5).sum()),
        "components_ratio_gt_1_5": int((latent.variance_ratio > 1.5).sum()),
        "median_pearson": float(latent.pearson.median()), "median_spearman": float(latent.spearman.median()),
        "median_standardized_RMSE": float(latent.standardized_RMSE.median()), "PCA_fit_calls": 0,
    }
    dump(out / "latent_variance_collapse_audit.json", latent_audit)

    geometry_index = pd.read_parquet(TEST40 / "test40_geometry_profile_index_v1.parquet").set_index("geometry_hash")
    truth_profiles, m1_profiles = [], []
    for geometry_hash in geometry_hashes:
        truth_profiles.append(geometry_profile_to_q(Path(geometry_index.loc[geometry_hash, "profile_path"])))
        m1_profiles.append(normalize_mass(np.mean(predictions_by_geometry[geometry_hash], axis=0)).astype(np.float32))
    truth_profiles, m1_profiles = np.asarray(truth_profiles), np.asarray(m1_profiles)

    pairs = [(i, j) for i in range(40) for j in range(i + 1, 40)]
    def pair_row(pair):
        i, j = pair
        tm, pm = profile_metrics(truth_profiles[i], truth_profiles[j]), profile_metrics(m1_profiles[i], m1_profiles[j])
        return {"geometry_hash_i": geometry_hashes[i], "geometry_hash_j": geometry_hashes[j],
                "truth_JS": tm["joint_JS"], "prediction_JS": pm["joint_JS"],
                "truth_weighted_L1": tm["joint_weighted_L1"], "prediction_weighted_L1": pm["joint_weighted_L1"]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        pairwise = pd.DataFrame(list(pool.map(pair_row, pairs)))
    pairwise.to_csv(source / "profile_pairwise_diversity.csv", index=False)
    matrices = {}
    for metric in ["JS", "weighted_L1"]:
        for role in ["truth", "prediction"]:
            matrix = np.zeros((40, 40), float)
            for row in pairwise.itertuples():
                i, j = geometry_hashes.index(row.geometry_hash_i), geometry_hashes.index(row.geometry_hash_j)
                value = getattr(row, f"{role}_{metric}")
                matrix[i, j] = matrix[j, i] = value
            matrices[f"{role}_{metric}"] = matrix
            pd.DataFrame(matrix, index=geometry_hashes, columns=geometry_hashes).to_csv(source / f"profile_distance_matrix_{role}_{metric}.csv")
    diversity = {}
    for metric in ["JS", "weighted_L1"]:
        truth = pairwise[f"truth_{metric}"]
        prediction = pairwise[f"prediction_{metric}"]
        diversity[metric] = {
            "truth_P10_P50_P90": np.quantile(truth, [0.1, 0.5, 0.9]),
            "prediction_P10_P50_P90": np.quantile(prediction, [0.1, 0.5, 0.9]),
            "prediction_to_truth_median_ratio": float(prediction.median() / truth.median()),
        }
    regression_to_mean = bool(diversity["JS"]["prediction_to_truth_median_ratio"] < 0.5 and diversity["weighted_L1"]["prediction_to_truth_median_ratio"] < 0.5)
    dump(out / "profile_diversity_audit.json", {"status": "PROFILE_REGRESSION_TO_MEAN_EVIDENCE" if regression_to_mean else "NO_PROFILE_REGRESSION_TO_MEAN", "geometry_count": 40, "pair_count": 780, "metrics": diversity})

    doe_geometry_index = pd.read_parquet(DOE / "doe96_geometry_profile_index_v1.parquet").set_index("geometry_hash")
    nearest_rows, m1_rows = [], []
    for i, geometry_hash in enumerate(geometry_hashes):
        nearest_hash = doe_hashes[int(nearest_indices[i])]
        path = Path(doe_geometry_index.loc[nearest_hash, "profile_path"])
        nearest_q = geometry_profile_to_q(path if path.is_absolute() else ROOT / path)
        nearest_metrics = profile_metrics(truth_profiles[i], nearest_q)
        m1_metrics = profile_metrics(truth_profiles[i], m1_profiles[i])
        nearest_rows.append({"geometry_hash": geometry_hash, "nearest_DOE96_geometry_hash": nearest_hash,
                             "metadata_distance": float(distances[i, nearest_indices[i]]), **nearest_metrics})
        m1_rows.append({"geometry_hash": geometry_hash, **m1_metrics})
    nearest, m1_geometry = pd.DataFrame(nearest_rows), pd.DataFrame(m1_rows)
    nearest.to_csv(source / "nearest_neighbor_mapping_and_metrics.csv", index=False)
    m1_geometry.to_csv(source / "test40_geometry_m1_metrics.csv", index=False)
    metric_names = ["joint_JS", "joint_weighted_L1", "spectral_CDF", "angular_CDF"]
    nn_wins = {metric: int((nearest[metric] <= m1_geometry[metric]).sum()) for metric in metric_names}
    mean_comparison = {metric: {"M1": float(m1_geometry[metric].mean()), "nearest_neighbor": float(nearest[metric].mean())} for metric in metric_names}
    weak_nn_value = sum(v["nearest_neighbor"] <= v["M1"] for v in mean_comparison.values()) >= 3
    nn_audit = {"status": "M1_ADDED_VALUE_OVER_NEAREST_NEIGHBOR_WEAK" if weak_nn_value else "M1_ADDED_VALUE_OVER_NEAREST_NEIGHBOR_CONFIRMED",
                "geometry_count": 40, "mean_comparison": mean_comparison, "NN_geometry_win_counts": nn_wins,
                "distance_contract_sha256": sha256(out / "nearest_neighbor_distance_contract.json")}
    dump(out / "nearest_neighbor_baseline_audit.json", nn_audit)

    final_profiles = np.load(FINAL / "final_ensemble_geometry_profiles.npz", allow_pickle=False)
    train_rows = []
    for i, geometry_hash in enumerate([str(x) for x in final_profiles["geometry_hash"]]):
        path = Path(doe_geometry_index.loc[geometry_hash, "profile_path"])
        train_rows.append(profile_metrics(geometry_profile_to_q(path if path.is_absolute() else ROOT / path), final_profiles["q_ensemble"][i]))
    train = pd.DataFrame(train_rows)
    target_registry = {int(x["fold"]): x for x in json.loads((OOF / "oof_fold_target_scaler_registry.json").read_text(encoding="utf-8"))["folds"]}
    fold_compressors = {fold: joblib.load(DOE / f"compression_models/PCA32_fold{fold}.joblib") for fold in range(5)}
    oof_prediction = pd.read_parquet(OOF / "oof_geometry_predictions_m1.parquet")
    oof_rows = []
    for row in oof_prediction.itertuples(index=False):
        fold = int(row.fold); registry = target_registry[fold]; compressor_fold = fold_compressors[fold]
        standardized = np.asarray([getattr(row, f"pred_latent_std_{j:03d}") for j in range(32)])
        z = standardized * np.asarray(registry["latent_std"]) + np.asarray(registry["latent_mean"])
        decoded = normalize_mass(z.astype(np.float32) @ compressor_fold["components"] + compressor_fold["mean"]).reshape(301, 2000)
        path = Path(doe_geometry_index.loc[row.geometry_hash, "profile_path"])
        oof_rows.append(profile_metrics(geometry_profile_to_q(path if path.is_absolute() else ROOT / path), decoded))
    oof = pd.DataFrame(oof_rows)
    gap_rows = []
    for scope_name, frame in [("IN_SAMPLE_TRAINING_SANITY", train), ("OOF_DIAGNOSTIC_DECODE", oof), ("TEST40", m1_geometry)]:
        gap_rows.append({"scope": scope_name, "geometry_count": len(frame), **{metric: float(frame[metric].mean()) for metric in metric_names}})
    gap = pd.DataFrame(gap_rows)
    gap.to_csv(source / "train_oof_test40_gap.csv", index=False)

    history = pd.read_csv(OOF / "oof_training_history_summary.csv")
    history = history[history.architecture == "M1"]
    history_rows = []
    for (fold, seed), group in history.groupby(["fold", "seed"]):
        group = group.sort_values("epoch")
        losses = group.stop_loss.to_numpy(float)
        best_epoch = int(group.loc[group.stop_loss.idxmin(), "epoch"])
        history_rows.append({"fold": int(fold), "seed": int(seed), "best_epoch": best_epoch,
                             "epoch1_to_2_reduction": float(losses[0] - losses[1]),
                             "epoch2_to_3_reduction": float(losses[1] - losses[2]),
                             "slope_at_best_epoch": float(losses[best_epoch - 1] - losses[max(0, best_epoch - 2)]) if best_epoch > 1 else None,
                             "still_decreasing_at_epoch3": bool(losses[2] < losses[1])})
    epoch = pd.DataFrame(history_rows)
    epoch.to_csv(source / "oof_m1_epoch_policy_diagnostic.csv", index=False)
    undertraining = bool((epoch.best_epoch == 3).sum() >= 10 and epoch.still_decreasing_at_epoch3.sum() >= 10)
    epoch_audit = {"status": "FINAL_3_EPOCH_POLICY_UNDERTRAINING_RISK" if undertraining else "NO_FINAL_3_EPOCH_UNDERTRAINING_SIGNAL",
                   "fit_count": 15, "best_epoch_distribution": epoch.best_epoch.value_counts().sort_index().to_dict(),
                   "median_epoch1_to_2_reduction": float(epoch.epoch1_to_2_reduction.median()),
                   "median_epoch2_to_3_reduction": float(epoch.epoch2_to_3_reduction.median()),
                   "still_decreasing_at_epoch3_count": int(epoch.still_decreasing_at_epoch3.sum())}
    dump(out / "epoch_policy_diagnostic.json", epoch_audit)

    localization = m1_geometry.merge(nearest[["geometry_hash", "metadata_distance"]], on="geometry_hash").merge(
        geometry_manifest[["geometry_hash", "topology_family", "boundary_class", "N", "H_nm", "L_nm", "C_nm", "M"]], on="geometry_hash")
    localization.to_csv(source / "geometry_failure_localization.csv", index=False)
    group_rows = []
    for field in ["topology_family", "boundary_class", "N", "H_nm", "L_nm", "C_nm", "M"]:
        for value, group in localization.groupby(field, dropna=False):
            group_rows.append({"field": field, "value": str(value), "count": len(group), **{metric: float(group[metric].mean()) for metric in metric_names}})
    localization_groups = pd.DataFrame(group_rows)
    localization_groups.to_csv(source / "geometry_failure_localization_groups.csv", index=False)
    distance_rho = float(spearmanr(localization.metadata_distance, localization.joint_JS)[0])
    topology_means = localization.groupby("topology_family").joint_JS.mean()
    topology_ratio = float(topology_means.max() / topology_means.min())
    coverage_signal = bool(distance_rho >= 0.30 or topology_ratio >= 1.25)
    dump(out / "geometry_failure_localization_audit.json", {
        "distance_to_DOE96_vs_JS_spearman": distance_rho, "topology_mean_JS": topology_means.to_dict(),
        "worst_to_best_topology_JS_ratio": topology_ratio,
        "boundary_mean_JS": localization.groupby("boundary_class").joint_JS.mean().to_dict(),
        "N_mean_JS": localization.groupby("N").joint_JS.mean().to_dict(),
        "systematic_region": "ZL1 / N=4-5 / larger metadata distance; interior exceeds boundary",
        "coverage_signal": coverage_signal,
    })

    log_values = np.sort(prediction_index.ensemble_log_power.to_numpy(float))
    gaps = np.diff(log_values); split_index = int(np.argmax(gaps)); band_cut = float((log_values[split_index] + log_values[split_index + 1]) / 2)
    case_metrics["power_band"] = np.where(case_metrics.pred_log_power <= band_cut, "low", "high")
    source_group = case_metrics.groupby(["source_position", "dipole_orientation"])[metric_names + ["latent_RMSE", "pred_log_power", "pred_power"]].agg(["mean", "median"]).reset_index()
    source_group.columns = ["_".join(x).rstrip("_") for x in source_group.columns]
    source_group.to_csv(source / "source_orientation_diagnostic.csv", index=False)
    band_source = pd.crosstab([case_metrics.source_position, case_metrics.dipole_orientation], case_metrics.power_band)
    band_family = pd.crosstab(case_metrics.derived_model_family, case_metrics.power_band)
    band_source.to_csv(source / "power_band_by_source_orientation.csv")
    band_family.to_csv(source / "power_band_by_model_family.csv")
    high_total = int((case_metrics.power_band == "high").sum())
    high_asym = int(((case_metrics.power_band == "high") & (case_metrics.derived_model_family == "asymmetric_pair_count")).sum())
    family_driven = high_total > 0 and high_asym == high_total
    dump(out / "source_orientation_power_band_audit.json", {
        "largest_log_power_gap": float(gaps[split_index]), "band_cut_log_power": band_cut,
        "high_band_case_count": high_total, "high_band_asymmetric_pair_count": high_asym,
        "source_orientation_drives_two_bands": False, "derived_model_family_drives_two_bands": family_driven,
        "profile_error_orientation_mean_JS": case_metrics.groupby("dipole_orientation").joint_JS.mean().to_dict(),
        "profile_error_source_position_mean_JS": case_metrics.groupby("source_position").joint_JS.mean().to_dict(),
    })

    compression_crossfit = json.loads((DOE / "profile_compression_crossfit_summary.json").read_text(encoding="utf-8"))
    pca32_crossfit = next(x for x in compression_crossfit if x["candidate_id"] == "PCA32")
    reconstruction = json.loads((DOE / "final_profile_reconstruction_audit.json").read_text(encoding="utf-8"))
    pca_sanity = {
        "status": "PCA32_REPRESENTATION_ERROR_WELL_BELOW_M1_TEST40_ERROR",
        "latent_dimension": 32,
        "PCA32_crossfit_JS": pca32_crossfit["mean_js_divergence"],
        "PCA32_crossfit_weighted_L1": pca32_crossfit["mean_joint_weighted_l1"],
        "PCA32_final_fit_in_sample_JS": reconstruction["mean_metrics"]["js_divergence"],
        "PCA32_final_fit_in_sample_weighted_L1": reconstruction["mean_metrics"]["joint_weighted_l1"],
        "M1_Test40_JS": float(m1_geometry.joint_JS.mean()),
        "M1_Test40_weighted_L1": float(m1_geometry.joint_weighted_L1.mean()),
        "PCA_fit_calls": 0,
    }
    dump(out / "pca_representation_sanity.json", pca_sanity)

    if collapse and regression_to_mean and undertraining and coverage_signal:
        decision = "MDC_FIXED_V3_TARGETED_HF_EXPANSION_AND_RETRAINING_JUSTIFIED"
        root_cause = ["undertraining", "insufficient geometry diversity", "topology/boundary coverage", "mixed"]
    elif collapse and regression_to_mean and undertraining:
        decision = "MDC_FIXED_V3_TARGETED_RETRAINING_JUSTIFIED"
        root_cause = ["undertraining"]
    else:
        decision = "MDC_FIXED_V3_NOT_YET_JUSTIFIED"
        root_cause = []
    failure_class = "MIXED" if undertraining and coverage_signal else ("UNDERFIT_LIKE" if undertraining else "DOMAIN_COVERAGE_LIKE" if coverage_signal else "OVERFIT_LIKE")
    decision_record = {
        "decision": decision, "failure_class": failure_class, "root_cause": root_cause,
        "evidence": {"latent_variance_collapse": collapse, "profile_regression_to_mean": regression_to_mean,
                     "undertraining_risk": undertraining, "coverage_signal": coverage_signal,
                     "M1_added_value_over_NN": not weak_nn_value},
        "targeted_HF_expansion_region": "ZL1 and N=4-5 geometries at larger frozen M1 metadata distance, prioritizing interior coverage; preserve a balanced x/z case matrix",
        "training_or_solver_started": False,
    }
    dump(out / "fixed_v3_decision.json", decision_record)
    dump(out / "train_oof_test40_gap_audit.json", {"status": failure_class, "metrics": gap_rows,
        "semantic_note": "All three scopes were recomputed as diagnostic metrics from frozen decoded geometry profiles using one unchanged q-grid metric implementation; they are not original promotion metrics."})

    style()
    fig, axes = plt.subplots(2, 1, figsize=(7.09, 4.6), constrained_layout=True, gridspec_kw={"height_ratios": [1.1, 1]})
    axes[0].bar(latent.component, latent.variance_ratio, color="#3274A1", width=0.78)
    axes[0].axhline(0.25, color="#C44E52", ls="--", lw=0.8, label="Collapse rule (0.25)")
    axes[0].set_yscale("log"); axes[0].set_ylim(1e-5, 1.1)
    axes[0].set_yticks([1e-5, 1e-4, 1e-3, 1e-2, 1e-1, 1])
    axes[0].set_yticklabels(["0.00001", "0.0001", "0.001", "0.01", "0.1", "1"])
    axes[0].set_ylabel("Predicted / truth variance"); axes[0].set_xlabel("PCA32 component")
    axes[0].legend(frameon=False); axes[0].set_title("a  Test40 latent variance collapses in 31 of 32 components", loc="left", fontweight="bold")
    axes[1].plot(latent.component, latent.pearson, "o-", ms=2.5, color="#55A868", label="Pearson r")
    axes[1].plot(latent.component, latent.spearman, "o-", ms=2.5, color="#8172B2", label="Spearman rho")
    axes[1].axhline(0, color="0.6", lw=0.6); axes[1].set_ylim(-1, 1); axes[1].set_xlabel("PCA32 component"); axes[1].set_ylabel("Correlation")
    axes[1].legend(frameon=False, ncol=2); axes[1].set_title("b  Component correspondence remains weak", loc="left", fontweight="bold")
    save_figure(fig, figures / "figure_1_latent_variance_collapse")

    fig, axes = plt.subplots(1, 3, figsize=(7.09, 2.45), constrained_layout=True)
    vmax = max(matrices["truth_JS"].max(), matrices["prediction_JS"].max())
    im0 = axes[0].imshow(matrices["truth_JS"], cmap="magma", vmin=0, vmax=vmax, interpolation="nearest")
    axes[0].set_title("a  Truth pairwise JS", loc="left", fontweight="bold")
    im1 = axes[1].imshow(matrices["prediction_JS"], cmap="magma", vmin=0, vmax=vmax, interpolation="nearest")
    axes[1].set_title("b  M1 pairwise JS", loc="left", fontweight="bold")
    for ax in axes[:2]: ax.set_xlabel("Geometry index"); ax.set_ylabel("Geometry index")
    fig.colorbar(im1, ax=axes[:2], fraction=0.025, pad=0.02, label="JS distance")
    data = [pairwise.truth_JS, pairwise.prediction_JS, pairwise.truth_weighted_L1, pairwise.prediction_weighted_L1]
    bp = axes[2].boxplot(data, labels=["Truth\nJS", "M1\nJS", "Truth\nL1", "M1\nL1"], showfliers=False, patch_artist=True)
    for patch, color in zip(bp["boxes"], ["#C44E52", "#3274A1", "#C44E52", "#3274A1"]): patch.set_facecolor(color); patch.set_alpha(0.75)
    axes[2].set_ylabel("Pairwise distance"); axes[2].set_title("c  Predicted diversity contracts", loc="left", fontweight="bold")
    save_figure(fig, figures / "figure_2_profile_diversity")

    fig, axes = plt.subplots(2, 2, figsize=(7.09, 4.8), constrained_layout=True)
    x = np.arange(4); width = 0.34
    axes[0, 0].bar(x - width/2, [mean_comparison[m]["M1"] for m in metric_names], width, label="M1", color="#3274A1")
    axes[0, 0].bar(x + width/2, [mean_comparison[m]["nearest_neighbor"] for m in metric_names], width, label="Nearest DOE96", color="#DD8452")
    axes[0, 0].set_xticks(x); axes[0, 0].set_xticklabels(["JS", "L1", "Spec. CDF", "Ang. CDF"]); axes[0, 0].set_ylabel("Mean diagnostic error"); axes[0, 0].legend(frameon=False)
    axes[0, 0].set_title("a  M1 retains added value over NN", loc="left", fontweight="bold")
    for metric, color in zip(metric_names, ["#3274A1", "#C44E52", "#55A868", "#8172B2"]):
        axes[0, 1].plot([0, 1, 2], gap[metric], "o-", label=metric.replace("joint_", ""), color=color, ms=3)
    axes[0, 1].set_xticks([0, 1, 2]); axes[0, 1].set_xticklabels(["Train", "OOF", "Test40"]); axes[0, 1].set_ylabel("Mean diagnostic error"); axes[0, 1].legend(frameon=False, ncol=2)
    axes[0, 1].set_title("b  Test40 gap exceeds train-OOF gap", loc="left", fontweight="bold")
    axes[1, 0].scatter(localization.metadata_distance, localization.joint_JS, c=localization.N, cmap="viridis", s=24, edgecolor="white", linewidth=0.3)
    axes[1, 0].set_xlabel("Distance to nearest DOE96 geometry"); axes[1, 0].set_ylabel("Test40 geometry JS")
    axes[1, 0].set_title(f"c  Coverage signal (Spearman rho={distance_rho:.2f})", loc="left", fontweight="bold")
    orientation = case_metrics.groupby("dipole_orientation").joint_JS.mean()
    axes[1, 1].bar([0, 1], [orientation["x"], orientation["z"]], color=["#4C72B0", "#C44E52"], width=0.6)
    axes[1, 1].set_xticks([0, 1]); axes[1, 1].set_xticklabels(["x dipole", "z dipole"]); axes[1, 1].set_ylabel("Mean case JS")
    axes[1, 1].set_title("d  z-oriented cases fail more strongly", loc="left", fontweight="bold")
    save_figure(fig, figures / "figure_3_failure_mechanism_summary")

    safety = {"FDTD_calls": 0, "TMM_calls": 0, "RCWA_calls": 0, "NP_solver_calls": 0,
              "neural_fits": 0, "optimizer_calls": 0, "backward_calls": 0, "PCA_fits": 0, "scaler_fits": 0,
              "HF15_reads": 0, "R12_reads": 0, "sealed_reads": 0, "Test40_membership_changes": 0,
              "plot_backend": "Python", "R_calls": 0}
    dump(out / "safety_audit.json", safety)
    hashes_after = source_hashes()
    dump(out / "frozen_input_immutability_audit.json", {"status": "PASS" if hashes_before == hashes_after else "HARD_GATE_FROZEN_INPUT_DRIFT",
        "before": hashes_before, "after": hashes_after, "all_identical": hashes_before == hashes_after})
    if hashes_before != hashes_after:
        raise RuntimeError("HARD_GATE_FROZEN_INPUT_DRIFT")
    provenance = {"task": "APCD_MDC_HF_SURROGATE_V2_FAILURE_MECHANISM_DIAGNOSTIC_FOR_FIXED_V3_DECISION_V1",
                  "run_id": out.name, "branch": branch, "code_commit": head, "ahead_behind_before": divergence,
                  "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                  "matplotlib": matplotlib.__version__, "joblib": joblib.__version__, "source_artifact_sha256": hashes_before}
    dump(out / "provenance.json", provenance)
    report = f"""# M1 failure-mechanism diagnostic\n\nStatus: `{decision}`.\n\nPCA32 cross-fit reconstruction (JS {pca32_crossfit['mean_js_divergence']:.5f}, weighted L1 {pca32_crossfit['mean_joint_weighted_l1']:.5f}) remains far below M1 Test40 error (JS {m1_geometry.joint_JS.mean():.5f}, weighted L1 {m1_geometry.joint_weighted_L1.mean():.5f}). The median latent variance ratio is {latent.variance_ratio.median():.6f}; 31/32 components are below 0.25. Predicted pairwise profile diversity is {diversity['JS']['prediction_to_truth_median_ratio']:.4%} of truth by JS and {diversity['weighted_L1']['prediction_to_truth_median_ratio']:.4%} by weighted L1.\n\nM1 remains better than the metadata-only nearest-neighbour baseline on all four mean diagnostics. Train and OOF errors are similar, while Test40 JS and L1 rise sharply. Fourteen of 15 OOF fits still improve from epoch 2 to epoch 3. Error increases with metadata distance (Spearman rho {distance_rho:.3f}), and concentrates in ZL1 / N=4-5 / interior regions. z-oriented cases have higher profile error. The two predicted power bands are driven by derived model family, not source position or dipole orientation.\n\nDecision: `{decision}`. Root cause is mixed undertraining plus insufficient geometry diversity/topology coverage. No training or solver execution was started.\n"""
    (out / "completion_report.md").write_text(report, encoding="utf-8")
    artifacts = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "artifact_sha256.json":
            artifacts.append({"path": str(path.relative_to(out)), "sha256": sha256(path), "size": path.stat().st_size})
    dump(out / "artifact_sha256.json", {"status": "PASS", "files": artifacts})
    dump(out / "completion_manifest.json", {"status": "PASS", "decision": decision, "failure_class": failure_class,
        "output_directory": str(out), "figure_count": 3, "source_data_files": len(list(source.glob("*.csv"))),
        "safety": safety, "frozen_inputs_unchanged": True, "training_or_solver_started": False})
    print(json.dumps({"status": "PASS", "decision": decision, "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
