from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import sys

try:
    import closeout_d6_m05_orphan_v1 as _core
except ImportError:
    from . import closeout_d6_m05_orphan_v1 as _core

CASE_ID = "K6GDP2_DEV_G023"
ATTEMPT_ID = "attempt_001"
RUN_ID = "K6V2_G023_20261006T144241Z_0a0cb192"
SCHEMA = "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1"
PRODUCTION_ROOT = pathlib.Path(r"D:\apcd_runtime\gpu_production_runner_v1")
CONTROL_DB = pathlib.Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
COUPLING_LEDGER = pathlib.Path(
    r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\QUEUE_EXECUTION_LEDGER_V1.json"
)
EXPECTED_LEDGER_SHA256 = "79da35c8c1fa129527c0828b954dfbcb1b9541e2fc236223c02bd47266bf05f9"
EXPECTED_ENTRY_COUNT = 35
EXPECTED_SEQUENCE_INDEX = 35

for _name, _value in (("CASE_ID", CASE_ID), ("ATTEMPT_ID", ATTEMPT_ID),
                       ("RUN_ID", RUN_ID), ("SCHEMA", SCHEMA)):
    setattr(_core, _name, _value)


class CloseoutBlocked(RuntimeError):
    pass


def _run_dir(root):
    return pathlib.Path(root) / "runs" / CASE_ID / ATTEMPT_ID / RUN_ID


def _truth_probe(run_dir, ledger_path):
    run_dir = pathlib.Path(run_dir)
    ledger_path = pathlib.Path(ledger_path)
    ledger_raw = ledger_path.read_bytes()
    ledger_sha = hashlib.sha256(ledger_raw).hexdigest()
    if ledger_sha != EXPECTED_LEDGER_SHA256:
        raise CloseoutBlocked("COUPLING_LEDGER_SHA256_CHANGED")
    try:
        ledger = json.loads(ledger_raw.decode("utf-8-sig"))
    except Exception as exc:
        raise CloseoutBlocked("COUPLING_LEDGER_INVALID") from exc
    records = ledger.get("case_records")
    if not isinstance(records, dict):
        raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_SCHEMA_INVALID")
    row = records.get(CASE_ID)
    if not isinstance(row, dict):
        raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_MISSING")
    current = ledger.get("current_case") or {}
    if (ledger.get("entered_count") != EXPECTED_ENTRY_COUNT
            or ledger.get("automatic_replay_count") != 0):
        raise CloseoutBlocked("COUPLING_ENTRY_OR_REPLAY_COUNT_MISMATCH")
    if (current.get("case_id") != CASE_ID or current.get("run_id") != RUN_ID
            or current.get("phase") != "RUN_ONE_IN_PROGRESS"
            or current.get("sequence_index") != EXPECTED_SEQUENCE_INDEX):
        raise CloseoutBlocked("COUPLING_LEDGER_CURRENT_CASE_MISMATCH")
    if (row.get("case_id", CASE_ID) != CASE_ID or row.get("attempt_id") != ATTEMPT_ID
            or row.get("run_id") != RUN_ID or row.get("phase") != "RUN_ONE_IN_PROGRESS"
            or row.get("sequence_index") != EXPECTED_SEQUENCE_INDEX):
        raise CloseoutBlocked("COUPLING_LEDGER_CASE_RECORD_MISMATCH")
    if CASE_ID in ledger.get("truth_valid_case_ids", []) or CASE_ID in ledger.get("labels_valid_case_ids", []):
        raise CloseoutBlocked("COUPLING_TARGET_ALREADY_HAS_VALID_TRUTH")
    if any(row.get(k) for k in ("ingest_truth_path", "truth_path", "ingest_result_path", "label_path")):
        raise CloseoutBlocked("COUPLING_TARGET_HAS_INGEST_ARTIFACT")
    validation_path = run_dir / "validation.json"
    hashes_path = run_dir / "hashes.json"
    try:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CloseoutBlocked("RUN_VALIDATION_OR_HASHES_UNREADABLE") from exc
    if validation != {"state": "PENDING"} or hashes != {"state": "PENDING"}:
        raise CloseoutBlocked("RUN_VALIDATION_OR_HASHES_NOT_PENDING")
    h5_path = run_dir / "run" / "run_output.h5"
    try:
        import h5py
        with h5py.File(h5_path, "r") as h5:
            datasets = []
            h5.visititems(lambda name, obj: datasets.append(name) if isinstance(obj, h5py.Dataset) else None)
    except Exception as exc:
        raise CloseoutBlocked("POSTENTRY_H5_TRUTH_INSPECTION_FAILED") from exc
    noncoords = [p for p in datasets if p.rsplit("/", 1)[-1].lower() not in {"x", "y", "z"}]
    if noncoords:
        raise CloseoutBlocked("POSTENTRY_H5_CONTAINS_NON_COORDINATE_RESULTS")
    candidates = []
    closeout_name = _core.CLOSEOUT_DIRNAME
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.relative_to(run_dir).parts[0] == closeout_name:
            continue
        if path == h5_path or path.suffix.lower() == ".fsp":
            continue
        lower = path.name.lower()
        if "truth" in lower or "scientific_valid" in lower or path.suffix.lower() == ".npz":
            candidates.append(str(path.relative_to(run_dir)))
    if candidates:
        raise CloseoutBlocked("POSTENTRY_TRUTH_CANDIDATE_ARTIFACT_PRESENT")
    return {
        "truth_available": False,
        "reason": "VALIDATION_AND_HASHES_PENDING;H5_COORDINATES_ONLY;COUPLING_EXCLUDES_TARGET",
        "validation_state": "PENDING", "hashes_state": "PENDING",
        "h5_path": str(h5_path), "h5_sha256": _core._sha(h5_path),
        "h5_dataset_paths": sorted(datasets), "non_coordinate_dataset_paths": noncoords,
        "coupling_ledger_sha256": ledger_sha,
        "truth_valid_case": False, "labels_valid_case": False,
        "candidate_truth_artifacts": candidates,
        "expected_entered_count": EXPECTED_ENTRY_COUNT,
        "sequence_index": EXPECTED_SEQUENCE_INDEX,
    }


def closeout_g023_production():
    root = PRODUCTION_ROOT.resolve()
    if root != pathlib.Path(_core._runner.PRODUCTION_RUNNER_ROOT).resolve():
        raise CloseoutBlocked("PINNED_RUNNER_ROOT_MISMATCH")
    result = _core._closeout_one_run(
        root, CONTROL_DB, COUPLING_LEDGER,
        process_probe=_core._process_probe,
        hold_probe=_core._hold_probe,
        truth_probe=_truth_probe,
        authority_reference="USER_PROJECT_OWNER_APPROVED_RECOVERY;G023_FAILED_POSTENTRY_NO_TRUTH;ENTRY_UNKNOWN_NOT_REPLAYED",
    )
    closeout_dir = _core._closeout_dir(root)
    claim = _core._read_json(closeout_dir / "claim.json")
    disposition_path = closeout_dir / "disposition.json"
    journal_path = closeout_dir / "journal.json"
    receipt_path = closeout_dir / "receipt.json"
    inventory = claim["input_hashes"]["run_inventory"]
    receipt_body = {
        "schema": SCHEMA + "_RECEIPT",
        "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": RUN_ID,
        "result": "CLOSED", "disposition": "FAILED_POSTENTRY_NO_TRUTH",
        "solver_entry_count": 1, "solver_invocations": 1, "automatic_replay_count": 0,
        "historical_physical_entry_interpretation": "ONE_ENTRY_RECORDED;NO_REPLAY;NO_SECOND_ENTRY",
        "truth_available": False, "scientific_valid": False, "training_admitted": False,
        "recovery_fence_id": claim["recovery_fence_id"],
        "authority_reference": claim.get("authority_reference"),
        "coupling_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "input_run_artifacts_sha256": inventory,
        "disposition_path": str(disposition_path), "disposition_sha256": _core._sha(disposition_path),
        "journal_path": str(journal_path), "journal_sha256": _core._sha(journal_path),
        "status_sha256": _core._sha(_core._paths(root)["status"]),
        "registry_sha256": _core._sha(_core._paths(root)["registry"]),
        "active_marker_archive_sha256": _core._sha(closeout_dir / "released_active_run.json"),
        "runner_lock_archive_sha256": _core._sha(closeout_dir / "released_runner.lock"),
        "created_utc": claim["created_utc"],
    }
    receipt = dict(receipt_body, receipt_sha256=_core._sha_bytes(_core._canonical(receipt_body)))
    if receipt_path.exists():
        existing = _core._read_json(receipt_path)
        if existing != receipt:
            old_body = dict(existing)
            old_self_hash = old_body.pop("receipt_sha256", None)
            expected_body = dict(receipt)
            expected_self_hash = expected_body.pop("receipt_sha256", None)
            if old_self_hash != _core._sha_bytes(_core._canonical(old_body)):
                raise CloseoutBlocked("G023_EXISTING_RECEIPT_SELF_HASH_INVALID")
            for key in ("status_sha256", "registry_sha256"):
                if old_body.get(key) is None:
                    old_body[key] = expected_body.get(key)
            if old_body != expected_body:
                raise CloseoutBlocked("G023_CLOSEOUT_RECEIPT_CONFLICT")
            if expected_self_hash != _core._sha_bytes(_core._canonical(expected_body)):
                raise CloseoutBlocked("G023_NEW_RECEIPT_SELF_HASH_INVALID")
            _core._write_json(receipt_path, receipt)
    else:
        _core._write_json(receipt_path, receipt)
    result["receipt_path"] = str(receipt_path)
    result["receipt_sha256"] = _core._sha(receipt_path)
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(closeout_g023_production(), sort_keys=True))
    except (CloseoutBlocked, _core.CloseoutBlocked) as exc:
        print(json.dumps({"result": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
