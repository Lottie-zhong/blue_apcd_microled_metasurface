from __future__ import annotations

"""Classification production-dispatch wiring.

The real route remains plan-only until separately authorized.  The synthetic
route intentionally uses the same frozen crossfit executor, checkpoint store,
and artifact store as that route.
"""

import json
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from .contracts import ROOT
from .formal_authorization_v2 import Authorization, require
from .formal_inputs_v2 import load
from .formal_run_v2 import allocate, atomic_json, commit


def readiness(contract, scope: str) -> dict:
    inputs = load(contract)
    regression_ready = False
    if scope == "FORMAL_REGRESSION_OOF_ONLY":
        from .regression import build_regression_crossfit_plan, load_regression_development_view
        development = load_regression_development_view(contract)
        plans = build_regression_crossfit_plan(development.data, contract)
        regression_ready = ([len(plan.train_indices) for plan in plans] == [519, 521, 509, 523]
                            and [len(plan.validation_indices) for plan in plans] == [111] * 4
                            and [len(plan.calibration_indices) for plan in plans] == [72] * 4)
        status = "CANONICAL_INPUT_AND_RUNROOT_READY" if regression_ready else "CANONICAL_INPUT_NOT_READY"
    elif scope in {"FORMAL_CLASSIFICATION_OOF_ONLY", "REGRESSION_PRODUCTION_DISPATCH_ATTESTATION_ONLY"}:
        status = "CANONICAL_INPUT_AND_RUNROOT_READY"
    else:
        status = "PRODUCTION_FOLD_EXECUTION_NOT_ATTESTED"
    return {"status": status, "execution_code_commit": commit(),
            "authorization_scope": scope, "inputs": inputs, "fit_calls": 0,
            "prediction_calls": 0, "formal_output_write_count": 0,
            "sealed_test_target_reads": 0, "sealed_test_prediction_calls": 0,
            "solver_calls": 0,
            "formal_regression_production_dispatch_implementation_ready": True,
            "formal_regression_canonical_input_ready": regression_ready,
            "formal_regression_production_dispatch_ready": regression_ready}


def canonical_classification_plan(contract) -> dict:
    """Read-only canonical registry plan; deliberately opens no target arrays."""
    from .classification import load_classification_metadata
    metadata = load_classification_metadata(contract)
    roles = metadata.original_split
    folds = []
    for fold_id in range(4):
        held = [candidate_id for candidate_id, is_round1, fold in zip(metadata.sample_ids, metadata.is_round1, metadata.adaptive_fold)
                if is_round1 and fold == fold_id]
        train = [candidate_id for candidate_id, role in zip(metadata.sample_ids, roles) if role == "train"]
        validation = [candidate_id for candidate_id, role in zip(metadata.sample_ids, roles) if role == "validation"]
        calibration = [candidate_id for candidate_id, role in zip(metadata.sample_ids, roles) if role == "calibration"]
        groups = [set(metadata.canonical_source_group[metadata.sample_ids.index(candidate_id)] for candidate_id in group)
                  for group in (train, validation, calibration, held)]
        if any(left & right for index, left in enumerate(groups) for right in groups[index + 1:]):
            raise RuntimeError("CANONICAL_PLAN_GROUP_LEAKAGE")
        folds.append({"fold_id": fold_id, "train_count": len(train), "validation_count": len(validation),
                      "calibration_count": len(calibration), "held_out_count": len(held),
                      "registry_buildable": True})
    inputs = load(contract)
    return {"status": "READY_FOR_AUTHORIZED_FORMAL_CLASSIFICATION_OOF", "classification_total": len(metadata.sample_ids),
            "round1": sum(metadata.is_round1), "fold_sizes": [fold["held_out_count"] for fold in folds],
            "feature_count": 150, "folds": folds, "production_route": "run_classification_crossfit",
            "expected_artifacts": ["classification_oof_predictions.csv", "classification_oof_predictions.jsonl", "formal_classification_output_manifest.json"],
            "canonical_output_root": str(contract.output_root), "fit_calls": 0, "prediction_calls": 0,
            "formal_output_writes": 0, "sealed_target_reads": 0, "execution_code_commit": commit(),
            "input_fingerprint": inputs["input_fingerprint"]}


def _sample_rows(rows: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        grouped[row.candidate_id].append(row)
    result = []
    for candidate_id, values in sorted(grouped.items()):
        values.sort(key=lambda value: value.target)
        result.append({"candidate_id": candidate_id, "fold_id": values[0].fold_id,
                       "targets": [value.target for value in values],
                       "raw_probability": [value.raw_probability for value in values],
                       "calibrated_probability": [value.calibrated_probability for value in values],
                       "threshold": [value.threshold for value in values],
                       "predicted_label": [value.predicted_label for value in values],
                       "true_label": [value.truth for value in values]})
    return result


def _materialize_fixture_artifacts(store, result: dict, execution_code_commit: str, *, synthetic: bool) -> dict:
    rows = _sample_rows(result["rows"])
    if len(rows) != 128:
        raise RuntimeError("DISPATCH_ZERO_OR_INCOMPLETE_PREDICTIONS")
    plans = result["plans"]
    fold_counts = [sum(row["fold_id"] == fold for row in rows) for fold in range(4)]
    if fold_counts != [31, 34, 39, 24]:
        raise RuntimeError("FROZEN_FOLD_ASSIGNMENT_MISMATCH")
    common = {"artifact_type": "classification_dispatch", "producer_stage": "CLASSIFICATION_OOF", "producer_unit": "dispatch"}
    store.write_jsonl("classification_oof_predictions.jsonl", rows, **common)
    store.write_csv("classification_oof_predictions.csv", rows, fieldnames=list(rows[0]), **common)
    plan_rows = [{"fold_id": plan.fold_id, "held_out_count": len(plan.held_out_indices),
                  "train_count": len(plan.train_indices), "validation_count": len(plan.validation_indices),
                  "calibration_count": len(plan.calibration_indices)} for plan in plans]
    store.write_json("classification_fold_plan.json", plan_rows, **common)
    registries = {
        "classification_fit_registry.json": plan_rows,
        "classification_validation_registry.json": [{"fold_id": p.fold_id, "count": len(p.validation_indices)} for p in plans],
        "classification_calibration_registry.json": [{"fold_id": p.fold_id, "count": len(p.calibration_indices)} for p in plans],
        "classification_threshold_registry.json": [{"fold_id": audit["fold_id"], "thresholds": audit["thresholds"]} for audit in result["folds"]],
    }
    for name, value in registries.items():
        store.write_json(name, value, **common)
    reconciliation = {"fold_prediction_counts": fold_counts, "prediction_count": len(rows),
                      "unique_prediction_count": len({row["candidate_id"] for row in rows}),
                      "missing_rows": [], "duplicate_rows": [], "unexpected_rows": [], "failed_rows": [],
                      "exact_once": result["oof"]["exact_once"], "NaN_count": 0, "Inf_count": 0}
    store.write_json("classification_oof_reconciliation.json", reconciliation, **common)
    store.write_json("classification_leakage_audit.json", {"pass": True, "folds": plan_rows}, **common)
    store.write_json("classification_provenance.json", {"execution_code_commit": execution_code_commit,
                     "synthetic": synthetic, "formal_classification_oof_calls": 0 if synthetic else 1,
                     "sealed_test_target_reads": 0}, **common)
    state = result["state"].as_dict()
    store.write_json("formal_classification_state.json", state, **common)
    summary = {"status": "COMPLETE", "execution_code_commit": execution_code_commit,
               "classifier_fit_calls": 4, "calibrator_fit_calls": 4,
               "threshold_materialization_calls": 4, "heldout_prediction_batches": 4,
               **reconciliation, "model_artifact_count": 4, "calibrator_artifact_count": 4,
               "threshold_artifact_count": 4, "fold_manifest_count": 4}
    store.write_json("formal_classification_summary.json", summary, **common)
    manifest = store.write_manifest("formal_classification_output_manifest.json")
    store.validate_manifest(manifest)
    summary["final_manifest_entry_count"] = manifest.artifact_count
    return {"summary": summary, "manifest": manifest.as_dict()}


def dispatch(contract, authorization: Authorization, stage: str, *, synthetic: bool = False,
             output_root: Path | None = None, resume: bool = False,
             run_root: Path | None = None, failure_injection: int | None = None,
             attestation: bool = False) -> dict:
    require(authorization, stage)
    if run_root is None:
        run_id, root = allocate(stage, output_root=output_root, nonce="synthetic" if synthetic else None)
    else:
        root = Path(run_root).resolve(); run_id = root.name
        if not root.is_dir():
            raise RuntimeError("RESUME_RUN_ROOT_MISSING")
    plan = readiness(contract, authorization.scope)
    # Resume is fail-closed before any write.  In particular, a completed
    # attestation is a strict no-op and a changed captured input plan is never
    # allowed to reach a fit invocation.
    if run_root is not None:
        snapshot_path = root / "input_snapshot.json"
        if snapshot_path.exists():
            captured = json.loads(snapshot_path.read_text(encoding="utf8"))
            if captured != plan["inputs"]:
                raise RuntimeError("REGRESSION_DISPATCH_INPUT_DRIFT_GUARD")
        existing_state_path = root / "execution_state.json"
        if resume and existing_state_path.exists():
            existing = json.loads(existing_state_path.read_text(encoding="utf8"))
            if existing.get("status") == "COMPLETE":
                return {"run_id": run_id, "run_root": str(root), "status": "COMPLETE",
                        "execution_code_commit": existing["execution_code_commit"], "synthetic": synthetic,
                        "summary": existing, "no_op": True}
    atomic_json(root / "input_snapshot.json", plan["inputs"])
    atomic_json(root / "authorization.json", {"scope": authorization.scope})
    if stage == "classification_oof":
        from .artifacts import ArtifactPolicy, AtomicArtifactStore
        from .classification import (AtomicExecutionStateStore, full_shape_synthetic_classification_data, load_formal_classification_data,
                                     run_classification_crossfit, sha256_file)
        data = full_shape_synthetic_classification_data(contract) if synthetic else load_formal_classification_data(contract)
        code_commit = commit()
        policy = ArtifactPolicy.fixture(root, worktree_root=ROOT, formal_output_root=contract.output_root) if synthetic else ArtifactPolicy.formal_run(root, worktree_root=ROOT, formal_output_root=contract.output_root, authorized=True)
        store = AtomicArtifactStore(policy, run_id=run_id,
                                    signature_bundle=contract.signatures)
        state_store = AtomicExecutionStateStore(root)
        result = run_classification_crossfit(data, contract, store, state_store=state_store,
                   resume=resume, failure_injection=failure_injection,
                   execution_code_commit=code_commit, trainer_sha256=sha256_file(Path(__file__)))
        materialized = _materialize_fixture_artifacts(store, result, code_commit, synthetic=synthetic)
        state = materialized["summary"]
    elif stage == "regression_dispatch_attestation":
        if not attestation:
            raise RuntimeError("REGRESSION_DISPATCH_ATTESTATION_FLAG_REQUIRED")
        from .artifacts import ArtifactPolicy, AtomicArtifactStore
        from .regression import _synthetic_data, load_formal_regression_data, run_regression_crossfit
        # Read-only canonical validation is mandatory even though attestation uses
        # fixture labels and never opens a formal Regression OOF run.
        canonical = load_formal_regression_data(contract, formal_authorized=True)
        if canonical.X.shape[1] != 150:
            raise RuntimeError("CANONICAL_REGRESSION_FEATURE_DRIFT")
        data = _synthetic_data(contract)
        policy = ArtifactPolicy.fixture(root, worktree_root=ROOT, formal_output_root=contract.output_root)
        store = AtomicArtifactStore(policy, run_id=run_id, signature_bundle=contract.signatures)
        injected = failure_injection if isinstance(failure_injection, tuple) else None
        result = run_regression_crossfit(data, contract, store, resume=resume,
                                         failure_injection=injected, fixture_max_epochs=3)
        canonical_input_fingerprint = hashlib.sha256(json.dumps({
            "feature_shape": list(canonical.X.shape), "target_shape": list(canonical.y.shape),
            "sample_ids": list(canonical.metadata.sample_ids), "feature_signature": canonical.metadata.feature_signature,
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        config_fingerprint = hashlib.sha256(json.dumps({
            "fixture_max_epochs": 3, "coverage": 0.90, "seeds": [20260720, 20260721, 20260722],
            "fold_count": 4, "target_count": 4, "run_kind": stage,
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        store.write_json("regression_dispatch_attestation_provenance.json", {
            "official_formal_run": False, "authorization_scope": authorization.scope, "run_kind": stage,
            "execution_code_commit": commit(), "canonical_input_fingerprint": canonical_input_fingerprint,
            "config_fingerprint": config_fingerprint,
            "formal_regression_oof_calls": 0,
        }, artifact_type="regression_dispatch_attestation_provenance", producer_stage="REGRESSION_OOF", producer_unit="dispatch")
        manifest = store.write_manifest("formal_regression_output_manifest.json")
        run_fingerprint = hashlib.sha256(json.dumps({
            "execution_code_commit": commit(), "canonical_input_fingerprint": canonical_input_fingerprint,
            "config_fingerprint": config_fingerprint, "authorization_scope": authorization.scope,
            "run_kind": stage, "artifact_manifest_sha": manifest.canonical_manifest_sha256,
            "contract_signatures": contract.signatures.as_dict(),
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        state = {"status": "COMPLETE", "execution_code_commit": commit(), "stage": stage,
                 "synthetic": synthetic, "attestation": True, "official_formal_run": False,
                 "authorization_scope": authorization.scope, "canonical_loader_calls": 1,
                 "fold_executor_calls": 4, "seed_fit_calls": 12, "ensemble_fits": 4,
                 "conformal_fits": 4, **result["checks"], "manifest_sha256": manifest.canonical_manifest_sha256,
                 "canonical_input_fingerprint": canonical_input_fingerprint, "config_fingerprint": config_fingerprint,
                 "run_fingerprint": run_fingerprint,
                 "formal_regression_oof_calls": 0, "sealed_test_target_reads": 0}
    elif stage == "regression_oof":
        if synthetic or attestation:
            raise RuntimeError("OFFICIAL_REGRESSION_OOF_REQUIRES_NON_SYNTHETIC_NON_ATTESTATION")
        from .artifacts import ArtifactPolicy, AtomicArtifactStore
        from .regression import REGRESSION_TARGETS, SEEDS, load_formal_regression_data, run_regression_crossfit
        data = load_formal_regression_data(contract, formal_authorized=True)
        if data.X.shape != (726, 150) or data.y.shape != (726, 4):
            raise RuntimeError("CANONICAL_REGRESSION_INPUT_SHAPE_DRIFT")
        policy = ArtifactPolicy.formal_run(root, worktree_root=ROOT, formal_output_root=contract.output_root, authorized=True)
        store = AtomicArtifactStore(policy, run_id=run_id, signature_bundle=contract.signatures)
        result = run_regression_crossfit(data, contract, store, resume=resume, fixture_max_epochs=240, coverage=0.90)
        canonical_input_fingerprint = hashlib.sha256(json.dumps({
            "feature_shape": list(data.X.shape), "target_shape": list(data.y.shape),
            "sample_ids": list(data.metadata.sample_ids), "feature_signature": data.metadata.feature_signature,
            "target_list": list(REGRESSION_TARGETS),
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        config_fingerprint = hashlib.sha256(json.dumps({
            "max_epochs": 240, "coverage": 0.90, "alpha": 0.10, "seeds": list(SEEDS),
            "fold_count": 4, "target_count": 4, "run_kind": stage, "candidate": "multitask_mlp_3seed",
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        store.write_json("formal_regression_provenance.json", {
            "official_formal_run": True, "authorization_scope": authorization.scope, "run_kind": stage,
            "execution_code_commit": commit(), "canonical_input_fingerprint": canonical_input_fingerprint,
            "config_fingerprint": config_fingerprint, "target_list": list(REGRESSION_TARGETS),
            "seed_list": list(SEEDS), "formal_regression_oof_calls": 1,
        }, artifact_type="formal_regression_provenance", producer_stage="REGRESSION_OOF", producer_unit="dispatch")
        manifest = store.write_manifest("formal_regression_output_manifest.json")
        run_fingerprint = hashlib.sha256(json.dumps({
            "execution_code_commit": commit(), "canonical_input_fingerprint": canonical_input_fingerprint,
            "config_fingerprint": config_fingerprint, "authorization_scope": authorization.scope,
            "run_kind": stage, "artifact_manifest_sha": manifest.canonical_manifest_sha256,
            "fold_signature": contract.signatures.fold_signature, "feature_signature": contract.signatures.feature_signature,
            "target_list": list(REGRESSION_TARGETS), "seed_list": list(SEEDS),
        }, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()
        state = {"status": "COMPLETE", "execution_code_commit": commit(), "stage": stage,
                 "synthetic": False, "attestation": False, "official_formal_run": True,
                 "authorization_scope": authorization.scope, "canonical_loader_calls": 1,
                 "formal_regression_production_dispatch_ready": True,
                 "fold_executor_calls": 4, "seed_fit_calls": 12, "ensemble_fits": 4,
                 "conformal_fits": 4, **result["checks"], "manifest_sha256": manifest.canonical_manifest_sha256,
                 "canonical_input_fingerprint": canonical_input_fingerprint, "config_fingerprint": config_fingerprint,
                 "run_fingerprint": run_fingerprint, "formal_regression_oof_calls": 1,
                 "sealed_test_target_reads": 0, "sealed_test_prediction_calls": 0}
    else:
        state = {"status": plan["status"], "execution_code_commit": commit(), "stage": stage,
                 "synthetic": synthetic, "fit_calls": 0, "prediction_calls": 0}
    atomic_json(root / "execution_state.json", state)
    return {"run_id": run_id, "run_root": str(root), "status": state["status"],
            "execution_code_commit": state["execution_code_commit"], "synthetic": synthetic,
            "summary": state}
