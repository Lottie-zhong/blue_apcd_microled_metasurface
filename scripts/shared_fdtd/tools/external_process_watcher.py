from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def creation_time(proc: psutil.Process) -> str | None:
    try:
        return datetime.fromtimestamp(proc.create_time(), timezone.utc).isoformat()
    except (psutil.Error, OSError, ValueError):
        return None


def process_row(proc: psutil.Process) -> dict:
    try:
        info = proc.as_dict(attrs=["pid", "ppid", "name", "cmdline", "create_time"])
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return {}
    cmdline = info.get("cmdline") or []
    if isinstance(cmdline, (list, tuple)):
        cmdline = " ".join(str(x) for x in cmdline)
    return {
        "pid": int(info.get("pid") or proc.pid),
        "ppid": int(info.get("ppid") or 0),
        "name": str(info.get("name") or ""),
        "command_line": str(cmdline),
        "creation_time_utc": (
            datetime.fromtimestamp(float(info["create_time"]), timezone.utc).isoformat()
            if info.get("create_time") else None
        ),
    }


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("watcher manifest must be an object")
    data.setdefault("watcher_id", path.stem)
    data.setdefault("match_rules", [])
    data.setdefault("seed_pids", [])
    if not data["match_rules"] and not data["seed_pids"]:
        raise ValueError("watcher manifest needs match_rules or seed_pids")
    return data


def matches(row: dict, manifest: dict) -> bool:
    if not row:
        return False
    if int(row["pid"]) in {int(x) for x in manifest.get("seed_pids", [])}:
        return True
    name = row["name"].lower()
    command = row["command_line"].lower()
    for rule in manifest.get("match_rules", []):
        names = {str(x).lower() for x in rule.get("names", [])}
        tokens = [str(x).lower() for x in rule.get("tokens", [])]
        if name in names and (not tokens or any(token in command for token in tokens)):
            return True
    return False


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    with tmp.open("r+b") as fh:
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class ExternalProcessWatcher:
    def __init__(self, manifest_path: str | Path, output_dir: str | Path, interval_s: float = 0.5, stop_file: str | Path | None = None):
        self.manifest_path = Path(manifest_path)
        self.manifest = load_manifest(self.manifest_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeline = self.output_dir / "external_process_watcher.jsonl"
        self.heartbeat_path = self.output_dir / "watcher_heartbeat.json"
        self.interval_s = max(float(interval_s), 0.05)
        self.stop_file = Path(stop_file) if stop_file else None
        self.watcher_pid = os.getpid()
        self.watcher_proc = psutil.Process(self.watcher_pid)
        self.seen: dict[int, tuple[psutil.Process, dict]] = {}
        self.last_state: dict[int, dict] = {}
        self.watcher_identity = {
            "pid": self.watcher_pid,
            "ppid": os.getppid(),
            "creation_time_utc": creation_time(self.watcher_proc),
            "started_utc": utc_now(),
        }

    def emit(self, event_type: str, **payload) -> None:
        row = {"timestamp_utc": utc_now(), "event_type": event_type, **payload}
        with self.timeline.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def snapshot(self) -> dict[int, tuple[psutil.Process, dict]]:
        current = {}
        candidate_names = {
            str(name).lower()
            for rule in self.manifest.get("match_rules", [])
            for name in rule.get("names", [])
        }
        seed_pids = {int(x) for x in self.manifest.get("seed_pids", [])}
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.pid not in seed_pids and str(proc.info.get("name") or "").lower() not in candidate_names:
                    continue
            except (psutil.Error, OSError):
                continue
            row = process_row(proc)
            if matches(row, self.manifest):
                current[row["pid"]] = (proc, row)
        return current

    def observe(self) -> None:
        current = self.snapshot()
        current_pids = set(current)
        for pid, (proc, row) in current.items():
            parent_seen = row["ppid"] in current_pids
            previous = self.last_state.get(pid)
            if previous is None:
                self.emit("PROCESS_CREATED", process=row, parent_seen=parent_seen)
            elif any(previous.get(k) != row.get(k) for k in ("ppid", "name", "command_line", "creation_time_utc")):
                self.emit("PROCESS_RELATIONSHIP_CHANGED", process=row, previous=previous, parent_seen=parent_seen)
            self.last_state[pid] = row
            self.seen[pid] = (proc, row)
        for pid in sorted(set(self.seen) - current_pids):
            proc, previous = self.seen.pop(pid)
            exit_code = None
            exit_status = "NOT_EXPOSED_AFTER_DISAPPEARANCE"
            try:
                exit_code = proc.wait(timeout=0)
                exit_status = "EXPOSED"
            except psutil.TimeoutExpired:
                exit_status = "STILL_RUNNING_OR_UNAVAILABLE"
            except (psutil.Error, OSError):
                pass
            self.emit("PROCESS_DISAPPEARED", process=previous, exit_code=exit_code, exit_code_status=exit_status)
            self.last_state.pop(pid, None)
        active = [row for _, row in current.values()]
        heartbeat = {
            "timestamp_utc": utc_now(),
            "watcher": self.watcher_identity,
            "active_processes": active,
            "active_pids": sorted(current_pids),
        }
        self.emit("WATCHER_HEARTBEAT", watcher=heartbeat)
        atomic_json(self.heartbeat_path, heartbeat)

    def run(self, duration_s: float = 0.0) -> int:
        manifest_hash = hashlib.sha256(self.manifest_path.read_bytes()).hexdigest()
        self.emit("WATCHER_STARTED", watcher=self.watcher_identity, manifest=str(self.manifest_path), manifest_sha256=manifest_hash)
        deadline = time.monotonic() + duration_s if duration_s > 0 else None
        reason = "STOP_FILE" if self.stop_file else "DURATION"
        try:
            while True:
                if self.stop_file and self.stop_file.exists():
                    reason = "STOP_FILE"
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    reason = "DURATION"
                    break
                self.observe()
                time.sleep(self.interval_s)
        except KeyboardInterrupt:
            reason = "INTERRUPT"
        finally:
            self.observe()
            self.emit("WATCHER_STOPPED", watcher={**self.watcher_identity, "stopped_utc": utc_now()}, reason=reason)
            atomic_json(self.heartbeat_path, {"timestamp_utc": utc_now(), "watcher": self.watcher_identity, "stopped": True, "reason": reason})
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--stop-file")
    args = parser.parse_args()
    return ExternalProcessWatcher(args.manifest, args.output_dir, args.interval, args.stop_file).run(args.duration)


if __name__ == "__main__":
    raise SystemExit(main())
