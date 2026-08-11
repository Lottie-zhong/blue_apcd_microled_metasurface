"""Formal MDC HF surrogate V3 OOF runner.

This runner is intentionally outcome-blind: it materializes the frozen 45-fit
matrix, uses only DOE96 + reclassified V2 Test40 + completed AL64 profiles,
and never opens V3-Test40/HF15/R12 truth paths.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

# RCP_LCP ships Intel MKL alongside the PyTorch runtime.  This is a process
# compatibility setting only; package/environment versions remain frozen.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd

try:
    import torch
    from torch import nn
except Exception as exc:  # pragma: no cover
    raise RuntimeError("RCP_LCP torch is required") from exc

torch.set_num_threads(1)


REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
READINESS = REPO / "scripts" / "mdc_hf_surrogate_v3_training_readiness_v1.py"
PROMOTION = REPO / "scripts" / "mdc_hf_surrogate_v3_oof_promotion_policy_v1.py"
GEOM = CONTRACT / "v3_development_geometry_manifest_v1.csv"
CASES = CONTRACT / "v3_development_case_matrix_v1.csv"
AL_GEOM = CONTRACT / "v3_al64_geometry_manifest_v1.csv"
AL_CASES = CONTRACT / "v3_al64_future_case_matrix_v1.csv"
MODEL_CONTRACT = CONTRACT / "v3_model_candidate_contract_v1.json"
TRAIN_CONTRACT = CONTRACT / "v3_training_contract_v1.json"
LOSS_CONTRACT = CONTRACT / "v3_profile_only_loss_contract_v1.json"
TEST40_LOCK = CONTRACT / "v3_test40_manifest_lock_v1.json"
TEST40_OVERLAP = CONTRACT / "v3_test40_overlap_audit_v1.json"

DOE_INDEX = REPO / "outputs" / "mdc_hf_surrogate_v2_doe96_joint_profile_database_v1" / "20260803T_doe96_joint_profile_6b6d7e2" / "doe96_case_label_index_v1.parquet"
V2_INDEX = REPO / "outputs" / "mdc_hf_surrogate_v2_test40_selection_conflict_resolution_v1" / "20260808T_test40_selection_conflict_resolution_489b54e" / "test40_case_label_index_v1.parquet"
AL_INDEX = REPO / "outputs" / "mdc_hf_surrogate_v3_al64_real_2d_fdtd_v1" / "20260810T1355Z_0bfbbd5_targeted_al64_real_2d_fdtd_v3" / "al64_case_label_index.csv"
AL_COMPLETION = AL_INDEX.parent / "al64_completion_manifest.json"

NATIVE_SHAPE = (301, 2000)
PROFILE_DIM = NATIVE_SHAPE[0] * NATIVE_SHAPE[1]
SEEDS = (20260810, 20260811, 20260812)
FOLDS = tuple(range(5))
INNER_SEED = 20260813
FIT_CAP = 45
MIN_EPOCHS = 50
MAX_EPOCHS = 400
PATIENCE = 50
MIN_DELTA = 1e-6
LR = 3e-4
MIN_LR = 1e-6
WARMUP = 10
GRAD_CLIP = 1.0
BATCH_GEOMETRY_GROUPS = 16
PROFILE_WEIGHTS = {"profile": 0.4117647058823529, "JS": 0.23529411764705882, "spectral_CDF": 0.17647058823529413, "angular_CDF": 0.17647058823529413}
TOPOLOGIES = ("Explicit", "ZL1", "ZL2")
PARENT_FAMILY_FEATURES = ("asymmetric_pair_count", "dual_defect", "grouped_chirped", "hybrid_periodic_aperiodic", "locally_aperiodic", "off_center_defect", "symmetric_periodic", "termination_reversed")
NUMERIC_FEATURES = ("N", "H_nm", "L_nm", "C_nm", "M", "defect_thickness_nm", "total_thickness_nm", "layer_count")
FEATURE_ORDER = PARENT_FAMILY_FEATURES + NUMERIC_FEATURES + ("has_C", "has_M", "source_top", "source_centroid", "source_bottom", "dipole_x", "dipole_z")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha_obj(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def stable_key(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32 - 1))
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def trap_weights(x: np.ndarray) -> np.ndarray:
    out = np.empty_like(x, dtype=np.float64)
    out[1:-1] = (x[2:] - x[:-2]) / 2.0
    out[0] = (x[1] - x[0]) / 2.0
    out[-1] = (x[-1] - x[-2]) / 2.0
    return out


def q_from_npz(path: Path, wavelength: np.ndarray, angle_rad: np.ndarray) -> np.ndarray:
    if not path.is_absolute():
        path = REPO / path
    with np.load(path, allow_pickle=False) as z:
        lam = np.asarray(z["wavelength_nm"], dtype=np.float64)
        ang = np.asarray(z["angle_deg"], dtype=np.float64)
        raw = np.asarray(z["joint_raw"], dtype=np.float64)
    if raw.shape != NATIVE_SHAPE or not np.array_equal(lam, wavelength) or not np.array_equal(np.deg2rad(ang), angle_rad):
        raise RuntimeError("HARD_GATE_NATIVE_GRID_OR_SHAPE_MISMATCH")
    if not np.isfinite(raw).all() or (raw < 0).any():
        raise RuntimeError("HARD_GATE_PROFILE_NONFINITE_OR_NEGATIVE")
    weights = trap_weights(wavelength)[:, None] * trap_weights(angle_rad)[None, :]
    integral = float(np.sum(raw * weights))
    if not math.isfinite(integral) or integral <= 0:
        raise RuntimeError("HARD_GATE_PROFILE_NORMALIZATION")
    q = (raw / integral) * weights
    q = np.maximum(q, 0.0)
    q /= max(float(q.sum()), 1e-30)
    return q.astype(np.float32, copy=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    geom = pd.concat([pd.read_csv(GEOM), pd.read_csv(AL_GEOM)], ignore_index=True).copy()
    geom["geometry_hash"] = geom.geometry_hash.astype(str)
    if len(geom) != 200 or geom.geometry_hash.nunique() != 200:
        raise RuntimeError("HARD_GATE_DEVELOPMENT_GEOMETRY_MEMBERSHIP")
    rows: list[dict[str, Any]] = []
    doe = pd.read_parquet(DOE_INDEX)
    for r in doe.to_dict("records"):
        rows.append({"role": "DOE96_FORMAL_DEVELOPMENT", "case_uid": str(r["case_hash"]), "geometry_hash": str(r["geometry_hash"]), "source_position": str(r["source_position"]), "dipole_orientation": str(r["dipole_orientation"]), "raw_path": str(r["joint_tensor_path"]), "raw_sha256": str(r["joint_tensor_sha256"])})
    v2 = pd.read_parquet(V2_INDEX)
    for r in v2.to_dict("records"):
        rows.append({"role": "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3", "case_uid": str(r["test_case_uid"]), "geometry_hash": str(r["geometry_hash"]), "source_position": str(r["source_position"]), "dipole_orientation": str(r["dipole_orientation"]), "raw_path": str(r["joint_tensor_path"]), "raw_sha256": str(r["joint_tensor_sha256"])})
    al = pd.read_csv(AL_INDEX)
    for r in al.to_dict("records"):
        if str(r.get("solver_status")) != "COMPLETE" or str(r.get("accepted")) not in {"True", "1", "1.0"}:
            raise RuntimeError("HARD_GATE_AL64_CASE_NOT_ACCEPTED")
        rows.append({"role": "AL64_FORMAL_DEVELOPMENT", "case_uid": str(r["case_uid"]), "geometry_hash": str(r["geometry_hash"]), "source_position": str(r["source_position"]), "dipole_orientation": str(r["dipole_orientation"]), "raw_path": str(r["raw_npz_path"]), "raw_sha256": str(r["raw_npz_sha256"])})
    cases = pd.DataFrame(rows)
    expected_positions = {"top", "centroid", "bottom"}
    expected_orientations = {"x", "z"}
    if len(cases) != 1200 or cases.case_uid.nunique() != 1200 or cases.groupby("geometry_hash").size().nunique() != 1 or cases.groupby("geometry_hash").size().iloc[0] != 6:
        raise RuntimeError("HARD_GATE_DEVELOPMENT_CASE_MEMBERSHIP")
    if set(cases.geometry_hash) != set(geom.geometry_hash):
        raise RuntimeError("HARD_GATE_GEOMETRY_CASE_JOIN")
    if set(cases.source_position) != expected_positions or set(cases.dipole_orientation) != expected_orientations:
        raise RuntimeError("HARD_GATE_SIX_CASE_SIGNATURE")
    if not AL_COMPLETION.exists() or read_json(AL_COMPLETION).get("status") != "PASS":
        raise RuntimeError("HARD_GATE_AL64_COMPLETION_MANIFEST")
    # The only V3-Test40 reads allowed are metadata identity/overlap contracts.
    lock = read_json(TEST40_LOCK)
    overlap = read_json(TEST40_OVERLAP)
    if lock.get("labels_generated") is not False or lock.get("labels_read") != 0 or overlap.get("status") != "PASS":
        raise RuntimeError("HARD_GATE_V3_TEST40_SEALED")
    first = Path(cases.iloc[0].raw_path)
    with np.load(first, allow_pickle=False) as z:
        wavelength = np.asarray(z["wavelength_nm"], dtype=np.float64)
        angle_rad = np.deg2rad(np.asarray(z["angle_deg"], dtype=np.float64))
    if tuple(wavelength.shape) != (301,) or tuple(angle_rad.shape) != (2000,):
        raise RuntimeError("HARD_GATE_GRID")
    return geom, cases, wavelength, angle_rad, np.asarray(cases.index, dtype=np.int64)


def feature_rows(geom: pd.DataFrame, cases: pd.DataFrame) -> np.ndarray:
    gmap = geom.set_index("geometry_hash")
    out = np.zeros((len(cases), len(FEATURE_ORDER)), dtype=np.float32)
    for i, r in enumerate(cases.itertuples(index=False)):
        g = gmap.loc[r.geometry_hash]
        topo = str(g.topology_family)
        for j, name in enumerate(PARENT_FAMILY_FEATURES):
            out[i, j] = float(topo == name)
        for j, name in enumerate(NUMERIC_FEATURES, start=len(PARENT_FAMILY_FEATURES)):
            value = pd.to_numeric(pd.Series([g.get(name, np.nan)]), errors="coerce").iloc[0]
            out[i, j] = 0.0 if pd.isna(value) else float(value)
        out[i, len(PARENT_FAMILY_FEATURES) + 8] = float(pd.notna(pd.to_numeric(pd.Series([g.get("C_nm", np.nan)]), errors="coerce").iloc[0]))
        out[i, len(PARENT_FAMILY_FEATURES) + 9] = float(pd.notna(pd.to_numeric(pd.Series([g.get("M", np.nan)]), errors="coerce").iloc[0]))
        base = len(PARENT_FAMILY_FEATURES) + 10
        out[i, base : base + 3] = [float(r.source_position == x) for x in ("top", "centroid", "bottom")]
        out[i, base + 3 : base + 5] = [float(r.dipole_orientation == x) for x in ("x", "z")]
    return out


def fit_pca(q: np.ndarray, train_indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X = np.asarray(q[train_indices], dtype=np.float32)
    mean = X.mean(axis=0, dtype=np.float64).astype(np.float32)
    C = X - mean
    gram = np.asarray(C @ C.T, dtype=np.float64)
    vals, vecs = np.linalg.eigh(gram)
    ix = np.argsort(vals)[::-1][:32]
    vals = np.maximum(vals[ix], 1e-18)
    comp = np.asarray((vecs[:, ix].T @ C) / np.sqrt(vals)[:, None], dtype=np.float32)
    return mean, comp


def transform_pca(q: np.ndarray, mean: np.ndarray, comp: np.ndarray) -> np.ndarray:
    out = np.empty((len(q), comp.shape[0]), dtype=np.float32)
    for start in range(0, len(q), 16):
        out[start : start + 16] = (np.asarray(q[start : start + 16], dtype=np.float32) - mean) @ comp.T
    return out


class ResidualBlock(nn.Module):
    def __init__(self, width: int, dropout: float):
        super().__init__()
        self.fc1 = nn.Linear(width, width)
        self.fc2 = nn.Linear(width, width)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        y = torch.relu(self.fc1(x))
        y = self.dropout(y)
        return torch.relu(x + self.fc2(y))


class ProfileOnlyModel(nn.Module):
    def __init__(self, cfg: Mapping[str, Any]):
        super().__init__()
        self.input_stem = nn.Linear(int(cfg["input_width"]), int(cfg["residual_width"]))
        self.blocks = nn.ModuleList([ResidualBlock(int(cfg["residual_width"]), float(cfg["dropout"])) for _ in range(int(cfg["residual_blocks"]))])
        self.latent_hidden = nn.Linear(int(cfg["residual_width"]), int(cfg["latent_width"]))
        self.latent_head = nn.Linear(int(cfg["latent_width"]), int(cfg["profile_head_width"]))
        self.power_head = None
        self.auxiliary_head = None

    def forward(self, x):
        y = torch.relu(self.input_stem(x))
        for block in self.blocks:
            y = block(y)
        y = torch.relu(self.latent_hidden(y))
        return {"latent": self.latent_head(y)}


def profile_loss_torch(prediction: torch.Tensor, target: torch.Tensor) -> dict[str, torch.Tensor]:
    pred = torch.clamp(prediction, min=0.0)
    truth = torch.clamp(target, min=0.0)
    pred = pred / torch.clamp(pred.sum(dim=(-2, -1), keepdim=True), min=1e-12)
    truth = truth / torch.clamp(truth.sum(dim=(-2, -1), keepdim=True), min=1e-12)
    log_pred = torch.log(torch.clamp(pred, min=1e-12))
    log_truth = torch.log(torch.clamp(truth, min=1e-12))
    profile = torch.nn.functional.smooth_l1_loss(log_pred, log_truth, reduction="mean")
    midpoint = 0.5 * (pred + truth)
    js = 0.5 * torch.sum(pred * torch.log(torch.clamp(pred / torch.clamp(midpoint, min=1e-12), min=1e-12)) + truth * torch.log(torch.clamp(truth / torch.clamp(midpoint, min=1e-12), min=1e-12)), dim=(-2, -1)).mean()
    spec_p = pred.sum(dim=-1); spec_t = truth.sum(dim=-1)
    ang_p = pred.sum(dim=-2); ang_t = truth.sum(dim=-2)
    spec_p = spec_p / torch.clamp(spec_p.sum(dim=-1, keepdim=True), min=1e-12); spec_t = spec_t / torch.clamp(spec_t.sum(dim=-1, keepdim=True), min=1e-12)
    ang_p = ang_p / torch.clamp(ang_p.sum(dim=-1, keepdim=True), min=1e-12); ang_t = ang_t / torch.clamp(ang_t.sum(dim=-1, keepdim=True), min=1e-12)
    spectral = torch.abs(torch.cumsum(spec_p, dim=-1) - torch.cumsum(spec_t, dim=-1)).mean()
    angular = torch.abs(torch.cumsum(ang_p, dim=-1) - torch.cumsum(ang_t, dim=-1)).mean()
    vals = {"profile": profile, "JS": js, "spectral_CDF": spectral, "angular_CDF": angular}
    vals["total"] = sum(PROFILE_WEIGHTS[k] * vals[k] for k in PROFILE_WEIGHTS)
    return vals


def profile_loss_numpy(prediction: np.ndarray, target: np.ndarray) -> dict[str, float]:
    pred = np.maximum(np.asarray(prediction, dtype=np.float64), 0.0); truth = np.maximum(np.asarray(target, dtype=np.float64), 0.0)
    pred /= np.maximum(pred.sum(axis=(-2, -1), keepdims=True), 1e-12); truth /= np.maximum(truth.sum(axis=(-2, -1), keepdims=True), 1e-12)
    lp = np.log(np.maximum(pred, 1e-12)); lt = np.log(np.maximum(truth, 1e-12)); diff = np.abs(lp - lt); profile = np.where(diff < 1.0, 0.5 * diff * diff, diff - 0.5).mean()
    mid = 0.5 * (pred + truth); js = 0.5 * np.sum(pred * np.log(np.maximum(pred / np.maximum(mid, 1e-12), 1e-12)) + truth * np.log(np.maximum(truth / np.maximum(mid, 1e-12), 1e-12)), axis=(-2, -1)).mean()
    sp = pred.sum(axis=-1); st = truth.sum(axis=-1); ap = pred.sum(axis=-2); at = truth.sum(axis=-2)
    sp /= np.maximum(sp.sum(axis=-1, keepdims=True), 1e-12); st /= np.maximum(st.sum(axis=-1, keepdims=True), 1e-12); ap /= np.maximum(ap.sum(axis=-1, keepdims=True), 1e-12); at /= np.maximum(at.sum(axis=-1, keepdims=True), 1e-12)
    spectral = np.abs(np.cumsum(sp, axis=-1) - np.cumsum(st, axis=-1)).mean(); angular = np.abs(np.cumsum(ap, axis=-1) - np.cumsum(at, axis=-1)).mean()
    vals = {"profile": float(profile), "JS": float(js), "spectral_CDF": float(spectral), "angular_CDF": float(angular)}; vals["total"] = sum(PROFILE_WEIGHTS[k] * vals[k] for k in PROFILE_WEIGHTS); return vals


def geometry_folds(geom: pd.DataFrame) -> dict[int, list[str]]:
    ordered = sorted(geom.geometry_hash.astype(str), key=lambda x: stable_key("MDC_V3_OUTER_FOLD", 20260810, x))
    return {f: sorted(ordered[f::5]) for f in FOLDS}


def inner_split(geom: pd.DataFrame, held_out: set[str]) -> tuple[list[str], list[str]]:
    train = geom.loc[~geom.geometry_hash.isin(held_out)].copy(); stop: list[str] = []
    for topo, block in train.groupby(train.topology_family.fillna("ALL"), sort=True):
        values = sorted(block.geometry_hash.astype(str), key=lambda x: stable_key("MDC_V3_INNER_STOP", INNER_SEED, x))
        stop.extend(values[: max(1, int(math.ceil(len(values) * 0.20)))])
    stop_set = set(stop); fit = sorted(set(train.geometry_hash) - stop_set)
    if stop_set & held_out or not stop_set <= set(train.geometry_hash):
        raise RuntimeError("HARD_GATE_INNER_STOP_LEAKAGE")
    return fit, sorted(stop_set)


def load_candidates() -> list[dict[str, Any]]:
    c = read_json(MODEL_CONTRACT)
    if c.get("candidate_count") != 3 or [x["id"] for x in c["candidates"]] != ["V3-A", "V3-B", "V3-C"]:
        raise RuntimeError("HARD_GATE_CANDIDATE_REGISTRY")
    if any(int(x["input_width"]) != len(FEATURE_ORDER) for x in c["candidates"]):
        raise RuntimeError("HARD_GATE_FEATURE_WIDTH")
    return c["candidates"]


def write_schema_contract(run: Path) -> dict[str, Any]:
    parent_schema = REPO / "outputs" / "mdc_hf_surrogate_v2_oof_model_selection_v1" / "20260804T_oof_model_selection_08915e7" / "oof_geometry_input_schema.json"
    parent_case = REPO / "outputs" / "mdc_hf_surrogate_v2_oof_model_selection_v1" / "20260804T_oof_model_selection_08915e7" / "oof_case_conditioning_schema.json"
    if not parent_schema.exists() or not parent_case.exists():
        raise RuntimeError("HARD_GATE_PARENT_INPUT_SCHEMA_MISSING")
    contract = {"contract_id": "MDC_HF_SURROGATE_V3_INPUT_SCHEMA_INHERITED_V1", "feature_order": list(FEATURE_ORDER), "input_width": len(FEATURE_ORDER), "geometry_feature_order": list(PARENT_FAMILY_FEATURES + NUMERIC_FEATURES + ("has_C", "has_M")), "case_feature_order": ["source_top", "source_centroid", "source_bottom", "dipole_x", "dipole_z"], "numeric_fields": list(NUMERIC_FEATURES), "missing_value_policy": "inherit parent V2: numeric fill 0; has_C/has_M masks; continuous geometry fields fold-local standardized; one-hot fields unscaled", "unknown_topology_policy": "V3 families Explicit/ZL1/ZL2 are out-of-vocabulary for the frozen parent eight-family one-hot; encode all eight parent family bits as zero; retain original topology_family only for stratified diagnostics", "provenance": {"parent_geometry_schema": str(parent_schema), "parent_geometry_schema_sha256": sha_file(parent_schema), "parent_case_schema": str(parent_case), "parent_case_schema_sha256": sha_file(parent_case), "v3_model_candidate_contract": str(MODEL_CONTRACT), "v3_model_candidate_contract_sha256": sha_file(MODEL_CONTRACT), "reason": "V3 frozen input_width=23 exactly matches inherited parent 18+5 interface; V3 freeze provides no replacement feature schema"}, "status": "PASS"}
    dump_json(run / "v3_input_schema_contract.json", contract); return contract


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--run-dir", required=True); ap.add_argument("--max-fits", type=int, default=FIT_CAP); ap.add_argument("--preflight-only", action="store_true"); args = ap.parse_args()
    run = Path(args.run_dir); run.mkdir(parents=True, exist_ok=True)
    geom, cases, wavelength, angle_rad, _ = load_inputs(); candidates = load_candidates(); schema = write_schema_contract(run)
    Xraw = feature_rows(geom, cases)
    folds = geometry_folds(geom); fold_records = {}; inner_records = {}
    for f in FOLDS:
        fit, stop = inner_split(geom, set(folds[f])); fold_records[str(f)] = {"outer_held_out": folds[f], "outer_train": sorted(set(geom.geometry_hash) - set(folds[f]))}; inner_records[str(f)] = {"inner_train": fit, "inner_stop": stop}
    dump_json(run / "formal_membership_and_split_registry.json", {"status": "PASS", "geometry_count": len(geom), "case_count": len(cases), "folds": fold_records, "inner_stop": inner_records, "fold_sha256": sha_obj(fold_records), "inner_sha256": sha_obj(inner_records), "case_level_leakage": False, "formal_matrix": [[c["id"], f, s] for c in candidates for f in FOLDS for s in SEEDS]})
    if args.preflight_only:
        dump_json(run / "execution_accounting.json", {"planned_unique_fits": FIT_CAP, "started": 0, "completed": 0, "resumed": 0, "solver_calls": 0, "status": "PREFLIGHT_PASS"}); print(json.dumps({"status": "PREFLIGHT_PASS", "geometry_count": len(geom), "case_count": len(cases), "fits": FIT_CAP, "schema_sha256": sha_file(run / "v3_input_schema_contract.json")})); return 0
    if args.max_fits != FIT_CAP:
        raise RuntimeError("HARD_GATE_FORMAL_MATRIX_MUST_BE_45")
    # Materialize q profiles once. This is a development artifact, never staged.
    qpath = run / "profile_q_memmap.f32"; q = np.memmap(qpath, mode="w+", dtype="float32", shape=(len(cases), PROFILE_DIM))
    for i, p in enumerate(cases.raw_path):
        q[i] = q_from_npz(Path(p), wavelength, angle_rad).reshape(-1)
    q.flush()
    # Fit one fold-local PCA and scaler per outer fold, then reuse across candidate/seed fits.
    fold_assets: dict[int, dict[str, Any]] = {}
    for f in FOLDS:
        held = set(folds[f]); train_cases = np.flatnonzero(~cases.geometry_hash.isin(held).to_numpy()); mean, comp = fit_pca(q, train_cases); z = transform_pca(q, mean, comp)
        train_geom = ~geom.geometry_hash.isin(held); case_train = cases.geometry_hash.isin(set(geom.loc[train_geom, "geometry_hash"])).to_numpy(); mu = Xraw[case_train].mean(axis=0); sd = Xraw[case_train].std(axis=0); sd[: len(PARENT_FAMILY_FEATURES)] = 1.0; sd[len(PARENT_FAMILY_FEATURES)+8:] = 1.0; sd = np.where(sd < 1e-12, 1.0, sd); Xs = (Xraw - mu) / sd
        asset_dir = run / "fold_assets" / f"fold_{f}"; asset_dir.mkdir(parents=True, exist_ok=True); np.savez_compressed(asset_dir / "pca.npz", mean=mean, components=comp); np.savez_compressed(asset_dir / "scaler.npz", mean=mu, std=sd); np.save(asset_dir / "latent_targets.npy", z); fold_assets[f] = {"mean": mean, "components": comp, "z": z, "X": Xs, "pca_sha256": sha_file(asset_dir / "pca.npz"), "scaler_sha256": sha_file(asset_dir / "scaler.npz")}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu"); print(f"device={device}")
    fit_records = []; oof_rows = []; started = 0; completed = 0; resumed = 0
    for cand in candidates:
        for f in FOLDS:
            held = set(folds[f]); train_geom, stop_geom = inner_split(geom, held); train_idx = np.flatnonzero(cases.geometry_hash.isin(set(train_geom)).to_numpy()); stop_idx = np.flatnonzero(cases.geometry_hash.isin(set(stop_geom)).to_numpy()); held_idx = np.flatnonzero(cases.geometry_hash.isin(held).to_numpy()); asset = fold_assets[f]; components_t = torch.from_numpy(asset["components"]).to(device); mean_t = torch.from_numpy(asset["mean"]).to(device)
            for seed in SEEDS:
                set_seed(seed); fit_id = {"candidate_id": cand["id"], "outer_fold": f, "seed": seed}; fit_key = sha_obj(fit_id); fit_dir = run / "fits" / fit_key; fit_dir.mkdir(parents=True, exist_ok=True); provenance = {**fit_id, "fit_key": fit_key, "train_geometry_hashes": train_geom, "inner_stop_geometry_hashes": stop_geom, "outer_heldout_geometry_hashes": sorted(held), "pca_sha256": asset["pca_sha256"], "scaler_sha256": asset["scaler_sha256"], "schema_sha256": sha_file(run / "v3_input_schema_contract.json"), "loss_contract_sha256": sha_file(LOSS_CONTRACT), "training_contract_sha256": sha_file(TRAIN_CONTRACT), "code_commit": os.popen("git rev-parse HEAD").read().strip()}
                state_path = fit_dir / "state.pt"; best_path = fit_dir / "best.pt"; result_path = fit_dir / "fit_result.json"
                if result_path.exists() and best_path.exists():
                    rec = read_json(result_path); fit_records.append(rec); completed += 1; resumed += 1
                    for i in held_idx: oof_rows.append({"candidate_id": cand["id"], "outer_fold": f, "seed": seed, "case_index": int(i), "geometry_hash": str(cases.iloc[i].geometry_hash), "source_position": str(cases.iloc[i].source_position), "dipole_orientation": str(cases.iloc[i].dipole_orientation), "latent": np.load(fit_dir / "heldout_pred_latent.npy")[list(held_idx).index(i)].tolist()})
                    continue
                started += 1
                model = ProfileOnlyModel(cand).to(device); opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=float(cand["weight_decay"])); sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda e: (e + 1) / WARMUP if e + 1 <= WARMUP else (MIN_LR / LR) + (1 - MIN_LR / LR) * (1 + math.cos(math.pi * (e + 1 - WARMUP) / (MAX_EPOCHS - WARMUP))) / 2)
                start_epoch = 0; best_metric = float("inf"); best_epoch = 0; patience_count = 0; best_state = None
                if state_path.exists():
                    checkpoint = torch.load(state_path, map_location=device, weights_only=False); model.load_state_dict(checkpoint["model"]); opt.load_state_dict(checkpoint["optimizer"]); sched.load_state_dict(checkpoint["scheduler"]); start_epoch = int(checkpoint["epoch"]); best_metric = float(checkpoint["best_metric"]); best_epoch = int(checkpoint["best_epoch"]); patience_count = int(checkpoint["patience_count"]); best_state = checkpoint["best_state"]; resumed += 1
                x_t = torch.from_numpy(asset["X"]).to(device); z_t = torch.from_numpy(asset["z"]).to(device)
                geom_order = sorted(set(cases.geometry_hash)); geom_to_indices = {g: np.flatnonzero(cases.geometry_hash.to_numpy() == g) for g in geom_order}
                for epoch in range(start_epoch + 1, MAX_EPOCHS + 1):
                    model.train(); order = train_idx.copy(); rng = np.random.default_rng(seed + epoch); rng.shuffle(order); groups = [order[i : i + BATCH_GEOMETRY_GROUPS * 6] for i in range(0, len(order), BATCH_GEOMETRY_GROUPS * 6)]
                    for batch in groups:
                        opt.zero_grad(set_to_none=True); out = model(x_t[batch])["latent"]; pred = out @ components_t + mean_t; truth = z_t[batch] @ components_t + mean_t; loss = profile_loss_torch(pred.reshape(-1, *NATIVE_SHAPE), truth.reshape(-1, *NATIVE_SHAPE))["total"]; loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP); opt.step()
                    sched.step(); model.eval()
                    if epoch >= MIN_EPOCHS:
                        with torch.no_grad():
                            pred_stop = (model(x_t[stop_idx])["latent"] @ components_t + mean_t).detach().cpu().numpy().reshape(-1, *NATIVE_SHAPE); truth_stop = (z_t[stop_idx] @ components_t + mean_t).detach().cpu().numpy().reshape(-1, *NATIVE_SHAPE)
                        stop_pred = []; stop_truth = []
                        for g in stop_geom:
                            inds = [int(i) for i in stop_idx if str(cases.iloc[i].geometry_hash) == g]; loc = [list(stop_idx).index(i) for i in inds]; stop_pred.append(np.mean(np.maximum(pred_stop[loc], 0.0), axis=0)); stop_truth.append(np.mean(np.maximum(truth_stop[loc], 0.0), axis=0))
                        metric = profile_loss_numpy(np.asarray(stop_pred), np.asarray(stop_truth))["total"]
                        improved = metric < best_metric - MIN_DELTA
                        if improved:
                            best_metric = metric; best_epoch = epoch; patience_count = 0; best_state = copy.deepcopy(model.state_dict()); torch.save({"model": best_state, "candidate_id": cand["id"], "outer_fold": f, "seed": seed, "best_epoch": best_epoch, "best_metric": best_metric, "provenance": provenance}, best_path)
                        else:
                            patience_count += 1
                        if patience_count >= PATIENCE: break
                    torch.save({"epoch": epoch, "model": model.state_dict(), "optimizer": opt.state_dict(), "scheduler": sched.state_dict(), "best_metric": best_metric, "best_epoch": best_epoch, "patience_count": patience_count, "best_state": best_state, "provenance": provenance}, state_path)
                if best_epoch < MIN_EPOCHS or best_state is None: raise RuntimeError("HARD_GATE_NO_ELIGIBLE_CHECKPOINT")
                model.load_state_dict(best_state); model.eval();
                with torch.no_grad(): pred_hold = model(x_t[held_idx])["latent"].detach().cpu().numpy()
                np.save(fit_dir / "heldout_pred_latent.npy", pred_hold); result = {**provenance, "best_epoch": best_epoch, "best_inner_stop_composite": best_metric, "stopping_reason": "patience" if patience_count >= PATIENCE else "max_epochs", "finite": bool(np.isfinite(pred_hold).all()), "prediction_complete": len(pred_hold) == len(held_idx), "fold_leakage": False, "case_leakage": False, "pca_scaler_leakage": False, "outer_stop_contamination": False, "status": "COMPLETED", "checkpoint_sha256": sha_file(best_path)}; dump_json(result_path, result); fit_records.append(result); completed += 1
                for pos, i in enumerate(held_idx): oof_rows.append({"candidate_id": cand["id"], "outer_fold": f, "seed": seed, "case_index": int(i), "geometry_hash": str(cases.iloc[i].geometry_hash), "source_position": str(cases.iloc[i].source_position), "dipole_orientation": str(cases.iloc[i].dipole_orientation), "latent": pred_hold[pos].tolist()})
                dump_json(run / "execution_accounting.json", {"planned_unique_fits": FIT_CAP, "started": started, "completed": completed, "resumed": resumed, "duplicate_formal_identities": 0, "solver_calls": 0, "status": "RUNNING"})
    dump_json(run / "execution_accounting.json", {"planned_unique_fits": FIT_CAP, "started": started, "completed": completed, "resumed": resumed, "duplicate_formal_identities": 0, "solver_calls": 0, "status": "PASS" if completed == FIT_CAP else "HARD_GATE_FORMAL_MATRIX_INCOMPLETE"})
    (run / "oof_predictions.jsonl").write_text("\n".join(json.dumps(x, separators=(",", ":")) for x in oof_rows), encoding="utf-8")
    dump_json(run / "fit_matrix.json", {"status": "PASS" if len(fit_records) == FIT_CAP else "HARD_GATE_FORMAL_MATRIX_INCOMPLETE", "fit_count": len(fit_records), "fits": fit_records})
    print(json.dumps({"status": "PASS" if completed == FIT_CAP else "HARD_GATE_FORMAL_MATRIX_INCOMPLETE", "started": started, "completed": completed, "resumed": resumed, "run_dir": str(run)})); return 0


if __name__ == "__main__":
    raise SystemExit(main())
