import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.mdc_ml.hf_formal_read_guard import FormalReadGuardError, guarded_read_formal_labels, validate_prelabel_contract, validate_evaluation_source_static


def _ready(tmp_path):
    pre = tmp_path / "pre"
    for n in ["prelabel_model_lock.json", "prelabel_target_comparability_contract.json", "prelabel_evaluation_plan.json", "hf15_prelabel_feature_matrix.parquet", "hf15_prelabel_regression_predictions.parquet", "hf15_prelabel_eligibility_routing.parquet", "prelabel_fresh_replay_1.json", "prelabel_fresh_replay_2.json", "prelabel_prediction_sha.json", "prelabel_routing_sha.json"]:
        (pre / n).parent.mkdir(parents=True, exist_ok=True); (pre / n).write_text("{}")
    root = tmp_path / "formal"; root.mkdir(); pq.write_table(pa.table({"geometry_hash": ["g"], "target": [1.0]}), root / "labels.parquet")
    return pre, root, {"blind_status": "BLIND_ACTIVE", "formal_value_read_count": 0}


def test_missing_lock_fails_before_open(tmp_path):
    pre, root, reg = _ready(tmp_path); (pre / "prelabel_model_lock.json").unlink()
    with pytest.raises(FormalReadGuardError): validate_prelabel_contract(pre, reg, ["geometry_hash"], {"geometry_hash"})


def test_columns_none_and_extra_fail(tmp_path):
    pre, root, reg = _ready(tmp_path)
    with pytest.raises(FormalReadGuardError): validate_prelabel_contract(pre, reg, None, {"geometry_hash"})
    with pytest.raises(FormalReadGuardError): validate_prelabel_contract(pre, reg, ["target"], {"geometry_hash"})


def test_retired_rejects_entrypoint_before_open(tmp_path):
    pre, root, reg = _ready(tmp_path); reg["blind_status"] = "RETIRED_DUE_TO_PRELABEL_FORMAL_VALUE_EXPOSURE"
    with pytest.raises(FormalReadGuardError): guarded_read_formal_labels(root / "labels.parquet", dataset_root=root, registry=reg, prelabel_dir=pre, requested_columns=["geometry_hash"], allowed_columns={"geometry_hash"}, access_log=tmp_path / "access.log")


def test_diagnostics_and_nonzero_counter_fail(tmp_path):
    pre, root, reg = _ready(tmp_path); reg["formal_value_read_count"] = 1
    with pytest.raises(FormalReadGuardError): validate_prelabel_contract(pre, reg, ["geometry_hash"], {"geometry_hash"})
    reg["formal_value_read_count"] = 0
    with pytest.raises(FormalReadGuardError): guarded_read_formal_labels(root / "case_diagnostics_v1.parquet", dataset_root=root, registry=reg, prelabel_dir=pre, requested_columns=["geometry_hash"], allowed_columns={"geometry_hash"}, access_log=tmp_path / "access.log")


def test_valid_mock_reads_allowlist_once(tmp_path):
    pre, root, reg = _ready(tmp_path); log=tmp_path / "access.log"
    t=guarded_read_formal_labels(root / "labels.parquet", dataset_root=root, registry=reg, prelabel_dir=pre, requested_columns=["geometry_hash"], allowed_columns={"geometry_hash"}, access_log=log)
    assert t.column_names == ["geometry_hash"] and reg["formal_value_read_count"] == 1 and log.is_file()


def test_legacy_direct_path_is_rejected_before_value_read(tmp_path):
    old = tmp_path / "old_eval.py"
    old.write_text("HF15_ROOT='x'\nimport pandas as pd\npd.read_parquet(HF15_ROOT)\n")
    with pytest.raises(FormalReadGuardError): validate_evaluation_source_static(old)
