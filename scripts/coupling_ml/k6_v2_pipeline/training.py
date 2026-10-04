"""V2 grouped-CV fit planner, train-only model fitting, and resumable artifacts.

This module performs no solver work. Importing it does not train. Call the staged
executor only after development truth is admitted and the frozen plan is audited.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from statistics import median
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import joblib
import numpy as np

from .contracts import (
    CaseCollection,
    CaseTruth,
    DATASET_AUTHORITY_SHA256,
    DEVELOPMENT_ROLES,
    H1_AUTHORITY_SHA256,
    H2_DECODER_SHA256,
    PHYSICAL_CONTRACT_SHA256,
    ROLE_GLOBAL_DEV,
    ROLE_LOCAL_AXIS,
    ROLE_OLD32,
    V2_AMENDMENT_01_SHA256,
    V2_BASE_PROTOCOL_SHA256,
    V2_CANDIDATE_CSV_SHA256,
    V2_FOLD_MANIFEST_SHA256,
    V2_INNER_FOLD_MANIFEST_SHA256,
    V2_LEARNING_CURVE_MANIFEST_SHA256,
    pack_model_target,
)
from .models import (
    EXPECTED_MLP_PARAMETERS,
    KRR_GAMMAS,
    KRR_RIDGE_ALPHAS,
    MLP_EARLY_STOP_MIN_DELTA,
    MLP_EARLY_STOP_PATIENCE,
    MLP_MAX_UPDATES,
    MLP_SEEDS,
    MLP_WEIGHT_DECAYS,
    CartesianMLP,
    GeometryStandardizer,
    RBFKRR,
    V2TargetNormalizer,
    mlp_loss_components,
    mlp_parameter_count,
    numpy_loss_components,
    unpack_prediction,
)

PROTOCOL_RELATIVE_DIR = Path("reports/coupling/COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2")
V1_PROTOCOL_RELATIVE_PATH = Path("reports/coupling/COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1/PREREGISTERED_PROTOCOL_V1.json")
G0_PROTOCOL_RELATIVE_PATH = Path("reports/coupling/COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1/protocol.json")
V1_PROTOCOL_SHA256 = "e18ea780917107c437d425293ff1da5628241221197e889cc22696e90d242abd"
G0_PROTOCOL_SHA256 = "a4c13a28b4c95533fcbc32c8944603d47eaf3c5423baca4060353055bf1517dc"
REFIT_POLICY = "V1 frozen rule inherited by V2 Amendment 01: per-seed floor-median inner best update; 3 inner folds for each outer-fold refit and all available selected inner best updates for final all-160 refit."
SEED_AGGREGATION = "Per-seed C_hat complex arithmetic mean; per-seed P_scale inverse-normalized, exp-transformed, then arithmetic mean in positive physical P_scale domain."
INNER_EARLY_STOP_RULE = "minimum mean normalized L_C+L_P; patience=50, min_delta=1e-5, earliest-step tie; maximum 1000 full-geometry updates."
EXPECTED_TOTAL_FITS = 281
FIT_BUDGET_CEILING = 284
SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"
PRODUCTION = "PRODUCTION"
ENGINEERING_DIAGNOSTIC = "ENGINEERING_DIAGNOSTIC"
_ENGINEERING_DIAGNOSTIC_AUTHORITY = object()
_REAL32_DIAGNOSTIC_TRAIN_IDS = (
    "K6V1_EXT01", "K6V1_EXT02", "K6V1_S02", "K6V1_EXT04",
    "K6V1_S37", "K6V1_S31", "K6V1_EXT13", "K6V1_S33",
    "K6V1_S39", "K6V1_S47", "K6V1_S32", "K6V1_S21",
    "K6V1_S04", "K6V1_S15", "K6V1_S48", "K6V1_EXT12",
    "K6V1_EXT08", "K6V1_EXT03", "K6V1_S35", "K6V1_EXT10",
    "K6V1_EXT06", "K6V1_EXT14", "K6V1_S36", "K6V1_EXT09",
)
_REAL32_DIAGNOSTIC_VALIDATION_IDS = (
    "K6V1_S45", "K6V1_S16", "K6V1_S05", "K6V1_EXT07",
    "K6V1_EXT05", "K6V1_EXT11", "K6V1_S42", "K6V1_S03",
)


@dataclass(frozen=True)
class FitTask:
    task_id: str
    phase: str
    model_kind: str
    outer_fold: Optional[int]
    inner_fold: Optional[int]
    training_geometry_count: int
    train_case_ids: Tuple[str, ...]
    prediction_case_ids: Tuple[str, ...] = ()
    gamma: Optional[float] = None
    ridge_alpha: Optional[float] = None
    weight_decay: Optional[float] = None
    seed: Optional[int] = None
    fixed_updates: Optional[int] = None
    config_source: Optional[str] = None
    update_source: Optional[str] = None

    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_engineering_diagnostic_task(task: FitTask) -> None:
    if (task.phase != "engineering_diagnostic" or task.outer_fold is not None
            or task.inner_fold is not None or task.training_geometry_count != 24
            or tuple(task.train_case_ids) != _REAL32_DIAGNOSTIC_TRAIN_IDS
            or tuple(task.prediction_case_ids) != _REAL32_DIAGNOSTIC_VALIDATION_IDS
            or set(task.train_case_ids) & set(task.prediction_case_ids)
            or task.config_source != "DIAGNOSTIC_CONFIGS_V1.json"
            or task.update_source != "frozen_24_8_median_grid_rule"):
        raise ValueError("real32_engineering_diagnostic_task_identity_mismatch")
    if task.model_kind == "RBF_KRR":
        valid = (task.task_id == "real32_diag_krr_seed3208"
                 and task.gamma == 1.0 / 3.0 and task.ridge_alpha == 1e-2
                 and task.weight_decay is None and task.seed is None
                 and task.fixed_updates is None)
    elif task.model_kind == "CARTESIAN_MLP":
        valid = (task.task_id == "real32_diag_mlp_s0_seed3208"
                 and task.gamma is None and task.ridge_alpha is None
                 and task.weight_decay == 1e-4 and task.seed == 0
                 and task.fixed_updates is None)
    else:
        valid = False
    if not valid:
        raise ValueError("real32_engineering_diagnostic_config_mismatch")


@dataclass(frozen=True)
class FitCounts:
    inner_krr: int
    inner_mlp: int
    learning_curve_krr: int
    learning_curve_mlp: int
    final_global: int
    local_affine: int
    total: int

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class FitPlan:
    repository_root: str
    development_case_ids: Tuple[str, ...]
    development_role_by_id: Mapping[str, str]
    geometry_by_id: Mapping[str, Tuple[int, ...]]
    outer_validation_ids: Mapping[int, Tuple[str, ...]]
    inner_tasks: Tuple[FitTask, ...]
    curve_templates: Tuple[FitTask, ...]
    final_templates: Tuple[FitTask, ...]
    local_tasks: Tuple[FitTask, ...]
    counts: FitCounts
    source_hashes: Mapping[str, str]

    def to_summary(self) -> Dict[str, Any]:
        return {
            "schema": "COUPLING_ML_K6_V2_FIT_PLAN_V1",
            "development_geometry_count": len(self.development_case_ids),
            "outer_folds": sorted(self.outer_validation_ids),
            "learning_curve_training_sizes": [32, 64, 128],
            "inner_tasks": len(self.inner_tasks),
            "curve_tasks": len(self.curve_templates),
            "final_tasks": len(self.final_templates),
            "local_tasks": len(self.local_tasks),
            "counts": self.counts.to_dict(),
            "fit_ceiling": FIT_BUDGET_CEILING,
            "protocol_sources": dict(self.source_hashes),
            "refit_policy": REFIT_POLICY,
            "seed_aggregation": SEED_AGGREGATION,
            "confirmation_responses_opened": False,
            "truth_fits_executed": 0,
        }


@dataclass
class FitRun:
    task: FitTask
    model: Any
    x_scaler: GeometryStandardizer
    target_scaler: V2TargetNormalizer
    input_sha256: str
    training_loss: float
    validation_loss: Optional[float]
    best_update: int
    actual_updates: int
    history: List[Dict[str, float]] = field(default_factory=list)
    prediction_case_ids: Tuple[str, ...] = ()
    predicted_c_hat: Optional[np.ndarray] = None
    predicted_p_scale: Optional[np.ndarray] = None
    synthetic_test_only: bool = False
    resumed_from_update: int = 0
    resume_count: int = 0
    optimizer_updates_this_invocation: int = 0
    replayed_optimizer_updates: int = 0


@dataclass(frozen=True)
class InnerSelection:
    outer_fold: int
    krr_gamma: float
    krr_alpha: float
    mlp_weight_decay: float
    mlp_updates_by_seed: Mapping[int, int]
    krr_mean_validation_loss: float
    mlp_mean_validation_loss: float


_RESOLVED_REFIT_AUTHORITY = object()


@dataclass(frozen=True)
class ResolvedRefits:
    curve_tasks: Tuple[FitTask, ...]
    final_tasks: Tuple[FitTask, ...]
    outer_selections: Mapping[int, InnerSelection]
    final_krr_gamma: float
    final_krr_alpha: float
    final_mlp_weight_decay: float
    final_mlp_updates_by_seed: Mapping[int, int]
    _authority: Any = field(default=None, repr=False, compare=False)


_SYNTHETIC_TEST_FIT_COUNTS = {"RBF_KRR": 0, "CARTESIAN_MLP": 0}


def reset_synthetic_test_fit_counts() -> None:
    for key in _SYNTHETIC_TEST_FIT_COUNTS:
        _SYNTHETIC_TEST_FIT_COUNTS[key] = 0


def synthetic_test_fit_counts() -> Dict[str, int]:
    return dict(_SYNTHETIC_TEST_FIT_COUNTS)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _require_hash(path: Path, expected: str, label: str, hashes: Dict[str, str]) -> None:
    actual = _sha256(path)
    if actual.lower() != expected.lower():
        raise ValueError(f"frozen_{label}_sha256_mismatch:{actual}")
    hashes[label] = actual


def _geometry_from_row(row: Mapping[str, str]) -> Tuple[int, ...]:
    return tuple(int(row[f"D{i}_nm"]) for i in range(1, 7))


def _candidate_role_map(rows: Sequence[Mapping[str, str]]):
    role, geometry, order = {}, {}, []
    for row in rows:
        case_id = row["case_id"]
        if case_id in role:
            raise ValueError(f"duplicate_candidate_case_id:{case_id}")
        role[case_id] = row["role"]
        geometry[case_id] = _geometry_from_row(row)
        order.append(case_id)
    return role, geometry, order


def build_fit_plan(repository_root: Optional[Path] = None) -> FitPlan:
    """Read only frozen geometry/fold manifests and compile the exact fit schedule."""
    root = Path(repository_root) if repository_root else Path(__file__).resolve().parents[3]
    proto = root / PROTOCOL_RELATIVE_DIR
    hashes: Dict[str, str] = {}
    _require_hash(proto / "REVISED_PREREGISTERED_PROTOCOL_V2.json", V2_BASE_PROTOCOL_SHA256, "v2_base_protocol", hashes)
    _require_hash(proto / "REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json", V2_AMENDMENT_01_SHA256, "v2_amendment_01", hashes)
    _require_hash(proto / "GLOBAL_DATASET_CANDIDATES_V2.csv", V2_CANDIDATE_CSV_SHA256, "candidate_csv", hashes)
    _require_hash(proto / "DEVELOPMENT_FOLD_MANIFEST_V2.csv", V2_FOLD_MANIFEST_SHA256, "outer_fold_manifest", hashes)
    _require_hash(proto / "INNER_FOLD_MANIFEST_V2.csv", V2_INNER_FOLD_MANIFEST_SHA256, "inner_fold_manifest", hashes)
    _require_hash(proto / "LEARNING_CURVE_SUBSET_MANIFEST_V2.csv", V2_LEARNING_CURVE_MANIFEST_SHA256, "learning_curve_manifest", hashes)
    _require_hash(root / V1_PROTOCOL_RELATIVE_PATH, V1_PROTOCOL_SHA256, "inherited_v1_protocol", hashes)
    _require_hash(root / G0_PROTOCOL_RELATIVE_PATH, G0_PROTOCOL_SHA256, "g0_training_precedent", hashes)

    candidate_rows = _read_csv(proto / "GLOBAL_DATASET_CANDIDATES_V2.csv")
    candidate_roles, geometry, candidate_order = _candidate_role_map(candidate_rows)
    role_counts = {}
    for role in candidate_roles.values():
        role_counts[role] = role_counts.get(role, 0) + 1
    if role_counts != {
        ROLE_LOCAL_AXIS: 12,
        ROLE_GLOBAL_DEV: 116,
        "SEALED_LOCAL_COMBINATION": 4,
        "SEALED_CONFIRMATION_GLOBAL": 28,
    }:
        raise ValueError(f"frozen_candidate_role_counts_mismatch:{role_counts}")
    new_development = [
        case_id for case_id in candidate_order
        if candidate_roles[case_id] in (ROLE_LOCAL_AXIS, ROLE_GLOBAL_DEV)
    ]
    if len(new_development) != 128 or len(set(new_development)) != 128:
        raise ValueError("frozen_new_development_count_or_identity_mismatch")

    outer_rows = _read_csv(proto / "DEVELOPMENT_FOLD_MANIFEST_V2.csv")
    outer_val_by_fold: Dict[int, List[str]] = {i: [] for i in range(1, 5)}
    for row in outer_rows:
        fold = int(row["outer_fold"])
        case_id = row["case_id"]
        if fold not in outer_val_by_fold or case_id not in candidate_roles:
            raise ValueError("outer_fold_manifest_unknown_fold_or_case")
        if row["role"] != candidate_roles[case_id] or case_id not in new_development:
            raise ValueError("outer_fold_manifest_role_or_pool_mismatch")
        if geometry[case_id] != _geometry_from_row(row):
            raise ValueError(f"outer_fold_geometry_mismatch:{case_id}")
        if row["all_21_wavelengths_grouped"].lower() != "true":
            raise ValueError(f"outer_fold_wavelength_grouping_false:{case_id}")
        outer_val_by_fold[fold].append(case_id)
    if any(len(ids) != 32 for ids in outer_val_by_fold.values()):
        raise ValueError("outer_fold_must_hold_32_new_geometry_groups")
    if set().union(*(set(v) for v in outer_val_by_fold.values())) != set(new_development):
        raise ValueError("outer_folds_do_not_partition_new_development")

    lc_rows = _read_csv(proto / "LEARNING_CURVE_SUBSET_MANIFEST_V2.csv")
    lc_by_fold_size: Dict[Tuple[int, int], List[str]] = {}
    old32_ids = set()
    for row in lc_rows:
        fold, size = int(row["outer_fold"]), int(row["training_geometry_count"])
        case_id = row["case_id"]
        if fold not in range(1, 5) or size not in (32, 64, 128):
            raise ValueError("learning_curve_manifest_invalid_fold_or_size")
        ids = lc_by_fold_size.setdefault((fold, size), [])
        ids.append(case_id)
        if row["all_21_wavelengths_grouped"].lower() != "true":
            raise ValueError(f"learning_curve_wavelength_grouping_false:{case_id}")
        if row["role"] == "EXISTING32_TRAIN_ONLY":
            old32_ids.add(case_id)
            if case_id not in geometry:
                geometry[case_id] = _geometry_from_row(row)
                candidate_roles[case_id] = ROLE_OLD32
            elif geometry[case_id] != _geometry_from_row(row):
                raise ValueError(f"old32_geometry_conflict:{case_id}")
    if len(old32_ids) != 32:
        raise ValueError("expected_exactly_32_existing_development_geometries")

    new_fold_of_case = {cid: fold for fold, ids in outer_val_by_fold.items() for cid in ids}
    for fold in range(1, 5):
        pool128 = lc_by_fold_size.get((fold, 128), [])
        pool64 = lc_by_fold_size.get((fold, 64), [])
        pool32 = lc_by_fold_size.get((fold, 32), [])
        expected_pool = old32_ids | {cid for cid, assigned in new_fold_of_case.items() if assigned != fold}
        if len(pool128) != 128 or set(pool128) != expected_pool:
            raise ValueError(f"outer_train_pool_not_128_or_wrong_membership:{fold}")
        if len(pool32) != 32 or set(pool32) != old32_ids:
            raise ValueError(f"learning_size32_not_actual_existing32:{fold}")
        new64 = set(pool64) - old32_ids
        new128 = set(pool128) - old32_ids
        if len(pool64) != 64 or set(pool64) & old32_ids != old32_ids or len(new64) != 32:
            raise ValueError(f"learning_size64_count_or_composition_mismatch:{fold}")
        if not set(pool32) <= set(pool64) <= set(pool128) or not new64 <= new128:
            raise ValueError(f"learning_curve_subsets_not_nested:{fold}")
        if len(new128) != 96:
            raise ValueError(f"outer_fold_new_train_count_not_96:{fold}")

    inner_rows = _read_csv(proto / "INNER_FOLD_MANIFEST_V2.csv")
    inner_val_by_fold: Dict[Tuple[int, int], List[str]] = {}
    inner_all_by_outer: Dict[int, List[str]] = {i: [] for i in range(1, 5)}
    for row in inner_rows:
        outer, inner, case_id = int(row["outer_fold"]), int(row["inner_fold"]), row["case_id"]
        if outer not in range(1, 5) or inner not in range(1, 4):
            raise ValueError("inner_fold_manifest_invalid_fold")
        if row["all_21_wavelengths_grouped"].lower() != "true":
            raise ValueError(f"inner_fold_wavelength_grouping_false:{case_id}")
        if row["role"] == "EXISTING32_TRAIN_ONLY":
            old32_ids.add(case_id)
            candidate_roles[case_id] = ROLE_OLD32
            geometry[case_id] = _geometry_from_row(row)
        else:
            if case_id not in candidate_roles or row["role"] != candidate_roles[case_id]:
                raise ValueError(f"inner_fold_role_mismatch:{case_id}")
            if geometry[case_id] != _geometry_from_row(row):
                raise ValueError(f"inner_fold_geometry_mismatch:{case_id}")
        inner_val_by_fold.setdefault((outer, inner), []).append(case_id)
        inner_all_by_outer[outer].append(case_id)
    for outer in range(1, 5):
        expected_pool = set(lc_by_fold_size[(outer, 128)])
        if set(inner_all_by_outer[outer]) != expected_pool or len(inner_all_by_outer[outer]) != 128:
            raise ValueError(f"inner_folds_do_not_cover_outer_train_pool:{outer}")
        val_union = set()
        for inner in range(1, 4):
            vals = inner_val_by_fold.get((outer, inner), [])
            if not vals or val_union.intersection(vals):
                raise ValueError(f"inner_validation_partition_invalid:{outer}:{inner}")
            val_union.update(vals)
        if val_union != expected_pool:
            raise ValueError(f"inner_folds_not_disjoint_partition:{outer}")

    dev_ids = tuple(sorted(old32_ids | set(new_development)))
    if len(dev_ids) != 160:
        raise ValueError("development_pool_must_contain_160_geometry_groups")
    development_roles = {cid: candidate_roles[cid] for cid in dev_ids}
    if any(r not in DEVELOPMENT_ROLES for r in development_roles.values()):
        raise ValueError("non_development_role_in_frozen_training_pool")

    inner_tasks: List[FitTask] = []
    curve_templates: List[FitTask] = []
    final_templates: List[FitTask] = []
    local_tasks: List[FitTask] = []
    for outer in range(1, 5):
        pool_order = lc_by_fold_size[(outer, 128)]
        for inner in range(1, 4):
            val_ids = tuple(inner_val_by_fold[(outer, inner)])
            train_ids = tuple(cid for cid in pool_order if cid not in set(val_ids))
            if set(train_ids) & set(val_ids) or len(train_ids) + len(val_ids) != 128:
                raise ValueError(f"inner_train_validation_overlap_or_count:{outer}:{inner}")
            for gamma in KRR_GAMMAS:
                for alpha in KRR_RIDGE_ALPHAS:
                    inner_tasks.append(FitTask(
                        task_id=f"inner_o{outer}_i{inner}_krr_g{gamma:.8g}_a{alpha:.8g}",
                        phase="inner", model_kind="RBF_KRR", outer_fold=outer,
                        inner_fold=inner, training_geometry_count=len(train_ids),
                        train_case_ids=train_ids, prediction_case_ids=val_ids,
                        gamma=gamma, ridge_alpha=alpha,
                    ))
            for wd in MLP_WEIGHT_DECAYS:
                for seed in MLP_SEEDS:
                    inner_tasks.append(FitTask(
                        task_id=f"inner_o{outer}_i{inner}_mlp_wd{wd:.8g}_s{seed}",
                        phase="inner", model_kind="CARTESIAN_MLP", outer_fold=outer,
                        inner_fold=inner, training_geometry_count=len(train_ids),
                        train_case_ids=train_ids, prediction_case_ids=val_ids,
                        weight_decay=wd, seed=seed,
                    ))
        for size in (32, 64, 128):
            train_ids = tuple(lc_by_fold_size[(outer, size)])
            predict_ids = tuple(outer_val_by_fold[outer])
            curve_templates.append(FitTask(
                task_id=f"curve_o{outer}_n{size}_krr", phase="learning_curve",
                model_kind="RBF_KRR", outer_fold=outer, inner_fold=None,
                training_geometry_count=size, train_case_ids=train_ids,
                prediction_case_ids=predict_ids, config_source=f"outer_{outer}_inner_selection",
            ))
            for seed in MLP_SEEDS:
                curve_templates.append(FitTask(
                    task_id=f"curve_o{outer}_n{size}_mlp_s{seed}", phase="learning_curve",
                    model_kind="CARTESIAN_MLP", outer_fold=outer, inner_fold=None,
                    training_geometry_count=size, train_case_ids=train_ids,
                    prediction_case_ids=predict_ids, seed=seed,
                    config_source=f"outer_{outer}_inner_selection",
                    update_source=f"outer_{outer}_per_seed_inner_best_median",
                ))
    for gamma in (None,):
        final_templates.append(FitTask(
            task_id="final_all160_krr", phase="final", model_kind="RBF_KRR",
            outer_fold=None, inner_fold=None, training_geometry_count=160,
            train_case_ids=dev_ids, config_source="mode_of_four_outer_selected_configs",
        ))
    for seed in MLP_SEEDS:
        final_templates.append(FitTask(
            task_id=f"final_all160_mlp_s{seed}", phase="final",
            model_kind="CARTESIAN_MLP", outer_fold=None, inner_fold=None,
            training_geometry_count=160, train_case_ids=dev_ids, seed=seed,
            config_source="mode_of_four_outer_selected_weight_decay",
            update_source="per_seed_floor_median_of_selected_inner_best_updates_across_4x3_folds",
        ))

    local_ids = [cid for cid in candidate_order if candidate_roles[cid] == ROLE_LOCAL_AXIS]
    if len(local_ids) != 12:
        raise ValueError("local_affine_requires_exactly_12_frozen_axis_cases")
    for held_out in local_ids:
        local_tasks.append(FitTask(
            task_id=f"local_loo_{held_out}", phase="local_leave_one_axial_out",
            model_kind="LOCAL_AFFINE", outer_fold=None, inner_fold=None,
            training_geometry_count=11, train_case_ids=tuple(cid for cid in local_ids if cid != held_out),
            prediction_case_ids=(held_out,),
        ))
    local_tasks.append(FitTask(
        task_id="local_final_all12", phase="local_final",
        model_kind="LOCAL_AFFINE", outer_fold=None, inner_fold=None,
        training_geometry_count=12, train_case_ids=tuple(local_ids),
    ))

    counts = FitCounts(
        inner_krr=sum(t.model_kind == "RBF_KRR" for t in inner_tasks),
        inner_mlp=sum(t.model_kind == "CARTESIAN_MLP" for t in inner_tasks),
        learning_curve_krr=sum(t.model_kind == "RBF_KRR" for t in curve_templates),
        learning_curve_mlp=sum(t.model_kind == "CARTESIAN_MLP" for t in curve_templates),
        final_global=len(final_templates),
        local_affine=len(local_tasks),
        total=len(inner_tasks) + len(curve_templates) + len(final_templates) + len(local_tasks),
    )
    if counts.to_dict() != {
        "inner_krr": 108, "inner_mlp": 108, "learning_curve_krr": 12,
        "learning_curve_mlp": 36, "final_global": 4, "local_affine": 13, "total": 281,
    }:
        raise ValueError(f"frozen_fit_budget_mismatch:{counts.to_dict()}")
    if counts.total > FIT_BUDGET_CEILING:
        raise ValueError("frozen_fit_budget_exceeded")
    hashes.update({
        "physical_contract": PHYSICAL_CONTRACT_SHA256,
        "dataset_authority": DATASET_AUTHORITY_SHA256,
        "h1_authority": H1_AUTHORITY_SHA256,
        "h2_decoder": H2_DECODER_SHA256,
    })
    return FitPlan(
        repository_root=str(root), development_case_ids=dev_ids,
        development_role_by_id=development_roles, geometry_by_id=geometry,
        outer_validation_ids={f: tuple(ids) for f, ids in outer_val_by_fold.items()},
        inner_tasks=tuple(inner_tasks), curve_templates=tuple(curve_templates),
        final_templates=tuple(final_templates), local_tasks=tuple(local_tasks),
        counts=counts, source_hashes=hashes,
    )


def _mode(values: Sequence[Any], tie_key):
    counts: Dict[Any, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    maximum = max(counts.values())
    tied = [value for value, count in counts.items() if count == maximum]
    return sorted(tied, key=tie_key)[0]


def floor_median_updates(steps: Sequence[int]) -> int:
    if not steps or any(int(s) < 1 or int(s) > MLP_MAX_UPDATES for s in steps):
        raise ValueError("invalid_inner_best_update_values")
    return int(math.floor(float(median([int(s) for s in steps]))))


def resolve_refit_tasks(plan: FitPlan, inner_runs: Sequence[FitRun]) -> ResolvedRefits:
    """Resolve CV configs and per-seed epochs without inspecting outer-val truth."""
    by_key = {}
    expected_by_id = {t.task_id: t for t in plan.inner_tasks}
    expected = set(expected_by_id)
    seen = set()
    for run in inner_runs:
        task = run.task
        if (task.task_id not in expected or task.phase != "inner"
                or task != expected_by_id.get(task.task_id) or run.synthetic_test_only):
            raise ValueError("inner_selection_received_unauthorized_inner_fit")
        if task.task_id in seen or run.validation_loss is None:
            raise ValueError("inner_selection_duplicate_or_missing_validation_loss")
        seen.add(task.task_id)
        by_key[(task.outer_fold, task.inner_fold, task.model_kind, task.gamma,
                task.ridge_alpha, task.weight_decay, task.seed)] = run
    if seen != expected:
        raise ValueError(f"inner_selection_missing_fits:{len(expected - seen)}")

    selections: Dict[int, InnerSelection] = {}
    for outer in range(1, 5):
        krr_scores = {}
        for gamma in KRR_GAMMAS:
            for alpha in KRR_RIDGE_ALPHAS:
                losses = [by_key[(outer, inner, "RBF_KRR", gamma, alpha, None, None)].validation_loss
                          for inner in range(1, 4)]
                krr_scores[(gamma, alpha)] = float(np.mean(losses))
        best_krr = sorted(krr_scores, key=lambda cfg: (krr_scores[cfg], cfg[0], -cfg[1]))[0]

        mlp_scores = {}
        for wd in MLP_WEIGHT_DECAYS:
            losses = [by_key[(outer, inner, "CARTESIAN_MLP", None, None, wd, seed)].validation_loss
                      for inner in range(1, 4) for seed in MLP_SEEDS]
            mlp_scores[wd] = float(np.mean(losses))
        best_wd = sorted(mlp_scores, key=lambda wd: (mlp_scores[wd], -wd))[0]
        updates = {
            seed: floor_median_updates([
                by_key[(outer, inner, "CARTESIAN_MLP", None, None, best_wd, seed)].best_update
                for inner in range(1, 4)
            ])
            for seed in MLP_SEEDS
        }
        selections[outer] = InnerSelection(
            outer_fold=outer, krr_gamma=best_krr[0], krr_alpha=best_krr[1],
            mlp_weight_decay=best_wd, mlp_updates_by_seed=updates,
            krr_mean_validation_loss=krr_scores[best_krr],
            mlp_mean_validation_loss=mlp_scores[best_wd],
        )

    final_krr = _mode(
        [(s.krr_gamma, s.krr_alpha) for s in selections.values()],
        tie_key=lambda cfg: (cfg[0], -cfg[1]),
    )
    final_wd = _mode(
        [s.mlp_weight_decay for s in selections.values()], tie_key=lambda wd: -wd
    )
    final_updates = {}
    for seed in MLP_SEEDS:
        steps = []
        for outer in range(1, 5):
            chosen_wd = selections[outer].mlp_weight_decay
            for inner in range(1, 4):
                steps.append(by_key[(outer, inner, "CARTESIAN_MLP", None, None,
                                     chosen_wd, seed)].best_update)
        final_updates[seed] = floor_median_updates(steps)

    curves = []
    for template in plan.curve_templates:
        outer = template.outer_fold
        assert outer is not None
        selection = selections[outer]
        if template.model_kind == "RBF_KRR":
            curves.append(replace(
                template, gamma=selection.krr_gamma, ridge_alpha=selection.krr_alpha,
                config_source=f"outer_{outer}_inner_cv_min_mean_loss",
            ))
        else:
            assert template.seed is not None
            curves.append(replace(
                template, weight_decay=selection.mlp_weight_decay,
                fixed_updates=selection.mlp_updates_by_seed[template.seed],
                config_source=f"outer_{outer}_inner_cv_min_mean_loss",
                update_source=f"outer_{outer}_seed{template.seed}_floor_median_3_inner_best",
            ))
    finals = []
    for template in plan.final_templates:
        if template.model_kind == "RBF_KRR":
            finals.append(replace(
                template, gamma=final_krr[0], ridge_alpha=final_krr[1],
                config_source="mode_of_four_outer_selected_configs_tie_small_gamma_large_alpha",
            ))
        else:
            assert template.seed is not None
            finals.append(replace(
                template, weight_decay=final_wd,
                fixed_updates=final_updates[template.seed],
                config_source="mode_of_four_outer_selected_weight_decay_tie_largest",
                update_source=f"seed{template.seed}_floor_median_selected_inner_best_4x3",
            ))
    return ResolvedRefits(
        curve_tasks=tuple(curves), final_tasks=tuple(finals),
        outer_selections=selections, final_krr_gamma=final_krr[0],
        final_krr_alpha=final_krr[1], final_mlp_weight_decay=final_wd,
        final_mlp_updates_by_seed=final_updates,
        _authority=_RESOLVED_REFIT_AUTHORITY,
    )


def seed_mean_predictions(seed_predictions: Sequence[Tuple[np.ndarray, np.ndarray]]):
    """Mean complex C_hat and mean positive physical P_scale, never mean log outputs."""
    if not seed_predictions:
        raise ValueError("seed_predictions_empty")
    c = np.stack([np.asarray(x[0], dtype=np.complex128) for x in seed_predictions], axis=0)
    p = np.stack([np.asarray(x[1], dtype=np.float64) for x in seed_predictions], axis=0)
    if not np.isfinite(c.real).all() or not np.isfinite(c.imag).all():
        raise ValueError("seed_c_hat_nonfinite")
    if not np.isfinite(p).all() or (p <= 0.0).any():
        raise ValueError("seed_p_scale_must_be_finite_positive")
    c_mean = np.mean(c, axis=0)
    p_mean = np.mean(p, axis=0, dtype=np.float64)
    if not np.isfinite(p_mean).all() or (p_mean <= 0.0).any():
        raise ValueError("seed_mean_p_scale_invalid")
    return c_mean, p_mean


def arrays_from_cases(cases: Sequence[CaseTruth]):
    if not cases:
        raise ValueError("case_subset_empty")
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_case_id_in_fit_subset")
    X = np.asarray([c.ordered_D_nm for c in cases], dtype=np.float64)
    if X.shape != (len(cases), 6) or not np.isfinite(X).all():
        raise ValueError("ordered_geometry_matrix_invalid")
    Y = np.concatenate([pack_model_target(c.c_hat, c.p_scale) for c in cases], axis=0)
    return X, Y


def _cpu_state_dict(state):
    """Copy module tensors to CPU so the atomic progress checkpoint is portable."""
    return {key: value.detach().cpu().clone() for key, value in state.items()}


def _restore_mlp_rng_state(payload, device: str) -> None:
    import torch
    random.setstate(payload["python_rng_state"])
    np.random.set_state(payload["numpy_rng_state"])
    torch.set_rng_state(payload["torch_cpu_rng_state"].cpu())
    saved_cuda = payload.get("torch_cuda_rng_states")
    if device.startswith("cuda"):
        if saved_cuda is None or not torch.cuda.is_available():
            raise ValueError("mlp_progress_checkpoint_cuda_rng_mismatch")
        if len(saved_cuda) != torch.cuda.device_count():
            raise ValueError("mlp_progress_checkpoint_cuda_device_count_mismatch")
        torch.cuda.set_rng_state_all([state.cpu() for state in saved_cuda])


def _save_mlp_progress_checkpoint(
    path: Path, *, task: FitTask, input_sha256: str, device: str,
    completed_updates: int, model, optimizer, best_state, best_update: int,
    best_val: float, stale: int, early_stopped: bool, history,
    resume_count: int,
) -> None:
    """Atomically commit model, optimizer, RNG and trajectory after one update."""
    import torch
    path = Path(path)
    cuda_states = torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
    payload = {
        "schema": "COUPLING_ML_K6_V2_MLP_PROGRESS_V1",
        "task_sha256": task.fingerprint(),
        "input_sha256": input_sha256,
        "device": str(device),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "completed_updates": int(completed_updates),
        "model_state": _cpu_state_dict(model.state_dict()),
        "optimizer_state": optimizer.state_dict(),
        "best_state": None if best_state is None else _cpu_state_dict(best_state),
        "best_update": int(best_update),
        "best_val": float(best_val),
        "stale": int(stale),
        "early_stopped": bool(early_stopped),
        "history": list(history),
        "resume_count": int(resume_count),
        "python_rng_state": random.getstate(),
        "numpy_rng_state": np.random.get_state(),
        "torch_cpu_rng_state": torch.get_rng_state().cpu(),
        "torch_cuda_rng_states": cuda_states,
    }

    def write_checkpoint(tmp: Path) -> None:
        with tmp.open("wb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())

    _atomic_write_bytes(path, write_checkpoint)


def _load_mlp_progress_checkpoint(
    path: Path, *, task: FitTask, input_sha256: str, device: str,
):
    import torch
    try:
        payload = torch.load(Path(path), map_location=device, weights_only=False)
    except Exception as exc:
        raise RuntimeError("mlp_progress_checkpoint_unreadable") from exc
    if (payload.get("schema") != "COUPLING_ML_K6_V2_MLP_PROGRESS_V1"
            or payload.get("task_sha256") != task.fingerprint()
            or payload.get("input_sha256") != input_sha256
            or payload.get("device") != str(device)
            or payload.get("cuda_device_count", 0)
                != (torch.cuda.device_count() if torch.cuda.is_available() else 0)):
        raise ValueError("mlp_progress_checkpoint_provenance_mismatch")
    return payload


def fit_arrays(
    task: FitTask,
    X_train: np.ndarray,
    Y_train: np.ndarray,
    *,
    X_validation: Optional[np.ndarray] = None,
    Y_validation: Optional[np.ndarray] = None,
    X_prediction: Optional[np.ndarray] = None,
    prediction_case_ids: Sequence[str] = (),
    device: str = "cpu",
    run_purpose: str = PRODUCTION,
    checkpoint_path: Optional[Path] = None,
    after_optimizer_update: Optional[Callable[[int], None]] = None,
) -> FitRun:
    """Public raw-array entry point, restricted to synthetic implementation tests."""
    if run_purpose != SYNTHETIC_TEST_ONLY:
        raise ValueError("public_array_fitting_is_synthetic_test_only")
    return _fit_arrays_impl(
        task, X_train, Y_train, X_validation=X_validation, Y_validation=Y_validation,
        X_prediction=X_prediction, prediction_case_ids=prediction_case_ids,
        device=device, run_purpose=SYNTHETIC_TEST_ONLY,
        checkpoint_path=checkpoint_path, after_optimizer_update=after_optimizer_update,
    )


def _fit_arrays_impl(
    task: FitTask,
    X_train: np.ndarray,
    Y_train: np.ndarray,
    *,
    X_validation: Optional[np.ndarray] = None,
    Y_validation: Optional[np.ndarray] = None,
    X_prediction: Optional[np.ndarray] = None,
    prediction_case_ids: Sequence[str] = (),
    device: str = "cpu",
    run_purpose: str = PRODUCTION,
    checkpoint_path: Optional[Path] = None,
    after_optimizer_update: Optional[Callable[[int], None]] = None,
    _scheduled_authorized: bool = False,
    _engineering_diagnostic_authority: Any = None,
) -> FitRun:
    """Internal fit implementation; production calls require scheduled authority."""
    if (run_purpose == PRODUCTION) != bool(_scheduled_authorized):
        raise ValueError("raw_array_production_fit_requires_scheduled_authority")
    if run_purpose == ENGINEERING_DIAGNOSTIC:
        if _engineering_diagnostic_authority is not _ENGINEERING_DIAGNOSTIC_AUTHORITY:
            raise ValueError("engineering_diagnostic_requires_scoped_authority")
        _validate_engineering_diagnostic_task(task)
    elif _engineering_diagnostic_authority is not None:
        raise ValueError("engineering_diagnostic_authority_used_for_wrong_purpose")
    if task.model_kind not in ("RBF_KRR", "CARTESIAN_MLP"):
        raise ValueError("fit_arrays_only_supports_frozen_global_models")
    if run_purpose not in (PRODUCTION, SYNTHETIC_TEST_ONLY, ENGINEERING_DIAGNOSTIC):
        raise ValueError("unknown_fit_purpose")
    if after_optimizer_update is not None and (
            run_purpose != SYNTHETIC_TEST_ONLY
            or task.model_kind != "CARTESIAN_MLP"
            or checkpoint_path is None):
        raise ValueError("optimizer_update_callback_requires_synthetic_mlp_checkpoint")
    if checkpoint_path is not None and task.model_kind != "CARTESIAN_MLP":
        raise ValueError("progress_checkpoints_are_mlp_only")
    if run_purpose == SYNTHETIC_TEST_ONLY:
        _SYNTHETIC_TEST_FIT_COUNTS[task.model_kind] += 1
    xtr = np.asarray(X_train, dtype=np.float64)
    ytr = np.asarray(Y_train, dtype=np.float64)
    if xtr.shape != (task.training_geometry_count, 6) or ytr.shape != (len(xtr), 609):
        raise ValueError("fit_training_array_shape_mismatch")
    if not np.isfinite(xtr).all() or not np.isfinite(ytr).all():
        raise ValueError("fit_training_array_nonfinite")
    if task.phase in ("inner", "engineering_diagnostic"):
        if X_validation is None or Y_validation is None:
            raise ValueError("inner_fit_requires_grouped_validation")
    elif task.phase in ("learning_curve", "final"):
        if task.model_kind == "CARTESIAN_MLP" and task.fixed_updates is None:
            raise ValueError("refit_requires_inner_selected_fixed_update_count")
        if Y_validation is not None:
            raise ValueError("refit_must_not_use_outer_validation_truth_for_selection")
    else:
        raise ValueError("unsupported_fit_phase")

    x_scaler = GeometryStandardizer.fit(xtr)
    y_scaler = V2TargetNormalizer.fit(ytr)
    xn = x_scaler.transform(xtr)
    yn = y_scaler.transform(ytr)
    xv = None if X_validation is None else x_scaler.transform(X_validation)
    yv = None if Y_validation is None else y_scaler.transform(Y_validation)
    xp = None if X_prediction is None else x_scaler.transform(X_prediction)
    if xv is not None and (yv is None or len(xv) != len(yv)):
        raise ValueError("fit_validation_geometry_target_mismatch")
    x_hash = hashlib.sha256()
    x_hash.update(json.dumps({"task": asdict(task)}, sort_keys=True, separators=(",", ":")).encode())
    for arr in (xtr, ytr, X_validation, Y_validation, X_prediction):
        if arr is not None:
            a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
            x_hash.update(str(a.shape).encode("ascii"))
            x_hash.update(a.tobytes())
    input_sha = x_hash.hexdigest()

    history: List[Dict[str, float]] = []
    best_update = 0
    actual_updates = 0
    validation_loss: Optional[float] = None
    resumed_from_update = 0
    resume_count = 0
    optimizer_updates_this_invocation = 0
    if task.model_kind == "RBF_KRR":
        if task.gamma is None or task.ridge_alpha is None:
            raise ValueError("krr_task_missing_frozen_grid_config")
        model = RBFKRR(task.gamma, task.ridge_alpha).fit(xn, yn)
        train_pred = model.predict(xn)
        train_loss = numpy_loss_components(train_pred, yn)[2]
        if xv is not None:
            validation_loss = numpy_loss_components(model.predict(xv), yv)[2]
    else:
        import torch
        from .models import MLP_MAX_UPDATES, MLP_EARLY_STOP_PATIENCE, MLP_EARLY_STOP_MIN_DELTA
        if task.seed not in MLP_SEEDS or task.weight_decay not in MLP_WEIGHT_DECAYS:
            raise ValueError("mlp_task_outside_frozen_seed_or_decay_grid")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("requested_cuda_device_unavailable")
        random.seed(task.seed)
        np.random.seed(task.seed)
        torch.manual_seed(task.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(task.seed)
        model = CartesianMLP(task.seed).to(device)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=1e-3, weight_decay=task.weight_decay
        )
        xt = torch.as_tensor(xn, dtype=torch.float32, device=device)
        yt = torch.as_tensor(yn, dtype=torch.float32, device=device)
        xvt = None if xv is None else torch.as_tensor(xv, dtype=torch.float32, device=device)
        yvt = None if yv is None else torch.as_tensor(yv, dtype=torch.float32, device=device)
        early = task.phase in ("inner", "engineering_diagnostic")
        max_updates = MLP_MAX_UPDATES if early else int(task.fixed_updates or 0)
        if max_updates < 1 or max_updates > MLP_MAX_UPDATES:
            raise ValueError("mlp_update_count_outside_frozen_budget")
        best_val = float("inf")
        best_state = None
        stale = 0
        early_stopped = False
        train_loss = float("nan")
        if checkpoint_path is not None and Path(checkpoint_path).exists():
            progress = _load_mlp_progress_checkpoint(
                Path(checkpoint_path), task=task, input_sha256=input_sha, device=device,
            )
            model.load_state_dict(progress["model_state"])
            optimizer.load_state_dict(progress["optimizer_state"])
            history = list(progress["history"])
            actual_updates = int(progress["completed_updates"])
            resumed_from_update = actual_updates
            resume_count = int(progress.get("resume_count", 0)) + 1
            best_state = progress["best_state"]
            best_update = int(progress["best_update"])
            best_val = float(progress["best_val"])
            stale = int(progress["stale"])
            early_stopped = bool(progress["early_stopped"])
            _restore_mlp_rng_state(progress, device)
        if actual_updates < 0 or actual_updates > max_updates or len(history) != actual_updates:
            raise ValueError("mlp_progress_checkpoint_update_history_mismatch")
        if history and int(history[-1]["step"]) != actual_updates:
            raise ValueError("mlp_progress_checkpoint_update_history_mismatch")
        if best_update < 0 or best_update > actual_updates:
            raise ValueError("mlp_progress_checkpoint_best_update_mismatch")
        start_step = max_updates + 1 if early_stopped else actual_updates + 1
        for step in range(start_step, max_updates + 1):
            model.train()
            optimizer.zero_grad(set_to_none=True)
            before = [p.detach().clone() for p in model.parameters()]
            pred = model(xt)
            c_loss, p_loss, loss = mlp_loss_components(pred, yt)
            loss.backward()
            grad_sq = sum(float(torch.sum(p.grad.detach() ** 2).item()) for p in model.parameters())
            grad_norm = math.sqrt(grad_sq)
            optimizer.step()
            update_sq = sum(float(torch.sum((p.detach() - old) ** 2).item())
                            for p, old in zip(model.parameters(), before))
            update_norm = math.sqrt(update_sq)
            model.eval()
            with torch.no_grad():
                trp = model(xt)
                tlc, tlp, tloss = mlp_loss_components(trp, yt)
                if xvt is not None:
                    vpred = model(xvt)
                    vlc, vlp, vloss = mlp_loss_components(vpred, yvt)
                    vvalue = float(vloss.item())
                else:
                    vlc = vlp = vloss = None
                    vvalue = None
            train_loss = float(tloss.item())
            record = {
                "step": float(step), "train_c_loss": float(tlc.item()),
                "train_log_p_loss": float(tlp.item()), "train_loss": train_loss,
                "gradient_norm": grad_norm, "update_norm": update_norm,
            }
            if vvalue is not None:
                record.update({
                    "validation_c_loss": float(vlc.item()),
                    "validation_log_p_loss": float(vlp.item()),
                    "validation_loss": vvalue,
                })
            history.append(record)
            actual_updates = step
            if early:
                if vvalue is None:
                    raise ValueError("inner_mlp_validation_missing")
                if vvalue < best_val - MLP_EARLY_STOP_MIN_DELTA:
                    best_val = vvalue
                    best_update = step
                    best_state = _cpu_state_dict(model.state_dict())
                    stale = 0
                else:
                    stale += 1
                early_stopped = stale >= MLP_EARLY_STOP_PATIENCE
            if checkpoint_path is not None:
                _save_mlp_progress_checkpoint(
                    Path(checkpoint_path), task=task, input_sha256=input_sha,
                    device=device, completed_updates=step, model=model,
                    optimizer=optimizer, best_state=best_state, best_update=best_update,
                    best_val=best_val, stale=stale, early_stopped=early_stopped,
                    history=history, resume_count=resume_count,
                )
            if after_optimizer_update is not None:
                after_optimizer_update(step)
            optimizer_updates_this_invocation += 1
            if early_stopped:
                break
        if early:
            if best_state is None:
                raise RuntimeError("mlp_early_stop_never_selected_checkpoint")
            model.load_state_dict(best_state)
            validation_loss = best_val
        else:
            best_update = max_updates
        model = model.to("cpu")
        if xv is not None:
            # This is an inner validation metric only; outer fold truth is never passed here.
            xt_eval = torch.as_tensor(xv, dtype=torch.float32)
            model.eval()
            with torch.no_grad():
                pred_eval = model(xt_eval).cpu().numpy().astype(np.float64)
            if early:
                validation_loss = numpy_loss_components(pred_eval, yv)[2]
        # Recompute normalized train loss from the selected/final checkpoint.
        model.eval()
        with torch.no_grad():
            train_pred = model(torch.as_tensor(xn, dtype=torch.float32)).cpu().numpy().astype(np.float64)
        train_loss = numpy_loss_components(train_pred, yn)[2]

    if task.model_kind == "RBF_KRR":
        if xv is not None:
            validation_loss = numpy_loss_components(model.predict(xv), yv)[2]
    pred_raw = None
    c_pred = p_pred = None
    if xp is not None and len(prediction_case_ids):
        if task.model_kind == "RBF_KRR":
            pred_norm = model.predict(xp)
        else:
            import torch
            model.eval()
            with torch.no_grad():
                pred_norm = model(torch.as_tensor(xp, dtype=torch.float32)).cpu().numpy().astype(np.float64)
        pred_raw = y_scaler.inverse_transform(pred_norm)
        c_pred, p_pred = unpack_prediction(pred_raw)
        if len(c_pred) != len(prediction_case_ids):
            raise ValueError("prediction_case_id_count_mismatch")
    return FitRun(
        task=task, model=model, x_scaler=x_scaler, target_scaler=y_scaler,
        input_sha256=input_sha, training_loss=train_loss,
        validation_loss=validation_loss, best_update=best_update,
        actual_updates=actual_updates, history=history,
        prediction_case_ids=tuple(prediction_case_ids),
        predicted_c_hat=c_pred, predicted_p_scale=p_pred,
        synthetic_test_only=(run_purpose == SYNTHETIC_TEST_ONLY),
        resumed_from_update=resumed_from_update, resume_count=resume_count,
        optimizer_updates_this_invocation=optimizer_updates_this_invocation,
        replayed_optimizer_updates=0,
    )


def predict_fit_run(run: FitRun, X: np.ndarray):
    """Predict raw Cartesian C_hat and physical positive P_scale for geometry-only rows."""
    x = _matrix6(X)
    xn = run.x_scaler.transform(x)
    if run.task.model_kind == "RBF_KRR":
        yn = run.model.predict(xn)
    elif run.task.model_kind == "CARTESIAN_MLP":
        import torch
        run.model.eval()
        with torch.no_grad():
            yn = run.model(torch.as_tensor(xn, dtype=torch.float32)).cpu().numpy().astype(np.float64)
    else:
        raise ValueError("unsupported_model_for_geometry_prediction")
    return unpack_prediction(run.target_scaler.inverse_transform(yn))


def _matrix6(X):
    x = np.asarray(X, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 6 or len(x) == 0 or not np.isfinite(x).all():
        raise ValueError("prediction_geometry_must_be_finite_Nx6")
    return x


def _validate_development_case_map(case_map: Mapping[str, CaseTruth], plan: FitPlan):
    """Validate only IDs, roles and ordered geometry before any response is read."""
    expected = set(plan.development_case_ids)
    actual = set(case_map)
    if actual != expected:
        missing, extra = sorted(expected - actual), sorted(actual - expected)
        raise ValueError(f"development_case_allowlist_mismatch:missing={missing[:5]}:extra={extra[:5]}")
    for case_id in plan.development_case_ids:
        case = case_map[case_id]
        if getattr(case, "case_id", None) != case_id:
            raise ValueError(f"development_case_key_identity_mismatch:{case_id}")
        expected_role = plan.development_role_by_id[case_id]
        if getattr(case, "role", None) != expected_role:
            raise ValueError(f"development_case_role_mismatch:{case_id}")
        try:
            geometry = np.asarray(case.ordered_D_nm, dtype=np.float64)
        except Exception as exc:
            raise ValueError(f"development_ordered_geometry_invalid:{case_id}") from exc
        expected_geometry = np.asarray(plan.geometry_by_id[case_id], dtype=np.float64)
        if (geometry.shape != (6,) or not np.isfinite(geometry).all()
                or not np.array_equal(geometry, expected_geometry)):
            raise ValueError(f"development_ordered_geometry_mismatch:{case_id}")
    return case_map


def _development_case_map(collection: CaseCollection, plan: FitPlan):
    cases = collection.training_cases()
    by_id = {c.case_id: c for c in cases}
    if len(by_id) != len(cases):
        raise ValueError("duplicate_case_id_in_development_collection")
    _validate_development_case_map(by_id, plan)
    return by_id


def _fit_plan_signature(plan: FitPlan) -> str:
    payload = {
        "development_case_ids": list(plan.development_case_ids),
        "development_role_by_id": dict(sorted(plan.development_role_by_id.items())),
        "geometry_by_id": {k: list(v) for k, v in sorted(plan.geometry_by_id.items())},
        "outer_validation_ids": {str(k): list(v) for k, v in sorted(plan.outer_validation_ids.items())},
        "inner_tasks": [asdict(t) for t in plan.inner_tasks],
        "curve_templates": [asdict(t) for t in plan.curve_templates],
        "final_templates": [asdict(t) for t in plan.final_templates],
        "local_tasks": [asdict(t) for t in plan.local_tasks],
        "source_hashes": dict(sorted(plan.source_hashes.items())),
        "counts": plan.counts.to_dict(),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_scheduled_task(task: FitTask, plan: FitPlan, refit_authorization=None) -> None:
    if task.phase == "inner":
        expected = {candidate.task_id: candidate for candidate in plan.inner_tasks}
        if expected.get(task.task_id) != task:
            raise ValueError("scheduled_inner_task_not_in_frozen_plan")
        return
    if task.phase not in ("learning_curve", "final"):
        raise ValueError("scheduled_task_phase_not_authorized")

    templates = plan.curve_templates if task.phase == "learning_curve" else plan.final_templates
    template = next((candidate for candidate in templates if candidate.task_id == task.task_id), None)
    if template is None:
        raise ValueError("scheduled_refit_task_id_not_in_frozen_plan")
    common_fields = (
        "task_id", "phase", "model_kind", "outer_fold", "inner_fold",
        "training_geometry_count", "train_case_ids", "prediction_case_ids", "seed",
    )
    if any(getattr(task, name) != getattr(template, name) for name in common_fields):
        raise ValueError("scheduled_refit_task_template_fields_mismatch")

    if task.model_kind == "RBF_KRR":
        if (task.gamma not in KRR_GAMMAS or task.ridge_alpha not in KRR_RIDGE_ALPHAS
                or task.weight_decay is not None or task.fixed_updates is not None
                or task.update_source is not None):
            raise ValueError("scheduled_krr_config_outside_frozen_selection")
        expected_config = (
            f"outer_{task.outer_fold}_inner_cv_min_mean_loss"
            if task.phase == "learning_curve"
            else "mode_of_four_outer_selected_configs_tie_small_gamma_large_alpha"
        )
    elif task.model_kind == "CARTESIAN_MLP":
        if (task.gamma is not None or task.ridge_alpha is not None
                or task.weight_decay not in MLP_WEIGHT_DECAYS
                or task.fixed_updates is None
                or not 1 <= task.fixed_updates <= MLP_MAX_UPDATES):
            raise ValueError("scheduled_mlp_config_outside_frozen_selection")
        expected_config = (
            f"outer_{task.outer_fold}_inner_cv_min_mean_loss"
            if task.phase == "learning_curve"
            else "mode_of_four_outer_selected_weight_decay_tie_largest"
        )
        expected_update_source = (
            f"outer_{task.outer_fold}_seed{task.seed}_floor_median_3_inner_best"
            if task.phase == "learning_curve"
            else "per_seed_floor_median_of_selected_inner_best_updates_across_4x3_folds"
        )
        if task.update_source != expected_update_source:
            raise ValueError("scheduled_mlp_update_source_mismatch")
    else:
        raise ValueError("scheduled_model_kind_not_authorized")
    if task.config_source != expected_config:
        raise ValueError("scheduled_task_config_source_mismatch")

    if not isinstance(refit_authorization, ResolvedRefits) or (
            refit_authorization._authority is not _RESOLVED_REFIT_AUTHORITY):
        raise ValueError("scheduled_refit_requires_inner_cv_resolution")
    authorized = (
        refit_authorization.curve_tasks if task.phase == "learning_curve"
        else refit_authorization.final_tasks
    )
    selected = next((candidate for candidate in authorized if candidate.task_id == task.task_id), None)
    if selected is None or selected != task:
        raise ValueError("scheduled_refit_task_not_in_inner_cv_resolution")


def _task_cases_to_arrays(by_id: Mapping[str, CaseTruth], ids: Sequence[str], include_target: bool):
    cases = []
    for case_id in ids:
        case = by_id[case_id]
        if case.role not in DEVELOPMENT_ROLES:
            raise ValueError(f"non_development_case_requested_by_fit:{case_id}")
        cases.append(case)
    X = np.asarray([c.ordered_D_nm for c in cases], dtype=np.float64)
    if X.shape != (len(cases), 6) or not np.isfinite(X).all():
        raise ValueError("fit_case_geometry_invalid")
    if include_target:
        Y = np.concatenate([pack_model_target(c.c_hat, c.p_scale) for c in cases], axis=0)
        return X, Y
    return X


def _atomic_write_bytes(path: Path, writer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        writer(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_fit_task(
    task: FitTask,
    case_map: Mapping[str, CaseTruth],
    artifact_root: Path,
    *,
    device: str = "cpu",
    resume: bool = True,
    run_purpose: str = PRODUCTION,
    refit_authorization: Optional[ResolvedRefits] = None,
) -> FitRun:
    """Run only a fresh-plan task with development-only cases and CV authorization."""
    if run_purpose != PRODUCTION:
        raise ValueError("scheduled_case_fit_path_is_production_only")
    if task.model_kind not in ("RBF_KRR", "CARTESIAN_MLP"):
        raise ValueError("local_affine_tasks_are_owned_by_local_diagnostic_module")
    fresh_plan = build_fit_plan()
    _validate_scheduled_task(task, fresh_plan, refit_authorization)
    _validate_development_case_map(case_map, fresh_plan)
    Xtr, Ytr = _task_cases_to_arrays(case_map, task.train_case_ids, include_target=True)
    Xval = Yval = None
    if task.phase == "inner":
        Xval, Yval = _task_cases_to_arrays(case_map, task.prediction_case_ids, include_target=True)
    Xpred = None
    if task.prediction_case_ids:
        Xpred = _task_cases_to_arrays(case_map, task.prediction_case_ids, include_target=False)
    digest = hashlib.sha256()
    digest.update(task.fingerprint().encode("ascii"))
    for arr in (Xtr, Ytr, Xval, Yval, Xpred):
        if arr is not None:
            contiguous = np.ascontiguousarray(arr, dtype=np.float64)
            digest.update(str(contiguous.shape).encode("ascii"))
            digest.update(contiguous.tobytes())
    data_sha = digest.hexdigest()
    output_dir = Path(artifact_root) / task.task_id
    if resume and run_purpose == PRODUCTION:
        cached = _load_cached_fit(task, output_dir, data_sha)
        if cached is not None:
            return cached
    try:
        run = _fit_arrays_impl(
            task, Xtr, Ytr, X_validation=Xval, Y_validation=Yval,
            X_prediction=Xpred, prediction_case_ids=task.prediction_case_ids if Xpred is not None else (),
            device=device, run_purpose=PRODUCTION, _scheduled_authorized=True,
            checkpoint_path=(output_dir / "progress.pt"
                             if task.model_kind == "CARTESIAN_MLP" else None),
        )
        run.input_sha256 = data_sha
        if run_purpose == PRODUCTION:
            _save_fit_run(run, output_dir, data_sha)
        return run
    except Exception as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        failure = {
            "schema": "COUPLING_ML_K6_V2_FIT_FAILURE_V1",
            "status": "FAILED_RETRY_SAME_TASK",
            "task": asdict(task), "task_sha256": task.fingerprint(),
            "data_sha256": data_sha, "error_type": type(exc).__name__,
            "error": str(exc), "protocol_sources": dict((
                ("v1_protocol_sha256", V1_PROTOCOL_SHA256),
                ("g0_protocol_sha256", G0_PROTOCOL_SHA256),
                ("v2_base_sha256", V2_BASE_PROTOCOL_SHA256),
                ("v2_amendment_01_sha256", V2_AMENDMENT_01_SHA256),
            )),
        }
        (output_dir / "failure.json").write_text(json.dumps(failure, sort_keys=True, indent=2), encoding="utf-8")
        raise


def execute_global_pipeline(
    collection: CaseCollection,
    plan: FitPlan,
    artifact_root: Path,
    *,
    device: str = "cpu",
    resume: bool = True,
):
    """Execute only the preregistered 268 global fits; returns local tasks unexecuted."""
    fresh_plan = build_fit_plan()
    if _fit_plan_signature(plan) != _fit_plan_signature(fresh_plan):
        raise ValueError("caller_fit_plan_differs_from_fresh_frozen_plan")
    plan = fresh_plan
    by_id = _development_case_map(collection, plan)
    if mlp_parameter_count() != EXPECTED_MLP_PARAMETERS:
        raise RuntimeError("frozen_mlp_parameter_count_mismatch")
    inner_runs = [
        run_fit_task(task, by_id, Path(artifact_root) / "inner", device=device, resume=resume)
        for task in plan.inner_tasks
    ]
    resolved = resolve_refit_tasks(plan, inner_runs)
    refit_runs = [
        run_fit_task(
            task, by_id, Path(artifact_root) / task.phase, device=device, resume=resume,
            refit_authorization=resolved,
        )
        for task in (*resolved.curve_tasks, *resolved.final_tasks)
    ]
    return {
        "inner_runs": inner_runs,
        "refit_runs": refit_runs,
        "resolved": resolved,
        "local_tasks_not_executed": plan.local_tasks,
        "planned_global_fits": len(plan.inner_tasks) + len(plan.curve_templates) + len(plan.final_templates),
        "actual_global_fit_tasks": len(inner_runs) + len(refit_runs),
        "production_fit_count": len(inner_runs) + len(refit_runs),
    }


def predict_mlp_seed_ensemble(runs: Sequence[FitRun], X: np.ndarray):
    """Mean C_hat complex coordinates and positive physical P_scale across 3 seeds."""
    if len(runs) != 3 or any(r.task.model_kind != "CARTESIAN_MLP" for r in runs):
        raise ValueError("mlp_ensemble_requires_exactly_three_mlp_seed_fits")
    if sorted(r.task.seed for r in runs) != list(MLP_SEEDS):
        raise ValueError("mlp_ensemble_seed_set_mismatch")
    signatures = {
        (r.task.phase, r.task.outer_fold, r.task.training_geometry_count, r.task.weight_decay)
        for r in runs
    }
    if len(signatures) != 1:
        raise ValueError("mlp_ensemble_fit_protocol_mismatch")
    ordered = sorted(runs, key=lambda r: int(r.task.seed))
    predictions = [predict_fit_run(run, X) for run in ordered]
    c_mean, p_mean = seed_mean_predictions(predictions)
    return c_mean, p_mean, {
        "method": SEED_AGGREGATION,
        "seed_order": list(MLP_SEEDS),
        "p_scale_domain": "positive_physical_after_individual_exp",
    }


# Hash-checked fit checkpoints: cached results require matching provenance and artifact bytes.
def _save_fit_run(run: FitRun, output_dir: Path, data_sha: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    hist_path = output_dir / "trajectory.json"
    history_bytes = json.dumps(run.history, sort_keys=True, allow_nan=False).encode("utf-8")
    _atomic_write_bytes(hist_path, lambda tmp: tmp.write_bytes(history_bytes))
    pred_path = output_dir / "predictions.npz"
    if run.predicted_c_hat is not None and run.predicted_p_scale is not None:
        def write_predictions(tmp: Path) -> None:
            with tmp.open("wb") as stream:
                np.savez_compressed(
                    stream, case_ids=np.asarray(run.prediction_case_ids, dtype="U"),
                    c_hat=run.predicted_c_hat, p_scale=run.predicted_p_scale)
        _atomic_write_bytes(pred_path, write_predictions)
        pred_sha = _sha256(pred_path)
    else:
        pred_sha = None
    model_path = output_dir / "fit.joblib"
    _atomic_write_bytes(model_path, lambda tmp: joblib.dump(run, tmp, compress=3))
    progress_path = output_dir / "progress.pt"
    progress_sha = _sha256(progress_path) if progress_path.exists() else None
    metadata = {
        "schema": "COUPLING_ML_K6_V2_FIT_CHECKPOINT_V1",
        "status": "COMPLETE",
        "task": asdict(run.task),
        "task_sha256": run.task.fingerprint(),
        "input_sha256": run.input_sha256,
        "data_sha256": data_sha,
        "artifact_sha256": {
            "fit.joblib": _sha256(model_path),
            "trajectory.json": _sha256(hist_path),
            "predictions.npz": pred_sha,
            "progress.pt": progress_sha,
        },
        "training_loss": run.training_loss,
        "validation_loss": run.validation_loss,
        "best_update": run.best_update,
        "actual_updates": run.actual_updates,
        "resume": {
            "resumed_from_update": run.resumed_from_update,
            "resume_count": run.resume_count,
            "optimizer_updates_this_invocation": run.optimizer_updates_this_invocation,
            "replayed_optimizer_updates": run.replayed_optimizer_updates,
            "checkpoint_interval_updates": 1,
            "atomic_progress_checkpoint": run.task.model_kind == "CARTESIAN_MLP",
        },
        "synthetic_test_only": run.synthetic_test_only,
        "normalization": {"geometry": run.x_scaler.to_dict(),
                          "target": run.target_scaler.to_dict()},
        "protocol_sources": {
            "v1_protocol_sha256": V1_PROTOCOL_SHA256,
            "g0_protocol_sha256": G0_PROTOCOL_SHA256,
            "v2_base_sha256": V2_BASE_PROTOCOL_SHA256,
            "v2_amendment_01_sha256": V2_AMENDMENT_01_SHA256,
        },
        "refit_policy": REFIT_POLICY,
        "seed_aggregation": SEED_AGGREGATION,
    }
    payload = json.dumps(metadata, sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    _atomic_write_bytes(output_dir / "fit_manifest.json", lambda tmp: tmp.write_bytes(payload))


def _load_cached_fit(task: FitTask, output_dir: Path, data_sha: str) -> Optional[FitRun]:
    manifest = output_dir / "fit_manifest.json"
    model_path = output_dir / "fit.joblib"
    if not manifest.exists() and not model_path.exists():
        return None
    if not manifest.exists() or not model_path.exists():
        raise ValueError(f"incomplete_fit_checkpoint_requires_review:{task.task_id}")
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    artifacts = meta.get("artifact_sha256", {})
    paths = {"fit.joblib": model_path, "trajectory.json": output_dir / "trajectory.json"}
    pred_sha = artifacts.get("predictions.npz")
    if pred_sha is not None:
        paths["predictions.npz"] = output_dir / "predictions.npz"
    progress_sha = artifacts.get("progress.pt")
    if progress_sha is not None:
        paths["progress.pt"] = output_dir / "progress.pt"
    hashes_match = all(path.exists() and artifacts.get(name) == _sha256(path)
                       for name, path in paths.items())
    if (meta.get("status") != "COMPLETE"
            or meta.get("task_sha256") != task.fingerprint()
            or meta.get("data_sha256") != data_sha
            or not hashes_match):
        raise ValueError(f"fit_checkpoint_provenance_mismatch:{task.task_id}")
    run = joblib.load(model_path)
    if not isinstance(run, FitRun) or run.task.fingerprint() != task.fingerprint():
        raise ValueError(f"fit_checkpoint_payload_mismatch:{task.task_id}")
    return run
