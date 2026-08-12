import importlib.util, json
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "freeze_mdc_hf_surrogate_v3_final_5seed_policy_v1.py"
spec = importlib.util.spec_from_file_location("final_5seed_policy", SCRIPT)
policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)
def test_exact_final_seed_set_and_no_performance_selection():
    result = policy.validate_seeds()
    assert result["seed_order"] == [20260813, 20260814, 20260815, 20260816, 20260817]
    assert result["seed_count"] == 5
    assert result["selection"] == "NO_PERFORMANCE_SELECTION_OR_DELETION"
    assert result["additional_seed_allowed"] is False
    with pytest.raises(policy.PolicyError): policy.validate_seeds((20260813, 20260814, 20260815, 20260816))
def test_ensemble_is_unweighted_decoded_profile_mean():
    data = json.loads((policy.OUT / "final_ensemble_policy.json").read_text(encoding="utf-8"))
    assert data["aggregation"] == "arithmetic_mean_of_five_decoded_normalized_joint_profiles"
    assert data["seed_weights"] == [0.2] * 5
    assert data["performance_weighting"] is False
    assert data["best_seed_selection"] is False
    assert data["median_ensemble"] is False
    assert data["parameter_or_weight_averaging"] is False
def test_loss_contract_excludes_power_and_auxiliary_load():
    audit = policy.validate_loss()
    assert audit["sum"] == pytest.approx(1.0)
    assert audit["power_loss"] == 0.0
    assert audit["power_head"] == "ABSENT"
    assert audit["auxiliary_loss"] == "NOT_LOAD_BEARING"
def test_fixed_epoch_and_no_validation_policy():
    data = json.loads((policy.OUT / "final_training_interface.json").read_text(encoding="utf-8"))
    assert data["final_epoch"] == 117
    assert data["epoch_policy"] == "exactly_117_epochs; no validation; no early stopping; no checkpoint hunting"
    assert data["checkpoint_policy"] == "only_epoch_117"
    assert data["training_authorized"] is False
def test_shared_full_development_pca_routing_without_fit():
    data = json.loads((policy.OUT / "full_development_pca_scaler_routing_policy.json").read_text(encoding="utf-8"))
    assert data["full_development_geometry_count"] == 200
    assert data["full_development_case_count"] == 1200
    assert data["pca_components"] == 32
    assert data["shared_by_final_seeds"] is True
    assert data["per_seed_pca_fit"] is False
    assert data["fit_calls_this_task"] == 0
def test_exact_membership_and_sealed_metadata_only():
    result = policy.validate_membership()
    assert result["geometry_counts"] == {"DOE96": 96, "V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3": 40, "AL64": 64, "total": 200}
    assert result["case_counts"]["total"] == 1200
    assert result["cases_per_geometry"] == 6
    assert result["v3_test40_geometry_overlap"] == 0
    assert result["al64_labels_read"] == 0
    assert result["v3_test40_labels_read"] == 0
def test_warning_and_capability_scope_are_not_dropped():
    warning = json.loads((policy.OUT / "known_failure_warning_inheritance.json").read_text(encoding="utf-8"))
    scope = json.loads((policy.OUT / "capability_scope_assertion.json").read_text(encoding="utf-8"))
    assert warning["warning"] == "KNOWN_FAILURE_LEVEL_STRATUM_WARNING"
    assert warning["reference"] == {"JS": 0.22933, "weighted_L1": 1.1506}
    assert warning["must_remain_visible"] is True
    assert scope["external_validation_claim"] is False
    assert scope["quantitative_fdtd_replacement"] is False
def test_all_task_safety_counters_are_zero():
    status = json.loads((policy.OUT / "final_5seed_policy_status.json").read_text(encoding="utf-8"))
    assert all(value == 0 for value in status["safety"].values())
