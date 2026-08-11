from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
POLICY_SCRIPT = ROOT / "scripts" / "mdc_hf_surrogate_v3_final_epoch_policy_v1.py"
spec = importlib.util.spec_from_file_location("final_epoch_policy", POLICY_SCRIPT)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def fit_records(epochs):
    seeds = (20260810, 20260811, 20260812)
    rows = []
    index = 0
    for fold in range(5):
        for seed in seeds:
            rows.append({"fit_id": f"V3-A__seed{seed}__fold{fold}", "outer_fold": fold, "seed": seed, "eligible_best_epoch": epochs[index], "status": "VALID"})
            index += 1
    return rows


def test_policy_contract_is_frozen_and_outcome_blind():
    audit = policy.policy_audit()
    assert audit["status"] == "PASS"
    assert audit["eligible_epoch_range"] == [50, 400]
    assert audit["rounding"] == "round_half_up"
    assert audit["source_fit_count"] == 15
    assert audit["outer_fold_forbidden"] is True
    assert audit["v3_test40_forbidden"] is True
    assert audit["solver_calls"] == 0
    assert audit["training_fits"] == 0


def test_epoch_below_50_cannot_be_selected_even_if_metric_is_lower():
    result = policy.eligible_best_epoch({3: 0.01, 50: 0.2, 51: 0.2})
    assert result["eligible_best_epoch"] == 50
    assert result["ignored_before_min_epochs"] == [3]


def test_machine_equal_minimum_selects_earliest_epoch():
    result = policy.eligible_best_epoch({50: 0.25, 80: 0.1, 81: 0.1, 100: 0.2})
    assert result["eligible_best_epoch"] == 80


def test_outer_power_auxiliary_and_test40_cannot_drive_checkpoint():
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.eligible_best_epoch({50: 0.2}, uses_outer_fold=True)
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.eligible_best_epoch({50: 0.2}, uses_power=True)
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.eligible_best_epoch({50: 0.2}, uses_auxiliary=True)
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.eligible_best_epoch({50: 0.2}, uses_v3_test40=True)


def test_final_epoch_uses_median_and_round_half_up():
    rows = fit_records([50, 50, 51, 51, 52, 52, 53, 53, 54, 54, 55, 55, 56, 56, 57])
    result = policy.derive_final_epoch(rows, "V3-A")
    assert result["fit_count"] == 15
    assert result["median_best_epoch"] == 53
    assert result["final_epoch"] == 53
    assert result["rounding"] == "round_half_up"

    assert policy.round_half_up(50.5) == 51
    assert policy.round_half_up(51.49) == 51


def test_final_epoch_requires_complete_15_fit_matrix_and_selected_architecture():
    rows = fit_records([50] * 15)
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.derive_final_epoch(rows[:-1], "V3-A")
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.derive_final_epoch(rows, "NONE")
    rows[0]["fold_leakage"] = True
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.derive_final_epoch(rows, "V3-A")


def test_max_epoch_saturation_is_warning_only():
    result = policy.derive_final_epoch(fit_records([400] * 15), "V3-B")
    assert result["final_epoch"] == 400
    assert result["max_epoch_count"] == 15
    assert result["max_epoch_saturation_warning"] == "MAX_EPOCH_SATURATION_WARNING"


def test_full_development_training_semantics_are_fixed():
    rows = fit_records([60] * 15)
    result = policy.derive_final_epoch(rows, "V3-C")
    plan = {"geometry_count": 200, "case_count": 1200, "final_epoch": result["final_epoch"], "validation_split": "none", "early_stopping": False, "checkpoint_hunting": False, "loss_based_epoch_adjustment": False, "v3_test40_access": False}
    assert policy.validate_full_development_training_plan(plan, derived_final_epoch=result["final_epoch"])["status"] == "PASS"
    plan["early_stopping"] = True
    with pytest.raises(policy.FinalEpochPolicyError):
        policy.validate_full_development_training_plan(plan, derived_final_epoch=result["final_epoch"])
