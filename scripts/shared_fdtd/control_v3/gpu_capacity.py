from __future__ import annotations

import json
from typing import Any

from .db import utc_now

GPU_ACTIVE_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")


def ensure_gpu_capacity_tables(con, default_cap: int = 1) -> None:
    # execute each DDL statement without implicitly committing the owner transaction.
    con.execute('CREATE TABLE IF NOT EXISTS backend_capacity (\n          backend_type TEXT PRIMARY KEY,\n          physical_cap INTEGER NOT NULL CHECK(physical_cap BETWEEN 1 AND 3),\n          updated_at TEXT NOT NULL\n        )')
    con.execute("CREATE TABLE IF NOT EXISTS gpu_capacity_leases (\n          capacity_lease_id INTEGER PRIMARY KEY AUTOINCREMENT,\n          branch_id TEXT NOT NULL,\n          logical_case_id TEXT NOT NULL,\n          attempt_id TEXT NOT NULL,\n          slot_id TEXT NOT NULL,\n          lease_token_hash TEXT NOT NULL,\n          fencing_generation INTEGER NOT NULL,\n          state TEXT NOT NULL CHECK(state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED','RELEASED')),\n          created_at TEXT NOT NULL,\n          updated_at TEXT NOT NULL,\n          released_at TEXT,\n          UNIQUE(branch_id, logical_case_id, attempt_id)\n        )")
    con.execute('CREATE INDEX IF NOT EXISTS idx_gpu_capacity_leases_active\n          ON gpu_capacity_leases(state)')
    con.execute(
        "INSERT OR IGNORE INTO backend_capacity(backend_type,physical_cap,updated_at) VALUES('GPU',?,?)",
        (int(default_cap), utc_now()),
    )


def set_gpu_physical_cap(con, physical_cap: int) -> None:
    physical_cap = int(physical_cap)
    if physical_cap not in (1, 2, 3):
        raise ValueError("GPU_PHYSICAL_CONCURRENCY_CAP must be 1, 2, or 3")
    ensure_gpu_capacity_tables(con)
    con.execute("UPDATE backend_capacity SET physical_cap=?,updated_at=? WHERE backend_type='GPU'", (physical_cap, utc_now()))


def gpu_capacity_status(con, *, cap_override: int | None = None, ensure: bool = True) -> dict[str, Any]:
    if ensure:
        ensure_gpu_capacity_tables(con)
    row = con.execute("SELECT physical_cap FROM backend_capacity WHERE backend_type='GPU'").fetchone()
    configured_cap = int(row["physical_cap"] if row is not None else 1)
    cap = int(cap_override) if cap_override is not None else configured_cap
    if cap not in (1, 2, 3):
        raise ValueError("GPU capacity must be 1, 2, or 3")
    used = int(con.execute("SELECT COUNT(*) FROM gpu_capacity_leases WHERE state IN (?,?,?,?)", GPU_ACTIVE_STATES).fetchone()[0])
    return {
        "backend_type": "GPU",
        "GPU_PHYSICAL_CONCURRENCY_CAP": cap,
        "GPU_CAPACITY_USED": used,
        "GPU_CAPACITY_AVAILABLE": max(0, cap - used),
        "configured_cap": configured_cap,
        "authoritative_active_gpu_owners": used,
        "status": "PASS" if used < cap else "WAIT_RESOURCE_CAPACITY",
        "reasons": [] if used < cap else ["GPU_PHYSICAL_CAPACITY_EXHAUSTED"],
    }


def reserve_gpu_capacity(con, lease: Any) -> dict[str, Any]:
    status = gpu_capacity_status(con)
    if status["status"] != "PASS":
        raise RuntimeError(json.dumps(status, sort_keys=True))
    now = utc_now()
    existing = con.execute(
        "SELECT capacity_lease_id,state FROM gpu_capacity_leases WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (lease.owner_branch, lease.logical_case_id, lease.attempt_id),
    ).fetchone()
    values = (lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.slot_id, lease.token_hash, lease.fencing_generation, "RESERVED", now, now)
    if existing is None:
        con.execute(
            "INSERT INTO gpu_capacity_leases(branch_id,logical_case_id,attempt_id,slot_id,lease_token_hash,fencing_generation,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            values,
        )
    elif existing["state"] == "RELEASED":
        con.execute(
            "UPDATE gpu_capacity_leases SET slot_id=?,lease_token_hash=?,fencing_generation=?,state='RESERVED',created_at=?,updated_at=?,released_at=NULL WHERE capacity_lease_id=?",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, now, now, existing["capacity_lease_id"]),
        )
    else:
        raise RuntimeError("GPU_CAPACITY_LEASE_ALREADY_ACTIVE")
    return gpu_capacity_status(con)


def mutate_gpu_capacity(con, lease: Any, state: str) -> int:
    if state not in GPU_ACTIVE_STATES:
        raise ValueError("invalid GPU capacity state")
    ensure_gpu_capacity_tables(con)
    return con.execute(
        "UPDATE gpu_capacity_leases SET state=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND slot_id=? AND lease_token_hash=? AND fencing_generation=?",
        (state, utc_now(), lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.slot_id, lease.token_hash, lease.fencing_generation),
    ).rowcount


def release_gpu_capacity(con, lease: Any) -> int:
    ensure_gpu_capacity_tables(con)
    now = utc_now()
    return con.execute(
        "UPDATE gpu_capacity_leases SET state='RELEASED',released_at=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND slot_id=? AND lease_token_hash=? AND fencing_generation=? AND state<>'RELEASED'",
        (now, now, lease.owner_branch, lease.logical_case_id, lease.attempt_id, lease.slot_id, lease.token_hash, lease.fencing_generation),
    ).rowcount

import csv
import hashlib
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 1.336057 GiB was the validated 5 nm canary peak. Its ceil is the minimum
# available-memory gate. The observed 9246 MiB is a recorded baseline only.
GPU_REQUIRED_FREE_MIB = 1369
GPU_VALIDATED_BASELINE_FREE_MIB = 9246
GPU_OBSERVED_PEAK_GIB = 1.336057


def _gpu_capacity_now():
    return datetime.now(timezone.utc).isoformat()


def _gpu_capacity_int(value):
    text = str(value or "").strip()
    if not text or text.upper() in {"N/A", "[N/A]", "NOT SUPPORTED"}:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError, OverflowError):
        return None


def _gpu_capacity_unavailable(reason, details=None):
    return {
        "schema": "SHARED_V3_EXTERNAL_GPU_CAPACITY_SNAPSHOT_V1",
        "captured_at_utc": _gpu_capacity_now(),
        "capture_status": "UNAVAILABLE",
        "capture_reason": str(reason),
        "required_free_mib": GPU_REQUIRED_FREE_MIB,
        "validated_baseline_free_mib": GPU_VALIDATED_BASELINE_FREE_MIB,
        "observed_peak_gib": GPU_OBSERVED_PEAK_GIB,
        "selected_gpu": None,
        "devices": [],
        "compute_processes": [],
        "external_compute_processes": [],
        "shared_v3_active_owners": [],
        "process_attribution_status": "UNAVAILABLE",
        "process_visibility_scope": "NVIDIA_QUERY_COMPUTE_APPS",
        "process_memory_visibility": "PER_PROCESS_MEMORY_MAY_BE_NA_UNDER_WINDOWS_WDDM",
        "details": details or {},
    }


def _gpu_capacity_csv(text, expected_fields):
    if expected_fields == 4 and "no running processes found" in text.lower():
        return []
    rows = []
    for row in csv.reader((line for line in text.splitlines() if line.strip()), skipinitialspace=True):
        values = [value.strip() for value in row]
        if len(values) != expected_fields:
            raise ValueError("NVIDIA_SMI_CSV_FIELD_COUNT")
        rows.append(values)
    return rows


def _shared_v3_gpu_owners(db):
    owners = []
    bound_pids = set()
    with db.connect(readonly=True) as con:
        tables = {str(row[0]) for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "gpu_capacity_leases" not in tables or "lease_events" not in tables:
            raise RuntimeError("SHARED_V3_GPU_OWNER_TABLES_UNAVAILABLE")
        active = con.execute(
            "SELECT branch_id,logical_case_id,attempt_id,slot_id,lease_token_hash,fencing_generation,state "
            "FROM gpu_capacity_leases WHERE state IN (?,?,?,?) ORDER BY branch_id,logical_case_id,attempt_id",
            GPU_ACTIVE_STATES,
        ).fetchall()
        for row in active:
            key = (
                row["branch_id"], row["logical_case_id"], row["attempt_id"],
                row["lease_token_hash"], row["fencing_generation"],
            )
            process_rows = con.execute(
                "SELECT metadata_json FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? "
                "AND lease_token_hash=? AND fencing_generation=? AND event_type='SCIENTIFIC_PROCESS_BOUND' ORDER BY event_id",
                key,
            ).fetchall()
            process_pids = []
            for event in process_rows:
                try:
                    pid = int(json.loads(event["metadata_json"]).get("pid"))
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
                if pid > 0:
                    process_pids.append(pid)
                    bound_pids.add(pid)
            owners.append({
                "branch_id": row["branch_id"],
                "logical_case_id": row["logical_case_id"],
                "attempt_id": row["attempt_id"],
                "slot_id": row["slot_id"],
                "lease_token_hash": row["lease_token_hash"],
                "fencing_generation": int(row["fencing_generation"]),
                "state": row["state"],
                "bound_process_pids": sorted(set(process_pids)),
            })
    return owners, bound_pids


def capture_external_gpu_capacity_snapshot(db, gpu_resource_name=None):
    """Read the selected NVIDIA device, compute processes, and Shared V3 owners."""
    executable = shutil.which("nvidia-smi")
    if not executable:
        candidate = Path(r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe")
        executable = str(candidate) if candidate.is_file() else None
    if not executable:
        return _gpu_capacity_unavailable("NVIDIA_SMI_NOT_FOUND")
    try:
        device_result = subprocess.run(
            [executable, "--query-gpu=index,name,uuid,utilization.gpu,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, check=False,
        )
        process_result = subprocess.run(
            [executable, "--query-compute-apps=gpu_uuid,pid,process_name,used_memory", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _gpu_capacity_unavailable("NVIDIA_SMI_QUERY_FAILED", {"error": str(exc)})
    if device_result.returncode != 0:
        return _gpu_capacity_unavailable("NVIDIA_SMI_DEVICE_QUERY_FAILED", {"stderr": device_result.stderr.strip()})
    if process_result.returncode != 0:
        return _gpu_capacity_unavailable("NVIDIA_SMI_PROCESS_QUERY_FAILED", {"stderr": process_result.stderr.strip()})
    try:
        raw_devices = _gpu_capacity_csv(device_result.stdout, 7)
        raw_processes = _gpu_capacity_csv(process_result.stdout, 4)
    except ValueError as exc:
        return _gpu_capacity_unavailable(str(exc))
    devices = []
    for index, name, gpu_uuid, utilization, total, used, free in raw_devices:
        try:
            gpu_index = int(index)
        except ValueError:
            return _gpu_capacity_unavailable("NVIDIA_SMI_GPU_INDEX_INVALID")
        devices.append({
            "index": gpu_index,
            "name": name,
            "uuid": gpu_uuid,
            "utilization_gpu_percent": _gpu_capacity_int(utilization),
            "memory_total_mib": _gpu_capacity_int(total),
            "memory_used_mib": _gpu_capacity_int(used),
            "memory_free_mib": _gpu_capacity_int(free),
        })
    requested = "".join(ch for ch in str(gpu_resource_name or "").lower() if ch.isalnum())
    if requested:
        matching_rows = [
            device for device in devices
            if requested in "".join(ch for ch in (device["name"] + device["uuid"]).lower() if ch.isalnum())
            or requested in {str(device["index"]), f"gpu{device['index']}", f"cuda{device['index']}"}
        ]
        if len(matching_rows) == 1:
            selected_rows = matching_rows
            resolution_mode = "EXACT_DEVICE_MATCH"
        elif not matching_rows and len(devices) == 1:
            # Resolve a logical label only when the host exposes one physical device.
            selected_rows = devices
            resolution_mode = "SINGLE_VISIBLE_DEVICE_FOR_LOGICAL_RESOURCE_LABEL"
        else:
            selected_rows = []
            resolution_mode = "RESOURCE_LABEL_UNRESOLVED_OR_AMBIGUOUS"
    elif len(devices) == 1:
        selected_rows = devices
        resolution_mode = "SINGLE_VISIBLE_DEVICE_NO_RESOURCE_LABEL"
    else:
        selected_rows = []
        resolution_mode = "NO_UNIQUE_DEVICE"
    if (len(selected_rows) != 1 or selected_rows[0]["memory_free_mib"] is None
            or selected_rows[0]["memory_used_mib"] is None):
        return _gpu_capacity_unavailable(
            "GPU_DEVICE_SELECTION_OR_MEMORY_UNAVAILABLE",
            {
                "requested_gpu_resource_name": gpu_resource_name,
                "requested_resource_name": gpu_resource_name,
                "visible_devices": devices,
                "resolution_mode": resolution_mode,
            },
        )
    compute_processes = []
    for gpu_uuid, pid, process_name, used_memory in raw_processes:
        try:
            process_pid = int(pid)
        except ValueError:
            return _gpu_capacity_unavailable("NVIDIA_SMI_PROCESS_PID_INVALID")
        compute_processes.append({
            "gpu_uuid": gpu_uuid,
            "pid": process_pid,
            "process_name": process_name,
            "used_memory_mib": _gpu_capacity_int(used_memory),
        })
    try:
        owners, bound_pids = _shared_v3_gpu_owners(db)
    except Exception as exc:
        return _gpu_capacity_unavailable("SHARED_V3_GPU_OWNER_SNAPSHOT_FAILED", {"error": str(exc)})
    selected = selected_rows[0]
    selected_processes = [process for process in compute_processes if process["gpu_uuid"] == selected["uuid"]]
    external = [process for process in selected_processes if process["pid"] not in bound_pids]
    known_process_memory = [process["used_memory_mib"] for process in selected_processes]
    unattributed_memory = (
        max(0, selected["memory_used_mib"] - sum(known_process_memory))
        if all(value is not None for value in known_process_memory) else None
    )
    return {
        "schema": "SHARED_V3_EXTERNAL_GPU_CAPACITY_SNAPSHOT_V1",
        "captured_at_utc": _gpu_capacity_now(),
        "capture_status": "PASS",
        "capture_reason": "GPU_AND_PROCESS_SNAPSHOT_READ",
        "requested_gpu_resource_name": gpu_resource_name,
        "requested_resource_name": gpu_resource_name,
        "resolved_gpu": {"index": selected["index"], "uuid": selected["uuid"], "name": selected["name"]},
        "resolution_mode": resolution_mode,
        "required_free_mib": GPU_REQUIRED_FREE_MIB,
        "validated_baseline_free_mib": GPU_VALIDATED_BASELINE_FREE_MIB,
        "observed_peak_gib": GPU_OBSERVED_PEAK_GIB,
        "selected_gpu": selected,
        "devices": devices,
        "compute_processes": compute_processes,
        "external_compute_processes": external,
        "shared_v3_active_owners": owners,
        "process_attribution_status": "PASS",
        "process_visibility_scope": "NVIDIA_QUERY_COMPUTE_APPS",
        "process_memory_visibility": "PER_PROCESS_MEMORY_MAY_BE_NA_UNDER_WINDOWS_WDDM",
        "unattributed_gpu_memory_mib": unattributed_memory,
    }


def evaluate_external_gpu_capacity(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("capture_status") != "PASS":
        reason = snapshot.get("capture_reason") if isinstance(snapshot, dict) else "SNAPSHOT_MISSING"
        return {
            "status": "WAIT_EXTERNAL_GPU_CAPACITY",
            "reason": reason or "GPU_CAPACITY_SNAPSHOT_UNAVAILABLE",
            "required_free_mib": GPU_REQUIRED_FREE_MIB,
            "observed_free_mib": None,
        }
    device = snapshot.get("selected_gpu") or {}
    free_mib = device.get("memory_free_mib")
    if isinstance(free_mib, bool) or not isinstance(free_mib, int):
        return {
            "status": "WAIT_EXTERNAL_GPU_CAPACITY", "reason": "GPU_FREE_MEMORY_UNAVAILABLE",
            "required_free_mib": GPU_REQUIRED_FREE_MIB, "observed_free_mib": None,
        }
    if free_mib < GPU_REQUIRED_FREE_MIB:
        return {
            "status": "WAIT_EXTERNAL_GPU_CAPACITY", "reason": "GPU_FREE_MEMORY_BELOW_VALIDATED_PEAK",
            "required_free_mib": GPU_REQUIRED_FREE_MIB, "observed_free_mib": free_mib,
        }
    return {
        "status": "PASS", "reason": "GPU_FREE_MEMORY_MEETS_VALIDATED_PEAK",
        "required_free_mib": GPU_REQUIRED_FREE_MIB, "observed_free_mib": free_mib,
    }


def persist_external_gpu_capacity_snapshot(
    attempt_root, *, branch_id, case_id, attempt_id, lease, phase, snapshot, event_paths=None,
):
    """Durably append a fenced snapshot and return the hash linked from the launch claim."""
    from pathlib import Path
    from shared_fdtd.engine.event_log import append_event

    paths = [Path(path) for path in (event_paths or [Path(attempt_root) / "events.jsonl"])]
    if not paths:
        raise ValueError("GPU_CAPACITY_EVENT_PATH_REQUIRED")
    unique_paths = []
    for path in paths:
        if path not in unique_paths:
            unique_paths.append(path)
    decision = evaluate_external_gpu_capacity(snapshot)
    record = {
        "schema": "SHARED_V3_GPU_CAPACITY_SNAPSHOT_EVENT_V1",
        "snapshot_id": uuid.uuid4().hex,
        "phase": str(phase),
        "status": decision["status"],
        "reason": decision["reason"],
        "required_free_mib": decision["required_free_mib"],
        "observed_free_mib": decision["observed_free_mib"],
        "branch_id": branch_id,
        "case_id": case_id,
        "attempt_id": attempt_id,
        "slot_id": lease.slot_id,
        "lease_token_hash": lease.token_hash,
        "fencing_generation": int(lease.fencing_generation),
        "snapshot": snapshot,
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    snapshot_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    event_payload = {**record, "snapshot_sha256": snapshot_sha256}
    persisted_paths = []
    for path in unique_paths:
        event = append_event(path, "GPU_CAPACITY_SNAPSHOT", **event_payload)
        if event.get("snapshot_id") != record["snapshot_id"] or event.get("snapshot_sha256") != snapshot_sha256:
            raise RuntimeError("GPU_CAPACITY_SNAPSHOT_EVENT_REF_MISMATCH")
        persisted_paths.append(str(path))
    return {
        "status": decision["status"],
        "reason": decision["reason"],
        "event_schema": "SHARED_V3_GPU_CAPACITY_SNAPSHOT_EVENT_V1",
        "snapshot_id": record["snapshot_id"],
        "snapshot_sha256": snapshot_sha256,
        "required_free_mib": decision["required_free_mib"],
        "observed_free_mib": decision["observed_free_mib"],
        "phase": str(phase),
        "event_paths": persisted_paths,
    }
