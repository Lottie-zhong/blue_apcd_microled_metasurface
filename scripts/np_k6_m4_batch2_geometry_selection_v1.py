"""ZERO-SOLVER NP K6 M4 Batch2 geometry selection.

This stage reads frozen development metadata, LF predictions, M3 checkpoints, and
the development geometry manifest.  It never imports lumapi and never invokes a
solver.  The policy is materialized and hashed before candidate identities are
selected.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import re
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import torch


ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
M3 = ROOT / r"outputs\np_k6_m3_pilot_retraining_v1"
M2 = ROOT / r"outputs\np_k6_m2_active_learning_batch1_selection_v1"
FOUNDATION = ROOT / r"outputs\np_k6_ml_d0_database_foundation_v1"
TRAIN_VIEW = M3 / "development_hf_v2_training_view.csv"
OUT = ROOT / r"outputs\np_k6_m4_batch2_geometry_selection_v1"
WAVELENGTHS = list(range(445, 456))
TX_PLUS1 = 4


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def parse_diameters(gid: str) -> list[float]:
    values = [float(x) for x in re.findall(r"D(\d+)", gid)]
    if len(values) != 6:
        raise RuntimeError(f"invalid six-diameter geometry: {gid}")
    return values


def finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def load_m3_module():
    path = ROOT / r"scripts\np_k6_m3_pilot_retraining_v1.py"
    spec = importlib.util.spec_from_file_location("np_k6_m3_pilot_retraining_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M3 implementation missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def minmax_rank(values: dict[str, float], reverse: bool = False) -> dict[str, float]:
    ordered = sorted(values, key=lambda k: (values[k], k), reverse=reverse)
    n = max(1, len(ordered) - 1)
    out: dict[str, float] = {}
    for i, key in enumerate(ordered):
        out[key] = 1.0 - i / n if reverse else i / n
    return out


def percentile(values: dict[str, float], key: str) -> float:
    return float(np.percentile(np.asarray(list(values.values()), dtype=float), 50.0)) if values else 0.0


def feature_vector(gid: str) -> np.ndarray:
    d = np.asarray(parse_diameters(gid), dtype=float) / 230.0
    diffs = np.diff(d)
    gaps = np.asarray([1.0 - (d[i] + d[i + 1]) / 2.0 for i in range(5)], dtype=float)
    span = np.asarray([d[-1] - d[0], d.mean(), d.std(), np.sum(d[::2] - d[1::2])], dtype=float)
    return np.concatenate([d, diffs, gaps, span])


def pairwise_stats(ids: list[str], distances: dict[tuple[str, str], float], threshold: float) -> dict[str, Any]:
    vals = [distances[tuple(sorted((a, b)))] for a, b in combinations(ids, 2)]
    return {
        "count": len(vals),
        "min": float(min(vals)) if vals else 0.0,
        "mean": float(np.mean(vals)) if vals else 0.0,
        "max": float(max(vals)) if vals else 0.0,
        "redundant_pairs_at_or_below_threshold": int(sum(v <= threshold for v in vals)),
        "threshold": threshold,
    }


def main() -> None:
    torch.set_num_threads(1)
    OUT.mkdir(parents=True, exist_ok=True)
    m3 = load_m3_module()
    m3_state = read_json(M3 / "m3_training_state.json")
    m3_ensemble = read_json(M3 / "acquisition_ensemble_manifest.json")
    m3_validator = read_json(M3 / "m3_standalone_validator_report.json")
    if m3_validator.get("status") != "PASS" or m3_state.get("solver_run_invocations") != 0 or m3_state.get("sealed_target_reads") != 0:
        raise RuntimeError("HARD_GATE_M3_AUTHORITY_NOT_PASS_OR_ZERO_SOLVER")
    training_rows = read_csv(TRAIN_VIEW)
    training_hashes = {r["geometry_hash"] for r in training_rows}
    training_ids = {r["geometry_id"] for r in training_rows}
    if len(training_rows) != 198 or len(training_hashes) != 9 or {int(r["wavelength_nm"]) for r in training_rows} != set(WAVELENGTHS):
        raise RuntimeError("HARD_GATE_M3_TRAINING_VIEW_SPLIT_CONFLICT")
    if not all(r["training_label"].lower() == "true" and r["quality_gate_pass"].lower() == "true" and r["diagnostic_only"].lower() == "false" for r in training_rows):
        raise RuntimeError("HARD_GATE_M3_LABEL_GATE_CONFLICT")

    candidate_path = M2 / "candidate_acquisition_features.csv"
    candidate_source = read_csv(candidate_path)
    candidate_source_hash = sha256(candidate_path)
    geometry_manifest_path = FOUNDATION / "k6_hf_pilot_geometry_manifest.json"
    split_manifest_path = FOUNDATION / "k6_split_manifest.json"
    geometry_manifest = read_json(geometry_manifest_path)
    development_manifest = [r for r in geometry_manifest["rows"] if r["pilot_role"] == "development_pilot"]
    sealed_manifest = [r for r in geometry_manifest["rows"] if r["pilot_role"] == "sealed_test_pilot"]
    dev_by_hash = {r["geometry_hash"]: r for r in development_manifest}
    sealed_hashes = {r["geometry_hash"] for r in sealed_manifest}
    source_hashes = {r["geometry_hash"] for r in candidate_source}
    if len(candidate_source) != len(source_hashes) or len(development_manifest) != 48 or len(sealed_manifest) != 12:
        raise RuntimeError("HARD_GATE_DEVELOPMENT_GEOMETRY_UNIVERSE_CONFLICT")
    if source_hashes & sealed_hashes:
        raise RuntimeError("HARD_GATE_CANDIDATE_SEALED_OVERLAP")
    if not source_hashes <= set(dev_by_hash):
        raise RuntimeError("HARD_GATE_CANDIDATE_OUTSIDE_DEVELOPMENT_SPLIT")
    if not training_hashes <= set(dev_by_hash):
        raise RuntimeError("HARD_GATE_HF_OUTSIDE_DEVELOPMENT_SPLIT")
    eligible_source = [r for r in candidate_source if r["geometry_hash"] not in training_hashes and r["geometry_hash"] not in sealed_hashes]
    if len(eligible_source) != 39:
        raise RuntimeError(f"HARD_GATE_EFFECTIVE_CANDIDATE_COUNT:{len(eligible_source)}")
    effective_hashes = {r["geometry_hash"] for r in eligible_source}
    if effective_hashes & training_hashes or effective_hashes & sealed_hashes:
        raise RuntimeError("HARD_GATE_EFFECTIVE_CANDIDATE_OVERLAP")

    # Fit the same M3 node normalization on the 198-row development view.
    train_feature_rows = [{"geometry_id": r["geometry_id"], "wavelength_nm": int(r["wavelength_nm"]), "polarization": r["polarization"]} for r in training_rows]
    train_nodes = np.asarray([m3.features(r)[0] for r in train_feature_rows], dtype=np.float32)
    node_mean = train_nodes.mean((0, 1)); node_std = train_nodes.std((0, 1)); node_std[node_std < 1e-6] = 1.0
    candidate_input_rows: list[dict[str, Any]] = []
    for row in sorted(eligible_source, key=lambda x: (x["geometry_id"], x["geometry_hash"])):
        for pol in ("p", "s"):
            for wl in WAVELENGTHS:
                candidate_input_rows.append({"geometry_id": row["geometry_id"], "geometry_hash": row["geometry_hash"], "wavelength_nm": wl, "polarization": pol})
    x = np.asarray([(m3.features(r)[0] - node_mean) / node_std for r in candidate_input_rows], dtype=np.float32)
    c = np.asarray([m3.features(r)[1] for r in candidate_input_rows], dtype=np.float32)
    device = torch.device("cpu")
    model_predictions: dict[str, dict[tuple[str, int, str], dict[str, np.ndarray]]] = {"CNN": {}, "MLP": {}}
    for item in m3_ensemble["models"]:
        model_name = str(item["model"])
        cls = m3.M1.CircularCNN if model_name == "CNN" else m3.M1.SmallMLP
        model = cls()
        checkpoint = Path(item["checkpoint_path"])
        if not checkpoint.exists() or sha256(checkpoint) != item["checkpoint_sha256"]:
            raise RuntimeError(f"HARD_GATE_M3_CHECKPOINT_HASH:{checkpoint}")
        state = torch.load(checkpoint, map_location="cpu")
        model.load_state_dict(state["state_dict"])
        model.eval()
        with torch.no_grad():
            pred = model(torch.from_numpy(x), torch.from_numpy(c))
        p = {k: v.detach().cpu().numpy() for k, v in pred.items()}
        for i, row in enumerate(candidate_input_rows):
            tx = p["tx"][i]
            model_predictions[model_name][(row["geometry_id"], row["wavelength_nm"], row["polarization"])] = {
                "T": float(p["T"][i]), "R": float(p["R"][i]), "eta_plus1": float(tx[TX_PLUS1]),
                "directionality": float(tx[TX_PLUS1] / (tx.sum() + 1e-12)), "non_target_efficiency": float(tx.sum() - tx[TX_PLUS1]),
                "tx": tx.astype(float).tolist(),
            }

    # Frozen LF predictions are reused only as a physical baseline, never as HF y.
    lf_path = M2 / "cnn_ensemble_predictions.csv.gz"
    lf_rows: dict[tuple[str, int, str], dict[str, float]] = {}
    with gzip.open(lf_path, "rt", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["geometry_id"], int(row["wavelength_nm"]), row["polarization"])
            if row["geometry_hash"] in effective_hashes:
                lf_rows[key] = {k: float(row[k]) for k in ("lf_T", "lf_R", "lf_eta_plus1", "lf_directionality")}
    if len(lf_rows) != len(candidate_input_rows):
        raise RuntimeError("HARD_GATE_LF_CANDIDATE_PROFILE_INCOMPLETE")

    def group_values(gid: str, model_name: str, field: str) -> list[float]:
        return [model_predictions[model_name][(gid, wl, pol)][field] for wl in WAVELENGTHS for pol in ("p", "s")]

    def at_450(gid: str, model_name: str, field: str, pol: str) -> float:
        return model_predictions[model_name][(gid, 450, pol)][field]

    profile_rows: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for src in sorted(eligible_source, key=lambda r: (r["geometry_id"], r["geometry_hash"])):
        gid, gh = src["geometry_id"], src["geometry_hash"]
        row: dict[str, Any] = {"geometry_id": gid, "geometry_hash": gh, **{f"D{i}": parse_diameters(gid)[i] for i in range(6)}}
        for model_name in ("CNN", "MLP"):
            prefix = model_name.lower()
            for field in ("T", "R", "eta_plus1", "directionality", "non_target_efficiency"):
                vals = group_values(gid, model_name, field)
                row[f"{prefix}_{field}_mean"] = float(np.mean(vals)); row[f"{prefix}_{field}_min"] = float(np.min(vals)); row[f"{prefix}_{field}_max"] = float(np.max(vals))
                row[f"{prefix}_{field}_450_p"] = at_450(gid, model_name, field, "p"); row[f"{prefix}_{field}_450_s"] = at_450(gid, model_name, field, "s")
        for field in ("T", "R", "eta_plus1", "directionality", "non_target_efficiency"):
            deltas = [abs(model_predictions["CNN"][(gid, wl, pol)][field] - model_predictions["MLP"][(gid, wl, pol)][field]) for wl in WAVELENGTHS for pol in ("p", "s")]
            row[f"cnn_mlp_{field}_discrepancy_mean"] = float(np.mean(deltas)); row[f"cnn_mlp_{field}_discrepancy_max"] = float(np.max(deltas))
        ps = {}
        for field in ("T", "R", "eta_plus1", "directionality", "non_target_efficiency"):
            deltas = [abs(model_predictions[model_name][(gid, wl, "p")][field] - model_predictions[model_name][(gid, wl, "s")][field]) for model_name in ("CNN", "MLP") for wl in WAVELENGTHS]
            ps[field] = deltas
            row[f"predicted_ps_{field}_discrepancy_mean"] = float(np.mean(deltas)); row[f"predicted_ps_{field}_discrepancy_max"] = float(np.max(deltas))
        lfvals = [lf_rows[(gid, wl, pol)] for wl in WAVELENGTHS for pol in ("p", "s")]
        for field in ("T", "R", "eta_plus1", "directionality"):
            vals = [x[f"lf_{field}"] for x in lfvals]
            row[f"lf_{field}_mean"] = float(np.mean(vals)); row[f"lf_{field}_min"] = float(np.min(vals)); row[f"lf_{field}_max"] = float(np.max(vals))
            row[f"lf_{field}_450_p"] = lf_rows[(gid, 450, "p")][f"lf_{field}"]; row[f"lf_{field}_450_s"] = lf_rows[(gid, 450, "s")][f"lf_{field}"]
            deltas = [abs(model_predictions["CNN"][(gid, wl, pol)][field] - lf_rows[(gid, wl, pol)][f"lf_{field}"]) for wl in WAVELENGTHS for pol in ("p", "s")]
            row[f"cnn_lf_{field}_discrepancy_mean"] = float(np.mean(deltas)); row[f"cnn_lf_{field}_discrepancy_max"] = float(np.max(deltas))
        row["predicted_eta_robust_mean"] = float((row["cnn_eta_plus1_mean"] + row["mlp_eta_plus1_mean"]) / 2.0)
        row["predicted_eta_robust_min"] = float(min(row["cnn_eta_plus1_min"], row["mlp_eta_plus1_min"]))
        row["predicted_eta_robust_450_mean"] = float(np.mean([row["cnn_eta_plus1_450_p"], row["cnn_eta_plus1_450_s"], row["mlp_eta_plus1_450_p"], row["mlp_eta_plus1_450_s"]]))
        row["predicted_T_robust_min"] = float(min(row["cnn_T_min"], row["mlp_T_min"]))
        row["predicted_directionality_robust_min"] = float(min(row["cnn_directionality_min"], row["mlp_directionality_min"]))
        row["predicted_non_target_robust_max"] = float(max(row["cnn_non_target_efficiency_max"], row["mlp_non_target_efficiency_max"]))
        profile_rows.extend({"geometry_id": gid, "geometry_hash": gh, "wavelength_nm": wl, "polarization": pol, **{f"cnn_{field}": model_predictions["CNN"][(gid, wl, pol)][field] for field in ("T", "R", "eta_plus1", "directionality", "non_target_efficiency")}, **{f"mlp_{field}": model_predictions["MLP"][(gid, wl, pol)][field] for field in ("T", "R", "eta_plus1", "directionality", "non_target_efficiency")}, **lf_rows[(gid, wl, pol)]} for wl in WAVELENGTHS for pol in ("p", "s"))
        metrics.append(row)

    # Physical feature-space distances are fit on the complete 48-geometry development universe.
    dev_ids = [r["geometry_id"] for r in development_manifest]
    dev_hash_by_id = {r["geometry_id"]: r["geometry_hash"] for r in development_manifest}
    raw_vectors = np.asarray([feature_vector(g) for g in dev_ids], dtype=float)
    fmean, fstd = raw_vectors.mean(axis=0), raw_vectors.std(axis=0); fstd[fstd < 1e-9] = 1.0
    scaled = {gid: (feature_vector(gid) - fmean) / fstd for gid in dev_ids}
    dist: dict[tuple[str, str], float] = {}
    for a, b in combinations(dev_ids, 2):
        dist[tuple(sorted((a, b)))] = float(np.linalg.norm(scaled[a] - scaled[b]))
    def distance(a: str, b: str) -> float:
        return 0.0 if a == b else dist[tuple(sorted((a, b)))]
    current_hf_ids = sorted(training_ids)
    for row in metrics:
        gid = row["geometry_id"]; existing = [distance(gid, x) for x in current_hf_ids]
        row["distance_to_existing_hf9_min"] = float(min(existing)); row["distance_to_existing_hf9_mean"] = float(np.mean(existing)); row["distance_to_existing_hf9_max"] = float(max(existing))

    # Freeze policy before selecting any candidate identity.
    policy = {
        "schema_version": "np_k6_m4_selection_policy_v1",
        "version_id": "NP_K6_M4_POLICY_PHYSICS_ROBUST_ROLE_BALANCED_V1",
        "scope": "development_candidate_pool_only; zero_solver; p_s_separate",
        "primary_batch_size": 4,
        "role_order": ["exploitation_1", "exploitation_2", "coverage_exploration", "model_conflict_physics_stress"],
        "performance_weights": {"eta_robust_mean": 0.40, "eta_robust_min": 0.25, "T_robust_min": 0.15, "directionality_robust_min": 0.15, "inverse_non_target_robust_max": 0.05},
        "exploitation_2_weights": {"performance": 0.75, "distance_from_exploitation_1": 0.25},
        "coverage_weights": {"distance_to_existing_hf9_min": 0.70, "distance_to_existing_hf9_mean": 0.30},
        "conflict_weights": {"p_s_eta_discrepancy": 0.45, "cnn_mlp_eta_discrepancy": 0.30, "cnn_lf_eta_discrepancy": 0.25},
        "conflict_performance_floor": "candidate_pool_median_on_performance_and_T_and_directionality",
        "tie_break": "geometry_id_ascending_after_score_descending",
        "physical_distance_feature_space": "D0-D5, adjacent jumps, complement gaps, span/mean/std/alternating proxy; standardized on 48 development geometries",
        "pairwise_redundancy_threshold": 0.25,
        "exclusions": ["sealed_test_manifest", "all_existing_M3_HF9", "duplicate_geometry_hash", "non_development_geometry", "formal_label_or_target_values"],
        "uncertainty_role": "relative_context_only; never primary score; not calibrated probability or confidence interval",
        "source_dataset_sha256": sha256(TRAIN_VIEW),
        "candidate_pool_sha256": candidate_source_hash,
        "geometry_manifest_sha256": sha256(geometry_manifest_path),
        "split_manifest_sha256": sha256(split_manifest_path),
        "m3_ensemble_version_id": m3_ensemble["version_id"],
        "m3_checkpoint_hashes": sorted(x["checkpoint_sha256"] for x in m3_ensemble["models"]),
        "solver_run_invocations": 0,
        "sealed_target_reads": 0,
    }
    policy_canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"))
    policy_hash = hashlib.sha256(policy_canonical.encode()).hexdigest()
    policy["policy_hash"] = policy_hash
    write_json(OUT / "m4_selection_policy.json", policy)

    byid = {r["geometry_id"]: r for r in metrics}
    performance_components = {
        "eta_robust_mean": {r["geometry_id"]: r["predicted_eta_robust_mean"] for r in metrics},
        "eta_robust_min": {r["geometry_id"]: r["predicted_eta_robust_min"] for r in metrics},
        "T_robust_min": {r["geometry_id"]: r["predicted_T_robust_min"] for r in metrics},
        "directionality_robust_min": {r["geometry_id"]: r["predicted_directionality_robust_min"] for r in metrics},
        "inverse_non_target_robust_max": {r["geometry_id"]: 1.0 - r["predicted_non_target_robust_max"] for r in metrics},
    }
    ranks = {name: minmax_rank(vals) for name, vals in performance_components.items()}
    for r in metrics:
        gid = r["geometry_id"]
        r["performance_score"] = float(sum(policy["performance_weights"][name] * ranks[name][gid] for name in ranks))
        r["coverage_score"] = float(0.70 * minmax_rank({x["geometry_id"]: x["distance_to_existing_hf9_min"] for x in metrics})[gid] + 0.30 * minmax_rank({x["geometry_id"]: x["distance_to_existing_hf9_mean"] for x in metrics})[gid])
        r["conflict_score"] = float(0.45 * minmax_rank({x["geometry_id"]: x["predicted_ps_eta_plus1_discrepancy_mean"] for x in metrics})[gid] + 0.30 * minmax_rank({x["geometry_id"]: x["cnn_mlp_eta_plus1_discrepancy_mean"] for x in metrics})[gid] + 0.25 * minmax_rank({x["geometry_id"]: x["cnn_lf_eta_plus1_discrepancy_mean"] for x in metrics})[gid])

    remaining = set(byid)
    selected_roles: dict[str, str] = {}
    e1 = sorted(remaining, key=lambda g: (-byid[g]["performance_score"], g))[0]; selected_roles[e1] = "exploitation_1"; remaining.remove(e1)
    e2_scores = {g: 0.75 * byid[g]["performance_score"] + 0.25 * minmax_rank({x: distance(x, e1) for x in remaining})[g] for g in remaining}
    e2 = sorted(remaining, key=lambda g: (-e2_scores[g], g))[0]; selected_roles[e2] = "exploitation_2"; remaining.remove(e2)
    cov = sorted(remaining, key=lambda g: (-byid[g]["coverage_score"], g))[0]; selected_roles[cov] = "coverage_exploration"; remaining.remove(cov)
    perf_median = float(np.median([byid[g]["performance_score"] for g in remaining])); t_median = float(np.median([byid[g]["predicted_T_robust_min"] for g in remaining])); d_median = float(np.median([byid[g]["predicted_directionality_robust_min"] for g in remaining]))
    stress_pool = [g for g in remaining if byid[g]["performance_score"] >= perf_median and byid[g]["predicted_T_robust_min"] >= t_median and byid[g]["predicted_directionality_robust_min"] >= d_median]
    if not stress_pool: stress_pool = sorted(remaining)
    stress = sorted(stress_pool, key=lambda g: (-byid[g]["conflict_score"], g))[0]; selected_roles[stress] = "model_conflict_physics_stress"; remaining.remove(stress)
    primary_ids = [g for g, _ in sorted(selected_roles.items(), key=lambda x: ["exploitation_1", "exploitation_2", "coverage_exploration", "model_conflict_physics_stress"].index(x[1]))]

    backup_scores = {g: 0.50 * byid[g]["performance_score"] + 0.30 * byid[g]["coverage_score"] + 0.20 * byid[g]["conflict_score"] for g in remaining}
    backup_ids = sorted(remaining, key=lambda g: (-backup_scores[g], g))[:8]
    all_roles = {g: selected_roles[g] for g in selected_roles}
    for i, g in enumerate(backup_ids, 1): all_roles[g] = f"backup_rank_{i}"
    for r in metrics: r["role"] = all_roles.get(r["geometry_id"], "not_selected"); r["policy_hash"] = policy_hash
    write_csv(OUT / "m4_candidate_selection_long.csv", metrics)
    write_csv(OUT / "m4_candidate_prediction_profiles_long.csv", profile_rows)
    write_csv(OUT / "m4_geometry_feature_space.csv", [{"geometry_id": gid, "geometry_hash": dev_hash_by_id[gid], **{f"feature_{i:02d}": float(v) for i, v in enumerate(scaled[gid])}, "is_current_hf9": gid in current_hf_ids, "is_effective_candidate": gid in byid} for gid in dev_ids])

    # Coverage comparisons for current HF9, HF9+primary4, +first6, +first8.
    sets = {"current_hf9": current_hf_ids, "hf9_plus_primary4": current_hf_ids + primary_ids, "hf9_plus_first6": current_hf_ids + primary_ids + backup_ids[:2], "hf9_plus_first8": current_hf_ids + primary_ids + backup_ids[:4]}
    coverage_rows: list[dict[str, Any]] = []; coverage_json: dict[str, Any] = {}
    diameter_bins = [(100, 129), (130, 159), (160, 189), (190, 230)]; phase_values = {gid: float(np.sum(np.asarray(parse_diameters(gid), dtype=float)[::2] - np.asarray(parse_diameters(gid), dtype=float)[1::2])) for gid in dev_ids}; phase_quantiles = np.quantile(list(phase_values.values()), [0.25, 0.5, 0.75])
    for set_name, ids in sets.items():
        nearest = [min(distance(gid, x) for x in ids) for gid in dev_ids]
        pair = pairwise_stats(ids[len(current_hf_ids):] if set_name != "current_hf9" else [], dist, policy["pairwise_redundancy_threshold"])
        hist = {f"diameter_bin_{lo}_{hi}": int(sum(lo <= d <= hi for gid in ids for d in parse_diameters(gid))) for lo, hi in diameter_bins}
        hist.update({"gap_lt15": int(sum(gap < 15 for gid in ids for gap in np.diff(parse_diameters(gid)))), "gap_15_29": int(sum(15 <= gap < 30 for gid in ids for gap in np.diff(parse_diameters(gid)))), "gap_ge30": int(sum(gap >= 30 for gid in ids for gap in np.diff(parse_diameters(gid))))})
        hist.update({"phase_proxy_q1": int(sum(phase_values[gid] <= phase_quantiles[0] for gid in ids)), "phase_proxy_q2": int(sum(phase_quantiles[0] < phase_values[gid] <= phase_quantiles[1] for gid in ids)), "phase_proxy_q3": int(sum(phase_quantiles[1] < phase_values[gid] <= phase_quantiles[2] for gid in ids)), "phase_proxy_q4": int(sum(phase_values[gid] > phase_quantiles[2] for gid in ids))})
        summary = {"geometry_count": len(ids), "nearest_hf_distance_min": float(min(nearest)), "nearest_hf_distance_median": float(np.median(nearest)), "nearest_hf_distance_mean": float(np.mean(nearest)), "nearest_hf_distance_p90": float(np.percentile(nearest, 90)), "nearest_hf_distance_max": float(max(nearest)), "pairwise": pair, "coverage_histogram": hist, "all_inside_development_bounds": True}
        coverage_json[set_name] = summary
        coverage_rows.append({"set_name": set_name, **{k: v for k, v in summary.items() if not isinstance(v, (dict, list))}})
    before = coverage_json["current_hf9"]
    for name in ("hf9_plus_primary4", "hf9_plus_first6", "hf9_plus_first8"):
        for key in ("nearest_hf_distance_mean", "nearest_hf_distance_p90", "nearest_hf_distance_max"):
            coverage_json[name][f"improvement_{key}"] = float(before[key] - coverage_json[name][key])
    write_json(OUT / "m4_geometry_coverage_audit.json", {"schema_version": "np_k6_m4_geometry_coverage_audit_v1", "feature_space": policy["physical_distance_feature_space"], "development_geometry_count": len(dev_ids), "current_hf9_count": len(current_hf_ids), "comparisons": coverage_json, "solver_run_invocations": 0, "sealed_target_reads": 0})
    write_csv(OUT / "m4_geometry_coverage_summary.csv", coverage_rows)

    runtime = read_json(M3 / "batch1_runtime_cost_audit.json"); wall = runtime["total_wall_clock"]; engine = runtime["engine_runtime"]
    cost_rows = []
    for label, count in (("primary4", 4), ("first6", 6), ("first8", 8)):
        cases = count * 2
        cost_rows.append({"batch": label, "logical_geometries": count, "paired_ps_case_count": cases, "clean_physical_solver_count": cases, "wall_clock_median_hours": float(cases * wall["median_s"] / 3600.0), "wall_clock_p90_hours": float(cases * wall["p90_s"] / 3600.0), "engine_median_hours": float(cases * engine["median_s"] / 3600.0), "engine_p90_hours": float(cases * engine["p90_s"] / 3600.0), "replacement_or_infrastructure_risk": "historical Batch1 had 1 lost execution and 1 controlled replacement; not counted as normal clean demand"})
    cost_package = {"schema_version": "np_k6_m4_solver_cost_decision_package_v1", "source_runtime_audit": str(M3 / "batch1_runtime_cost_audit.json"), "source_runtime_audit_sha256": sha256(M3 / "batch1_runtime_cost_audit.json"), "batches": cost_rows, "solver_authorization": False, "solver_run_invocations": 0, "sealed_target_reads": 0}
    write_json(OUT / "m4_solver_cost_decision_package.json", cost_package)

    selection = {"schema_version": "np_k6_m4_selection_manifest_v1", "status": "NP_K6_M4_BATCH2_GEOMETRY_SELECTION_READY_FOR_SOLVER_AUTHORIZATION", "recommended_batch_size": 4, "policy_hash": policy_hash, "primary4": [{"geometry_id": g, "geometry_hash": dev_hash_by_id[g], "role": selected_roles[g]} for g in primary_ids], "backups_ranked": [{"rank": i + 1, "geometry_id": g, "geometry_hash": dev_hash_by_id[g], "role": f"backup_rank_{i + 1}"} for i, g in enumerate(backup_ids)], "first6_additions": [{"geometry_id": g, "geometry_hash": dev_hash_by_id[g], "role": f"backup_rank_{i + 1}"} for i, g in enumerate(backup_ids[:2])], "first8_additions": [{"geometry_id": g, "geometry_hash": dev_hash_by_id[g], "role": f"backup_rank_{i + 3}"} for i, g in enumerate(backup_ids[2:4])], "development_candidate_source_count": len(candidate_source), "effective_candidate_count": len(eligible_source), "existing_hf9_count": len(current_hf_ids), "sealed_count": len(sealed_hashes), "solver_run_invocations": 0, "sealed_target_reads": 0}
    write_json(OUT / "m4_selection_manifest.json", selection)
    authority = {"schema_version": "np_k6_m4_authority_audit_v1", "m3_training_view": str(TRAIN_VIEW), "m3_training_view_sha256": sha256(TRAIN_VIEW), "m3_validator": str(M3 / "m3_standalone_validator_report.json"), "m3_validator_status": m3_validator.get("status"), "m3_ensemble_manifest": str(M3 / "acquisition_ensemble_manifest.json"), "m3_ensemble_version_id": m3_ensemble.get("version_id"), "candidate_pool_source": str(candidate_path), "candidate_pool_sha256": candidate_source_hash, "geometry_manifest": str(geometry_manifest_path), "geometry_manifest_sha256": sha256(geometry_manifest_path), "split_manifest": str(split_manifest_path), "split_manifest_sha256": sha256(split_manifest_path), "development_universe_count": len(development_manifest), "sealed_universe_count": len(sealed_manifest), "candidate_pool_count": len(candidate_source), "effective_candidate_count": len(eligible_source), "existing_hf9_count": len(current_hf_ids), "candidate_existing_hf_overlap_count": len(source_hashes & training_hashes), "candidate_sealed_overlap_count": len(source_hashes & sealed_hashes), "effective_existing_hf_overlap_count": len(effective_hashes & training_hashes), "effective_sealed_overlap_count": len(effective_hashes & sealed_hashes), "duplicate_candidate_hashes": len(candidate_source) - len(source_hashes), "formal_label_values_read": False, "sealed_target_reads": 0, "solver_run_invocations": 0, "m3_checkpoint_hashes": policy["m3_checkpoint_hashes"]}
    write_json(OUT / "m4_authority_audit.json", authority)
    write_json(OUT / "m4_solver_zero_audit.json", {"schema_version": "np_k6_m4_solver_zero_audit_v1", "fdtd_run_invocations": 0, "lumapi_run_invocations": 0, "sealed_target_reads": 0, "batch2_started": False, "lumerical_imported": False})

    checks = {
        "development_universe_48": len(development_manifest) == 48,
        "candidate_pool_45": len(candidate_source) == 45,
        "effective_candidates_39": len(eligible_source) == 39,
        "existing_hf9_excluded": not effective_hashes & training_hashes,
        "sealed_overlap_zero": not effective_hashes & sealed_hashes,
        "duplicate_candidate_hash_zero": len(candidate_source) == len(source_hashes),
        "primary4_unique": len(primary_ids) == 4 and len(set(primary_ids)) == 4,
        "backups_at_least4": len(backup_ids) >= 4 and not set(backup_ids[:4]) & set(primary_ids),
        "d0_d5_order_preserved": all(parse_diameters(g) == [float(byid[g][f"D{i}"]) for i in range(6)] for g in byid),
        "policy_hash_present": len(policy_hash) == 64,
        "m3_model_ids_complete": len(m3_ensemble.get("models", [])) == 6 and all(x.get("solver_calls") == 0 for x in m3_ensemble.get("models", [])),
        "predictions_complete": len(profile_rows) == len(eligible_source) * 22,
        "prediction_numeric_finite": all(finite(v) for r in metrics for k, v in r.items() if isinstance(v, (int, float))),
        "solver_zero": True,
        "sealed_zero": True,
    }
    write_json(OUT / "m4_validator_report.json", {"schema_version": "np_k6_m4_geometry_selection_validator_v1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "errors": [k for k, v in checks.items() if not v], "policy_hash": policy_hash, "solver_run_invocations": 0, "sealed_target_reads": 0})
    write_json(OUT / "m4_provenance_manifest.json", {"schema_version": "np_k6_m4_provenance_manifest_v1", "authority": authority, "selection_policy_hash": policy_hash, "selection_manifest_sha256": sha256(OUT / "m4_selection_manifest.json"), "solver_run_invocations": 0, "sealed_target_reads": 0})
    # Build a lightweight checksum manifest; runtime M3 checkpoints and no arrays are included.
    files = []
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name != "m4_checksum_manifest.json":
            files.append({"path": p.name, "sha256": sha256(p), "size_bytes": p.stat().st_size, "git_candidate": p.stat().st_size < 2_000_000})
    write_json(OUT / "m4_checksum_manifest.json", {"schema_version": "np_k6_m4_checksum_manifest_v1", "files": files, "runtime_checkpoints_excluded": True, "solver_run_invocations": 0, "sealed_target_reads": 0})
    write_json(OUT / "m4_decision.json", {"schema_version": "np_k6_m4_decision_v1", "status": selection["status"], "recommendation": "authorize_primary4_only_after_user_approval", "pure_uncertainty_primary_score": False, "primary_roles_fixed": True, "p_s_equivalence_claim": False, "solver_started": False, "policy_hash": policy_hash})
    print(json.dumps({"status": selection["status"], "policy_hash": policy_hash, "primary4": selection["primary4"], "backups": selection["backups_ranked"], "effective_candidate_count": len(eligible_source), "solver_run_invocations": 0, "sealed_target_reads": 0}, indent=2))


if __name__ == "__main__":
    main()
