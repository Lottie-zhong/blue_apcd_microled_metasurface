import importlib.util
import json
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
RUNNER = ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("d6_runner_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_attestation_and_legacy_tripwire():
    runner = load_runner()
    att = runner.runtime_attestation()
    assert att["status"] == "PASS"
    runtime = runner.load_runtime()
    try:
        runtime.legacy_forbidden()
    except RuntimeError as exc:
        assert str(exc) == runtime.FORBIDDEN
    else:
        raise AssertionError("tripwire did not fire")


def test_fake_backend_entrypoint_and_atomicity():
    runner = load_runner()
    assert runner.actual_entrypoint_replay()["status"] == "PASS"
    assert runner.atomic_and_tamper_tests()["status"] == "PASS"


def test_locking_tamper_import_and_hard_stop():
    runner = load_runner()
    assert runner.locking_tests()["status"] == "PASS"
    assert runner.tamper_tests()["status"] == "PASS"
    assert runner.import_tests()["status"] == "PASS"
    assert runner.hard_stop_tests()["status"] == "PASS"


def test_complete_suite_and_package():
    runner = load_runner()
    result = runner.complete_suite()
    assert result["status"] == "PASS"
    assert result["formal_d6_staging_created"] is False
    manifest = json.loads((runner.PACKAGE / "package_manifest.json").read_text())
    assert manifest["status"] == "READY_FOR_EXPLICIT_D6_EXECUTION"
