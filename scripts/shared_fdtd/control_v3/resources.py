from __future__ import annotations

import csv
import ctypes
import io
import json
import os
import subprocess
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ACTIVE_RESERVATION_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")


class ResourceCapacityWait(RuntimeError):
    """Admission was safely deferred; no scientific entry was made."""

    def __init__(self, evidence: dict[str, Any]):
        self.evidence = evidence
        super().__init__("WAIT_RESOURCE_CAPACITY: " + json.dumps(evidence, sort_keys=True, default=str))


@dataclass(frozen=True)
class ResourceRequest:
    resource_class: str
    estimated_peak_ram_bytes: int | None
    estimated_commit_bytes: int | None
    mpi_ranks: int
    threads: int
    integrated_pw: bool
    safety_margin_ratio: float = 0.25

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ResourceRequest | None":
        nested = payload.get("resource_request")
        source = dict(nested) if isinstance(nested, dict) else {}
        for key in ("resource_class", "estimated_peak_ram_bytes", "estimated_commit_bytes", "mpi_ranks", "threads", "integrated_pw", "safety_margin_ratio"):
            if key in payload:
                source[key] = payload[key]
        if not bool(payload.get("production_science")) and not bool(source):
            return None
        return cls(
            resource_class=str(source.get("resource_class", "UNKNOWN")).upper(),
            estimated_peak_ram_bytes=_positive_int(source.get("estimated_peak_ram_bytes")),
            estimated_commit_bytes=_positive_int(source.get("estimated_commit_bytes")),
            mpi_ranks=int(source.get("mpi_ranks", payload.get("processes", 1))),
            threads=int(source.get("threads", payload.get("threads", 1))),
            integrated_pw=bool(source.get("integrated_pw", payload.get("integrated_pw", False))),
            safety_margin_ratio=float(source.get("safety_margin_ratio", 0.25)),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResourceSnapshot:
    status: str
    captured_utc: str
    total_physical_bytes: int | None
    available_physical_bytes: int | None
    total_commit_bytes: int | None
    available_commit_bytes: int | None
    current_commit_bytes: int | None
    pagefile_headroom_bytes: int | None
    engine_process_count: int
    engine_working_set_bytes: int
    smpd_process_count: int
    mpiexec_process_count: int
    process_count: int
    process_errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _positive_int(value: Any) -> int | None:
    if value in (None, "", 0, "0"):
        return None
    value = int(value)
    return value if value > 0 else None


def ensure_resource_tables(con) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS resource_reservations (
          reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
          branch_id TEXT NOT NULL,
          logical_case_id TEXT NOT NULL,
          attempt_id TEXT NOT NULL,
          slot_id TEXT NOT NULL,
          resource_class TEXT NOT NULL,
          estimated_peak_ram_bytes INTEGER,
          estimated_commit_bytes INTEGER,
          mpi_ranks INTEGER NOT NULL,
          threads INTEGER NOT NULL,
          integrated_pw INTEGER NOT NULL DEFAULT 0,
          safety_margin_ratio REAL NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED','RELEASED')),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          released_at TEXT,
          UNIQUE(branch_id, logical_case_id, attempt_id)
        );
        CREATE INDEX IF NOT EXISTS idx_resource_reservations_active
          ON resource_reservations(state, branch_id, integrated_pw);
        """
    )


def _memory_status() -> dict[str, int]:
    if os.name != "nt":
        raise OSError("Windows memory API unavailable")

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    value = MemoryStatusEx()
    value.dwLength = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    total_commit = int(value.ullTotalPageFile)
    available_commit = int(value.ullAvailPageFile)
    return {
        "total_physical_bytes": int(value.ullTotalPhys),
        "available_physical_bytes": int(value.ullAvailPhys),
        "total_commit_bytes": total_commit,
        "available_commit_bytes": available_commit,
        "current_commit_bytes": total_commit - available_commit,
        "pagefile_headroom_bytes": available_commit,
    }


def _processes_from_windows() -> tuple[list[dict[str, Any]], list[str]]:
    if os.name != "nt":
        return [], ["process census unavailable on non-Windows"]

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong), ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_wchar * 260),
        ]

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot == invalid_handle:
        return [], ["CreateToolhelp32Snapshot failed"]
    rows: list[dict[str, Any]] = []
    try:
        entry = ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(entry)
        first = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while first:
            pid = int(entry.th32ProcessID)
            working_set = 0
            handle = kernel32.OpenProcess(0x0410, False, pid)
            if handle:
                counters = ProcessMemoryCounters()
                counters.cb = ctypes.sizeof(counters)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                    working_set = int(counters.WorkingSetSize)
                kernel32.CloseHandle(handle)
            rows.append({"Name": entry.szExeFile, "ProcessId": pid, "WorkingSetSize": working_set})
            first = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return rows, [] if rows else ["process census returned no rows"]


def read_resource_snapshot(process_provider: Callable[[], Iterable[dict[str, Any]]] | None = None) -> ResourceSnapshot:
    captured = datetime.now(timezone.utc).isoformat()
    errors: list[str] = []
    try:
        memory = _memory_status()
    except Exception as exc:
        memory = {key: None for key in ("total_physical_bytes", "available_physical_bytes", "total_commit_bytes", "available_commit_bytes", "current_commit_bytes", "pagefile_headroom_bytes")}
        errors.append("memory:" + repr(exc))
    try:
        if process_provider is None:
            processes, process_errors = _processes_from_windows()
            errors.extend("process:" + x for x in process_errors)
        else:
            processes = list(process_provider())
    except Exception as exc:
        processes = []
        errors.append("process:" + repr(exc))
    engine_names = {"fdtd-engine-msmpi.exe", "fdtd-solutions.exe"}
    smpd_names = {"smpd.exe", "smpd-intel-4.0.3.009-x64.exe"}
    mpiexec_names = {"mpiexec.exe", "mpiexec.hydra.exe"}
    engine = [row for row in processes if str(row.get("Name", "")).lower() in engine_names]
    smpd = [row for row in processes if str(row.get("Name", "")).lower() in smpd_names]
    mpiexec = [row for row in processes if str(row.get("Name", "")).lower() in mpiexec_names]
    working_set = sum(int(row.get("WorkingSetSize") or row.get("working_set_bytes") or 0) for row in engine)
    return ResourceSnapshot(
        status="PASS" if not errors and memory["available_physical_bytes"] is not None else "DEGRADED",
        captured_utc=captured,
        **memory,
        engine_process_count=len(engine),
        engine_working_set_bytes=working_set,
        smpd_process_count=len(smpd),
        mpiexec_process_count=len(mpiexec),
        process_count=len(processes),
        process_errors=tuple(errors),
    )


def _active_reservations(con) -> list[dict[str, Any]]:
    ensure_resource_tables(con)
    return [dict(row) for row in con.execute("SELECT * FROM resource_reservations WHERE state IN (?,?,?,?)", ACTIVE_RESERVATION_STATES)]


def resource_admission(con, branch: str, request: ResourceRequest, snapshot: ResourceSnapshot, *, pw_integrated_max_concurrent: int = 1) -> dict[str, Any]:
    rows = _active_reservations(con)
    reasons: list[str] = []
    if request.resource_class not in {"LIGHT", "STANDARD", "HEAVY"}:
        reasons.append("RESOURCE_CLASS_UNDECLARED")
    if request.estimated_peak_ram_bytes is None or request.estimated_commit_bytes is None:
        reasons.append("RESOURCE_ESTIMATE_REQUIRED")
    if snapshot.status != "PASS":
        reasons.append("RESOURCE_SNAPSHOT_DEGRADED")
    integrated_count = sum(int(row["integrated_pw"]) for row in rows if row["branch_id"] == "coupling_ml" and int(row["integrated_pw"]) == 1)
    if request.integrated_pw and integrated_count >= pw_integrated_max_concurrent:
        reasons.append("PW_INTEGRATED_CONCURRENCY_LIMIT")
    active_slots = [dict(row) for row in con.execute("SELECT slot_id,owner_branch,logical_case_id,attempt_id,state FROM slots WHERE state <> 'FREE'")]
    reservation_keys = {(row["branch_id"], row["logical_case_id"], row["attempt_id"]) for row in rows}
    # Traditional is a valid foreign branch with no ML-specific reservation row.
    known_unreserved_foreign_branches = {"traditional"}
    unknown_active = [
        row for row in active_slots
        if row["owner_branch"] not in known_unreserved_foreign_branches
        and (row["owner_branch"], row["logical_case_id"], row["attempt_id"]) not in reservation_keys
    ]
    if unknown_active:
        reasons.append("ACTIVE_OWNER_WITHOUT_RESOURCE_RESERVATION")
    reserved_ram = sum(int(row["estimated_peak_ram_bytes"] or 0) for row in rows)
    reserved_commit = sum(int(row["estimated_commit_bytes"] or 0) for row in rows)
    requested_ram = int(request.estimated_peak_ram_bytes or 0)
    requested_commit = int(request.estimated_commit_bytes or 0)
    margin = max(0.0, float(request.safety_margin_ratio))
    projected_ram = int((reserved_ram + requested_ram) * (1.0 + margin))
    projected_commit = int((reserved_commit + requested_commit) * (1.0 + margin))
    if snapshot.available_physical_bytes is None or projected_ram > snapshot.available_physical_bytes:
        reasons.append("PHYSICAL_RAM_HEADROOM")
    if snapshot.available_commit_bytes is None or projected_commit > snapshot.available_commit_bytes:
        reasons.append("COMMIT_HEADROOM")
    return {
        "RESOURCE_PREFLIGHT": "PASS" if not reasons else "WAIT_RESOURCE_CAPACITY",
        "status": "PASS" if not reasons else "WAIT_RESOURCE_CAPACITY",
        "branch": branch,
        "request": request.as_dict(),
        "snapshot": snapshot.as_dict(),
        "active_reservation_count": len(rows),
        "active_integrated_pw_count": integrated_count,
        "unknown_active_slot_count": len(unknown_active),
        "reserved_peak_ram_bytes": reserved_ram,
        "reserved_commit_bytes": reserved_commit,
        "projected_peak_ram_bytes": projected_ram,
        "projected_commit_bytes": projected_commit,
        "safety_margin_ratio": margin,
        "pw_integrated_max_concurrent": pw_integrated_max_concurrent,
        "reasons": reasons,
    }


def append_resource_sample(path: str | Path, sample: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(sample, sort_keys=True, default=str) + "\\n")
        handle.flush()
        os.fsync(handle.fileno())


def runtime_resource_sample(request: ResourceRequest | None, *, snapshot_provider: Callable[[], ResourceSnapshot] = read_resource_snapshot) -> dict[str, Any]:
    try:
        snapshot = snapshot_provider()
        sample = {"event_type": "RESOURCE_SAMPLE", "timestamp_utc": snapshot.captured_utc, "snapshot": snapshot.as_dict()}
        if request is not None:
            margin = 1.0 + max(0.0, request.safety_margin_ratio)
            pressure = (snapshot.available_physical_bytes is None or snapshot.available_commit_bytes is None or snapshot.available_physical_bytes < int((request.estimated_peak_ram_bytes or 0) * margin) or snapshot.available_commit_bytes < int((request.estimated_commit_bytes or 0) * margin))
            if pressure:
                sample.update({"event_type": "RESOURCE_PRESSURE_WARNING", "new_admissions_blocked": True, "scientific_solver_action": "NONE"})
        return sample
    except BaseException as exc:
        return {"event_type": "RESOURCE_MONITOR_DEGRADED", "timestamp_utc": datetime.now(timezone.utc).isoformat(), "error": repr(exc), "new_admissions_blocked": True, "scientific_solver_action": "NONE"}


class RuntimeResourceMonitor:
    def __init__(self, request: ResourceRequest | None, path: str | Path, *, interval_s: float = 30.0, sample_provider: Callable[[], ResourceSnapshot] = read_resource_snapshot):
        self.request = request
        self.path = Path(path)
        self.interval_s = max(1.0, float(interval_s))
        self.sample_provider = sample_provider
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        def loop() -> None:
            while not self._stop.is_set():
                sample = runtime_resource_sample(self.request, snapshot_provider=self.sample_provider)
                try:
                    append_resource_sample(self.path, sample)
                except BaseException:
                    pass
                self._stop.wait(self.interval_s)
        self._thread = threading.Thread(target=loop, name="v3-resource-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=min(5.0, self.interval_s + 1.0))
