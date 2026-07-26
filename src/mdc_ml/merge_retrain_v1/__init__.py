"""Frozen backend primitives for MDC-ML merge/retrain v1."""

from .artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    ArtifactManifest,
    ArtifactPolicy,
    ArtifactRecord,
    AtomicArtifactStore,
)
from .candidates import (
    UnfittedMLPEnsemble,
    build_unfitted_classification_candidate,
    build_unfitted_mlp_ensemble,
    build_unfitted_regression_candidate,
    candidate_factory_audit,
    classification_specs,
    regression_specs,
)
from .contracts import (
    CandidateSpec,
    EarlyStoppingContract,
    FrozenContract,
    SignatureBundle,
    TargetContract,
    load_frozen_contract,
)
from .state import (
    STATE_SCHEMA_VERSION,
    ResumeSignatureMismatch,
    StageState,
    StateTransitionError,
    TrainingExecutionState,
    UnitState,
)

__all__ = [
    "ARTIFACT_SCHEMA_VERSION",
    "STATE_SCHEMA_VERSION",
    "ArtifactManifest",
    "ArtifactPolicy",
    "ArtifactRecord",
    "AtomicArtifactStore",
    "CandidateSpec",
    "EarlyStoppingContract",
    "FrozenContract",
    "ResumeSignatureMismatch",
    "SignatureBundle",
    "StageState",
    "StateTransitionError",
    "TargetContract",
    "TrainingExecutionState",
    "UnfittedMLPEnsemble",
    "UnitState",
    "build_unfitted_classification_candidate",
    "build_unfitted_mlp_ensemble",
    "build_unfitted_regression_candidate",
    "candidate_factory_audit",
    "classification_specs",
    "load_frozen_contract",
    "regression_specs",
]
