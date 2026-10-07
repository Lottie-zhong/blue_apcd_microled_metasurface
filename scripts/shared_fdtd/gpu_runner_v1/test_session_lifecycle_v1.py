import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adapter
import runner


def _manifest(tmp_path, run_id, case_id="TEST_CASE"):
    pre = tmp_path / (run_id + ".fsp")
    pre.write_bytes(b"unsolved setup")
    return {
        "case_id": case_id,
        "attempt_id": "attempt_001",
        "run_id": run_id,
        "geometry": [120, 115, 230, 140, 110, 115],
        "physical_contract_sha256": runner.CONTRACT_SHA256,
        "expansion_manifest_sha256": runner.EXPANSION_SHA256,
        "pre_fsp_path": str(pre),
        "pre_fsp_sha256": runner.sha256_file(pre),
    }


def _no_owner(_root):
    return False


def _gpu_snapshot():
    return {"free_mib": 9000}


def test_keyboard_interrupt_after_entry_is_terminal_and_never_replayable(tmp_path):
    root = tmp_path / "runner"
    manifest = _manifest(tmp_path, "interrupt-after-entry")

    def interrupt_solver(_manifest, _run_dir):
        raise KeyboardInterrupt()

    with pytest.raises(runner.RunnerError):
        runner.run_one(manifest, root, interrupt_solver, lambda *_: {}, _gpu_snapshot, _no_owner)

    run_dir = root / "runs" / manifest["case_id"] / manifest["attempt_id"] / manifest["run_id"]
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "registry.json").read_text(encoding="utf-8"))
    assert status["state"] == "FAILED_POSTENTRY"
    assert status["solver_entered"] is True
    assert status["solver_invocations"] == 1
    assert status["failure"].startswith("KeyboardInterrupt")
    assert registry["runs"][0]["state"] == "FAILED_POSTENTRY"
    assert not (root / ".runner.lock").exists()
    assert not (root / "active_run.json").exists()

    retry = dict(manifest, run_id="interrupt-after-entry-new-run-id")
    with pytest.raises(runner.RunnerError, match="POST_ENTRY_REPLAY_FORBIDDEN"):
        runner.run_one(retry, root, lambda *_: {}, lambda *_: {}, _gpu_snapshot, _no_owner)


def test_keyboard_interrupt_before_entry_is_terminal_preentry(tmp_path):
    root = tmp_path / "runner"
    manifest = _manifest(tmp_path, "interrupt-before-entry")

    def interrupt_snapshot():
        raise KeyboardInterrupt()

    with pytest.raises(runner.RunnerError):
        runner.run_one(manifest, root, lambda *_: {}, lambda *_: {}, interrupt_snapshot, _no_owner)

    run_dir = root / "runs" / manifest["case_id"] / manifest["attempt_id"] / manifest["run_id"]
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "registry.json").read_text(encoding="utf-8"))
    assert status["state"] == "FAILED_PREENTRY"
    assert status["solver_entered"] is False
    assert status["solver_invocations"] == 0
    assert registry["runs"][0]["state"] == "FAILED_PREENTRY"
    assert not (root / ".runner.lock").exists()
    assert not (root / "active_run.json").exists()


def test_run_one_cli_routes_through_scheduler_api_and_never_runs_parent(monkeypatch, tmp_path, capsys):
    manifest = tmp_path / "request.json"
    manifest.write_text("{}", encoding="utf-8")
    expected = {"run_dir": "durable", "state": "DONE", "solver_invocations": 1}
    calls = []
    monkeypatch.setattr(adapter, "run_one_scheduled", lambda path: calls.append(path) or expected)
    monkeypatch.setattr(adapter, "run_cli", lambda *_: (_ for _ in ()).throw(AssertionError("parent ran solver")))
    assert adapter.main(["run-one", str(manifest)]) == 0
    assert calls == [str(manifest)]
    assert json.loads(capsys.readouterr().out) == expected


def test_detached_breakaway_path_is_removed():
    assert not hasattr(adapter, "run_one_detached")
    assert not hasattr(adapter, "_run_one_detached_worker")
