from __future__ import annotations

import argparse
import json
import ctypes
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
sys.path.insert(0, str(ROOT / "scripts"))
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
HOST_PYTHON = r"C:\Users\DELL\anaconda3\pythonw.exe"
HOST_SCRIPT = r"D:\apcd_runtime\bin\v3g2h.py"
def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def launch_process(command):
    class StartupInfo(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("lpReserved", ctypes.c_void_p),
            ("lpDesktop", ctypes.c_void_p), ("lpTitle", ctypes.c_void_p),
            ("dwX", ctypes.c_ulong), ("dwY", ctypes.c_ulong),
            ("dwXSize", ctypes.c_ulong), ("dwYSize", ctypes.c_ulong),
            ("dwXCountChars", ctypes.c_ulong), ("dwYCountChars", ctypes.c_ulong),
            ("dwFillAttribute", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
            ("wShowWindow", ctypes.c_ushort), ("cbReserved2", ctypes.c_ushort),
            ("lpReserved2", ctypes.c_void_p), ("hStdInput", ctypes.c_void_p),
            ("hStdOutput", ctypes.c_void_p), ("hStdError", ctypes.c_void_p),
        ]

    class ProcessInformation(ctypes.Structure):
        _fields_ = [
            ("hProcess", ctypes.c_void_p), ("hThread", ctypes.c_void_p),
            ("dwProcessId", ctypes.c_ulong), ("dwThreadId", ctypes.c_ulong),
        ]

    startup = StartupInfo()
    startup.cb = ctypes.sizeof(startup)
    process = ProcessInformation()
    command_line = ctypes.create_unicode_buffer(command)
    ok = ctypes.windll.kernel32.CreateProcessW(
        None, command_line, None, None, False, 0x08000000,
        None, str(ROOT), ctypes.byref(startup), ctypes.byref(process),
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    ctypes.windll.kernel32.CloseHandle(process.hThread)
    ctypes.windll.kernel32.CloseHandle(process.hProcess)
    return int(process.dwProcessId)


def launch_factory(db_path, preentry_only=False):
    from shared_fdtd.engine.event_log import append_event
    from shared_fdtd.control_v3.allocator import Allocator
    from shared_fdtd.control_v3.db import ControlDB
    from shared_fdtd.control_v3.resources import ResourceRequest, read_resource_snapshot
    def launch(row, lease):
        payload = json.loads(row["payload_json"])
        request = ResourceRequest.from_payload(payload)
        backend_type = payload.get("backend_type")
        if backend_type is None and (payload.get("production_science") or row["branch_id"] == "traditional"):
            backend_type = "CPU"
        boundary_snapshot = read_resource_snapshot() if (request is not None or backend_type is not None) else None
        allocator = Allocator(ControlDB(db_path))
        runtime = Path(payload["runtime"])
        runtime.mkdir(parents=True, exist_ok=True)
        config = runtime / "host_config.json"
        cfg = {
            "db": str(db_path), "runtime": str(runtime), "output_root": payload["output_root"],
            "attempt_root": payload["attempt_root"], "pre_fsp": payload["pre_fsp"],
            "pre_fsp_sha256": payload["pre_fsp_sha256"], "physical_contract_hash": payload["physical_contract_hash"],
            "branch": row["branch_id"], "case": row["logical_case_id"], "attempt": row["attempt_id"],
            "task": payload["task"], "slot_id": lease.slot_id, "lease_token": lease.lease_token,
            "fencing_generation": lease.fencing_generation, "admission_control_generation": lease.control_generation,
            "admission_provenance": lease.admission_provenance, "task_name": payload["task_name"],
            "created_utc": now(),
            "production_science": bool(payload.get("production_science", False)),
            "resource_request": payload.get("resource_request"),
            "resource_policy": payload.get("resource_policy"),
            "backend_type": payload.get("backend_type", "CPU"),
            "gpu_resource_name": payload.get("gpu_resource_name"),
            "resource_class": payload.get("resource_class"),
            "estimated_peak_ram_bytes": payload.get("estimated_peak_ram_bytes"),
            "estimated_commit_bytes": payload.get("estimated_commit_bytes"),
            "mpi_ranks": payload.get("mpi_ranks", payload.get("processes", 12)),
            "threads": payload.get("threads", 1),
            "integrated_pw": bool(payload.get("integrated_pw", False)),
            "scientific_launcher": payload.get("scientific_launcher"),
            "pw_contract": payload.get("pw_contract"),
            "entry_confirmation_poll_s": payload.get("entry_confirmation_poll_s", 0.5),
            "resource_monitor_interval_s": payload.get("resource_monitor_interval_s", 30.0),
            "scientific_entry_allowed": not preentry_only,
            "zero_solver_boundary_only": bool(preentry_only),
        }
        atomic(config, cfg)
        command = f"{HOST_PYTHON} {HOST_SCRIPT} {config}"
        def start_host(provenance):
            cfg.update(provenance)
            atomic(config, cfg)
            append_event(runtime / "events.jsonl", "HOST_START_INTENT", task_name=payload["task_name"], config=str(config), slot_id=lease.slot_id, provenance=provenance)
            host_pid = launch_process(command)
            append_event(runtime / "events.jsonl", "HOST_PROCESS_STARTED", host_pid=host_pid, command=command, provenance=provenance)
            return host_pid
        boundary = allocator.final_launch_revalidation(
            lease, resource_request=request, resource_snapshot=boundary_snapshot,
            resource_policy=payload.get("resource_policy"), backend_type=backend_type,
            admission_timestamp=(lease.admission_provenance or {}).get("admission_timestamp"),
            start=start_host,
        )
        if not boundary["eligible"]:
            return {"queue_state": "WAIT_RESOURCE_CAPACITY", "admission": boundary}
        if preentry_only:
            boundary = Path(payload["attempt_root"]) / "scientific_entry_boundary.json"
            previous_mtime_ns = boundary.stat().st_mtime_ns if boundary.is_file() else 0
            deadline = time.monotonic() + 60.0
            while time.monotonic() < deadline:
                if boundary.is_file() and boundary.stat().st_mtime_ns > previous_mtime_ns:
                    candidate = json.loads(boundary.read_text(encoding="utf-8"))
                    if (
                        candidate.get("status") == "PREENTRY_BOUNDARY_REACHED"
                        and candidate.get("case_id") == row["logical_case_id"]
                        and candidate.get("attempt_id") == row["attempt_id"]
                        and candidate.get("fencing_generation") == lease.fencing_generation
                        and candidate.get("solver_entered") is False
                        and candidate.get("scientific_solver_entry_count") == 0
                        and candidate.get("run_invocation_count") == 0
                    ):
                        return {"queue_state": "WAIT_RESOURCE_CAPACITY", "boundary": str(boundary)}
                time.sleep(0.5)
            raise RuntimeError("PREENTRY_BOUNDARY_TIMEOUT")
    return launch


def main():
    from shared_fdtd.control_v3.db import ControlDB
    from shared_fdtd.engine.dispatcher import dispatch_once
    from shared_fdtd.engine.status import readonly_status
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--preentry-only", action="store_true")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--audit", default=r"D:\apcd_runtime\global_fdtd_control_v3\dispatcher_last.json")
    args = parser.parse_args()
    db = ControlDB(args.db)
    launched = dispatch_once(db, "coupling_ml", launch_factory(Path(args.db), preentry_only=args.preentry_only))
    atomic(args.audit, {"timestamp_utc": now(), "branch": "coupling_ml", "launched": launched, "preentry_only": args.preentry_only, "status": readonly_status(db)})
    print(json.dumps({"status": "PASS", "launched": launched}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
