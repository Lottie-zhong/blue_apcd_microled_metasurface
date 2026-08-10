from __future__ import annotations

import importlib.util
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "np_k6_m2_g04p_controlled_recompute_validator_v1.py"


def _validator():
    spec = importlib.util.spec_from_file_location("g04p_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_controlled_recompute_standalone_validator():
    assert _validator().validate()["status"] == "PASS"


def test_gate_has_exact_11_points_and_readonly_extraction():
    evidence = ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1"
    gate = json.loads((evidence / "replacement_v2_gate.json").read_text(encoding="utf-8-sig"))
    assert gate["wavelengths_nm"] == list(range(445, 456))
    assert gate["readonly_reload"] is True
    assert gate["run_called"] is False and gate["save_called"] is False


def test_no_second_replacement_or_training():
    evidence = ROOT / "outputs" / "np_k6_m2_g04p_controlled_recompute_v1"
    audit = json.loads((evidence / "solver_invocation_audit.json").read_text(encoding="utf-8-sig"))
    assert audit["replacement_run_invocations"] == 1
    assert audit["second_replacement"] == 0 and audit["attempt_002"] == 0
    assert audit["training_started"] == 0
