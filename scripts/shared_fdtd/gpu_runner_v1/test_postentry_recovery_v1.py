from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import postentry_recovery_v1 as recovery
import runner


def _identity():
    return {"case_id": "K6GDP2_DEV_G025", "attempt_id": "attempt_001",
            "run_id": "K6V2_G025_20261008T140327Z_454d6858"}


def test_checkpoint_requires_exactly_one_entered_registry_row():
    identity = _identity()
    request_id = "28c992f00bb8b032ecf06f4d8e8dc431"
    manifest = dict(identity)
    status = dict(identity, state="SOLVER_ENTERED", solver_entered=True, solver_invocations=1)
    request = dict(request_id=request_id, identity=identity, request_sha256="a" * 64)
    claim = dict(request_id=request_id, request_sha256="a" * 64, pid=44352)
    row = dict(identity, state="SOLVER_ENTERED")
    assert recovery.validate_postentry_checkpoint(
        manifest, status, [row], request, claim, **identity, request_id=request_id) == row
    try:
        recovery.validate_postentry_checkpoint(
            manifest, status, [row, dict(row)], request, claim, **identity, request_id=request_id)
    except recovery.RecoveryError as exc:
        assert str(exc) == "REGISTRY_TARGET_NOT_UNIQUE_ENTERED"
    else:
        raise AssertionError("duplicate registry row accepted")


def test_checkpoint_rejects_zero_entry_and_identity_mismatch():
    identity = _identity()
    request_id = "28c992f00bb8b032ecf06f4d8e8dc431"
    request = dict(request_id=request_id, identity=identity, request_sha256="a" * 64)
    claim = dict(request_id=request_id, request_sha256="a" * 64, pid=44352)
    row = dict(identity, state="SOLVER_ENTERED")
    status = dict(identity, state="SOLVER_ENTERED", solver_entered=True, solver_invocations=0)
    try:
        recovery.validate_postentry_checkpoint(
            dict(identity), status, [row], request, claim, **identity, request_id=request_id)
    except recovery.RecoveryError as exc:
        assert str(exc) == "TARGET_ENTRY_COUNT_NOT_ONE"
    else:
        raise AssertionError("zero-entry state accepted")


def test_control_marker_archive_preserves_bytes_and_identity(tmp_path):
    identity = _identity()
    request_id = "28c992f00bb8b032ecf06f4d8e8dc431"
    payloads = {
        ".runner.lock": dict(identity, pid=44352),
        "active_run.json": dict(identity, pid=44352),
        "scheduler_worker_v1.lock": dict(request_id=request_id, pid=44352),
    }
    hashes = {}
    for name, value in payloads.items():
        path = tmp_path / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        hashes[name] = recovery.sha_file(path)
    archived = recovery._archive_markers(
        tmp_path, tmp_path / "archive", hashes, case_id=identity["case_id"],
        attempt_id=identity["attempt_id"], run_id=identity["run_id"],
        request_id=request_id, worker_pid=44352)
    assert set(archived) == set(payloads)
    for name in payloads:
        assert not (tmp_path / name).exists()
        assert recovery.sha_file(archived[name]["path"]) == hashes[name]


def test_control_marker_hash_mismatch_does_not_move_source(tmp_path):
    identity = _identity()
    request_id = "28c992f00bb8b032ecf06f4d8e8dc431"
    for name, value in (
        (".runner.lock", dict(identity, pid=44352)),
        ("active_run.json", dict(identity, pid=44352)),
        ("scheduler_worker_v1.lock", dict(request_id=request_id, pid=44352)),
    ):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    hashes = {name: recovery.sha_file(tmp_path / name) for name in
              (".runner.lock", "active_run.json", "scheduler_worker_v1.lock")}
    hashes[".runner.lock"] = "0" * 64
    try:
        recovery._archive_markers(
            tmp_path, tmp_path / "archive", hashes, case_id=identity["case_id"],
            attempt_id=identity["attempt_id"], run_id=identity["run_id"],
            request_id=request_id, worker_pid=44352)
    except recovery.RecoveryError as exc:
        assert str(exc) == "CONTROL_MARKER_HASH_CHANGED:.runner.lock"
    else:
        raise AssertionError("unmatched control marker archived")
    assert (tmp_path / ".runner.lock").is_file()


def test_runner_persists_original_exception_and_phase(tmp_path):
    try:
        raise RuntimeError("fresh load exploded")
    except RuntimeError as exc:
        saved = runner._persist_failure_diagnostic(
            tmp_path, {"state": "SOLVER_RETURNED", "solver_invocations": 1},
            "FRESH_LOAD_VALIDATION", True, exc)
    path = Path(saved["path"])
    record = json.loads(path.read_text(encoding="utf-8"))
    assert saved["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert record["exception_type"] == "RuntimeError"
    assert record["exception"] == "fresh load exploded"
    assert record["phase"] == "FRESH_LOAD_VALIDATION"
    assert "fresh load exploded" in record["traceback"]
    assert record["solver_entered"] is True


def test_copy_file_durable_uses_writable_sync_handle(tmp_path):
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy" / "source.bin"
    source.write_bytes(b"preserved FSP bytes")
    recovery._copy_file_durable(source, destination)
    assert destination.read_bytes() == source.read_bytes()
    assert recovery.sha_file(destination) == recovery.sha_file(source)
