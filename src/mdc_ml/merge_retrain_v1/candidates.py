from __future__ import annotations

"""Frozen candidate specifications and strictly unfitted candidate construction."""

import dataclasses
import importlib.util
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge

from .contracts import (
    ROOT,
    CandidateSpec,
    FrozenContract,
    freeze,
    sha256_value,
    thaw,
)


_TREE_KEYS = ("n_estimators", "min_samples_leaf", "max_features")
_HGB_KEYS = ("max_iter", "learning_rate", "max_leaf_nodes", "l2_regularization")


@dataclass(frozen=True)
class UnfittedMLPEnsemble:
    prototype: Any
    bundles: tuple[Any, ...]
    seeds: tuple[int, ...]
    runtime_config: Mapping[str, Any]


def _load_shared_module() -> Any:
    path = ROOT / "scripts" / "train_mdc_ml_shared_surrogate_v1.py"
    spec = importlib.util.spec_from_file_location("_mdc_shared_v1_candidate_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("SHARED_V1_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _items(contract: FrozenContract, kind: str) -> tuple[Mapping[str, Any], ...]:
    if kind == "classification":
        return contract.classification_allowlist
    if kind == "regression":
        return contract.regression_allowlist
    raise ValueError("UNKNOWN_CANDIDATE_KIND:" + kind)


def _bounded_ids(contract: FrozenContract, kind: str) -> tuple[str, ...]:
    return (
        contract.bounded_classification_ids
        if kind == "classification"
        else contract.bounded_regression_ids
    )


def _item(contract: FrozenContract, kind: str, candidate_id: str) -> Mapping[str, Any]:
    allowed = {str(item["candidate_id"]): item for item in _items(contract, kind)}
    if candidate_id not in allowed:
        raise ValueError("UNKNOWN_CANDIDATE:" + candidate_id)
    if candidate_id not in _bounded_ids(contract, kind):
        raise ValueError("CANDIDATE_OUTSIDE_BOUNDED_SET:" + candidate_id)
    return allowed[candidate_id]


def _runtime_projection(
    contract: FrozenContract,
    kind: str,
    item: Mapping[str, Any],
    target_index: int,
    seed: int,
) -> dict[str, Any]:
    family = str(item["estimator_family"])
    frozen = thaw(item["hyperparameters"])
    if family == "dummy_prevalence":
        return {"strategy": "prior"}
    if family == "dummy_stratified":
        return {"strategy": "stratified", "random_state": seed + target_index}
    if kind == "regression" and family == "dummy_mean":
        return {"strategy": "mean"}
    if kind == "regression" and family == "dummy_median":
        return {"strategy": "median"}
    if kind == "classification" and family == "linear":
        return {
            "C": frozen["C"],
            "class_weight": "balanced",
            "max_iter": 3000,
            "random_state": seed,
        }
    if kind == "regression" and family == "linear":
        return {"alpha": frozen["alpha"]}
    if family == "extra_trees":
        projection = {key: frozen[key] for key in _TREE_KEYS}
        projection.update({"n_jobs": 8, "random_state": seed + target_index})
        if kind == "classification":
            projection["class_weight"] = "balanced"
        return projection
    if family == "hist_gradient_boosting":
        projection = {key: frozen[key] for key in _HGB_KEYS}
        projection["random_state"] = seed + target_index
        return projection
    if family == "multitask_mlp":
        optimizer = frozen["optimizer"]
        return {
            "input_dim": contract.feature_count,
            "hidden": frozen["hidden_layers"],
            "dropout": frozen["dropout"],
            "learning_rate": optimizer["learning_rate"],
            "weight_decay": optimizer["weight_decay"],
            "batch_size": frozen["batch_size"],
            "max_epochs": frozen["max_epochs"],
            "patience": contract.early_stopping.patience,
            "seeds": list(contract.training_seeds["regressor_ensemble_seeds"]),
        }
    raise ValueError("UNSUPPORTED_FROZEN_ESTIMATOR_FAMILY:" + family)


def _candidate_spec(
    contract: FrozenContract,
    kind: str,
    item: Mapping[str, Any],
    target_index: int = 0,
    seed: int | None = None,
) -> CandidateSpec:
    if seed is None:
        seed = int(contract.training_seeds["classifier_candidate_seed"])
    source = item["source_reference"]
    full_snapshot = {
        key: thaw(value)
        for key, value in item.items()
        if key not in {"source_reference", "resolved_value_sha256"}
    }
    full_snapshot_sha = sha256_value(full_snapshot)
    if full_snapshot_sha != str(source["resolved_value_sha256"]):
        raise RuntimeError("CANDIDATE_FULL_SNAPSHOT_DRIFT:" + str(item["candidate_id"]))
    runtime = _runtime_projection(contract, kind, item, target_index, seed)
    payload = {
        "kind": kind,
        "candidate_id": item["candidate_id"],
        "estimator_family": item["estimator_family"],
        "estimator_class": item["estimator"],
        "frozen_hyperparameters": thaw(item["hyperparameters"]),
        "runtime_constructor_parameters": runtime,
        "random_state_rule": item["random_state_rule"],
        "preprocessing": item["preprocessing"],
        "source_commit": source["source_commit"],
        "source_path": source["source_path"],
        "source_symbol": source["source_key_or_symbol"],
        "source_sha256": source["source_sha256"],
        "resolved_value_sha256": item["resolved_value_sha256"],
        "full_snapshot_sha256": full_snapshot_sha,
        "runtime_projection_sha256": sha256_value(runtime),
    }
    frozen_payload = dict(payload)
    frozen_payload["frozen_hyperparameters"] = freeze(payload["frozen_hyperparameters"])
    frozen_payload["runtime_constructor_parameters"] = freeze(runtime)
    frozen_payload["candidate_spec_sha256"] = sha256_value(payload)
    return CandidateSpec(**frozen_payload)


def classification_specs(contract: FrozenContract) -> tuple[CandidateSpec, ...]:
    return tuple(_candidate_spec(contract, "classification", item) for item in _items(contract, "classification"))


def regression_specs(contract: FrozenContract) -> tuple[CandidateSpec, ...]:
    return tuple(_candidate_spec(contract, "regression", item) for item in _items(contract, "regression"))


def _build_sklearn(spec: CandidateSpec) -> Any:
    params = thaw(spec.runtime_constructor_parameters)
    constructors = {
        "sklearn.dummy.DummyClassifier": DummyClassifier,
        "sklearn.dummy.DummyRegressor": DummyRegressor,
        "sklearn.linear_model.LogisticRegression": LogisticRegression,
        "sklearn.linear_model.Ridge": Ridge,
        "sklearn.ensemble.ExtraTreesClassifier": ExtraTreesClassifier,
        "sklearn.ensemble.ExtraTreesRegressor": ExtraTreesRegressor,
        "sklearn.ensemble.HistGradientBoostingClassifier": HistGradientBoostingClassifier,
        "sklearn.ensemble.HistGradientBoostingRegressor": HistGradientBoostingRegressor,
    }
    if spec.estimator_class not in constructors:
        raise ValueError("NOT_A_SKLEARN_CANDIDATE:" + spec.candidate_id)
    return constructors[spec.estimator_class](**params)


def build_unfitted_classification_candidate(
    contract: FrozenContract,
    candidate_id: str,
    target_index: int,
    seed: int,
) -> Any:
    item = _item(contract, "classification", candidate_id)
    if item["estimator_family"] == "multitask_mlp":
        return build_unfitted_mlp_ensemble(contract, contract.feature_count)
    return _build_sklearn(_candidate_spec(contract, "classification", item, target_index, seed))


def build_unfitted_regression_candidate(
    contract: FrozenContract,
    candidate_id: str,
    target_index: int,
    seed: int,
) -> Any:
    item = _item(contract, "regression", candidate_id)
    if item["estimator_family"] == "multitask_mlp":
        return build_unfitted_mlp_ensemble(contract, contract.feature_count)
    return _build_sklearn(_candidate_spec(contract, "regression", item, target_index, seed))


def build_unfitted_mlp_ensemble(
    contract: FrozenContract,
    input_dim: int = 150,
) -> UnfittedMLPEnsemble:
    if input_dim != contract.feature_count:
        raise ValueError("MLP_INPUT_DIM_CONTRACT_MISMATCH")
    item = _item(contract, "regression", "multitask_mlp_3seed")
    spec = _candidate_spec(contract, "regression", item)
    runtime = thaw(spec.runtime_constructor_parameters)
    shared = _load_shared_module()
    mlp_config = {
        key: runtime[key]
        for key in (
            "hidden",
            "dropout",
            "learning_rate",
            "weight_decay",
            "batch_size",
            "max_epochs",
            "patience",
        )
    }
    seeds = tuple(int(seed) for seed in runtime["seeds"])
    prototype = shared.SharedMLP(input_dim, list(runtime["hidden"]), float(runtime["dropout"]))
    bundles = tuple(shared.MLPBundle(dict(mlp_config), seed) for seed in seeds)
    if any(bundle.model is not None for bundle in bundles):
        raise RuntimeError("UNFITTED_MLP_BUNDLE_HAS_MODEL")
    return UnfittedMLPEnsemble(
        prototype=prototype,
        bundles=bundles,
        seeds=seeds,
        runtime_config=MappingProxyType(mlp_config),
    )


def effective_parameter_audit(estimator: Any, spec: CandidateSpec) -> dict[str, Any]:
    effective = estimator.get_params(deep=False)
    expected = thaw(spec.frozen_hyperparameters)
    expected.update(thaw(spec.runtime_constructor_parameters))
    relevant_keys = sorted(expected)
    observed = {key: effective.get(key) for key in relevant_keys}
    expected_relevant = {key: expected[key] for key in relevant_keys}
    matches = {
        key: observed[key] == expected_relevant[key]
        for key in relevant_keys
    }
    if not all(matches.values()):
        raise RuntimeError(
            "EFFECTIVE_PARAMETER_DRIFT:"
            + spec.candidate_id
            + ":"
            + ",".join(key for key, match in matches.items() if not match)
        )
    return {
        "candidate_id": spec.candidate_id,
        "effective_parameter_sha256": sha256_value(observed),
        "effective_parameters": observed,
    }


def candidate_factory_audit(contract: FrozenContract) -> dict[str, Any]:
    seed = int(contract.training_seeds["classifier_candidate_seed"])
    cls_specs = classification_specs(contract)
    reg_specs = regression_specs(contract)
    cls_effective: dict[str, str] = {}
    reg_effective: dict[str, str] = {}
    for spec in cls_specs:
        if spec.estimator_family == "multitask_mlp":
            continue
        runtime_spec = _candidate_spec(
            contract,
            "classification",
            _item(contract, "classification", spec.candidate_id),
            target_index=0,
            seed=seed,
        )
        estimator = _build_sklearn(runtime_spec)
        cls_effective[spec.candidate_id] = effective_parameter_audit(
            estimator, runtime_spec
        )["effective_parameter_sha256"]
    for spec in reg_specs:
        if spec.estimator_family == "multitask_mlp":
            continue
        runtime_spec = _candidate_spec(
            contract,
            "regression",
            _item(contract, "regression", spec.candidate_id),
            target_index=0,
            seed=seed,
        )
        estimator = _build_sklearn(runtime_spec)
        reg_effective[spec.candidate_id] = effective_parameter_audit(
            estimator, runtime_spec
        )["effective_parameter_sha256"]

    ensemble = build_unfitted_mlp_ensemble(contract, contract.feature_count)
    linear_layers = [
        module
        for module in ensemble.prototype.trunk
        if module.__class__.__name__ == "Linear"
    ]
    dropout_layers = [
        module
        for module in ensemble.prototype.trunk
        if module.__class__.__name__ == "Dropout"
    ]
    hidden = [int(layer.out_features) for layer in linear_layers]
    if (
        hidden != [256, 128]
        or [float(layer.p) for layer in dropout_layers] != [0.1, 0.1]
        or ensemble.prototype.cls_head.out_features != 4
        or ensemble.prototype.reg_head.out_features != 4
    ):
        raise RuntimeError("MLP_ARCHITECTURE_DRIFT")
    return {
        "status": "PASS",
        "classification_candidate_count": len(cls_specs),
        "regression_candidate_count": len(reg_specs),
        "classification_candidate_ids": [spec.candidate_id for spec in cls_specs],
        "regression_candidate_ids": [spec.candidate_id for spec in reg_specs],
        "classification_candidate_spec_sha256": {
            spec.candidate_id: spec.candidate_spec_sha256 for spec in cls_specs
        },
        "regression_candidate_spec_sha256": {
            spec.candidate_id: spec.candidate_spec_sha256 for spec in reg_specs
        },
        "classification_effective_parameter_sha256": cls_effective,
        "regression_effective_parameter_sha256": reg_effective,
        "mlp_hidden": hidden,
        "mlp_dropout": [float(layer.p) for layer in dropout_layers],
        "mlp_classification_head": int(ensemble.prototype.cls_head.out_features),
        "mlp_regression_head": int(ensemble.prototype.reg_head.out_features),
        "mlp_seeds": list(ensemble.seeds),
        "unfitted_mlp_seed_count": len(ensemble.bundles),
        "fit_calls": 0,
    }
