from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from shared_fdtd.engine.persistence import atomic_json, sha256_file

RUNTIME_PATCH_VERSION = "3.0.3-durable-postsolver-finisher"


def _file_record(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return {
        "path": str(p),
        "exists": p.is_file(),
        "sha256": sha256_file(p) if p.is_file() else None,
        "size_bytes": p.stat().st_size if p.is_file() else None,
    }


def write_durable_attempt_state(
    path: str | Path,
    *,
    cfg: Mapping[str, Any],
    lease: Any,
    setup_path: str | Path | None = None,
    runtime_fsp: str | Path | None = None,
    native_target: str | Path | None = None,
    post_target: str | Path | None = None,
    raw_target: str | Path | None = None,
    logs: list[str | Path] | None = None,
    adapter_identity: str = "UNSPECIFIED",
    adapter_hash: str | None = None,
    persistence_preflight: Mapping[str, Any] | None = None,
    expected_process_identity: Mapping[str, Any] | None = None,
    scientific_contract_hash: str | None = None,
    solver_entry_timestamp: str | None = None,
    canonical_state: str | None = None,
) -> dict[str, Any]:
    """Write the reconstructable attempt contract before scientific entry."""
    data = {
        "state_schema": "APCD_SHARED_DURABLE_ATTEMPT_STATE_V1",
        "runtime_patch_version": RUNTIME_PATCH_VERSION,
        "owner_branch": cfg["branch"],
        "logical_case_id": cfg["case"],
        "attempt_id": cfg["attempt"],
        "slot_id": lease.slot_id,
        "lease_token_hash": lease.token_hash,
        "fencing_generation": int(lease.fencing_generation),
        "scientific_contract_hash": scientific_contract_hash or cfg.get("physical_contract_hash"),
        "adapter_identity": adapter_identity,
        "adapter_hash": adapter_hash,
        "setup": _file_record(setup_path) if setup_path else None,
        "runtime_fsp": str(runtime_fsp) if runtime_fsp else None,
        "native_target": str(native_target) if native_target else None,
        "post_target": str(post_target) if post_target else None,
        "raw_target": str(raw_target) if raw_target else None,
        "logs": [str(x) for x in (logs or [])],
        "solver_entry_timestamp_utc": solver_entry_timestamp,
        "scientific_invocation_count": int(cfg.get("scientific_invocation_count", 0)),
        "expected_process_identity": dict(expected_process_identity or {}),
        "persistence_preflight": dict(persistence_preflight or {}),
        "replay": 0,
        "solver_runs": int(cfg.get("scientific_invocation_count", 0)),
        "canonical_state": canonical_state or cfg.get("canonical_state", "SETUP_READY"),
    }
    atomic_json(path, data)
    return data


def read_durable_attempt_state(path: str | Path) -> dict[str, Any]:
    import json

    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    required = ("owner_branch", "logical_case_id", "attempt_id", "slot_id", "lease_token_hash", "fencing_generation")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError("durable attempt state missing: " + ",".join(missing))
    return data
