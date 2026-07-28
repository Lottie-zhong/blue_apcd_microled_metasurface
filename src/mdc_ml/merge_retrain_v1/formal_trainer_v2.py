from __future__ import annotations

"""Formal MDC-ML execution runner v2.

This module defines the complete persisted execution contract while keeping
formal data execution behind an explicit future authorization gate.  The only
callable execution path in this freeze is the synthetic fixture.
"""

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from .classification import synthetic_classification_fixture
from .contracts import FrozenContract, ROOT, canonical_json, sha256_file
from .regression import REGRESSION_TARGETS, synthetic_regression_fixture

SCHEMA_VERSION = "mdc_ml_formal_execution_runner_v2"
IMPLEMENTATION_SCOPE = "FORMAL_EXECUTION_CODE_ONLY_SYNTHETIC_FREEZE"
FORMAL_ARTIFACTS = (
    "classification_oof_predictions.csv", "regression_oof_sample_predictions.csv",
    "classifier_calibration_thresholds.json", "regression_conformal_quantiles.json",
    "v1_v2_oof_comparison.json", "validation_comparison.json",
    "paired_group_bootstrap.json", "promotion_route.json", "execution_manifest_v2.json",
)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, path)


def _commit() -> str:
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()


@dataclass(frozen=True)
class FormalExecutionPlan:
    implementation_head: str
    conformal_coverage: float = 0.90
    conformal_alpha: float = 0.10
    conformal_source: str = "original_calibration_only"
    targets: tuple[str, ...] = REGRESSION_TARGETS
    sealed_test_target_reads: int = 0
    sealed_test_prediction_calls: int = 0
    sealed_test_evaluation_count: int = 1
    formal_classification_oof_calls: int = 0
    formal_regression_oof_calls: int = 0
    formal_training_calls: int = 0
    tmm_calls: int = 0
    fdtd_calls: int = 0
    lumerical_calls: int = 0


def formal_execution_plan() -> FormalExecutionPlan:
    return FormalExecutionPlan(implementation_head=_commit())


def require_formal_authorization(*, authorized: bool) -> None:
    if not authorized:
        raise RuntimeError("FORMAL_MERGE_RETRAIN_EXECUTION_REQUIRES_SEPARATE_AUTHORIZATION")


def run_formal_classification_oof(*, authorized: bool, **_: Any) -> None:
    require_formal_authorization(authorized=authorized)
    raise RuntimeError("FORMAL_INPUT_LOADER_REQUIRED_AT_AUTHORIZED_EXECUTION")


def run_formal_regression_oof(*, authorized: bool, **_: Any) -> None:
    require_formal_authorization(authorized=authorized)
    raise RuntimeError("FORMAL_INPUT_LOADER_REQUIRED_AT_AUTHORIZED_EXECUTION")


def run_final_competition(*, authorized: bool, **_: Any) -> None:
    require_formal_authorization(authorized=authorized)
    raise RuntimeError("FORMAL_INPUT_LOADER_REQUIRED_AT_AUTHORIZED_EXECUTION")


def synthetic_full_trainer_fixture(contract: FrozenContract, output_root: Path, run_id: str) -> dict[str, Any]:
    """Exercise both frozen backends and emit a complete v2 manifest; no formal input is read."""
    root = output_root.resolve() / run_id
    if ROOT.resolve() in root.parents or root == ROOT.resolve():
        raise RuntimeError("FIXTURE_OUTPUT_ROOT_MUST_BE_OUTSIDE_WORKTREE")
    root.mkdir(parents=True, exist_ok=False)
    classification = synthetic_classification_fixture(contract, root, "classification")
    regression = synthetic_regression_fixture(contract, root, "regression")
    plan = formal_execution_plan()
    manifest = {
        "schema_version": SCHEMA_VERSION, "implementation_scope": IMPLEMENTATION_SCOPE,
        "execution_code_commit": plan.implementation_head, "formal_artifacts": list(FORMAL_ARTIFACTS),
        "formal_contract": asdict(plan), "classification_fixture": classification,
        "regression_fixture": regression, "v1_v2_oof_comparison": "planned_at_authorized_execution",
        "validation_comparison": "planned_at_authorized_execution",
        "paired_group_bootstrap": "planned_at_authorized_execution",
        "promotion_and_route": "planned_at_authorized_execution", "status": "PASS",
    }
    _atomic_json(root / "execution_manifest_v2.json", manifest)
    audit = {"status": "PASS", "execution_code_commit": plan.implementation_head,
             "formal_classification_oof_calls": 0, "formal_regression_oof_calls": 0,
             "formal_training_calls": 0, "sealed_test_target_reads": 0,
             "sealed_test_prediction_calls": 0, "sealed_test_evaluation_count": 1,
             "TMM_calls": 0, "FDTD_calls": 0, "Lumerical_calls": 0,
             "classification_fixture_status": classification["status"], "regression_fixture_status": regression["status"],
             "manifest_sha256": sha256_file(root / "execution_manifest_v2.json")}
    _atomic_json(root / "full_trainer_fixture_audit_v2.json", audit)
    return {"status": "PASS", "audit": audit, "audit_path": str(root / "full_trainer_fixture_audit_v2.json")}
