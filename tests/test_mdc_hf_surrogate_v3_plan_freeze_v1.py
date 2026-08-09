from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "freeze_mdc_hf_surrogate_v3_plan_v1.py"


def test_plan_freeze_has_no_solver_or_training_calls():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"solver_calls": 0' in text
    assert '"training_authorized": False' in text
    assert '"labels_read": 0' in text
    assert "subprocess.check_output([sys.executable, \"-m\", \"pip\", \"freeze\"]" in text


def test_al64_contract_is_stratified_and_outcome_free():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "APCD_MDC_V3_AL64_V1" in text
    assert '"ZL1": 32' in text
    assert '"Explicit": 16' in text
    assert '"ZL2": 16' in text
    assert "metadata_distance_to_base136" in text
    assert "M1 power" not in text
    assert "future_labels_status" in text


def test_v3_test40_is_independent_and_frozen_before_training():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "MDC_HF_SURROGATE_V3_TEST40_V1" in text
    assert "V2_Test40" in text and "AL64" in text
    assert "labels_status\": \"NOT_GENERATED\"" in text
    assert "freeze_timing\": \"before any V3 training\"" in text
    assert "selection_key_expression" in text


def test_profile_only_candidates_and_duration_are_preregistered():
    text = SCRIPT.read_text(encoding="utf-8")
    for token in ["V3-A", "V3-B", "V3-C", "max_epochs", "min_epochs", "inner_stop", "outer_held_out_never_used_for_early_stopping", "power_loss", "exact_weights_frozen_before_training"]:
        assert token in text
    assert "candidate_count\": 3" in text
    assert "maximum_unique_neural_fits\": 45" in text


def test_no_v2_final_epoch_three_inheritance():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"final_epoch_3_inherited": False' in text


def test_lightweight_contracts_are_published_to_tracked_contract_directory():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "publish_names" in text
    assert "v3_al64_geometry_manifest_v1.csv" in text
    assert "v3_test40_manifest_lock_v1.json" in text
