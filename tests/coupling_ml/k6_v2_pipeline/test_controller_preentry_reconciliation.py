from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "coupling_ml"
    / "k6_v2_pipeline"
    / "serial_queue.py"
)
_SPEC = importlib.util.spec_from_file_location("k6_preentry_reconciliation_test_module", _SCRIPT)
sq = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sq)


def _bundle():
    identity = {
        "case_id": "K6GDP2_DEV_G027",
        "attempt_id": "attempt_001",
        "run_id": "K6V2_G027_20261009T092453Z_5bd7193e",
    }
    failure = "RunnerError:RUNNER_OWNED_ACTIVITY_PRESENT"
    status = {
        "schema": "APCD_GPU_RUN_STATUS_V1",
        **identity,
        "state": "FAILED_PREENTRY",
        "solver_entered": False,
        "solver_invocations": 0,
        "failure": failure,
    }
    exception = {
        "schema": "APCD_GPU_RUNNER_V1_FAILURE_EXCEPTION_V1",
        **identity,
        "state_at_failure": "PENDING",
        "phase": "PRE_ENTRY_CHECKS",
        "solver_entered": False,
        "solver_invocations": 0,
        "exception_type": "RunnerError",
        "exception": "RUNNER_OWNED_ACTIVITY_PRESENT",
    }
    request = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_REQUEST_V1",
        "request_id": "c8616f548daff61ce04bbca6c4f3cac5",
        "request_sha256": "a" * 64,
        "identity": identity,
        "manifest_path": "D:/queue/RUN_ENVELOPE.json",
        "manifest_sha256": "b" * 64,
    }
    claim = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_WORKER_CLAIM_V1",
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "task_name": r"\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER",
    }
    result = {
        "schema": "APCD_GPU_RUNNER_V1_SCHEDULED_RESULT_V1",
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "exit_code": 2,
        "error_type": "RunnerError",
        "error": "RUNNER_OWNED_ACTIVITY_PRESENT",
        "solver_entered": False,
        "run_status": {
            "failure": failure,
            "solver_entered": False,
            "solver_invocations": 0,
            "state": "FAILED_PREENTRY",
        },
        "claim_sha256": "c" * 64,
    }
    query = {"state": "TERMINAL", "task": None, "request": request, "result": result}
    return identity, status, exception, request, claim, query


def test_preentry_bundle_accepts_terminal_zero_entry_failure():
    identity, status, exception, request, claim, query = _bundle()

    assert sq._validate_preentry_query_bundle(
        identity, status, exception, {"state": "PENDING"}, {"state": "PENDING"},
        request, claim, query
    ) == query["result"]


@pytest.mark.parametrize("mutation", ["status", "result", "exception", "query"])
def test_preentry_bundle_rejects_entry_or_identity_ambiguity(mutation):
    identity, status, exception, request, claim, query = _bundle()
    if mutation == "status":
        status["solver_entered"] = True
    elif mutation == "result":
        query["result"]["solver_entered"] = True
    elif mutation == "exception":
        exception["run_id"] = "other-run"
    else:
        query["state"] = "NEEDS_RECONCILIATION"

    with pytest.raises(sq.StopQueue):
        sq._validate_preentry_query_bundle(
            identity, status, exception, {"state": "PENDING"}, {"state": "PENDING"},
            request, claim, query
        )


def test_legacy_source_hash_uses_runner_bound_manifest_and_start_claim():
    manifest_sha = "a" * 64
    request_id = "765457a089c44d50f24aa7ca821e9fce"
    manifest = {
        "controller_run_id": "controller-1",
        "controller_script_path": "D:/coupling/serial_queue.py",
        "controller_script_sha256": "b" * 64,
        "queue_manifest_sha256": "c" * 64,
        "queue_id": "queue-1",
    }
    binding = {
        "schema": "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_BINDING_V1",
        "request_id": request_id,
        "controller_manifest_sha256": manifest_sha,
        "controller_script_path": manifest["controller_script_path"],
        "controller_script_sha256": manifest["controller_script_sha256"],
        "queue_manifest_sha256": manifest["queue_manifest_sha256"],
        "queue_id": manifest["queue_id"],
        "controller_run_id": manifest["controller_run_id"],
    }
    claim = {
        "schema": "APCD_GPU_RUNNER_V1_CONTROLLER_START_CLAIM_V1",
        "request_id": request_id,
        "controller_manifest_sha256": manifest_sha,
        "queue_id": manifest["queue_id"],
        "task_name": sq.CONTROLLER_TASK_NAME,
    }

    assert sq._runner_attests_controller_source_pin(
        manifest, binding, claim, request_id, manifest_sha)
    binding["controller_script_sha256"] = "0" * 64
    assert not sq._runner_attests_controller_source_pin(
        manifest, binding, claim, request_id, manifest_sha)


def test_controller_stop_reconciler_excludes_only_its_exact_process(monkeypatch):
    request_id = "765457a089c44d50f24aa7ca821e9fce"
    script = str(_SCRIPT.resolve())
    monkeypatch.setattr(sq.os, "getpid", lambda: 4242)
    monkeypatch.setattr(sq.sys, "argv", [
        script, "--reconcile-controller-stop-only",
        "--runner-controller-request-id", request_id,
    ])
    processes = [{
        "ProcessId": 4242,
        "ParentProcessId": 4000,
        "CommandLine": f'"{script}" --reconcile-controller-stop-only '
            f"--runner-controller-request-id {request_id}",
        "Name": "python.exe",
    }, {
        "ProcessId": 4000,
        "ParentProcessId": 3000,
        "Name": "cmd.exe",
        "CommandLine": f'cmd /c "{script} --reconcile-controller-stop-only '
            f'--runner-controller-request-id {request_id}"',
    }, {
        "ProcessId": 8888,
        "ParentProcessId": 1,
        "Name": "python.exe",
        "CommandLine": 'python.exe D:/other/serial_queue.py --execute',
    }]
    assert sq._exclude_verified_current_reconciler_process(
        processes, request_id, required_mode="--reconcile-controller-stop-only") == [processes[2]]


def test_preentry_reconciliation_accepts_only_matching_isolated_pointers():
    case_id = "K6GDP2_DEV_G027"
    run_id = "K6V2_G027_20261009T092453Z_5bd7193e"
    envelope = "D:/queue/RUN_ENVELOPE.json"
    current = {
        "case_id": case_id,
        "phase": "FAILED_OR_ISOLATED",
        "run_id": run_id,
        "run_envelope_path": envelope,
        "run_envelope_sha256": "a" * 64,
    }
    record = {
        "phase": "RUN_ONE_IN_PROGRESS",
        "run_id": run_id,
        "run_envelope_path": envelope,
        "run_envelope_sha256": "a" * 64,
    }
    batch = {"current_case": {"case_id": case_id, "phase": "FAILED_OR_ISOLATED", "run_id": run_id}}

    assert sq._preentry_current_pointers_match(current, batch, record, case_id)
    batch["current_case"]["run_id"] = "different-run"
    assert not sq._preentry_current_pointers_match(current, batch, record, case_id)


def test_dry_run_sequence_uses_frozen_global_case_order():
    ordered = [
        f"K6LDA1_DEV_D{i}_{pol}05"
        for i in range(1, 7)
        for pol in ("M", "P")
    ]
    ordered.extend(f"K6GDP2_DEV_G{i:03d}" for i in range(1, 129))
    assert sq.case_sequence_index(ordered, "K6GDP2_DEV_G027") == 39
