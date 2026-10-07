import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import task_scheduler_v1 as scheduler


def fake_adapter(tmp_path):
    adapter_path = tmp_path / "adapter.py"
    adapter_path.write_text("# fake no-solver adapter\n", encoding="utf-8")

    def read_manifest(path):
        return json.loads(Path(path).read_text(encoding="utf-8")), None

    return SimpleNamespace(__file__=str(adapter_path), read_cli_manifest=read_manifest, run_cli=Mock())


def manifest(tmp_path, run_id="QUEUE_SYNTHETIC_RUN"):
    path = tmp_path / (run_id + ".json")
    path.write_text(json.dumps({"case_id": "QUEUE_SYNTHETIC_CASE",
                                "attempt_id": "attempt_001", "run_id": run_id}),
                    encoding="utf-8")
    return path


def synthetic_result():
    return {"status": {"state": "SYNTHETIC_WORKER_RESULT", "solver_entered": False,
                       "solver_invocations": 0, "replay_count": 0},
            "solver_entries_this_call": 0, "automatic_replay_count": 0}


def test_detached_submit_returns_before_scheduled_worker_finishes(monkeypatch, tmp_path):
    adapter = fake_adapter(tmp_path)
    root = tmp_path / "runner"
    case_manifest = manifest(tmp_path)
    worker_started = threading.Event()
    allow_worker_to_finish = threading.Event()
    worker_threads = []
    worker_results = []

    def fake_start_task():
        def run_worker():
            worker_results.append(scheduler.task_worker_once(
                root=root, adapter_module=adapter,
                run_cli=lambda _path: (worker_started.set(),
                                       allow_worker_to_finish.wait(5),
                                       synthetic_result())[-1]))
        thread = threading.Thread(target=run_worker, daemon=True)
        worker_threads.append(thread)
        thread.start()

    monkeypatch.setattr(scheduler, "_start_worker_task", fake_start_task)
    started = time.monotonic()
    submitted = scheduler.submit_one(case_manifest, root=root, adapter_module=adapter, start_task=True)
    submit_elapsed = time.monotonic() - started
    assert worker_started.wait(2)
    assert submit_elapsed < 2
    assert submitted["state"] == "PENDING"
    allow_worker_to_finish.set()
    for thread in worker_threads:
        thread.join(5)
    assert len(worker_results) == 1
    terminal = scheduler.query_one(submitted["request_id"], root=root,
                                   task_info_fn=lambda: {"state": "Ready"})
    assert terminal["state"] == "TERMINAL"
    assert terminal["result"]["result"]["solver_entries_this_call"] == 0


def test_controller_exit_leaves_worker_and_restart_reconciles_stale_queue_state(monkeypatch, tmp_path):
    adapter = fake_adapter(tmp_path)
    root = tmp_path / "runner"
    case_manifest = manifest(tmp_path, "QUEUE_EXIT_RUN")
    state_path = tmp_path / "queue-state.json"
    worker_started = threading.Event()
    release_worker = threading.Event()
    worker_threads = []
    worker_calls = []

    def fake_start_task():
        def run_worker():
            worker_calls.append(scheduler.task_worker_once(
                root=root, adapter_module=adapter,
                run_cli=lambda _path: (worker_started.set(), release_worker.wait(5),
                                       synthetic_result())[-1]))
        thread = threading.Thread(target=run_worker, daemon=True)
        worker_threads.append(thread)
        thread.start()

    monkeypatch.setattr(scheduler, "_start_worker_task", fake_start_task)
    with pytest.raises(RuntimeError, match="SIMULATED_CONTROLLER_EXIT"):
        request = scheduler.submit_one(case_manifest, root=root, adapter_module=adapter, start_task=True)
        assert worker_started.wait(2)
        state_path.write_text(json.dumps({"phase": "RUN_ONE_IN_PROGRESS",
            "request_id": request["request_id"], "solver_entries": 0}), encoding="utf-8")
        raise RuntimeError("SIMULATED_CONTROLLER_EXIT")

    # The caller/controller is gone; the independently scheduled worker continues.
    release_worker.set()
    for thread in worker_threads:
        thread.join(5)
    stale = json.loads(state_path.read_text(encoding="utf-8"))
    resumed = scheduler.query_one(stale["request_id"], root=root,
                                  task_info_fn=lambda: {"state": "Ready"})
    assert resumed["state"] == "TERMINAL"
    # Synthetic restart reconciles the exact immutable request before advancing.
    assert resumed["request"]["identity"]["run_id"] == "QUEUE_EXIT_RUN"
    stale.update({"phase": "RECONCILED", "solver_entries": 0,
                  "replay_count": 0, "result_sha256": resumed["result"]["result_sha256"]})
    state_path.write_text(json.dumps(stale), encoding="utf-8")
    assert json.loads(state_path.read_text(encoding="utf-8"))["phase"] == "RECONCILED"
    assert len(worker_calls) == 1
    assert worker_calls[0]["exit_code"] == 0
    assert worker_calls[0]["solver_entered"] is None
    assert resumed["result"]["result"]["automatic_replay_count"] == 0


def test_stale_claim_is_reconciled_not_redispatched(monkeypatch, tmp_path):
    adapter = fake_adapter(tmp_path)
    root = tmp_path / "runner"
    case_manifest = manifest(tmp_path, "QUEUE_STALE_PREENTRY")
    request = scheduler.submit_one(case_manifest, root=root, adapter_module=adapter, start_task=False)
    request_dir = Path(request["request_path"]).parent
    (request_dir / "worker_claim.json").write_text("{}", encoding="utf-8")
    status_path = root / "runs" / "QUEUE_SYNTHETIC_CASE" / "attempt_001" / "QUEUE_STALE_PREENTRY" / "status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(json.dumps({"case_id": "QUEUE_SYNTHETIC_CASE",
        "attempt_id": "attempt_001", "run_id": "QUEUE_STALE_PREENTRY",
        "state": "FAILED_PREENTRY", "solver_entered": False,
        "solver_invocations": 0, "replay_count": 0}), encoding="utf-8")
    stale = scheduler.query_one(request["request_id"], root=root,
                                task_info_fn=lambda: {"state": "Ready"})
    assert stale["state"] == "NEEDS_RECONCILIATION"
    adapter.run_cli.assert_not_called()
    # A controller must stop at this state; query does not create a replacement request.
    assert len(list((root / "requests" / "scheduled_run_one_v1").iterdir())) == 1


def test_duplicate_submission_maps_to_one_request_and_one_worker_claim(monkeypatch, tmp_path):
    adapter = fake_adapter(tmp_path)
    root = tmp_path / "runner"
    case_manifest = manifest(tmp_path, "QUEUE_DUPLICATE_RUN")
    started = threading.Event()
    release = threading.Event()
    start_calls = []
    worker_threads = []
    worker_claim_count = []
    start_guard = threading.Lock()

    def fake_start_task():
        with start_guard:
            start_calls.append(True)
            if started.is_set():
                return  # Synthetic Scheduler IgnoreNew behavior.
            started.set()
        def run_worker():
            worker_claim_count.append(scheduler.task_worker_once(
                root=root, adapter_module=adapter,
                run_cli=lambda _path: (release.wait(5), synthetic_result())[-1]))
        thread = threading.Thread(target=run_worker, daemon=True)
        worker_threads.append(thread)
        thread.start()

    monkeypatch.setattr(scheduler, "_start_worker_task", fake_start_task)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(scheduler.submit_one, case_manifest, root=root,
                            adapter_module=adapter, start_task=True)
        second = pool.submit(scheduler.submit_one, case_manifest, root=root,
                             adapter_module=adapter, start_task=True)
        one, two = first.result(timeout=5), second.result(timeout=5)
    assert one["request_id"] == two["request_id"]
    assert len(list((root / "requests" / "scheduled_run_one_v1").iterdir())) == 1
    assert len(start_calls) == 2  # Both callers requested start; Scheduler IgnoreNew admits one instance.
    release.set()
    for thread in worker_threads:
        thread.join(5)
    assert len(worker_claim_count) == 1
    assert worker_claim_count[0]["result"] == "RECORDED"
    assert scheduler.query_one(one["request_id"], root=root,
        task_info_fn=lambda: {"state": "Ready"})["state"] == "TERMINAL"
    assert len(list((root / "requests" / "scheduled_run_one_v1").iterdir())) == 1
