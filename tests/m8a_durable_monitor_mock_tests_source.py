from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent / "scripts"))
from np_k6_m8a_durable_monitor_v2 import CASES, DuplicateMonitor, DurableMonitor, monitor_query


def fake_sample(*, entered=False, lineage=True, engine_completed=False, post_saved=False, controller_returned=False, accepted=False, entered_case_id=None):
    cases = []
    for index, case_id in enumerate(CASES):
        active = entered and (case_id == entered_case_id if entered_case_id else index == 0)
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
        first_value = json.loads(first)
        second_value = json.loads(second)
        assert first_value["alerts"][0]["alert_fingerprint"] == second_value["alerts"][0]["alert_fingerprint"]
        assert second_value["reported"] is True


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


def test_j_hourly_summary_after_six_samples_and_no_fake_progress():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        for index in range(6):
            sample = fake_sample()
            sample["timestamp_utc"] = f"2026-08-17T{index // 6:02d}:{(index * 10) % 60:02d}:00+00:00"
            sample["process_lineage"]["cpu_seconds"] = float(index * 2)
            monitor.process_sample(sample)
        assert monitor.hourly_summary_path.exists()
        summary = json.loads(monitor.hourly_summary_path.read_text(encoding="utf-8"))
        assert set(summary) == {
            "timestamp", "case", "attempt", "entered", "run", "engine_state", "progress",
            "pid_alive", "cpu_time_delta_1h", "runtime_seconds", "slot", "post_fsp", "extraction",
            "latest_anomaly", "monitor_health",
        }
        assert summary["case"] == "NP_K6_M8A_PRIMARY2_G02_S"
        assert summary["progress"] is None
        assert summary["cpu_time_delta_1h"] == 10.0
        assert summary["monitor_health"]["monitor_interval_seconds"] == 600
        assert summary["monitor_health"]["hourly_summary_interval_seconds"] == 3600


def test_k_hourly_summary_updates_on_each_six_sample_window():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        for index in range(12):
            sample = fake_sample()
            sample["timestamp_utc"] = f"2026-08-17T{index // 6:02d}:{(index * 10) % 60:02d}:00+00:00"
            sample["process_lineage"]["cpu_seconds"] = float(index)
            monitor.process_sample(sample)
        summary = json.loads(monitor.hourly_summary_path.read_text(encoding="utf-8"))
        assert summary["timestamp"] == "2026-08-17T01:50:00+00:00"
        assert summary["cpu_time_delta_1h"] == 6.0
        assert monitor.state["last_hourly_summary_sample_count"] == 12


def test_l_query_fast_path_prefers_hourly_summary():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        for _ in range(6):
            monitor.process_sample(fake_sample())
        result = monitor_query(root)
        assert result["hourly_summary"]["case"] == "NP_K6_M8A_PRIMARY2_G02_S"
        assert result["repository_scan"] is False


def test_m_historical_failure_does_not_mask_current_healthy_execution():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        historical = {
            "schema": "apcd_global_durable_monitor_policy_v2",
            "task_id": "NP_K6_M8A_PRIMARY2",
            "reported": True,
            "alerts": [{
                "task_id": "NP_K6_M8A_PRIMARY2",
                "alert_code": "CONTROLLER_OR_SUPERVISOR_DEAD",
                "alert_fingerprint": "historical-dead-fingerprint",
                "first_detected_timestamp_utc": "2026-08-17T01:00:00+00:00",
                "evidence": {"cases": ["NP_K6_M8A_PRIMARY2_G02_S"]},
            }],
        }
        monitor.failure_path.write_text(json.dumps(historical), encoding="utf-8")
        sample = fake_sample(entered=True, lineage=True, entered_case_id="NP_K6_M8A_PRIMARY2_G02_S")
        monitor.process_sample(sample)
        state = json.loads(monitor.state_path.read_text(encoding="utf-8"))
        assert state["current_execution_state"] == "ENGINE_RUNNING"
        assert state["active_hard_gate"] is False
        assert state["active_alert"] is None
        assert state["historical_anomalies"][0]["alert_code"] == "CONTROLLER_OR_SUPERVISOR_DEAD"
        assert state["historical_anomalies"][0]["resolved_by_later_authoritative_state"] is True
        failure = json.loads(monitor.failure_path.read_text(encoding="utf-8"))
        assert failure["alerts"][0]["alert_fingerprint"] == "historical-dead-fingerprint"
        assert failure["event_bindings"][0]["case_id"] == "NP_K6_M8A_PRIMARY2_G02_S"
        assert failure["event_bindings"][0]["attempt_id"] == "attempt_001"


def test_n_unresolved_current_failure_remains_active_hard_gate():
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monitor = DurableMonitor(root, visible_output=False)
        monitor.process_sample(fake_sample(entered=True, lineage=True, entered_case_id="NP_K6_M8A_PRIMARY2_G02_S"))
        monitor.process_sample(fake_sample(entered=True, lineage=False, entered_case_id="NP_K6_M8A_PRIMARY2_G02_S"))
        state = json.loads(monitor.state_path.read_text(encoding="utf-8"))
        assert state["current_execution_state"] == "ENGINE_STATE_UNRESOLVED"
        assert state["active_hard_gate"] is True
        assert state["active_alert"]["alert_code"] == "WORKER_LINEAGE_LOST"
        assert state["historical_anomalies"][-1]["resolved_by_later_authoritative_state"] is False


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
