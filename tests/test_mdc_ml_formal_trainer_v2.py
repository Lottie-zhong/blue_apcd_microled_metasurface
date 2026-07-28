from pathlib import Path

import pytest

from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_trainer_v2 import (
    formal_execution_plan, require_formal_authorization, synthetic_full_trainer_fixture,
)


def test_formal_plan_is_guarded_and_has_fixed_conformal_contract(tmp_path: Path):
    plan = formal_execution_plan()
    assert (plan.conformal_coverage, plan.conformal_alpha) == (0.90, 0.10)
    assert plan.sealed_test_evaluation_count == 1
    with pytest.raises(RuntimeError, match="REQUIRES_SEPARATE_AUTHORIZATION"):
        require_formal_authorization(authorized=False)


def test_full_trainer_synthetic_fixture_has_no_formal_calls(tmp_path: Path):
    result = synthetic_full_trainer_fixture(load_frozen_contract(), tmp_path, "full")
    assert result["status"] == "PASS"
    assert result["audit"]["formal_training_calls"] == 0
    assert result["audit"]["formal_regression_oof_calls"] == 0
