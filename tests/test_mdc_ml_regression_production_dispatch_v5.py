import json
from pathlib import Path

import pytest

from mdc_ml.merge_retrain_v1.contracts import load_frozen_contract
from mdc_ml.merge_retrain_v1.formal_authorization_v2 import Authorization
from mdc_ml.merge_retrain_v1.formal_execution_v2 import dispatch


def _dispatch(root: Path, **kwargs):
    return dispatch(load_frozen_contract(),
                    Authorization("REGRESSION_PRODUCTION_DISPATCH_ATTESTATION_ONLY"),
                    "regression_dispatch_attestation", synthetic=False,
                    output_root=root, attestation=True, **kwargs)


def test_attestation_scope_is_disjoint_from_official_oof(tmp_path: Path):
    with pytest.raises(RuntimeError, match="AUTHORIZATION_SCOPE_NOT_GRANTED"):
        dispatch(load_frozen_contract(), Authorization("FORMAL_REGRESSION_OOF_ONLY"),
                 "regression_dispatch_attestation", synthetic=False, output_root=tmp_path,
                 attestation=True)
    assert not list(tmp_path.iterdir())


def test_dispatch_failure_resume_drift_and_completed_noop(tmp_path: Path):
    with pytest.raises(RuntimeError, match="FIXTURE_FAILURE_INJECTION"):
        _dispatch(tmp_path, failure_injection=(1, 20260721))
    run_root = next(tmp_path.iterdir())
    completed = sorted((run_root / "folds" / "fold_1").glob("seed_*.joblib"))
    assert len(completed) == 1
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in completed}
    result = _dispatch(tmp_path, run_root=run_root, resume=True)
    assert result["summary"]["seed_fit_calls"] == 12
    assert result["summary"]["sample_rows"] == 100
    assert result["summary"]["target_rows"] == 400
    assert result["summary"]["seed_target_rows"] == 1200
    assert result["summary"]["ineligible_rows"] == 28
    assert all((p.read_bytes(), p.stat().st_mtime_ns) == value for p, value in before.items())
    state_before = (run_root / "execution_state.json").read_bytes()
    no_op = _dispatch(tmp_path, run_root=run_root, resume=True)
    assert no_op["no_op"] is True
    assert (run_root / "execution_state.json").read_bytes() == state_before
    snapshot = run_root / "input_snapshot.json"
    original = snapshot.read_bytes(); snapshot.write_bytes(b"{}")
    with pytest.raises(RuntimeError, match="INPUT_DRIFT_GUARD"):
        _dispatch(tmp_path, run_root=run_root, resume=True)
    snapshot.write_bytes(original)
    assert json.loads((run_root / "execution_state.json").read_text())["formal_regression_oof_calls"] == 0
