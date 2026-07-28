from __future__ import annotations

from pathlib import Path

from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.regression import (
    REGRESSION_TARGETS,
    build_regression_crossfit_plan,
    load_regression_metadata,
    regression_backend_audit,
    synthetic_regression_fixture,
)


def test_metadata_partition_plan_and_read_only_audit():
    contract = load_frozen_contract()
    metadata = load_regression_metadata(contract)
    plans = build_regression_crossfit_plan(metadata, contract)
    audit = regression_backend_audit(contract)
    assert REGRESSION_TARGETS == contract.targets.regression_targets
    assert metadata.counts["round1_eligible_count"] == 100
    assert metadata.counts["round1_ineligible_count"] == 28
    assert [len(plan.held_out_indices) for plan in plans] == [24, 22, 34, 20]
    assert sum(len(plan.held_out_indices) for plan in plans) == 100
    assert audit["status"] == "PASS" and audit["fit_calls"] == 0
    assert audit["formal_regression_oof_calls"] == audit["sealed_test_target_reads"] == 0


def test_synthetic_fixture_trains_three_seeds_resumes_and_fresh_reloads(tmp_path: Path):
    result = synthetic_regression_fixture(load_frozen_contract(), tmp_path, "pytest-regression")
    audit = result["audit"]
    assert result["status"] == "PASS"
    assert audit["synthetic_regression_fit_calls"] == 12
    assert audit["sample_oof_rows"] == 100 and audit["target_oof_rows"] == 400 and audit["seed_target_oof_rows"] == 1200
    assert audit["ineligible_rows"] == 28 and audit["ineligible_prediction_count"] == 0
    assert audit["failure_injection_executed"] and audit["resume_executed"]
    assert audit["completed_seed_sha_mtime_preserved"] and audit["artifact_drift_guard_pass"]
    assert audit["independent_seed_artifacts"] and audit["fresh_process"]["all_match"]
    assert audit["formal_regression_oof_calls"] == audit["formal_training_calls"] == audit["sealed_test_target_reads"] == 0
