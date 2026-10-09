import math
import os

import psutil


def identity(pid=None):
    p = psutil.Process(os.getpid() if pid is None else pid)
    return {
        "pid": p.pid,
        "creation_time": p.create_time(),
        "ppid": p.ppid(),
        "executable": p.exe(),
        "command": p.cmdline(),
        "user": p.username(),
    }


def identity_state(record):
    if (
        not isinstance(record, dict)
        or type(record.get("pid")) is not int
        or type(record.get("creation_time")) not in (int, float)
        or not math.isfinite(record["creation_time"])
        or not record.get("executable")
    ):
        return "unknown"
    try:
        p = psutil.Process(record["pid"])
        if abs(p.create_time() - record["creation_time"]) > 0.001:
            return "reused"
        if os.path.normcase(p.exe()) != os.path.normcase(record["executable"]):
            return "unknown"
        return "live" if p.is_running() else "dead"
    except psutil.NoSuchProcess:
        return "dead"
    except (psutil.AccessDenied, OSError):
        return "unknown"


def census():
    result = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if any(v in (p.info["name"] or "").lower() for v in ["fdtd", "python"]):
                result.append(identity(p.pid))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            result.append({"pid": p.pid, "state": "unknown"})
    return result
