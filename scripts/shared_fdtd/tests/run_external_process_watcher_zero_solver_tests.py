from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB, utc_now
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.reconciler import closeout_owned_postentry_no_truth

WATCHER = ROOT / "scripts" / "shared_fdtd" / "tools" / "external_process_watcher.py"
SCHEMA = ROOT / "scripts" / "shared_fdtd" / "control_v3" / "schema.sql"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def wait_for(path: Path, key: str, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            value = read_json(path)
            if key in value:
                return value
        time.sleep(0.05)
    raise AssertionError(f"timeout waiting for {key}: {path}")


def spawn(mode: str, token: str, state: Path, stop: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, str(__file__), "--dummy-mode", mode, token, str(state), str(stop)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def wait_pid_gone(pid: int, timeout: float = 5.0) -> None:
    import psutil
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and psutil.pid_exists(pid):
        time.sleep(0.05)


def dummy(mode: str, token: str, state_path: str, stop_path: str) -> int:
    state = Path(state_path)
    stop = Path(stop_path)
    if mode == "child":
        write_json(state, {"child_ready": True, "pid": os.getpid()})
        deadline = time.monotonic() + 20
        while not stop.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        write_json(state, {"child_stopped": True, "pid": os.getpid()})
        return 0
    if mode in {"host-normal", "host-hold", "host-crash", "host-detached", "host-finally"}:
        child_state = state.with_name(state.stem + "_child.json")
        child_stop = state.with_name(state.stem + "_child.stop")
        child = spawn("child", token, child_state, child_stop)
        wait_for(child_state, "child_ready")
        write_json(state, {"host_ready": True, "pid": os.getpid(), "child_pid": child.pid})
        if mode == "host-normal":
            child_stop.touch()
            child.wait(timeout=5)
            write_json(state, {"host_completed": True, "child_pid": child.pid})
            return 0
        if mode in {"host-crash", "host-detached"}:
            os._exit(91)
        try:
            if mode == "host-finally":
                raise RuntimeError("injected cleanup path")
            while not stop.exists():
                time.sleep(0.05)
        finally:
            write_json(state, {"host_finally": True, "child_pid": child.pid})
            child_stop.touch()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.terminate()
        return 0
    if mode in {"observer", "controller"}:
        write_json(state, {mode + "_ready": True, "pid": os.getpid()})
        while not stop.exists():
            time.sleep(0.05)
        return 0
    raise SystemExit(f"unknown dummy mode: {mode}")


def process_probe(case: str):
    import psutil
    needle = case.lower()
    rows = []
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline", "create_time"]):
        try:
            info = proc.info
            cmd = " ".join(info.get("cmdline") or [])
            if needle in cmd.lower():
                rows.append({"ProcessId": info["pid"], "ParentProcessId": info.get("ppid") or 0, "Name": info.get("name") or "", "CommandLine": cmd})
        except (psutil.Error, OSError):
            pass
    return rows


def reconciler_case(root: Path, live: bool) -> str:
    root.mkdir(parents=True, exist_ok=True)
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    case = "EXTWATCH_RECON_" + uuid.uuid4().hex[:8]
    attempt = root / "attempt"
    attempt.mkdir()
    with db.immediate() as con:
        con.execute(
            "INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            ("coupling_ml", case, "attempt_001", "SCIENTIFIC_SOLVER_RUNNING", json.dumps({"attempt_root": str(attempt), "runtime": str(root / "runtime")}), utc_now(), utc_now()),
        )
    lease = Allocator(db).acquire("coupling_ml", case, "attempt_001")
    Allocator(db).mark_entered(lease)
    append_event(attempt / "events.jsonl", "SCIENTIFIC_SOLVER_ENTERED", process_identity={"pid": 1234})
    result = closeout_owned_postentry_no_truth(
        db, "coupling_ml", {(case, "attempt_001"): attempt},
        process_probe=(lambda _state: [{"ProcessId": 1234, "Name": "dummy-engine.exe", "CommandLine": case}]) if live else (lambda _state: []),
    )
    if live:
        assert result[0]["status"] == "SOLVER_STILL_RUNNING"
        assert next(x for x in Allocator(db).list_slots_readonly() if x["slot_id"] == lease.slot_id)["state"] == "LIVE"
        return "SOLVER_STILL_RUNNING"
    assert result[0]["status"] == "TRUTH_FINALIZATION_PENDING"
    assert result[0]["release"] == "PRESERVED"
    assert result[0]["replay"] == 0
    assert next(x for x in Allocator(db).list_slots_readonly() if x["slot_id"] == lease.slot_id)["state"] == "LIVE"
    return "TRUTH_FINALIZATION_PENDING"


def run_tests() -> dict:
    root = Path(tempfile.mkdtemp(prefix="external-watcher-topology-"))
    token = "EXTWATCH_" + uuid.uuid4().hex
    watcher_out = root / "watcher"
    manifest = root / "manifest.json"
    stop_file = root / "watcher.stop"
    watcher_stderr = (root / "watcher.stderr").open("w", encoding="utf-8")
    manifest.write_text(json.dumps({
        "schema": "APCD_EXTERNAL_PROCESS_WATCHER_MANIFEST_V1",
        "watcher_id": token,
        "match_rules": [{"names": ["python.exe", "pythonw.exe"], "tokens": [token]}],
    }, indent=2) + "\n", encoding="utf-8")
    watcher = subprocess.Popen(
        [sys.executable, str(WATCHER), "--manifest", str(manifest), "--output-dir", str(watcher_out), "--interval", "0.05", "--stop-file", str(stop_file)],
        stdout=subprocess.DEVNULL,
        stderr=watcher_stderr,
        creationflags=CREATE_NO_WINDOW,
    )
    results = {}
    processes = []
    try:
        # A: normal host completion.
        state = root / "a.json"; stop = root / "a.stop"; p = spawn("host-normal", token, state, stop); p.wait(timeout=8); results["A_normal_host_completion"] = p.returncode == 0
        # B: host exits unexpectedly, child remains until independently stopped.
        state = root / "b.json"; stop = root / "b.stop"; child_stop = state.with_name(state.stem + "_child.stop"); p = spawn("host-crash", token, state, stop); wait_for(state, "host_ready"); p.wait(timeout=5); child_pid = read_json(state)["child_pid"]; results["B_host_unexpected_child_survives"] = p.returncode == 91 and __import__("psutil").pid_exists(child_pid); child_stop.touch(); wait_pid_gone(child_pid)
        # C: force-terminate host, child remains.
        state = root / "c.json"; stop = root / "c.stop"; child_stop = state.with_name(state.stem + "_child.stop"); p = spawn("host-hold", token, state, stop); wait_for(state, "host_ready"); child_pid = read_json(state)["child_pid"]; stop_process(p); results["C_host_force_terminated_child_survives"] = not __import__("psutil").pid_exists(p.pid) and __import__("psutil").pid_exists(child_pid); child_stop.touch(); wait_pid_gone(child_pid)
        # D: observer disappears while host and child remain.
        observer_state = root / "d_observer.json"; observer_stop = root / "d_observer.stop"; observer = spawn("observer", token, observer_state, observer_stop); wait_for(observer_state, "observer_ready"); state = root / "d_host.json"; stop = root / "d_host.stop"; child_stop = state.with_name(state.stem + "_child.stop"); host = spawn("host-hold", token, state, stop); wait_for(state, "host_ready"); child_pid = read_json(state)["child_pid"]; stop_process(observer); results["D_observer_disappears_host_child_remain"] = host.poll() is None and __import__("psutil").pid_exists(child_pid); stop_process(host); child_stop.touch(); wait_pid_gone(child_pid); observer_stop.touch()
        # E/F: controller and host/control processes disappear; independent watcher remains.
        controller_state = root / "e_controller.json"; controller_stop = root / "e_controller.stop"; controller = spawn("controller", token, controller_state, controller_stop); wait_for(controller_state, "controller_ready"); state = root / "e_host.json"; stop = root / "e_host.stop"; child_stop = state.with_name(state.stem + "_child.stop"); host = spawn("host-hold", token, state, stop); wait_for(state, "host_ready"); child_pid = read_json(state)["child_pid"]; stop_process(controller); stop_process(host); results["E_controller_disappears_child_active"] = __import__("psutil").pid_exists(child_pid); results["F_watcher_survives_control_disappearance"] = watcher.poll() is None; child_stop.touch(); wait_pid_gone(child_pid); controller_stop.touch()
        # G: parent close / no Job Object path: detached child survives parent exit.
        state = root / "g.json"; stop = root / "g.stop"; child_stop = state.with_name(state.stem + "_child.stop"); p = spawn("host-detached", token, state, stop); wait_for(state, "host_ready"); p.wait(timeout=5); child_pid = read_json(state)["child_pid"]; results["G_parent_close_child_survives"] = p.returncode == 91 and __import__("psutil").pid_exists(child_pid); child_stop.touch(); wait_pid_gone(child_pid)
        # H: finally/cleanup path is durable and harmless.
        state = root / "h.json"; stop = root / "h.stop"; p = spawn("host-finally", token, state, stop); p.wait(timeout=5); results["H_cleanup_finally_path"] = p.returncode != 0 and read_json(state).get("host_finally") is True
        # I/J: reconciler preserves live entry and only closeouts after process loss; heartbeat is DB-only.
        results["I_reconciler_live_preserves_entry"] = reconciler_case(root / "i", True) == "SOLVER_STILL_RUNNING"
        results["I_reconciler_process_loss_preserves_owner"] = reconciler_case(root / "i_loss", False) == "TRUTH_FINALIZATION_PENDING"
        (root / "j").mkdir(parents=True, exist_ok=True)
        db = ControlDB(root / "j" / "control.sqlite3"); db.initialize(SCHEMA)
        case = "EXTWATCH_HEARTBEAT_" + uuid.uuid4().hex[:8]; lease = Allocator(db).acquire("coupling_ml", case, "attempt_001"); Allocator(db).mark_entered(lease); Allocator(db).heartbeat(lease)
        with db.connect(readonly=True) as con:
            heartbeat_count = con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='HEARTBEAT'", (case,)).fetchone()[0]
        results["J_heartbeat_without_science"] = heartbeat_count == 1
        results["J_heartbeat_lease_transition"] = lease.fencing_generation > 0
        alive_before_stop = watcher.poll() is None
        time.sleep(1.0)
        stop_file.touch()
        watcher.wait(timeout=8)
        watcher_stderr.close()
        watcher_error_text = (root / "watcher.stderr").read_text(errors="replace")
        results["watcher_alive_before_stop"] = alive_before_stop
        results["watcher_returncode"] = watcher.returncode == 0
        lines = [json.loads(x) for x in (watcher_out / "external_process_watcher.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        results["watcher_started_heartbeat_stopped"] = all(any(x["event_type"] == event for x in lines) for event in ("WATCHER_STARTED", "WATCHER_HEARTBEAT", "WATCHER_STOPPED"))
        results["watcher_process_created_and_disappeared"] = any(x["event_type"] == "PROCESS_CREATED" for x in lines) and any(x["event_type"] == "PROCESS_DISAPPEARED" for x in lines)
        results["watcher_durable_flush"] = (watcher_out / "watcher_heartbeat.json").is_file() and (watcher_out / "external_process_watcher.jsonl").stat().st_size > 0
        return {"status": "PASS" if all(results.values()) else "FAIL", "count": len(results), "passed": sum(bool(x) for x in results.values()), "results": results, "watcher_events": [{"event_type": x.get("event_type"), "pid": (x.get("process") or {}).get("pid"), "name": (x.get("process") or {}).get("name"), "command_line": (x.get("process") or {}).get("command_line")} for x in lines], "watcher_stderr": watcher_error_text, "watcher_returncode_value": watcher.returncode, "solver_invocations": 0, "root": str(root)}
    finally:
        stop_file.touch()
        if watcher.poll() is None:
            try: watcher.wait(timeout=3)
            except subprocess.TimeoutExpired: watcher.terminate()
        if not watcher_stderr.closed:
            watcher_stderr.close()
        shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--dummy-mode":
        return dummy(*sys.argv[2:])
    result = run_tests()
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
