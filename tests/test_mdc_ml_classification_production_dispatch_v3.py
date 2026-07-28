from pathlib import Path

from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_authorization_v2 import Authorization
from mdc_ml.merge_retrain_v1.formal_execution_v2 import dispatch


def test_full_shape_dispatch_runs_frozen_components(tmp_path: Path):
    got = dispatch(load_frozen_contract(), Authorization("FORMAL_CLASSIFICATION_OOF_ONLY"), "classification_oof", synthetic=True, output_root=tmp_path)
    assert got["status"] == "COMPLETE"
    assert got["synthetic"]
    summary = got["summary"]
    assert summary["prediction_count"] == 128
    assert summary["fold_prediction_counts"] == [31, 34, 39, 24]
    assert summary["exact_once"]
    root = Path(got["run_root"])
    for name in (
        "classification_oof_predictions.csv",
        "classification_oof_predictions.jsonl",
        "classification_fold_plan.json",
        "classification_fit_registry.json",
        "classification_validation_registry.json",
        "classification_calibration_registry.json",
        "classification_threshold_registry.json",
        "classification_oof_reconciliation.json",
        "classification_leakage_audit.json",
        "classification_provenance.json",
        "formal_classification_state.json",
        "formal_classification_summary.json",
        "formal_classification_output_manifest.json",
    ):
        assert (root / name).stat().st_size > 0
