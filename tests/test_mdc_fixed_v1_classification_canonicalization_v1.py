from pathlib import Path
import json

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1")
OUT = ROOT / "outputs/mdc_fixed_v1_classification_canonicalization_v1/20260802T101700Z_90abc54ff31f"


def load(rel):
    return json.loads((OUT / rel).read_text())


def test_roles_and_fit_counts():
    role = load("audits/classification_estimator_role_audit.json")
    done = load("manifests/completion_manifest.json")
    assert role["canonical_final_fit_api_calls"] == 1
    assert role["canonical_final_seed"] == 20260720
    assert role["no_fold_selection"] is True
    assert done["new_classification_oof_fits"] == 0
    assert done["new_classification_final_fit_api_calls"] == 1
    assert done["new_regression_fits"] == 0


def test_loader_and_replay():
    loader = load("manifests/canonical_classifier_loader_contract.json")
    replay = load("predictions/fresh_load_prediction_sha.json")
    assert loader["loads_final_classifiers"] == 1
    assert loader["loads_oof_estimators"] is False
    assert loader["fit_calls_during_inference"] == 0
    assert loader["threshold_refit"] == 0
    assert replay["identical"] is True


def test_applicability_and_regression_guard():
    app = load("manifests/hf15_classification_applicability_contract.json")
    reg = load("audits/regression_artifact_immutability_audit.json")
    assert app["status"] == "NOT_APPLICABLE_TO_HF15_PHYSICAL_TRUTH"
    assert app["hf15_formal_label_reads"] == 0
    assert reg["status"] == "PASS"
    assert reg["drift"] == []
