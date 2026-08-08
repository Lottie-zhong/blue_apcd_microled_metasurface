"""NP K6 M2 active-learning Batch1 selector.

Acquisition-only stage: consume the authoritative 66-row HF pilot dataset,
load the existing CNN committee, train only an acquisition-only MLP committee,
score the unlabeled development pool, and freeze six geometries plus twelve
future task manifests.  Never invoke FDTD or access sealed labels.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

ROOT = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1")
os.chdir(ROOT)
DATASET = ROOT / "outputs" / "np_k6_hf_pilot_dataset_v1"
M1_OUT = ROOT / "outputs" / "np_k6_m1_pilot_training_v1"
GEOM_MANIFEST = ROOT / "outputs" / "np_k6_ml_d0_database_foundation_v1" / "k6_hf_pilot_geometry_manifest.json"
SPLIT_MANIFEST = ROOT / "outputs" / "np_k6_ml_d0_database_foundation_v1" / "k6_split_manifest.json"
OUT = ROOT / "outputs" / "np_k6_m2_active_learning_batch1_selection_v1"
M1_SCRIPT = ROOT / "scripts" / "np_k6_m1_pilot_training_v1.py"
CONFIG_PATH = ROOT / "configs" / "np_k6_forward_surrogate_pilot_v1.json"
WAVELENGTHS = list(range(445, 456))
POLARIZATIONS = ["p", "s"]
SEEDS = [17, 29, 43]
GENERATOR = "NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2"
STACK = "NP_K6_INDEPENDENT_STACK_PILOT_V1"
TX_ORDER_IDS = [-3, -2, -1, 0, 1, 2, 3]
RX_ORDER_IDS = list(range(-5, 6))
ETA_INDEX = TX_ORDER_IDS.index(1)
EXPECTED_HEAD = "35b7bfe"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def csv_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def csv_read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_diameters(geometry_id: str) -> list[float]:
    values = [float(v) for v in re.findall(r"D(\d+)", geometry_id)]
    if len(values) != 6:
        raise RuntimeError(f"six diameters required: {geometry_id}")
    return values


def load_m1_module():
    spec = importlib.util.spec_from_file_location("np_k6_m1_training", M1_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("M1 script import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_checkpoint(torch, model_cls, path: Path, device, hidden: int | None = None):
    model = model_cls(hidden=hidden) if hidden is not None else model_cls()
    try:
        payload = torch.load(path, map_location=device, weights_only=False)
    except TypeError:
        payload = torch.load(path, map_location=device)
    state = payload["state_dict"] if isinstance(payload, dict) and "state_dict" in payload else payload
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


def robust_summary(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med)))
    scale = max(1.4826 * mad, 1e-12)
    return {"median": med, "mad": mad, "scale": scale, "min": float(values.min()), "max": float(values.max())}


def robust_percentile(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    out = np.zeros(len(values), dtype=float)
    if len(values) > 1:
        out[order] = np.arange(len(values), dtype=float) / float(len(values) - 1)
    return out


def collect_lf_authority() -> dict[str, dict[str, Any]]:
    root = ROOT / "outputs" / "np_k6_p1d2_sixbin_exhaustive_ranking_27point_v1"
    found: dict[str, dict[str, Any]] = {}
    if not root.exists():
        return found
    for path in sorted(root.glob("*")):
        if path.suffix.lower() not in {".json", ".csv"} or path.stat().st_size > 50_000_000:
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8")) if path.suffix.lower() == ".json" else csv_read(path)
        except Exception:
            continue
        stack = [obj]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                gid, gh = item.get("geometry_id"), item.get("geometry_hash")
                if gid or gh:
                    rec = {
                        "source_file": str(path),
                        "rank": item.get("rank", item.get("global_rank", item.get("candidate_rank"))),
                        "passing": item.get("passing", item.get("passes", item.get("legacy_gate_pass"))),
                        "pareto": item.get("pareto", item.get("pareto_front")),
                        "raw_status": item.get("status", item.get("classification", item.get("release_status"))),
                    }
                    if gid: found[str(gid)] = rec
                    if gh: found[str(gh)] = rec
                stack.extend(v for v in item.values() if isinstance(v, (dict, list)))
            elif isinstance(item, list):
                stack.extend(item)
    return found


def scan_legacy_ledger() -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    by_hash: dict[str, list[dict[str, Any]]] = {}
    all_entries: list[dict[str, Any]] = []
    for path in (ROOT / "outputs").rglob("attempt_ledger.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        gh = str(obj.get("geometry_hash", ""))
        gid = str(obj.get("geometry_id", ""))
        if not gh and not gid:
            continue
        entry = {
            "path": str(path),
            "case_id": obj.get("case_id"),
            "geometry_hash": gh,
            "geometry_id": gid,
            "entered": bool(obj.get("entered") or obj.get("solver_entered")),
            "run_invocation_count": int(obj.get("run_invocation_count", 0) or 0),
            "aborted": bool(obj.get("aborted") or obj.get("aborted_scope_correction")),
            "status": obj.get("status", obj.get("classification")),
        }
        all_entries.append(entry)
        if gh:
            by_hash.setdefault(gh, []).append(entry)
    return by_hash, all_entries


def main() -> None:
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output directory: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    import torch

    m1 = load_m1_module()
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    data = m1.AnchorDataset()
    if len(data.rows) != 66:
        raise RuntimeError("formal HF row count is not 66")
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        raise RuntimeError("HARD_GATE_M2_CUDA_UNAVAILABLE")
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if git_head != EXPECTED_HEAD and not git_head.startswith(EXPECTED_HEAD):
        raise RuntimeError(f"unexpected HEAD for M2 reconciliation: {git_head}")

    geom_obj = json.loads(GEOM_MANIFEST.read_text(encoding="utf-8"))
    split_obj = json.loads(SPLIT_MANIFEST.read_text(encoding="utf-8"))
    geom_rows = geom_obj["rows"]
    formal_hashes = sorted({r["geometry_hash"] for r in data.rows})
    formal_ids = sorted({r["geometry_id"] for r in data.rows})
    legacy_by_hash, legacy_entries = scan_legacy_ledger()
    sealed = [r for r in geom_rows if r.get("pilot_role") == "sealed_test_pilot"]
    dev = [r for r in geom_rows if r.get("pilot_role") == "development_pilot"]
    eligible, excluded = [], []
    for row in dev:
        gh, gid = str(row["geometry_hash"]), str(row["geometry_id"])
        reasons = []
        if gh in formal_hashes or gid in formal_ids:
            reasons.append("already_formal_hf_labeled")
        histories = legacy_by_hash.get(gh, [])
        consumed = [x for x in histories if x["entered"] or x["run_invocation_count"] > 0 or x["aborted"]]
        if consumed:
            reasons.append("entered_or_aborted_historical_identity")
        if reasons:
            excluded.append({"geometry_id": gid, "geometry_hash": gh, "reasons": reasons, "legacy_records": histories})
        else:
            d = parse_diameters(gid)
            if sorted(d) != d or any(v < 100 or v > 230 or (v - 100) % 5 != 0 for v in d):
                excluded.append({"geometry_id": gid, "geometry_hash": gh, "reasons": ["geometry_contract_invalid"]})
            else:
                eligible.append({"geometry_id": gid, "geometry_hash": gh, "pilot_index": row.get("pilot_index"), "diameters": d, "legacy_unentered_task_count": len(histories), "legacy_records": histories})
    if not eligible:
        raise RuntimeError("no eligible development candidates")
    existing = np.asarray([parse_diameters(g) for g in formal_ids], dtype=float)
    cand_vec = np.asarray([x["diameters"] for x in eligible], dtype=float)
    norm_vec = (cand_vec - 100.0) / 130.0
    existing_norm = (existing - 100.0) / 130.0
    distance = np.linalg.norm(norm_vec[:, None, :] - norm_vec[None, :, :], axis=2)
    existing_dist = np.linalg.norm(norm_vec[:, None, :] - existing_norm[None, :, :], axis=2)
    pairwise = distance[np.triu_indices(len(eligible), 1)]
    near_threshold = float(np.percentile(pairwise, 25)) if len(pairwise) else 0.0
    novelty_rows = []
    formal_keys = [f"{d[0]:.0f}_{d[1]:.0f}_{d[2]:.0f}_{d[3]:.0f}_{d[4]:.0f}_{d[5]:.0f}" for d in existing]
    for i, c in enumerate(eligible):
        dists = existing_dist[i]
        diam = np.asarray(c["diameters"], dtype=float)
        gaps = np.diff(diam)
        c.update({
            "novelty_min_distance": float(dists.min()),
            "novelty_mean_distance": float(dists.mean()),
            "novelty_max_distance": float(dists.max()),
            "diameter_span_nm": float(diam.max() - diam.min()),
            "adjacent_jump_min_nm": float(gaps.min()),
            "adjacent_jump_mean_nm": float(gaps.mean()),
            "adjacent_jump_max_nm": float(gaps.max()),
            "gap_proxy_min_nm": float(290.0 - np.max((diam[:-1] + diam[1:]) / 2.0)),
            "design_boundary_distance_nm": float(np.min(np.minimum(diam - 100.0, 230.0 - diam))),
            "design_boundary_distance_normalized": float(np.min(np.minimum(diam - 100.0, 230.0 - diam)) / 130.0),
        })
        novelty_rows.append({"geometry_id": c["geometry_id"], "geometry_hash": c["geometry_hash"], **{f"distance_to_formal_{j}": float(dists[j]) for j in range(len(formal_ids))}, "min_distance": float(dists.min()), "mean_distance": float(dists.mean()), "max_distance": float(dists.max())})
    json_write(OUT / "geometry_distance_matrix_summary.json", {
        "schema_version": "np_k6_m2_geometry_distance_summary_v1",
        "eligible_count": len(eligible), "normalization": "diameter_nm_minus_100_divided_by_130",
        "pairwise_count": int(len(pairwise)), "pairwise_min": float(pairwise.min()) if len(pairwise) else 0.0,
        "pairwise_median": float(np.median(pairwise)) if len(pairwise) else 0.0, "pairwise_max": float(pairwise.max()) if len(pairwise) else 0.0,
        "near_duplicate_threshold_25th_percentile": near_threshold, "existing_hf_geometry_hashes": formal_hashes, "existing_hf_geometry_ids": formal_ids,
    })
    csv_write(OUT / "geometry_novelty_metrics.csv", novelty_rows)

    all_nodes = np.asarray([m1.AnchorDataset.features(data, r)[0] for r in data.rows], dtype=np.float32)
    model_mean, model_std = all_nodes.mean((0, 1)), all_nodes.std((0, 1))
    model_std[model_std < 1e-6] = 1.0
    context_rows, xs, cs = [], [], []
    stub = m1.AnchorDataset.__new__(m1.AnchorDataset)
    for c in eligible:
        for wl in WAVELENGTHS:
            for pol in POLARIZATIONS:
                r = {"geometry_id": c["geometry_id"], "geometry_hash": c["geometry_hash"], "wavelength_nm": wl, "polarization": pol}
                context_rows.append(r)
                node, ctx = stub.features(r)
                xs.append((node - model_mean) / model_std)
                cs.append(ctx)
    x_np, c_np = np.asarray(xs, dtype=np.float32), np.asarray(cs, dtype=np.float32)

    cnn_manifest = json.loads((M1_OUT / "acquisition_ensemble_manifest.json").read_text(encoding="utf-8"))
    cnn_models = []
    hidden = int(cfg.get("model", {}).get("hidden", 32))
    for item in cnn_manifest["models"]:
        path = Path(item["checkpoint_path"])
        if not path.exists() or sha256(path) != item["checkpoint_sha256"]:
            raise RuntimeError(f"CNN checkpoint provenance mismatch: {path}")
        cnn_models.append((item["seed"], load_checkpoint(torch, m1.CircularCNN, path, device, hidden)))
    mlp_runtime = OUT / "runtime_checkpoints"
    mlp_runtime.mkdir(parents=True, exist_ok=True)
    full_arrays = m1.tensor_targets(data.rows, model_mean, model_std)
    mlp_models, mlp_manifest_models = [], []
    for seed in SEEDS:
        model, history, best_epoch, best_monitor = m1.train_one(m1.SmallMLP(), full_arrays, None, seed, device, cfg)
        path = mlp_runtime / f"mlp_acquisition_seed_{seed}.pt"
        torch.save({"state_dict": model.state_dict(), "seed": seed, "epoch": best_epoch, "config": cfg, "purpose": "ACQUISITION_ONLY", "solver_calls": 0, "training_label_source": "66_formal_hf_observations"}, path)
        model.eval()
        mlp_models.append((seed, model))
        mlp_manifest_models.append({"seed": seed, "epoch": best_epoch, "best_monitor_loss": best_monitor, "checkpoint_path": str(path), "checkpoint_sha256": sha256(path), "purpose": "ACQUISITION_ONLY", "training_rows": 66, "training_geometry_hashes": formal_hashes, "dataset_manifest_sha256": sha256(DATASET / "dataset_checksum_manifest.json"), "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(), "device": str(device), "sealed_access": 0, "solver_calls": 0})
    json_write(OUT / "mlp_ensemble_manifest.json", {"schema_version": "np_k6_m2_mlp_acquisition_ensemble_v1", "purpose": "ACQUISITION_ONLY", "seed_count": 3, "checkpoint_count": 3, "models": mlp_manifest_models, "training_rows": 66, "training_geometry_hashes": formal_hashes, "dataset_manifest_sha256": sha256(DATASET / "dataset_checksum_manifest.json"), "sealed_access": 0, "solver_calls": 0, "final_performance_model": False})
    json_write(OUT / "cnn_ensemble_provenance.json", {"schema_version": "np_k6_m2_cnn_ensemble_provenance_v1", "source_manifest": str(M1_OUT / "acquisition_ensemble_manifest.json"), "source_manifest_sha256": sha256(M1_OUT / "acquisition_ensemble_manifest.json"), "purpose": "ACQUISITION_ONLY", "seed_count": 3, "checkpoint_count": 3, "models": cnn_manifest["models"], "training_geometry_hashes": formal_hashes, "dataset_manifest_sha256": sha256(DATASET / "dataset_checksum_manifest.json"), "sealed_access": 0, "solver_calls": 0, "m1_retrained": False})

    def infer(models):
        out = []
        with torch.no_grad():
            xt, ct = torch.from_numpy(x_np).to(device, non_blocking=True), torch.from_numpy(c_np).to(device, non_blocking=True)
            for seed, model in models:
                p = model(xt, ct)
                out.append((seed, {k: v.detach().cpu().numpy() for k, v in p.items()}))
        return out

    cnn_preds, mlp_preds = infer(cnn_models), infer(mlp_models)
    fake_lf = [{"geometry_id": r["geometry_id"], "wavelength_nm": r["wavelength_nm"], "polarization": r["polarization"]} for r in context_rows]
    lf_pred = m1.lf_baseline(fake_lf, data.rows)
    T_lf, R_lf = np.asarray(lf_pred["T"], float), np.asarray(lf_pred["R"], float)
    tx_lf, rx_lf = np.asarray(lf_pred["tx"], float), np.asarray(lf_pred["rx"], float)
    eta_lf, dir_lf = tx_lf[:, ETA_INDEX], tx_lf[:, ETA_INDEX] / (T_lf + 1e-12)

    def stack(preds, key):
        return np.stack([p[key] for _, p in preds], axis=0)
    cnn_T, cnn_R, cnn_tx, cnn_rx = stack(cnn_preds, "T"), stack(cnn_preds, "R"), stack(cnn_preds, "tx"), stack(cnn_preds, "rx")
    mlp_T, mlp_R, mlp_tx, mlp_rx = stack(mlp_preds, "T"), stack(mlp_preds, "R"), stack(mlp_preds, "tx"), stack(mlp_preds, "rx")
    cnn_eta, mlp_eta = cnn_tx[:, :, ETA_INDEX], mlp_tx[:, :, ETA_INDEX]
    ctx_rows = []
    for i, r in enumerate(context_rows):
        rec = dict(r)
        rec.update({"lf_T": float(T_lf[i]), "lf_R": float(R_lf[i]), "lf_eta_plus1": float(eta_lf[i]), "lf_directionality": float(dir_lf[i])})
        for seed, p in cnn_preds:
            rec.update({f"cnn_{seed}_T": float(p["T"][i]), f"cnn_{seed}_R": float(p["R"][i]), f"cnn_{seed}_eta_plus1": float(p["tx"][i, ETA_INDEX]), f"cnn_{seed}_directionality": float(p["tx"][i, ETA_INDEX] / (p["T"][i] + 1e-12))})
        for seed, p in mlp_preds:
            rec.update({f"mlp_{seed}_T": float(p["T"][i]), f"mlp_{seed}_R": float(p["R"][i]), f"mlp_{seed}_eta_plus1": float(p["tx"][i, ETA_INDEX]), f"mlp_{seed}_directionality": float(p["tx"][i, ETA_INDEX] / (p["T"][i] + 1e-12))})
        ceta, meta = cnn_eta[:, i], mlp_eta[:, i]
        rec.update({"cnn_mean_T": float(cnn_T[:, i].mean()), "cnn_mean_R": float(cnn_R[:, i].mean()), "cnn_mean_eta_plus1": float(ceta.mean()), "cnn_mean_directionality": float(ceta.mean() / (cnn_T[:, i].mean() + 1e-12)), "cnn_std_T": float(cnn_T[:, i].std()), "cnn_std_R": float(cnn_R[:, i].std()), "cnn_std_eta_plus1": float(ceta.std()), "mlp_mean_T": float(mlp_T[:, i].mean()), "mlp_mean_R": float(mlp_R[:, i].mean()), "mlp_mean_eta_plus1": float(meta.mean()), "mlp_mean_directionality": float(meta.mean() / (mlp_T[:, i].mean() + 1e-12)), "mlp_std_T": float(mlp_T[:, i].std()), "mlp_std_R": float(mlp_R[:, i].std()), "cnn_mlp_disagreement_T": float(abs(cnn_T[:, i].mean() - mlp_T[:, i].mean())), "cnn_mlp_disagreement_R": float(abs(cnn_R[:, i].mean() - mlp_R[:, i].mean())), "cnn_mlp_disagreement_eta_plus1": float(abs(ceta.mean() - meta.mean())), "cnn_mlp_disagreement_all_order": float(np.mean(np.abs(np.concatenate([cnn_tx[:, i].mean(0)-mlp_tx[:, i].mean(0), cnn_rx[:, i].mean(0)-mlp_rx[:, i].mean(0)])))), "cnn_lf_eta_residual": float(abs(ceta.mean() - eta_lf[i])), "cnn_lf_spectrum_residual": float(np.mean(np.abs(cnn_tx[:, i].mean(0)-tx_lf[i]))), "cnn_lf_order_distribution_residual": float(np.mean(np.abs(np.concatenate([cnn_tx[:, i].mean(0)-tx_lf[i], cnn_rx[:, i].mean(0)-rx_lf[i]]))))})
        ctx_rows.append(rec)
    with gzip.open(OUT / "cnn_ensemble_predictions.csv.gz", "wt", newline="", encoding="utf-8") as f:
        fields = list(dict.fromkeys(k for r in ctx_rows for k in r))
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(ctx_rows)

    lf_auth = collect_lf_authority()
    summary_rows = []
    for c in eligible:
        idx = np.asarray([i for i, r in enumerate(context_rows) if r["geometry_hash"] == c["geometry_hash"]])
        ceta, meta, cT, cR, mT, mR = cnn_eta[:, idx], mlp_eta[:, idx], cnn_T[:, idx], cnn_R[:, idx], mlp_T[:, idx], mlp_R[:, idx]
        ctx_c_tx, ctx_c_rx, ctx_m_tx, ctx_m_rx = cnn_tx[:, idx], cnn_rx[:, idx], mlp_tx[:, idx], mlp_rx[:, idx]
        rec = dict(c)
        rec.update({
            "cnn_eta_uncertainty_mean": float(ceta.std(0).mean()), "cnn_eta_uncertainty_max": float(ceta.std(0).max()), "cnn_T_uncertainty_mean": float(cT.std(0).mean()), "cnn_R_uncertainty_mean": float(cR.std(0).mean()), "cnn_all_order_uncertainty_mean": float(np.concatenate([ctx_c_tx, ctx_c_rx], axis=2).std(0).mean()),
            "mlp_eta_uncertainty_mean": float(meta.std(0).mean()), "mlp_eta_uncertainty_max": float(meta.std(0).max()), "mlp_T_uncertainty_mean": float(mT.std(0).mean()), "mlp_R_uncertainty_mean": float(mR.std(0).mean()),
            "cnn_mlp_eta_disagreement_mean": float(np.mean(np.abs(ceta.mean(0)-meta.mean(0)))), "cnn_mlp_eta_disagreement_max": float(np.max(np.abs(ceta.mean(0)-meta.mean(0)))), "cnn_mlp_T_disagreement_mean": float(np.mean(np.abs(cT.mean(0)-mT.mean(0)))), "cnn_mlp_R_disagreement_mean": float(np.mean(np.abs(cR.mean(0)-mR.mean(0)))), "cnn_mlp_all_order_disagreement_mean": float(np.mean(np.abs(np.concatenate([ctx_c_tx.mean(0)-ctx_m_tx.mean(0), ctx_c_rx.mean(0)-ctx_m_rx.mean(0)], axis=1)))),
            "hf_model_lf_eta_residual_mean": float(np.mean(np.abs(ceta.mean(0)-eta_lf[idx]))), "hf_model_lf_eta_residual_max": float(np.max(np.abs(ceta.mean(0)-eta_lf[idx]))), "hf_model_lf_spectrum_residual_mean": float(np.mean(np.abs(ctx_c_tx.mean(0)-tx_lf[idx]))), "hf_model_lf_order_distribution_residual_mean": float(np.mean(np.abs(np.concatenate([ctx_c_tx.mean(0)-tx_lf[idx], ctx_c_rx.mean(0)-rx_lf[idx]], axis=1)))),
            "predicted_eta_plus1_mean": float(ceta.mean()), "predicted_eta_plus1_min": float(ceta.mean(0).min()), "predicted_eta_plus1_max": float(ceta.mean(0).max()),
        })
        p450 = next(j for j, r in enumerate(context_rows) if r["geometry_hash"] == c["geometry_hash"] and r["wavelength_nm"] == 450 and r["polarization"] == "p")
        s450 = next(j for j, r in enumerate(context_rows) if r["geometry_hash"] == c["geometry_hash"] and r["wavelength_nm"] == 450 and r["polarization"] == "s")
        rec.update({"predicted_eta_plus1_450_p": float(cnn_eta[:, p450].mean()), "predicted_eta_plus1_450_s": float(cnn_eta[:, s450].mean()), "predicted_directionality_mean": float(np.mean(ceta/(cT+1e-12))), "predicted_directionality_450_p": float(cnn_eta[:, p450].mean()/(cnn_T[:, p450].mean()+1e-12)), "predicted_directionality_450_s": float(cnn_eta[:, s450].mean()/(cnn_T[:, s450].mean()+1e-12))})
        lf_rec = lf_auth.get(c["geometry_hash"], lf_auth.get(c["geometry_id"], {}))
        rec.update({"lf_rank": lf_rec.get("rank"), "lf_passing_status": lf_rec.get("passing", "not_in_authoritative_passing_set"), "lf_pareto_status": lf_rec.get("pareto", "not_in_authoritative_pareto_set"), "lf_authority_source": lf_rec.get("source_file")})
        summary_rows.append(rec)
    metric_keys = ["cnn_eta_uncertainty_mean","cnn_eta_uncertainty_max","cnn_T_uncertainty_mean","cnn_R_uncertainty_mean","cnn_all_order_uncertainty_mean","mlp_eta_uncertainty_mean","mlp_eta_uncertainty_max","mlp_T_uncertainty_mean","mlp_R_uncertainty_mean","cnn_mlp_eta_disagreement_mean","cnn_mlp_eta_disagreement_max","cnn_mlp_T_disagreement_mean","cnn_mlp_R_disagreement_mean","cnn_mlp_all_order_disagreement_mean","hf_model_lf_eta_residual_mean","hf_model_lf_spectrum_residual_mean","hf_model_lf_order_distribution_residual_mean","predicted_eta_plus1_mean","predicted_eta_plus1_min","predicted_eta_plus1_max","novelty_min_distance","novelty_mean_distance","novelty_max_distance"]
    normalization = {"schema_version":"np_k6_m2_eligible_pool_robust_normalization_v1","fit_scope":"eligible_development_pool_only","sealed_stats_used":False,"formal_hf_targets_used":False,"metrics":{}}
    for key in metric_keys:
        vals = np.asarray([float(r[key]) for r in summary_rows])
        normalization["metrics"][key] = robust_summary(vals)
        for r, pct in zip(summary_rows, robust_percentile(vals)):
            r[key + "_percentile"] = float(pct)
    json_write(OUT / "acquisition_normalization.json", normalization)
    for r in summary_rows:
        r["cnn_uncertainty_score"] = float(np.mean([r["cnn_eta_uncertainty_mean_percentile"],r["cnn_T_uncertainty_mean_percentile"],r["cnn_R_uncertainty_mean_percentile"],r["cnn_all_order_uncertainty_mean_percentile"]]))
        r["committee_uncertainty_score"] = float(np.mean([r["cnn_uncertainty_score"],r["mlp_eta_uncertainty_mean_percentile"],r["mlp_T_uncertainty_mean_percentile"],r["mlp_R_uncertainty_mean_percentile"]]))
        r["disagreement_score"] = float(np.mean([r["cnn_mlp_eta_disagreement_mean_percentile"],r["cnn_mlp_T_disagreement_mean_percentile"],r["cnn_mlp_R_disagreement_mean_percentile"],r["cnn_mlp_all_order_disagreement_mean_percentile"]]))
        r["performance_score"] = float(r["predicted_eta_plus1_mean_percentile"])
    csv_write(OUT / "candidate_acquisition_features.csv", summary_rows)
    by_hash = {r["geometry_hash"]: r for r in summary_rows}
    def rank_for(key): return [r["geometry_hash"] for r in sorted(summary_rows, key=lambda r: (-float(r[key]), r["geometry_hash"]))]
    rankings = {"U1_cnn_uncertainty":rank_for("cnn_uncertainty_score"),"U2_committee_uncertainty":rank_for("committee_uncertainty_score"),"D1_novelty":rank_for("novelty_min_distance"),"X1_disagreement":rank_for("disagreement_score"),"P1_performance":rank_for("performance_score")}
    ids = [r["geometry_hash"] for r in summary_rows]
    id_to_i = {gh:i for i,gh in enumerate(ids)}
    selected, slots = [], []
    def near_selected(gh): return any(float(distance[id_to_i[gh],id_to_i[s["geometry_hash"]]]) <= near_threshold for s in selected)
    def choose(slot, ranking, metric, avoid_near=True):
        chosen = None; fallback = False
        for gh in ranking:
            if gh in {s["geometry_hash"] for s in selected}: continue
            if avoid_near and near_selected(gh): continue
            chosen = by_hash[gh]; break
        if chosen is None:
            fallback = True
            for gh in ranking:
                if gh not in {s["geometry_hash"] for s in selected}:
                    chosen = by_hash[gh]; break
        if chosen is None: raise RuntimeError(f"cannot fill {slot}")
        rationale = {"slot":slot,"metric":metric,"rank_position":ranking.index(chosen["geometry_hash"])+1,"fallback_near_duplicate_relaxed":fallback}
        chosen = dict(chosen); chosen["_rationale"] = rationale; selected.append(chosen); slots.append(rationale)
    choose("U1", rankings["U1_cnn_uncertainty"], "highest CNN epistemic uncertainty", avoid_near=False)
    choose("U2", rankings["U2_committee_uncertainty"], "highest committee uncertainty after U1 near-duplicate exclusion")
    choose("D1", rankings["D1_novelty"], "farthest from current three formal HF geometries")
    d2_rank = sorted(ids, key=lambda gh: (-min(float(existing_dist[id_to_i[gh]].min()), min([float(distance[id_to_i[gh],id_to_i[s["geometry_hash"]]]) for s in selected] or [float("inf")])), gh))
    choose("D2", d2_rank, "maximin coverage against existing HF and selected set")
    choose("X1", rankings["X1_disagreement"], "highest CNN/MLP eta/order disagreement")
    choose("P1", rankings["P1_performance"], "highest predicted eta(+1), excluding nearby selected candidates")
    if len(selected) != 6 or len({r["geometry_hash"] for r in selected}) != 6: raise RuntimeError("selection cardinality/uniqueness failure")
    selection_rows=[]
    for slot,r in zip(["U1","U2","D1","D2","X1","P1"],selected):
        selection_rows.append({"slot":slot,"geometry_id":r["geometry_id"],"geometry_hash":r["geometry_hash"],**{f"D{i}":int(round(r["diameters"][i])) for i in range(6)},"cnn_uncertainty_percentile":float(r["cnn_uncertainty_score"]),"committee_uncertainty_percentile":float(r["committee_uncertainty_score"]),"novelty_percentile":float(r["novelty_min_distance_percentile"]),"cnn_mlp_disagreement_percentile":float(r["disagreement_score"]),"predicted_eta_plus1":float(r["predicted_eta_plus1_mean"]),"predicted_eta_plus1_min":float(r["predicted_eta_plus1_min"]),"predicted_eta_plus1_max":float(r["predicted_eta_plus1_max"]),"predicted_eta_plus1_450_p":float(r["predicted_eta_plus1_450_p"]),"predicted_eta_plus1_450_s":float(r["predicted_eta_plus1_450_s"]),"lf_rank":r["lf_rank"],"lf_passing_status":r["lf_passing_status"],"lf_pareto_status":r["lf_pareto_status"],"rationale":json.dumps(r["_rationale"],sort_keys=True)})
    csv_write(OUT / "batch1_selected_geometries.csv", selection_rows)
    json_write(OUT / "slot_rankings.json", {"schema_version":"np_k6_m2_slot_rankings_v1","near_duplicate_threshold":near_threshold,"selection_order":["U1","U2","D1","D2","X1","P1"],"rankings":rankings,"D2_dynamic_ranking":d2_rank,"slots":slots})
    stability={"schema_version":"np_k6_m2_selection_stability_v1","top_n":10,"cnn_seed_top10":{},"selected_percentiles":{},"top10_overlap":{}}
    seed_rankings={}
    for seed,p in cnn_preds:
        vals=np.asarray([float(np.mean(p["tx"][np.asarray([j for j,rr in enumerate(context_rows) if rr["geometry_hash"]==gh]),ETA_INDEX])) for gh in ids])
        seed_rankings[f"cnn_seed_{seed}"]=[ids[i] for i in np.argsort(-vals,kind="mergesort")]
        stability["cnn_seed_top10"][f"seed_{seed}"]=seed_rankings[f"cnn_seed_{seed}"][:10]
    for name,vals in [("cnn_ensemble_eta",np.asarray([r["predicted_eta_plus1_mean"] for r in summary_rows])),("mlp_ensemble_eta",np.asarray([float(mlp_eta[:,np.asarray([j for j,rr in enumerate(context_rows) if rr["geometry_hash"]==gh])].mean()) for gh in ids])),("committee_disagreement",np.asarray([r["cnn_mlp_eta_disagreement_mean"] for r in summary_rows]))]:
        seed_rankings[name]=[ids[i] for i in np.argsort(-vals,kind="mergesort")]
        stability[f"{name}_top10"]=seed_rankings[name][:10]
    names=list(seed_rankings)
    for i,a in enumerate(names):
        for b in names[i+1:]: stability["top10_overlap"][f"{a}__{b}"]=len(set(seed_rankings[a][:10])&set(seed_rankings[b][:10]))
    for r in selection_rows:
        base=by_hash[r["geometry_hash"]]
        stability["selected_percentiles"][r["slot"]]={"geometry_hash":r["geometry_hash"],"cnn_uncertainty":r["cnn_uncertainty_percentile"],"novelty":r["novelty_percentile"],"disagreement":r["cnn_mlp_disagreement_percentile"],"performance":float(base["performance_score"]),"lf_rank":r["lf_rank"]}
    json_write(OUT / "selection_stability_audit.json", stability)
    json_write(OUT / "batch1_selection_rationale.json", {"schema_version":"np_k6_m2_batch1_selection_rationale_v1","selection_order":["U1","U2","D1","D2","X1","P1"],"selected_geometry_count":6,"representation_gate":{"uncertainty_slots":2,"diversity_slots":2,"disagreement_slots":1,"performance_slots":1},"near_duplicate_threshold":near_threshold,"slots":slots,"no_top6_single_score":True,"no_all_lf_passing_or_pareto_only":True,"selection_is_acquisition_only":True,"sealed_access":0,"solver_calls":0})
    tasks=[]
    for i,r in enumerate(selection_rows,1):
        for pol in ["p","s"]:
            tasks.append({"task_id":f"NP_K6_M2_BATCH1_G{i:02d}_{pol.upper()}","batch_id":"NP_K6_M2_BATCH1","slot":r["slot"],"geometry_id":r["geometry_id"],"geometry_hash":r["geometry_hash"],"diameters_nm":[r[f"D{j}"] for j in range(6)],"polarization":pol,"u_x":0.0,"k_y":0.0,"wavelengths_nm":WAVELENGTHS,"wavelength_count":11,"generator_id":GENERATOR,"interface_stack_id":STACK,"maximum_simulation_time_s":3e-12,"auto_shutoff_threshold":1e-5,"entered":False,"solver_entered":False,"run_invocation_count":0,"solver_authorized":False,"training_label":False,"candidate_performance_label":False,"development":True,"sealed":False,"diagnostic_only":False,"active_learning_batch":1,"planned_only":True})
    old=ROOT/"outputs"/"np_k6_ml_d0_database_foundation_v1"/"k6_hf_task_ledger.json"
    json_write(OUT/"batch1_task_manifest.json",{"schema_version":"np_k6_m2_batch1_task_manifest_v1","batch_id":"NP_K6_M2_BATCH1","selected_geometry_count":6,"task_count":12,"expected_new_observations":132,"tasks":tasks,"solver_calls":0,"sealed_access":0,"legacy_task_ledger_reconciliation":{"path":str(old),"sha256":sha256(old) if old.exists() else None,"old_identity_untouched":True,"selected_geometry_legacy_unentered_counts":{r["geometry_hash"]:int(by_hash[r["geometry_hash"]]["legacy_unentered_task_count"]) for r in selection_rows}},"current_formal_observations":66,"expected_after_success":198})
    json_write(OUT/"candidate_pool_audit.json",{"schema_version":"np_k6_m2_candidate_pool_audit_v1","geometry_manifest_path":str(GEOM_MANIFEST),"geometry_manifest_sha256":sha256(GEOM_MANIFEST),"split_manifest_path":str(SPLIT_MANIFEST),"split_manifest_sha256":sha256(SPLIT_MANIFEST),"development_total":len(dev),"sealed_total":len(sealed),"already_formal_hf_labeled":len(formal_hashes),"eligible_unlabeled_development":len(eligible),"excluded_rows":excluded,"sealed_excluded_count":len(sealed),"sealed_access":0,"entered_or_aborted_historical_exclusion_count":sum("entered_or_aborted_historical_identity" in x["reasons"] for x in excluded),"duplicate_geometry_hashes":len(eligible)-len({x["geometry_hash"] for x in eligible}),"legacy_task_ledger_entries_scanned":len(legacy_entries),"no_p0_rerun":True,"no_m1_retraining":True})
    json_write(OUT/"solver_budget_audit.json",{"schema_version":"np_k6_m2_solver_budget_audit_v1","stage":"M2_ACTIVE_LEARNING_BATCH1_SELECTION","solver_calls":0,"new_fsp_count":0,"entered_count":0,"sealed_access":0,"p0_rerun":False,"m1_retrained":False,"planned_tasks":12,"all_planned_tasks_entered":False})
    json_write(OUT/"provenance_audit.json",{"schema_version":"np_k6_m2_provenance_audit_v1","head":git_head,"expected_head":EXPECTED_HEAD,"p0_dataset_manifest_sha256":sha256(DATASET/"dataset_checksum_manifest.json"),"m1_acquisition_manifest_sha256":sha256(M1_OUT/"acquisition_ensemble_manifest.json"),"geometry_manifest_sha256":sha256(GEOM_MANIFEST),"split_manifest_sha256":sha256(SPLIT_MANIFEST),"sealed_access":0,"solver_calls":0,"m1_retrained":False,"source_labels":"66 formal FDTD observations only"})
    json_write(OUT/"state_reconciliation.json",{"schema_version":"np_k6_m2_state_reconciliation_v1","head":git_head,"expected_head":EXPECTED_HEAD,"P0_REVALIDATED_AT_HEAD_35B7BFE":git_head.startswith(EXPECTED_HEAD),"P0_STAGE_LOCAL_STATUS":"NP_K6_HF_P0_ANCHOR_DATASET_COMPLETE_PILOT_TRAINING_READY","P0_FORMAL_HF_GEOMETRIES":3,"P0_FORMAL_HF_OBSERVATIONS":66,"P0_SOLVER_CALLS":6,"M1_STAGE_LOCAL_STATUS":"NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY","M1_real_training_started":True,"M1_cuda_training_completed":True,"M1_checkpoint_count":3,"M1_checkpoint_purpose":"ACQUISITION_ONLY","M1_sealed_access":0,"M1_solver_calls":0,"global_authoritative_state":"NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTED_FDTD_AUTHORIZATION_PENDING","M2_solver_calls":0,"M2_sealed_access":0})
    all_files=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name!="checksum_manifest.json" and p.suffix.lower() not in {".pt",".npz",".h5",".hdf5"}:
            all_files.append({"path":p.name,"sha256":sha256(p),"size_bytes":p.stat().st_size})
    json_write(OUT/"checksum_manifest.json",{"schema_version":"np_k6_m2_batch1_selection_v1","files":all_files,"runtime_checkpoints_excluded_from_git":True,"solver_calls":0,"sealed_access":0})
    report=ROOT/"docs"/"np_k6_m2_active_learning_batch1_selection_v1.md"
    lines=["# NP K6 M2 active-learning Batch1 selection v1","","Status: NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTED_FDTD_AUTHORIZATION_PENDING.","","Acquisition-only development selection. No FDTD solver was called, no sealed labels were accessed, and no M1 retraining was performed.","",f"- P0: 3 formal geometries / 66 observations.","- M1: 3 CNN acquisition checkpoints (seeds 17/29/43); MLP committee is acquisition-only.",f"- Development pool: {len(dev)} total, {len(formal_hashes)} formal HF excluded, {len(sealed)} sealed excluded, {len(eligible)} eligible unlabeled.",f"- Batch1: exactly 6 geometries and 12 planned p/s tasks; expected observations after successful future acquisition: 198.","","## Selected slots",""]
    for r in selection_rows:
        lines.append(f"- {r['slot']}: {r['geometry_id']}; D={r['D0']},{r['D1']},{r['D2']},{r['D3']},{r['D4']},{r['D5']}; predicted eta(+1)={r['predicted_eta_plus1']:.6f}; rationale={r['rationale']}")
    lines += ["","## Gates","","- All selected tasks have entered=false, run_invocation_count=0, solver_authorized=false, development=true, sealed=false.","- Contexts are p/s × 445–455 nm, u_x=0, k_y=0, 3 ps maximum simulation time, auto-shutoff 1e-5.","- Selection order is U1 -> U2 -> D1 -> D2 -> X1 -> P1; near-duplicate threshold is the eligible-pool pairwise-distance 25th percentile.","","Next action: wait for explicit authorization NP_K6_M2_BATCH1_FDTD_ACQUISITION."]
    report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"status":"NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTED_FDTD_AUTHORIZATION_PENDING","eligible":len(eligible),"selected":selection_rows,"tasks":len(tasks),"solver_calls":0,"sealed_access":0,"output":str(OUT)},indent=2,default=str))


if __name__ == "__main__":
    main()
