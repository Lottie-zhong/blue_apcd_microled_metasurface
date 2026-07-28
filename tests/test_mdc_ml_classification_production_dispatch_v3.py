from pathlib import Path

from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_authorization_v2 import Authorization
from mdc_ml.merge_retrain_v1.formal_execution_v2 import dispatch


def test_full_shape_dispatch_runs_frozen_components(tmp_path: Path):
    got = dispatch(load_frozen_contract(), Authorization("FORMAL_CLASSIFICATION_OOF_ONLY"), "classification_oof", synthetic=True, output_root=tmp_path)
    assert got["status"] == "COMPLETE"
    assert got["synthetic"]
