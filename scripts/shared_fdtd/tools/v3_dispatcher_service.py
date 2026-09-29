from __future__ import annotations

import argparse
import json
import ctypes
import os
import msvcrt
import subprocess
from ctypes import wintypes
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
HOST_PYTHON = r"C:\Users\DELL\anaconda3\python.exe"
HOST_SCRIPT = str(ROOT / "scripts" / "shared_fdtd" / "tools" / "v3_g2_host.py")
CREATE_NO_WINDOW = 0x08000000
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK = 0x00001000
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000


class LaunchContextError(RuntimeError):
    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence = evidence

def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def launch_process(command, stdout_path=None, stderr_path=None):
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

    class BasicLimit(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong), ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong), ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong), ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class ExtendedLimit(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimit), ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetCurrentProcessId.restype = wintypes.DWORD
    kernel32.IsProcessInJob.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.BOOL)]
    kernel32.IsProcessInJob.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInformation)]
    kernel32.CreateProcessW.restype = wintypes.BOOL

    in_job = wintypes.BOOL()
    is_job_ok = bool(kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), None, ctypes.byref(in_job)))
    is_job_error = ctypes.get_last_error() if not is_job_ok else 0
    job_flags = None
    query_job_ok = False
    query_job_error = 0
    if is_job_ok and in_job.value:
        limits = ExtendedLimit()
        returned = wintypes.DWORD()
        query_job_ok = bool(kernel32.QueryInformationJobObject(None, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(limits), ctypes.sizeof(limits), ctypes.byref(returned)))
        query_job_error = ctypes.get_last_error() if not query_job_ok else 0
        if query_job_ok:
            job_flags = int(limits.BasicLimitInformation.LimitFlags)
    context = {
        "process_id": int(kernel32.GetCurrentProcessId()),
        "is_process_in_job": bool(in_job.value) if is_job_ok else None,
        "is_process_in_job_ok": is_job_ok,
        "is_process_in_job_error": is_job_error,
        "query_job_extended_ok": query_job_ok,
        "query_job_extended_error": query_job_error,
        "job_limit_flags": job_flags,
        "job_breakaway_ok": bool(job_flags is not None and job_flags & JOB_OBJECT_LIMIT_BREAKAWAY_OK),
        "job_silent_breakaway_ok": bool(job_flags is not None and job_flags & JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK),
        "job_kill_on_close": bool(job_flags is not None and job_flags & JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE),
    }
    if not is_job_ok or (in_job.value and not query_job_ok):
        raise LaunchContextError("BLOCKED_TASK_JOB_CONTEXT", {"launch_context": context, "policy": "job_context_unobservable"})
    if not in_job.value or (job_flags is not None and job_flags & JOB_OBJECT_LIMIT_SILENT_BREAKAWAY_OK):
        creation_flags = CREATE_NO_WINDOW
        policy = "no_job_no_breakaway" if not in_job.value else "silent_breakaway_no_explicit_flag"
    elif job_flags & JOB_OBJECT_LIMIT_BREAKAWAY_OK:
        creation_flags = CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB
        policy = "explicit_breakaway_allowed"
    else:
        raise LaunchContextError("BLOCKED_TASK_JOB_CONTEXT", {"launch_context": context, "policy": "restrictive_job_no_safe_breakaway"})

    stdout_file = None
    stderr_file = None
    try:
        startup = StartupInfo()
        startup.cb = ctypes.sizeof(startup)
        if stdout_path is not None or stderr_path is not None:
            stdout_path = str(stdout_path or stderr_path)
            stderr_path = str(stderr_path or stdout_path)
            Path(stdout_path).parent.mkdir(parents=True, exist_ok=True)
            Path(stderr_path).parent.mkdir(parents=True, exist_ok=True)
            stdout_file = open(stdout_path, "ab", buffering=0)
            stderr_file = open(stderr_path, "ab", buffering=0)
            os.set_handle_inheritable(msvcrt.get_osfhandle(stdout_file.fileno()), True)
            os.set_handle_inheritable(msvcrt.get_osfhandle(stderr_file.fileno()), True)
            startup.dwFlags = 0x00000100  # STARTF_USESTDHANDLES
            startup.hStdOutput = msvcrt.get_osfhandle(stdout_file.fileno())
            startup.hStdError = msvcrt.get_osfhandle(stderr_file.fileno())
        process = ProcessInformation()
        command_line = ctypes.create_unicode_buffer(command)
        ok = kernel32.CreateProcessW(
            None, command_line, None, None, bool(stdout_file is not None),
            creation_flags, None, str(ROOT), ctypes.byref(startup), ctypes.byref(process)
        )
        if not ok:
            error_code = ctypes.get_last_error()
            raise LaunchContextError("CREATEPROCESS_FAILED", {
                "launch_context": context,
                "policy": policy,
                "creation_flags": creation_flags,
                "command_line": command,
                "cwd": str(ROOT),
                "stdout_path": str(stdout_path) if stdout_path else None,
                "stderr_path": str(stderr_path) if stderr_path else None,
                "createprocess_ok": False,
                "get_last_error": error_code,
                "get_last_error_message": ctypes.FormatError(error_code),
            })
        pid = int(process.dwProcessId)
        kernel32.CloseHandle(process.hThread)
        kernel32.CloseHandle(process.hProcess)
        return pid
    finally:
        if stdout_file is not None:
            stdout_file.close()
        if stderr_file is not None:
            stderr_file.close()


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
            "exact_launch_permit_id": payload.get("exact_launch_permit_id"),
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
        command = subprocess.list2cmdline([HOST_PYTHON, "-u", HOST_SCRIPT, str(config)])
        stdout_path = runtime / "host_stdout.log"
        stderr_path = runtime / "host_stderr.log"
        def start_host(provenance):
            cfg.update(provenance)
            atomic(config, cfg)
            append_event(runtime / "events.jsonl", "HOST_START_INTENT", task_name=payload["task_name"], config=str(config), slot_id=lease.slot_id, provenance=provenance)
            try:
                host_pid = launch_process(command, stdout_path=stdout_path, stderr_path=stderr_path)
            except LaunchContextError as exc:
                append_event(runtime / "events.jsonl", "HOST_PROCESS_START_FAILED", command=command, cwd=str(ROOT), stdout_path=str(stdout_path), stderr_path=str(stderr_path), error=str(exc), evidence=exc.evidence, provenance=provenance)
                raise
            launch_record = {
                "host_pid": host_pid,
                "command": command,
                "cwd": str(ROOT),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "launch_timestamp_utc": now(),
                "provenance": provenance,
            }
            append_event(runtime / "events.jsonl", "HOST_PROCESS_CREATED", **launch_record)
            append_event(runtime / "events.jsonl", "HOST_PROCESS_STARTED", **launch_record)
            return host_pid
        boundary = allocator.final_launch_revalidation(
            lease, resource_request=request, resource_snapshot=boundary_snapshot,
            resource_policy=payload.get("resource_policy"), backend_type=backend_type,
            admission_timestamp=(lease.admission_provenance or {}).get("admission_timestamp"),
            exact_permit_id=payload.get("exact_launch_permit_id"), consume_permit=False,
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
