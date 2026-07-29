from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_execution_v2 import readiness
from mdc_ml.merge_retrain_v1.regression import build_regression_crossfit_plan, load_regression_development_view


def test_regression_development_view_excludes_sealed_test_before_loading_targets():
    view = load_regression_development_view(load_frozen_contract())
    assert view.data.X.shape == (726, 150)
    assert view.data.y.shape == (726, 4)
    assert len(view.ineligible_registry) == 28
    assert len(view.excluded_sealed_registry) == 377
    assert all(row["original_split"] == "test" for row in view.excluded_sealed_registry)
    assert all(role != "test" for role in view.data.metadata.roles)
    plans = build_regression_crossfit_plan(view.data, load_frozen_contract())
    assert [len(p.train_indices) for p in plans] == [519, 521, 509, 523]
    assert [len(p.validation_indices) for p in plans] == [111] * 4
    assert [len(p.calibration_indices) for p in plans] == [72] * 4
    assert [len(p.held_out_indices) for p in plans] == [24, 22, 34, 20]


def test_formal_readiness_is_composite_and_preflight_only():
    state = readiness(load_frozen_contract(), "FORMAL_REGRESSION_OOF_ONLY")
    assert state["formal_regression_canonical_input_ready"] is True
    assert state["formal_regression_production_dispatch_ready"] is True
    assert state["fit_calls"] == state["prediction_calls"] == 0
