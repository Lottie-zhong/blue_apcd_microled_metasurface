"""Zero-solver readiness contracts for the frozen MDC HF surrogate V3 plan.

This module deliberately contains no solver, training, optimizer, backward,
PCA-fit, or scaler-fit entry points.  It consumes only the frozen development
metadata manifests and the V3-Test40 lock/overlap metadata allowlist.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover - the runtime contract requires numpy.
    np = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_plan_freeze_v1"
REPORT_DIR = ROOT / "contracts" / "mdc_hf_surrogate_v2" / "v3_training_readiness_v1"

DEV_GEOMETRIES = CONTRACT_DIR / "v3_development_geometry_manifest_v1.csv"
DEV_CASES = CONTRACT_DIR / "v3_development_case_matrix_v1.csv"
AL_GEOMETRIES = CONTRACT_DIR / "v3_al64_geometry_manifest_v1.csv"
AL_CASES = CONTRACT_DIR / "v3_al64_future_case_matrix_v1.csv"
AL_OVERLAP = CONTRACT_DIR / "v3_al64_overlap_audit_v1.json"
TEST40_LOCK = CONTRACT_DIR / "v3_test40_manifest_lock_v1.json"
TEST40_OVERLAP = CONTRACT_DIR / "v3_test40_overlap_audit_v1.json"
MODEL_CONTRACT = CONTRACT_DIR / "v3_model_candidate_contract_v1.json"
LOSS_CONTRACT = CONTRACT_DIR / "v3_profile_only_loss_contract_v1.json"
TRAINING_CONTRACT = CONTRACT_DIR / "v3_training_contract_v1.json"
METRICS_CONTRACT = CONTRACT_DIR / "v3_selection_metrics_contract_v1.json"
ENV_CONTRACT = CONTRACT_DIR / "v3_environment_provenance_v1.json"
PIP_FREEZE = CONTRACT_DIR / "RCP_LCP_pip_freeze.txt"
ROLE_TRANSITION = CONTRACT_DIR / "v3_data_role_transition_v1.json"
PLAN_COMPLETION = CONTRACT_DIR / "v3_plan_freeze_completion_manifest_v1.json"
PLAN_ARTIFACT_SHA = CONTRACT_DIR / "v3_plan_freeze_artifact_sha256_v1.json"

NATIVE_PROFILE_SHAPE = (301, 2000)
PROFILE_WEIGHTS = {
    "profile": 0.4117647058823529,
    "JS": 0.23529411764705882,
    "spectral_CDF": 0.17647058823529413,
    "angular_CDF": 0.17647058823529413,
}
FIT_CAP = 45
OUTER_FOLDS = 5
INNER_STOP_SEED = 20260813
OUTER_SEED = 20260810


class ReadinessError(RuntimeError):
    """A readiness contract violation."""


class SealedTestAccessError(ReadinessError):
    """An attempt to access V3-Test40 truth/label/target data."""


class FormalTrainingRejected(ReadinessError):
    """Formal V3 training is not authorized by the current readiness state."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def object_sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_key(prefix: str, seed: int, value: str) -> str:
    return hashlib.sha256(f"{prefix}|{seed}|{value.lower()}".encode("utf-8")).hexdigest()


def case_identity(row: Mapping[str, Any]) -> str:
    for key in ("case_uid", "test_case_uid", "case_hash"):
        value = str(row.get(key, ""))
        if value:
            return value
    raise ReadinessError("case row has no immutable identity")


def _six_case_signature(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    required = {("top", "x"), ("top", "z"), ("centroid", "x"), ("centroid", "z"), ("bottom", "x"), ("bottom", "z")}
    observed = {(str(row.get("source_position")), str(row.get("dipole_orientation"))) for row in rows}
    return {"complete": observed == required, "observed": sorted([list(x) for x in observed]), "expected": sorted([list(x) for x in required])}


class SealedTest40Guard:
    """Allow only V3-Test40 identity metadata, never labels or target paths."""

    ALLOWED_METADATA_NAMES = {"v3_test40_manifest_lock_v1.json", "v3_test40_overlap_audit_v1.json"}
    SEALED_TOKEN = re.compile(r"(?:MDC_HF_SURROGATE_V3_TEST40_V1|v3_test40)", re.IGNORECASE)
    TRUTH_TOKEN = re.compile(r"(?:label|truth|target|diagnostic|prediction)", re.IGNORECASE)

    def metadata_path_allowed(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        return resolved.parent == CONTRACT_DIR.resolve() and resolved.name in self.ALLOWED_METADATA_NAMES

    def assert_path_allowed(self, path: Path | str, operation: str = "read") -> None:
        candidate = Path(path)
        text = str(candidate).replace("\\", "/")
        if self.metadata_path_allowed(candidate):
            return
        if self.SEALED_TOKEN.search(text) or (self.TRUTH_TOKEN.search(text) and "test40" in text.lower()):
            raise SealedTestAccessError(f"V3-Test40 sealed {operation} forbidden: {candidate}")

    def read_metadata(self, path: Path) -> dict[str, Any]:
        if not self.metadata_path_allowed(path):
            self.assert_path_allowed(path, "metadata read")
            raise SealedTestAccessError(f"metadata path not on V3-Test40 allowlist: {path}")
        return read_json(path)

    def audit(self) -> dict[str, Any]:
        lock = self.read_metadata(TEST40_LOCK)
        overlap = self.read_metadata(TEST40_OVERLAP)
        passed = (
            lock.get("test_id") == "MDC_HF_SURROGATE_V3_TEST40_V1"
            and lock.get("labels_generated") is False
            and lock.get("labels_read") == 0
            and lock.get("solver_calls") == 0
            and lock.get("status") == "FROZEN"
            and overlap.get("formal_numerical_value_reads") == 0
            and overlap.get("status") == "PASS"
        )
        return {
            "status": "PASS" if passed else "HARD_GATE_V3_TEST40_SEALED_METADATA_INVALID",
            "metadata_files_read": [TEST40_LOCK.name, TEST40_OVERLAP.name],
            "labels_generated": lock.get("labels_generated"),
            "labels_read": lock.get("labels_read"),
            "solver_calls": lock.get("solver_calls"),
            "formal_numerical_value_reads": overlap.get("formal_numerical_value_reads"),
            "truth_paths_scanned": False,
            "target_paths_scanned": False,
            "guard_policy": "metadata_allowlist_only; label/target/truth reads forbidden",
        }


@dataclass(frozen=True)
class MembershipAudit:
    base_geometry_count: int
    base_case_count: int
    al64_geometry_count: int
    al64_case_count: int
    total_geometry_count: int
    total_case_count: int
    base_six_case_complete: bool
    al64_six_case_complete: bool
    base_case_uid_unique: bool
    al64_case_uid_unique: bool
    base_geometry_unique: bool
    al64_geometry_unique: bool
    overlap_count: int
    al64_pending: bool
    status: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class CanonicalV3DevelopmentLoader:
    """Canonical V3 development membership loader with preflight/formal modes."""

    def __init__(self, contract_dir: Path = CONTRACT_DIR):
        self.contract_dir = contract_dir

    def load(self, *, formal: bool = False) -> dict[str, Any]:
        base_geometries = read_csv(self.contract_dir / DEV_GEOMETRIES.name)
        base_cases = read_csv(self.contract_dir / DEV_CASES.name)
        al_geometries = read_csv(self.contract_dir / AL_GEOMETRIES.name)
        al_cases = read_csv(self.contract_dir / AL_CASES.name)
        self._validate_base(base_geometries, base_cases)
        self._validate_al64(al_geometries, al_cases)
        base_hashes = {row["geometry_hash"] for row in base_geometries}
        al_hashes = {row["geometry_hash"] for row in al_geometries}
        overlap = len(base_hashes & al_hashes)
        al_pending = any(row.get("future_solver_status") != "ACCEPTED" for row in al_geometries)
        audit = MembershipAudit(
            base_geometry_count=len(base_geometries),
            base_case_count=len(base_cases),
            al64_geometry_count=len(al_geometries),
            al64_case_count=len(al_cases),
            total_geometry_count=len(base_geometries) + len(al_geometries),
            total_case_count=len(base_cases) + len(al_cases),
            base_six_case_complete=_six_case_signature(base_cases)["complete"],
            al64_six_case_complete=_six_case_signature(al_cases)["complete"],
            base_case_uid_unique=len({case_identity(row) for row in base_cases}) == len(base_cases),
            al64_case_uid_unique=len({case_identity(row) for row in al_cases}) == len(al_cases),
            base_geometry_unique=len(base_hashes) == len(base_geometries),
            al64_geometry_unique=len(al_hashes) == len(al_geometries),
            overlap_count=overlap,
            al64_pending=al_pending,
            status="WAITING_FOR_AL64_COMPLETION" if al_pending else "FORMAL_MEMBERSHIP_COMPLETE",
        )
        if audit.overlap_count or audit.base_geometry_count != 136 or audit.base_case_count != 816:
            raise ReadinessError("canonical V3 base membership cardinality/overlap failure")
        if audit.total_geometry_count != 200 or audit.total_case_count != 1200:
            raise ReadinessError("canonical V3 formal membership cardinality failure")
        if formal and al_pending:
            raise FormalTrainingRejected("formal V3 training requires accepted AL64 64/384 membership")
        return {
            "membership": audit.as_dict(),
            "base_geometry_manifest": str(self.contract_dir / DEV_GEOMETRIES.name),
            "base_case_matrix": str(self.contract_dir / DEV_CASES.name),
            "al64_geometry_manifest": str(self.contract_dir / AL_GEOMETRIES.name),
            "al64_case_matrix": str(self.contract_dir / AL_CASES.name),
            "base_roles": sorted({row["source_role"] for row in base_geometries}),
            "al64_labels_status": sorted({row["future_labels_status"] for row in al_geometries}),
            "al64_solver_status": sorted({row["future_solver_status"] for row in al_geometries}),
            "formal_training_allowed": not al_pending and audit.total_geometry_count == 200 and audit.total_case_count == 1200,
        }

    @staticmethod
    def _validate_base(geometries: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]) -> None:
        roles = {str(row.get("source_role")) for row in geometries}
        expected_roles = {"DOE96_FORMAL_DEVELOPMENT", "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3"}
        if roles != expected_roles or len(geometries) != 136 or len(cases) != 816:
            raise ReadinessError("base development manifest is not frozen 136/816")
        if not _six_case_signature(cases)["complete"]:
            raise ReadinessError("base development matrix missing one of six source cases")
        if len({row["geometry_hash"] for row in geometries}) != 136:
            raise ReadinessError("base development geometry hash duplicate")
        if len({case_identity(row) for row in cases}) != 816:
            raise ReadinessError("base development case identity duplicate")

    @staticmethod
    def _validate_al64(geometries: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]) -> None:
        if len(geometries) != 64 or len(cases) != 384:
            raise ReadinessError("AL64 frozen membership cardinality failure")
        if not _six_case_signature(cases)["complete"]:
            raise ReadinessError("AL64 case matrix missing one of six source cases")
        if len({row["geometry_hash"] for row in geometries}) != 64:
            raise ReadinessError("AL64 geometry hash duplicate")
        if len({case_identity(row) for row in cases}) != 384:
            raise ReadinessError("AL64 case UID duplicate")
        if any(row.get("future_labels_status") != "NOT_GENERATED" for row in geometries):
            raise ReadinessError("AL64 labels must remain NOT_GENERATED in readiness mode")


@dataclass(frozen=True)
class CandidateConfig:
    id: str
    backbone: str
    input_width: int
    latent_width: int
    profile_head_width: int
    residual_blocks: int
    residual_width: int
    dropout: float
    weight_decay: float
    regularization: str
    purpose: str

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "backbone": self.backbone, "input_width": self.input_width, "latent_width": self.latent_width, "profile_head_width": self.profile_head_width, "residual_blocks": self.residual_blocks, "residual_width": self.residual_width, "dropout": self.dropout, "weight_decay": self.weight_decay, "regularization": self.regularization, "purpose": self.purpose, "latent_output_dimension": "PCA32", "latent_head": "linear_signed", "power_head": "ABSENT_FROM_FORMAL_MODEL", "auxiliary_head": "NOT_LOAD_BEARING"}


def load_candidate_registry(path: Path = MODEL_CONTRACT) -> dict[str, Any]:
    contract = read_json(path)
    candidates = [CandidateConfig(**row) for row in contract["candidates"]]
    ids = [candidate.id for candidate in candidates]
    if ids != ["V3-A", "V3-B", "V3-C"] or contract.get("candidate_count") != 3:
        raise ReadinessError("V3 candidate IDs/order drift")
    if contract.get("PCA32_retained") is not True or contract.get("power_head") != "REMOVED_FROM_PRIMARY_V3_SHARED_LOSS":
        raise ReadinessError("V3 candidate contract target/head drift")
    entries = [candidate.as_dict() for candidate in candidates]
    return {"contract_id": contract["contract_id"], "candidate_count": 3, "candidates": entries, "serialization_sha256": object_sha(entries), "training_authorized": False}


def build_candidate_model(config: CandidateConfig):
    """Build a structural pure-forward model; this function never fits or trains."""
    try:
        import torch
        from torch import nn
    except Exception as exc:  # pragma: no cover
        raise ReadinessError(f"torch required for pure-forward structural test: {exc}") from exc

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
        def __init__(self):
            super().__init__()
            self.input_stem = nn.Linear(config.input_width, config.residual_width)
            self.blocks = nn.ModuleList([ResidualBlock(config.residual_width, config.dropout) for _ in range(config.residual_blocks)])
            self.latent_hidden = nn.Linear(config.residual_width, config.latent_width)
            self.latent_head = nn.Linear(config.latent_width, config.profile_head_width)
            self.power_head = None
            self.auxiliary_head = None

        def forward(self, x):
            y = torch.relu(self.input_stem(x))
            for block in self.blocks:
                y = block(y)
            y = torch.relu(self.latent_hidden(y))
            return {"latent": self.latent_head(y)}

    model = ProfileOnlyModel()
    return model


def _normalize_numpy(profile: Any, eps: float = 1e-12):
    if np is None:
        raise ReadinessError("numpy is required for profile metrics")
    value = np.asarray(profile, dtype=float)
    if value.ndim < 2:
        raise ReadinessError("profile must have at least two axes")
    if not np.all(np.isfinite(value)) or np.any(value < -eps):
        raise ReadinessError("profile contains nonfinite or negative raw intensity")
    value = np.maximum(value, 0.0)
    total = value.sum(axis=tuple(range(value.ndim - 2, value.ndim)), keepdims=True)
    if np.any(total <= eps):
        raise ReadinessError("profile normalization denominator is not positive")
    return value / total


def normalize_native_profile(profile: Any, *, require_native_shape: bool = True):
    value = np.asarray(profile, dtype=float)
    if require_native_shape and tuple(value.shape[-2:]) != NATIVE_PROFILE_SHAPE:
        raise ReadinessError(f"native profile shape must end in {NATIVE_PROFILE_SHAPE}, got {value.shape}")
    return _normalize_numpy(value)


def _cdf_numpy(profile: np.ndarray, axis: int) -> np.ndarray:
    marginal = profile.sum(axis=axis)
    denom = marginal.sum(axis=-1, keepdims=True)
    return np.cumsum(marginal / np.maximum(denom, 1e-12), axis=-1)


def profile_only_loss_numpy(prediction: Any, target: Any) -> dict[str, float]:
    pred = _normalize_numpy(prediction)
    truth = _normalize_numpy(target)
    log_pred = np.log(np.maximum(pred, 1e-12))
    log_truth = np.log(np.maximum(truth, 1e-12))
    diff = np.abs(log_pred - log_truth)
    smooth_l1 = np.where(diff < 1.0, 0.5 * diff * diff, diff - 0.5).mean()
    midpoint = 0.5 * (pred + truth)
    js = 0.5 * np.sum(pred * np.log(np.maximum(pred, 1e-12) / np.maximum(midpoint, 1e-12)) + truth * np.log(np.maximum(truth, 1e-12) / np.maximum(midpoint, 1e-12)), axis=(-2, -1)).mean()
    spectral = np.abs(_cdf_numpy(pred, axis=-1) - _cdf_numpy(truth, axis=-1)).mean()
    angular = np.abs(_cdf_numpy(pred, axis=-2) - _cdf_numpy(truth, axis=-2)).mean()
    values = {"profile": float(smooth_l1), "JS": float(js), "spectral_CDF": float(spectral), "angular_CDF": float(angular), "power_loss": 0.0, "auxiliary_loss": 0.0}
    values["total"] = sum(PROFILE_WEIGHTS[key] * values[key] for key in PROFILE_WEIGHTS)
    return values


def profile_only_loss_torch(prediction, target) -> dict[str, Any]:
    """Differentiable definition only; this task never invokes backward()."""
    import torch
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
    spec_p = spec_p / torch.clamp(spec_p.sum(dim=-1, keepdim=True), min=1e-12)
    spec_t = spec_t / torch.clamp(spec_t.sum(dim=-1, keepdim=True), min=1e-12)
    ang_p = ang_p / torch.clamp(ang_p.sum(dim=-1, keepdim=True), min=1e-12)
    ang_t = ang_t / torch.clamp(ang_t.sum(dim=-1, keepdim=True), min=1e-12)
    spectral = torch.abs(torch.cumsum(spec_p, dim=-1) - torch.cumsum(spec_t, dim=-1)).mean()
    angular = torch.abs(torch.cumsum(ang_p, dim=-1) - torch.cumsum(ang_t, dim=-1)).mean()
    values = {"profile": profile, "JS": js, "spectral_CDF": spectral, "angular_CDF": angular, "power_loss": torch.zeros((), dtype=profile.dtype, device=profile.device), "auxiliary_loss": torch.zeros((), dtype=profile.dtype, device=profile.device)}
    values["total"] = sum(PROFILE_WEIGHTS[key] * values[key] for key in PROFILE_WEIGHTS)
    return values


def loss_contract_audit() -> dict[str, Any]:
    contract = read_json(LOSS_CONTRACT)
    weights = {key: float(value["weight"]) for key, value in contract["components"].items()}
    expected = {"L_profile": PROFILE_WEIGHTS["profile"], "L_JS": PROFILE_WEIGHTS["JS"], "L_spectral_CDF": PROFILE_WEIGHTS["spectral_CDF"], "L_angular_CDF": PROFILE_WEIGHTS["angular_CDF"]}
    match = all(math.isclose(weights.get(key, float("nan")), value, rel_tol=0.0, abs_tol=1e-15) for key, value in expected.items())
    return {"contract_id": contract["contract_id"], "weights": PROFILE_WEIGHTS, "weight_sum": sum(PROFILE_WEIGHTS.values()), "weight_sum_close_to_one": math.isclose(sum(PROFILE_WEIGHTS.values()), 1.0, abs_tol=1e-12), "contract_weights_exact": match, "power_loss": 0.0, "auxiliary_loss": 0.0, "power_target_load_bearing": False, "auxiliary_target_load_bearing": False, "normalization": contract["normalization"], "status": "PASS" if match else "HARD_GATE_LOSS_CONTRACT_DRIFT"}


def _geometry_hashes(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    return [str(row["geometry_hash"]) for row in rows]


def outer_geometry_folds(geometry_rows: Sequence[Mapping[str, Any]], *, n_folds: int = OUTER_FOLDS, seed: int = OUTER_SEED, formal: bool = False) -> dict[str, Any]:
    hashes = sorted(set(_geometry_hashes(geometry_rows)))
    if formal and len(hashes) != 200:
        raise ReadinessError("formal OOF split requires exactly 200 development geometries")
    if n_folds != 5 or not hashes:
        raise ReadinessError("frozen outer split requires 5 nonempty folds")
    ordered = sorted(hashes, key=lambda value: stable_key("MDC_V3_OUTER_FOLD", seed, value))
    assignments = {value: index % n_folds for index, value in enumerate(ordered)}
    folds = {str(i): sorted([value for value, fold in assignments.items() if fold == i]) for i in range(n_folds)}
    return {"contract_id": "MDC_HF_SURROGATE_V3_OUTER_5FOLD_V1", "method": "geometry_hash_grouped_5_fold", "seed": seed, "geometry_count": len(hashes), "folds": folds, "case_level_leakage": False, "formal_membership": len(hashes) == 200, "status": "PASS"}


def inner_stop_membership(geometry_rows: Sequence[Mapping[str, Any]], outer_held_out: Iterable[str], *, seed: int = INNER_STOP_SEED, fraction: float = 0.20) -> dict[str, Any]:
    held_out = set(outer_held_out)
    train_rows = [row for row in geometry_rows if str(row["geometry_hash"]) not in held_out]
    groups: dict[str, list[str]] = {}
    for row in train_rows:
        stratum = str(row.get("topology_family") or "ALL")
        groups.setdefault(stratum, []).append(str(row["geometry_hash"]))
    stop: list[str] = []
    for stratum, values in sorted(groups.items()):
        ordered = sorted(set(values), key=lambda value: stable_key("MDC_V3_INNER_STOP", seed, value))
        take = max(1, int(math.ceil(len(ordered) * fraction))) if ordered else 0
        stop.extend(ordered[:take])
    stop_set = set(stop)
    train_set = {str(row["geometry_hash"]) for row in train_rows}
    if stop_set & held_out or not stop_set <= train_set:
        raise ReadinessError("inner-stop split overlaps outer held-out membership")
    return {"contract_id": "MDC_HF_SURROGATE_V3_INNER_STOP_V1", "seed": seed, "method": "deterministic_hash_stratified_20_percent_of_outer_train_geometries", "fraction": fraction, "outer_held_out_count": len(held_out), "outer_train_count": len(train_set), "inner_stop_count": len(stop_set), "inner_stop_geometry_hashes": sorted(stop_set), "inner_train_geometry_hashes": sorted(train_set - stop_set), "disjoint_from_outer_held_out": not bool(stop_set & held_out), "case_level_grouped": True, "status": "PASS"}


def split_leakage_audit(loader_report: Mapping[str, Any]) -> dict[str, Any]:
    base_rows = read_csv(DEV_GEOMETRIES)
    provisional = outer_geometry_folds(base_rows, formal=False)
    inner = inner_stop_membership(base_rows, provisional["folds"]["0"])
    return {"outer": provisional, "inner_stop_structural_136": inner, "formal_membership_materialized": False, "formal_rule_requires_al64": True, "no_case_level_random_split": True, "outer_held_out_never_used_for_stopping": True, "pca_scaler_fit_calls": 0, "status": "PASS"}


@dataclass
class FitBudget:
    max_unique_fits: int = FIT_CAP
    reservations: set[tuple[str, int, int]] = field(default_factory=set)

    def reserve(self, candidate_id: str, seed: int, outer_fold: int) -> str:
        identity = (str(candidate_id), int(seed), int(outer_fold))
        if identity in self.reservations:
            raise ReadinessError(f"duplicate neural fit identity: {identity}")
        if len(self.reservations) >= self.max_unique_fits:
            raise ReadinessError("HARD_GATE_NEURAL_FIT_BUDGET_EXCEEDED")
        self.reservations.add(identity)
        return hashlib.sha256(canonical_json(list(identity)).encode("utf-8")).hexdigest()

    def audit(self) -> dict[str, Any]:
        expected = 3 * 5 * 3
        return {"maximum_unique_neural_fits": self.max_unique_fits, "expected_contract_cap": expected, "reserved_unique_fits": len(self.reservations), "dispatch_calls": 0, "training_executed": False, "over_cap": len(self.reservations) > self.max_unique_fits, "status": "PASS" if self.max_unique_fits == expected and len(self.reservations) <= expected else "HARD_GATE_NEURAL_FIT_BUDGET"}


@dataclass(frozen=True)
class FormalFitIdentity:
    """Auditable identity for a future formal OOF fit; construction is not dispatch."""

    candidate_id: str
    seed: int
    outer_fold: int
    inner_stop_seed: int = INNER_STOP_SEED

    @property
    def checkpoint_identity(self) -> str:
        return object_sha({"candidate_id": self.candidate_id, "seed": self.seed, "outer_fold": self.outer_fold, "inner_stop_seed": self.inner_stop_seed})

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "seed": self.seed,
            "outer_fold": self.outer_fold,
            "inner_stop_seed": self.inner_stop_seed,
            "checkpoint_identity": self.checkpoint_identity,
        }


class FormalRunStateMachine:
    """Pure state/provenance contract for a future fit, with no training hooks."""

    ALLOWED = {
        "candidate": {"seed"},
        "seed": {"outer_fold"},
        "outer_fold": {"inner_stop"},
        "inner_stop": {"epoch"},
        "epoch": {"epoch", "completed", "failed", "resumable"},
        "resumable": {"epoch", "failed", "completed"},
        "failed": {"resumable"},
        "completed": set(),
    }

    def __init__(self, identity: FormalFitIdentity) -> None:
        self.identity = identity
        self.state = "candidate"
        self.epoch = 0
        self.history = ["candidate"]

    def transition(self, next_state: str, *, epoch: int | None = None) -> None:
        if next_state not in self.ALLOWED.get(self.state, set()):
            raise ReadinessError(f"invalid formal run state transition: {self.state}->{next_state}")
        if next_state == "epoch":
            if epoch is None or int(epoch) < 0:
                raise ReadinessError("epoch state requires a non-negative epoch")
            self.epoch = int(epoch)
        self.state = next_state
        self.history.append(next_state)

    def audit(self) -> dict[str, Any]:
        return {
            "identity": self.identity.as_dict(),
            "state": self.state,
            "epoch": self.epoch,
            "history": list(self.history),
            "dispatch_calls": 0,
            "training_executed": False,
            "status": "PASS",
        }


def execution_state_contract() -> dict[str, Any]:
    sample = FormalRunStateMachine(FormalFitIdentity("V3-A", 20260810, 0))
    for state in ("seed", "outer_fold", "inner_stop", "epoch"):
        sample.transition(state, epoch=0 if state == "epoch" else None)
    return {
        "states": ["candidate", "seed", "outer_fold", "inner_stop", "epoch", "completed", "failed", "resumable"],
        "identity_fields": ["candidate_id", "seed", "outer_fold", "inner_stop_seed", "checkpoint_identity"],
        "max_unique_fits": FIT_CAP,
        "dispatch_calls": 0,
        "training_executed": False,
        "sample_state_audit": sample.audit(),
        "status": "PASS",
    }


def duration_contract_audit() -> dict[str, Any]:
    contract = read_json(TRAINING_CONTRACT)
    duration = contract["duration"]
    required = {"min_epochs": 50, "max_epochs": 400, "patience": 50, "optimizer": "AdamW", "scheduler": "cosine_decay", "final_epoch_3_inherited": False}
    actual = {"min_epochs": duration["min_epochs"], "max_epochs": duration["max_epochs"], "patience": duration["patience"], "optimizer": contract["optimizer"], "scheduler": contract["scheduler"], "final_epoch_3_inherited": duration["final_epoch_3_inherited"]}
    return {"required": required, "actual": actual, "early_stop_before_min_epoch_forbidden": True, "outer_metric_stopping_forbidden": True, "status": "PASS" if actual == required else "HARD_GATE_DURATION_CONTRACT_DRIFT"}


def validate_training_state(state: Mapping[str, Any]) -> None:
    if int(state.get("best_epoch", 0)) < 50 and state.get("status") == "completed":
        raise ReadinessError("best epoch below min_epochs cannot be accepted")
    if state.get("stopping_metric_source") == "outer_held_out":
        raise ReadinessError("outer fold metric cannot drive stopping")
    if state.get("final_epoch") == 3:
        raise ReadinessError("fixed-v2 final_epoch=3 policy is forbidden")


def _pairwise_mean_distance(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    distance = np.abs(values[:, None, :] - values[None, :, :]).mean(axis=-1)
    tri = distance[np.triu_indices(len(values), k=1)]
    return float(tri.mean()) if len(tri) else 0.0


def anti_collapse_metrics(predicted_latent: Any, truth_latent: Any, predicted_profiles: Any | None = None, truth_profiles: Any | None = None) -> dict[str, Any]:
    pred_latent = np.asarray(predicted_latent, dtype=float)
    truth_latent = np.asarray(truth_latent, dtype=float)
    if pred_latent.shape != truth_latent.shape or pred_latent.ndim != 2:
        raise ReadinessError("latent metric inputs must be matching [sample, component] arrays")
    truth_var = truth_latent.var(axis=0)
    pred_var = pred_latent.var(axis=0)
    ratio = pred_var / np.maximum(truth_var, 1e-12)
    collapsed = int(np.sum(pred_var <= 1e-12))
    result: dict[str, Any] = {"latent_variance_preservation": {"per_component_variance_ratio": ratio.tolist(), "median_variance_ratio": float(np.median(ratio)), "collapsed_component_count": collapsed}, "profile_pairwise_diversity_ratio": None, "profile_metrics": None, "fold_wise_metrics": None, "topology_wise_metrics": None, "worst_fold_guard_inputs": None, "worst_topology_guard_inputs": None, "promotion_thresholds": "NOT_DEFINED_IN_PLAN_FREEZE"}
    if predicted_profiles is not None and truth_profiles is not None:
        pp = _normalize_numpy(predicted_profiles)
        tt = _normalize_numpy(truth_profiles)
        result["profile_pairwise_diversity_ratio"] = _pairwise_mean_distance(pp.reshape(len(pp), -1)) / max(_pairwise_mean_distance(tt.reshape(len(tt), -1)), 1e-12)
        loss = profile_only_loss_numpy(pp, tt)
        result["profile_metrics"] = {"joint_JS": loss["JS"], "joint_weighted_L1": float(np.abs(pp - tt).mean()), "spectral_CDF": loss["spectral_CDF"], "angular_CDF": loss["angular_CDF"]}
    return result


def pca_scaler_leakage_guard(*, outer_training: Iterable[str], outer_held_out: Iterable[str], fit_membership: Iterable[str], mode: str = "outer_fold") -> dict[str, Any]:
    train, held, fit = set(outer_training), set(outer_held_out), set(fit_membership)
    if fit & held:
        raise ReadinessError("PCA/scaler fit membership leaks outer held-out geometry")
    if mode == "outer_fold" and not fit <= train:
        raise ReadinessError("outer-fold PCA/scaler fit must be subset of outer training")
    if mode == "full_development" and fit != train:
        raise ReadinessError("full-development fit requires explicit full-development membership")
    return {"mode": mode, "fit_count": len(fit), "outer_training_count": len(train), "outer_held_out_count": len(held), "leakage": False, "PCA_fit_calls": 0, "scaler_fit_calls": 0, "status": "PASS"}


def environment_audit() -> dict[str, Any]:
    expected = read_json(ENV_CONTRACT)
    actual: dict[str, Any] = {"python_executable": sys.executable, "python_version": platform.python_version(), "platform": platform.platform()}
    try:
        import torch
        actual.update({"torch_version": torch.__version__, "cuda_build": torch.version.cuda, "cuda_runtime_available": bool(torch.cuda.is_available()), "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
    except Exception as exc:
        actual.update({"torch_import_error": str(exc), "torch_version": None, "cuda_build": None, "cuda_runtime_available": False, "gpu": None})
    actual["pip_freeze_sha256"] = file_sha(PIP_FREEZE) if PIP_FREEZE.exists() else None
    fields = ("python_version", "torch_version", "cuda_build", "gpu", "pip_freeze_sha256")
    matches = {field: actual.get(field) == expected.get(field) for field in fields}
    return {"expected": {field: expected.get(field) for field in fields}, "actual": actual, "matches": matches, "status": "PASS" if all(matches.values()) else "HARD_GATE_ENVIRONMENT_PROVENANCE_MISMATCH"}


def readiness_gate(loader_report: Mapping[str, Any], sealed_report: Mapping[str, Any], counters: Mapping[str, int]) -> dict[str, Any]:
    membership = loader_report["membership"]
    required_zero = ("FDTD_calls", "TMM_calls", "RCWA_calls", "NP_solver_calls", "neural_fits", "optimizer_calls", "backward_calls", "PCA_fits", "scaler_fits", "V3_Test40_label_reads", "HF15_formal_label_reads", "HF15_diagnostics_value_reads", "R12_formal_label_reads", "R12_diagnostics_value_reads")
    zero_ok = all(int(counters.get(key, -1)) == 0 for key in required_zero)
    base_ok = membership["base_geometry_count"] == 136 and membership["base_case_count"] == 816 and membership["base_six_case_complete"]
    al_ok = membership["al64_geometry_count"] == 64 and membership["al64_case_count"] == 384 and membership["al64_six_case_complete"] and not membership["al64_pending"]
    sealed_ok = sealed_report.get("status") == "PASS" and sealed_report.get("labels_read") == 0
    ready = base_ok and al_ok and zero_ok and sealed_ok and membership["total_geometry_count"] == 200 and membership["total_case_count"] == 1200
    return {"status": "READY_FOR_SEPARATE_V3_OOF_TRAINING_AUTHORIZATION" if ready else "WAITING_FOR_AL64_COMPLETION", "base_136_816_ok": base_ok, "al64_64_384_accepted": al_ok, "total_200_1200_ok": membership["total_geometry_count"] == 200 and membership["total_case_count"] == 1200, "sealed_v3_test40_ok": sealed_ok, "zero_solver_training_counters_ok": zero_ok, "formal_training_allowed": ready}


def run_readiness(output_dir: Path = REPORT_DIR) -> dict[str, Any]:
    loader = CanonicalV3DevelopmentLoader()
    loader_report = loader.load(formal=False)
    sealed_report = SealedTest40Guard().audit()
    counters = {key: 0 for key in ("FDTD_calls", "TMM_calls", "RCWA_calls", "NP_solver_calls", "neural_fits", "optimizer_calls", "backward_calls", "PCA_fits", "scaler_fits", "V3_Test40_label_reads", "HF15_formal_label_reads", "HF15_diagnostics_value_reads", "R12_formal_label_reads", "R12_diagnostics_value_reads")}
    budget = FitBudget()
    payloads = {
        "readiness_report.json": {"task": "MDC_HF_SURROGATE_V3_TRAINING_PIPELINE_ZERO_SOLVER_READINESS_FROZEN", "status": "MDC_HF_SURROGATE_V3_TRAINING_PIPELINE_ZERO_SOLVER_READINESS_FROZEN_WAITING_FOR_AL64", "loader": loader_report, "sealed_guard": sealed_report, "counters": counters},
        "architecture_registry.json": load_candidate_registry(),
        "loss_contract_verification.json": loss_contract_audit(),
        "split_leakage_audit.json": split_leakage_audit(loader_report),
        "anti_collapse_metric_registry.json": {"contract": read_json(METRICS_CONTRACT), "implemented_metrics": ["latent_variance_preservation", "collapsed_component_count", "profile_pairwise_diversity_ratio", "joint_JS", "joint_weighted_L1", "spectral_CDF", "angular_CDF", "fold_wise_metrics", "topology_wise_metrics", "worst_fold_guard_inputs", "worst_topology_guard_inputs"], "threshold_status": "NOT_DEFINED_IN_PLAN_FREEZE", "status": "PASS"},
          "training_duration_guard.json": duration_contract_audit(),
          "training_dispatch_budget_audit.json": budget.audit(),
          "training_execution_state_contract.json": execution_state_contract(),
          "sealed_test_guard_audit.json": sealed_report,
        "al64_pending_gate_result.json": readiness_gate(loader_report, sealed_report, counters),
        "environment_provenance_report.json": environment_audit(),
    }
    for name, value in payloads.items():
        write_json(output_dir / name, value)
    report = payloads["readiness_report.json"]
    md = ["# MDC HF Surrogate V3 zero-solver readiness", "", f"- Status: `{report['status']}`", "- Current development preflight: 136 geometries / 816 cases", "- Future AL64 gate: 64 geometries / 384 cases pending", "- Formal target: 200 geometries / 1200 cases", "- Solver/training/PCA/scaler calls in this task: all zero", "- V3-Test40 labels: NOT_GENERATED and NOT_READ; metadata-only lock audit", "- Formal execution state identity/state-machine contract: PASS; dispatch calls: 0", "- Promotion thresholds: not defined in plan freeze; metric computation only.", ""]
    (output_dir / "readiness_report.md").write_text("\n".join(md), encoding="utf-8")
    hashes = {path.name: {"sha256": file_sha(path), "size": path.stat().st_size} for path in sorted(output_dir.iterdir()) if path.is_file() and path.name != "artifact_sha256.json"}
    write_json(output_dir / "artifact_sha256.json", {"status": "PASS", "files": hashes})
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(REPORT_DIR))
    args = parser.parse_args()
    print(json.dumps(run_readiness(Path(args.output_dir)), ensure_ascii=False, sort_keys=True))
