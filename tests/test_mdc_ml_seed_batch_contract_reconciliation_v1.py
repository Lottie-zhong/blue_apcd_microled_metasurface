import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT / "configs" / name).read_text(encoding="utf-8"))

def test_classification_fold_seed_contract_is_canonical():
    c = load("classification_fixed_v1_training_contract_v2.json")
    assert c["contract_id"] == "MDC_CLASSIFICATION_FIXED_V1_SEEDS_V2"
    assert c["fold_contract"]["canonical_fold_order"] == [0, 1, 2, 3]
    assert c["fold_contract"]["estimator_seed_by_fold"] == {str(i): 20260720 + i for i in range(4)}
    assert c["fold_contract"]["held_out_counts"] == [31, 34, 39, 24]
    assert c["calibration"]["randomness_status"] == "NOT_APPLICABLE_DETERMINISTIC"
    assert c["threshold"]["randomness_status"] == "NOT_APPLICABLE_DETERMINISTIC"

def test_regression_batch_contract_replays_exact_counts():
    c = load("regression_fixed_v1_training_contract_v2.json")
    rows = c["fold_contract"]["train_rows_by_fold"]
    assert c["batch_contract"]["regression_batch_contract"] == "MINIBATCH_128"
    assert c["batch_contract"]["data_materialization"] == "FULL_FOLD_TENSOR_IN_MEMORY"
    assert c["batch_contract"]["expected_optimizer_steps_per_epoch"] == [(n + 127) // 128 for n in rows]
    assert c["batch_contract"]["last_batch_rows_by_fold"] == [n % 128 for n in rows]
    assert c["batch_contract"]["drop_last"] is False
    assert c["seeds"]["model_seeds"] == [20260720, 20260721, 20260722]

def test_readiness_is_no_run_and_contracts_are_frozen():
    r = load("training_readiness_status_v3.json")
    assert r["status"] == "TRAINING_CONTRACT_READY_NO_RUN"
    for key in ("training_runs", "estimator_fit_calls", "optimizer_steps", "backward_calls", "calibration_fits", "conformal_fits", "solver_calls"):
        assert r[key] == 0
    assert r["hf15_formal_label_reads"] == 0
    assert r["sealed_test_reads"] == 0

def test_execution_policy_forbids_training_and_external_reads():
    c = load("training_execution_contract_v2.json")
    assert c["hyperparameter_search_runs"] == 0
    assert c["architecture_comparison_runs"] == 0
    assert c["hf15_evaluation_runs"] == 0
    assert "optimizer.step during static tests" in c["forbidden_operations"]
