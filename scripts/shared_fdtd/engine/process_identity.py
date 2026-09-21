from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psutil

from shared_fdtd.control_v3.db import utc_now


def _row(process):
    info = process.info
    created = info.get("create_time")
    creation = (
        datetime.fromtimestamp(created, timezone.utc).isoformat()
        if created
        else ""
    )
    command = info.get("cmdline") or []
    if isinstance(command, (list, tuple)):
        command = " ".join(str(value) for value in command)
    return {
        "ProcessId": int(info["pid"]),
        "ParentProcessId": int(info.get("ppid") or 0),
        "Name": info.get("name") or "",
        "CreationDate": creation,
        "CommandLine": str(command),
    }


def snapshot(case_text=""):
    needle = case_text.lower()
    rows = []
    for process in psutil.process_iter(
        ["pid", "ppid", "name", "create_time", "cmdline"]
    ):
        try:
            row = _row(process)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        if not needle or needle in row["CommandLine"].lower():
            rows.append(row)
    return rows


def host_identity():
    created = psutil.Process(os.getpid()).create_time()
    return {
        "pid": os.getpid(),
        "creation_time_utc": datetime.fromtimestamp(
            created, timezone.utc
        ).isoformat(),
        "recorded_at": utc_now(),
    }


def write_identity(path, case, attempt, lease):
    data = {
        "case": case,
        "attempt": attempt,
        "host": host_identity(),
        "slot_id": lease.slot_id,
        "fencing_generation": lease.fencing_generation,
        "processes": snapshot(case),
    }
    Path(path).write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return data
