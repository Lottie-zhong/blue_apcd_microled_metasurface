from __future__ import annotations

"""Deterministic training execution state and complete resume signature gate."""

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .contracts import SignatureBundle, canonical_json


STATE_SCHEMA_VERSION = "mdc_ml_training_execution_state_v1"
STATUSES = ("NOT_STARTED", "RUNNING", "PARTIAL", "FAILED", "COMPLETE")
STAGES = (
    "PREFLIGHT",
    "CLASSIFICATION_OOF",
    "REGRESSION_OOF",
    "FINAL_CLASSIFICATION",
    "FINAL_REGRESSION",
    "CALIBRATION",
    "CONFORMAL",
    "EVALUATION",
    "PROMOTION_ROUTE",
    "FINALIZE",
)
UNIT_TYPES = ("fold", "candidate", "seed", "artifact")
RESUME_SIGNATURE_FIELDS = (
    "trainer_sha256",
    "execution_code_commit",
    "config_sha256",
    "promotion_contract_sha256",
    "training_contract_sha256",
    "dataset_signature",
    "fold_signature",
    "feature_signature",
)
_ALLOWED = {
    "NOT_STARTED": {"RUNNING"},
    "RUNNING": {"PARTIAL", "FAILED", "COMPLETE"},
    "PARTIAL": {"RUNNING", "FAILED", "COMPLETE"},
    "FAILED": {"RUNNING"},
    "COMPLETE": set(),
}


class StateTransitionError(RuntimeError):
    pass


class ResumeSignatureMismatch(RuntimeError):
    def __init__(self, mismatches: list[dict[str, Any]]):
        self.mismatches = mismatches
        super().__init__("RESUME_SIGNATURE_MISMATCH:" + canonical_json(mismatches))


def _transition_allowed(current: str, new: str, *, resume: bool = False) -> bool:
    if current == new:
        return True
    if current == "FAILED" and new == "RUNNING":
        return resume
    return new in _ALLOWED[current]


@dataclass
class UnitState:
    unit_type: str
    unit_id: str
    status: str = "NOT_STARTED"
    required_artifacts: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    exception_summary: str | None = None

    def __post_init__(self) -> None:
        if self.unit_type not in UNIT_TYPES:
            raise ValueError("UNKNOWN_UNIT_TYPE:" + self.unit_type)
        if self.status not in STATUSES:
            raise ValueError("UNKNOWN_STATE_STATUS:" + self.status)

    def transition(
        self,
        new_status: str,
        *,
        artifacts: Iterable[str] | None = None,
        exception_summary: str | None = None,
        resume: bool = False,
    ) -> None:
        if new_status not in STATUSES or not _transition_allowed(
            self.status, new_status, resume=resume
        ):
            raise StateTransitionError(f"ILLEGAL_UNIT_TRANSITION:{self.status}->{new_status}")
        produced = tuple(sorted(set(self.artifacts if artifacts is None else artifacts)))
        if new_status == "COMPLETE" and not set(self.required_artifacts) <= set(produced):
            raise StateTransitionError("UNIT_COMPLETE_MISSING_ARTIFACT")
        if new_status == "FAILED" and not exception_summary:
            raise StateTransitionError("FAILED_UNIT_REQUIRES_EXCEPTION_SUMMARY")
        self.status = new_status
        self.artifacts = produced
        self.exception_summary = exception_summary

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_type": self.unit_type,
            "unit_id": self.unit_id,
            "status": self.status,
            "required_artifacts": list(self.required_artifacts),
            "artifacts": list(self.artifacts),
            "exception_summary": self.exception_summary,
        }


@dataclass
class StageState:
    name: str
    status: str = "NOT_STARTED"
    units: dict[str, UnitState] = field(default_factory=dict)
    exception_summary: str | None = None

    def __post_init__(self) -> None:
        if self.name not in STAGES:
            raise ValueError("UNKNOWN_TRAINING_STAGE:" + self.name)
        if self.status not in STATUSES:
            raise ValueError("UNKNOWN_STATE_STATUS:" + self.status)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "units": [
                self.units[key].as_dict()
                for key in sorted(self.units)
            ],
            "exception_summary": self.exception_summary,
        }


@dataclass
class TrainingExecutionState:
    schema_version: str
    run_id: str
    status: str
    current_stage: str | None
    trainer_sha256: str
    execution_code_commit: str
    config_sha256: str
    promotion_contract_sha256: str
    training_contract_sha256: str
    dataset_signature: str
    fold_signature: str
    feature_signature: str
    stages: dict[str, StageState]
    created_at: str
    updated_at: str
    failure_stage: str | None = None
    exception_summary: str | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError("UNKNOWN_STATE_STATUS:" + self.status)
        if self.current_stage is not None and self.current_stage not in STAGES:
            raise ValueError("UNKNOWN_TRAINING_STAGE:" + self.current_stage)
        if tuple(self.stages) != STAGES:
            raise ValueError("STATE_STAGE_SCHEMA_DRIFT")

    @classmethod
    def new(
        cls,
        run_id: str,
        signatures: SignatureBundle,
        *,
        timestamp: str = "1970-01-01T00:00:00+00:00",
    ) -> "TrainingExecutionState":
        values = signatures.as_resume_dict()
        return cls(
            schema_version=STATE_SCHEMA_VERSION,
            run_id=run_id,
            status="NOT_STARTED",
            current_stage=None,
            stages={name: StageState(name=name) for name in STAGES},
            created_at=timestamp,
            updated_at=timestamp,
            **values,
        )

    def signature_bundle(self) -> SignatureBundle:
        return SignatureBundle(
            config_sha256=self.config_sha256,
            promotion_contract_sha256=self.promotion_contract_sha256,
            training_contract_sha256=self.training_contract_sha256,
            dataset_signature=self.dataset_signature,
            fold_signature=self.fold_signature,
            feature_signature=self.feature_signature,
            trainer_sha256=self.trainer_sha256,
            execution_code_commit=self.execution_code_commit,
        )

    def transition(
        self,
        new_status: str,
        *,
        timestamp: str,
        resume: bool = False,
        failure_stage: str | None = None,
        exception_summary: str | None = None,
    ) -> None:
        if new_status not in STATUSES or not _transition_allowed(
            self.status, new_status, resume=resume
        ):
            raise StateTransitionError(f"ILLEGAL_STATE_TRANSITION:{self.status}->{new_status}")
        if new_status == "FAILED" and (not failure_stage or not exception_summary):
            raise StateTransitionError("FAILED_STATE_REQUIRES_FAILURE_INFORMATION")
        if new_status == "COMPLETE" and any(
            stage.status != "COMPLETE" for stage in self.stages.values()
        ):
            raise StateTransitionError("STATE_COMPLETE_WITH_INCOMPLETE_STAGE")
        self.status = new_status
        self.updated_at = timestamp
        self.failure_stage = failure_stage if new_status == "FAILED" else None
        self.exception_summary = exception_summary if new_status == "FAILED" else None

    def add_unit(self, stage: str, unit: UnitState) -> None:
        stage_state = self.stages[stage]
        key = f"{unit.unit_type}:{unit.unit_id}"
        if key in stage_state.units:
            raise StateTransitionError("DUPLICATE_STAGE_UNIT:" + key)
        stage_state.units[key] = unit

    def transition_unit(
        self,
        stage: str,
        unit_type: str,
        unit_id: str,
        new_status: str,
        *,
        timestamp: str,
        artifacts: Iterable[str] | None = None,
        exception_summary: str | None = None,
        resume: bool = False,
    ) -> None:
        key = f"{unit_type}:{unit_id}"
        if key not in self.stages[stage].units:
            raise StateTransitionError("UNKNOWN_STAGE_UNIT:" + key)
        self.stages[stage].units[key].transition(
            new_status,
            artifacts=artifacts,
            exception_summary=exception_summary,
            resume=resume,
        )
        self.updated_at = timestamp

    def transition_stage(
        self,
        stage: str,
        new_status: str,
        *,
        timestamp: str,
        resume: bool = False,
        exception_summary: str | None = None,
    ) -> None:
        current = self.stages[stage]
        if new_status not in STATUSES or not _transition_allowed(
            current.status, new_status, resume=resume
        ):
            raise StateTransitionError(
                f"ILLEGAL_STAGE_TRANSITION:{current.status}->{new_status}"
            )
        predecessors = STAGES[:STAGES.index(stage)]
        # Synthetic regression backend validation is independent of the formal
        # classification OOF stage.  It still requires PREFLIGHT, while formal
        # stages retain their original total ordering.
        if stage == "REGRESSION_OOF":
            predecessors = ("PREFLIGHT",)
        if new_status in {"RUNNING", "COMPLETE"} and any(
            self.stages[name].status != "COMPLETE" for name in predecessors
        ):
            raise StateTransitionError("STAGE_PREDECESSOR_INCOMPLETE")
        if new_status == "COMPLETE" and any(
            unit.status != "COMPLETE" for unit in current.units.values()
        ):
            raise StateTransitionError("STAGE_COMPLETE_WITH_INCOMPLETE_UNIT")
        if new_status == "FAILED" and not exception_summary:
            raise StateTransitionError("FAILED_STAGE_REQUIRES_EXCEPTION_SUMMARY")
        current.status = new_status
        current.exception_summary = exception_summary
        self.current_stage = stage
        self.updated_at = timestamp

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "status": self.status,
            "current_stage": self.current_stage,
            **self.signature_bundle().as_resume_dict(),
            "stages": [self.stages[name].as_dict() for name in STAGES],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "failure_stage": self.failure_stage,
            "exception_summary": self.exception_summary,
        }

    def canonical_json(self) -> str:
        return canonical_json(self.as_dict())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TrainingExecutionState":
        stages: dict[str, StageState] = {}
        for stage_value in value["stages"]:
            units = {
                f"{unit['unit_type']}:{unit['unit_id']}": UnitState(
                    unit_type=unit["unit_type"],
                    unit_id=unit["unit_id"],
                    status=unit["status"],
                    required_artifacts=tuple(unit["required_artifacts"]),
                    artifacts=tuple(unit["artifacts"]),
                    exception_summary=unit.get("exception_summary"),
                )
                for unit in stage_value["units"]
            }
            stages[stage_value["name"]] = StageState(
                name=stage_value["name"],
                status=stage_value["status"],
                units=units,
                exception_summary=stage_value.get("exception_summary"),
            )
        kwargs = {field: value[field] for field in RESUME_SIGNATURE_FIELDS}
        return cls(
            schema_version=value["schema_version"],
            run_id=value["run_id"],
            status=value["status"],
            current_stage=value["current_stage"],
            stages=stages,
            created_at=value["created_at"],
            updated_at=value["updated_at"],
            failure_stage=value.get("failure_stage"),
            exception_summary=value.get("exception_summary"),
            **kwargs,
        )


def resume_signature_gate(
    expected: SignatureBundle,
    observed: SignatureBundle | TrainingExecutionState | dict[str, Any],
) -> list[dict[str, Any]]:
    expected_values = expected.as_resume_dict()
    if isinstance(observed, TrainingExecutionState):
        observed_values = observed.signature_bundle().as_resume_dict()
    elif isinstance(observed, SignatureBundle):
        observed_values = observed.as_resume_dict()
    else:
        observed_values = {field: observed.get(field) for field in RESUME_SIGNATURE_FIELDS}
    rows = [
        {
            "field": field,
            "expected": expected_values[field],
            "observed": observed_values[field],
            "match": observed_values[field] == expected_values[field],
        }
        for field in RESUME_SIGNATURE_FIELDS
    ]
    mismatches = [row for row in rows if not row["match"]]
    if mismatches:
        raise ResumeSignatureMismatch(mismatches)
    return rows
