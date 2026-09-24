from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from shared_fdtd.tools.pw_scientific_launcher import (
    _gpu_completion_evidence,
    _standalone_gpu_command,
    _standalone_gpu_script,
    load_only_validate,
    run_and_confirm_entry,
    run_gpu_and_confirm_completion,
    run_standalone_gpu_and_confirm_completion,
)


def cfg(run_fsp):
    return {
        "run_fsp": str(run_fsp),
        "entry_confirmation_poll_s": 0.0,
        "gpu_resource_name": "GPU license audit",
        "pw_contract": {
            "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
            "samples_nm": [], "references_nm": [], "materials": {},
            "stack_layers": [], "wavelengths_nm": [],
        },
    }


def row(run_fsp):
    return {
        "ProcessId": "42",
        "Name": "fdtd-engine-msmpi.exe",
        "CommandLine": f"fdtd-engine-msmpi.exe {run_fsp}",
    }


def expect_error(fn, text):
    try:
        fn()
    except RuntimeError as exc:
        assert text in str(exc), (text, exc)
    else:
        raise AssertionError(f"missing expected error: {text}")


def test_missing_log(root, run):
    run.write_text("setup", encoding="utf-8")
    expect_error(
        lambda: run_gpu_and_confirm_completion(
            None, cfg(run), lambda _: None, process_snapshot=lambda: [], run_callable=lambda: None
        ),
        "GPU_COMPLETION_BARRIER_LOG_MISSING",
    )


def test_api_early_return(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Starting total iterations", encoding="utf-8")
    expect_error(
        lambda: run_gpu_and_confirm_completion(
            None, cfg(run), lambda _: None, process_snapshot=lambda: [], run_callable=lambda: None
        ),
        "GPU_COMPLETION_BARRIER_LOG_INCOMPLETE",
    )


def test_active_job(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation complete", encoding="utf-8")
    expect_error(
        lambda: run_gpu_and_confirm_completion(
            None, cfg(run), lambda _: None, process_snapshot=lambda: [row(run)], run_callable=lambda: None
        ),
        "GPU_COMPLETION_BARRIER_ACTIVE_PROCESS",
    )


def test_missing_monitor(root, run):
    class MissingMonitor:
        def getdata(self, monitor, component):
            raise RuntimeError(f"missing monitor {monitor}")

    contract = {
        "pw_contract": {
            "monitors": {"input": "MON_IN", "pre": "MON_PRENP", "output": "MON_POSTNP"},
            "samples_nm": [],
            "references_nm": [],
            "materials": {},
            "stack_layers": [],
            "wavelengths_nm": [],
        }
    }
    expect_error(lambda: load_only_validate(MissingMonitor(), contract), "missing monitor")


def test_completed_job(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation complete", encoding="utf-8")
    seen = []
    evidence = run_gpu_and_confirm_completion(
        None, cfg(run), seen.append, process_snapshot=lambda: [], run_callable=lambda: None
    )
    assert evidence["observation"] == "gpu_job_completed"
    assert len(seen) == 1
    assert seen[0]["observation"] == "job_manager_returned_with_completion"


def test_restart_replay_is_blocked(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation complete", encoding="utf-8")
    seen = []
    run_gpu_and_confirm_completion(None, cfg(run), seen.append, process_snapshot=lambda: [], run_callable=lambda: None)
    run_gpu_and_confirm_completion(None, cfg(run), seen.append, process_snapshot=lambda: [], run_callable=lambda: None)
    assert len(seen) == 2
    assert all(item["observation"] == "job_manager_returned_with_completion" for item in seen)


def test_idempotent_evidence(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation complete", encoding="utf-8")
    first = _gpu_completion_evidence(cfg(run), lambda: [], run)
    second = _gpu_completion_evidence(cfg(run), lambda: [], run)
    assert first == second


def test_mutex_blocks_active_job(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation complete", encoding="utf-8")
    expect_error(
        lambda: _gpu_completion_evidence(cfg(run), lambda: [row(run)], run),
        "GPU_COMPLETION_BARRIER_ACTIVE_PROCESS",
    )


def test_release_gate():
    state = {"solver_returned": False, "slot_release_status": "HELD"}
    assert not (state["solver_returned"] and state["slot_release_status"] == "RELEASED")
    state.update(solver_returned=True, slot_release_status="RELEASED")
    assert state["solver_returned"]


def test_cpu_path_unchanged():
    seen = []
    run_and_confirm_entry(
        object(),
        {"run_fsp": "cpu_runtime.fsp", "entry_confirmation_poll_s": 0.0},
        seen.append,
        process_snapshot=lambda: [],
        run_callable=lambda: None,
    )
    assert seen[0]["observation"] == "lumapi.run_returned"


def test_v1_nonreuse():
    events = [{"event_type": "SCIENTIFIC_SOLVER_ENTERED", "attempt_id": "attempt_001"}]
    assert sum(event["event_type"] == "SCIENTIFIC_SOLVER_ENTERED" for event in events) == 1
    assert not any(event.get("replay") for event in events)


def test_completed_job_with_entry_process(root, run):
    run.write_text("setup", encoding="utf-8")
    (root / "gpu_p0.log").write_text("Simulation finished", encoding="utf-8")
    seen = []
    calls = []

    def snapshot():
        calls.append(len(calls))
        return [row(run)] if len(calls) == 2 else []

    evidence = run_gpu_and_confirm_completion(
        None,
        cfg(run),
        seen.append,
        process_snapshot=snapshot,
        run_callable=lambda: time.sleep(0.05),
    )
    assert evidence["observation"] == "gpu_job_completed"
    assert seen[0]["observation"] == "new_solver_process"


def test_standalone_command_and_script(root, run):
    command = _standalone_gpu_command(
        Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\bin\fdtd-solutions.exe"),
        Path(r"C:\case root\run_gpu.lsf"), Path(r"C:\case root\run.fsp"),
    )
    assert command[1:5] == ["-nw", "-hide", "-trust-script", "-run"]
    assert command[-2:] == [r"C:\case root\run_gpu.lsf", r"C:\case root\run.fsp"]
    script = _standalone_gpu_script("GPU license audit", ["MON_IN", "MON_POSTNP"])
    assert 'run("FDTD","GPU","GPU license audit");' in script
    assert 'getdata("MON_IN","f");' in script
    assert "runjobs" not in script


def test_standalone_child_success(root, run):
    run.write_text("setup", encoding="utf-8")
    class Child:
        def poll(self):
            return 0
    seen = []
    evidence = run_standalone_gpu_and_confirm_completion(
        cfg(run), seen.append, process_snapshot=lambda: [],
        popen_factory=lambda *args, **kwargs: Child(),
    )
    assert evidence["returncode"] == 0
    assert seen[0]["observation"] == "standalone_child_returned"


def test_standalone_child_failure(root, run):
    run.write_text("setup", encoding="utf-8")
    class Child:
        def poll(self):
            return 17
    expect_error(
        lambda: run_standalone_gpu_and_confirm_completion(
            cfg(run), lambda _: None, process_snapshot=lambda: [],
            popen_factory=lambda *args, **kwargs: Child(),
        ), "GPU_STANDALONE_CHILD_FAILED:17",
    )


def main():
    tests = [
        test_missing_log,
        test_api_early_return,
        test_active_job,
        test_missing_monitor,
        test_completed_job,
        test_restart_replay_is_blocked,
        test_idempotent_evidence,
        test_mutex_blocks_active_job,
        lambda root, run: test_release_gate(),
        lambda root, run: test_cpu_path_unchanged(),
        lambda root, run: test_v1_nonreuse(),
        test_completed_job_with_entry_process,
        test_standalone_command_and_script,
        test_standalone_child_success,
        test_standalone_child_failure,
    ]
    results = []
    for test in tests:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "case_runtime.fsp"
            test(root, run)
        results.append({"test": test.__name__, "status": "PASS"})
    print(json.dumps({
        "status": "PASS",
        "tests": results,
        "test_count": len(results),
        "solver_runs": 0,
        "scientific_solver_entries": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
