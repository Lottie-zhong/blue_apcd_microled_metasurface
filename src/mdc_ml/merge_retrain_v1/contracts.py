from __future__ import annotations

"""Pure-read loading and validation of the frozen merge/retrain contract."""

import dataclasses
import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "configs" / "mdc_ml_active_learning_merge_retrain_v1.yaml"
EXPECTED_CONFIG_SHA256 = "76e51a802f598e458264c31db5b6024ade4a0e0a65f3ba2cc3c4587fcd74ade6"
EXPECTED_PROMOTION_CONTRACT_SHA256 = "71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52"
EXPECTED_TRAINING_CONTRACT_SHA256 = "4cc187dc18f2e18bae32dc659d1ffad6f2baf0fa411c7214fa98db02645ce886"
EXPECTED_FOLD_SIGNATURE = "1eff4d939bfe1af28964baebac8e33d0cb9953e98d9009921fac1eb3ae841aa7"
EXPECTED_FEATURE_COUNT = 150
EXPECTED_REGRESSION_TARGETS = (
    "spectral_fwhm_normal_nm",
    "angular_fwhm_450_deg",
    "cone5_integral_proxy",
    "normal_band_transmission_proxy",
)
EXPECTED_ENSEMBLE_SEEDS = (20260720, 20260721, 20260722)


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _plain(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    return _plain(value)


@dataclass(frozen=True)
class SignatureBundle:
    config_sha256: str
    promotion_contract_sha256: str
    training_contract_sha256: str
    dataset_signature: str
    fold_signature: str
    feature_signature: str
    trainer_sha256: str = ""
    execution_code_commit: str = ""

    def as_dict(self) -> dict[str, str]:
        return _plain(self)

    def as_resume_dict(self) -> dict[str, str]:
        return {
            "trainer_sha256": self.trainer_sha256,
            "execution_code_commit": self.execution_code_commit,
            "config_sha256": self.config_sha256,
            "promotion_contract_sha256": self.promotion_contract_sha256,
            "training_contract_sha256": self.training_contract_sha256,
            "dataset_signature": self.dataset_signature,
            "fold_signature": self.fold_signature,
            "feature_signature": self.feature_signature,
        }


@dataclass(frozen=True)
class CandidateSpec:
    kind: str
    candidate_id: str
    estimator_family: str
    estimator_class: str
    frozen_hyperparameters: Mapping[str, Any]
    runtime_constructor_parameters: Mapping[str, Any]
    random_state_rule: str
    preprocessing: str
    source_commit: str
    source_path: str
    source_symbol: str
    source_sha256: str
    resolved_value_sha256: str
    full_snapshot_sha256: str
    runtime_projection_sha256: str
    candidate_spec_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return _plain(self)


@dataclass(frozen=True)
class TargetContract:
    classification_targets: tuple[str, ...]
    regression_targets: tuple[str, ...]
    feature_signature: str
    feature_count: int
    transforms: Mapping[str, Any]


@dataclass(frozen=True)
class EarlyStoppingContract:
    patience: int
    validation_source: str
    minimum_delta: float
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class FrozenContract:
    config_path: Path
    signatures: SignatureBundle
    targets: TargetContract
    classification_allowlist: tuple[Mapping[str, Any], ...]
    regression_allowlist: tuple[Mapping[str, Any], ...]
    bounded_classification_ids: tuple[str, ...]
    bounded_regression_ids: tuple[str, ...]
    fixed_classification_baseline: str
    fixed_regression_baseline: str
    training_seeds: Mapping[str, Any]
    target_transforms: Mapping[str, Any]
    early_stopping: EarlyStoppingContract
    route_rules: Mapping[str, Any]
    source_references: tuple[Mapping[str, Any], ...]
    output_root: Path
    raw_config: Mapping[str, Any]

    @property
    def config_sha256(self) -> str:
        return self.signatures.config_sha256

    @property
    def promotion_contract_sha256(self) -> str:
        return self.signatures.promotion_contract_sha256

    @property
    def training_contract_sha256(self) -> str:
        return self.signatures.training_contract_sha256

    @property
    def fold_signature(self) -> str:
        return self.signatures.fold_signature

    @property
    def feature_signature(self) -> str:
        return self.signatures.feature_signature

    @property
    def feature_count(self) -> int:
        return self.targets.feature_count


def _load_merge_builder() -> Any:
    path = ROOT / "scripts" / "build_mdc_ml_active_learning_merge_retrain_v1.py"
    spec = importlib.util.spec_from_file_location("_mdc_merge_builder_contract_reader", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("FROZEN_CONTRACT_BUILDER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_references(value: Any) -> tuple[Mapping[str, Any], ...]:
    found: list[Mapping[str, Any]] = []
    if isinstance(value, dict):
        if {"source_commit", "source_path", "source_key_or_symbol", "source_sha256"} <= set(value):
            found.append(freeze(value))
        for item in value.values():
            found.extend(_source_references(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_source_references(item))
    return tuple(found)


def _raise_contract_mismatch(checks: Mapping[str, bool]) -> None:
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise RuntimeError("FROZEN_CONTRACT_MISMATCH:" + canonical_json(failed))


def validate_frozen_contract(contract: FrozenContract) -> FrozenContract:
    cls_ids = tuple(item["candidate_id"] for item in contract.classification_allowlist)
    reg_ids = tuple(item["candidate_id"] for item in contract.regression_allowlist)
    source_refs = contract.source_references
    checks = {
        "config_sha256": contract.config_sha256 == EXPECTED_CONFIG_SHA256,
        "promotion_contract_sha256": (
            contract.promotion_contract_sha256 == EXPECTED_PROMOTION_CONTRACT_SHA256
        ),
        "training_contract_sha256": (
            contract.training_contract_sha256 == EXPECTED_TRAINING_CONTRACT_SHA256
        ),
        "fold_signature": contract.fold_signature == EXPECTED_FOLD_SIGNATURE,
        "feature_count": contract.feature_count == EXPECTED_FEATURE_COUNT,
        "regression_target_order": contract.targets.regression_targets == EXPECTED_REGRESSION_TARGETS,
        "classification_candidate_count": len(cls_ids) == 10,
        "regression_candidate_count": len(reg_ids) == 10,
        "candidate_ids_unique": len(cls_ids) == len(set(cls_ids))
        and len(reg_ids) == len(set(reg_ids)),
        "classification_bounded_subset": set(contract.bounded_classification_ids) <= set(cls_ids),
        "regression_bounded_subset": set(contract.bounded_regression_ids) <= set(reg_ids),
        "fixed_classification_baseline_bounded": (
            contract.fixed_classification_baseline in contract.bounded_classification_ids
        ),
        "fixed_regression_baseline_bounded": (
            contract.fixed_regression_baseline in contract.bounded_regression_ids
        ),
        "ensemble_seeds": (
            tuple(contract.training_seeds["regressor_ensemble_seeds"]) == EXPECTED_ENSEMBLE_SEEDS
        ),
        "source_references_present": bool(source_refs),
        "source_references_resolved": all(
            len(str(reference["source_commit"])) == 40
            and len(str(reference["source_sha256"])) == 64
            and bool(reference["source_path"])
            and bool(reference["source_key_or_symbol"])
            for reference in source_refs
        ),
        "no_unresolved_placeholder": not _load_merge_builder().has_unresolved_placeholder(
            thaw(contract.raw_config)
        ),
        "first_training_not_started": (
            contract.raw_config["contract_revision"]["first_training_started"] is False
        ),
    }
    _raise_contract_mismatch(checks)
    return contract


def load_frozen_contract(config_path: Path = CONFIG) -> FrozenContract:
    config_path = config_path.resolve()
    config_sha = sha256_file(config_path)
    _raise_contract_mismatch({"config_sha256": config_sha == EXPECTED_CONFIG_SHA256})

    raw = json.loads(config_path.read_text(encoding="utf-8"))
    builder = _load_merge_builder()
    result = builder.validate_existing(config_path)
    output_root = (ROOT / raw["output_root"]).resolve()
    merge_audit = json.loads((output_root / "merge_audit_v1.json").read_text(encoding="utf-8"))
    source_checks = builder.validate_source_references(builder.training_execution_contract(raw))
    _raise_contract_mismatch(
        {
            "builder_validate_existing": result["status"] == "PASS"
            and all(result["checks"].values()),
            "promotion_contract_sha256": (
                result["promotion_contract_sha256"] == EXPECTED_PROMOTION_CONTRACT_SHA256
            ),
            "training_contract_sha256": (
                result["training_execution_contract_sha256"] == EXPECTED_TRAINING_CONTRACT_SHA256
            ),
            "fold_signature": merge_audit["fold_signature"] == EXPECTED_FOLD_SIGNATURE,
            "source_references": bool(source_checks) and all(source_checks),
        }
    )

    allow = raw["model_candidate_allowlist"]
    bounded = raw["bounded_recompetition_candidate_set"]
    fixed = raw["fixed_v1_architecture_retrain"]
    transforms = raw["target_transforms"]
    early = raw["early_stopping"]
    contract = FrozenContract(
        config_path=config_path,
        signatures=SignatureBundle(
            config_sha256=config_sha,
            promotion_contract_sha256=result["promotion_contract_sha256"],
            training_contract_sha256=result["training_execution_contract_sha256"],
            dataset_signature=merge_audit["merged_dataset_signature"],
            fold_signature=merge_audit["fold_signature"],
            feature_signature=raw["shared_feature_signature"],
        ),
        targets=TargetContract(
            classification_targets=tuple(raw["classification_targets"]),
            regression_targets=tuple(raw["regression_targets"]),
            feature_signature=raw["shared_feature_signature"],
            feature_count=int(transforms["feature_count"]),
            transforms=freeze(transforms),
        ),
        classification_allowlist=tuple(freeze(item) for item in allow["classification"]),
        regression_allowlist=tuple(freeze(item) for item in allow["regression"]),
        bounded_classification_ids=tuple(bounded["classification_candidate_ids"]),
        bounded_regression_ids=tuple(bounded["regression_candidate_ids"]),
        fixed_classification_baseline=fixed["classification"]["candidate_id"],
        fixed_regression_baseline=fixed["regression"]["candidate_id"],
        training_seeds=freeze(raw["training_seeds"]),
        target_transforms=freeze(transforms),
        early_stopping=EarlyStoppingContract(
            patience=int(early["patience"]),
            validation_source=str(early["validation_source"]),
            minimum_delta=float(early["minimum_delta"]),
            raw=freeze(early),
        ),
        route_rules=freeze(raw["route_rules"]),
        source_references=_source_references(builder.training_execution_contract(raw)),
        output_root=output_root,
        raw_config=freeze(raw),
    )
    return validate_frozen_contract(contract)


def contract_signature_bundle(contract: FrozenContract) -> dict[str, str]:
    return contract.signatures.as_dict()
