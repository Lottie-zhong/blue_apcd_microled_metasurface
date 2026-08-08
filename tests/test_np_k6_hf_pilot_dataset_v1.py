from pathlib import Path
import importlib.util


def _validator():
    p = Path(r"D:\project\worktrees\blue_apcd_np_k6_mdc_v1\scripts\validate_np_k6_hf_pilot_dataset_v1.py")
    spec = importlib.util.spec_from_file_location("np_k6_hf_pilot_dataset_validator_v1", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_np_k6_hf_pilot_dataset_transaction():
    result = _validator().validate()
    assert result["pass"] is True
    assert result["formal_observation_count"] == 66
    assert result["case_count"] == 6
