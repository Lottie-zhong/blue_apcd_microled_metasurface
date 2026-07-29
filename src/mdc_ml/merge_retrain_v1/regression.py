from __future__ import annotations

"""Synthetic-only, three-seed regression crossfit backend.

Formal regression labels and formal OOF stay authorization-gated.  The module
only reads formal registry metadata for its contract audit; every fit is driven
by caller-provided synthetic data under a system-TEMP artifact policy.
"""

import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn

from .artifacts import ArtifactPolicy, AtomicArtifactStore
from .classification import AtomicExecutionStateStore, MATERIAL_TOKEN_INDICES, _execution_code_commit, _now
from .contracts import FrozenContract, ROOT, canonical_json, sha256_file, sha256_value
from .state import TrainingExecutionState, UnitState

REGRESSION_TARGETS = (
    "spectral_fwhm_normal_nm", "angular_fwhm_450_deg",
    "cone5_integral_proxy", "normal_band_transmission_proxy",
)
SEEDS = (20260720, 20260721, 20260722)
SCHEMA_VERSION = "mdc_ml_regression_three_seed_crossfit_v1"
FIXTURE_COVERAGE = 0.90


def _signature(values: Iterable[str]) -> str:
    return sha256_value(sorted(map(str, values)))


def _array_signature(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(np.round(values, 12)).tobytes()).hexdigest()


@dataclass(frozen=True)
class RegressionMetadata:
    sample_ids: tuple[str, ...]
    geometry_hashes: tuple[str, ...]
    groups: tuple[str, ...]
    roles: tuple[str, ...]
    folds: tuple[int, ...]
    is_round1: tuple[bool, ...]
    eligible: tuple[bool, ...]
    exclusion_reason: tuple[str, ...]
    target_validity_masks: tuple[str, ...]
    provenance: tuple[str, ...]
    feature_signature: str
    counts: dict[str, int]


@dataclass(frozen=True)
class RegressionData:
    X: np.ndarray
    y: np.ndarray
    metadata: RegressionMetadata


@dataclass(frozen=True)
class RegressionDevelopmentView:
    data: RegressionData
    ineligible_registry: tuple[dict[str, str], ...]
    excluded_sealed_registry: tuple[dict[str, str], ...]
    view_fingerprint: str


@dataclass(frozen=True)
class RegressionFoldPlan:
    fold_id: int
    train_indices: tuple[int, ...]
    held_out_indices: tuple[int, ...]
    validation_indices: tuple[int, ...]
    calibration_indices: tuple[int, ...]
    train_signature: str
    held_out_signature: str
    validation_signature: str
    calibration_signature: str
    feature_signature: str


class RegressionMLP(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(150, 256), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(256, 128), nn.ReLU(), nn.Dropout(0.1), nn.Linear(128, 4),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.network(values)


def _scaled(scaler: StandardScaler, X: np.ndarray) -> np.ndarray:
    values = scaler.transform(X)
    values[:, MATERIAL_TOKEN_INDICES] = X[:, MATERIAL_TOKEN_INDICES]
    return values.astype(np.float32, copy=False)


def _eligible(row: dict[str, str]) -> bool:
    return row["continuous_regression_target_eligible"] == "True" and row["nominal_4d_objective_eligible"] == "True"


def _reason(row: dict[str, str]) -> str:
    reasons = []
    for key in ("continuous_regression_target_eligible", "nominal_4d_objective_eligible", "spectral_fwhm_valid", "angular_fwhm_valid"):
        if row.get(key) != "True": reasons.append(key + "=false")
    return ";".join(reasons) or "eligible"


def load_regression_metadata(contract: FrozenContract) -> RegressionMetadata:
    """Read only frozen registry metadata; this function never constructs target arrays."""
    root = contract.output_root
    rows = list(csv.DictReader((root / "merged_registry_v1.csv").open(encoding="utf8", newline="")))
    assignment = {row["candidate_id"]: row for row in csv.DictReader((root / "adaptive_crossfit_assignment_v1.csv").open(encoding="utf8", newline=""))}
    ids = tuple(row["candidate_id"] for row in rows)
    round1 = tuple(value.startswith("ROUND1:") for value in ids)
    eligible = tuple(_eligible(row) for row in rows)
    folds = tuple(int(assignment[value]["fold"]) if value in assignment else -1 for value in ids)
    roles = tuple(("round1_eligible_fold_" + str(folds[index])) if round1[index] and eligible[index] else (("round1_ineligible_fold_" + str(folds[index])) if round1[index] else row["original_split"]) for index, row in enumerate(rows))
    counts = {
        "round1_count": sum(round1),
        "round1_eligible_count": sum(round1[index] and eligible[index] for index in range(len(rows))),
        "round1_ineligible_count": sum(round1[index] and not eligible[index] for index in range(len(rows))),
        "original_train_eligible": sum(role == "train" and eligible[index] for index, role in enumerate(roles)),
        "original_validation_eligible": sum(role == "validation" and eligible[index] for index, role in enumerate(roles)),
        "original_calibration_eligible": sum(role == "calibration" and eligible[index] for index, role in enumerate(roles)),
        "sealed_test": sum(role == "test" for role in roles),
    }
    if counts["round1_count"] != 128 or counts["round1_eligible_count"] != 100 or counts["round1_ineligible_count"] != 28:
        raise RuntimeError("REGRESSION_METADATA_PARTITION_DRIFT:" + canonical_json(counts))
    return RegressionMetadata(
        ids, tuple(row["canonical_geometry_hash"] for row in rows),
        tuple(assignment[value]["group_id"] if value in assignment else row["canonical_geometry_hash"] for value, row in zip(ids, rows)),
        roles, folds, round1, eligible, tuple(_reason(row) for row in rows),
        tuple(row.get("continuous_regression_target_mask", "{}") for row in rows),
        tuple(row.get("source_dataset", "") + ":" + row.get("source_row_id", "") for row in rows), contract.feature_signature, counts,
    )


def load_formal_regression_data(contract: FrozenContract, *, formal_authorized: bool = False) -> RegressionData:
    """Read-only canonical adapter; execution remains authorization-gated."""
    if not formal_authorized:
        raise PermissionError("FORMAL_REGRESSION_OOF_REQUIRES_SEPARATE_AUTHORIZATION")
    return load_regression_development_view(contract).data


def load_regression_development_view(contract: FrozenContract) -> RegressionDevelopmentView:
    """Load only the versioned non-sealed development view and identity registries."""
    root = contract.output_root
    development_contract = json.loads((ROOT / "configs" / "mdc_ml_regression_development_contract_v1.json").read_text(encoding="utf8"))
    if development_contract["development_rows"] != 726 or development_contract["sealed_regression_rows_excluded"] != 111:
        raise RuntimeError("REGRESSION_DEVELOPMENT_CONTRACT_DRIFT")
    meta = json.loads((root / "regression_development_view_v1.json").read_text(encoding="utf8"))
    if meta["development_rows"] != 726 or meta["excluded_sealed_identity_rows"] != 111:
        raise RuntimeError("REGRESSION_DEVELOPMENT_VIEW_CONTRACT_DRIFT")
    view = np.load(root / "regression_development_view_v1.npz", allow_pickle=False)
    X = np.asarray(view["X"], dtype=float); y = np.asarray(view["y_regression"], dtype=float)
    ids = tuple(str(v) for v in view["candidate_ids"]); roles = tuple(str(v) for v in view["roles"])
    folds = tuple(int(v) for v in view["folds"]); round1 = tuple(role.startswith("round1_eligible_fold_") for role in roles)
    if X.shape != (726, 150) or y.shape != (726, 4) or not np.isfinite(y).all():
        raise RuntimeError("REGRESSION_DEVELOPMENT_VIEW_SHAPE_OR_TARGET_DRIFT")
    counts = {"round1_count": 100, "round1_eligible_count": 100, "round1_ineligible_count": 28,
              "original_train_eligible": 443, "original_validation_eligible": 111,
              "original_calibration_eligible": 72, "sealed_test": 111}
    metadata = RegressionMetadata(ids, tuple(str(v) for v in view["geometry_hashes"]), tuple(str(v) for v in view["groups"]),
        roles, folds, round1, tuple(True for _ in ids), tuple("eligible" for _ in ids), tuple(str(v) for v in view["target_masks"]),
        tuple(str(v) for v in view["provenance"]), contract.feature_signature, counts)
    ineligible = tuple({key: row[key] for key in ("candidate_id","canonical_geometry_hash","source_dataset","source_row_id","original_split")}
        for row in csv.DictReader((root / "merged_registry_v1.csv").open(encoding="utf8", newline=""))
        if row["candidate_id"].startswith("ROUND1:") and row["continuous_regression_target_eligible"] == "False")
    excluded = tuple(csv.DictReader((root / "regression_development_excluded_sealed_v1.csv").open(encoding="utf8", newline="")))
    if len(ineligible) != 28 or len(excluded) != 377:
        raise RuntimeError("REGRESSION_DEVELOPMENT_IDENTITY_REGISTRY_DRIFT")
    return RegressionDevelopmentView(RegressionData(X, y, metadata), ineligible, excluded, meta["view_fingerprint"])


def build_regression_crossfit_plan(data: RegressionMetadata | RegressionData, contract: FrozenContract) -> tuple[RegressionFoldPlan, ...]:
    metadata = data.metadata if isinstance(data, RegressionData) else data
    if metadata.feature_signature != contract.feature_signature or tuple(contract.targets.regression_targets) != REGRESSION_TARGETS:
        raise RuntimeError("REGRESSION_CONTRACT_DRIFT")
    validation = tuple(index for index, role in enumerate(metadata.roles) if role == "validation" and metadata.eligible[index])
    calibration = tuple(index for index, role in enumerate(metadata.roles) if role == "calibration" and metadata.eligible[index])
    base_train = tuple(index for index, role in enumerate(metadata.roles) if role == "train" and metadata.eligible[index])
    plans = []
    for fold in range(4):
        held = tuple(index for index, role in enumerate(metadata.roles) if role == f"round1_eligible_fold_{fold}")
        train = base_train + tuple(index for index, role in enumerate(metadata.roles) if role.startswith("round1_eligible_fold_") and role != f"round1_eligible_fold_{fold}")
        if not held or set(train) & set(held) or set(train) & (set(validation) | set(calibration)):
            raise RuntimeError("REGRESSION_SPLIT_LEAKAGE")
        if {metadata.groups[index] for index in train} & {metadata.groups[index] for index in held}:
            raise RuntimeError("REGRESSION_GROUP_LEAKAGE")
        plans.append(RegressionFoldPlan(fold, train, held, validation, calibration, _signature(metadata.sample_ids[index] for index in train), _signature(metadata.sample_ids[index] for index in held), _signature(metadata.sample_ids[index] for index in validation), _signature(metadata.sample_ids[index] for index in calibration), metadata.feature_signature))
    held_all = [index for plan in plans for index in plan.held_out_indices]
    expected = [index for index, flag in enumerate(metadata.is_round1) if flag and metadata.eligible[index]]
    if sorted(held_all) != expected or len(set(held_all)) != len(expected):
        raise RuntimeError("REGRESSION_OOF_EXACT_ONCE_PLAN_FAILED")
    return tuple(plans)


def regression_backend_audit(contract: FrozenContract) -> dict[str, Any]:
    metadata = load_regression_metadata(contract)
    plans = build_regression_crossfit_plan(metadata, contract)
    return {
        "status": "PASS", "round1_count": 128, "regression_eligible_count": 100, "regression_ineligible_count": 28,
        "fold_count": 4, "eligible_fold_sizes": [len(plan.held_out_indices) for plan in plans], "eligible_fold_size_sum": sum(len(plan.held_out_indices) for plan in plans),
        "eligible_ineligible_overlap": 0, "group_overlap": 0, "train_held_out_overlap": 0,
        "fixed_candidate_id": contract.fixed_regression_baseline, "seed_count": 3, "seeds": list(SEEDS), "target_count": 4, "feature_count": 150,
        "formal_conformal_coverage_parameter_pending_contract": True,
        "fit_calls": 0, "formal_regression_oof_calls": 0, "formal_output_write_count": 0, "sealed_test_target_reads": 0, "sealed_test_prediction_calls": 0, "TMM_calls": 0, "FDTD_calls": 0, "Lumerical_calls": 0,
    }


def _set_seed(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.use_deterministic_algorithms(True, warn_only=True)


def _target_scaler(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = y.mean(axis=0); scale = y.std(axis=0); scale = np.where(scale < 1e-12, 1.0, scale)
    return mean.astype(np.float32), scale.astype(np.float32)


def _fit_seed(data: RegressionData, plan: RegressionFoldPlan, seed: int, *, max_epochs: int) -> dict[str, Any]:
    _set_seed(seed)
    scaler = StandardScaler().fit(data.X[list(plan.train_indices)])
    mean, scale = _target_scaler(data.y[list(plan.train_indices)])
    train_x = torch.tensor(_scaled(scaler, data.X[list(plan.train_indices)])); train_y = torch.tensor((data.y[list(plan.train_indices)] - mean) / scale, dtype=torch.float32)
    val_x = torch.tensor(_scaled(scaler, data.X[list(plan.validation_indices)])); val_y = torch.tensor((data.y[list(plan.validation_indices)] - mean) / scale, dtype=torch.float32)
    model = RegressionMLP(); optimizer = torch.optim.AdamW(model.parameters(), lr=0.0007, weight_decay=1e-5, betas=(0.9, 0.999), eps=1e-8)
    loss_fn = nn.SmoothL1Loss(beta=1.0); best = math.inf; best_epoch = -1; best_state = None; wait = 0; trace = []
    for epoch in range(max_epochs):
        model.train(); optimizer.zero_grad(set_to_none=True); loss = loss_fn(model(train_x), train_y); loss.backward(); optimizer.step()
        model.eval()
        with torch.no_grad(): val_loss = float(loss_fn(model(val_x), val_y).item())
        trace.append(val_loss)
        if val_loss < best - 1e-7:
            best = val_loss; best_epoch = epoch; best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}; wait = 0
        else:
            wait += 1
            if wait >= 35: break
    if best_state is None: raise RuntimeError("REGRESSION_EARLY_STOPPING_NO_BEST_STATE")
    model.load_state_dict(best_state)
    return {"seed": seed, "state_dict": model.state_dict(), "feature_scaler": scaler, "target_mean": mean, "target_scale": scale, "best_epoch": best_epoch, "validation_trace": trace, "validation_signature": plan.validation_signature, "train_signature": plan.train_signature, "architecture": {"input": 150, "hidden": [256, 128], "dropout": 0.1, "output": 4}, "optimizer": {"name": "AdamW", "lr": 0.0007, "weight_decay": 1e-5, "betas": [0.9, 0.999], "eps": 1e-8}, "loss": "SmoothL1Loss(beta=1.0)"}


def _predict(bundle: dict[str, Any], X: np.ndarray) -> np.ndarray:
    model = RegressionMLP(); model.load_state_dict(bundle["state_dict"]); model.eval()
    values = torch.tensor(_scaled(bundle["feature_scaler"], X))
    with torch.no_grad(): standard = model(values).detach().cpu().numpy()
    return standard * np.asarray(bundle["target_scale"]) + np.asarray(bundle["target_mean"])


def _quantile(values: np.ndarray, coverage: float) -> np.ndarray:
    try: return np.quantile(values, coverage, axis=0, method="higher")
    except TypeError: return np.quantile(values, coverage, axis=0, interpolation="higher")


def _state(store: AtomicArtifactStore, contract: FrozenContract, run_id: str, trainer_sha: str, commit: str) -> TrainingExecutionState:
    signatures = type(contract.signatures)(**{**contract.signatures.as_dict(), "trainer_sha256": trainer_sha, "execution_code_commit": commit})
    state = TrainingExecutionState.new(run_id, signatures, timestamp=_now()); state.transition("RUNNING", timestamp=_now()); state.transition_stage("PREFLIGHT", "RUNNING", timestamp=_now()); state.transition_stage("PREFLIGHT", "COMPLETE", timestamp=_now()); state.transition_stage("REGRESSION_OOF", "RUNNING", timestamp=_now())
    for fold in range(4):
        state.add_unit("REGRESSION_OOF", UnitState("fold", f"fold_{fold}", required_artifacts=(f"folds/fold_{fold}/complete.json",)))
        for seed in SEEDS: state.add_unit("REGRESSION_OOF", UnitState("seed", f"fold_{fold}_seed_{seed}", required_artifacts=(f"folds/fold_{fold}/seed_{seed}.joblib", f"folds/fold_{fold}/seed_{seed}_snapshot.json")))
        state.add_unit("REGRESSION_OOF", UnitState("artifact", f"fold_{fold}_ensemble", required_artifacts=(f"folds/fold_{fold}/ensemble.json",)))
        state.add_unit("REGRESSION_OOF", UnitState("artifact", f"fold_{fold}_conformal", required_artifacts=(f"folds/fold_{fold}/conformal.json",)))
    return state


def _seed_paths(fold: int, seed: int) -> tuple[str, str]:
    return f"folds/fold_{fold}/seed_{seed}.joblib", f"folds/fold_{fold}/seed_{seed}_snapshot.json"


def _verify_seed(store: AtomicArtifactStore, state: TrainingExecutionState, fold: int, seed: int) -> None:
    model_relative, snapshot_relative = _seed_paths(fold, seed); model_path = store.root / model_relative; snapshot_path = store.root / snapshot_relative
    if not model_path.is_file() or not snapshot_path.is_file(): raise RuntimeError("REGRESSION_COMPLETED_SEED_ARTIFACT_MISSING")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf8"))
    if snapshot["checkpoint_sha256"] != sha256_file(model_path): raise RuntimeError("REGRESSION_ARTIFACT_DRIFT_GUARD")
    joblib.load(model_path)


def _write_seed(store: AtomicArtifactStore, state: TrainingExecutionState, plan: RegressionFoldPlan, seed: int, bundle: dict[str, Any]) -> None:
    model_relative, snapshot_relative = _seed_paths(plan.fold_id, seed)
    model_record = store.write_joblib(model_relative, bundle, artifact_type="regression_seed_checkpoint", producer_stage="REGRESSION_OOF", producer_unit=f"fold_{plan.fold_id}_seed_{seed}")
    scaler_sha = sha256_value({"feature_mean": bundle["feature_scaler"].mean_.tolist(), "feature_scale": bundle["feature_scaler"].scale_.tolist(), "target_mean": np.asarray(bundle["target_mean"]).tolist(), "target_scale": np.asarray(bundle["target_scale"]).tolist()})
    candidate_snapshot_sha = sha256_value({"architecture": bundle["architecture"], "optimizer": bundle["optimizer"], "loss": bundle["loss"]})
    snapshot = {"fold": plan.fold_id, "seed": seed, "checkpoint_sha256": model_record.sha256, "candidate_snapshot_sha256": candidate_snapshot_sha, "scaler_sha256": scaler_sha, "train_signature": plan.train_signature, "validation_signature": plan.validation_signature, "calibration_signature": plan.calibration_signature, "heldout_signature": plan.held_out_signature, "feature_signature": plan.feature_signature, "fold_signature": state.fold_signature, "execution_code_commit": state.execution_code_commit, "best_epoch": bundle["best_epoch"], "validation_trace": bundle["validation_trace"], "fixture_max_epochs": len(bundle["validation_trace"])}
    store.write_json(snapshot_relative, snapshot, artifact_type="regression_seed_snapshot", producer_stage="REGRESSION_OOF", producer_unit=f"fold_{plan.fold_id}_seed_{seed}")
    state.transition_unit("REGRESSION_OOF", "seed", f"fold_{plan.fold_id}_seed_{seed}", "COMPLETE", timestamp=_now(), artifacts=(model_relative, snapshot_relative))


def _record_existing(store: AtomicArtifactStore, relative: str, artifact_type: str, unit: str) -> None:
    path = store.root / relative
    store.write_bytes(relative, path.read_bytes(), artifact_type=artifact_type, producer_stage="REGRESSION_OOF", producer_unit=unit)


def _materialize_fold(data: RegressionData, plan: RegressionFoldPlan, store: AtomicArtifactStore, state: TrainingExecutionState, *, coverage: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    bundles = []
    for seed in SEEDS:
        relative, snapshot = _seed_paths(plan.fold_id, seed); _verify_seed(store, state, plan.fold_id, seed); _record_existing(store, relative, "regression_seed_checkpoint", f"fold_{plan.fold_id}_seed_{seed}"); _record_existing(store, snapshot, "regression_seed_snapshot", f"fold_{plan.fold_id}_seed_{seed}"); bundles.append(joblib.load(store.root / relative))
    held = data.X[list(plan.held_out_indices)]; calibration = data.X[list(plan.calibration_indices)]
    held_seed = np.stack([_predict(bundle, held) for bundle in bundles]); calibration_seed = np.stack([_predict(bundle, calibration) for bundle in bundles])
    held_mean = held_seed.mean(axis=0); held_std = held_seed.std(axis=0); calibration_mean = calibration_seed.mean(axis=0)
    residual = np.abs(calibration_mean - data.y[list(plan.calibration_indices)]); quantiles = _quantile(residual, coverage)
    ensemble_payload = {"fold": plan.fold_id, "seeds": list(SEEDS), "heldout_signature": plan.held_out_signature, "seed_prediction_signatures": [sha256_value(np.round(held_seed[index], 12).tolist()) for index in range(3)], "ensemble_signature": sha256_value(np.round(held_mean, 12).tolist()), "seed_spread_signature": sha256_value(np.round(held_std, 12).tolist())}
    conformal_payload = {"fold": plan.fold_id, "coverage": coverage, "quantile_method": "higher", "calibration_signature": plan.calibration_signature, "quantiles": quantiles.tolist(), "interval_signature": sha256_value(np.round(np.stack((held_mean - quantiles, held_mean + quantiles)), 12).tolist())}
    if state.stages["REGRESSION_OOF"].units[f"artifact:fold_{plan.fold_id}_ensemble"].status == "NOT_STARTED":
        state.transition_unit("REGRESSION_OOF", "artifact", f"fold_{plan.fold_id}_ensemble", "RUNNING", timestamp=_now())
    if state.stages["REGRESSION_OOF"].units[f"artifact:fold_{plan.fold_id}_conformal"].status == "NOT_STARTED":
        state.transition_unit("REGRESSION_OOF", "artifact", f"fold_{plan.fold_id}_conformal", "RUNNING", timestamp=_now())
    store.write_json(f"folds/fold_{plan.fold_id}/ensemble.json", ensemble_payload, artifact_type="regression_ensemble", producer_stage="REGRESSION_OOF", producer_unit=f"fold_{plan.fold_id}_ensemble")
    store.write_json(f"folds/fold_{plan.fold_id}/conformal.json", conformal_payload, artifact_type="regression_conformal", producer_stage="REGRESSION_OOF", producer_unit=f"fold_{plan.fold_id}_conformal")
    state.transition_unit("REGRESSION_OOF", "artifact", f"fold_{plan.fold_id}_ensemble", "COMPLETE", timestamp=_now(), artifacts=(f"folds/fold_{plan.fold_id}/ensemble.json",))
    state.transition_unit("REGRESSION_OOF", "artifact", f"fold_{plan.fold_id}_conformal", "COMPLETE", timestamp=_now(), artifacts=(f"folds/fold_{plan.fold_id}/conformal.json",))
    samples=[]; targets=[]; seed_rows=[]; intervals=[]; calibration_rows=[]
    for local, index in enumerate(plan.held_out_indices):
        samples.append({"candidate_id": data.metadata.sample_ids[index], "geometry_hash": data.metadata.geometry_hashes[index], "fold_id": plan.fold_id, "ensemble_mean": json.dumps(held_mean[local].tolist()), "ensemble_std": json.dumps(held_std[local].tolist()), "ensemble_min": json.dumps(held_seed[:, local, :].min(axis=0).tolist()), "ensemble_max": json.dumps(held_seed[:, local, :].max(axis=0).tolist()), "train_signature": plan.train_signature, "heldout_signature": plan.held_out_signature})
        for target_index, target in enumerate(REGRESSION_TARGETS):
            key = {"candidate_id": data.metadata.sample_ids[index], "target": target, "fold_id": plan.fold_id, "truth": float(data.y[index, target_index]), "ensemble_mean": float(held_mean[local, target_index]), "ensemble_std": float(held_std[local, target_index]), "ensemble_min": float(held_seed[:, local, target_index].min()), "ensemble_max": float(held_seed[:, local, target_index].max())}
            targets.append(key); intervals.append({**key, "lower": float(held_mean[local, target_index] - quantiles[target_index]), "upper": float(held_mean[local, target_index] + quantiles[target_index]), "width": float(2 * quantiles[target_index]), "coverage": coverage, "quantile_method": "higher"})
            for seed_index, seed in enumerate(SEEDS): seed_rows.append({"candidate_id": data.metadata.sample_ids[index], "target": target, "seed": seed, "fold_id": plan.fold_id, "prediction": float(held_seed[seed_index, local, target_index])})
    for local, index in enumerate(plan.calibration_indices):
        for target_index, target in enumerate(REGRESSION_TARGETS): calibration_rows.append({"fold_id": plan.fold_id, "candidate_id": data.metadata.sample_ids[index], "target": target, "prediction": float(calibration_mean[local, target_index]), "truth": float(data.y[index, target_index]), "nonconformity": float(residual[local, target_index]), "calibration_signature": plan.calibration_signature})
    store.write_json(f"folds/fold_{plan.fold_id}/complete.json", {"fold": plan.fold_id, "heldout_signature": plan.held_out_signature, "coverage": coverage, "seed_count": 3}, artifact_type="regression_fold_complete", producer_stage="REGRESSION_OOF", producer_unit=f"fold_{plan.fold_id}")
    state.transition_unit("REGRESSION_OOF", "fold", f"fold_{plan.fold_id}", "COMPLETE", timestamp=_now(), artifacts=(f"folds/fold_{plan.fold_id}/complete.json",))
    return samples, targets, seed_rows, intervals, calibration_rows


def _validate(rows: list[dict[str, Any]], targets: list[dict[str, Any]], seed_rows: list[dict[str, Any]], ineligible: list[dict[str, Any]], metadata: RegressionMetadata) -> dict[str, Any]:
    eligible_ids = {metadata.sample_ids[index] for index, flag in enumerate(metadata.is_round1) if flag and metadata.eligible[index]}
    ineligible_ids = {metadata.sample_ids[index] for index, flag in enumerate(metadata.is_round1) if flag and not metadata.eligible[index]}
    if len(rows) != len(eligible_ids) or {row["candidate_id"] for row in rows} != eligible_ids: raise RuntimeError("REGRESSION_SAMPLE_OOF_EXACT_ONCE_FAILED")
    if len(targets) != len(eligible_ids) * 4 or len({(row["candidate_id"], row["target"]) for row in targets}) != len(targets): raise RuntimeError("REGRESSION_TARGET_OOF_EXACT_ONCE_FAILED")
    if len(seed_rows) != len(eligible_ids) * 4 * 3 or len({(row["candidate_id"], row["target"], row["seed"]) for row in seed_rows}) != len(seed_rows): raise RuntimeError("REGRESSION_SEED_OOF_EXACT_ONCE_FAILED")
    if {row["candidate_id"] for row in ineligible} != ineligible_ids or ({row["candidate_id"] for row in targets} & ineligible_ids): raise RuntimeError("REGRESSION_INELIGIBLE_PREDICTION_LEAKAGE")
    return {"sample_rows": len(rows), "target_rows": len(targets), "seed_target_rows": len(seed_rows), "ineligible_rows": len(ineligible), "exact_once": True, "ineligible_prediction_count": 0}


def run_regression_crossfit(data: RegressionData, contract: FrozenContract, store: AtomicArtifactStore, *, state_store: AtomicExecutionStateStore | None = None, resume: bool = False, failure_injection: tuple[int, int] | None = None, fixture_max_epochs: int = 3, coverage: float = FIXTURE_COVERAGE) -> dict[str, Any]:
    if contract.fixed_regression_baseline != "multitask_mlp_3seed" or data.X.shape[1] != 150 or data.y.shape[1] != 4: raise RuntimeError("REGRESSION_FROZEN_CONTRACT_DRIFT")
    plans = build_regression_crossfit_plan(data, contract); state_store = state_store or AtomicExecutionStateStore(store.root); trainer_sha = sha256_file(Path(__file__)); commit = _execution_code_commit()
    if state_store.path.exists():
        state = state_store.load()
        if not resume: raise RuntimeError("REGRESSION_STATE_EXISTS_REQUIRES_RESUME")
        if state.execution_code_commit != commit or state.trainer_sha256 != trainer_sha: raise RuntimeError("REGRESSION_RESUME_SIGNATURE_DRIFT")
        if state.status == "FAILED":
            state.transition("RUNNING", timestamp=_now(), resume=True)
            state.transition_stage("REGRESSION_OOF", "RUNNING", timestamp=_now(), resume=True)
            # A failed fixture run may leave the parent fold unit failed while
            # completed seed checkpoints remain reusable.  Reopen only failed
            # units; completed units are independently checksum-verified below.
            for key, unit in state.stages["REGRESSION_OOF"].units.items():
                if unit.status == "FAILED":
                    unit_type, unit_id = key.split(":", 1)
                    state.transition_unit("REGRESSION_OOF", unit_type, unit_id, "RUNNING", timestamp=_now(), resume=True)
        state_store.persist(state)
    else:
        state = _state(store, contract, store.run_id, trainer_sha, commit); state_store.persist(state)
    try:
        for plan in plans:
            fold_unit = state.stages["REGRESSION_OOF"].units[f"fold:fold_{plan.fold_id}"]
            if fold_unit.status == "NOT_STARTED":
                state.transition_unit("REGRESSION_OOF", "fold", f"fold_{plan.fold_id}", "RUNNING", timestamp=_now(), resume=resume)
                state_store.persist(state)
            for seed in SEEDS:
                unit = state.stages["REGRESSION_OOF"].units[f"seed:fold_{plan.fold_id}_seed_{seed}"]
                if unit.status == "COMPLETE": _verify_seed(store, state, plan.fold_id, seed); continue
                state.transition_unit("REGRESSION_OOF", "seed", f"fold_{plan.fold_id}_seed_{seed}", "RUNNING", timestamp=_now(), resume=resume); state_store.persist(state)
                if failure_injection == (plan.fold_id, seed): raise RuntimeError(f"FIXTURE_FAILURE_INJECTION_FOLD_{plan.fold_id}_SEED_{seed}")
                bundle = _fit_seed(data, plan, seed, max_epochs=fixture_max_epochs); _write_seed(store, state, plan, seed, bundle); state_store.persist(state)
        sample_rows=[]; target_rows=[]; seed_rows=[]; intervals=[]; calibration_rows=[]
        for plan in plans:
            rows = _materialize_fold(data, plan, store, state, coverage=coverage)
            for target, values in zip((sample_rows, target_rows, seed_rows, intervals, calibration_rows), rows): target.extend(values)
            state_store.persist(state)
        ineligible = [{"candidate_id": data.metadata.sample_ids[index], "geometry_hash": data.metadata.geometry_hashes[index], "canonical_source_group": data.metadata.groups[index], "fold": data.metadata.folds[index], "regression_eligible": False, "classification_label": None, "exclusion_reason": data.metadata.exclusion_reason[index], "target_validity_mask": data.metadata.target_validity_masks[index], "failure_stage": "metadata_eligibility", "failure_reason": data.metadata.exclusion_reason[index], "provenance": data.metadata.provenance[index]} for index, flag in enumerate(data.metadata.is_round1) if flag and not data.metadata.eligible[index]]
        checks = _validate(sample_rows, target_rows, seed_rows, ineligible, data.metadata)
        fieldnames = lambda rows: list(rows[0]) if rows else []
        store.write_csv("regression_oof_sample_predictions.csv", sample_rows, fieldnames=fieldnames(sample_rows), artifact_type="regression_oof_samples", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_csv("regression_oof_target_predictions.csv", target_rows, fieldnames=fieldnames(target_rows), artifact_type="regression_oof_targets", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_csv("regression_oof_seed_target_predictions.csv", seed_rows, fieldnames=fieldnames(seed_rows), artifact_type="regression_oof_seed_targets", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_csv("regression_oof_conformal_intervals.csv", intervals, fieldnames=fieldnames(intervals), artifact_type="regression_intervals", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_csv("regression_calibration_nonconformity.csv", calibration_rows, fieldnames=fieldnames(calibration_rows), artifact_type="regression_calibration", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_json("regression_conformal_quantiles.json", {"coverage": coverage, "quantile_method": "higher", "formal_conformal_coverage_parameter_pending_contract": True, "fold_count": 4}, artifact_type="regression_quantiles", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_csv("regression_ineligible_registry.csv", ineligible, fieldnames=fieldnames(ineligible), artifact_type="regression_ineligible_registry", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_json("regression_fold_plan.json", {"plans": [asdict(plan) for plan in plans]}, artifact_type="regression_fold_plan", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_json("regression_seed_manifest.json", {"seeds": list(SEEDS), "fit_count": 12}, artifact_type="regression_seed_manifest", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_json("regression_scaler_manifest.json", {"feature_scaler": "train_only", "target_scaler": "eligible_train_only"}, artifact_type="regression_scaler_manifest", producer_stage="REGRESSION_OOF", producer_unit="all")
        checkpoints = [{"fold": fold, "seed": seed, "checkpoint": _seed_paths(fold, seed)[0], "snapshot": _seed_paths(fold, seed)[1], "checkpoint_sha256": sha256_file(store.root / _seed_paths(fold, seed)[0])} for fold in range(4) for seed in SEEDS]
        store.write_json("regression_checkpoint_manifest.json", {"checkpoint_count": len(checkpoints), "checkpoints": checkpoints}, artifact_type="regression_checkpoint_manifest", producer_stage="REGRESSION_OOF", producer_unit="all")
        store.write_json("regression_oof_manifest.json", {"sample_rows": checks["sample_rows"], "target_rows": checks["target_rows"], "seed_target_rows": checks["seed_target_rows"], "ineligible_rows": checks["ineligible_rows"], "exact_once": checks["exact_once"], "ineligible_prediction_count": checks["ineligible_prediction_count"]}, artifact_type="regression_oof_manifest", producer_stage="REGRESSION_OOF", producer_unit="all")
        manifest = store.write_manifest(); store.validate_manifest(manifest)
        state.transition_stage("REGRESSION_OOF", "COMPLETE", timestamp=_now()); state.transition("PARTIAL", timestamp=_now()); state_store.persist(state)
        return {"plans": plans, "sample_rows": sample_rows, "target_rows": target_rows, "seed_rows": seed_rows, "intervals": intervals, "calibration_rows": calibration_rows, "ineligible": ineligible, "checks": checks, "manifest_sha256": manifest.canonical_manifest_sha256, "state": state, "coverage": coverage}
    except Exception as exc:
        running = next((key for key, unit in reversed(list(state.stages["REGRESSION_OOF"].units.items())) if unit.status == "RUNNING"), None)
        if running:
            unit_type, unit_id = running.split(":", 1); state.transition_unit("REGRESSION_OOF", unit_type, unit_id, "FAILED", timestamp=_now(), exception_summary=str(exc))
        state.transition_stage("REGRESSION_OOF", "FAILED", timestamp=_now(), exception_summary=str(exc)); state.transition("FAILED", timestamp=_now(), failure_stage="REGRESSION_OOF", exception_summary=str(exc)); state_store.persist(state); raise


def _synthetic_data(contract: FrozenContract) -> RegressionData:
    rng = np.random.default_rng(20260728); ntrain, nval, ncal, nheld, nineligible = 24, 16, 16, 100, 28; total = ntrain + nval + ncal + nheld + nineligible
    X = rng.normal(size=(total, 150)); X[:, MATERIAL_TOKEN_INDICES] = rng.integers(0, 3, size=(total, len(MATERIAL_TOKEN_INDICES))); weights = rng.normal(size=(150, 4)); y = X @ weights / 25 + rng.normal(scale=0.05, size=(total, 4))
    ids=[]; groups=[]; roles=[]; folds=[]; round1=[]; eligible=[]; reasons=[]; masks=[]; provenance=[]
    for index in range(total):
        if index < ntrain: role, fold, r1, ok = "train", -1, False, True
        elif index < ntrain + nval: role, fold, r1, ok = "validation", -1, False, True
        elif index < ntrain + nval + ncal: role, fold, r1, ok = "calibration", -1, False, True
        elif index < ntrain + nval + ncal + nheld:
            fold=(index - ntrain - nval - ncal) // 25; role=f"round1_eligible_fold_{fold}"; r1=True; ok=True
        else:
            fold=(index - ntrain - nval - ncal - nheld) // 7; role=f"round1_ineligible_fold_{fold}"; r1=True; ok=False; y[index]=np.nan
        ids.append(("ROUND1:" if r1 else "SYNTH:") + f"{index:04d}"); groups.append("group:" + ids[-1]); roles.append(role); folds.append(fold); round1.append(r1); eligible.append(ok); reasons.append("eligible" if ok else "nominal_4d_objective_eligible=false"); masks.append("{\"all\":true}" if ok else "{\"all\":false}"); provenance.append("synthetic_fixture")
    metadata = RegressionMetadata(tuple(ids), tuple(hashlib.sha256(value.encode()).hexdigest() for value in ids), tuple(groups), tuple(roles), tuple(folds), tuple(round1), tuple(eligible), tuple(reasons), tuple(masks), tuple(provenance), contract.feature_signature, {"round1_count": 128, "round1_eligible_count": 100, "round1_ineligible_count": 28})
    return RegressionData(X.astype(np.float32), y.astype(np.float32), metadata)


def synthetic_regression_fixture(contract: FrozenContract, output_root: Path, run_id: str, *, fail_once: bool = True) -> dict[str, Any]:
    output_root = output_root.resolve()
    if str(ROOT.resolve()).lower() in str(output_root).lower(): raise ValueError("FIXTURE_OUTPUT_ROOT_MUST_BE_OUTSIDE_WORKTREE")
    root = output_root / run_id; data = _synthetic_data(contract); store = AtomicArtifactStore(ArtifactPolicy.fixture(root, worktree_root=ROOT, formal_output_root=contract.output_root), run_id=run_id, signature_bundle=contract.signatures); state_store = AtomicExecutionStateStore(root)
    failure = (1, 20260722); completed_before = []
    try:
        run_regression_crossfit(data, contract, store, state_store=state_store, failure_injection=failure if fail_once else None)
    except RuntimeError as exc:
        if "FIXTURE_FAILURE_INJECTION" not in str(exc): raise
        for seed in SEEDS[:2]:
            path = store.root / _seed_paths(1, seed)[0]
            if path.exists(): completed_before.append((path, sha256_file(path), path.stat().st_mtime_ns))
    failed = state_store.load(); result = run_regression_crossfit(data, contract, store, state_store=state_store, resume=True, failure_injection=None)
    preserved = all(sha256_file(path) == checksum and path.stat().st_mtime_ns == mtime for path, checksum, mtime in completed_before)
    fold = result["plans"][0]; bundles = [joblib.load(store.root / _seed_paths(0, seed)[0]) for seed in SEEDS]; held = data.X[list(fold.held_out_indices)]; calibration = data.X[list(fold.calibration_indices)]; held_seed = np.stack([_predict(bundle, held) for bundle in bundles]); calibration_seed = np.stack([_predict(bundle, calibration) for bundle in bundles]); quantiles = np.asarray(json.loads((store.root / "folds" / "fold_0" / "conformal.json").read_text(encoding="utf8"))["quantiles"])
    inputs = root / "fresh_input.npz"; np.savez(inputs, held=held, calibration=calibration); expected = {"parent_pid": os.getpid(), "seed_signatures": [sha256_value(np.round(held_seed[index], 12).tolist()) for index in range(3)], "ensemble_signature": sha256_value(np.round(held_seed.mean(axis=0), 12).tolist()), "interval_signature": sha256_value(np.round(np.stack((held_seed.mean(axis=0)-quantiles, held_seed.mean(axis=0)+quantiles)), 12).tolist()), "eligibility_signature": _signature(data.metadata.sample_ids[index] for index, flag in enumerate(data.metadata.eligible) if flag and data.metadata.is_round1[index]), "ineligibility_signature": _signature(data.metadata.sample_ids[index] for index, flag in enumerate(data.metadata.eligible) if not flag and data.metadata.is_round1[index])}
    expected["seed_signatures"] = [_array_signature(held_seed[index]) for index in range(3)]
    expected["ensemble_signature"] = _array_signature(held_seed.mean(axis=0))
    expected["interval_signature"] = _array_signature(np.stack((held_seed.mean(axis=0) - quantiles, held_seed.mean(axis=0) + quantiles)))
    expected_path=root / "fresh_expected.json"; expected_path.write_text(json.dumps(expected, sort_keys=True), encoding="utf8"); worker=root / "fresh_process_result_v1.json"; env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUNBUFFERED": "1"}; command=[sys.executable, "-m", "mdc_ml.merge_retrain_v1.regression_fresh_process", "--fixture-root", str(root), "--input-npz", str(inputs), "--expected-json", str(expected_path), "--result-json", str(worker)]; child=subprocess.run(command, capture_output=True, text=True, env=env); (root / "fresh_process_stdout.log").write_text(child.stdout, encoding="utf8"); (root / "fresh_process_stderr.log").write_text(child.stderr, encoding="utf8"); fresh=json.loads(worker.read_text(encoding="utf8")) if worker.exists() else {"status":"FAIL"}
    drift_path=store.root / _seed_paths(0, SEEDS[0])[0]; original=drift_path.read_bytes(); drift_path.write_bytes(original+b"X"); drift_guard=False
    try: run_regression_crossfit(data, contract, store, state_store=state_store, resume=True)
    except RuntimeError: drift_guard=True
    drift_path.write_bytes(original)
    artifact_hashes=[sha256_file(store.root / _seed_paths(fold_id, seed)[0]) for fold_id in range(4) for seed in SEEDS]
    audit={"schema_version": SCHEMA_VERSION, "fixture_run_id": run_id, "contract_signature_bundle": result["state"].signature_bundle().as_dict(), "fixture_max_epochs": 3, "fixture_coverage": FIXTURE_COVERAGE, "formal_conformal_coverage_parameter_pending_contract": True, "synthetic_regression_fit_calls": 12, "formal_regression_fit_calls": 0, "formal_regression_oof_calls": 0, "formal_training_calls": 0, "sealed_test_target_reads": 0, "sealed_test_prediction_calls": 0, "formal_output_write_count": 0, "TMM_calls": 0, "FDTD_calls": 0, "Lumerical_calls": 0, "failure_injection_executed": failed.status == "FAILED", "failed_state_observed": failed.status == "FAILED", "resume_executed": True, "completed_seed_sha_mtime_preserved": preserved, "artifact_drift_guard_pass": drift_guard, "state_checkpoint_count": len(list((root / "state" / "checkpoints").glob("*.json"))), "top_level_final_status": result["state"].status, "regression_stage_final_status": result["state"].stages["REGRESSION_OOF"].status, "sample_oof_rows": result["checks"]["sample_rows"], "target_oof_rows": result["checks"]["target_rows"], "seed_target_oof_rows": result["checks"]["seed_target_rows"], "ineligible_rows": result["checks"]["ineligible_rows"], "ineligible_prediction_count": result["checks"]["ineligible_prediction_count"], "exact_once": result["checks"]["exact_once"], "independent_seed_artifacts": len(set(artifact_hashes)) > 1, "fresh_process_return_code": child.returncode, "fresh_process": fresh, "final_status": "PASS" if all([failed.status == "FAILED", preserved, drift_guard, result["state"].status == "PARTIAL", result["checks"]["exact_once"], len(set(artifact_hashes)) > 1, child.returncode == 0, fresh.get("all_match", False)]) else "FAIL"}
    record=store.write_json("regression_fixture_audit_v1.json", audit, artifact_type="regression_fixture_audit", producer_stage="REGRESSION_OOF", producer_unit="fixture")
    return {"status": audit["final_status"], "fixture_run_id": run_id, "audit_path": str(store.root / "regression_fixture_audit_v1.json"), "audit_sha256": record.sha256, "audit": audit}
