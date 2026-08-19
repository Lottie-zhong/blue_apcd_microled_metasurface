from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(r"D:\\project\\worktrees\\blue_apcd_np_k6_mdc_v1")
SCRIPT = ROOT / "scripts" / "validate_np_k6_m10b_rayleigh_cutoff_forensic_v1.py"


def _validator():
    spec = importlib.util.spec_from_file_location("np_m10b_rayleigh_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_np_k6_m10b_rayleigh_cutoff_forensic_zero_solver():
    report = _validator().validate()
    assert report["passed"], report
    assert report["new_solver_calls"] == 0
    assert report["S_entered"] == 0
