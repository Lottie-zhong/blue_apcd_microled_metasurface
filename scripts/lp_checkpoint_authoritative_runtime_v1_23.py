"""Checkpoint-authoritative LP V1.22 runtime.

This module intentionally imports neither lumapi nor any legacy runner.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Protocol

SCHEMA = "LP_ML_SCHEMA_V1.23"
VALIDATOR_ID = "LP_V122_CHECKPOINT_AUTHORITATIVE_POST_SOLVER_ACCEPTANCE_V1"
VALIDATOR_VERSION = "V1"
REGISTRATION_MODE = "CHECKPOINT_AUTHORITATIVE_ATOMIC_REGISTRATION"
EVENT_MODE = "APPEND_ONLY_NDJSON"
LOCK_MODE = "O_EXCL_SINGLE_WRITER"
SERIALIZER = "TEMP_FLUSH_FSYNC_ATOMIC_REPLACE"
FORBIDDEN = "LEGACY_VALIDATOR_FORBIDDEN_FOR_LP_ML_SCHEMA_V1_22"
WEIGHTED_G0_VERSION = "LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"
NORMALIZATION_VERSION = "LP_WEIGHTED_G0_SQRT_T_NORM_V1"


class PhysicsBackend(Protocol):
    calls: list[str]
    def open_session(self) -> None: ...
    def build_geometry(self, spec: dict[str, Any]) -> None: ...
    def configure_source_boundaries_monitor(self, spec: dict[str, Any], polarization: str) -> None: ...
    def run_solver(self) -> None: ...
    def extract_weighted_g0_observables(self) -> dict[str, Any]: ...
    def close_session(self) -> None: ...


def sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_bytes(path: Path, data: bytes, interrupt: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            if interrupt == "before_flush":
                raise RuntimeError("TEST_INTERRUPT_BEFORE_FLUSH")
            handle.flush()
            os.fsync(handle.fileno())
        if interrupt == "before_replace":
            raise RuntimeError("TEST_INTERRUPT_BEFORE_REPLACE")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_json(path: Path, data: Any, interrupt: str | None = None) -> None:
    atomic_bytes(path, json.dumps(data, sort_keys=True, indent=2, allow_nan=False).encode("utf8"), interrupt)


def write_csv(path: Path, rows: list[dict[str, Any]], interrupt: str | None = None) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / "rows.csv"
        with work.open("w", encoding="utf8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        atomic_bytes(path, work.read_bytes(), interrupt)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf8", newline="") as handle:
        return list(csv.DictReader(handle))


def append_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf8", newline="") as handle:
        handle.write(json.dumps({"event": event, **fields}, sort_keys=True, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def legacy_forbidden(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError(FORBIDDEN)


def _finite(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite(v) for v in value)
    return not isinstance(value, float) or math.isfinite(value)


def validate_attestation(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    required = (
        "git_head", "runner", "callback", "validator", "schema",
        "registration_mode", "event_log_mode", "lock_mode", "serializer", "source_hashes",
    )
    for key in required:
        if key == "git_head" and expected.get(key) == "COMMIT_BOUND_AT_RUNTIME":
            continue
        if actual.get(key) != expected.get(key):
            raise RuntimeError(f"ATTESTATION_IDENTITY_MISMATCH:{key}")
    if actual.get("legacy_runtime_gate_allowed") or actual.get("legacy_line557_allowed"):
        raise RuntimeError(FORBIDDEN)


class ExecutionLock:
    def __init__(self, path: Path, identity: dict[str, Any]):
        self.path = path
        self.identity = identity
        self.owned = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "start_time": time.time(),
            "command_line": sys.argv,
            **self.identity,
        }
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError("ACTIVE_EXECUTION_LOCK_PRESENT") from exc
        with os.fdopen(fd, "w", encoding="utf8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        self.owned = True

    def release(self) -> None:
        if self.owned:
            self.path.unlink(missing_ok=True)
            self.owned = False


def archive_stale_lock(path: Path, lineage_dir: Path, reason: str) -> dict[str, Any]:
    original_sha = sha256(path)
    lineage_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(lineage_dir.glob(path.name + ".*.json"))
    if existing:
        return json.loads(existing[0].read_text(encoding="utf8"))
    archive = lineage_dir / f"{path.name}.{original_sha[:16]}.lock"
    os.replace(path, archive)
    record = {
        "status": "PASS",
        "original_path": str(path),
        "archive_path": str(archive),
        "original_sha256": original_sha,
        "reason": reason,
    }
    atomic_json(lineage_dir / f"{path.name}.{original_sha[:16]}.json", record)
    return record


def validate_checkpoint(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError("CHECKPOINT_MISSING")
    checkpoint = json.loads(path.read_text(encoding="utf8"))
    required = (
        "candidate_id", "input_basis", "wavelength_nm", "exact_geometry_hash",
        "physics_configuration_hash", "weighted_G0_version", "normalization_version",
        "weighted_G0_Ex", "weighted_G0_Ey", "source_T", "normalization_scale",
        "material_hash", "source_hash", "boundary_hash", "monitor_hash", "reference_plane_nm",
    )
    missing = [key for key in required if key not in checkpoint]
    if missing:
        raise RuntimeError("CHECKPOINT_REQUIRED_FIELDS_MISSING:" + ",".join(missing))
    for key in (
        "candidate_id", "input_basis", "wavelength_nm", "exact_geometry_hash",
        "physics_configuration_hash", "weighted_G0_version", "normalization_version",
    ):
        expected_key = "input_polarization" if key == "input_basis" else key
        if str(checkpoint[key]) != str(expected[expected_key]):
            raise RuntimeError(f"CHECKPOINT_IDENTITY_MISMATCH:{key}")
    if not _finite(checkpoint):
        raise RuntimeError("CHECKPOINT_NONFINITE")
    for key in checkpoint:
        if key.startswith("predicted_") or key.startswith("model_prediction"):
            raise RuntimeError("PREDICTION_CONTAMINATION_FORBIDDEN")
    for field in ("weighted_G0_Ex", "weighted_G0_Ey"):
        if set(checkpoint[field]) != {"real", "imag"}:
            raise RuntimeError("COMPLEX_FIELD_INCOMPLETE:" + field)
    return checkpoint


def formal_subrun_key(expected: dict[str, Any]) -> str:
    fields = (
        "candidate_id", "input_polarization", "wavelength_nm", "exact_geometry_hash",
        "physics_configuration_hash", "weighted_G0_version", "normalization_version",
        "source_plan_sha256",
    )
    return "|".join(str(expected[field]) for field in fields)


def post_solver_acceptance(
    checkpoint_path: Path,
    expected: dict[str, Any],
    formal_csv: Path,
    event_log: Path,
) -> dict[str, Any]:
    """Sole V1.22 post-solver registration callback."""
    append_event(event_log, "POST_SOLVER_CALLBACK_RECEIVED", candidate_id=expected["candidate_id"])
    checkpoint = validate_checkpoint(checkpoint_path, expected)
    checkpoint_sha = sha256(checkpoint_path)
    key = formal_subrun_key(expected)
    row = {
        **expected,
        "formal_subrun_key": key,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "weighted_G0_Ex": json.dumps(checkpoint["weighted_G0_Ex"], sort_keys=True),
        "weighted_G0_Ey": json.dumps(checkpoint["weighted_G0_Ey"], sort_keys=True),
        "source_T": checkpoint["source_T"],
        "normalization_scale": checkpoint["normalization_scale"],
        "validator_id": VALIDATOR_ID,
        "quality_status": "PASS",
    }
    rows = read_csv(formal_csv)
    matches = [existing for existing in rows if existing.get("formal_subrun_key") == key]
    if matches:
        if len(matches) != 1 or matches[0].get("checkpoint_sha256") != checkpoint_sha:
            raise RuntimeError("FORMAL_SUBRUN_KEY_CONFLICT")
    else:
        write_csv(formal_csv, rows + [row])
    reloaded = [existing for existing in read_csv(formal_csv) if existing.get("formal_subrun_key") == key]
    if len(reloaded) != 1:
        raise RuntimeError("EXACT_ONE_ROW_ASSERTION_FAILED")
    if reloaded[0]["checkpoint_sha256"] != sha256(checkpoint_path):
        raise RuntimeError("FORMAL_ROW_CHECKSUM_RELOAD_FAILED")
    append_event(event_log, "ACCEPTED", candidate_id=expected["candidate_id"], formal_subrun_key=key)
    return {"status": "PASS", "formal_subrun_key": key, "row": reloaded[0]}
