from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "scripts"))
from np_k6_m8a_durable_monitor_v2 import CASES, DuplicateMonitor, DurableMonitor, monitor_query


def fake_sample(*, entered=False, lineage=True, engine_completed=False, post_saved=False, controller_returned=False, accepted=False):
    cases = []
    for index, case_id in enumerate(CASES):
        active = entered and index == 0
        cases.append({
            "case_id": case_id,
            "attempt_id": "attempt_001",
            "entered": active,
            "run_invocation_count": 1 if active else 0,
            "engine_completed": engine_completed if active else False,
            "engine_physical_complete": engine_completed if active else False,
            "post_saved": post_saved if active else False,
            "controller_returned": controller_returned if active else False,
            "formal_accepted": accepted if active else True,
        })
    return {
        "timestamp_utc": "2026-08-17T00:00:00+00:00",
        "task_id": "NP_K6_M8A_PRIMARY2",
        "cases": cases,
        "process_lineage": {
            "process_snapshot_ok": True,
            "matched_processes": [{"ProcessId": 1234}] if lineage else [],
            "pid": [1234] if lineage else [],
            "ppid": [1] if lineage else [],
        },
        "global_slot_state": {"active_slots": [], "global_capacity": 3},
        "entered_unresolved": [],
        "solver_calls": 0,
        "read_only": True,
    }


def read_lines(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_a_initial_snapshot():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        monitor.process_sample(fake_sample())
        assert monitor.state_path.exists()
        assert len(read_lines(monitor.progress_path)) == 1
        assert monitor.state["read_only"] is True


def test_b_same_pid_multiple_records_reduced_interval():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, interval_seconds=1, visible_output=False)
        for _ in range(3):
            monitor.process_sample(fake_sample())
        rows = read_lines(monitor.progress_path)
        assert len(rows) == 3
        assert len({row.get("process_lineage", {}).get("pid") and tuple(row["process_lineage"]["pid"]) for row in rows}) == 1


def test_c_duplicate_launch_rejected():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        first = DurableMonitor(root, visible_output=False)
        first.acquire_lock()
        try:
            second = DurableMonitor(root, visible_output=False)
            try:
                second.acquire_lock()
            except DuplicateMonitor:
                pass
            else:
                raise AssertionError("duplicate monitor launch was accepted")
        finally:
            first.release_lock()


def test_d_normal_no_alert():
    with tempfile.TemporaryDirectory() as raw:
        monitor = DurableMonitor(Path(raw), visible_output=False)
        monitor.process_sample(fake_sample())
        assert not monitor.failure_path.exists()


def test_e_lineage_loss_alert_once():
    with tempfile.TemporaryDirectory() as raw:
        monitor = DurableMonitor(Path(raw), visible_output=False)
        monitor.process_sample(fake_sample(entered=True, lineage=True))
        monitor.process_sample(fake_sample(entered=True, lineage=False))
        first = monitor.failure_path.read_text(encoding="utf-8")
        monitor.process_sample(fake_sample(entered=True, lineage=False))
        second = monitor.failure_path.read_text(encoding="utf-8")
        assert first == second
        assert json.loads(second)["reported"] is True


def test_f_engine_complete_post_missing_anomaly():
    with tempfile.TemporaryDirectory() as raw:
        monitor = DurableMonitor(Path(raw), visible_output=False)
        monitor.process_sample(fake_sample(entered=True, engine_completed=True))
        report = json.loads(monitor.failure_path.read_text(encoding="utf-8"))
        assert report["alerts"][0]["alert_code"] == "POST_ENGINE_CLOSURE_ANOMALY"


def test_g_terminal_success_once():
    with tempfile.TemporaryDirectory() as raw:
        monitor = DurableMonitor(Path(raw), visible_output=False)
        sample = fake_sample()
        sample["cases"] = [dict(case, formal_accepted=True) for case in sample["cases"]]
        monitor.process_sample(sample)
        # all four cases are accepted in this terminal sample
        monitor.process_sample(sample)
        terminal = json.loads(monitor.success_path.read_text(encoding="utf-8"))
        assert terminal["terminal"] == "success"
        assert len(read_lines(monitor.progress_path)) == 2


def test_h_crash_restart_resume_without_worker_mutation():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        first = DurableMonitor(root, visible_output=False)
        first.process_sample(fake_sample())
        before = first.state["sample_count"]
        second = DurableMonitor(root, visible_output=False)
        second.process_sample(fake_sample())
        assert second.state["sample_count"] == before + 1
        assert second.state.get("solver_calls", 0) == 0


def test_i_query_fast_path():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        monitor.process_sample(fake_sample())
        result = monitor_query(root)
        assert result["fast_path"] is True
        assert result["repository_scan"] is False
        assert result["last_progress"]["task_id"] == "NP_K6_M8A_PRIMARY2"


def test_zero_solver_and_registry_immutability():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        registry = {"active_slots": [{"case_uid": CASES[0]}], "global_capacity": 3}
        sample = fake_sample()
        sample["global_slot_state"] = registry
        monitor = DurableMonitor(root, visible_output=False)
        monitor.process_sample(sample)
        assert sample["solver_calls"] == 0
        assert sample["global_slot_state"] == registry


def main() -> int:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(json.dumps({"status": "PASS", "test_count": len(tests), "solver_calls": 0, "registry_mutations": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
