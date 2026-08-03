import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_np_k6_p0_closure_diagnosis_v1.py"
spec = importlib.util.spec_from_file_location("validate_np_k6_p0_closure_diagnosis_v1", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_closure_diagnosis_is_read_only_and_single_variable():
    stage = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1/outputs/np_k6_hf_p0_label_generator_recovery_v1")
    errors = module.validate(stage)
    assert errors == [], errors
