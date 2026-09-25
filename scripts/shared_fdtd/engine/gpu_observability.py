from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


UNKNOWN = "UNKNOWN"
_SOLVER_NAMES = {"fdtd-solutions.exe", "fdtd-engine-msmpi.exe", "fdtd-engine.exe", "mpiexec.exe", "mpiexec"}


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _pid(row):
    return str(row.get("ProcessId", row.get("pid", "")))


def _name(row):
    return str(row.get("Name", row.get("name", "")) or "")


def _relevant(row, child_pid=None):
    return _pid(row) == str(child_pid) or _name(row).lower() in _SOLVER_NAMES or "fdtd-engine" in _name(row).lower()


def _jsonl(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, default=str) + "\n")


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def _tail(path, limit=80):
    path = Path(path)
    if not path.is_file():
        return {"path": str(path), "exists": False, "tail": []}
    return {"path": str(path), "exists": True, "tail": path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]}


class GpuEngineObservability:
    """Append-only process/timeline evidence; never mutates control state."""

    def __init__(self, root, cfg, snapshot, now=None):
        self.root = Path(root)
        self.cfg = dict(cfg)
        self.snapshot = snapshot
        self.now = now or _now
        self.forensics = self.root / "forensics"
        self.timeline_path = self.forensics / "runtime_timeline.jsonl"
        self.provenance_path = self.forensics / "process_exit_provenance.json"
        self.tail_path = self.forensics / "final_log_tail.json"
        self.child_pid = None
        self.child = None
        self.records = {}
        self.last_rows = []

    def _token_hash(self):
        value = self.cfg.get("owner_token") or self.cfg.get("lease_token_hash")
        if value:
            return str(value)
        raw = self.cfg.get("lease_token")
        if raw:
            return hashlib.sha256(str(raw).encode("utf-8")).hexdigest()
        return None

    def _files(self):
        run_fsp = Path(self.cfg.get("run_fsp", ""))
        log_paths = [Path(value) for value in self.cfg.get("log_paths", [])]
        if run_fsp:
            log_paths.extend(sorted(run_fsp.parent.glob("*_p*.log")))
        h5 = Path(self.cfg["h5_path"]) if self.cfg.get("h5_path") else None
        return run_fsp, log_paths, h5

    def _rows(self):
        rows = list(self.snapshot() or [])
        self.last_rows = [row for row in rows if _relevant(row, self.child_pid)]
        timestamp = self.now()
        for row in self.last_rows:
            pid = _pid(row)
            if not pid:
                continue
            record = self.records.setdefault(pid, {"pid": pid, "first_observed_utc": timestamp, "first": dict(row)})
            record["last_observed_utc"] = timestamp
            record["last"] = dict(row)
            record["parent_pid"] = row.get("ParentProcessId", row.get("ppid", UNKNOWN))
            record["name"] = _name(row)
            record["return_code"] = row.get("returncode", UNKNOWN)
        return self.last_rows

    def observe(self, *, child=None, event="POLL", extra=None):
        if child is not None:
            self.child = child
            self.child_pid = getattr(child, "pid", self.child_pid)
        rows = self._rows()
        run_fsp, log_paths, h5 = self._files()
        child_alive = self.child is not None and self.child.poll() is None
        h5_exists = bool(h5 and h5.is_file())
        payload = {
            "timestamp_utc": self.now(),
            "event": event,
            "attempt_id": self.cfg.get("attempt"),
            "child_alive": child_alive,
            "mpiexec_alive": any(_name(row).lower() in {"mpiexec.exe", "mpiexec"} for row in rows),
            "engine_pids": [_pid(row) for row in rows if "fdtd-engine" in _name(row).lower()],
            "gpu_process_present": any("fdtd-engine" in _name(row).lower() for row in rows),
            "p0_size": max((path.stat().st_size for path in log_paths if path.is_file()), default=0),
            "p0_mtime": max((path.stat().st_mtime for path in log_paths if path.is_file()), default=None),
            "fsp_size": run_fsp.stat().st_size if run_fsp.is_file() else 0,
            "h5_exists": h5_exists,
            "h5_size": h5.stat().st_size if h5_exists else 0,
            "control_generation": self.cfg.get("control_generation", UNKNOWN),
            "hold": self.cfg.get("hold", UNKNOWN),
            "branch_enabled": self.cfg.get("branch_enabled", UNKNOWN),
            "owner_token": self._token_hash(),
            "processes": rows,
        }
        if extra:
            payload.update(extra)
        _jsonl(self.timeline_path, payload)
        return rows

    def child_started(self, child, *, command, cwd):
        self.child = child
        self.child_pid = getattr(child, "pid", None)
        self.cfg["command"] = list(command)
        self.cfg["working_directory"] = str(cwd)
        self.observe(child=child, event="CHILD_STARTED", extra={"child_pid": self.child_pid, "command": list(command), "working_directory": str(cwd)})

    def finalize(self, reason, *, child=None, command=None, cwd=None):
        if child is not None:
            self.child = child
            self.child_pid = getattr(child, "pid", self.child_pid)
        self.observe(child=self.child, event="FINAL", extra={"reason": reason})
        child_return_code = UNKNOWN
        if self.child is not None:
            value = self.child.poll()
            child_return_code = value if value is not None else UNKNOWN
        child_record = self.records.get(str(self.child_pid), {}) if self.child_pid is not None else {}
        child_record = {
            **child_record,
            "pid": self.child_pid if self.child_pid is not None else UNKNOWN,
            "return_timestamp_utc": self.now(),
            "return_code": child_return_code,
        }
        process_records = []
        for pid, record in sorted(self.records.items()):
            if str(pid) == str(self.child_pid):
                continue
            process_records.append({**record, "exit_code": record.get("return_code", UNKNOWN) or UNKNOWN})
        _atomic_json(self.provenance_path, {
            "schema": "GPU_ENGINE_EXIT_OBSERVABILITY_V1",
            "finalized_utc": self.now(),
            "reason": reason,
            "case_id": self.cfg.get("case"),
            "attempt_id": self.cfg.get("attempt"),
            "resource_name": self.cfg.get("gpu_resource_name", UNKNOWN),
            "command": list(command or self.cfg.get("command", [])),
            "working_directory": str(cwd or self.cfg.get("working_directory", UNKNOWN)),
            "child": child_record,
            "descendants": process_records,
            "last_process_snapshot": self.last_rows,
        })
        _, log_paths, _ = self._files()
        _atomic_json(self.tail_path, {
            "schema": "GPU_ENGINE_EXIT_OBSERVABILITY_V1",
            "finalized_utc": self.now(),
            "reason": reason,
            "logs": [_tail(path) for path in dict.fromkeys(log_paths)],
        })
