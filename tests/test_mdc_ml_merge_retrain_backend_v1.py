from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import joblib
import pytest
import torch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mdc_ml.merge_retrain_v1 import artifacts as ART
from mdc_ml.merge_retrain_v1 import candidates as CAND
from mdc_ml.merge_retrain_v1 import contracts as CONTRACTS
from mdc_ml.merge_retrain_v1 import state as STATE


EXPECTED_CLASSIFICATION = [
    "dummy_prevalence",
    "dummy_stratified",
    "linear_C_0.1",
    "linear_C_1.0",
    "linear_C_10.0",
    "extra_trees_0",
    "extra_trees_1",
    "hgb_0",
    "hgb_1",
    "multitask_mlp_3seed",
]
EXPECTED_REGRESSION = [
    "dummy_mean",
    "dummy_median",
    "ridge_0.1",
    "ridge_1.0",
    "ridge_10.0",
    "extra_trees_0",
    "extra_trees_1",
    "hgb_0",
    "hgb_1",
    "multitask_mlp_3seed",
]


def _load_trainer(name: str = "backend_test_trainer"):
    path = ROOT / "scripts" / "train_mdc_ml_active_learning_merge_retrain_v1.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


TRAINER = _load_trainer()
SHARED = CAND._load_shared_module()


@pytest.fixture(scope="session")
def contract():
    return CONTRACTS.load_frozen_contract()


@pytest.fixture
def no_fit(monkeypatch):
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        calls.append("forbidden")
        raise AssertionError("FIT_OR_OPTIMIZER_CALL_FORBIDDEN")

    for cls in (
        CAND.DummyClassifier,
        CAND.DummyRegressor,
        CAND.LogisticRegression,
        CAND.Ridge,
        CAND.ExtraTreesClassifier,
        CAND.ExtraTreesRegressor,
        CAND.HistGradientBoostingClassifier,
        CAND.HistGradientBoostingRegressor,
    ):
        monkeypatch.setattr(cls, "fit", forbidden)
    monkeypatch.setattr(SHARED.ClassificationBundle, "fit", forbidden)
    monkeypatch.setattr(SHARED.RegressionBundle, "fit", forbidden)
    monkeypatch.setattr(SHARED.MLPBundle, "fit", forbidden)
    monkeypatch.setattr(torch.optim.Optimizer, "step", forbidden)
    monkeypatch.setattr(torch.optim.AdamW, "step", forbidden)
    monkeypatch.setattr(CAND, "_load_shared_module", lambda: SHARED)
    yield calls
    assert calls == []


@pytest.fixture
def signatures(contract):
    values = contract.signatures
    return CONTRACTS.SignatureBundle(
        config_sha256=values.config_sha256,
        promotion_contract_sha256=values.promotion_contract_sha256,
        training_contract_sha256=values.training_contract_sha256,
        dataset_signature=values.dataset_signature,
        fold_signature=values.fold_signature,
        feature_signature=values.feature_signature,
        trainer_sha256="a" * 64,
        execution_code_commit="b" * 40,
    )


@pytest.mark.parametrize(
    ("attribute", "expected"),
    [
        ("config_sha256", CONTRACTS.EXPECTED_CONFIG_SHA256),
        ("promotion_contract_sha256", CONTRACTS.EXPECTED_PROMOTION_CONTRACT_SHA256),
        ("training_contract_sha256", CONTRACTS.EXPECTED_TRAINING_CONTRACT_SHA256),
        ("fold_signature", CONTRACTS.EXPECTED_FOLD_SIGNATURE),
        ("feature_count", 150),
        ("feature_signature", "cc49c7b99dcf486f373f1add526c4c23174069dc92bace0dae6b8fabbcc3cd69"),
        ("fixed_classification_baseline", "extra_trees_1"),
        ("fixed_regression_baseline", "multitask_mlp_3seed"),
    ],
)
def test_contract_frozen_fields(contract, attribute, expected):
    assert getattr(contract, attribute) == expected


def test_contract_target_order(contract):
    assert contract.targets.regression_targets == CONTRACTS.EXPECTED_REGRESSION_TARGETS


def test_contract_candidate_counts_and_lists(contract):
    assert [item["candidate_id"] for item in contract.classification_allowlist] == EXPECTED_CLASSIFICATION
    assert [item["candidate_id"] for item in contract.regression_allowlist] == EXPECTED_REGRESSION


def test_contract_dummy_regressors_are_distinct(contract):
    items = {item["candidate_id"]: item for item in contract.regression_allowlist}
    assert items["dummy_mean"]["hyperparameters"]["strategy"] == "mean"
    assert items["dummy_median"]["hyperparameters"]["strategy"] == "median"


def test_contract_bounded_sets_and_baselines(contract):
    assert set(contract.bounded_classification_ids) <= set(EXPECTED_CLASSIFICATION)
    assert set(contract.bounded_regression_ids) <= set(EXPECTED_REGRESSION)
    assert contract.fixed_classification_baseline in contract.bounded_classification_ids
    assert contract.fixed_regression_baseline in contract.bounded_regression_ids


def test_contract_training_seeds(contract):
    assert tuple(contract.training_seeds["regressor_ensemble_seeds"]) == (20260720, 20260721, 20260722)


def test_contract_source_references_resolve(contract):
    assert contract.source_references
    assert all(len(reference["source_commit"]) == 40 for reference in contract.source_references)
    assert all(len(reference["source_sha256"]) == 64 for reference in contract.source_references)


def test_contract_unresolved_placeholder_rejected(contract):
    raw = CONTRACTS.thaw(contract.raw_config)
    raw["route_rules"]["backend_test_placeholder"] = "TBD"
    altered = dataclasses.replace(contract, raw_config=CONTRACTS.freeze(raw))
    with pytest.raises(RuntimeError, match="no_unresolved_placeholder"):
        CONTRACTS.validate_frozen_contract(altered)


def test_contract_config_drift_rejected(tmp_path):
    raw = json.loads(CONTRACTS.CONFIG.read_text(encoding="utf-8"))
    raw["contract_id"] = "drift"
    path = tmp_path / "drift.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(RuntimeError, match="config_sha256"):
        CONTRACTS.load_frozen_contract(path)


def test_contract_loader_is_pure_read(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("WRITE_FORBIDDEN")

    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    assert CONTRACTS.load_frozen_contract().config_sha256 == CONTRACTS.EXPECTED_CONFIG_SHA256


def test_contract_signature_bundle(contract):
    assert CONTRACTS.contract_signature_bundle(contract) == contract.signatures.as_dict()


def test_candidate_spec_lists(contract):
    assert [spec.candidate_id for spec in CAND.classification_specs(contract)] == EXPECTED_CLASSIFICATION
    assert [spec.candidate_id for spec in CAND.regression_specs(contract)] == EXPECTED_REGRESSION


@pytest.mark.parametrize(
    ("kind", "candidate_id", "class_name", "parameter", "expected"),
    [
        ("classification", "dummy_prevalence", "DummyClassifier", "strategy", "prior"),
        ("classification", "dummy_stratified", "DummyClassifier", "strategy", "stratified"),
        ("classification", "linear_C_0.1", "LogisticRegression", "C", 0.1),
        ("classification", "linear_C_1.0", "LogisticRegression", "C", 1.0),
        ("classification", "linear_C_10.0", "LogisticRegression", "C", 10.0),
        ("classification", "extra_trees_0", "ExtraTreesClassifier", "n_estimators", 256),
        ("classification", "extra_trees_1", "ExtraTreesClassifier", "n_estimators", 384),
        ("classification", "hgb_0", "HistGradientBoostingClassifier", "max_iter", 180),
        ("classification", "hgb_1", "HistGradientBoostingClassifier", "max_iter", 240),
        ("regression", "dummy_mean", "DummyRegressor", "strategy", "mean"),
        ("regression", "dummy_median", "DummyRegressor", "strategy", "median"),
        ("regression", "ridge_0.1", "Ridge", "alpha", 0.1),
        ("regression", "ridge_1.0", "Ridge", "alpha", 1.0),
        ("regression", "ridge_10.0", "Ridge", "alpha", 10.0),
        ("regression", "extra_trees_0", "ExtraTreesRegressor", "n_estimators", 256),
        ("regression", "extra_trees_1", "ExtraTreesRegressor", "n_estimators", 384),
        ("regression", "hgb_0", "HistGradientBoostingRegressor", "max_iter", 180),
        ("regression", "hgb_1", "HistGradientBoostingRegressor", "max_iter", 240),
    ],
)
def test_all_sklearn_candidates_construct_unfitted(
    contract, no_fit, kind, candidate_id, class_name, parameter, expected
):
    builder = (
        CAND.build_unfitted_classification_candidate
        if kind == "classification"
        else CAND.build_unfitted_regression_candidate
    )
    estimator = builder(contract, candidate_id, 0, 20260720)
    assert estimator.__class__.__name__ == class_name
    assert estimator.get_params(deep=False)[parameter] == expected
    assert not hasattr(estimator, "n_features_in_")


@pytest.mark.parametrize(
    ("kind", "candidate_id"),
    [
        ("classification", "dummy_stratified"),
        ("classification", "extra_trees_0"),
        ("classification", "hgb_0"),
        ("regression", "extra_trees_0"),
        ("regression", "hgb_0"),
    ],
)
def test_target_seed_derivation(contract, no_fit, kind, candidate_id):
    builder = (
        CAND.build_unfitted_classification_candidate
        if kind == "classification"
        else CAND.build_unfitted_regression_candidate
    )
    estimator = builder(contract, candidate_id, 3, 20260730)
    assert estimator.get_params(deep=False)["random_state"] == 20260733


def test_logistic_seed_does_not_add_target_index(contract, no_fit):
    estimator = CAND.build_unfitted_classification_candidate(
        contract, "linear_C_1.0", 3, 20260730
    )
    assert estimator.random_state == 20260730


def test_mlp_ensemble_is_unfitted_and_frozen(contract, no_fit):
    ensemble = CAND.build_unfitted_mlp_ensemble(contract)
    assert ensemble.seeds == (20260720, 20260721, 20260722)
    assert len(ensemble.bundles) == 3
    assert all(bundle.model is None for bundle in ensemble.bundles)
    linear = [module for module in ensemble.prototype.trunk if isinstance(module, torch.nn.Linear)]
    dropout = [module for module in ensemble.prototype.trunk if isinstance(module, torch.nn.Dropout)]
    assert [layer.out_features for layer in linear] == [256, 128]
    assert [layer.p for layer in dropout] == [0.1, 0.1]
    assert ensemble.prototype.cls_head.out_features == 4
    assert ensemble.prototype.reg_head.out_features == 4


@pytest.mark.parametrize("kind", ["classification", "regression"])
def test_mlp_candidate_routes_to_unfitted_ensemble(contract, no_fit, kind):
    builder = (
        CAND.build_unfitted_classification_candidate
        if kind == "classification"
        else CAND.build_unfitted_regression_candidate
    )
    result = builder(contract, "multitask_mlp_3seed", 0, 20260720)
    assert isinstance(result, CAND.UnfittedMLPEnsemble)


def test_candidate_spec_hash_layers_are_deterministic(contract):
    first = CAND.classification_specs(contract)
    second = CAND.classification_specs(contract)
    assert [spec.candidate_spec_sha256 for spec in first] == [
        spec.candidate_spec_sha256 for spec in second
    ]
    assert all(len(spec.full_snapshot_sha256) == 64 for spec in first)
    assert all(len(spec.runtime_projection_sha256) == 64 for spec in first)
    assert all(spec.full_snapshot_sha256 != spec.runtime_projection_sha256 for spec in first)


def test_effective_parameter_drift_rejected(contract, no_fit):
    item = CAND._item(contract, "classification", "linear_C_1.0")
    spec = CAND._candidate_spec(contract, "classification", item, 0, 20260720)
    estimator = CAND._build_sklearn(spec)
    estimator.set_params(C=99.0)
    with pytest.raises(RuntimeError, match="EFFECTIVE_PARAMETER_DRIFT"):
        CAND.effective_parameter_audit(estimator, spec)


def test_unknown_candidate_rejected(contract):
    with pytest.raises(ValueError, match="UNKNOWN_CANDIDATE"):
        CAND.build_unfitted_regression_candidate(contract, "unknown", 0, 1)


def test_outside_bounded_candidate_rejected(contract):
    altered = dataclasses.replace(
        contract,
        bounded_regression_ids=tuple(
            item for item in contract.bounded_regression_ids if item != "ridge_1.0"
        ),
    )
    with pytest.raises(ValueError, match="CANDIDATE_OUTSIDE_BOUNDED_SET"):
        CAND.build_unfitted_regression_candidate(altered, "ridge_1.0", 0, 1)


def test_candidate_factory_audit_zero_fit(contract, no_fit):
    result = CAND.candidate_factory_audit(contract)
    assert result["status"] == "PASS"
    assert result["classification_candidate_count"] == 10
    assert result["regression_candidate_count"] == 10
    assert result["unfitted_mlp_seed_count"] == 3
    assert result["fit_calls"] == 0


def test_state_initialization(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    assert state.status == "NOT_STARTED"
    assert state.current_stage is None
    assert tuple(state.stages) == STATE.STAGES


@pytest.mark.parametrize(
    ("start", "end", "resume"),
    [
        ("NOT_STARTED", "RUNNING", False),
        ("RUNNING", "PARTIAL", False),
        ("RUNNING", "FAILED", False),
        ("PARTIAL", "RUNNING", False),
        ("PARTIAL", "FAILED", False),
        ("FAILED", "RUNNING", True),
    ],
)
def test_legal_state_transitions(signatures, start, end, resume):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.status = start
    kwargs = {}
    if end == "FAILED":
        kwargs = {"failure_stage": "PREFLIGHT", "exception_summary": "expected"}
    state.transition(end, timestamp="t1", resume=resume, **kwargs)
    assert state.status == end


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("NOT_STARTED", "COMPLETE"),
        ("FAILED", "COMPLETE"),
        ("COMPLETE", "RUNNING"),
        ("FAILED", "RUNNING"),
    ],
)
def test_illegal_state_transitions(signatures, start, end):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.status = start
    with pytest.raises(STATE.StateTransitionError):
        state.transition(end, timestamp="t1")


def test_state_complete_terminal(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.transition("RUNNING", timestamp="t1")
    for stage in STATE.STAGES:
        state.transition_stage(stage, "RUNNING", timestamp="t2")
        state.transition_stage(stage, "COMPLETE", timestamp="t3")
    state.transition("COMPLETE", timestamp="t4")
    with pytest.raises(STATE.StateTransitionError):
        state.transition("RUNNING", timestamp="t5")


def test_stage_order_guard(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    with pytest.raises(STATE.StateTransitionError, match="PREDECESSOR"):
        state.transition_stage("REGRESSION_OOF", "RUNNING", timestamp="t")


def test_unit_artifact_completion_gate(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    unit = STATE.UnitState(
        "candidate", "c1", required_artifacts=("models/c1.joblib",)
    )
    state.add_unit("PREFLIGHT", unit)
    state.transition_unit("PREFLIGHT", "candidate", "c1", "RUNNING", timestamp="t1")
    with pytest.raises(STATE.StateTransitionError, match="MISSING_ARTIFACT"):
        state.transition_unit(
            "PREFLIGHT", "candidate", "c1", "COMPLETE", timestamp="t2"
        )
    state.transition_unit(
        "PREFLIGHT",
        "candidate",
        "c1",
        "COMPLETE",
        timestamp="t3",
        artifacts=("models/c1.joblib",),
    )


def test_incomplete_seed_blocks_stage_complete(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.add_unit("PREFLIGHT", STATE.UnitState("seed", "20260720"))
    state.transition_stage("PREFLIGHT", "RUNNING", timestamp="t1")
    with pytest.raises(STATE.StateTransitionError, match="INCOMPLETE_UNIT"):
        state.transition_stage("PREFLIGHT", "COMPLETE", timestamp="t2")


def test_partial_and_failure_information(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.transition("RUNNING", timestamp="t1")
    state.transition("PARTIAL", timestamp="t2")
    state.transition("FAILED", timestamp="t3", failure_stage="PREFLIGHT", exception_summary="boom")
    assert state.failure_stage == "PREFLIGHT"
    assert state.exception_summary == "boom"


def test_resume_signature_gate_pass(signatures):
    rows = STATE.resume_signature_gate(signatures, signatures)
    assert len(rows) == 8
    assert all(row["match"] for row in rows)


@pytest.mark.parametrize("field", STATE.RESUME_SIGNATURE_FIELDS)
def test_each_resume_signature_drift_rejected(signatures, field):
    observed = signatures.as_resume_dict()
    observed[field] = "drift"
    with pytest.raises(STATE.ResumeSignatureMismatch) as caught:
        STATE.resume_signature_gate(signatures, observed)
    assert caught.value.mismatches == [
        {
            "field": field,
            "expected": signatures.as_resume_dict()[field],
            "observed": "drift",
            "match": False,
        }
    ]


def test_state_serialization_is_deterministic(signatures):
    state = STATE.TrainingExecutionState.new("run", signatures)
    state.add_unit("PREFLIGHT", STATE.UnitState("artifact", "b"))
    state.add_unit("PREFLIGHT", STATE.UnitState("artifact", "a"))
    text = state.canonical_json()
    assert text == state.canonical_json()
    restored = STATE.TrainingExecutionState.from_dict(json.loads(text))
    assert restored.canonical_json() == text


@pytest.fixture
def store(tmp_path, contract, signatures):
    policy = ART.ArtifactPolicy.fixture(
        tmp_path / "store",
        worktree_root=ROOT,
        formal_output_root=contract.output_root,
    )
    return ART.AtomicArtifactStore(policy, run_id="run", signature_bundle=signatures)


@pytest.mark.parametrize(
    ("method", "name", "value"),
    [
        ("write_bytes", "a.bin", b"abc"),
        ("write_text", "a.txt", "abc\n"),
        ("write_json", "a.json", {"b": 2, "a": 1}),
        ("write_jsonl", "a.jsonl", [{"a": 1}, {"b": 2}]),
        ("write_csv", "a.csv", [{"a": 1, "b": 2}]),
        ("write_joblib", "a.joblib", {"a": [1, 2]}),
    ],
)
def test_atomic_artifact_formats(store, method, name, value):
    record = getattr(store, method)(
        name,
        value,
        artifact_type=method,
        producer_stage="PREFLIGHT",
        producer_unit="unit",
    )
    assert record.size_bytes > 0
    assert len(record.sha256) == 64
    assert not list(store.root.rglob("*.tmp"))
    if method == "write_joblib":
        assert joblib.load(store.root / name) == value


def test_manifest_deterministic_sorting(tmp_path, contract, signatures):
    manifests = []
    for index, order in enumerate((("b.json", "a.json"), ("a.json", "b.json"))):
        policy = ART.ArtifactPolicy.fixture(
            tmp_path / f"store-{index}",
            worktree_root=ROOT,
            formal_output_root=contract.output_root,
        )
        current = ART.AtomicArtifactStore(
            policy, run_id="same", signature_bundle=signatures, created_at="fixed"
        )
        for name in order:
            current.write_json(
                name,
                {"name": name},
                artifact_type="json",
                producer_stage="PREFLIGHT",
                producer_unit=name,
            )
        manifests.append(current.manifest())
    assert [r.relative_path for r in manifests[0].records] == ["a.json", "b.json"]
    assert manifests[0].canonical_manifest_sha256 == manifests[1].canonical_manifest_sha256


def test_manifest_validation_and_write(store):
    store.write_json(
        "a.json", {"a": 1}, artifact_type="json", producer_stage="PREFLIGHT", producer_unit="a"
    )
    manifest = store.write_manifest()
    store.validate_manifest(manifest)
    assert (store.root / "artifact_manifest_v1.json").is_file()
    assert store.audit_unregistered(ignore=("artifact_manifest_v1.json",)) == ()


def test_manifest_detects_drift(store):
    store.write_text(
        "a.txt", "a", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
    )
    manifest = store.manifest()
    (store.root / "a.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(RuntimeError, match="ARTIFACT_DRIFT"):
        store.validate_manifest(manifest)


def test_manifest_detects_missing(store):
    store.write_text(
        "a.txt", "a", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
    )
    manifest = store.manifest()
    (store.root / "a.txt").unlink()
    with pytest.raises(RuntimeError, match="ARTIFACT_MISSING"):
        store.validate_manifest(manifest)


@pytest.mark.parametrize("path", ["../escape.json", "a/../../escape.json"])
def test_artifact_traversal_rejected(store, path):
    with pytest.raises(ValueError, match="TRAVERSAL"):
        store.write_json(
            path, {}, artifact_type="json", producer_stage="PREFLIGHT", producer_unit="a"
        )


def test_absolute_child_rejected(store, tmp_path):
    with pytest.raises(ValueError, match="TRAVERSAL"):
        store.write_json(
            tmp_path / "escape.json",
            {},
            artifact_type="json",
            producer_stage="PREFLIGHT",
            producer_unit="a",
        )


def test_fixture_root_policy_rejects_worktree(contract, signatures):
    policy = ART.ArtifactPolicy.fixture(
        ROOT / "fixture-forbidden",
        worktree_root=ROOT,
        formal_output_root=contract.output_root,
    )
    with pytest.raises(ValueError, match="SYSTEM_TEMP|WORKTREE"):
        ART.AtomicArtifactStore(policy, run_id="run", signature_bundle=signatures)


def test_formal_root_without_authorization_rejected(contract, signatures):
    policy = ART.ArtifactPolicy.formal(
        contract.output_root,
        worktree_root=ROOT,
        formal_output_root=contract.output_root,
        authorized=False,
    )
    with pytest.raises(PermissionError, match="FORMAL_ARTIFACT_WRITE_NOT_AUTHORIZED"):
        ART.AtomicArtifactStore(policy, run_id="run", signature_bundle=signatures)


def test_overwrite_sha_mismatch_rejected(store):
    store.write_text(
        "a.txt", "a", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
    )
    with pytest.raises(FileExistsError, match="OVERWRITE_SHA_MISMATCH"):
        store.write_text(
            "a.txt", "b", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
        )


def test_symlink_escape_rejected(store, tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    link = store.root / "link"
    try:
        os.symlink(external, link, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink privilege unavailable: {error}")
    with pytest.raises(ValueError, match="ESCAPE"):
        store.write_text(
            "link/a.txt", "a", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
        )


def test_atomic_failure_cleans_temp(store, monkeypatch):
    def fail_replace(*args, **kwargs):
        raise OSError("expected")

    monkeypatch.setattr(ART.os, "replace", fail_replace)
    with pytest.raises(OSError, match="expected"):
        store.write_text(
            "a.txt", "a", artifact_type="text", producer_stage="PREFLIGHT", producer_unit="a"
        )
    assert not list(store.root.rglob("*.tmp"))


def test_unregistered_artifact_audit(store):
    (store.root / "unregistered.txt").write_text("x", encoding="utf-8")
    assert store.audit_unregistered() == ("unregistered.txt",)


def test_trainer_import_is_read_only():
    builder = CONTRACTS._load_merge_builder()
    contract = CONTRACTS.load_frozen_contract()
    before = builder.output_tree(contract.output_root)
    _load_trainer("backend_test_trainer_fresh")
    assert builder.output_tree(contract.output_root) == before


def test_trainer_preflight(contract):
    result = TRAINER.preflight()
    assert result["status"] == "PASS"
    assert result["feature_count"] == 150
    assert result["formal_training_started"] is False


def test_trainer_status_not_started():
    result = TRAINER.status()
    assert result["status"] == "NOT_STARTED"
    assert result["formal_training_calls"] == 0


def test_trainer_backend_audit(contract, no_fit):
    result = TRAINER.backend_audit()
    assert result["status"] == "PASS"
    assert result["classification_candidate_ids"] == EXPECTED_CLASSIFICATION
    assert result["regression_candidate_ids"] == EXPECTED_REGRESSION
    assert result["fit_calls"] == 0
    assert result["formal_output_write_count"] == 0
    assert result["fixture_evidence_scope"] == "INTERFACE_LEVEL_SYNTHETIC_EVIDENCE"


def test_trainer_backend_audit_does_not_change_formal_tree(no_fit):
    builder = CONTRACTS._load_merge_builder()
    contract = CONTRACTS.load_frozen_contract()
    before = builder.output_tree(contract.output_root)
    TRAINER.backend_audit()
    assert builder.output_tree(contract.output_root) == before


def test_trainer_backend_audit_cli():
    result = subprocess.run(
        [sys.executable, str(TRAINER.__file__), "--backend-audit"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.splitlines()[-1])
    assert payload["status"] == "PASS"
    assert payload["regression_candidate_count"] == 10
    assert payload["fit_calls"] == 0


def test_trainer_formal_modes_remain_blocked():
    result = subprocess.run(
        [sys.executable, str(TRAINER.__file__), "--run-oof"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "FORMAL_MODE_REQUIRES" in result.stderr


def test_trainer_classification_only_scope_is_explicit():
    assert TRAINER.FORMAL_PATH_SCOPE == "CLASSIFICATION_ONLY_INCOMPLETE_FORMAL_PATH"
    assert "CLASSIFICATION_ONLY_INCOMPLETE_FORMAL_PATH" in TRAINER.run_oof.__doc__


def test_trainer_legacy_resume_guard(contract):
    TRAINER.resume_guard(
        {
            "config_sha": contract.config_sha256,
            "feature_signature": contract.feature_signature,
        },
        CONTRACTS.thaw(contract.raw_config),
    )


def test_trainer_full_resume_guard_rejects_drift(contract):
    expected = CONTRACTS.SignatureBundle(
        config_sha256=contract.config_sha256,
        promotion_contract_sha256=contract.promotion_contract_sha256,
        training_contract_sha256=contract.training_contract_sha256,
        dataset_signature=contract.signatures.dataset_signature,
        fold_signature=contract.fold_signature,
        feature_signature=contract.feature_signature,
        trainer_sha256=TRAINER.sha(Path(TRAINER.__file__)),
        execution_code_commit=TRAINER._execution_commit(),
    ).as_resume_dict()
    expected["dataset_signature"] = "drift"
    with pytest.raises(STATE.ResumeSignatureMismatch):
        TRAINER.resume_guard(expected, CONTRACTS.thaw(contract.raw_config))
