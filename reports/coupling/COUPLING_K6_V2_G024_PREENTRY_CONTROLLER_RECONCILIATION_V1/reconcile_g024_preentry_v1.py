#!/usr/bin/env python3
"""One-time, G024-only pre-entry reconciliation. Never starts Runner or solver."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CASE_ID = "K6GDP2_DEV_G024"
ATTEMPT_ID = "attempt_001"
OLD_RUN_ID = "K6V2_G024_20261007T110238Z_9bdcaaf0"
REQUEST_ID = "32155c227f489da2ccf673266720bbca"
CONTROLLER_REQUEST_ID = "f0aeb35290a77db5c05c0346f1a40f81"
QUEUE_ID = "K6V2V128REMAINING20261007105811Z"
CONTROLLER_RUN_ID = "K6V2SERIAL20261007T105811Z_ce8009d2"
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
QUEUE_REPORT = ROOT / "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1"
RUNNER_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
RUNNER_WORKTREE = Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
REQUEST_DIR = RUNNER_ROOT / "requests/scheduled_run_one_v1" / REQUEST_ID
CONTROLLER_DIR = RUNNER_ROOT / "requests/scheduled_queue_controller_v1" / CONTROLLER_REQUEST_ID
REQUEST_PATH = REQUEST_DIR / "request.json"
RESULT_PATH = REQUEST_DIR / "result.json"
CLAIM_PATH = REQUEST_DIR / "worker_claim.json"
CONTROLLER_MANIFEST = CONTROLLER_DIR / "controller_manifest.json"
CONTROLLER_START_CLAIM = CONTROLLER_DIR / "start_claim.json"
CONTROLLER_STATUS = QUEUE_REPORT / f"CONTROLLER_STATUS_{CONTROLLER_RUN_ID}.json"
QUEUE_SCRIPT = ROOT / "scripts/coupling_ml/k6_v2_pipeline/serial_queue.py"
QUEUE_MANIFEST = QUEUE_REPORT / "BATCH_QUEUE_MANIFEST_V1.json"
LEDGER = QUEUE_REPORT / "QUEUE_EXECUTION_LEDGER_V1.json"
BATCH = QUEUE_REPORT / "BATCH_PREPARATION_STATUS_V1.json"
ENVELOPE = QUEUE_REPORT / f"RUN_ENVELOPE_{OLD_RUN_ID}.json"
RUN_LOG = QUEUE_REPORT / f"RUNNER_CLI_OUTPUT_{OLD_RUN_ID}.log"
PREFLIGHT = QUEUE_REPORT / "FORMAL_PREFLIGHT_RESULT_K6GDP2_DEV_G024_A78274BE_0c0478423f6b.json"
LOAD_READBACK = QUEUE_REPORT / "FRESH_LOAD_READBACK_K6GDP2_DEV_G024_A78274BE_V1.json"
REGISTRY = RUNNER_ROOT / "registry.json"
RUN_ROOT = RUNNER_ROOT / "runs"
LABEL_NPZ = QUEUE_REPORT / f"INGESTED_TRUTH_{CASE_ID}_V1.npz"
INGEST_RESULT = QUEUE_REPORT / f"INGEST_RESULT_{CASE_ID}_V1.json"
RESUME_RECEIPT = CONTROLLER_STATUS.with_name("resume_receipt_v1.json")

PINNED_RAW_SHA256 = {
    str(REQUEST_PATH): "33ece245acbfd7e5e203cb7e18933ec7df5b32cfa2881180adbbe99f88d03a21",
    str(RESULT_PATH): "21194ce49f6d7d15187c73f7d762cd024520b943eb47ccf83ed3076781cd17a9",
    str(CLAIM_PATH): "95195d1d04a208ef2b15e5d84e232c7e6ad819037898db56d7a3ceebd912aff5",
    str(ENVELOPE): "d90ca7cfa0af43649862ff9b41ac5f68bab9d65c1a63898ff00f6847903a6cd5",
    str(RUN_LOG): "4fb05209de2e51d3e2846f308bb8297b3450dd4eedde1baa343cea9dc0668d1a",
    str(CONTROLLER_MANIFEST): "f0aeb35290a77db5c05c0346f1a40f81a11f6fd9dab1a828a2ce7ab41f998edd",
    str(QUEUE_MANIFEST): "fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7",
    str(QUEUE_SCRIPT): "5ede3c2b2d85c225f73041a5d9332397bfa6fa03d91c39c8bba40089131d5ae5",
    str(LEDGER): "8f4c55b4948b236b493c2c5165452f63f69d2bc0ac3757ad100b6fabde9188c5",
    str(BATCH): "44b59f8fa57e1f7f7f487b584af2748251bc99ae1c5b1a857cbe50e3a7c3cec1",
    str(CONTROLLER_STATUS): "7ecf1f425c8eddd3370dbf60f2ad27a23537c996a1a94a862e3a40453453d539",
}

class ReconcileError(RuntimeError):
    pass

def need(condition: bool, code: str) -> None:
    if not condition:
        raise ReconcileError(code)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def read_json(path: Path) -> tuple[dict, bytes]:
    need(path.is_file() and not path.is_symlink(), "JSON_FILE_MISSING_OR_UNSAFE:" + str(path))
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise ReconcileError("JSON_INVALID:" + str(path)) from exc
    need(isinstance(value, dict), "JSON_ROOT_NOT_OBJECT:" + str(path))
    return value, raw

def verify_worker_chain(request: dict, result: dict, claim: dict) -> dict:
    request_body = dict(request)
    saved_request_sha = request_body.pop("request_sha256", None)
    need(request.get("schema") == "APCD_GPU_RUNNER_V1_SCHEDULED_REQUEST_V1",
         "REQUEST_SCHEMA_INVALID")
    need(saved_request_sha == canonical_sha256(request_body), "REQUEST_CANONICAL_SHA_INVALID")
    need(request.get("request_id") == REQUEST_ID, "REQUEST_ID_INVALID")
    identity = request.get("identity")
    need(identity == {"case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "run_id": OLD_RUN_ID},
         "REQUEST_IDENTITY_INVALID")
    need(request.get("manifest_sha256") == file_sha256(ENVELOPE), "REQUEST_ENVELOPE_SHA_INVALID")
    need(Path(request.get("manifest_path", "")).resolve() == ENVELOPE.resolve(),
         "REQUEST_ENVELOPE_PATH_INVALID")

    claim_sha = canonical_sha256(claim)
    need(claim.get("schema") == "APCD_GPU_RUNNER_V1_SCHEDULED_WORKER_CLAIM_V1",
         "WORKER_CLAIM_SCHEMA_INVALID")
    need(claim.get("request_id") == REQUEST_ID and claim.get("request_sha256") == saved_request_sha,
         "WORKER_CLAIM_REQUEST_BINDING_INVALID")
    need(claim.get("task_name") == r"\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER",
         "WORKER_CLAIM_TASK_INVALID")

    result_body = dict(result)
    saved_result_sha = result_body.pop("result_sha256", None)
    need(result.get("schema") == "APCD_GPU_RUNNER_V1_SCHEDULED_RESULT_V1",
         "RESULT_SCHEMA_INVALID")
    need(saved_result_sha == canonical_sha256(result_body), "RESULT_CANONICAL_SHA_INVALID")
    need(result.get("request_id") == REQUEST_ID
         and result.get("request_sha256") == saved_request_sha
         and result.get("claim_sha256") == claim_sha,
         "RESULT_CHAIN_BINDING_INVALID")
    need(result.get("worker_pid") == claim.get("pid"), "RESULT_WORKER_PID_INVALID")
    need(result.get("exit_code") == 2 and result.get("error") == "GPU_RESOURCE_NAME_REQUIRED"
         and result.get("run_status") is None and result.get("solver_entered") is False,
         "RESULT_NOT_PROVEN_PREENTRY_FAILURE")
    return {
        "request_id": REQUEST_ID,
        "request_canonical_sha256": saved_request_sha,
        "result_canonical_sha256": saved_result_sha,
        "claim_canonical_sha256": claim_sha,
        "worker_pid": claim.get("pid"),
        "failure": result.get("error"),
        "exit_code": result.get("exit_code"),
        "solver_entered": False,
    }

def identity_matches(value: dict, require_run_id: bool = True) -> bool:
    ok = value.get("case_id") == CASE_ID and value.get("attempt_id") == ATTEMPT_ID
    if require_run_id:
        ok = ok and value.get("run_id") == OLD_RUN_ID
    return ok

def _counter_snapshot(ledger: dict) -> dict:
    names = (
        "entered_count", "truth_valid_count", "labels_valid_count",
        "remaining_unentered_count", "automatic_replay_count", "training_fits",
        "p_scale_fits", "confirmation_response_access_count",
    )
    return {name: ledger.get(name) for name in names}

def build_reconciled_snapshots(ledger: dict, batch: dict, status: dict,
                                evidence: dict, timestamp: str) -> tuple[dict, dict, dict]:
    """Pure state transition. G024 remains unentered and attempt_001 remains eligible."""
    l, b, s = copy.deepcopy(ledger), copy.deepcopy(batch), copy.deepcopy(status)
    need(l.get("entered_count") == 35 and l.get("truth_valid_count") == 33
         and l.get("labels_valid_count") == 33 and l.get("remaining_unentered_count") == 93,
         "LEDGER_COUNTS_OUTSIDE_G024_SNAPSHOT")
    need(l.get("automatic_replay_count") == 0 and l.get("training_fits") == 0
         and l.get("p_scale_fits") == 0 and l.get("confirmation_response_access_count") == 0,
         "LEDGER_PROTECTED_COUNTER_NONZERO")
    need(CASE_ID not in l.get("entered_case_ids", [])
         and CASE_ID not in l.get("truth_valid_case_ids", [])
         and CASE_ID not in l.get("labels_valid_case_ids", []),
         "G024_ALREADY_ENTERED_OR_LABELED")
    prior_pointer = l.get("current_case")
    need(isinstance(prior_pointer, dict) and prior_pointer.get("case_id") == CASE_ID
         and prior_pointer.get("phase") == "FAILED_OR_ISOLATED"
         and prior_pointer.get("run_id") == OLD_RUN_ID
         and prior_pointer.get("sequence_index") == 36,
         "LEDGER_CURRENT_POINTER_NOT_G024_FAILURE")
    need(b.get("current_case", {}).get("case_id") == CASE_ID
         and b.get("current_case", {}).get("phase") == "RUN_ONE_IN_PROGRESS"
         and b.get("current_case", {}).get("run_id") == OLD_RUN_ID,
         "BATCH_CURRENT_POINTER_NOT_G024")
    need(s.get("schema") == "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1"
         and s.get("state") == "RUNNING" and s.get("current_case_id") == CASE_ID
         and s.get("request_id") == CONTROLLER_REQUEST_ID
         and s.get("controller_manifest_sha256") == PINNED_RAW_SHA256[str(CONTROLLER_MANIFEST)]
         and s.get("queue_id") == QUEUE_ID
         and s.get("unresolved_runner_request_ids") == []
         and s.get("post_entry_automatic_replays") == 0,
         "CONTROLLER_STATUS_NOT_G024_BOUNDARY")
    need(isinstance(l.get("case_records"), dict), "LEDGER_CASE_RECORDS_INVALID")
    prior_record = l["case_records"].get(CASE_ID)
    need(isinstance(prior_record, dict) and prior_record.get("phase") == "RUN_ONE_IN_PROGRESS"
         and prior_record.get("attempt_id") == ATTEMPT_ID
         and prior_record.get("run_id") == OLD_RUN_ID
         and prior_record.get("case_id", CASE_ID) == CASE_ID
         and prior_record.get("sequence_index") == 36,
         "G024_PRIOR_CASE_RECORD_INVALID")
    failures = [row for row in l.get("failed_or_isolated_cases", [])
                if isinstance(row, dict) and row.get("case_id") == CASE_ID]
    need(len(failures) == 1, "G024_FAILURE_EVENT_NOT_UNIQUE")
    fail_row = failures[0]
    fail_evidence = fail_row.get("evidence")
    need(fail_row.get("phase") == "RUN_ONE" and fail_row.get("sequence_index") == 36
         and isinstance(fail_evidence, dict) and fail_evidence.get("returncode") == 2
         and fail_evidence.get("run_log_sha256") == evidence["run_log_sha256"],
         "G024_FAILURE_EVENT_NOT_BOUND_TO_RUNNER_LOG")
    need(not l.get("isolated_case_ids") or CASE_ID not in l.get("isolated_case_ids", []),
         "G024_ALREADY_ISOLATED")

    before_counts = _counter_snapshot(l)
    fail_evidence["preentry_reconciliation"] = {
        "schema": "COUPLING_K6_V2_G024_PREENTRY_RECONCILIATION_EVIDENCE_V1",
        "disposition": "PREENTRY_FAILURE_NO_SOLVER_ENTRY",
        "case_id": CASE_ID,
        "attempt_id": ATTEMPT_ID,
        "failed_run_id": OLD_RUN_ID,
        "sequence_index": 36,
        "solver_entered": False,
        "entry_consumed": False,
        "automatic_replay_count": 0,
        "truth_valid": False,
        "labels_valid": False,
        "same_attempt_remains_unentered": True,
        "next_dispatch_requires_fresh_run_id": True,
        "prior_ledger_current_pointer": prior_pointer,
        "prior_case_record": prior_record,
        "runner_request_chain": evidence["runner_request_chain"],
        "artifact_sha256": evidence["artifact_sha256"],
        "preflight": evidence["preflight"],
        "fresh_load_readback": evidence["fresh_load_readback"],
        "runner_state": evidence["runner_state"],
        "captured_at_utc": timestamp,
    }
    del l["case_records"][CASE_ID]
    l["current_case"] = None
    b["current_case"] = None
    b["updated_at_utc"] = timestamp
    s["current_case_id"] = None
    s["unresolved_runner_request_ids"] = []
    s["updated_at_utc"] = timestamp
    need(_counter_snapshot(l) == before_counts, "PROTECTED_COUNTERS_CHANGED")
    return l, b, s

def query_task(task_name: str) -> dict:
    ps = (
        "$ErrorActionPreference='Stop'; "
        f"$t=Get-ScheduledTask -TaskName '{task_name}'; "
        f"$i=Get-ScheduledTaskInfo -TaskName '{task_name}'; "
        "[Console]::Out.Write((ConvertTo-Json -Compress -InputObject "
        "@{state=[string]$t.State;last_task_result=$i.LastTaskResult}))"
    )
    done = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=20, check=False,
    )
    need(done.returncode == 0, "TASK_SCHEDULER_QUERY_FAILED:" + task_name + ":" + done.stderr[-300:])
    try:
        return json.loads(done.stdout.strip())
    except Exception as exc:
        raise ReconcileError("TASK_SCHEDULER_JSON_INVALID:" + task_name) from exc

def matching_processes() -> list[dict]:
    ps = (
        "$ErrorActionPreference='Stop'; "
        "$xs=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and "
        "$_.CommandLine -match '32155c227f489da2ccf673266720bbca|"
        "K6V2_G024_20261007T110238Z_9bdcaaf0' } | "
        "Select-Object ProcessId,Name,CommandLine); "
        "[Console]::Out.Write((ConvertTo-Json -Compress -InputObject $xs))"
    )
    done = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=20, check=False,
    )
    need(done.returncode == 0, "PROCESS_SCAN_FAILED:" + done.stderr[-300:])
    value = json.loads(done.stdout.strip() or "[]")
    if isinstance(value, dict):
        return [value]
    return list(value or [])

def contains_case_id_key(value: Any, case_id: str) -> bool:
    if isinstance(value, dict):
        if value.get("case_id") == case_id:
            return True
        return any(contains_case_id_key(v, case_id) for v in value.values())
    if isinstance(value, list):
        return any(contains_case_id_key(v, case_id) for v in value)
    return False

def validate_queue_membership(queue_manifest: dict, controller: dict) -> None:
    ordered = queue_manifest.get("ordered_case_ids")
    controller_ids = controller.get("case_ids")
    need(isinstance(ordered, list) and ordered.count(CASE_ID) == 1,
         "G024_NOT_IN_FROZEN_QUEUE_MANIFEST")
    need(isinstance(controller_ids, list) and controller_ids
         and controller_ids[0] == CASE_ID and controller_ids.count(CASE_ID) == 1,
         "G024_NOT_FIRST_OR_UNIQUE_IN_CONTROLLER")

def git_context() -> dict:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                         capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    branch = subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"],
                            capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    need(branch == "work/mdc-np-coupling-ml-v1", "UNEXPECTED_COUPLING_BRANCH")
    return {"branch": branch, "head": head}

def verify_inputs() -> dict:
    need(Path(__file__).resolve().parents[3] == ROOT, "UNEXPECTED_WORKTREE_ROOT")
    need(os.environ.get("COMPUTERNAME", "").upper() == "DESKTOP-NNE313K",
         "WRONG_HOST")
    need(os.environ.get("USERNAME", "").lower() == "dell", "WRONG_USER")
    git = git_context()

    raw_hashes = {}
    for path_s, expected in PINNED_RAW_SHA256.items():
        path = Path(path_s)
        need(path.is_file() and not path.is_symlink(), "PINNED_FILE_MISSING_OR_UNSAFE:" + path_s)
        actual = file_sha256(path)
        need(actual == expected, "PINNED_SHA_MISMATCH:" + path_s)
        raw_hashes[path_s] = actual

    request, _ = read_json(REQUEST_PATH)
    result, _ = read_json(RESULT_PATH)
    claim, _ = read_json(CLAIM_PATH)
    chain = verify_worker_chain(request, result, claim)
    envelope, _ = read_json(ENVELOPE)
    need(identity_matches(envelope) and envelope.get("attempt_id") == ATTEMPT_ID,
         "ENVELOPE_IDENTITY_INVALID")
    need(request.get("manifest_sha256") == raw_hashes[str(ENVELOPE)],
         "REQUEST_ENVELOPE_BINDING_MISMATCH")
    log_text = RUN_LOG.read_text(encoding="utf-8-sig").strip()
    need(log_text == "RUNNER_ERROR:SCHEDULED_WORKER_FAILED:GPU_RESOURCE_NAME_REQUIRED",
         "RUNNER_LOG_DISPOSITION_INVALID")

    preflight, _ = read_json(PREFLIGHT)
    need(identity_matches(preflight, require_run_id=False), "G024_PREFLIGHT_IDENTITY_INVALID")
    need(preflight.get("solver_run_called") is False
         and preflight.get("solver_invocations") == 0, "G024_PREFLIGHT_NOT_ZERO_ENTRY")
    dependency = preflight.get("dependency_preflight", {})
    need(preflight.get("result") == "PASS"
         and preflight.get("solver_run_called") is False
         and preflight.get("solver_invocations") == 0
         and dependency.get("result") == "PASS"
         and dependency.get("solver_run_called") is False
         and dependency.get("scientific_entry_performed") is False,
         "G024_PREFLIGHT_RESULT_NOT_ZERO_ENTRY_PASS")
    load, _ = read_json(LOAD_READBACK)
    need(identity_matches(load, require_run_id=False)
         and load.get("solver_run_called") is False and load.get("solver_invocations") == 0
         and load.get("scientific_entry_count") == 0
         and load.get("source_staged_semantic_parity") == "PASS"
         and load.get("source_validation", {}).get("validation", {}).get("status") == "PASS",
         "G024_LOAD_READBACK_NOT_ZERO_ENTRY_PASS")

    ledger, _ = read_json(LEDGER)
    batch, _ = read_json(BATCH)
    status, _ = read_json(CONTROLLER_STATUS)
    registry, registry_raw = read_json(REGISTRY)
    need(not contains_case_id_key(registry, CASE_ID), "G024_RUNNER_REGISTRY_ROW_EXISTS")
    need(not (RUN_ROOT / CASE_ID / ATTEMPT_ID).exists(), "G024_ATTEMPT_DIRECTORY_EXISTS")
    need(not (RUNNER_ROOT / "active_run.json").exists()
         and not (RUNNER_ROOT / ".runner.lock").exists(), "RUNNER_SLOT_NOT_CLEAR")
    need(not LABEL_NPZ.exists() and not INGEST_RESULT.exists(),
         "G024_TRUTH_OR_LABEL_ARTIFACT_EXISTS")
    need(not RESUME_RECEIPT.exists(), "STALE_CONTROLLER_RESUME_RECEIPT_EXISTS")

    controller, _ = read_json(CONTROLLER_MANIFEST)
    start_claim, _ = read_json(CONTROLLER_START_CLAIM)
    need(controller.get("schema") == "APCD_GPU_RUNNER_V1_COUPLING_QUEUE_CONTROLLER_MANIFEST_V1"
         and controller.get("controller_run_id") == CONTROLLER_RUN_ID
         and controller.get("queue_id") == QUEUE_ID
         and controller.get("controller_script_path") == str(QUEUE_SCRIPT)
         and controller.get("controller_script_sha256") == raw_hashes[str(QUEUE_SCRIPT)]
         and controller.get("queue_manifest_path") == str(QUEUE_MANIFEST)
         and controller.get("queue_manifest_sha256") == raw_hashes[str(QUEUE_MANIFEST)]
         and controller.get("max_cases") == 93
         and controller.get("max_concurrent_cases") == 1
         and controller.get("per_case_max_solver_entries") == 1
         and controller.get("post_entry_automatic_replays") == 0
         and controller.get("case_ids", [None])[0] == CASE_ID,
         "CONTROLLER_MANIFEST_SCOPE_INVALID")
    need(CONTROLLER_REQUEST_ID == raw_hashes[str(CONTROLLER_MANIFEST)][:32]
         and start_claim.get("schema") == "APCD_GPU_RUNNER_V1_CONTROLLER_START_CLAIM_V1"
         and start_claim.get("request_id") == CONTROLLER_REQUEST_ID
         and start_claim.get("controller_manifest_sha256") == raw_hashes[str(CONTROLLER_MANIFEST)]
         and start_claim.get("queue_id") == QUEUE_ID,
         "CONTROLLER_START_CLAIM_BINDING_INVALID")
    need(controller.get("status_path") == str(CONTROLLER_STATUS)
         and status.get("controller_manifest_sha256") == raw_hashes[str(CONTROLLER_MANIFEST)],
         "CONTROLLER_STATUS_MANIFEST_BINDING_INVALID")
    queue_manifest, _ = read_json(QUEUE_MANIFEST)
    validate_queue_membership(queue_manifest, controller)

    old_worker_sha = request.get("worker_module_sha256")
    current_worker_path = RUNNER_WORKTREE / "scripts/shared_fdtd/gpu_runner_v1/task_scheduler_v1.py"
    need(current_worker_path.is_file(), "CURRENT_RUNNER_WORKER_SOURCE_MISSING")
    current_worker_sha = file_sha256(current_worker_path)

    sched_controller = query_task("APCD_GPU_RUNNER_V1_COUPLING_SERIAL_QUEUE_CONTROLLER")
    sched_worker = query_task("APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER")
    need(sched_controller.get("state") == "Ready"
         and sched_controller.get("last_task_result") == 2,
         "CONTROLLER_TASK_NOT_READY_AFTER_EXIT")
    need(sched_worker.get("state") == "Ready", "SINGLE_CASE_WORKER_NOT_READY")
    procs = matching_processes()
    need(not procs, "G024_MATCHING_PROCESS_STILL_ACTIVE")

    need(ledger.get("current_case", {}).get("case_id") == CASE_ID
         and batch.get("current_case", {}).get("case_id") == CASE_ID
         and status.get("current_case_id") == CASE_ID,
         "G024_POINTERS_CHANGED_BEFORE_RECONCILIATION")
    before_counts = _counter_snapshot(ledger)
    need(before_counts == {
        "entered_count": 35, "truth_valid_count": 33, "labels_valid_count": 33,
        "remaining_unentered_count": 93, "automatic_replay_count": 0,
        "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0,
    }, "G024_COUNTERS_CHANGED")
    need(CASE_ID not in ledger.get("entered_case_ids", [])
         and CASE_ID not in ledger.get("truth_valid_case_ids", [])
         and CASE_ID not in ledger.get("labels_valid_case_ids", []),
         "G024_ALREADY_ENTERED_OR_LABELED")
    evidence_stub = {
        "run_log_sha256": raw_hashes[str(RUN_LOG)],
        "runner_request_chain": chain,
        "artifact_sha256": {
            path: sha for path, sha in raw_hashes.items()
            if path in {str(REQUEST_PATH), str(RESULT_PATH), str(CLAIM_PATH),
                        str(ENVELOPE), str(RUN_LOG), str(CONTROLLER_MANIFEST),
                        str(LEDGER), str(BATCH), str(CONTROLLER_STATUS),
                        str(QUEUE_MANIFEST), str(QUEUE_SCRIPT)}
        },
        "preflight": {"path": str(PREFLIGHT), "sha256": file_sha256(PREFLIGHT),
                      "result": "PASS", "solver_run_called": False, "solver_invocations": 0},
        "fresh_load_readback": {"path": str(LOAD_READBACK), "sha256": file_sha256(LOAD_READBACK),
                                "status": "PASS", "solver_run_called": False,
                                "solver_invocations": 0},
        "runner_state": {
            "registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
            "g024_registry_row": False, "g024_attempt_directory_exists": False,
            "active_run_exists": False, "runner_lock_exists": False,
            "matching_processes": procs,
            "controller_task": sched_controller, "worker_task": sched_worker,
            "request_worker_module_sha256": old_worker_sha,
            "current_worker_module_sha256": current_worker_sha,
        },
    }
    return {
        "captured_at_utc": utc_now(),
        "git_context": git,
        "host": os.environ.get("COMPUTERNAME"),
        "user": os.environ.get("USERNAME"),
        "artifact_sha256": raw_hashes,
        "runner_request_chain": chain,
        "preflight": evidence_stub["preflight"],
        "fresh_load_readback": evidence_stub["fresh_load_readback"],
        "runner_state": evidence_stub["runner_state"],
        "before_counts": before_counts,
        "evidence_stub": evidence_stub,
        "ledger": ledger,
        "batch": batch,
        "controller_status": status,
        "ledger_raw": LEDGER.read_bytes(),
        "batch_raw": BATCH.read_bytes(),
        "controller_status_raw": CONTROLLER_STATUS.read_bytes(),
    }

def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

def write_new(path: Path, content: bytes) -> None:
    need(not path.exists(), "OUTPUT_ALREADY_EXISTS:" + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)

def write_atomic(path: Path, content: bytes) -> None:
    tmp = path.with_name(path.name + ".g024_reconcile_tmp")
    need(not tmp.exists(), "TEMP_OUTPUT_EXISTS:" + str(tmp))
    tmp.write_bytes(content)
    os.replace(tmp, path)

def apply_reconciliation(snapshot: dict) -> dict:
    need(not (OUT / "RECOVERY_RECEIPT_V1.json").exists()
         and not (OUT / "PRE_RECONCILIATION_PLAN_V1.json").exists(),
         "RECONCILIATION_ALREADY_STARTED")
    timestamp = utc_now()
    ledger = snapshot["ledger"]
    batch = snapshot["batch"]
    status = snapshot["controller_status"]
    new_ledger, new_batch, new_status = build_reconciled_snapshots(
        ledger, batch, status, snapshot["evidence_stub"], timestamp)
    write_new(OUT / "PRE_RECONCILIATION_LEDGER_V1.json", snapshot["ledger_raw"])
    write_new(OUT / "PRE_RECONCILIATION_BATCH_V1.json", snapshot["batch_raw"])
    write_new(OUT / "PRE_RECONCILIATION_CONTROLLER_STATUS_V1.json",
              snapshot["controller_status_raw"])
    plan = {
        "schema": "COUPLING_K6_V2_G024_PREENTRY_RECONCILIATION_PLAN_V1",
        "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "failed_run_id": OLD_RUN_ID,
        "disposition": "PREENTRY_FAILURE_NO_SOLVER_ENTRY",
        "solver_entry": 0, "automatic_replay": 0, "truth_valid": False,
        "labels_valid": False, "same_attempt_remains_unentered": True,
        "next_dispatch_requires_fresh_run_id": True,
        "captured_at_utc": timestamp,
        "before_sha256": {
            str(LEDGER): file_sha256(LEDGER), str(BATCH): file_sha256(BATCH),
            str(CONTROLLER_STATUS): file_sha256(CONTROLLER_STATUS),
        },
        "evidence": {k: v for k, v in snapshot.items()
                     if k not in {"ledger", "batch", "controller_status",
                                  "ledger_raw", "batch_raw", "controller_status_raw",
                                  "evidence_stub"}},
        "git_context": snapshot["git_context"],
        "target_current_pointers": None,
        "counter_invariants": snapshot["before_counts"],
    }
    write_new(OUT / "PRE_RECONCILIATION_PLAN_V1.json", json_bytes(plan))
    write_atomic(LEDGER, json_bytes(new_ledger))
    write_atomic(BATCH, json_bytes(new_batch))
    write_atomic(CONTROLLER_STATUS, json_bytes(new_status))

    args = [
        sys.executable, str(QUEUE_SCRIPT),
        "--reconcile-controller-stop-only",
        "--runner-controller-manifest", str(CONTROLLER_MANIFEST),
        "--runner-controller-manifest-sha256", PINNED_RAW_SHA256[str(CONTROLLER_MANIFEST)],
        "--runner-controller-request-id", CONTROLLER_REQUEST_ID,
    ]
    done = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=90, check=False)
    stop_log = {
        "command": args, "returncode": done.returncode,
        "stdout": done.stdout, "stderr": done.stderr,
        "solver_invocations": 0, "runner_run_one_called": False,
    }
    write_new(OUT / "OFFICIAL_STOP_ONLY_OUTPUT_V1.json", json_bytes(stop_log))
    need(done.returncode == 0, "OFFICIAL_STOP_ONLY_FAILED:" + done.stderr[-500:])

    final_ledger, _ = read_json(LEDGER)
    final_batch, _ = read_json(BATCH)
    final_status, status_raw = read_json(CONTROLLER_STATUS)
    receipt, _ = read_json(RESUME_RECEIPT)
    need(final_ledger.get("current_case") is None and final_batch.get("current_case") is None
         and final_status.get("state") == "STOPPED_RECONCILED"
         and final_status.get("current_case_id") is None
         and final_status.get("unresolved_runner_request_ids") == [],
         "FINAL_STOP_ONLY_BOUNDARY_INVALID")
    need(CASE_ID not in final_ledger.get("case_records", {})
         and CASE_ID not in final_ledger.get("entered_case_ids", [])
         and CASE_ID not in final_ledger.get("truth_valid_case_ids", [])
         and CASE_ID not in final_ledger.get("labels_valid_case_ids", [])
         and _counter_snapshot(final_ledger) == snapshot["before_counts"],
         "FINAL_G024_OR_COUNTER_STATE_INVALID")
    event = next(row for row in final_ledger["failed_or_isolated_cases"]
                 if row.get("case_id") == CASE_ID)
    rec = event["evidence"]["preentry_reconciliation"]
    need(rec.get("prior_case_record", {}).get("attempt_id") == ATTEMPT_ID
         and rec.get("prior_case_record", {}).get("run_id") == OLD_RUN_ID
         and rec.get("solver_entered") is False,
         "PRIOR_G024_RECORD_NOT_PRESERVED")
    need(receipt.get("schema") == "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_RESUME_RECEIPT_V1"
         and receipt.get("request_id") == CONTROLLER_REQUEST_ID
         and receipt.get("controller_manifest_sha256") == PINNED_RAW_SHA256[str(CONTROLLER_MANIFEST)]
         and receipt.get("queue_id") == QUEUE_ID and receipt.get("safe_to_resume") is True
         and receipt.get("startup_reconciled") is True
         and receipt.get("current_case_id") is None
         and receipt.get("unresolved_runner_request_ids") == []
         and receipt.get("post_entry_automatic_replays") == 0
         and receipt.get("previous_status_sha256") == hashlib.sha256(status_raw).hexdigest()
         and receipt.get("resume_generation") == final_status.get("resume_generation", 0) + 1
         and receipt.get("runner_request_ids") == final_status.get("runner_request_ids"),
         "OFFICIAL_RESUME_RECEIPT_INVALID")

    final = {
        "schema": "COUPLING_K6_V2_G024_PREENTRY_RECONCILIATION_RECEIPT_V1",
        "git_context": snapshot["git_context"],
        "case_id": CASE_ID, "attempt_id": ATTEMPT_ID, "failed_run_id": OLD_RUN_ID,
        "disposition": "PREENTRY_FAILURE_NO_SOLVER_ENTRY",
        "entry_consumed": False, "solver_entries": 0, "automatic_replays": 0,
        "truth_valid": False, "labels_valid": False,
        "same_attempt_remains_unentered": True,
        "next_dispatch_requires_fresh_run_id_after_worker_fix": True,
        "training_fits": final_ledger.get("training_fits"),
        "p_scale_fits": final_ledger.get("p_scale_fits"),
        "confirmation_response_access_count": final_ledger.get("confirmation_response_access_count"),
        "counts": _counter_snapshot(final_ledger),
        "preserved_original_case_record": rec["prior_case_record"],
        "runner_request_chain": rec["runner_request_chain"],
        "artifact_sha256": rec["artifact_sha256"],
        "runner_state": rec["runner_state"],
        "preflight": rec["preflight"],
        "fresh_load_readback": rec["fresh_load_readback"],
        "controller": {
            "status_path": str(CONTROLLER_STATUS),
            "status_sha256": file_sha256(CONTROLLER_STATUS),
            "resume_receipt_path": str(RESUME_RECEIPT),
            "resume_receipt_sha256": file_sha256(RESUME_RECEIPT),
            "resume_receipt": receipt,
            "official_stop_only_returncode": done.returncode,
        },
        "reconciled_at_utc": utc_now(),
        "solver_invocations_this_utility": 0,
        "run_one_invocations_this_utility": 0,
        "queue_resume_invocations_this_utility": 0,
    }
    write_new(OUT / "RECOVERY_RECEIPT_V1.json", json_bytes(final))
    (OUT / "CONTINUATION.md").write_text(
        "# CONTINUATION - G024 PRE-ENTRY RECONCILIATION\n\n"
        f"Updated UTC: {final['reconciled_at_utc']}\n\n"
        f"Host: {os.environ.get('COMPUTERNAME')} / {os.environ.get('USERNAME')}\n"
        f"Coupling worktree: {ROOT}\nBranch: work/mdc-np-coupling-ml-v1\n"
        f"HEAD at reconciliation: {snapshot['git_context']['head']}\n\n"
        "G024 attempt_001 is proven pre-entry: scheduled request terminated with "
        "GPU_RESOURCE_NAME_REQUIRED, solver_entered=false, no registry row, no run "
        "directory, active slot, truth, or label. The failed run evidence and original "
        "case-record snapshot are preserved. Official controller state is "
        "STOPPED_RECONCILED with a hash-bound resume receipt. No queue resume, run-one, "
        "solver, training, or confirmation access was invoked by this utility.\n\n"
        "Before any queue continuation, perform the frozen live route/hold/generation/"
        "owner/fence/slot checks against the authorized Runner source and require the "
        "current GPU Runner HEAD 860f57a119d66b300b469125e31fec2f75bc733c. Dispatch only "
        "the same unentered G024 attempt_001 under a fresh unique run_id; post-entry "
        "automatic replay remains zero.\n\n"
        "Read RECOVERY_RECEIPT_V1.json, PRE_RECONCILIATION_PLAN_V1.json, and "
        "SHA256_INVENTORY_V1.json before resuming.\n",
        encoding="utf-8",
    )
    files = [
        "reconcile_g024_preentry_v1.py", "test_reconcile_g024_preentry_v1.py",
        "PRE_RECONCILIATION_LEDGER_V1.json", "PRE_RECONCILIATION_BATCH_V1.json",
        "PRE_RECONCILIATION_CONTROLLER_STATUS_V1.json", "PRE_RECONCILIATION_PLAN_V1.json",
        "OFFICIAL_STOP_ONLY_OUTPUT_V1.json", "RECOVERY_RECEIPT_V1.json", "CONTINUATION.md",
    ]
    inventory = {
        "schema": "COUPLING_K6_V2_G024_PREENTRY_RECONCILIATION_SHA256_INVENTORY_V1",
        "files": {name: file_sha256(OUT / name) for name in files},
        "controller_status_sha256": file_sha256(CONTROLLER_STATUS),
        "controller_resume_receipt_sha256": file_sha256(RESUME_RECEIPT),
        "queue_ledger_sha256": file_sha256(LEDGER),
        "batch_status_sha256": file_sha256(BATCH),
    }
    write_new(OUT / "SHA256_INVENTORY_V1.json", json_bytes(inventory))
    return final

def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify-only", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        snapshot = verify_inputs()
        if args.verify_only:
            planned_ledger, planned_batch, planned_status = build_reconciled_snapshots(
                snapshot["ledger"], snapshot["batch"], snapshot["controller_status"],
                snapshot["evidence_stub"], utc_now())
            print(json.dumps({
                "status": "VERIFIED_NO_WRITE", "case_id": CASE_ID,
                "attempt_id": ATTEMPT_ID, "failed_run_id": OLD_RUN_ID,
                "planned_ledger_current_case": planned_ledger.get("current_case"),
                "planned_batch_current_case": planned_batch.get("current_case"),
                "planned_controller_current_case_id": planned_status.get("current_case_id"),
                "solver_entered": False, "solver_invocations": 0,
                "counter_snapshot": snapshot["before_counts"],
                "evidence_sha256": snapshot["artifact_sha256"],
                "runner_request_chain": snapshot["runner_request_chain"],
                "runner_state": snapshot["runner_state"],
            }, indent=2))
            return 0
        final = apply_reconciliation(snapshot)
        print(json.dumps(final, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "STOPPED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
