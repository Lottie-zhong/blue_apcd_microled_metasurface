# -*- coding: utf-8 -*-
"""Sequential K6 V2 queue over the official GPU Runner V1 run-one CLI."""
import argparse
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1"
BATCH = REPORT / "BATCH_PREPARATION_STATUS_V1.json"
QMAN = REPORT / "BATCH_QUEUE_MANIFEST_V1.json"
LEDGER = REPORT / "QUEUE_EXECUTION_LEDGER_V1.json"
CASE_ROOT = ROOT / "outputs/coupling_ml/APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1"
RUN_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
RUN_TREE = Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
RUN_DIR = RUN_TREE / "scripts/shared_fdtd/gpu_runner_v1"
ADAPTER = RUN_DIR / "adapter.py"
AUTH = RUN_DIR / "controlled_admission_authority_v1.json"
POLICY = RUN_DIR / "controlled_admission_policy_v1.json"
BUDGET = RUN_DIR / "k6_v2_development_solver_budget_v1.json"
VALIDATOR = ROOT / "scripts/coupling_ml/validate_pw_k6_5nm_full_period_prefsp_v1.py"
AUTH_SHA = "a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35"
POLICY_SHA = "b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45"
BUDGET_SHA = "e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c"
CONTRACT_SHA = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
EXPANSION_SHA = "4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f"
INITIAL = ("K6LDA1_DEV_D1_M05", "K6LDA1_DEV_D1_P05", "K6LDA1_DEV_D2_M05")
INITIAL_LABELS = {
    "K6LDA1_DEV_D1_M05": (
        ROOT / "reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/FIRST_CASE_INGEST_RESULT_V1.json",
        ROOT / "reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/FIRST_CASE_INGEST_TRUTH_V1.npz"),
    "K6LDA1_DEV_D1_P05": (
        REPORT / "INGEST_RESULT_K6LDA1_DEV_D1_P05_V1.json",
        REPORT / "INGESTED_TRUTH_K6LDA1_DEV_D1_P05_V1.npz"),
    "K6LDA1_DEV_D2_M05": (
        REPORT / "INGEST_RESULT_K6LDA1_DEV_D2_M05_V1.json",
        REPORT / "INGESTED_TRUTH_K6LDA1_DEV_D2_M05_V1.npz"),
}
RESOURCE = "GPU license audit"

FAILED_POSTENTRY_AUTHORITY = {
    "case_id": "K6LDA1_DEV_D6_M05",
    "attempt_id": "attempt_001",
    "run_id": "K6V2_D6M05_20261005T182728Z_92041df6",
    "disposition_sha256": "c0dccb19b41b92e0ab2da46c3ab83bdc47fb61c6090e21a7b84cec2d1f0c84d0",
    "journal_sha256": "4935aa39829286d136172233ea6148e7c1982b9d4b6a07f234680237a1484365",
    "claim_sha256": "bcc2b973909925ccee9a61c7fed371826e6c8f9222d72c0d99f7ec9e4261de2b",
    "recovery_fence_id": "b9fef760fff54cb59faceeba428c056e",
}
G023_POSTENTRY_AUTHORITY = {
    "case_id": "K6GDP2_DEV_G023",
    "attempt_id": "attempt_001",
    "run_id": "K6V2_G023_20261006T144241Z_0a0cb192",
    "sequence_index": 35,
    "queue_manifest_file_sha256": "fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7",
    "queue_manifest_sha256": "ecbb9b32105f5a26adf051d614bef68fcf793e0f089eae391510e6b86a138e32",
    "ledger_sha256": "79da35c8c1fa129527c0828b954dfbcb1b9541e2fc236223c02bd47266bf05f9",
    "manifest_sha256": "5047e9bf42d83679e7615b4086a020a51c9cc06915a7b51b27c2cbd85c7134f8",
    "status_sha256": "e81e8e2fc2445a0bf798668c177a01b7062faef47e6e0952875cbfb240f50ab4",
    "disposition_sha256": "a529fafa81003c26f24640571388af4d195b28c17e2501a1c140bf21c0a90792",
    "receipt_file_sha256": "d6485fd48a875a5dadab14dd820b3ae2ad0c5819eee47197ee174d0b0faf07d3",
    "receipt_sha256": "ba4394dcf8952c667e45e0f76cb9eebe4e44afe73cd9c9d71151a1990857efcb",
    "journal_sha256": "98817f534a379a196efb12bed610f24260a44c3c440b0c931754aa1182289af2",
    "claim_file_sha256": "97156447b1894558bb631cf0e3e8f28c877acd2fa5fdc07d7547c24edb5d9e83",
    "claim_sha256": "7e8797b71fef3dc4a420ea56e946a3c49400e09608a9442cdd1e33a8aa64c65f",
    "registry_sha256": "8beb6f9593d8783113f0411f3f2a478f75faf3fbc317c5ae70a0fad3d910c11b",
    "recovery_fence_id": "975691dbbe88461580ab85a73bfbfd5a",
    "active_marker_archive_sha256": "dfd0e08c1a85d37f92accb7a51ff1f58b7cd60de939e5873f6e29b64c004accf",
    "runner_lock_archive_sha256": "c10e17415ad3178c9b7e3d6a4fe4dae300ee134f33c5ad2da79a5840705232bc",
    "coupling_ledger_path_sha256": "79da35c8c1fa129527c0828b954dfbcb1b9541e2fc236223c02bd47266bf05f9",
}
CONTROLLER_PROTOCOL = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_CLI_V1"
SCHEMA_CONTROLLER_MANIFEST = "APCD_GPU_RUNNER_V1_COUPLING_QUEUE_CONTROLLER_MANIFEST_V1"
SCHEMA_CONTROLLER_STATUS = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1"
SCHEMA_CONTROLLER_RESUME = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_RESUME_RECEIPT_V1"
CONTROLLER_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
CONTROLLER_REQUEST_ID_RE = re.compile(r"^[0-9a-f]{32}$")
FAILED_POSTENTRY_EVENT_ORDER = (
    "PREPARED", "DISPOSITION_WRITTEN", "STATUS_TERMINALIZATION_INTENT",
    "STATUS_TERMINALIZED", "REGISTRY_TERMINALIZATION_INTENT", "REGISTRY_TERMINALIZED",
    "RELEASE_READY", "ACTIVE_MARKER_RELEASED", "LOCK_RELEASE_INTENT", "LOCK_RELEASED",
)
CONTROLLER_PROTOCOL = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_CLI_V1"
CONTROLLER_MANIFEST_SCHEMA = "APCD_GPU_RUNNER_V1_COUPLING_QUEUE_CONTROLLER_MANIFEST_V1"
CONTROLLER_STATUS_SCHEMA = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_STATUS_V1"
CONTROLLER_RESUME_SCHEMA = "APCD_GPU_RUNNER_V1_QUEUE_CONTROLLER_RESUME_RECEIPT_V1"
CONTROLLER_TASK_NAME = r"\APCD_GPU_RUNNER_V1_COUPLING_SERIAL_QUEUE_CONTROLLER"
CONTROLLER_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
CONTROLLER_MAX_CASES = 128

FAILED_PREENTRY_AUTHORITY = {
    "case_id": "K6LDA1_DEV_D6_P05",
    "attempt_id": "attempt_001",
    "run_id": "K6V2_D6P05_20261006T063951Z_c6f073e5",
    "sequence_index": 12,
    "ledger_sha256": "0c4a7fd16b710412ced0b0fc7a465d2a30746bbb406e29566ce55b0fcd2211d1",
    "queue_manifest_sha256": "ecbb9b32105f5a26adf051d614bef68fcf793e0f089eae391510e6b86a138e32",
    "envelope_sha256": "96f3f5d9f4e1d1055c0837d0c0a259618bade0d7e346eb4f4b269f563ce03d2e",
    "manifest_sha256": "87c0aca8e1596be49b7c6f51e54cd298a37ee1a127958c3120171924ef5eff41",
    "pending_status_sha256": "a0c58c1438c613cacf750cc1d020298dc0d42ea98f6105254243632cd62ea490",
    "status_sha256": "a2bb8d0e589b8792601dff8c6cc1b3157c035be5b0073e50e3bd3d9247eac6c5",
    "pending_registry_sha256": "ba21857c1bfafcbb342819a5fa049fa8a1fe4649afd32067b519ebe627f0871a",
    "registry_terminal_sha256": "b3be6f8a1fcbec299939c5f531da2a9eaf58bff7b72bac86d900f16dfcfb3830",
    "disposition_sha256": "3c39dbfe0cb65059cd6db80271fc1964e9656429b2010fcfe11ffc690ee282ea",
    "claim_sha256": "454e041b19cf3a7d0656b3e8d06a3b4fb9b0725ed11c150cf070511f8cec3570",
    "journal_sha256": "29bc69da178291bb0ad4c5ad4c31cc2d9bcd36626f754bfd4e7393a369e2b1c0",
    "fence_sha256": "61d68e7957bdd486d8bb64b81ea7ed45d9ed02760db3b1fa0646a8018a120b42",
    "lock_sha256": "5c0510149267ae2d9df9e853601c6b5c60195e49633b437ff881fcd0c45fcb28",
    "lock_pid": 34072,
    "process_census_sha256": "661d9e2614bd3106db353b805d98db6f30c7dcd3790f73cdafd21605e8f1811b",
    "control_snapshot_sha256": "1e21975955e09b43ecf34d20089e05a554e3a31862cd1e9a4b644eb5208873d5",
    "control_db_sha256": "af802fd46c023009f0a342cfa9540990c8e3a0df9b30af09ef62deeba817d9fe",
    "control_generation": 27,
    "registry_other_rows_sha256": "c647e3b7da48c6126be22c100985032c67440b8bfa929d0c149d53d7f4eab4e2",
    "empty_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "immutable_artifacts": {
        "authority": {"path": r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\controlled_admission_authority_v1.json",
                      "sha256": "a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35"},
        "contract": {"path": r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D6_P05\attempt_001\physical_contract.json",
                     "sha256": "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"},
        "coupling_ledger_counts": {"automatic_replay_count": 0, "entered_count": 11,
                                   "target_phase": "RUN_ONE_IN_PROGRESS", "target_sequence_index": 12,
                                   "truth_valid_count": 10},
        "envelope": {"path": r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\RUN_ENVELOPE_K6V2_D6P05_20261006T063951Z_c6f073e5.json",
                     "sha256": "96f3f5d9f4e1d1055c0837d0c0a259618bade0d7e346eb4f4b269f563ce03d2e"},
        "ledger": {"path": r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\QUEUE_EXECUTION_LEDGER_V1.json",
                   "sha256": "0c4a7fd16b710412ced0b0fc7a465d2a30746bbb406e29566ce55b0fcd2211d1"},
        "pre_fsp": {"path": r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D6_P05\attempt_001\setup\runtime.fsp",
                    "sha256": "7b3a9f0a46ce8a001076b29bf2aee86ffd8b79107bc8babd270fd1d7e5e33e58"},
        "source_manifest": {"path": r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D6_P05\attempt_001\source_manifest.json",
                            "sha256": "ab6d929310fe6b329e54430dd1611a8ce811cdde12bb930d6e9bb6013e952edb"},
    },
    "target_artifacts": {
        "hashes": "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc",
        "manifest": "87c0aca8e1596be49b7c6f51e54cd298a37ee1a127958c3120171924ef5eff41",
        "solver_log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "validation": "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc",
    },
}
FAILED_PREENTRY_EVENT_ORDER = (
    "CLAIMED", "STATUS_TERMINALIZATION_INTENT", "STATUS_TERMINALIZED",
    "REGISTRY_TERMINALIZATION_INTENT", "REGISTRY_TERMINALIZED",
    "RELEASE_READY", "LOCK_RELEASE_INTENT",
)


class StopQueue(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(value, f, sort_keys=True, indent=2, ensure_ascii=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def need(condition, message):
    if not condition:
        raise StopQueue(message)


def artifact(case_dir, descriptor, name):
    need(isinstance(descriptor, dict) and isinstance(descriptor.get("path"), str),
         "BAD_CASE_ARTIFACT:" + name)
    path = (case_dir / descriptor["path"]).resolve(strict=True)
    need(path.is_file() and not path.is_symlink() and sha(path) == descriptor.get("sha256"),
         "CASE_ARTIFACT_SHA_MISMATCH:" + name)
    return path


def modules():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(RUN_DIR))
    return (importlib.import_module("scripts.coupling_ml.k6_v2_pipeline.ingest"),
            importlib.import_module("controlled_admission_v1"),
            importlib.import_module("adapter"))


def load_inputs():
    need(sha(AUTH) == AUTH_SHA and sha(POLICY) == POLICY_SHA and sha(BUDGET) == BUDGET_SHA,
         "FROZEN_RUNNER_AUTHORITY_SHA_MISMATCH")
    status, budget, authority = read(BATCH), read(BUDGET), read(AUTH)
    need(status.get("budget_sha256") == BUDGET_SHA
         and status.get("route_authority_sha256") == AUTH_SHA
         and status.get("route_policy_sha256") == POLICY_SHA, "BATCH_AUTHORITY_BINDING_MISMATCH")
    need(budget.get("status") == "OWNER_APPROVED_ACTIVE", "ENTRY_BUDGET_NOT_ACTIVE")
    limits = budget.get("limits", {})
    need(limits.get("max_total_entries") == 128 and limits.get("max_entries_per_case") == 1
         and limits.get("post_entry_automatic_replays") == 0, "ENTRY_BUDGET_LIMITS_MISMATCH")
    raw = budget.get("development_cases")
    need(isinstance(raw, list), "BUDGET_CASES_MISSING")
    ids = [x if isinstance(x, str) else x.get("case_id") for x in raw]
    need(len(ids) == 128 and len(set(ids)) == 128 and all(isinstance(x, str) for x in ids),
         "BUDGET_CASE_ORDER_INVALID")
    need(status.get("queue_case_ids") == [x for x in ids if x not in INITIAL],
         "QUEUE_DIFFERS_FROM_FROZEN_ORDER")
    need(authority.get("expansion_manifest_sha256") == EXPANSION_SHA, "EXPANSION_AUTHORITY_MISMATCH")
    ingest, controlled, adapter = modules()
    registry = ingest.load_frozen_case_registry(ROOT)
    need(set(ids).issubset(registry.development), "QUEUE_CASE_NOT_IN_DEVELOPMENT_ALLOWLIST")
    for cid in ids:
        case = registry.development[cid]
        need(case.get("attempt_id") == "attempt_001" and case.get("role") in ingest._DEV,
             "CASE_ROLE_OR_ATTEMPT_INVALID:" + cid)
    manifest = {
        "schema": "COUPLING_K6_V2_SERIAL_QUEUE_MANIFEST_V1",
        "budget_sha256": BUDGET_SHA, "route_authority_sha256": AUTH_SHA,
        "route_policy_sha256": POLICY_SHA, "physical_contract_sha256": CONTRACT_SHA,
        "queue_total": 128, "initially_entered_case_ids": list(INITIAL), "ordered_case_ids": ids,
        "ordered_cases": [{"case_id": c, "attempt_id": registry.development[c]["attempt_id"],
                           "role": registry.development[c]["role"],
                           "ordered_D_nm": list(registry.development[c]["ordered_D_nm"])} for c in ids],
        "confirmation_response_access": False, "per_case_max_solver_entries": 1,
        "post_entry_automatic_replays": 0,
        "execution_mode": "official run-one; DONE/truth/lock-release; ingest; then next case",
    }
    qsha = canonical_sha(manifest)
    manifest["queue_manifest_sha256"] = qsha
    if QMAN.exists():
        need(read(QMAN) == manifest, "QUEUE_MANIFEST_CONFLICT")
    else:
        write(QMAN, manifest)
    return status, budget, registry, ids, manifest, qsha, ingest, controlled, adapter


def runner_registry():
    path = RUN_ROOT / "registry.json"
    need(path.is_file(), "RUNNER_REGISTRY_MISSING")
    value = read(path)
    need(isinstance(value.get("runs"), list), "RUNNER_REGISTRY_SCHEMA_INVALID")
    return path, value


def rows_for(value, cid):
    return [r for r in value["runs"] if r.get("case_id") == cid and r.get("attempt_id") == "attempt_001"]


def runner_status(row, cid):
    path = Path(row.get("run_dir", "")) / "status.json"
    need(path.is_file(), "RUNNER_STATUS_MISSING:" + cid)
    value = read(path)
    need(value.get("case_id") == cid and value.get("attempt_id") == "attempt_001"
         and value.get("run_id") == row.get("run_id"), "RUNNER_STATUS_IDENTITY_MISMATCH:" + cid)
    return value


def initial_labels():
    result = {}
    for cid, (record, truth) in INITIAL_LABELS.items():
        need(record.is_file() and truth.is_file(), "INITIAL_LABEL_MISSING:" + cid)
        data = read(record)
        need(data.get("case_id") in (None, cid) and data.get("status") == "PASS",
             "INITIAL_LABEL_NOT_PASS:" + cid)
        declared = data.get("truth_artifact", {}).get("sha256")
        need(not declared or declared == sha(truth), "INITIAL_LABEL_SHA_MISMATCH:" + cid)
        result[cid] = {"result_path": str(record), "result_sha256": sha(record),
                       "truth_path": str(truth), "truth_sha256": sha(truth)}
    return result


def runner_canonical_sha(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_controller_manifest(path, expected_sha256, request_id):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), "CONTROLLER_MANIFEST_NOT_REGULAR_FILE")
    raw = path.read_bytes()
    actual_sha = hashlib.sha256(raw).hexdigest()
    need(actual_sha == expected_sha256 and CONTROLLER_REQUEST_ID_RE.fullmatch(str(request_id))
         and request_id == actual_sha[:32], "CONTROLLER_MANIFEST_REQUEST_BINDING_INVALID")
    try:
        manifest = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StopQueue("CONTROLLER_MANIFEST_JSON_INVALID") from exc
    required = ("controller_run_id", "queue_id", "controller_script_path", "controller_script_sha256",
        "queue_manifest_path", "queue_manifest_sha256", "case_ids", "max_cases",
        "max_concurrent_cases", "per_case_max_solver_entries", "post_entry_automatic_replays",
        "startup_reconcile_before_dispatch", "truth_before_next_case", "controller_protocol", "status_path")
    need(isinstance(manifest, dict) and manifest.get("schema") == SCHEMA_CONTROLLER_MANIFEST
         and all(key in manifest for key in required), "CONTROLLER_MANIFEST_SCHEMA_OR_FIELDS_INVALID")
    need(isinstance(manifest["controller_run_id"], str)
         and CONTROLLER_RUN_ID_RE.fullmatch(manifest["controller_run_id"])
         and isinstance(manifest["queue_id"], str)
         and CONTROLLER_RUN_ID_RE.fullmatch(manifest["queue_id"]), "CONTROLLER_RUN_ID_INVALID")
    script_path = Path(manifest["controller_script_path"]).resolve(strict=True)
    need(script_path == Path(__file__).resolve(strict=True)
         and manifest["controller_script_sha256"] == sha(script_path),
         "CONTROLLER_SCRIPT_IDENTITY_OR_SHA_MISMATCH")
    queue_path = Path(manifest["queue_manifest_path"]).resolve(strict=True)
    need(queue_path == QMAN.resolve(strict=True)
         and manifest["queue_manifest_sha256"] == sha(queue_path),
         "CONTROLLER_QUEUE_MANIFEST_IDENTITY_OR_SHA_MISMATCH")
    queue = read(queue_path)
    body = dict(queue)
    canonical_sha = body.pop("queue_manifest_sha256", None)
    need(canonical_sha == runner_canonical_sha(body), "CONTROLLER_QUEUE_MANIFEST_CANONICAL_SHA_INVALID")
    allowed_ids = queue.get("ordered_case_ids")
    case_ids = manifest["case_ids"]
    need(isinstance(allowed_ids, list) and isinstance(case_ids, list) and case_ids
         and all(isinstance(cid, str) and CONTROLLER_RUN_ID_RE.fullmatch(cid) for cid in case_ids)
         and len(case_ids) == len(set(case_ids)), "CONTROLLER_CASE_ALLOWLIST_INVALID")
    positions = {cid: index for index, cid in enumerate(allowed_ids) if isinstance(cid, str)}
    indexes = [positions.get(cid) for cid in case_ids]
    need(all(index is not None for index in indexes) and indexes == sorted(indexes),
         "CONTROLLER_CASES_OUTSIDE_OR_OUT_OF_ORDER")
    need(not (set(case_ids) & set(INITIAL)), "CONTROLLER_INITIAL_CASES_NOT_REDISPATCHABLE")
    need(not isinstance(manifest["max_cases"], bool) and manifest["max_cases"] == len(case_ids)
         and not isinstance(manifest["max_concurrent_cases"], bool) and manifest["max_concurrent_cases"] == 1
         and not isinstance(manifest["per_case_max_solver_entries"], bool)
         and manifest["per_case_max_solver_entries"] == 1
         and not isinstance(manifest["post_entry_automatic_replays"], bool)
         and manifest["post_entry_automatic_replays"] == 0
         and manifest["startup_reconcile_before_dispatch"] is True
         and manifest["truth_before_next_case"] is True
         and manifest["controller_protocol"] == CONTROLLER_PROTOCOL,
         "CONTROLLER_BOUND_OR_RECOVERY_POLICY_INVALID")
    status_path = Path(manifest["status_path"]).resolve(strict=False)
    try:
        status_path.relative_to(REPORT.resolve(strict=True))
    except ValueError as exc:
        raise StopQueue("CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT") from exc
    tokens = ("--runner-controller-manifest", "--runner-controller-manifest-sha256",
        "--runner-controller-request-id", "--runner-resume-receipt", "--runner-resume-receipt-sha256")
    script_text = script_path.read_text(encoding="utf-8-sig")
    need(all(token in script_text for token in tokens), "CONTROLLER_SCRIPT_PROTOCOL_TOKENS_MISSING")
    return {"manifest": manifest, "manifest_sha256": actual_sha, "request_id": request_id,
        "manifest_path": str(path.resolve()), "status_path": status_path,
        "case_ids": list(case_ids), "queue_id": manifest["queue_id"]}


def verify_controller_resume_receipt(controller, path, expected_sha256):
    receipt_path = Path(path)
    need(not receipt_path.is_symlink() and receipt_path.is_file()
         and sha(receipt_path) == expected_sha256, "CONTROLLER_RESUME_RECEIPT_FILE_SHA_INVALID")
    status_path = controller["status_path"]
    need(status_path.is_file() and not status_path.is_symlink(), "CONTROLLER_RESUME_STATUS_MISSING")
    status_raw = status_path.read_bytes()
    status = json.loads(status_raw.decode("utf-8-sig"))
    receipt = read(receipt_path)
    expected = {"schema": SCHEMA_CONTROLLER_RESUME, "request_id": controller["request_id"],
        "controller_manifest_sha256": controller["manifest_sha256"], "queue_id": controller["queue_id"],
        "previous_status_sha256": hashlib.sha256(status_raw).hexdigest(), "safe_to_resume": True,
        "startup_reconciled": True, "current_case_id": None,
        "unresolved_runner_request_ids": [], "post_entry_automatic_replays": 0}
    need(status.get("schema") == SCHEMA_CONTROLLER_STATUS and status.get("state") == "STOPPED_RECONCILED"
         and status.get("request_id") == controller["request_id"]
         and status.get("controller_manifest_sha256") == controller["manifest_sha256"]
         and status.get("queue_id") == controller["queue_id"] and status.get("current_case_id") is None
         and status.get("unresolved_runner_request_ids") == []
         and status.get("post_entry_automatic_replays") == 0,
         "CONTROLLER_RESUME_STATUS_NOT_SAFE")
    need(all(receipt.get(key) == value for key, value in expected.items())
         and receipt.get("resume_generation") == status.get("resume_generation", 0) + 1
         and isinstance(receipt.get("runner_request_ids"), list)
         and status.get("runner_request_ids") == receipt.get("runner_request_ids"),
         "CONTROLLER_RESUME_RECEIPT_NOT_BOUND_TO_STOPPED_STATUS")
    return receipt


def reconcile_controller_stopped_boundary(controller):
    """Mint a Runner-compatible resume receipt only at an audited case boundary."""
    status_path = controller["status_path"]
    need(status_path.is_file() and not status_path.is_symlink(), "CONTROLLER_STATUS_MISSING")
    status_raw = status_path.read_bytes()
    status = json.loads(status_raw.decode("utf-8-sig"))
    need(status.get("schema") == SCHEMA_CONTROLLER_STATUS
         and status.get("request_id") == controller["request_id"]
         and status.get("controller_manifest_sha256") == controller["manifest_sha256"]
         and status.get("queue_id") == controller["queue_id"]
         and status.get("state") in {"RUNNING", "STOPPED_RECONCILED"},
         "CONTROLLER_STOP_BOUNDARY_STATUS_IDENTITY_INVALID")
    receipt_path = status_path.with_name("resume_receipt_v1.json")
    if status.get("state") == "STOPPED_RECONCILED":
        need(receipt_path.is_file() and not receipt_path.is_symlink(),
             "CONTROLLER_STOPPED_STATUS_WITHOUT_RESUME_RECEIPT")
        verify_controller_resume_receipt(controller, receipt_path, sha(receipt_path))
        return {"status_path": str(status_path), "status_sha256": sha(status_path),
            "resume_receipt_path": str(receipt_path), "resume_receipt_sha256": sha(receipt_path),
            "state": "STOPPED_RECONCILED", "idempotent": True}
    need(status.get("current_case_id") is None
         and status.get("unresolved_runner_request_ids") == []
         and status.get("post_entry_automatic_replays") == 0
         and isinstance(status.get("runner_request_ids"), list),
         "CONTROLLER_STOP_BOUNDARY_HAS_ACTIVE_CASE_OR_REQUEST")
    ledger = read(LEDGER)
    batch = read(BATCH)
    need(ledger.get("current_case") is None and batch.get("current_case") is None,
         "CONTROLLER_STOP_BOUNDARY_LEDGER_POINTER_NOT_CLEAR")
    need(ledger.get("entered_count") == len(ledger.get("entered_case_ids", []))
         and ledger.get("truth_valid_count") == len(ledger.get("truth_valid_case_ids", []))
         and ledger.get("labels_valid_count") == len(ledger.get("labels_valid_case_ids", []))
         and set(ledger.get("truth_valid_case_ids", [])).issubset(set(ledger.get("entered_case_ids", [])))
         and set(ledger.get("labels_valid_case_ids", [])).issubset(set(ledger.get("truth_valid_case_ids", [])))
         and ledger.get("entered_count", 0) + ledger.get("remaining_unentered_count", 0) == 128
         and ledger.get("automatic_replay_count") == 0 and ledger.get("training_fits") == 0
         and ledger.get("p_scale_fits") == 0 and ledger.get("confirmation_response_access_count") == 0,
         "CONTROLLER_STOP_BOUNDARY_LEDGER_COUNTERS_INVALID")
    case_records = ledger.get("case_records", {})
    need(isinstance(case_records, dict), "CONTROLLER_STOP_BOUNDARY_CASE_RECORDS_INVALID")
    for cid in controller["case_ids"]:
        record = case_records.get(cid)
        if record is not None:
            need(record.get("phase") == "LABEL_PASS", "CONTROLLER_STOP_BOUNDARY_CASE_NOT_LABEL_VALID:" + cid)
    need(not (RUN_ROOT / "active_run.json").exists() and not (RUN_ROOT / ".runner.lock").exists(),
         "CONTROLLER_STOP_BOUNDARY_RUNNER_SLOT_NOT_CLEAR")
    need(not receipt_path.exists(), "CONTROLLER_STALE_RESUME_RECEIPT_PRESENT")
    status.update({"state": "STOPPED_RECONCILED", "startup_reconciled": True,
        "current_case_id": None, "unresolved_runner_request_ids": [],
        "post_entry_automatic_replays": 0, "stopped_at_utc": now()})
    write(status_path, status)
    stopped_sha = sha(status_path)
    receipt = {"schema": SCHEMA_CONTROLLER_RESUME, "request_id": controller["request_id"],
        "controller_manifest_sha256": controller["manifest_sha256"], "queue_id": controller["queue_id"],
        "previous_status_sha256": stopped_sha, "resume_generation": int(status.get("resume_generation", 0)) + 1,
        "safe_to_resume": True, "startup_reconciled": True, "current_case_id": None,
        "unresolved_runner_request_ids": [], "post_entry_automatic_replays": 0,
        "runner_request_ids": list(status.get("runner_request_ids", []))}
    if receipt_path.exists():
        need(read(receipt_path) == receipt, "CONTROLLER_RESUME_RECEIPT_CONFLICT")
    else:
        write(receipt_path, receipt)
    return {"status_path": str(status_path), "status_sha256": stopped_sha,
        "resume_receipt_path": str(receipt_path), "resume_receipt_sha256": sha(receipt_path),
        "state": "STOPPED_RECONCILED", "idempotent": False}


def verify_g023_failed_postentry_closeout(row, cid):
    """Verify the single immutable G023 post-entry closeout receipt."""
    expected = G023_POSTENTRY_AUTHORITY
    need(cid == expected["case_id"], "UNAUTHORIZED_G023_POSTENTRY_CASE:" + str(cid))
    target = {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]}
    need(isinstance(row, dict) and {k: row.get(k) for k in target} == target,
         "G023_POSTENTRY_IDENTITY_MISMATCH")
    reported = Path(row.get("run_dir", ""))
    run_dir = reported.resolve()
    expected_dir = (RUN_ROOT / "runs" / cid / expected["attempt_id"] / expected["run_id"]).resolve()
    need(not reported.is_symlink() and run_dir == expected_dir and run_dir.is_dir(),
         "G023_POSTENTRY_RUN_DIRECTORY_MISMATCH")
    need(row.get("state") == "FAILED_POSTENTRY" and row.get("solver_invocations") == 1
         and row.get("automatic_replay_count") == 0
         and row.get("postentry_disposition_sha256") == expected["disposition_sha256"]
         and row.get("postentry_closeout_fence_id") == expected["recovery_fence_id"],
         "G023_POSTENTRY_REGISTRY_STATE_INVALID")

    status_path = run_dir / "status.json"
    status = runner_status(row, cid)
    summary = status.get("postentry_closeout_v1", {})
    need(sha(status_path) == expected["status_sha256"] and status.get("state") == "FAILED_POSTENTRY"
         and status.get("solver_entered") is True and status.get("solver_invocations") == 1
         and status.get("failure") == "ORPHAN_POSTENTRY_NO_TRUTH_EXIT_REASON_UNKNOWN"
         and summary.get("schema") == "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1"
         and summary.get("disposition_sha256") == expected["disposition_sha256"]
         and summary.get("recovery_fence_id") == expected["recovery_fence_id"]
         and summary.get("entry_consumed") is True and summary.get("truth_available") is False
         and summary.get("automatic_replay_count") == 0,
         "G023_POSTENTRY_STATUS_INVALID")

    for marker_path in (RUN_ROOT / "active_run.json", RUN_ROOT / ".runner.lock"):
        if marker_path.exists():
            marker = read(marker_path)
            need(isinstance(marker, dict) and all(isinstance(marker.get(k), str) and marker.get(k)
                 for k in ("case_id", "attempt_id", "run_id")), "G023_CURRENT_SLOT_IDENTITY_INVALID")
            need((marker.get("case_id"), marker.get("attempt_id"), marker.get("run_id")) !=
                 (cid, expected["attempt_id"], expected["run_id"]), "G023_FAILED_RUN_STILL_OWNS_SLOT")

    closeout = run_dir / "postentry_closeout_v1"
    claim_path = closeout / "claim.json"
    disposition_path = closeout / "disposition.json"
    journal_path = closeout / "journal.json"
    receipt_path = closeout / "receipt.json"
    archive_lock_path = closeout / "released_runner.lock"
    archive_active_path = closeout / "released_active_run.json"
    required_files = (claim_path, disposition_path, journal_path, receipt_path,
                      archive_lock_path, archive_active_path)
    need(all(p.is_file() and not p.is_symlink() for p in required_files),
         "G023_POSTENTRY_RECEIPT_ARTIFACT_MISSING")
    need(sha(disposition_path) == expected["disposition_sha256"]
         and sha(journal_path) == expected["journal_sha256"]
         and sha(receipt_path) == expected["receipt_file_sha256"]
         and sha(claim_path) == expected["claim_file_sha256"]
         and sha(archive_lock_path) == expected["runner_lock_archive_sha256"]
         and sha(archive_active_path) == expected["active_marker_archive_sha256"],
         "G023_POSTENTRY_RECEIPT_SHA_MISMATCH")

    claim = read(claim_path)
    claim_body = dict(claim)
    claim_sha = claim_body.pop("claim_sha256", None)
    need(claim.get("schema") == "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1_RECOVERY_FENCE"
         and claim.get("target") == target and claim.get("recovery_fence_id") == expected["recovery_fence_id"]
         and claim_sha == expected["claim_sha256"] == runner_canonical_sha(claim_body),
         "G023_POSTENTRY_CLAIM_INVALID")

    disposition = read(disposition_path)
    truth = disposition.get("truth_evidence", {})
    need(disposition.get("schema") == "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1_DISPOSITION"
         and {k: disposition.get(k) for k in target} == target
         and disposition.get("disposition") == "FAILED_POSTENTRY_NO_TRUTH"
         and disposition.get("claim_sha256") == claim_sha
         and disposition.get("recovery_fence_id") == expected["recovery_fence_id"]
         and disposition.get("entry_consumed") is True and disposition.get("solver_invocations") == 1
         and disposition.get("automatic_replay_count") == 0
         and disposition.get("truth_available") is False and disposition.get("quarantine") is True
         and disposition.get("training_admitted") is False and disposition.get("scientific_valid") is False
         and truth.get("truth_available") is False and truth.get("truth_valid_case") is False
         and truth.get("labels_valid_case") is False and truth.get("candidate_truth_artifacts") == []
         and truth.get("non_coordinate_dataset_paths") == []
         and truth.get("validation_state") == "PENDING" and truth.get("hashes_state") == "PENDING",
         "G023_POSTENTRY_DISPOSITION_INVALID")
    h5_path = run_dir / "run" / "run_output.h5"
    need(h5_path.is_file() and Path(truth.get("h5_path", "")).resolve() == h5_path.resolve()
         and sha(h5_path) == truth.get("h5_sha256")
         and not (run_dir / "truth.h5").exists()
         and read(run_dir / "validation.json") == {"state": "PENDING"}
         and read(run_dir / "hashes.json") == {"state": "PENDING"},
         "G023_POSTENTRY_TRUTH_NOT_QUARANTINED")
    for name in ("INGEST_RESULT_" + cid + "_V1.json", "INGESTED_TRUTH_" + cid + "_V1.npz"):
        need(not (REPORT / name).exists(), "G023_POSTENTRY_LABEL_ARTIFACT_PRESENT")

    journal = read(journal_path)
    need(journal.get("schema") == "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1_HASH_CHAIN"
         and journal.get("claim_sha256") == claim_sha, "G023_POSTENTRY_JOURNAL_IDENTITY_INVALID")
    records = journal.get("records")
    need(isinstance(records, list) and tuple(r.get("event") for r in records) == FAILED_POSTENTRY_EVENT_ORDER,
         "G023_POSTENTRY_JOURNAL_EVENT_ORDER_INVALID")
    previous = None
    for sequence, record in enumerate(records, 1):
        body = dict(record)
        saved = body.pop("record_sha256", None)
        need(record.get("sequence") == sequence and record.get("previous_record_sha256") == previous
             and saved == runner_canonical_sha(body), "G023_POSTENTRY_JOURNAL_CHAIN_INVALID")
        previous = saved
    need(journal.get("chain_head_sha256") == previous, "G023_POSTENTRY_JOURNAL_HEAD_INVALID")
    events = {r["event"]: r.get("payload", {}) for r in records}
    need(events["DISPOSITION_WRITTEN"].get("disposition_sha256") == expected["disposition_sha256"]
         and events["DISPOSITION_WRITTEN"].get("recovery_fence_id") == expected["recovery_fence_id"]
         and events["STATUS_TERMINALIZED"].get("status_sha256") == expected["status_sha256"]
         and events["STATUS_TERMINALIZED"].get("solver_invocations") == 1
         and events["STATUS_TERMINALIZED"].get("automatic_replay_count") == 0,
         "G023_POSTENTRY_JOURNAL_STATUS_LINK_INVALID")
    registry_event = events["REGISTRY_TERMINALIZED"]
    release = events["RELEASE_READY"]
    need(registry_event.get("registry_sha256") == expected["registry_sha256"]
         and registry_event.get("disposition_sha256") == expected["disposition_sha256"]
         and registry_event.get("solver_invocations") == 1
         and registry_event.get("automatic_replay_count") == 0
         and release.get("identity") == target
         and release.get("control_snapshot", {}).get("health_status") == "PASS"
         and release.get("control_snapshot", {}).get("new_entry_hold") == 0
         and release.get("control_snapshot", {}).get("active_hold_count") == 0
         and release.get("process_snapshot", {}).get("available") is True
         and release.get("process_snapshot", {}).get("live_related") == []
         and release.get("truth_snapshot", {}).get("truth_available") is False,
         "G023_POSTENTRY_RELEASE_EVIDENCE_INVALID")
    need(events["ACTIVE_MARKER_RELEASED"].get("marker") == "active_run.json"
         and events["ACTIVE_MARKER_RELEASED"].get("result") == "ARCHIVED"
         and events["LOCK_RELEASED"].get("marker") == ".runner.lock"
         and events["LOCK_RELEASED"].get("result") == "ARCHIVED"
         and events["LOCK_RELEASED"].get("registry_target_state") == "FAILED_POSTENTRY"
         and events["LOCK_RELEASED"].get("solver_entry_count") == 1
         and events["LOCK_RELEASED"].get("automatic_replay_count") == 0
         and events["LOCK_RELEASED"].get("status_sha256") == expected["status_sha256"],
         "G023_POSTENTRY_SLOT_RELEASE_INVALID")

    receipt = read(receipt_path)
    receipt_body = dict(receipt)
    saved_receipt_sha = receipt_body.pop("receipt_sha256", None)
    need(saved_receipt_sha == expected["receipt_sha256"] == runner_canonical_sha(receipt_body)
         and receipt.get("schema") == "APCD_GPU_RUNNER_G023_POSTENTRY_CLOSEOUT_V1_RECEIPT"
         and receipt.get("result") == "CLOSED" and receipt.get("disposition") == "FAILED_POSTENTRY_NO_TRUTH"
         and {k: receipt.get(k) for k in target} == target
         and receipt.get("disposition_sha256") == expected["disposition_sha256"]
         and receipt.get("journal_sha256") == expected["journal_sha256"]
         and receipt.get("status_sha256") == expected["status_sha256"]
         and receipt.get("registry_sha256") == expected["registry_sha256"]
         and receipt.get("recovery_fence_id") == expected["recovery_fence_id"]
         and receipt.get("coupling_ledger_sha256") == expected["ledger_sha256"]
         and receipt.get("solver_entry_count") == 1 and receipt.get("solver_invocations") == 1
         and receipt.get("automatic_replay_count") == 0 and receipt.get("truth_available") is False
         and receipt.get("training_admitted") is False and receipt.get("scientific_valid") is False,
         "G023_POSTENTRY_RECEIPT_CONTENT_INVALID")
    registry_path = RUN_ROOT / "registry.json"
    need(sha(registry_path) == expected["registry_sha256"], "G023_POSTENTRY_REGISTRY_SHA_MISMATCH")
    need(read(QMAN).get("queue_manifest_sha256") == expected["queue_manifest_sha256"]
         and sha(QMAN) == expected["queue_manifest_file_sha256"], "G023_QUEUE_MANIFEST_AUTHORITY_MISMATCH")
    return {
        "case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
        "sequence_index": expected["sequence_index"], "phase": "FAILED_POSTENTRY_NO_TRUTH",
        "entry_consumed": True, "solver_invocations": 1, "automatic_replay_count": 0,
        "truth_available": False, "quarantine": True,
        "postentry_disposition_path": str(disposition_path),
        "postentry_disposition_sha256": expected["disposition_sha256"],
        "postentry_receipt_path": str(receipt_path), "postentry_receipt_file_sha256": expected["receipt_file_sha256"],
        "postentry_receipt_sha256": expected["receipt_sha256"],
        "postentry_journal_path": str(journal_path), "postentry_journal_sha256": expected["journal_sha256"],
        "postentry_claim_sha256": expected["claim_sha256"],
        "runner_registry_sha256": expected["registry_sha256"],
        "recovery_fence_id": expected["recovery_fence_id"],
        "runner_status_sha256": expected["status_sha256"], "runner_slot_released": True,
    }


def verify_failed_postentry_closeout(row, cid):
    """Allow only the fixed, separately-authorized Runner post-entry closeouts."""
    if cid == G023_POSTENTRY_AUTHORITY["case_id"]:
        return verify_g023_failed_postentry_closeout(row, cid)
    expected = FAILED_POSTENTRY_AUTHORITY
    need(cid == expected["case_id"], "UNAUTHORIZED_FAILED_POSTENTRY_CASE:" + str(cid))
    need(isinstance(row, dict) and row.get("case_id") == cid
         and row.get("attempt_id") == expected["attempt_id"]
         and row.get("run_id") == expected["run_id"], "FAILED_POSTENTRY_IDENTITY_MISMATCH:" + cid)
    reported_run_dir = Path(row.get("run_dir", ""))
    run_dir = reported_run_dir.resolve()
    expected_dir = (RUN_ROOT / "runs" / cid / expected["attempt_id"] / expected["run_id"]).resolve()
    need(not reported_run_dir.is_symlink() and run_dir == expected_dir and run_dir.is_dir(),
         "FAILED_POSTENTRY_RUN_DIRECTORY_MISMATCH:" + cid)
    need(row.get("state") == "FAILED_POSTENTRY" and row.get("solver_invocations") == 1
         and row.get("automatic_replay_count") == 0, "FAILED_POSTENTRY_REGISTRY_STATE_INVALID:" + cid)
    status_path = run_dir / "status.json"
    status = runner_status(row, cid)
    need(status.get("state") == "FAILED_POSTENTRY" and status.get("solver_entered") is True
         and status.get("solver_invocations") == 1
         and status.get("failure") == "ORPHAN_POSTENTRY_NO_TRUTH_EXIT_REASON_UNKNOWN",
         "FAILED_POSTENTRY_STATUS_INVALID:" + cid)
    fence = expected["recovery_fence_id"]
    summary = status.get("postentry_closeout_v1", {})
    need(summary.get("schema") == "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1"
         and summary.get("disposition_sha256") == expected["disposition_sha256"]
         and summary.get("recovery_fence_id") == fence and summary.get("entry_consumed") is True
         and summary.get("truth_available") is False and summary.get("automatic_replay_count") == 0
         and row.get("postentry_disposition_sha256") == expected["disposition_sha256"]
         and row.get("postentry_closeout_fence_id") == fence,
         "FAILED_POSTENTRY_STATUS_REGISTRY_CLOSEOUT_MISMATCH:" + cid)
    current_markers = []
    for marker_path in (RUN_ROOT / "active_run.json", RUN_ROOT / ".runner.lock"):
        if marker_path.exists():
            marker = read(marker_path)
            need(isinstance(marker, dict) and all(isinstance(marker.get(k), str) and marker.get(k)
                 for k in ("case_id", "attempt_id", "run_id")),
                 "FAILED_POSTENTRY_CURRENT_SLOT_IDENTITY_INVALID:" + cid)
            need(marker.get("case_id") != cid and marker.get("run_id") != expected["run_id"],
                 "FAILED_POSTENTRY_CURRENT_SLOT_STILL_POINTS_TO_FAILED_RUN:" + cid)
            current_markers.append(tuple(marker[k] for k in ("case_id", "attempt_id", "run_id")))
    need(len(set(current_markers)) <= 1, "FAILED_POSTENTRY_CURRENT_SLOT_MARKERS_DISAGREE:" + cid)
    closeout_dir = run_dir / "postentry_closeout_v1"
    claim_path, disposition_path, journal_path = (closeout_dir / n for n in ("claim.json", "disposition.json", "journal.json"))
    need(all(p.is_file() and not p.is_symlink() for p in (claim_path, disposition_path, journal_path)),
         "FAILED_POSTENTRY_CLOSEOUT_ARTIFACT_MISSING:" + cid)
    need(sha(disposition_path) == expected["disposition_sha256"]
         and sha(journal_path) == expected["journal_sha256"], "FAILED_POSTENTRY_CLOSEOUT_FILE_SHA_MISMATCH:" + cid)
    target = {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]}
    claim = read(claim_path); claim_body = dict(claim); claim_sha = claim_body.pop("claim_sha256", None)
    need(claim.get("schema") == "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_RECOVERY_FENCE"
         and claim.get("target") == target and claim.get("recovery_fence_id") == fence
         and claim_sha == expected["claim_sha256"] == runner_canonical_sha(claim_body),
         "FAILED_POSTENTRY_CLAIM_HASH_OR_IDENTITY_INVALID:" + cid)
    disposition = read(disposition_path); truth = disposition.get("truth_evidence", {})
    need(disposition.get("schema") == "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_DISPOSITION"
         and {k: disposition.get(k) for k in ("case_id", "attempt_id", "run_id")} == target
         and disposition.get("disposition") == "FAILED_POSTENTRY_NO_TRUTH"
         and disposition.get("claim_sha256") == claim_sha and disposition.get("recovery_fence_id") == fence
         and disposition.get("entry_consumed") is True and disposition.get("solver_invocations") == 1
         and disposition.get("automatic_replay_count") == 0 and disposition.get("truth_available") is False
         and disposition.get("training_admitted") is False and disposition.get("scientific_valid") is False
         and truth.get("truth_available") is False and truth.get("truth_valid_case") is False
         and truth.get("labels_valid_case") is False and truth.get("validation_state") == "PENDING"
         and truth.get("hashes_state") == "PENDING" and truth.get("candidate_truth_artifacts") == []
         and truth.get("non_coordinate_dataset_paths") == []
         and claim.get("input_hashes") == disposition.get("input_hashes"),
         "FAILED_POSTENTRY_DISPOSITION_CONTENT_INVALID:" + cid)
    h5_path = run_dir / "run" / "run_output.h5"
    need(h5_path.is_file() and Path(truth.get("h5_path", "")).resolve() == h5_path.resolve()
         and sha(h5_path) == truth.get("h5_sha256"), "FAILED_POSTENTRY_TRUTH_PROBE_HASH_MISMATCH:" + cid)
    need(not (run_dir / "truth.h5").exists()
         and read(run_dir / "validation.json") == {"state": "PENDING"}
         and read(run_dir / "hashes.json") == {"state": "PENDING"}, "FAILED_POSTENTRY_TRUTH_NOT_ISOLATED:" + cid)
    for name in ("INGEST_RESULT_" + cid + "_V1.json", "INGESTED_TRUTH_" + cid + "_V1.npz"):
        need(not (REPORT / name).exists(), "FAILED_POSTENTRY_LABEL_ARTIFACT_PRESENT:" + cid)
    journal = read(journal_path)
    need(journal.get("schema") == "APCD_GPU_RUNNER_D6_M05_ORPHAN_CLOSEOUT_V1_HASH_CHAIN"
         and journal.get("claim_sha256") == claim_sha, "FAILED_POSTENTRY_JOURNAL_IDENTITY_INVALID:" + cid)
    records = journal.get("records")
    need(isinstance(records, list) and tuple(x.get("event") for x in records) == FAILED_POSTENTRY_EVENT_ORDER,
         "FAILED_POSTENTRY_JOURNAL_EVENT_ORDER_INVALID:" + cid)
    previous = None
    for seq, record in enumerate(records, 1):
        body = dict(record); saved = body.pop("record_sha256", None)
        need(record.get("sequence") == seq and record.get("previous_record_sha256") == previous
             and saved == runner_canonical_sha(body), "FAILED_POSTENTRY_JOURNAL_CHAIN_INVALID:" + cid)
        previous = saved
    need(journal.get("chain_head_sha256") == previous, "FAILED_POSTENTRY_JOURNAL_HEAD_INVALID:" + cid)
    events = {x["event"]: x.get("payload", {}) for x in records}
    status_sha = sha(status_path); release = events["RELEASE_READY"]
    need(events["DISPOSITION_WRITTEN"].get("disposition_sha256") == expected["disposition_sha256"]
         and events["DISPOSITION_WRITTEN"].get("recovery_fence_id") == fence
         and events["STATUS_TERMINALIZED"].get("status_sha256") == status_sha
         and events["STATUS_TERMINALIZED"].get("disposition_sha256") == expected["disposition_sha256"]
         and events["STATUS_TERMINALIZED"].get("solver_invocations") == 1
         and events["STATUS_TERMINALIZED"].get("automatic_replay_count") == 0,
         "FAILED_POSTENTRY_JOURNAL_STATUS_LINK_INVALID:" + cid)
    registry_terminal = events["REGISTRY_TERMINALIZED"]
    need(registry_terminal.get("disposition_sha256") == expected["disposition_sha256"]
         and registry_terminal.get("solver_invocations") == 1
         and registry_terminal.get("automatic_replay_count") == 0
         and release.get("identity") == target
         and release.get("control_snapshot", {}).get("health_status") == "PASS"
         and release.get("control_snapshot", {}).get("new_entry_hold") == 0
         and release.get("control_snapshot", {}).get("active_hold_count") == 0
         and release.get("process_snapshot", {}).get("available") is True
         and release.get("process_snapshot", {}).get("live_related") == []
         and release.get("truth_snapshot", {}).get("truth_available") is False,
         "FAILED_POSTENTRY_RELEASE_EVIDENCE_INVALID:" + cid)
    need(events["ACTIVE_MARKER_RELEASED"].get("marker") == "active_run.json"
         and events["ACTIVE_MARKER_RELEASED"].get("result") == "ARCHIVED"
         and events["LOCK_RELEASED"].get("marker") == ".runner.lock"
         and events["LOCK_RELEASED"].get("result") == "ARCHIVED"
         and events["LOCK_RELEASED"].get("registry_target_state") == "FAILED_POSTENTRY"
         and events["LOCK_RELEASED"].get("solver_entry_count") == 1
         and events["LOCK_RELEASED"].get("automatic_replay_count") == 0
         and events["LOCK_RELEASED"].get("status_sha256") == status_sha,
         "FAILED_POSTENTRY_SLOT_RELEASE_JOURNAL_INVALID:" + cid)
    return {
        "case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
        "phase": "FAILED_POSTENTRY_NO_TRUTH", "entry_consumed": True, "solver_invocations": 1,
        "automatic_replay_count": 0, "truth_available": False,
        "postentry_disposition_path": str(disposition_path),
        "postentry_disposition_sha256": expected["disposition_sha256"],
        "postentry_journal_path": str(journal_path), "postentry_journal_sha256": expected["journal_sha256"],
        "postentry_claim_sha256": claim_sha, "recovery_fence_id": fence,
        "runner_status_sha256": status_sha, "runner_slot_released": True,
    }


def _assert_failed_postentry_recorded(ledger, evidence):
    cid = evidence["case_id"]; record = ledger.get("case_records", {}).get(cid)
    need(isinstance(record, dict) and record.get("phase") == "FAILED_POSTENTRY_NO_TRUTH"
         and record.get("run_id") == evidence["run_id"] and record.get("entry_consumed") is True
         and record.get("postentry_closeout_evidence") == evidence,
         "FAILED_POSTENTRY_LEDGER_RECORD_MISSING_OR_MISMATCH:" + cid)
    need(cid in ledger.get("entered_case_ids", []) and cid not in ledger.get("truth_valid_case_ids", [])
         and cid not in ledger.get("labels_valid_case_ids", []), "FAILED_POSTENTRY_LEDGER_MEMBERSHIP_INVALID:" + cid)
    matches = [x for x in ledger.get("failed_or_isolated_cases", [])
               if isinstance(x, dict) and x.get("case_id") == cid]
    need(len(matches) == 1 and matches[0].get("run_id") == evidence["run_id"]
         and matches[0].get("phase") == evidence["phase"]
         and matches[0].get("entry_consumed") is True
         and matches[0].get("solver_invocations") == 1
         and matches[0].get("automatic_replay_count") == 0
         and matches[0].get("truth_available") is False
         and matches[0].get("postentry_disposition_sha256") == evidence["postentry_disposition_sha256"]
         and matches[0].get("postentry_journal_sha256") == evidence["postentry_journal_sha256"]
         and matches[0].get("recovery_fence_id") == evidence["recovery_fence_id"],
         "FAILED_POSTENTRY_ISOLATION_RECORD_MISSING_OR_MISMATCH:" + cid)


def record_failed_postentry_recovery(ledger, current, evidence):
    cid = evidence["case_id"]; expected = FAILED_POSTENTRY_AUTHORITY
    need(cid == expected["case_id"] and current.get("case_id") == cid
         and current.get("run_id") == evidence["run_id"] == expected["run_id"]
         and current.get("sequence_index") == 11 and current.get("phase") == "RUN_ONE_IN_PROGRESS",
         "FAILED_POSTENTRY_CURRENT_CASE_IDENTITY_MISMATCH:" + cid)
    records = ledger.get("case_records")
    need(isinstance(records, dict) and isinstance(records.get(cid), dict), "FAILED_POSTENTRY_CASE_RECORD_MISSING:" + cid)
    record = records[cid]
    need(record.get("run_id") == evidence["run_id"]
         and record.get("sequence_index") == current.get("sequence_index")
         and record.get("phase") == "RUN_ONE_IN_PROGRESS", "FAILED_POSTENTRY_CASE_RECORD_IDENTITY_MISMATCH:" + cid)
    need(ledger.get("entered_count") == 11 and ledger.get("truth_valid_count") == 10
         and ledger.get("labels_valid_count") == 10 and ledger.get("automatic_replay_count") == 0
         and ledger.get("training_fits") == 0 and ledger.get("p_scale_fits") == 0
         and ledger.get("confirmation_response_access_count") == 0,
         "FAILED_POSTENTRY_LEDGER_COUNTERS_MISMATCH:" + cid)
    need(cid not in ledger.get("truth_valid_case_ids", []) and cid not in ledger.get("labels_valid_case_ids", []),
         "FAILED_POSTENTRY_ALREADY_HAS_TRUTH_OR_LABELS:" + cid)
    existing = [x for x in ledger.get("failed_or_isolated_cases", [])
                if isinstance(x, dict) and x.get("case_id") == cid]
    need(len(existing) <= 1, "FAILED_POSTENTRY_DUPLICATE_ISOLATION_RECORD:" + cid)
    if existing:
        need(existing[0].get("run_id") == evidence["run_id"]
             and existing[0].get("postentry_disposition_sha256") == evidence["postentry_disposition_sha256"]
             and existing[0].get("postentry_journal_sha256") == evidence["postentry_journal_sha256"]
             and existing[0].get("recovery_fence_id") == evidence["recovery_fence_id"],
             "FAILED_POSTENTRY_EXISTING_ISOLATION_MISMATCH:" + cid)
    else:
        ledger.setdefault("failed_or_isolated_cases", []).append({
            "case_id": cid, "attempt_id": evidence["attempt_id"], "run_id": evidence["run_id"],
            "sequence_index": current["sequence_index"], "phase": evidence["phase"],
            "entry_consumed": True, "solver_invocations": 1, "automatic_replay_count": 0,
            "truth_available": False, "postentry_disposition_sha256": evidence["postentry_disposition_sha256"],
            "postentry_journal_sha256": evidence["postentry_journal_sha256"],
            "recovery_fence_id": evidence["recovery_fence_id"], "recorded_at_utc": now(),
        })
    record.update({"phase": evidence["phase"], "entry_consumed": True,
                   "postentry_closeout_evidence": evidence, "runner_status_sha256": evidence["runner_status_sha256"],
                   "postentry_disposition_sha256": evidence["postentry_disposition_sha256"],
                   "postentry_journal_sha256": evidence["postentry_journal_sha256"],
                   "recovery_fence_id": evidence["recovery_fence_id"], "truth_available": False,
                   "automatic_replay_count": 0, "terminalized_at_utc": now()})
    ledger["current_case"] = None


def record_g023_failed_postentry_recovery(ledger, current, evidence):
    """Record the single G023 consumed entry without changing any success counts."""
    expected = G023_POSTENTRY_AUTHORITY
    cid = expected["case_id"]
    need(evidence.get("case_id") == cid and evidence.get("run_id") == expected["run_id"]
         and evidence.get("entry_consumed") is True and evidence.get("solver_invocations") == 1
         and evidence.get("automatic_replay_count") == 0 and evidence.get("truth_available") is False
         and evidence.get("quarantine") is True,
         "G023_POSTENTRY_EVIDENCE_IDENTITY_INVALID")
    need(isinstance(current, dict) and current.get("case_id") == cid
         and current.get("run_id") == expected["run_id"]
         and current.get("sequence_index") == expected["sequence_index"]
         and current.get("phase") == "RUN_ONE_IN_PROGRESS",
         "G023_POSTENTRY_CURRENT_CASE_IDENTITY_MISMATCH")
    need(ledger.get("entered_count") == 35 and ledger.get("truth_valid_count") == 33
         and ledger.get("labels_valid_count") == 33
         and ledger.get("remaining_unentered_count") == 93
         and ledger.get("automatic_replay_count") == 0
         and ledger.get("training_fits") == 0 and ledger.get("p_scale_fits") == 0
         and ledger.get("confirmation_response_access_count") == 0,
         "G023_POSTENTRY_LEDGER_COUNTERS_MISMATCH")
    need(cid in ledger.get("entered_case_ids", [])
         and cid not in ledger.get("truth_valid_case_ids", [])
         and cid not in ledger.get("labels_valid_case_ids", [])
         and cid not in ledger.get("remaining_unentered_case_ids", []),
         "G023_POSTENTRY_LEDGER_MEMBERSHIP_INVALID")
    records = ledger.get("case_records")
    need(isinstance(records, dict) and isinstance(records.get(cid), dict),
         "G023_POSTENTRY_CASE_RECORD_MISSING")
    record = records[cid]
    need(record.get("attempt_id") == expected["attempt_id"]
         and record.get("run_id") == expected["run_id"]
         and record.get("sequence_index") == expected["sequence_index"]
         and record.get("phase") == "RUN_ONE_IN_PROGRESS"
         and record.get("run_envelope_sha256") == "759bffbf50bf29a154d9e4d4c54b0a87cbb4494c40fb764be3e3f79abd2581f2",
         "G023_POSTENTRY_CASE_RECORD_IDENTITY_MISMATCH")
    existing = [item for item in ledger.get("failed_or_isolated_cases", [])
                if isinstance(item, dict) and item.get("case_id") == cid]
    need(len(existing) <= 1, "G023_POSTENTRY_DUPLICATE_ISOLATION_RECORD")
    if existing:
        need(existing[0].get("run_id") == expected["run_id"]
             and existing[0].get("phase") == evidence["phase"]
             and existing[0].get("postentry_disposition_sha256") == evidence["postentry_disposition_sha256"]
             and existing[0].get("postentry_journal_sha256") == evidence["postentry_journal_sha256"]
             and existing[0].get("recovery_fence_id") == evidence["recovery_fence_id"],
             "G023_POSTENTRY_EXISTING_ISOLATION_MISMATCH")
    else:
        ledger.setdefault("failed_or_isolated_cases", []).append({
            "case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
            "sequence_index": expected["sequence_index"], "phase": evidence["phase"],
            "entry_consumed": True, "solver_invocations": 1, "automatic_replay_count": 0,
            "truth_available": False, "postentry_disposition_sha256": evidence["postentry_disposition_sha256"],
            "postentry_journal_sha256": evidence["postentry_journal_sha256"],
            "recovery_fence_id": evidence["recovery_fence_id"], "recorded_at_utc": now(),
        })
    record.update({"phase": evidence["phase"], "entry_consumed": True,
        "postentry_closeout_evidence": evidence, "runner_status_sha256": evidence["runner_status_sha256"],
        "postentry_disposition_sha256": evidence["postentry_disposition_sha256"],
        "postentry_journal_sha256": evidence["postentry_journal_sha256"],
        "recovery_fence_id": evidence["recovery_fence_id"], "truth_available": False,
        "automatic_replay_count": 0, "terminalized_at_utc": now()})
    ledger["current_case"] = None



def verify_preentry_case_label_binding(cid, attempt_id, failed_run_id, fresh_success_row=None):
    result_path = REPORT / ("INGEST_RESULT_" + cid + "_V1.json")
    label_path = REPORT / ("INGESTED_TRUTH_" + cid + "_V1.npz")
    result_exists, label_exists = result_path.exists(), label_path.exists()
    if not result_exists and not label_exists:
        return None
    need(result_exists and label_exists, "FAILED_PREENTRY_LABEL_PAIR_INCOMPLETE:" + cid)
    need(not result_path.is_symlink() and not label_path.is_symlink(),
         "FAILED_PREENTRY_LABEL_SYMLINK:" + cid)
    need(isinstance(fresh_success_row, dict), "FAILED_PREENTRY_LABEL_WITHOUT_FRESH_RUN:" + cid)
    run_id = fresh_success_row.get("run_id")
    need(fresh_success_row.get("case_id") == cid
         and fresh_success_row.get("attempt_id") == attempt_id
         and isinstance(run_id, str) and run_id and run_id != failed_run_id
         and fresh_success_row.get("state") in (None, "DONE"),
         "FAILED_PREENTRY_LABEL_RUN_ID_MISMATCH:" + cid)
    run_dir = Path(fresh_success_row.get("run_dir", ""))
    expected_dir = RUN_ROOT / "runs" / cid / attempt_id / run_id
    need(not run_dir.is_symlink() and run_dir.resolve() == expected_dir.resolve() and run_dir.is_dir(),
         "FAILED_PREENTRY_LABEL_RUN_DIRECTORY_MISMATCH:" + cid)
    manifest_path, status_path = run_dir / "manifest.json", run_dir / "status.json"
    validation_path, hashes_path = run_dir / "validation.json", run_dir / "hashes.json"
    truth_path, fsp_path = run_dir / "truth.h5", run_dir / "run.fsp"
    needed = (manifest_path, status_path, validation_path, hashes_path, truth_path, fsp_path)
    need(all(p.is_file() and not p.is_symlink() for p in needed),
         "FAILED_PREENTRY_LABEL_RUN_ARTIFACT_MISSING:" + cid)
    manifest, status = read(manifest_path), runner_status(fresh_success_row, cid)
    validation, hashes = read(validation_path), read(hashes_path)
    identity = {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id}
    need({k: manifest.get(k) for k in identity} == identity
         and {k: status.get(k) for k in identity} == identity
         and status.get("state") == "DONE" and status.get("solver_entered") is True
         and status.get("solver_invocations") == 1 and status.get("replay_count", 0) == 0,
         "FAILED_PREENTRY_LABEL_RUN_STATUS_MISMATCH:" + cid)
    need(all(validation.get(k) is True for k in
             ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid"))
         and validation.get("run_id") == run_id
         and Path(validation.get("truth_h5", "")).resolve() == truth_path.resolve(),
         "FAILED_PREENTRY_LABEL_RUN_VALIDATION_MISMATCH:" + cid)
    truth_sha, manifest_sha = sha(truth_path), sha(manifest_path)
    need(validation.get("truth_h5_sha256") == truth_sha
         and validation.get("run_fsp_sha256") == sha(fsp_path)
         and hashes.get("truth_h5_sha256") == truth_sha
         and hashes.get("manifest_sha256") == manifest_sha
         and hashes.get("validation_sha256") == sha(validation_path)
         and hashes.get("run_fsp_sha256") == sha(fsp_path),
         "FAILED_PREENTRY_LABEL_RUN_HASH_MISMATCH:" + cid)
    result = read(result_path)
    label_sha = sha(label_path)
    need(result.get("schema") == "COUPLING_K6_V2_DEVELOPMENT_CASE_INGEST_RESULT_V1"
         and {k: result.get(k) for k in identity} == identity
         and result.get("status") == "PASS" and result.get("solver_entered") is True
         and result.get("solver_invocations") == 1 and result.get("replay_count") == 0,
         "FAILED_PREENTRY_LABEL_RESULT_IDENTITY_MISMATCH:" + cid)
    inputs = result.get("input_artifacts", {})
    provenance = result.get("truth_provenance", {})
    need({k: inputs.get(k) for k in ("case_id", "attempt_id")} ==
         {"case_id": cid, "attempt_id": attempt_id}
         and inputs.get("status") == "DONE" and inputs.get("solver_invocations") == 1
         and inputs.get("replay_count") == 0,
         "FAILED_PREENTRY_LABEL_INPUT_IDENTITY_MISMATCH:" + cid)
    source = inputs.get("source_manifest", {})
    need(Path(source.get("path", "")).resolve() == manifest_path.resolve()
         and source.get("sha256") == manifest_sha
         and provenance.get("source_manifest_sha256") == manifest_sha,
         "FAILED_PREENTRY_LABEL_SOURCE_MANIFEST_MISMATCH:" + cid)
    contract_sha = manifest.get("physical_contract_sha256")
    need(isinstance(contract_sha, str) and inputs.get("physical_contract_sha256") == contract_sha
         and provenance.get("physical_contract_sha256") == contract_sha,
         "FAILED_PREENTRY_LABEL_CONTRACT_PROVENANCE_MISMATCH:" + cid)
    truth_input = inputs.get("truth_h5", {})
    need(Path(truth_input.get("path", "")).resolve() == truth_path.resolve()
         and truth_input.get("sha256") == truth_sha,
         "FAILED_PREENTRY_LABEL_TRUTH_SOURCE_MISMATCH:" + cid)
    truth_artifact = result.get("truth_artifact", {})
    need(Path(truth_artifact.get("path", "")).resolve() == label_path.resolve()
         and truth_artifact.get("sha256") == label_sha,
         "FAILED_PREENTRY_LABEL_TRUTH_SHA_MISMATCH:" + cid)
    expected_provenance = {
        "orders_sha256": "orders_json", "raw_metadata_sha256": "raw_metadata",
        "raw_npz_sha256": "raw_npz", "state_metadata_sha256": "state_metadata",
        "state_npz_sha256": "state_npz",
    }
    for provenance_key, input_key in expected_provenance.items():
        descriptor = inputs.get(input_key)
        recorded = provenance.get(provenance_key)
        if recorded is None and descriptor is None:
            continue
        need(isinstance(descriptor, dict) and descriptor.get("sha256") == recorded,
             "FAILED_PREENTRY_LABEL_PROVENANCE_MISMATCH:" + cid + ":" + provenance_key)
        artifact_path = Path(descriptor.get("path", ""))
        try:
            artifact_path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            need(False, "FAILED_PREENTRY_LABEL_PROVENANCE_PATH_MISMATCH:" + cid + ":" + input_key)
        need(artifact_path.is_file() and not artifact_path.is_symlink()
             and sha(artifact_path) == recorded,
             "FAILED_PREENTRY_LABEL_PROVENANCE_HASH_MISMATCH:" + cid + ":" + input_key)
    return {"case_id": cid, "attempt_id": attempt_id, "run_id": run_id,
        "truth_h5_sha256": truth_sha, "source_manifest_sha256": manifest_sha,
        "label_sha256": label_sha}


def verify_failed_preentry_recovery(row, cid, require_slot_free=False, fresh_success_row=None):
    expected = FAILED_PREENTRY_AUTHORITY
    need(cid == expected["case_id"], "UNAUTHORIZED_FAILED_PREENTRY_CASE:" + str(cid))
    need(isinstance(row, dict) and row.get("case_id") == cid
         and row.get("attempt_id") == expected["attempt_id"]
         and row.get("run_id") == expected["run_id"],
         "FAILED_PREENTRY_IDENTITY_MISMATCH:" + cid)
    reported = Path(row.get("run_dir", ""))
    run_dir = reported.resolve()
    expected_dir = (RUN_ROOT / "runs" / cid / expected["attempt_id"] / expected["run_id"]).resolve()
    need(not reported.is_symlink() and run_dir == expected_dir and run_dir.is_dir(),
         "FAILED_PREENTRY_RUN_DIRECTORY_MISMATCH:" + cid)
    need(row.get("state") == "FAILED_PREENTRY" and row.get("solver_entered") is False
         and row.get("solver_invocations") == 0 and row.get("automatic_replay_count") == 0,
         "FAILED_PREENTRY_REGISTRY_STATE_INVALID:" + cid)
    status_path = run_dir / "status.json"
    status = runner_status(row, cid)
    need(status.get("state") == "FAILED_PREENTRY" and status.get("solver_entered") is False
         and status.get("solver_invocations") == 0 and status.get("automatic_replay_count") == 0
         and status.get("failure") == "ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY"
         and status.get("preentry_recovery_claim_sha256") == expected["claim_sha256"]
         and status.get("preentry_recovery_disposition_sha256") == expected["disposition_sha256"]
         and status.get("preentry_recovery_fence_sha256") == expected["fence_sha256"]
         and sha(status_path) == expected["status_sha256"],
         "FAILED_PREENTRY_STATUS_INVALID:" + cid)
    need(row.get("preentry_recovery_disposition_sha256") == expected["disposition_sha256"]
         and row.get("preentry_recovery_fence_sha256") == expected["fence_sha256"],
         "FAILED_PREENTRY_REGISTRY_CLOSEOUT_MISMATCH:" + cid)
    manifest_path = run_dir / "manifest.json"
    need(manifest_path.is_file() and not manifest_path.is_symlink()
         and sha(manifest_path) == expected["manifest_sha256"],
         "FAILED_PREENTRY_MANIFEST_SHA_MISMATCH:" + cid)
    manifest = read(manifest_path)
    need({k: manifest.get(k) for k in ("case_id", "attempt_id", "run_id")} ==
         {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]},
         "FAILED_PREENTRY_MANIFEST_IDENTITY_MISMATCH:" + cid)
    recovery = run_dir / "preentry_recovery_v1"
    claim_path, disposition_path, journal_path = (recovery / n for n in
        ("claim.json", "disposition.json", "journal.json"))
    archive_path = recovery / "released_runner.lock"
    need(all(p.is_file() and not p.is_symlink() for p in
             (claim_path, disposition_path, journal_path, archive_path)),
         "FAILED_PREENTRY_RECOVERY_ARTIFACT_MISSING:" + cid)
    need(sha(claim_path) == expected["claim_sha256"]
         and sha(disposition_path) == expected["disposition_sha256"]
         and sha(journal_path) == expected["journal_sha256"]
         and sha(archive_path) == expected["lock_sha256"],
         "FAILED_PREENTRY_RECOVERY_FILE_SHA_MISMATCH:" + cid)
    claim = read(claim_path)
    need(claim.get("schema") == "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_CLAIM_V1"
         and {k: claim.get(k) for k in ("case_id", "attempt_id", "run_id")} ==
         {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]}
         and claim.get("immutable_artifacts") == expected["immutable_artifacts"]
         and claim.get("target_artifacts") == expected["target_artifacts"]
         and claim.get("registry_other_rows_sha256") == expected["registry_other_rows_sha256"],
         "FAILED_PREENTRY_CLAIM_CONTENT_INVALID:" + cid)
    fence_basis = {
        "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_FENCE_BASIS_V1",
        "case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
        "lock_sha256": expected["lock_sha256"], "manifest_sha256": expected["manifest_sha256"],
        "process_census_sha256": expected["process_census_sha256"],
        "registry_sha256": expected["pending_registry_sha256"],
        "status_sha256": expected["pending_status_sha256"],
        "control_snapshot_sha256": expected["control_snapshot_sha256"],
    }
    need(claim.get("fence_basis") == fence_basis
         and claim.get("fence_sha256") == expected["fence_sha256"] == canonical_sha(fence_basis),
         "FAILED_PREENTRY_FENCE_INVALID:" + cid)
    control = claim.get("control_snapshot", {})
    need(control.get("schema") == "APCD_GPU_RUNNER_GLOBAL_ENTRY_HOLD_SNAPSHOT_V1"
         and control.get("result") == "PASS" and control.get("health_status") == "PASS"
         and control.get("new_entry_hold") == 0 and control.get("active_global_hold_ids") == []
         and control.get("control_db_sha256") == expected["control_db_sha256"]
         and control.get("control_generation") == expected["control_generation"]
         and control.get("snapshot_sha256") == expected["control_snapshot_sha256"],
         "FAILED_PREENTRY_CONTROL_SNAPSHOT_INVALID:" + cid)
    process = claim.get("process_snapshot", {})
    need(process.get("lock_pid") == expected["lock_pid"] and process.get("lock_pid_present") is False
         and process.get("target_related_pids") == [] and process.get("descendant_pids") == []
         and process.get("process_census_sha256") == expected["process_census_sha256"],
         "FAILED_PREENTRY_PROCESS_SNAPSHOT_INVALID:" + cid)
    for name, descriptor in expected["immutable_artifacts"].items():
        if name == "ledger" or not isinstance(descriptor, dict) or "path" not in descriptor:
            continue
        artifact = Path(descriptor["path"])
        need(artifact.is_file() and not artifact.is_symlink() and sha(artifact) == descriptor["sha256"],
             "FAILED_PREENTRY_IMMUTABLE_ARTIFACT_MISMATCH:" + name)
    envelope_path = Path(expected["immutable_artifacts"]["envelope"]["path"])
    need(envelope_path.is_file() and sha(envelope_path) == expected["envelope_sha256"],
         "FAILED_PREENTRY_ENVELOPE_SHA_MISMATCH:" + cid)
    envelope = read(envelope_path)
    need({k: envelope.get(k) for k in ("case_id", "attempt_id", "run_id")} ==
         {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]},
         "FAILED_PREENTRY_ENVELOPE_IDENTITY_MISMATCH:" + cid)
    disposition = read(disposition_path)
    need(disposition.get("schema") == "APCD_GPU_RUNNER_V1_P05_ORPHAN_PREENTRY_DISPOSITION_V1"
         and {k: disposition.get(k) for k in ("case_id", "attempt_id", "run_id")} ==
         {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]}
         and disposition.get("result") == "FAILED_PREENTRY"
         and disposition.get("classification") == "ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY"
         and disposition.get("claim_sha256") == expected["claim_sha256"]
         and disposition.get("recovery_fence_sha256") == expected["fence_sha256"]
         and disposition.get("lock_original_sha256") == expected["lock_sha256"]
         and disposition.get("attempt_budget_consumed") is False
         and disposition.get("physical_solver_entry_count") == 0
         and disposition.get("solver_entered") is False
         and disposition.get("solver_invocations") == 0
         and disposition.get("automatic_replay_count") == 0
         and disposition.get("truth_created") is False and disposition.get("truth_valid") is False
         and disposition.get("same_run_id_reuse_supported") is False
         and disposition.get("next_run_policy") ==
             "same case_id and attempt_id may use a new run_id only after Coupling ledger reconciliation and fresh official launch revalidation",
         "FAILED_PREENTRY_DISPOSITION_CONTENT_INVALID:" + cid)
    evidence = disposition.get("evidence", {})
    need(evidence.get("manifest_sha256") == expected["manifest_sha256"]
         and evidence.get("status_sha256_before") == expected["pending_status_sha256"]
         and evidence.get("registry_sha256_before") == expected["pending_registry_sha256"]
         and evidence.get("process_census_sha256") == expected["process_census_sha256"]
         and evidence.get("control_generation") == expected["control_generation"]
         and evidence.get("control_snapshot_sha256") == expected["control_snapshot_sha256"]
         and evidence.get("coupling_artifacts") == expected["immutable_artifacts"],
         "FAILED_PREENTRY_DISPOSITION_EVIDENCE_INVALID:" + cid)
    archive = read(archive_path)
    need(archive == {"pid": expected["lock_pid"], "run_id": expected["run_id"],
                     "case_id": cid, "attempt_id": expected["attempt_id"]},
         "FAILED_PREENTRY_ARCHIVED_LOCK_IDENTITY_INVALID:" + cid)
    for marker_name in ("active_run.json", ".runner.lock"):
        marker_path = RUN_ROOT / marker_name
        if marker_path.exists():
            need(not marker_path.is_symlink(), "FAILED_PREENTRY_CURRENT_MARKER_SYMLINK:" + cid)
            marker = read(marker_path)
            need(isinstance(marker, dict)
                 and all(isinstance(marker.get(k), str) and marker.get(k)
                         for k in ("case_id", "attempt_id", "run_id"))
                 and not (marker.get("case_id") == cid and marker.get("run_id") == expected["run_id"]),
                 "FAILED_PREENTRY_CURRENT_MARKER_STILL_OLD_RUN:" + cid)
            need(not require_slot_free, "FAILED_PREENTRY_CURRENT_SLOT_NOT_FREE:" + cid)
    if require_slot_free:
        need(not (RUN_ROOT / "active_run.json").exists()
             and not (RUN_ROOT / ".runner.lock").exists(), "FAILED_PREENTRY_CURRENT_SLOT_NOT_FREE:" + cid)
    target_paths = {"manifest": manifest_path, "validation": run_dir / "validation.json",
                    "hashes": run_dir / "hashes.json", "solver_log": run_dir / "solver.log"}
    for name, path in target_paths.items():
        need(path.is_file() and sha(path) == expected["target_artifacts"][name],
             "FAILED_PREENTRY_TARGET_ARTIFACT_SHA_MISMATCH:" + name)
    need((run_dir / "solver.log").stat().st_size == 0
         and not (run_dir / "truth.h5").exists() and not (run_dir / "run.fsp").exists()
         and not (run_dir / "run" / "run_output.h5").exists()
         and read(run_dir / "validation.json") == {"state": "PENDING"}
         and read(run_dir / "hashes.json") == {"state": "PENDING"},
         "FAILED_PREENTRY_SOLVER_OR_TRUTH_OUTPUT_PRESENT:" + cid)
    verify_preentry_case_label_binding(cid, expected["attempt_id"], expected["run_id"], fresh_success_row)
    journal = read(journal_path)
    need(journal.get("schema") == "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_JOURNAL_V1"
         and {k: journal.get(k) for k in ("case_id", "attempt_id", "run_id")} ==
         {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"]}
         and journal.get("fence_sha256") == expected["fence_sha256"]
         and isinstance(journal.get("events"), list)
         and tuple(e.get("event_type") for e in journal["events"]) == FAILED_PREENTRY_EVENT_ORDER,
         "FAILED_PREENTRY_JOURNAL_IDENTITY_OR_ORDER_INVALID:" + cid)
    previous = "0" * 64
    for sequence, event in enumerate(journal["events"], 1):
        body = dict(event)
        saved = body.pop("event_sha256", None)
        need(event.get("sequence") == sequence and event.get("previous_event_sha256") == previous
             and saved == canonical_sha(body), "FAILED_PREENTRY_JOURNAL_CHAIN_INVALID:" + cid)
        previous = saved
    events = {e["event_type"]: e.get("details", {}) for e in journal["events"]}
    zero = {"automatic_replay_count": 0, "solver_entered": False, "solver_invocations": 0}
    need(events["CLAIMED"] == {"claim_sha256": expected["claim_sha256"],
         "disposition_sha256": expected["disposition_sha256"], "fence_sha256": expected["fence_sha256"]}
         and all(all(events[x].get(k) == v for k, v in zero.items())
                 and events[x].get("disposition_sha256") == expected["disposition_sha256"]
                 and events[x].get("fence_sha256") == expected["fence_sha256"]
                 for x in ("STATUS_TERMINALIZATION_INTENT", "STATUS_TERMINALIZED",
                           "REGISTRY_TERMINALIZATION_INTENT", "REGISTRY_TERMINALIZED")),
         "FAILED_PREENTRY_JOURNAL_ZERO_ENTRY_LINK_INVALID:" + cid)
    need(events["STATUS_TERMINALIZED"].get("status_sha256") == expected["status_sha256"]
         and events["REGISTRY_TERMINALIZED"].get("registry_sha256") == expected["registry_terminal_sha256"],
         "FAILED_PREENTRY_JOURNAL_TERMINAL_HASH_MISMATCH:" + cid)
    ready = events["RELEASE_READY"]
    need(all(ready.get(k) == v for k, v in zero.items())
         and ready.get("status_sha256") == expected["status_sha256"]
         and ready.get("registry_sha256") == expected["registry_terminal_sha256"]
         and ready.get("lock_archive_path") == str(archive_path),
         "FAILED_PREENTRY_RELEASE_EVIDENCE_INVALID:" + cid)
    intent = events["LOCK_RELEASE_INTENT"]
    need(all(intent.get(k) == v for k, v in zero.items())
         and intent.get("archive_path") == str(archive_path)
         and intent.get("original_lock_sha256") == expected["lock_sha256"],
         "FAILED_PREENTRY_LOCK_RELEASE_EVIDENCE_INVALID:" + cid)
    _, registry = runner_registry()
    matches = [r for r in registry["runs"] if r.get("case_id") == cid
               and r.get("attempt_id") == expected["attempt_id"] and r.get("run_id") == expected["run_id"]]
    need(len(matches) == 1 and matches[0] == row,
         "FAILED_PREENTRY_REGISTRY_ROW_MISSING_OR_MISMATCH:" + cid)
    return {"case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
        "phase": "FAILED_PREENTRY_NO_ENTRY", "entry_consumed": False,
        "solver_invocations": 0, "automatic_replay_count": 0, "truth_available": False,
        "claim_sha256": expected["claim_sha256"], "disposition_sha256": expected["disposition_sha256"],
        "journal_sha256": expected["journal_sha256"], "recovery_fence_sha256": expected["fence_sha256"],
        "archived_lock_sha256": expected["lock_sha256"], "runner_status_sha256": expected["status_sha256"],
        "run_directory": str(run_dir), "runner_slot_released": True}


def _assert_failed_preentry_recorded(ledger, evidence):
    expected = FAILED_PREENTRY_AUTHORITY
    cid = expected["case_id"]
    need(evidence.get("case_id") == cid and evidence.get("run_id") == expected["run_id"]
         and evidence.get("entry_consumed") is False and evidence.get("solver_invocations") == 0
         and evidence.get("automatic_replay_count") == 0 and evidence.get("truth_available") is False,
         "FAILED_PREENTRY_EVIDENCE_IDENTITY_INVALID:" + cid)
    matches = [x for x in ledger.get("failed_or_isolated_cases", [])
               if isinstance(x, dict) and x.get("case_id") == cid and x.get("run_id") == expected["run_id"]]
    need(len(matches) == 1 and matches[0].get("attempt_id") == expected["attempt_id"]
         and matches[0].get("sequence_index") == expected["sequence_index"]
         and matches[0].get("phase") == evidence["phase"]
         and matches[0].get("entry_consumed") is False
         and matches[0].get("solver_invocations") == 0 and matches[0].get("automatic_replay_count") == 0
         and matches[0].get("truth_available") is False
         and matches[0].get("claim_sha256") == expected["claim_sha256"]
         and matches[0].get("disposition_sha256") == expected["disposition_sha256"]
         and matches[0].get("journal_sha256") == expected["journal_sha256"]
         and matches[0].get("recovery_fence_sha256") == expected["fence_sha256"],
         "FAILED_PREENTRY_ISOLATION_RECORD_MISSING_OR_MISMATCH:" + cid)
    need(ledger.get("automatic_replay_count") == 0 and ledger.get("training_fits") == 0
         and ledger.get("p_scale_fits") == 0 and ledger.get("confirmation_response_access_count") == 0,
         "FAILED_PREENTRY_LEDGER_COUNTERS_INVALID:" + cid)
    record = ledger.get("case_records", {}).get(cid)
    need(isinstance(record, dict) and record.get("sequence_index") == expected["sequence_index"],
         "FAILED_PREENTRY_CASE_RECORD_MISSING_OR_MISMATCH:" + cid)
    if record.get("run_id") == expected["run_id"]:
        need(record.get("attempt_id") == expected["attempt_id"]
             and record.get("phase") == "FAILED_PREENTRY_NO_ENTRY"
             and record.get("entry_consumed") is False
             and record.get("preentry_recovery_evidence") == evidence,
             "FAILED_PREENTRY_CASE_RECORD_MISSING_OR_MISMATCH:" + cid)
    else:
        need(record.get("run_id") and record.get("run_id") != expected["run_id"]
             and record.get("attempt_id", expected["attempt_id"]) == expected["attempt_id"]
             and record.get("phase") in {"RUN_ONE_IN_PROGRESS", "TRUTH_DURABLE_SLOT_RELEASED_INGEST_PENDING", "LABEL_PASS"},
             "FAILED_PREENTRY_RETRY_CASE_RECORD_INVALID:" + cid)


def record_failed_preentry_recovery(ledger, current, evidence):
    expected = FAILED_PREENTRY_AUTHORITY
    cid = expected["case_id"]
    need(evidence.get("case_id") == cid and current.get("case_id") == cid
         and current.get("run_id") == expected["run_id"]
         and current.get("sequence_index") == expected["sequence_index"]
         and current.get("phase") == "RUN_ONE_IN_PROGRESS",
         "FAILED_PREENTRY_CURRENT_CASE_IDENTITY_MISMATCH:" + cid)
    need(sha(LEDGER) == expected["ledger_sha256"], "FAILED_PREENTRY_LEDGER_BASELINE_SHA_MISMATCH:" + cid)
    need(ledger.get("queue_manifest_sha256") == expected["queue_manifest_sha256"]
         and ledger.get("authorized_development_case_count") == 128
         and ledger.get("entered_count") == 11 and ledger.get("truth_valid_count") == 10
         and ledger.get("labels_valid_count") == 10 and ledger.get("automatic_replay_count") == 0
         and ledger.get("training_fits") == 0 and ledger.get("p_scale_fits") == 0
         and ledger.get("confirmation_response_access_count") == 0,
         "FAILED_PREENTRY_LEDGER_COUNTERS_MISMATCH:" + cid)
    need(cid not in ledger.get("entered_case_ids", [])
         and cid not in ledger.get("truth_valid_case_ids", [])
         and cid not in ledger.get("labels_valid_case_ids", [])
         and cid in ledger.get("remaining_unentered_case_ids", []),
         "FAILED_PREENTRY_CASE_ALREADY_COUNTED:" + cid)
    need(current.get("run_envelope_sha256") == expected["envelope_sha256"]
         and current.get("run_envelope_path") == expected["immutable_artifacts"]["envelope"]["path"],
         "FAILED_PREENTRY_CURRENT_ENVELOPE_MISMATCH:" + cid)
    record = ledger.get("case_records", {}).get(cid)
    need(isinstance(record, dict) and record.get("run_id") == expected["run_id"]
         and record.get("sequence_index") == expected["sequence_index"]
         and record.get("phase") == "RUN_ONE_IN_PROGRESS"
         and record.get("run_envelope_sha256") == expected["envelope_sha256"],
         "FAILED_PREENTRY_CASE_RECORD_IDENTITY_MISMATCH:" + cid)
    existing = [x for x in ledger.get("failed_or_isolated_cases", [])
                if isinstance(x, dict) and x.get("case_id") == cid]
    need(not existing, "FAILED_PREENTRY_DUPLICATE_ISOLATION_RECORD:" + cid)
    ledger.setdefault("failed_or_isolated_cases", []).append({
        "case_id": cid, "attempt_id": expected["attempt_id"], "run_id": expected["run_id"],
        "sequence_index": expected["sequence_index"], "phase": evidence["phase"],
        "entry_consumed": False, "solver_invocations": 0, "automatic_replay_count": 0,
        "truth_available": False, "claim_sha256": expected["claim_sha256"],
        "disposition_sha256": expected["disposition_sha256"], "journal_sha256": expected["journal_sha256"],
        "recovery_fence_sha256": expected["fence_sha256"], "recorded_at_utc": now(),
    })
    record.update({"attempt_id": expected["attempt_id"], "phase": evidence["phase"],
        "entry_consumed": False, "preentry_recovery_evidence": evidence,
        "runner_status_sha256": expected["status_sha256"], "truth_available": False,
        "automatic_replay_count": 0, "terminalized_at_utc": now()})
    ledger["current_case"] = None


def reconcile_failed_preentry(ledger, batch_status, evidence):
    expected = FAILED_PREENTRY_AUTHORITY
    cid = expected["case_id"]
    current = ledger.get("current_case")
    changed_ledger = False
    if isinstance(current, dict) and current.get("case_id") == cid:
        record_failed_preentry_recovery(ledger, current, evidence)
        changed_ledger = True
    else:
        if isinstance(current, dict) and current.get("case_id") == G023_POSTENTRY_AUTHORITY["case_id"]:
            need(current.get("run_id") == G023_POSTENTRY_AUTHORITY["run_id"]
                 and current.get("sequence_index") == G023_POSTENTRY_AUTHORITY["sequence_index"]
                 and current.get("phase") == "RUN_ONE_IN_PROGRESS",
                 "FAILED_PREENTRY_OTHER_CURRENT_CASE_PRESENT")
        else:
            need(current is None, "FAILED_PREENTRY_OTHER_CURRENT_CASE_PRESENT")
        _assert_failed_preentry_recorded(ledger, evidence)
    batch_current = batch_status.get("current_case")
    changed_status = False
    if isinstance(batch_current, dict) and batch_current.get("case_id") == cid:
        need(batch_current.get("sequence_index") == expected["sequence_index"]
             and batch_current.get("phase") in {"ENSURE_CURRENT_ROUTE_AND_PREFLIGHT", "LIVE_ENTRY_GATE", "RUN_ONE_IN_PROGRESS"}
             and batch_current.get("run_id") in (None, expected["run_id"]),
             "FAILED_PREENTRY_BATCH_POINTER_MISMATCH:" + cid)
        batch_status["current_case"] = None
        batch_status["queue_phase"] = "QUEUE_ACTIVE"
        batch_status["last_updated_utc"] = now()
        changed_status = True
    elif isinstance(batch_current, dict) and batch_current.get("case_id") == G023_POSTENTRY_AUTHORITY["case_id"]:
        need(batch_current.get("run_id") == G023_POSTENTRY_AUTHORITY["run_id"]
             and batch_current.get("sequence_index") == G023_POSTENTRY_AUTHORITY["sequence_index"]
             and batch_current.get("phase") == "RUN_ONE_IN_PROGRESS",
             "FAILED_PREENTRY_BATCH_POINTER_MISMATCH:" + cid)
    else:
        need(batch_current is None, "FAILED_PREENTRY_BATCH_POINTER_MISMATCH:" + cid)
    return changed_ledger, changed_status


def reconcile_failed_postentry(ledger, batch_status, evidence):
    expected = G023_POSTENTRY_AUTHORITY
    cid = expected["case_id"]
    current = ledger.get("current_case")
    changed_ledger = False
    if isinstance(current, dict) and current.get("case_id") == cid:
        record_g023_failed_postentry_recovery(ledger, current, evidence)
        changed_ledger = True
    else:
        need(current is None, "G023_POSTENTRY_OTHER_CURRENT_CASE_PRESENT")
        _assert_failed_postentry_recorded(ledger, evidence)
    batch_current = batch_status.get("current_case")
    changed_status = False
    if isinstance(batch_current, dict):
        need(batch_current.get("case_id") == cid
             and batch_current.get("run_id") == expected["run_id"]
             and batch_current.get("sequence_index") == expected["sequence_index"]
             and batch_current.get("phase") == "RUN_ONE_IN_PROGRESS",
             "G023_POSTENTRY_BATCH_POINTER_MISMATCH")
        batch_status["current_case"] = None
        batch_status["queue_phase"] = "QUEUE_RECOVERY_RECONCILED_STOPPED"
        batch_status["last_updated_utc"] = now()
        changed_status = True
    else:
        need(batch_current is None, "G023_POSTENTRY_BATCH_POINTER_MISMATCH")
    return changed_ledger, changed_status


def reconcile_g023_postentry_only():
    """Reconcile the single G023 post-entry receipt; this path never dispatches work."""
    expected_g = G023_POSTENTRY_AUTHORITY
    expected_p = FAILED_PREENTRY_AUTHORITY
    need(QMAN.is_file() and sha(QMAN) == expected_g["queue_manifest_file_sha256"],
         "RECOVERY_QUEUE_MANIFEST_FILE_SHA_MISMATCH")
    queue = read(QMAN)
    queue_body = dict(queue)
    saved_queue_sha = queue_body.pop("queue_manifest_sha256", None)
    need(saved_queue_sha == expected_g["queue_manifest_sha256"] == runner_canonical_sha(queue_body),
         "RECOVERY_QUEUE_MANIFEST_CANONICAL_SHA_MISMATCH")
    need(LEDGER.is_file() and BATCH.is_file(), "RECOVERY_LEDGER_OR_BATCH_STATUS_MISSING")

    _registry_path, registry = runner_registry()
    p_rows = [row for row in registry["runs"] if row.get("case_id") == expected_p["case_id"]
              and row.get("attempt_id") == expected_p["attempt_id"]]
    old_p = [row for row in p_rows if row.get("run_id") == expected_p["run_id"]]
    fresh_p = [row for row in p_rows if row.get("run_id") != expected_p["run_id"]]
    need(len(old_p) == 1 and len(fresh_p) == 1, "RECOVERY_P05_RUNNER_ROWS_AMBIGUOUS")
    p_evidence = verify_failed_preentry_recovery(old_p[0], expected_p["case_id"],
        require_slot_free=True, fresh_success_row=fresh_p[0])
    g_rows = [row for row in registry["runs"] if row.get("case_id") == expected_g["case_id"]
              and row.get("attempt_id") == expected_g["attempt_id"]
              and row.get("run_id") == expected_g["run_id"]]
    need(len(g_rows) == 1, "RECOVERY_G023_RUNNER_ROW_AMBIGUOUS")
    g_evidence = verify_g023_failed_postentry_closeout(g_rows[0], expected_g["case_id"])

    ledger_before_sha = sha(LEDGER)
    ledger = read(LEDGER)
    batch = read(BATCH)
    _assert_failed_preentry_recorded(ledger, p_evidence)
    receipt_path = REPORT / "G023_POSTENTRY_LEDGER_RECONCILIATION_V1.json"
    intent_path = REPORT / "G023_POSTENTRY_LEDGER_RECONCILIATION_INTENT_V1.json"
    prior_receipt = read(receipt_path) if receipt_path.is_file() else None
    prior_intent = read(intent_path) if intent_path.is_file() else None
    pre_state = ledger_before_sha == expected_g["ledger_sha256"]
    need(not (pre_state and prior_receipt is not None), "RECOVERY_BASELINE_HAS_CONFLICTING_RECEIPT")
    if not pre_state and prior_receipt is not None:
        _assert_failed_postentry_recorded(ledger, g_evidence)
        need(ledger.get("current_case") is None and batch.get("current_case") is None
             and prior_receipt.get("schema") == "COUPLING_K6_V2_G023_POSTENTRY_LEDGER_RECONCILIATION_V1"
             and prior_receipt.get("input_ledger_sha256") == expected_g["ledger_sha256"]
             and prior_receipt.get("output_ledger_sha256") == ledger_before_sha
             and prior_receipt.get("output_batch_status_sha256") == sha(BATCH)
             and prior_receipt.get("g023_evidence") == g_evidence
             and prior_receipt.get("d6_p05_evidence") == p_evidence,
             "RECOVERY_LEDGER_OR_RECEIPT_SHA_MISMATCH")
        need(ledger.get("entered_count") == 35 and ledger.get("truth_valid_count") == 33
             and ledger.get("labels_valid_count") == 33 and ledger.get("remaining_unentered_count") == 93
             and ledger.get("automatic_replay_count") == 0 and ledger.get("training_fits") == 0
             and ledger.get("p_scale_fits") == 0 and ledger.get("confirmation_response_access_count") == 0,
             "RECOVERY_POSTCONDITION_FAILED")
        print(json.dumps(dict(prior_receipt, receipt_path=str(receipt_path),
            receipt_sha256=sha(receipt_path), solver_entries_this_call=0,
            training_fits_this_call=0, p_scale_fits_this_call=0,
            confirmation_response_access_this_call=0, automatic_replays_this_call=0), indent=2), flush=True)
        return 0
    if pre_state:
        current = ledger.get("current_case")
        need(isinstance(current, dict) and current.get("case_id") == expected_g["case_id"]
             and current.get("run_id") == expected_g["run_id"]
             and current.get("sequence_index") == expected_g["sequence_index"]
             and current.get("phase") == "RUN_ONE_IN_PROGRESS",
             "RECOVERY_G023_BASELINE_CURRENT_CASE_MISMATCH")
        batch_current = batch.get("current_case")
        need(isinstance(batch_current, dict) and batch_current.get("case_id") == expected_g["case_id"]
             and batch_current.get("run_id") == expected_g["run_id"]
             and batch_current.get("sequence_index") == expected_g["sequence_index"]
             and batch_current.get("phase") == "RUN_ONE_IN_PROGRESS",
             "RECOVERY_G023_BASELINE_BATCH_POINTER_MISMATCH")
    else:
        need(isinstance(prior_intent, dict)
             and prior_intent.get("schema") == "COUPLING_K6_V2_G023_POSTENTRY_LEDGER_RECONCILIATION_INTENT_V1"
             and prior_intent.get("input_ledger_sha256") == expected_g["ledger_sha256"]
             and prior_intent.get("g023_evidence") == g_evidence
             and prior_intent.get("d6_p05_evidence") == p_evidence,
             "RECOVERY_UNRECOGNIZED_LEDGER_SHA")
        _assert_failed_postentry_recorded(ledger, g_evidence)
        need(ledger.get("current_case") is None, "RECOVERY_G023_POSTSTATE_CURRENT_CASE_NOT_CLEAR")
        batch_current = batch.get("current_case")
        if isinstance(batch_current, dict):
            need(sha(BATCH) == prior_intent.get("input_batch_status_sha256")
                 and batch_current.get("case_id") == expected_g["case_id"]
                 and batch_current.get("run_id") == expected_g["run_id"]
                 and batch_current.get("sequence_index") == expected_g["sequence_index"],
                 "RECOVERY_BATCH_STATUS_CHANGED_DURING_RECONCILIATION")
        else:
            need(batch_current is None, "RECOVERY_G023_POSTSTATE_BATCH_POINTER_INVALID")
    need(ledger.get("entered_count") == 35 and ledger.get("truth_valid_count") == 33
         and ledger.get("labels_valid_count") == 33 and ledger.get("remaining_unentered_count") == 93
         and ledger.get("automatic_replay_count") == 0 and ledger.get("training_fits") == 0
         and ledger.get("p_scale_fits") == 0 and ledger.get("confirmation_response_access_count") == 0,
         "RECOVERY_BASELINE_COUNTERS_MISMATCH")
    g_ledger_changed, g_status_changed = reconcile_failed_postentry(ledger, batch, g_evidence)
    if pre_state and not prior_intent:
        intent = {"schema": "COUPLING_K6_V2_G023_POSTENTRY_LEDGER_RECONCILIATION_INTENT_V1",
            "input_ledger_sha256": ledger_before_sha, "input_batch_status_sha256": sha(BATCH),
            "g023_evidence": g_evidence, "d6_p05_evidence": p_evidence,
            "solver_entries_this_call": 0, "created_at_utc": now()}
        write(intent_path, intent)
    elif prior_intent is not None:
        need(prior_intent.get("input_batch_status_sha256") == sha(BATCH)
             or batch.get("current_case") is None,
             "RECOVERY_INTENT_BATCH_BINDING_INVALID")
    if g_ledger_changed:
        write(LEDGER, ledger)
    if g_status_changed:
        write(BATCH, batch)
    final_ledger, final_batch = read(LEDGER), read(BATCH)
    _assert_failed_preentry_recorded(final_ledger, p_evidence)
    _assert_failed_postentry_recorded(final_ledger, g_evidence)
    need(final_ledger.get("current_case") is None and final_batch.get("current_case") is None
         and final_ledger.get("entered_count") == 35 and final_ledger.get("truth_valid_count") == 33
         and final_ledger.get("labels_valid_count") == 33 and final_ledger.get("remaining_unentered_count") == 93
         and final_ledger.get("automatic_replay_count") == 0 and final_ledger.get("training_fits") == 0
         and final_ledger.get("p_scale_fits") == 0
         and final_ledger.get("confirmation_response_access_count") == 0,
         "RECOVERY_POSTCONDITION_FAILED")
    receipt = {
        "schema": "COUPLING_K6_V2_G023_POSTENTRY_LEDGER_RECONCILIATION_V1",
        "mode": "READ_ONLY_EVIDENCE_PLUS_LEDGER_RECONCILIATION_NO_DISPATCH",
        "queue_manifest_file_sha256": expected_g["queue_manifest_file_sha256"],
        "queue_manifest_sha256": expected_g["queue_manifest_sha256"],
        "input_ledger_sha256": ledger_before_sha, "expected_input_ledger_sha256": expected_g["ledger_sha256"],
        "output_ledger_sha256": sha(LEDGER), "output_batch_status_sha256": sha(BATCH),
        "g023_evidence": g_evidence, "d6_p05_evidence": p_evidence,
        "counts": {key: final_ledger.get(key) for key in (
            "entered_count", "truth_valid_count", "labels_valid_count", "remaining_unentered_count",
            "automatic_replay_count", "training_fits", "p_scale_fits", "confirmation_response_access_count")},
        "solver_entries_this_call": 0, "training_fits_this_call": 0,
        "p_scale_fits_this_call": 0, "confirmation_response_access_this_call": 0,
        "automatic_replays_this_call": 0, "completed_at_utc": now(),
    }
    if receipt_path.exists():
        need(read(receipt_path).get("schema") == receipt["schema"]
             and read(receipt_path).get("output_ledger_sha256") == receipt["output_ledger_sha256"]
             and read(receipt_path).get("g023_evidence") == g_evidence,
             "RECOVERY_RECEIPT_CONFLICT")
    else:
        write(receipt_path, receipt)
    print(json.dumps(dict(receipt, receipt_path=str(receipt_path),
        receipt_sha256=sha(receipt_path)), indent=2), flush=True)
    return 0


def reconcile(ids, labels):
    path, rr = runner_registry()
    allowed = set(ids)
    foreign = [r for r in rr["runs"] if str(r.get("case_id", "")).startswith(
        ("K6LDA1_DEV_", "K6GDP2_DEV_")) and r.get("case_id") not in allowed]
    need(not foreign, "UNEXPECTED_K6_RUNNER_REGISTRY_ROWS")
    done, entered, failed = {}, [], {}
    for cid in ids:
        if cid == FAILED_PREENTRY_AUTHORITY["case_id"]:
            all_rows = [r for r in rr["runs"] if r.get("case_id") == cid]
            need(all(r.get("attempt_id") == FAILED_PREENTRY_AUTHORITY["attempt_id"] for r in all_rows),
                 "FAILED_PREENTRY_UNAUTHORIZED_ATTEMPT:" + cid)
            old_rows = [r for r in all_rows if r.get("run_id") == FAILED_PREENTRY_AUTHORITY["run_id"]]
            if not old_rows:
                need(not all_rows, "FAILED_PREENTRY_FIXED_RUN_MISSING_OR_DUPLICATE:" + cid)
                attempt_dir = RUN_ROOT / "runs" / cid / FAILED_PREENTRY_AUTHORITY["attempt_id"]
                need(not attempt_dir.exists(), "FAILED_PREENTRY_FIXED_RUN_MISSING_OR_DUPLICATE:" + cid)
                if LEDGER.is_file():
                    ledger = read(LEDGER)
                    current = ledger.get("current_case")
                    record = ledger.get("case_records", {}).get(cid)
                    isolated = [x for x in ledger.get("failed_or_isolated_cases", [])
                                if isinstance(x, dict) and x.get("case_id") == cid
                                and x.get("run_id") == FAILED_PREENTRY_AUTHORITY["run_id"]]
                    current_points_old = (isinstance(current, dict) and current.get("case_id") == cid
                        and (current.get("run_id") == FAILED_PREENTRY_AUTHORITY["run_id"]
                             or (current.get("run_id") is None
                                 and current.get("sequence_index") == FAILED_PREENTRY_AUTHORITY["sequence_index"])))
                    record_points_old = (isinstance(record, dict)
                        and (record.get("run_id") == FAILED_PREENTRY_AUTHORITY["run_id"]
                             or (record.get("run_id") is None
                                 and record.get("sequence_index") == FAILED_PREENTRY_AUTHORITY["sequence_index"])))
                    need(not current_points_old and not record_points_old and not isolated,
                         "FAILED_PREENTRY_FIXED_RUN_MISSING_BUT_LEDGER_POINTS_TO_OLD_RUN:" + cid)
                continue
            need(len(old_rows) == 1, "FAILED_PREENTRY_FIXED_RUN_MISSING_OR_DUPLICATE:" + cid)
            rows = [r for r in all_rows if r.get("run_id") != FAILED_PREENTRY_AUTHORITY["run_id"]]
            need(len(rows) <= 1, "FAILED_PREENTRY_MULTIPLE_FRESH_RUNS:" + cid)
            failed[cid] = verify_failed_preentry_recovery(
                old_rows[0], cid, fresh_success_row=rows[0] if rows else None)
            if not rows:
                continue
        else:
            rows = rows_for(rr, cid)
            need(len(rows) <= 1, "DUPLICATE_RUNNER_ENTRY:" + cid)
            if not rows:
                attempt = RUN_ROOT / "runs" / cid / "attempt_001"
                need(not attempt.exists() or not any(attempt.iterdir()), "RUN_DIRECTORY_WITHOUT_REGISTRY:" + cid)
                continue
        row, state = rows[0], runner_status(rows[0], cid)
        if state.get("solver_entered") is True and cid not in entered:
            entered.append(cid)
        if state.get("state") == "FAILED_POSTENTRY":
            failed[cid] = verify_failed_postentry_closeout(row, cid)
            continue
        need(state.get("state") == "DONE" and state.get("solver_entered") is True
             and state.get("solver_invocations") == 1 and state.get("replay_count", 0) == 0,
             "ENTERED_CASE_NEEDS_AUDIT:" + cid)
        run = Path(row["run_dir"])
        for name in ("truth.h5", "validation.json", "hashes.json", "run.fsp"):
            need((run / name).is_file(), "DURABLE_RUN_ARTIFACT_MISSING:" + cid + ":" + name)
        validation = read(run / "validation.json")
        need(all(validation.get(k) is True for k in
                 ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")),
             "RUNNER_VALIDATION_NOT_PASS:" + cid)
        done[cid] = row
    need(set(INITIAL).issubset(done) and set(INITIAL).issubset(labels), "INITIAL_CASES_NOT_RECONCILED")
    return path, rr, done, entered, failed


def record_ingest(cid, case, row, ingest):
    run = Path(row["run_dir"])
    state, validation = read(run / "status.json"), read(run / "validation.json")
    need(state.get("state") == "DONE" and state.get("solver_entered") is True
         and state.get("solver_invocations") == 1 and state.get("replay_count", 0) == 0,
         "RUNNER_ENTRY_INVALID:" + cid)
    need(all(validation.get(k) is True for k in
             ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")),
         "RUNNER_TRUTH_INVALID:" + cid)
    stem = cid + "__attempt_001"
    def desc(path):
        path = Path(path)
        need(path.is_file() and path.stat().st_size > 0, "TRUTH_ARTIFACT_NOT_DURABLE:" + str(path))
        return {"path": str(path), "sha256": sha(path)}
    record = {"case_id": cid, "attempt_id": "attempt_001", "role": case["role"],
              "ordered_D_nm": list(case["ordered_D_nm"]), "physical_contract_sha256": CONTRACT_SHA,
              "status": "DONE", "solver_invocations": 1, "replay_count": 0,
              "source_manifest": desc(run / "manifest.json"),
              "state_npz": desc(run / "state" / (stem + "_pw_complex_floquet_state.npz")),
              "state_metadata": desc(run / "state" / (stem + "_pw_complex_floquet_state.json")),
              "raw_npz": desc(run / "raw" / (stem + "_raw_complex_fields.npz")),
              "raw_metadata": desc(run / "raw" / (stem + "_raw.json")),
              "orders_json": desc(run / "orders" / (stem + "_orders.json")),
              "truth_h5": desc(run / "truth.h5")}
    truth = ingest.load_verified_runner_case(record, expected_role=case["role"], root=ROOT)
    need(truth.c_hat.shape == (21, 7, 2) and truth.p_scale.shape == (21,)
         and truth.eta.shape == (21, 7) and truth.absolute_order.shape == (21, 7),
         "INGEST_SHAPE_INVALID:" + cid)
    need(np.isfinite(truth.c_hat.real).all() and np.isfinite(truth.c_hat.imag).all()
         and np.isfinite(truth.p_scale).all(), "INGEST_NONFINITE:" + cid)
    npz = REPORT / ("INGESTED_TRUTH_" + cid + "_V1.npz")
    result_path = REPORT / ("INGEST_RESULT_" + cid + "_V1.json")
    arrays = {
        "case_id": np.asarray(cid), "attempt_id": np.asarray("attempt_001"),
        "role": np.asarray(case["role"]),
        "ordered_D_nm": np.asarray(case["ordered_D_nm"], dtype=np.int64),
        "wavelengths_nm": np.arange(440, 461), "order_m": np.arange(-3, 4),
        "polarization": np.asarray(["TE", "TM"]), "C_hat_real": truth.c_hat.real,
        "C_hat_imag": truth.c_hat.imag, "P_scale": truth.p_scale,
        "eta": truth.eta, "absolute_order": truth.absolute_order,
    }
    if npz.exists():
        need(npz.is_file(), "INGEST_TRUTH_PATH_NOT_FILE:" + cid)
        try:
            with np.load(npz, allow_pickle=False) as saved:
                need(set(saved.files) == set(arrays), "INGEST_ARTIFACT_KEYS_CONFLICT:" + cid)
                for key, expected in arrays.items():
                    need(np.array_equal(saved[key], expected), "INGEST_ARTIFACT_VALUE_CONFLICT:" + cid + ":" + key)
        except Exception as exc:
            raise StopQueue("INGEST_ARTIFACT_UNREADABLE:" + cid + ":" + str(exc)) from exc
    else:
        fd, temporary = tempfile.mkstemp(prefix=npz.name + ".tmp-", suffix=".npz", dir=str(REPORT))
        try:
            with os.fdopen(fd, "wb") as f:
                np.savez_compressed(f, **arrays)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, npz)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    if result_path.exists():
        old = read(result_path)
        need(old.get("status") == "PASS" and old.get("truth_artifact", {}).get("sha256") == sha(npz),
             "INGEST_ARTIFACT_CONFLICT:" + cid)
        return old
    result = {"schema": "COUPLING_K6_V2_DEVELOPMENT_CASE_INGEST_RESULT_V1", "status": "PASS",
        "decision": "INGESTED_FOR_DEVELOPMENT_ONLY; NOT_MODEL_ADMISSION", "case_id": cid,
        "attempt_id": "attempt_001", "role": case["role"], "ordered_D_nm": list(case["ordered_D_nm"]),
        "run_id": state["run_id"], "solver_entered": True, "solver_invocations": 1, "replay_count": 0,
        "access_counts": {"solver_entries_this_case": 1, "automatic_replay": 0,
            "training_fit_count": 0, "p_scale_fit_count": 0,
            "confirmation_response_opened": False, "diagnostic_data_accessed": False},
        "input_artifacts": record, "truth_artifact": {"path": str(npz), "sha256": sha(npz),
            "shapes": {"C_hat": [21, 7, 2], "P_scale": [21], "eta": [21, 7],
                       "absolute_order": [21, 7]}},
        "source_fraction_sum_vs_p_scale_max_abs": float(np.max(
            np.abs(truth.absolute_order.sum(axis=1) - truth.p_scale))),
        "truth_provenance": dict(truth.provenance), "completed_at_utc": now()}
    write(result_path, result)
    return result


def current_proof_valid(cd, manifest, ctrl):
    try:
        a = manifest["artifacts"]
        contract = read(artifact(cd, a["physical_contract"], "contract"))
        source, staged = artifact(cd, a["source_fsp"], "source"), artifact(cd, a["staged_fsp"], "staged")
        proof = read(artifact(cd, a["pre_entry_setup_load_proof"], "proof"))
        provenance = read(artifact(cd, a["case_provenance_source"], "provenance"))
        semantic = ctrl.canonical_sha256(contract)
        fp = ctrl.setup_fingerprint(case_class=manifest["case_class"], case_id=manifest["case_id"],
            attempt_id=manifest["attempt_id"], ordered_D_nm=provenance["ordered_D_nm"],
            physical_contract_sha256=manifest["physical_contract_sha256"],
            physical_contract_semantic_sha256=semantic)
        return (manifest.get("route_authority_sha256") == AUTH_SHA
            and manifest.get("route_policy_sha256") == POLICY_SHA
            and manifest.get("physical_contract_sha256") == CONTRACT_SHA
            and manifest.get("physical_contract_semantic_sha256") == semantic
            and manifest.get("setup_contract_fingerprint_sha256") == fp
            and proof.get("result") == "PASS" and proof.get("load_only_pass") is True
            and proof.get("solver_run_called") is False and proof.get("scientific_entry_count") == 0
            and proof.get("route_authority_sha256") == AUTH_SHA and proof.get("route_policy_sha256") == POLICY_SHA
            and proof.get("setup_contract_fingerprint_sha256") == fp
            and proof.get("source_fsp_sha256") == sha(source) and proof.get("staged_fsp_sha256") == sha(staged)
            and proof.get("setup_readback", {}).get("five_nm_validator_status") == "PASS"
            and proof.get("setup_readback", {}).get("ordered_D_nm") == provenance["ordered_D_nm"])
    except Exception:
        return False


def fresh_load(fsp, spec, env):
    proc = subprocess.run([sys.executable, str(VALIDATOR), "--fsp", str(fsp),
        "--spec-json", str(spec)], cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=900)
    need(proc.returncode == 0, "FRESH_LOAD_VALIDATOR_FAILED:" + proc.stderr[-800:])
    result = json.loads(proc.stdout)
    need(result.get("validation", {}).get("status") == "PASS", "FRESH_LOAD_NOT_PASS:" + str(fsp))
    return result


def refresh_proof(cid, case, status, ctrl):
    cd = CASE_ROOT / cid / "attempt_001"
    manifest_path = cd / "source_manifest.json"
    manifest = read(manifest_path)
    a = manifest["artifacts"]
    contract_path = artifact(cd, a["physical_contract"], "contract")
    source, staged = artifact(cd, a["source_fsp"], "source"), artifact(cd, a["staged_fsp"], "staged")
    spec = artifact(cd, a["five_nm_case_spec"], "spec")
    provenance_path = artifact(cd, a["case_provenance_source"], "provenance")
    provenance = read(provenance_path)
    geometry = list(case["ordered_D_nm"])
    need(provenance.get("ordered_D_nm") == geometry, "CASE_GEOMETRY_SOURCE_MISMATCH:" + cid)
    contract = read(contract_path)
    contract_sha, semantic = sha(contract_path), ctrl.canonical_sha256(contract)
    need(contract_sha == CONTRACT_SHA and sha(source) == sha(staged), "FROZEN_SETUP_MISMATCH:" + cid)
    fp = ctrl.setup_fingerprint(case_class="K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
        case_id=cid, attempt_id="attempt_001", ordered_D_nm=geometry,
        physical_contract_sha256=contract_sha, physical_contract_semantic_sha256=semantic)
    resolved = read(artifact(cd, a["resolved_setup"], "resolved_setup"))
    need(resolved.get("setup_contract_fingerprint_sha256") == fp, "RESOLVED_SETUP_FINGERPRINT_MISMATCH:" + cid)
    env = os.environ.copy()
    env["PYTHONPATH"] = r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python" + ";" + str(RUN_DIR) + ";" + env.get("PYTHONPATH", "")
    first = fresh_load(source, spec, env)
    second = first if sha(source) == sha(staged) else fresh_load(staged, spec, env)
    sr, tr = first["readback"], second["readback"]
    need(sr.get("case_id") == cid and tr.get("case_id") == cid
         and sr.get("ordered_D_nm") == geometry and tr.get("ordered_D_nm") == geometry,
         "FRESH_LOAD_IDENTITY_MISMATCH:" + cid)
    comparable = lambda r: {k: v for k, v in r.items() if k not in ("fsp", "fsp_sha256")}
    need(comparable(sr) == comparable(tr), "SOURCE_STAGED_READBACK_MISMATCH:" + cid)
    proof_path = cd / "pre_entry_setup_load_proof_current_a78274be.json"
    old_auth = manifest.get("route_authority_sha256")
    if old_auth != AUTH_SHA:
        legacy = cd / ("legacy_route_" + str(old_auth or "missing")[:12]) / "attempt_001"
        legacy.mkdir(parents=True, exist_ok=True)
        old_proof = cd / a["pre_entry_setup_load_proof"]["path"]
        for src, name in ((manifest_path, "source_manifest.json"), (old_proof, "pre_entry_setup_load_proof.json")):
            if src.is_file() and not (legacy / name).exists():
                shutil.copy2(src, legacy / name)
    proof = {"schema": "APCD_GPU_RUNNER_PREENTRY_SETUP_LOAD_PROOF_V1", "result": "PASS",
        "load_only_pass": True, "route_version": ctrl.ROUTE_VERSION,
        "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1", "case_id": cid,
        "attempt_id": "attempt_001", "route_authority_sha256": AUTH_SHA,
        "route_policy_sha256": POLICY_SHA, "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": semantic, "setup_contract_fingerprint_sha256": fp,
        "source_fsp_sha256": sha(source), "staged_fsp_sha256": sha(staged),
        "setup_readback": {"five_nm_validator_status": "PASS",
            "geometry_hash_sha256": tr.get("geometry_hash_sha256"), "ordered_D_nm": geometry,
            "source_staged_semantic_parity": "PASS", "staged_fsp_readback": tr},
        "proof_semantics": "setup LOAD only; no solver-produced truth",
        "scientific_entry_count": 0, "solver_invocations": 0, "solver_run_called": False,
        "post_entry_truth_proved": False, "post_entry_truth_required_after_solver": True,
        "created_at_utc": now()}
    write(proof_path, proof)
    manifest.update({"schema": "APCD_GPU_RUNNER_CONTROLLED_CASE_SOURCE_MANIFEST_V1",
        "route_version": ctrl.ROUTE_VERSION, "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
        "case_id": cid, "attempt_id": "attempt_001", "route_policy_sha256": POLICY_SHA,
        "route_authority_sha256": AUTH_SHA, "physical_contract_sha256": contract_sha,
        "physical_contract_semantic_sha256": semantic, "setup_contract_fingerprint_sha256": fp})
    manifest["artifacts"]["pre_entry_setup_load_proof"] = {"path": proof_path.name, "sha256": sha(proof_path)}
    write(manifest_path, manifest)
    report_path = REPORT / ("FRESH_LOAD_READBACK_" + cid + "_A78274BE_V1.json")
    if not report_path.exists():
        write(report_path, {"schema": "COUPLING_K6_CURRENT_ROUTE_FRESH_LOAD_READBACK_V1",
            "case_id": cid, "attempt_id": "attempt_001", "ordered_D_nm": geometry,
            "source_fsp_sha256": sha(source), "staged_fsp_sha256": sha(staged),
            "source_validation": first, "staged_validation": second,
            "source_staged_semantic_parity": "PASS", "solver_run_called": False,
            "solver_invocations": 0, "scientific_entry_count": 0, "captured_at_utc": now()})
    row = status.setdefault("cases", {}).setdefault(cid, {"case_id": cid, "attempt_id": "attempt_001",
        "role": case["role"], "ordered_D_nm": geometry})
    row.update({"status": "LOAD_PROOF_PASS", "source_manifest_path": str(manifest_path),
        "source_manifest_sha256": sha(manifest_path), "proof_path": str(proof_path),
        "proof_sha256": sha(proof_path), "fresh_load_readback_path": str(report_path),
        "fresh_load_readback_sha256": sha(report_path), "solver_invocations": 0,
        "scientific_entry_count": 0})
    status["last_updated_utc"] = now()
    write(BATCH, status)


def prepare_case(cid, case, status, ctrl):
    cd = CASE_ROOT / cid / "attempt_001"
    manifest_path = cd / "source_manifest.json"
    manifest = read(manifest_path)
    if not current_proof_valid(cd, manifest, ctrl):
        refresh_proof(cid, case, status, ctrl)
        manifest = read(manifest_path)
    a = manifest["artifacts"]
    contract, staged, proof = (artifact(cd, a[k], k) for k in
                               ("physical_contract", "staged_fsp", "pre_entry_setup_load_proof"))
    sm_sha = sha(manifest_path)
    row = status.get("cases", {}).get(cid, {})
    if row.get("status") == "PASS" and row.get("source_manifest_sha256") == sm_sha:
        rp = Path(row.get("preflight_result_path", ""))
        if rp.is_file() and sha(rp) == row.get("preflight_result_sha256") and read(rp).get("result") == "PASS":
            return {"source_manifest_path": str(manifest_path), "source_manifest_sha256": sm_sha,
                "proof_path": str(proof), "proof_sha256": sha(proof), "physical_contract_path": str(contract),
                "physical_contract_sha256": sha(contract), "pre_fsp_path": str(staged),
                "pre_fsp_sha256": sha(staged), "preflight_result_path": str(rp),
                "preflight_result_sha256": sha(rp)}
    suffix = sm_sha[:12]
    envelope_path = REPORT / ("FORMAL_PREFLIGHT_ENVELOPE_" + cid + "_A78274BE_" + suffix + ".json")
    result_path = REPORT / ("FORMAL_PREFLIGHT_RESULT_" + cid + "_A78274BE_" + suffix + ".json")
    envelope = {"schema": "APCD_GPU_RUNNER_CONTROLLED_SETUP_PREFLIGHT_ENVELOPE_V1",
        "route_version": ctrl.ROUTE_VERSION, "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
        "case_id": cid, "attempt_id": "attempt_001", "geometry": list(case["ordered_D_nm"]),
        "physical_contract_path": str(contract), "physical_contract_sha256": sha(contract),
        "pre_fsp_path": str(staged), "pre_fsp_sha256": sha(staged), "expansion_manifest_sha256": EXPANSION_SHA,
        "controlled_admission": {"authority_path": str(AUTH), "authority_sha256": AUTH_SHA,
            "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1", "route_version": ctrl.ROUTE_VERSION,
            "source_manifest_path": str(manifest_path), "source_manifest_sha256": sm_sha}}
    if envelope_path.exists():
        need(read(envelope_path) == envelope, "PREFLIGHT_ENVELOPE_CONFLICT:" + cid)
    else:
        write(envelope_path, envelope)
    if result_path.exists():
        result = read(result_path)
    else:
        env = os.environ.copy()
        env["PYTHONPATH"] = r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python" + ";" + str(RUN_DIR) + ";" + env.get("PYTHONPATH", "")
        env["APCD_GPU_RESOURCE_NAME"] = "SETUP_PREFLIGHT_ONLY_NO_SLOT"
        proc = subprocess.run([sys.executable, str(ADAPTER), "preflight-setup", str(envelope_path)],
            cwd=str(RUN_DIR), env=env, capture_output=True, text=True, timeout=1800)
        log = REPORT / ("FORMAL_PREFLIGHT_LOG_" + cid + "_A78274BE_" + suffix + ".txt")
        log.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
        need(proc.returncode == 0, "OFFICIAL_PREFLIGHT_FAILED:" + cid + ":" + proc.stderr[-800:])
        result = json.loads(proc.stdout)
        write(result_path, result)
    need(result.get("result") == "PASS" and result.get("solver_run_called") is False
         and result.get("solver_invocations") == 0 and result.get("scientific_entry_count") == 0,
         "OFFICIAL_PREFLIGHT_NOT_ZERO_SOLVER_PASS:" + cid)
    row = status.setdefault("cases", {}).setdefault(cid, {"case_id": cid, "attempt_id": "attempt_001",
        "role": case["role"], "ordered_D_nm": list(case["ordered_D_nm"])})
    row.update({"status": "PASS", "source_manifest_path": str(manifest_path),
        "source_manifest_sha256": sm_sha, "proof_path": str(proof), "proof_sha256": sha(proof),
        "preflight_envelope_path": str(envelope_path), "preflight_envelope_sha256": sha(envelope_path),
        "preflight_result_path": str(result_path), "preflight_result_sha256": sha(result_path),
        "solver_invocations": 0, "scientific_entry_count": 0, "preflight_completed_at_utc": now()})
    status["last_updated_utc"] = now()
    write(BATCH, status)
    return {"source_manifest_path": str(manifest_path), "source_manifest_sha256": sm_sha,
        "proof_path": str(proof), "proof_sha256": sha(proof), "physical_contract_path": str(contract),
        "physical_contract_sha256": sha(contract), "pre_fsp_path": str(staged),
        "pre_fsp_sha256": sha(staged), "preflight_result_path": str(result_path),
        "preflight_result_sha256": sha(result_path)}


def entry_gate(pack, adapter):
    control = adapter.read_global_entry_control()
    need(control.get("result") == "PASS", "GLOBAL_ENTRY_HOLD_NOT_PASS")
    busy = adapter.NativeAdapter.runner_owner_probe(RUN_ROOT)
    need(busy is False and not (RUN_ROOT / "active_run.json").exists()
         and not (RUN_ROOT / ".runner.lock").exists(), "RUNNER_SLOT_OR_LOCK_NOT_FREE")
    native = adapter.NativeAdapter(pack["physical_contract_path"], gpu_resource_name=RESOURCE)
    gpu = native.gpu_snapshot()
    free = gpu.get("free_mib")
    need(isinstance(free, int) and free >= adapter.MIN_GPU_FREE_MIB, "GPU_BELOW_RUNNER_MINIMUM")
    return {"global_control": control, "runner_owner_busy": busy, "gpu_free_mib": free,
        "gpu_minimum_free_mib": adapter.MIN_GPU_FREE_MIB,
        "gpu_snapshot_sha256": hashlib.sha256(json.dumps(gpu, sort_keys=True, default=str).encode()).hexdigest(),
        "checked_at_utc": now()}


def run_envelope(cid, case, pack, run_id):
    return {"case_id": cid, "attempt_id": "attempt_001", "run_id": run_id,
        "controlled_admission": {"authority_path": str(AUTH), "authority_sha256": AUTH_SHA,
            "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
            "route_version": "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1",
            "source_manifest_path": pack["source_manifest_path"],
            "source_manifest_sha256": pack["source_manifest_sha256"]},
        "expansion_manifest_sha256": EXPANSION_SHA, "geometry": list(case["ordered_D_nm"]),
        "physical_contract_path": pack["physical_contract_path"],
        "physical_contract_sha256": pack["physical_contract_sha256"],
        "pre_fsp_path": pack["pre_fsp_path"], "pre_fsp_sha256": pack["pre_fsp_sha256"]}


def update_counts(ledger, ids, registry):
    entered, truth = set(INITIAL), set(INITIAL)
    for cid in ids:
        rows = rows_for(registry, cid)
        states = [runner_status(row, cid) for row in rows]
        if any(state.get("solver_entered") is True for state in states):
            entered.add(cid)
        if any(state.get("state") == "DONE" and state.get("solver_entered") is True
               and state.get("solver_invocations") == 1 for state in states):
            truth.add(cid)
    labels = set(ledger.get("labels_valid_case_ids", [])) | set(INITIAL)
    ledger.update({"entered_case_ids": sorted(entered), "truth_valid_case_ids": sorted(truth),
        "labels_valid_case_ids": sorted(labels), "entered_count": len(entered),
        "truth_valid_count": len(truth), "labels_valid_count": len(labels),
        "remaining_unentered_case_ids": [c for c in ids if c not in entered],
        "remaining_unentered_count": 128 - len(entered), "last_updated_utc": now()})


def fresh_run_id(cid, registry=None):
    if registry is None:
        _, registry = runner_registry()
    existing_ids = {r.get("run_id") for r in registry.get("runs", [])}
    for _ in range(16):
        candidate = ("K6V2_" + cid.split("_DEV_", 1)[-1].replace("_", "") + "_"
                     + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_"
                     + uuid.uuid4().hex[:8])
        run_dir = RUN_ROOT / "runs" / cid / "attempt_001" / candidate
        envelope = REPORT / ("RUN_ENVELOPE_" + candidate + ".json")
        if candidate not in existing_ids and candidate != FAILED_PREENTRY_AUTHORITY["run_id"] \
                and not run_dir.exists() and not envelope.exists():
            return candidate
    raise StopQueue("FRESH_RUN_ID_COLLISION:" + cid)


def run_case(cid, sequence, case, inputs, ledger, *, controller=None, controller_status=None):
    status, budget, registry, ids, qmanifest, qsha, ingest, ctrl, adapter = inputs
    started = time.monotonic()
    if controller is not None:
        controller_status.update({"state": "RUNNING", "startup_reconciled": True,
            "current_case_id": cid, "updated_at_utc": now()})
        write(controller["status_path"], controller_status)
    status["current_case"] = {"case_id": cid, "sequence_index": sequence,
        "phase": "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT", "updated_at_utc": now()}
    status["queue_phase"] = "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT"
    status["last_updated_utc"] = now()
    write(BATCH, status)
    ledger["current_case"] = {"case_id": cid, "sequence_index": sequence,
        "phase": "ENSURE_CURRENT_ROUTE_AND_PREFLIGHT"}
    write(LEDGER, ledger)
    pack = prepare_case(cid, case, status, ctrl)
    ledger["phase_timings_seconds"]["route_proof_and_preflight"] += time.monotonic() - started
    status["current_case"]["phase"] = "LIVE_ENTRY_GATE"
    status["last_updated_utc"] = now()
    write(BATCH, status)
    gate = entry_gate(pack, adapter)
    print("LIVE_GATE_PASS " + cid + " generation=" +
          str(gate["global_control"].get("control_generation")) +
          " gpu_free_mib=" + str(gate["gpu_free_mib"]), flush=True)
    run_id = fresh_run_id(cid)
    epath = REPORT / ("RUN_ENVELOPE_" + run_id + ".json")
    write(epath, run_envelope(cid, case, pack, run_id))
    ehash = sha(epath)
    log = REPORT / ("RUNNER_CLI_OUTPUT_" + run_id + ".log")
    result_path = REPORT / ("RUN_ONE_RESULT_" + run_id + ".json")
    ledger["current_case"].update({"phase": "RUN_ONE_IN_PROGRESS", "run_id": run_id,
        "run_envelope_path": str(epath), "run_envelope_sha256": ehash})
    ledger.setdefault("case_records", {})[cid] = {"attempt_id": "attempt_001", "sequence_index": sequence,
        "phase": "RUN_ONE_IN_PROGRESS", "run_id": run_id, "run_envelope_path": str(epath),
        "run_envelope_sha256": ehash, "dispatch_at_utc": now()}
    write(LEDGER, ledger)
    status["current_case"]["phase"] = "RUN_ONE_IN_PROGRESS"
    status["current_case"]["run_id"] = run_id
    status["last_updated_utc"] = now()
    write(BATCH, status)
    if controller is not None:
        controller_status.update({"state": "RUNNING", "current_case_id": cid,
            "updated_at_utc": now()})
        write(controller["status_path"], controller_status)
    env = os.environ.copy()
    env["APCD_GPU_RESOURCE_NAME"] = RESOURCE
    env["PYTHONPATH"] = r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python" + ";" + str(RUN_DIR) + ";" + env.get("PYTHONPATH", "")
    t = time.monotonic()
    with log.open("wb") as output:
        proc = subprocess.Popen([sys.executable, str(ADAPTER), "run-one", str(epath)],
            cwd=str(RUN_DIR), env=env, stdout=output, stderr=subprocess.STDOUT)
        beat = time.monotonic()
        while proc.poll() is None:
            time.sleep(2)
            if time.monotonic() - beat >= 30:
                update_counts(ledger, ids, runner_registry()[1])
                ledger["current_case"]["heartbeat_at_utc"] = now()
                ledger["current_case"]["elapsed_seconds"] = time.monotonic() - t
                write(LEDGER, ledger)
                status["last_updated_utc"] = now()
                write(BATCH, status)
                print("QUEUE_HEARTBEAT " + cid + " elapsed_s=" +
                      str(int(time.monotonic() - t)), flush=True)
                beat = time.monotonic()
        returncode = proc.returncode
    run_elapsed = time.monotonic() - t
    ledger["phase_timings_seconds"]["run_one"] += run_elapsed
    registry_path, rr = runner_registry()
    rows = [r for r in rows_for(rr, cid) if r.get("run_id") == run_id]
    if returncode != 0 or len(rows) != 1:
        evidence = {"returncode": returncode, "run_log": str(log), "run_log_sha256": sha(log),
            "registry_rows": rows}
        if rows:
            evidence["runner_status"] = read(Path(rows[0]["run_dir"]) / "status.json")
        ledger["failed_or_isolated_cases"].append({"case_id": cid, "sequence_index": sequence,
            "phase": "RUN_ONE", "failed_at_utc": now(), "evidence": evidence})
        ledger["current_case"]["phase"] = "FAILED_OR_ISOLATED"
        update_counts(ledger, ids, rr)
        write(LEDGER, ledger)
        raise StopQueue("RUN_ONE_FAILED_OR_AMBIGUOUS:" + cid)
    row = rows[0]
    state = runner_status(row, cid)
    run = Path(row["run_dir"])
    validation = read(run / "validation.json")
    need(state.get("state") == "DONE" and state.get("solver_entered") is True
         and state.get("solver_invocations") == 1 and state.get("replay_count", 0) == 0,
         "POSTENTRY_STATUS_INVALID:" + cid)
    need(all(validation.get(k) is True for k in
             ("fresh_load_verified", "monitors_valid", "state_valid", "scientific_valid")),
         "POSTENTRY_VALIDATION_INVALID:" + cid)
    for name in ("run.fsp", "truth.h5", "validation.json", "hashes.json"):
        need((run / name).is_file() and (run / name).stat().st_size > 0,
             "DURABILITY_BARRIER_FAILED:" + cid + ":" + name)
    deadline = time.monotonic() + 180
    while adapter.NativeAdapter.runner_owner_probe(RUN_ROOT) is not False:
        need(time.monotonic() < deadline, "RUNNER_SLOT_RELEASE_TIMEOUT:" + cid)
        time.sleep(3)
    need(not (RUN_ROOT / "active_run.json").exists() and not (RUN_ROOT / ".runner.lock").exists(),
         "RUNNER_LOCK_NOT_RELEASED:" + cid)
    result_path = REPORT / ("RUN_ONE_RESULT_" + run_id + ".json")
    write(result_path, {"schema": "COUPLING_K6_V2_RUN_ONE_RESULT_V1", "status": "DONE",
        "case_id": cid, "attempt_id": "attempt_001", "run_id": run_id,
        "run_envelope_path": str(epath), "run_envelope_sha256": ehash,
        "runner_cli_output_path": str(log), "runner_cli_output_sha256": sha(log),
        "run_directory": str(run), "runner_status_sha256": sha(run / "status.json"),
        "truth_h5_sha256": sha(run / "truth.h5"), "validation_sha256": sha(run / "validation.json"),
        "live_entry_gate": gate, "solver_invocations": 1, "post_entry_automatic_replays": 0,
        "completed_at_utc": now()})
    ledger["current_case"]["phase"] = "TRUTH_DURABLE_SLOT_RELEASED_INGEST_PENDING"
    write(LEDGER, ledger)
    ingest_started = time.monotonic()
    result = record_ingest(cid, case, row, ingest)
    ledger["phase_timings_seconds"]["truth_ingest"] += time.monotonic() - ingest_started
    need(result.get("status") == "PASS", "LABEL_INGEST_FAILED:" + cid)
    if cid not in ledger["labels_valid_case_ids"]:
        ledger["labels_valid_case_ids"].append(cid)
    ledger["case_records"][cid].update({"phase": "LABEL_PASS", "run_directory": str(run),
        "runner_status_sha256": sha(run / "status.json"), "truth_h5_sha256": sha(run / "truth.h5"),
        "run_one_result_path": str(result_path), "run_one_result_sha256": sha(result_path),
        "ingest_result_path": str(REPORT / ("INGEST_RESULT_" + cid + "_V1.json")),
        "ingest_truth_path": str(REPORT / ("INGESTED_TRUTH_" + cid + "_V1.npz")),
        "completed_at_utc": now()})
    update_counts(ledger, ids, runner_registry()[1])
    ledger["current_case"] = None
    write(LEDGER, ledger)
    status["current_case"] = None
    status["queue_phase"] = "QUEUE_ACTIVE"
    status["last_updated_utc"] = now()
    write(BATCH, status)
    if controller is not None:
        controller_status.update({"state": "RUNNING", "current_case_id": None,
            "unresolved_runner_request_ids": [], "updated_at_utc": now()})
        write(controller["status_path"], controller_status)
    print("QUEUE_CASE_DONE " + cid + " run_id=" + run_id + " entered=" +
          str(ledger["entered_count"]) + " truth=" + str(ledger["truth_valid_count"]) +
          " labels=" + str(ledger["labels_valid_count"]) + " remaining=" +
          str(ledger["remaining_unentered_count"]), flush=True)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--reconcile-preentry-only", action="store_true")
    group.add_argument("--reconcile-g023-postentry-only", action="store_true")
    group.add_argument("--reconcile-controller-stop-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--runner-controller-manifest")
    parser.add_argument("--runner-controller-manifest-sha256")
    parser.add_argument("--runner-controller-request-id")
    parser.add_argument("--runner-resume-receipt")
    parser.add_argument("--runner-resume-receipt-sha256")
    args = parser.parse_args()
    if args.reconcile_g023_postentry_only:
        return reconcile_g023_postentry_only()
    controller_fields = (args.runner_controller_manifest, args.runner_controller_manifest_sha256,
                         args.runner_controller_request_id)
    controller_requested = any(value is not None for value in controller_fields)
    controller = None
    resume_receipt = None
    if controller_requested:
        need(all(value is not None for value in controller_fields),
             "CONTROLLER_MANIFEST_ARGUMENT_SET_INCOMPLETE")
        controller = verify_controller_manifest(*controller_fields)
        resume_fields = (args.runner_resume_receipt, args.runner_resume_receipt_sha256)
        need((resume_fields[0] is None) == (resume_fields[1] is None),
             "CONTROLLER_RESUME_RECEIPT_ARGUMENT_SET_INCOMPLETE")
        if resume_fields[0] is not None:
            resume_receipt = verify_controller_resume_receipt(controller, *resume_fields)
        elif controller["status_path"].exists() and not args.reconcile_controller_stop_only:
            raise StopQueue("CONTROLLER_STATUS_EXISTS_WITHOUT_RESUME_RECEIPT")
        args.execute = True
    else:
        need(not args.execute, "QUEUE_EXECUTE_REQUIRES_HASH_BOUND_RUNNER_CONTROLLER")
    if args.reconcile_controller_stop_only:
        need(controller is not None and resume_receipt is None,
             "CONTROLLER_STOP_RECONCILIATION_REQUIRES_FROZEN_CONTROLLER_MANIFEST")
        result = reconcile_controller_stopped_boundary(controller)
        print(json.dumps(result, indent=2), flush=True)
        return 0
    REPORT.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    status, budget, registry, ids, manifest, qsha, ingest, ctrl, adapter = inputs
    labels = initial_labels()
    _, rr, done, entered, failed = reconcile(ids, labels)
    queue_ids = [cid for cid in ids if cid not in INITIAL]
    if controller is not None:
        allowed = set(queue_ids)
        need(set(controller["case_ids"]).issubset(allowed), "CONTROLLER_CASE_ALLOWLIST_NOT_DEVELOPMENT_ONLY")
        queue_ids = list(controller["case_ids"])
    existing_ledger = read(LEDGER) if LEDGER.exists() else {}
    if controller is not None:
        labeled_for_controller = set(labels) | set(existing_ledger.get("labels_valid_case_ids", []))
        for cid in queue_ids:
            need(not (cid in failed and not (cid in done and cid in labeled_for_controller)),
                 "CONTROLLER_CASE_HAS_UNRESOLVED_RUNNER_FAILURE:" + cid)
            need(not (cid in entered and cid not in done),
                 "CONTROLLER_CASE_ENTRY_REQUIRES_RECONCILIATION:" + cid)
            need(not (cid in done and cid not in labeled_for_controller),
                 "CONTROLLER_CASE_TRUTH_INGEST_REQUIRES_RECONCILIATION:" + cid)
    preentry_cid = FAILED_PREENTRY_AUTHORITY["case_id"]
    preentry_evidence = failed.get(preentry_cid)
    if args.reconcile_preentry_only:
        need(preentry_evidence is not None, "FAILED_PREENTRY_RECOVERY_EVIDENCE_MISSING")
        ledger_changed, status_changed = reconcile_failed_preentry(existing_ledger, status, preentry_evidence)
        if ledger_changed:
            write(LEDGER, existing_ledger)
        if status_changed:
            write(BATCH, status)
        _assert_failed_preentry_recorded(read(LEDGER), preentry_evidence)
        print(json.dumps({"mode": "RECONCILE_PREENTRY_NO_SOLVER", "case_id": preentry_cid,
            "old_run_id": FAILED_PREENTRY_AUTHORITY["run_id"], "attempt_id": "attempt_001",
            "sequence_index": 12, "entry_consumed": False, "solver_invocations": 0,
            "automatic_replay_count": 0, "entered_count": read(LEDGER).get("entered_count"),
            "truth_valid_count": read(LEDGER).get("truth_valid_count"),
            "labels_valid_count": read(LEDGER).get("labels_valid_count"),
            "current_case": read(LEDGER).get("current_case"), "solver_entries_this_call": 0}, indent=2),
            flush=True)
        return 0
    if controller is not None:
        prior_generation = int(resume_receipt.get("resume_generation", 0)) if resume_receipt else 0
        controller_status = {"schema": SCHEMA_CONTROLLER_STATUS, "state": "RUNNING",
            "controller_run_id": controller["manifest"]["controller_run_id"],
            "request_id": controller["request_id"],
            "controller_manifest_sha256": controller["manifest_sha256"],
            "queue_id": controller["queue_id"], "resume_generation": prior_generation,
            "startup_reconciled": False, "current_case_id": None,
            "unresolved_runner_request_ids": [],
            "runner_request_ids": list(resume_receipt.get("runner_request_ids", [])) if resume_receipt else [],
            "post_entry_automatic_replays": 0, "updated_at_utc": now()}
    if not args.execute:
        labeled = set(labels) | set(existing_ledger.get("labels_valid_case_ids", []))
        reconciliation_required = False
        if preentry_evidence is not None:
            if existing_ledger.get("current_case") is not None:
                reconciliation_required = True
            else:
                _assert_failed_preentry_recorded(existing_ledger, preentry_evidence)
        for failed_cid, evidence in failed.items():
            if evidence.get("entry_consumed") is True:
                _assert_failed_postentry_recorded(existing_ledger, evidence)
        first = next((cid for cid in queue_ids
                      if cid not in entered or (cid in done and cid not in labeled)), None)
        case_status = status.get("cases", {}).get(first, {})
        next_run = fresh_run_id(first, rr) if first and not reconciliation_required else None
        sequence = queue_ids.index(first) + len(INITIAL) + 1 if first else None
        print(json.dumps({"mode": "DRY_RUN_NO_SOLVER", "queue_manifest_sha256": qsha,
            "frozen_total": 128, "actual_runner_entries": len(entered), "actual_done_truth": len(done),
            "labels_valid_count": existing_ledger.get("labels_valid_count", len(labels)),
            "queue_cases_remaining": sum(1 for cid in queue_ids if cid not in entered),
            "next_case": first, "next_attempt_id": "attempt_001" if first else None,
            "next_sequence_index": sequence, "planned_run_id": next_run,
            "planned_run_id_is_new": bool(next_run and next_run != FAILED_PREENTRY_AUTHORITY["run_id"]),
            "preentry_reconciliation_required": reconciliation_required,
            "next_preflight_status": case_status.get("status"),
            "preflight_result_sha256": case_status.get("preflight_result_sha256"),
            "training_fits": existing_ledger.get("training_fits", 0),
            "p_scale_fits": existing_ledger.get("p_scale_fits", 0),
            "confirmation_access": existing_ledger.get("confirmation_response_access_count", 0),
            "solver_entries_this_call": 0}, indent=2), flush=True)
        return 0
    ledger = existing_ledger if existing_ledger else {
        "schema": "COUPLING_K6_V2_SERIAL_QUEUE_EXECUTION_LEDGER_V1",
        "queue_manifest_sha256": qsha, "started_at_utc": now(),
        "phase_timings_seconds": {"route_proof_and_preflight": 0.0, "run_one": 0.0, "truth_ingest": 0.0},
        "case_records": {}, "labels_valid_case_ids": list(INITIAL), "failed_or_isolated_cases": [],
        "current_case": None, "training_fits": 0, "p_scale_fits": 0,
        "confirmation_response_access_count": 0, "automatic_replay_count": 0}
    need(ledger.get("queue_manifest_sha256") == qsha, "LEDGER_QUEUE_SHA_MISMATCH")
    ledger["labels_valid_case_ids"] = sorted(set(ledger.get("labels_valid_case_ids", [])) | set(INITIAL))
    ledger["authorized_development_case_count"] = 128
    ledger["initial_label_evidence"] = labels
    update_counts(ledger, ids, runner_registry()[1])
    recovered_failed_current = False
    for failed_cid, evidence in failed.items():
        current_for_failure = ledger.get("current_case")
        if evidence.get("entry_consumed") is True:
            if isinstance(current_for_failure, dict) and current_for_failure.get("case_id") == failed_cid:
                record_failed_postentry_recovery(ledger, current_for_failure, evidence)
                recovered_failed_current = True
            else:
                _assert_failed_postentry_recorded(ledger, evidence)
        else:
            need(current_for_failure is None, "FAILED_PREENTRY_LEDGER_RECONCILIATION_REQUIRED:" + failed_cid)
            _assert_failed_preentry_recorded(ledger, evidence)
    if recovered_failed_current:
        status["current_case"] = None
        status["queue_phase"] = "QUEUE_ACTIVE"
        status["last_updated_utc"] = now()
        write(BATCH, status)
    current = ledger.get("current_case")
    if isinstance(current, dict) and current.get("case_id"):
        cid = current["case_id"]
        current_run_id = current.get("run_id")
        rows = [r for r in rows_for(rr, cid) if r.get("run_id") == current_run_id] if current_run_id else []
        if rows:
            need(len(rows) == 1, "CURRENT_RUN_DUPLICATE_REGISTRY_ROW:" + cid)
            state = runner_status(rows[0], cid)
            if state.get("state") == "DONE":
                if cid not in ledger["labels_valid_case_ids"]:
                    result = record_ingest(cid, registry.development[cid], rows[0], ingest)
                    need(result.get("status") == "PASS", "RESUMED_INGEST_NOT_PASS:" + cid)
                    ledger["labels_valid_case_ids"].append(cid)
                sequence = int(current.get("sequence_index", 0))
                ledger.setdefault("case_records", {}).setdefault(cid, {}).update({
                    "attempt_id": "attempt_001", "sequence_index": sequence, "phase": "LABEL_PASS",
                    "run_id": rows[0].get("run_id"), "run_directory": rows[0].get("run_dir"),
                    "runner_status_sha256": sha(Path(rows[0]["run_dir"]) / "status.json"),
                    "truth_h5_sha256": sha(Path(rows[0]["run_dir"]) / "truth.h5"),
                    "resumed_ingest_at_utc": now(),
                })
                ledger["current_case"] = None
            elif state.get("solver_entered") is True:
                raise StopQueue("POSTENTRY_RESUME_REQUIRES_ZERO_SOLVER_RECOVERY:" + cid)
            else:
                raise StopQueue("PREENTRY_RESUME_REQUIRES_AUDIT:" + cid)
        elif (RUN_ROOT / "runs" / cid / "attempt_001").exists():
            raise StopQueue("RUN_DIR_WITHOUT_REGISTRY_ON_RESUME:" + cid)
        else:
            ledger["current_case"] = None
    write(LEDGER, ledger)
    if controller is not None:
        controller_status["startup_reconciled"] = True
        controller_status["updated_at_utc"] = now()
        write(controller["status_path"], controller_status)
    print("QUEUE_START total=128 actual_entered=" + str(len(entered)) +
          " done_truth=" + str(len(done)) + " initial_labels=3 remaining=" +
          str(128 - len(entered)) + " queue_sha256=" + qsha, flush=True)
    for cid in queue_ids:
        evidence = failed.get(cid)
        if evidence and evidence.get("entry_consumed") is True:
            continue
        if cid in done and cid in ledger["labels_valid_case_ids"]:
            continue
        if cid in done and cid not in ledger["labels_valid_case_ids"]:
            raise StopQueue("DONE_CASE_INGEST_REQUIRES_RECONCILIATION:" + cid)
        run_case(cid, ids.index(cid) + 1, registry.development[cid], inputs, ledger,
                 controller=controller, controller_status=controller_status if controller is not None else None)
        _, rr, done, entered, failed = reconcile(ids, set(ledger["labels_valid_case_ids"]))
    update_counts(ledger, ids, runner_registry()[1])
    ledger["queue_status"] = "COMPLETE" if ledger["labels_valid_count"] == 128 else "PARTIAL"
    ledger["finished_at_utc"] = now()
    ledger["current_case"] = None
    write(LEDGER, ledger)
    status["current_case"] = None
    status["queue_phase"] = "QUEUE_COMPLETE"
    status["last_updated_utc"] = now()
    write(BATCH, status)
    if controller is not None:
        controller_status.update({"state": "DONE", "current_case_id": None,
            "unresolved_runner_request_ids": [], "startup_reconciled": True,
            "updated_at_utc": now()})
        write(controller["status_path"], controller_status)
    print("QUEUE_COMPLETE entered=" + str(ledger["entered_count"]) +
          " truth=" + str(ledger["truth_valid_count"]) +
          " labels=" + str(ledger["labels_valid_count"]), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StopQueue as exc:
        print("QUEUE_STOP:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
