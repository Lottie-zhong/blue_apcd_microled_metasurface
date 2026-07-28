from pathlib import Path
import pytest
from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_authorization_v2 import Authorization
from mdc_ml.merge_retrain_v1.formal_execution_v2 import dispatch, readiness

def test_readiness_loads_canonical_inputs():
    value=readiness(load_frozen_contract(),"FORMAL_CLASSIFICATION_OOF_ONLY")
    assert value["inputs"]["round1_classification"]==128
    assert value["inputs"]["classification_fold_sizes"]==[31,34,39,24]

def test_scope_rejects_before_writes(tmp_path: Path):
    with pytest.raises(RuntimeError,match="AUTHORIZATION_SCOPE_NOT_GRANTED"):
        dispatch(load_frozen_contract(),Authorization("FORMAL_CLASSIFICATION_OOF_ONLY"),"regression_oof",synthetic=True,output_root=tmp_path)
