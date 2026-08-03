import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_np_k6_p0_failure_v1.py"
spec = importlib.util.spec_from_file_location("validate_np_k6_p0_failure_v1", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
validate = module.validate


def test_p0_failure_evidence_is_strict_early_stop():
    stage = Path(r"D:/project/worktrees/blue_apcd_np_k6_mdc_v1/outputs/np_k6_hf_p0_label_generator_recovery_v1")
    errors = validate(stage)
    assert errors == [], errors
    failure = json.loads((stage / "pilot_numerical_gate_failure.json").read_text(encoding="utf-8"))
    assert failure["gates"]["max_abs_closure_residual"] > 0.02
    assert failure["solver_entered_total"] == 1
