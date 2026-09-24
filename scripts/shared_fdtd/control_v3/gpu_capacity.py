from __future__ import annotations

import json
from typing import Any

from .db import utc_now

GPU_ACTIVE_STATES = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")


def ensure_gpu_capacity_tables(con, default_cap: int = 1) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS backend_capacity (
          backend_type TEXT PRIMARY KEY,
          physical_cap INTEGER NOT NULL CHECK(physical_cap BETWEEN 1 AND 3),
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS gpu_capacity_leases (
          capacity_lease_id INTEGER PRIMARY KEY AUTOINCREMENT,
          branch_id TEXT NOT NULL,
          logical_case_id TEXT NOT NULL,
          attempt_id TEXT NOT NULL,
          slot_id TEXT NOT NULL,
          lease_token_hash TEXT NOT NULL,
          fencing_generation INTEGER NOT NULL,
          state TEXT NOT NULL CHECK(state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED','RELEASED')),
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          released_at TEXT,
          UNIQUE(branch_id, logical_case_id, attempt_id)
        );
        CREATE INDEX IF NOT EXISTS idx_gpu_capacity_leases_active
          ON gpu_capacity_leases(state);
        """
    )
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
