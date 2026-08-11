from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mdc_hf_surrogate_v3_training_readiness_v1 as readiness


def test_readiness_loader_validates_136_816_and_marks_al64_pending():
    report = readiness.CanonicalV3DevelopmentLoader().load()
    m = report["membership"]
    assert (m["base_geometry_count"], m["base_case_count"]) == (136, 816)
    assert (m["al64_geometry_count"], m["al64_case_count"]) == (64, 384)
    assert (m["total_geometry_count"], m["total_case_count"]) == (200, 1200)
    assert m["al64_pending"] is True
    assert report["formal_training_allowed"] is False
    with pytest.raises(readiness.FormalTrainingRejected):
        readiness.CanonicalV3DevelopmentLoader().load(formal=True)


def test_readiness_loader_consumes_real_al64_completion_metadata():
    completion = readiness.ROOT / "outputs" / "mdc_hf_surrogate_v3_al64_real_2d_fdtd_v1" / "20260810T1355Z_0bfbbd5_targeted_al64_real_2d_fdtd_v3" / "al64_completion_manifest.json"
    report = readiness.CanonicalV3DevelopmentLoader(al64_completion_manifest=completion).load()
    membership = report["membership"]
    assert membership["al64_pending"] is False
    assert membership["status"] == "FORMAL_MEMBERSHIP_COMPLETE"
    assert report["formal_training_allowed"] is True
    gate = readiness.readiness_gate(report, readiness.SealedTest40Guard().audit(), {key: 0 for key in ("FDTD_calls", "TMM_calls", "RCWA_calls", "NP_solver_calls", "neural_fits", "optimizer_calls", "backward_calls", "PCA_fits", "scaler_fits", "V3_Test40_label_reads", "HF15_formal_label_reads", "HF15_diagnostics_value_reads", "R12_formal_label_reads", "R12_diagnostics_value_reads")})
    assert gate["status"] == "READY_FOR_SEPARATE_V3_OOF_TRAINING_AUTHORIZATION"


def test_v3_test40_guard_allows_only_lock_metadata_and_rejects_truth_paths(tmp_path):
    audit = readiness.SealedTest40Guard().audit()
    assert audit["status"] == "PASS"
    assert audit["labels_read"] == 0
    assert audit["truth_paths_scanned"] is False
    with pytest.raises(readiness.SealedTestAccessError):
        readiness.SealedTest40Guard().assert_path_allowed(tmp_path / "MDC_HF_SURROGATE_V3_TEST40_V1" / "labels.parquet")
    with pytest.raises(readiness.SealedTestAccessError):
        readiness.SealedTest40Guard().assert_path_allowed(tmp_path / "v3_test40_target_truth.json")


def test_candidate_registry_is_deterministic_and_profile_only():
    first = readiness.load_candidate_registry()
    second = readiness.load_candidate_registry()
    assert first["serialization_sha256"] == second["serialization_sha256"]
    assert [x["id"] for x in first["candidates"]] == ["V3-A", "V3-B", "V3-C"]
    assert all(x["latent_output_dimension"] == "PCA32" for x in first["candidates"])
    assert all(x["latent_head"] == "linear_signed" for x in first["candidates"])
    assert all(x["power_head"] == "ABSENT_FROM_FORMAL_MODEL" for x in first["candidates"])
    assert all(x["auxiliary_head"] == "NOT_LOAD_BEARING" for x in first["candidates"])


def test_candidate_models_are_pure_forward_structural_outputs():
    import torch

    torch.manual_seed(7)
    registry = readiness.load_candidate_registry()
    for entry in registry["candidates"]:
        config = readiness.CandidateConfig(**{key: entry[key] for key in ("id", "backbone", "input_width", "latent_width", "profile_head_width", "residual_blocks", "residual_width", "dropout", "weight_decay", "regularization", "purpose")})
        model = readiness.build_candidate_model(config).eval()
        output = model(torch.zeros(2, config.input_width))
        assert set(output) == {"latent"}
        assert tuple(output["latent"].shape) == (2, 32)
        assert model.power_head is None
        assert model.auxiliary_head is None


def test_profile_loss_exact_weights_finite_and_no_power_load_bearing():
    rng = np.random.default_rng(11)
    pred = rng.random((3, 4, 5))
    truth = rng.random((3, 4, 5))
    result = readiness.profile_only_loss_numpy(pred, truth)
    assert abs(sum(readiness.PROFILE_WEIGHTS.values()) - 1.0) < 1e-12
    assert all(np.isfinite(value) for value in result.values())
    assert result["power_loss"] == 0.0
    assert result["auxiliary_loss"] == 0.0
    audit = readiness.loss_contract_audit()
    assert audit["status"] == "PASS"
    assert audit["power_target_load_bearing"] is False


def test_profile_loss_torch_definition_is_differentiable_without_backward():
    import torch

    pred = torch.rand(2, 3, 4, requires_grad=True)
    truth = torch.rand(2, 3, 4)
    result = readiness.profile_only_loss_torch(pred, truth)
    assert result["total"].requires_grad
    assert result["power_loss"].item() == 0.0
    assert result["auxiliary_loss"].item() == 0.0
    # Deliberately no backward()/optimizer call in this readiness task.


def test_outer_and_inner_geometry_grouped_splits_have_no_leakage():
    rows = readiness.read_csv(readiness.DEV_GEOMETRIES)
    outer = readiness.outer_geometry_folds(rows)
    assert len(outer["folds"]) == 5
    all_hashes = set().union(*(set(values) for values in outer["folds"].values()))
    assert len(all_hashes) == 136
    for held_out in outer["folds"].values():
        inner = readiness.inner_stop_membership(rows, held_out)
        assert inner["disjoint_from_outer_held_out"]
        assert set(inner["inner_stop_geometry_hashes"]).isdisjoint(held_out)


def test_duration_guards_reject_short_outer_or_legacy_epoch_three():
    assert readiness.duration_contract_audit()["status"] == "PASS"
    with pytest.raises(readiness.ReadinessError):
        readiness.validate_training_state({"status": "completed", "best_epoch": 3, "stopping_metric_source": "inner_stop"})
    with pytest.raises(readiness.ReadinessError):
        readiness.validate_training_state({"status": "completed", "best_epoch": 50, "stopping_metric_source": "outer_held_out"})
    with pytest.raises(readiness.ReadinessError):
        readiness.validate_training_state({"status": "completed", "best_epoch": 50, "final_epoch": 3, "stopping_metric_source": "inner_stop"})


def test_fit_budget_hard_caps_45_unique_identities():
    budget = readiness.FitBudget()
    for candidate in ("V3-A", "V3-B", "V3-C"):
        for seed in (20260810, 20260811, 20260812):
            for fold in range(5):
                budget.reserve(candidate, seed, fold)
    assert len(budget.reservations) == 45
    with pytest.raises(readiness.ReadinessError, match="BUDGET_EXCEEDED"):
        budget.reserve("V3-A", 20260810, 99)


def test_execution_state_machine_is_deterministic_and_non_dispatching():
    identity = readiness.FormalFitIdentity("V3-A", 20260810, 0)
    first = readiness.FormalRunStateMachine(identity)
    for state in ("seed", "outer_fold", "inner_stop", "epoch"):
        first.transition(state, epoch=0 if state == "epoch" else None)
    first.transition("completed")
    second = readiness.FormalRunStateMachine(identity)
    for state in ("seed", "outer_fold", "inner_stop", "epoch"):
        second.transition(state, epoch=0 if state == "epoch" else None)
    second.transition("completed")
    assert first.audit() == second.audit()
    assert first.audit()["dispatch_calls"] == 0
    assert first.audit()["training_executed"] is False
    with pytest.raises(readiness.ReadinessError):
        readiness.FormalRunStateMachine(identity).transition("completed")


def test_anti_collapse_metrics_are_computable_and_thresholds_not_invented():
    rng = np.random.default_rng(21)
    latent = rng.normal(size=(6, 4))
    pred = latent + 0.01 * rng.normal(size=latent.shape)
    profiles = rng.random((6, 3, 4))
    metrics = readiness.anti_collapse_metrics(pred, latent, profiles, profiles)
    assert metrics["profile_metrics"]["joint_JS"] >= 0.0
    assert metrics["profile_pairwise_diversity_ratio"] > 0.0
    assert metrics["promotion_thresholds"] == "NOT_DEFINED_IN_PLAN_FREEZE"


def test_pca_scaler_membership_guard_blocks_outer_held_out_leakage():
    assert readiness.pca_scaler_leakage_guard(outer_training={"a", "b"}, outer_held_out={"c"}, fit_membership={"a"})["status"] == "PASS"
    with pytest.raises(readiness.ReadinessError):
        readiness.pca_scaler_leakage_guard(outer_training={"a", "b"}, outer_held_out={"c"}, fit_membership={"a", "c"})


def test_pending_readiness_gate_and_zero_counters():
    loader = readiness.CanonicalV3DevelopmentLoader().load()
    sealed = readiness.SealedTest40Guard().audit()
    counters = {key: 0 for key in ("FDTD_calls", "TMM_calls", "RCWA_calls", "NP_solver_calls", "neural_fits", "optimizer_calls", "backward_calls", "PCA_fits", "scaler_fits", "V3_Test40_label_reads", "HF15_formal_label_reads", "HF15_diagnostics_value_reads", "R12_formal_label_reads", "R12_diagnostics_value_reads")}
    gate = readiness.readiness_gate(loader, sealed, counters)
    assert gate["status"] == "WAITING_FOR_AL64_COMPLETION"
    assert gate["formal_training_allowed"] is False
    assert gate["zero_solver_training_counters_ok"] is True


def test_development_loader_roles_exclude_v3_test40():
    report = readiness.CanonicalV3DevelopmentLoader().load()
    assert report["base_roles"] == ["DOE96_FORMAL_DEVELOPMENT", "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3"]
    assert all("V3_TEST40" not in role for role in report["base_roles"])
