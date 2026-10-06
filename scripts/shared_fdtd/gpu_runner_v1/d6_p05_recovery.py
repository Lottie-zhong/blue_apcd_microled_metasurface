# -*- coding: utf-8 -*-
"""Fixed, zero-solver closeout for the single orphaned D6_P05 pre-entry run.

This module is deliberately not a general recovery API. The public production
entry point accepts no case, attempt, run, path, or policy arguments.
"""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import runner as _runner


CASE_ID = "K6LDA1_DEV_D6_P05"
ATTEMPT_ID = "attempt_001"
RUN_ID = "K6V2_D6P05_20261006T063951Z_c6f073e5"
PRODUCTION_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
COUPLING_ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
CONTROL_DB = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
COUPLING_PACKET = COUPLING_ROOT / r"reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1"
CASE_OUTPUT = COUPLING_ROOT / r"outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6LDA1_DEV_D6_P05\attempt_001"
AUTHORITY_PATH = Path(__file__).resolve().parent / "controlled_admission_authority_v1.json"

_EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_PRODUCTION_PINS = {
    "case_id": CASE_ID,
    "attempt_id": ATTEMPT_ID,
    "run_id": RUN_ID,
    "lock_sha256": "5c0510149267ae2d9df9e853601c6b5c60195e49633b437ff881fcd0c45fcb28",
    "registry_sha256": "ba21857c1bfafcbb342819a5fa049fa8a1fe4649afd32067b519ebe627f0871a",
    "manifest_sha256": "87c0aca8e1596be49b7c6f51e54cd298a37ee1a127958c3120171924ef5eff41",
    "pending_status_sha256": "a0c58c1438c613cacf750cc1d020298dc0d42ea98f6105254243632cd62ea490",
    "pending_doc_sha256": "0edaf0a487f3182602585b0237ae771e42b0fc273f4901829ba0b17932f49bbc",
    "empty_sha256": _EMPTY_SHA,
    "lock_pid": 34072,
    "contract_sha256": "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5",
    "expansion_sha256": "4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f",
    "pre_fsp_sha256": "7b3a9f0a46ce8a001076b29bf2aee86ffd8b79107bc8babd270fd1d7e5e33e58",
    "envelope_sha256": "96f3f5d9f4e1d1055c0837d0c0a259618bade0d7e346eb4f4b269f563ce03d2e",
    "ledger_sha256": "0c4a7fd16b710412ced0b0fc7a465d2a30746bbb406e29566ce55b0fcd2211d1",
    "source_manifest_sha256": "ab6d929310fe6b329e54430dd1611a8ce811cdde12bb930d6e9bb6013e952edb",
    "authority_sha256": "a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35",
    "control_db_sha256": "af802fd46c023009f0a342cfa9540990c8e3a0df9b30af09ef62deeba817d9fe",
    "control_generation": 27,
}

_RECOVERY_DIR_NAME = "preentry_recovery_v1"
_MUTEX_NAME = "recovery_mutex.lock"
_CLAIM_NAME = "claim.json"
_DISPOSITION_NAME = "disposition.json"
_JOURNAL_NAME = "journal.json"
_ARCHIVE_NAME = "released_runner.lock"
_RECOVERY_FILES = {_MUTEX_NAME, _CLAIM_NAME, _DISPOSITION_NAME, _JOURNAL_NAME, _ARCHIVE_NAME}
_ACTIVE_STATES = {"PRECHECK_PASS", "SOLVER_ENTERED", "SOLVER_RETURNED"}


class RecoveryError(RuntimeError):
    pass


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _sha_file(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, ValueError) as exc:
        raise RecoveryError("JSON_READ_FAILED:" + str(path)) from exc
    if not isinstance(value, dict):
        raise RecoveryError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _write_exclusive_json(path, value):
    path = Path(path)
    payload = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True).encode("utf-8") + b"\n"
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _lock_recovery_mutex(path):
    if os.name != "nt":
        raise RecoveryError("WINDOWS_MUTEX_REQUIRED")
    import msvcrt
    path = Path(path)
    stream = path.open("a+b")
    try:
        if path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        return stream
    except OSError as exc:
        stream.close()
        raise RecoveryError("RECOVERY_ALREADY_RUNNING") from exc


def _unlock_recovery_mutex(stream):
    import msvcrt
    try:
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        stream.close()


def _windows_process_census():
    command = (
        "$ErrorActionPreference='Stop'; "
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine "
        "| ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=45,
    )
    if result.returncode != 0:
        raise RecoveryError("PROCESS_CENSUS_FAILED:" + str(result.returncode))
    try:
        value = json.loads(result.stdout.decode("utf-8-sig", errors="strict"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("PROCESS_CENSUS_JSON_INVALID") from exc
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _process_evidence(processes, lock_pid, run_dir, case_id, run_id):
    if not isinstance(processes, list):
        raise RecoveryError("PROCESS_CENSUS_INVALID")
    rows = []
    for item in processes:
        if not isinstance(item, dict):
            raise RecoveryError("PROCESS_CENSUS_ROW_INVALID")
        try:
            pid = int(item.get("ProcessId", item.get("pid")))
            ppid = int(item.get("ParentProcessId", item.get("ppid", 0)) or 0)
        except (TypeError, ValueError):
            raise RecoveryError("PROCESS_CENSUS_PID_INVALID")
        rows.append({"pid": pid, "ppid": ppid,
                     "name": str(item.get("Name", item.get("name", ""))),
                     "command_line": str(item.get("CommandLine", item.get("command_line", "")) or "")})
    by_pid = {row["pid"]: row for row in rows}
    descendants = set()
    changed = True
    while changed:
        changed = False
        for row in rows:
            if row["pid"] != lock_pid and (row["ppid"] == lock_pid or row["ppid"] in descendants):
                if row["pid"] not in descendants:
                    descendants.add(row["pid"])
                    changed = True
    norm_run_dir = str(run_dir).replace("/", "\\").casefold().rstrip("\\")
    target_tokens = (case_id.casefold(), run_id.casefold(), norm_run_dir)
    target_related = []
    for row in rows:
        command = row["command_line"].replace("/", "\\").casefold()
        name = row["name"].casefold()
        command_match = any(token and token in command for token in target_tokens)
        active_coupling_queue = ("k6_v2_pipeline\\serial_queue.py" in command
                                 and "--execute" in command)
        if row["pid"] == lock_pid or row["pid"] in descendants or command_match:
            target_related.append(row)
            continue
        if active_coupling_queue:
            raise RecoveryError("COUPLING_SERIAL_QUEUE_EXECUTION_PRESENT")
        if name.startswith("fdtd-engine") or name in {"fdtd-engine-msmpi.exe", "fdtd-engine.exe"}:
            target_related.append(row)
    if target_related:
        raise RecoveryError("TARGET_PROCESS_OR_ENGINE_PRESENT")
    # Unrelated long-lived fdtd-solutions API/server processes are deliberately
    # reported, but do not block this run unless they match the orphan PID tree
    # or contain the exact case, run, or run-directory identity.
    ignored_api = sorted(row["pid"] for row in rows
                         if row["name"].casefold() == "fdtd-solutions.exe"
                         and row["pid"] not in descendants
                         and row["pid"] != lock_pid
                         and not any(token in row["command_line"].replace("/", "\\").casefold()
                                     for token in target_tokens))
    return {"lock_pid": lock_pid, "lock_pid_present": lock_pid in by_pid,
            "descendant_pids": sorted(descendants), "target_related_pids": [],
            "ignored_unrelated_fdtd_solutions_pids": ignored_api,
            "process_census_sha256": _sha_bytes(_canonical(rows))}


def _check_control(snapshot, pins):
    if not isinstance(snapshot, dict):
        raise RecoveryError("CONTROL_SNAPSHOT_INVALID")
    if (snapshot.get("result") != "PASS" or snapshot.get("new_entry_hold") != 0
            or snapshot.get("active_global_hold_ids") != []
            or snapshot.get("health_status") != "PASS"
            or snapshot.get("control_generation") != pins["control_generation"]
            or snapshot.get("control_db_sha256") != pins["control_db_sha256"]):
        raise RecoveryError("CONTROL_STATE_NOT_PINNED_HEALTHY")
    return snapshot


def _target_paths(root, pins):
    run_dir = Path(root) / "runs" / pins["case_id"] / pins["attempt_id"] / pins["run_id"]
    return {
        "root": Path(root),
        "run_dir": run_dir,
        "lock": Path(root) / ".runner.lock",
        "active": Path(root) / "active_run.json",
        "registry": Path(root) / "registry.json",
        "manifest": run_dir / "manifest.json",
        "status": run_dir / "status.json",
        "validation": run_dir / "validation.json",
        "hashes": run_dir / "hashes.json",
        "solver_log": run_dir / "solver.log",
        "recovery": run_dir / _RECOVERY_DIR_NAME,
    }


def _validate_external_artifacts(pins):
    external = pins.get("external_artifacts", {})
    observed = {}
    for name, record in sorted(external.items()):
        path = Path(record["path"])
        if not path.is_file() or _sha_file(path) != record["sha256"]:
            raise RecoveryError("EXTERNAL_ARTIFACT_CHANGED:" + name)
        observed[name] = {"path": str(path.resolve()), "sha256": record["sha256"]}
    envelope = _read_json(external["envelope"]["path"])
    if (envelope.get("case_id") != pins["case_id"]
            or envelope.get("attempt_id") != pins["attempt_id"]
            or envelope.get("run_id") != pins["run_id"]
            or envelope.get("physical_contract_sha256") != pins["contract_sha256"]
            or envelope.get("expansion_manifest_sha256") != pins["expansion_sha256"]
            or envelope.get("physical_contract_path") != external["contract"]["path"]
            or envelope.get("pre_fsp_path") != external["pre_fsp"]["path"]
            or envelope.get("pre_fsp_sha256") != pins["pre_fsp_sha256"]):
        raise RecoveryError("COUPLING_ENVELOPE_IDENTITY_MISMATCH")
    admission = envelope.get("controlled_admission")
    if not isinstance(admission, dict):
        raise RecoveryError("CONTROLLED_ADMISSION_MISSING")
    expected_admission = {
        "route_version": "APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1",
        "case_class": "K6_FIXED_CONTRACT_GEOMETRY_VARIANT_V1",
        "source_manifest_path": external["source_manifest"]["path"],
        "source_manifest_sha256": pins["source_manifest_sha256"],
        "authority_path": external["authority"]["path"],
        "authority_sha256": pins["authority_sha256"],
    }
    if any(admission.get(key) != value for key, value in expected_admission.items()):
        raise RecoveryError("COUPLING_ADMISSION_BINDING_MISMATCH")
    ledger = _read_json(external["ledger"]["path"])
    record = ledger.get("case_records", {}).get(pins["case_id"])
    current = ledger.get("current_case")
    if (not isinstance(record, dict) or not isinstance(current, dict)
            or record.get("phase") != "RUN_ONE_IN_PROGRESS"
            or record.get("run_id") != pins["run_id"]
            or record.get("sequence_index") != 12
            or record.get("run_envelope_sha256") != pins["envelope_sha256"]
            or current.get("case_id") != pins["case_id"]
            or current.get("run_id") != pins["run_id"]
            or ledger.get("automatic_replay_count") != 0
            or ledger.get("entered_count") != 11
            or ledger.get("truth_valid_count") != 10):
        raise RecoveryError("COUPLING_LEDGER_TARGET_NOT_PINNED")
    observed["coupling_ledger_counts"] = {
        "entered_count": ledger.get("entered_count"),
        "truth_valid_count": ledger.get("truth_valid_count"),
        "automatic_replay_count": ledger.get("automatic_replay_count"),
        "target_phase": record.get("phase"), "target_sequence_index": record.get("sequence_index")}
    return observed


def _registry_rows(registry, paths, pins):
    if (registry.get("schema") != "APCD_GPU_RUNNER_REGISTRY_V1"
            or not isinstance(registry.get("runs"), list)):
        raise RecoveryError("REGISTRY_INVALID")
    rows = registry["runs"]
    targets = [r for r in rows if isinstance(r, dict) and r.get("run_id") == pins["run_id"]]
    if len(targets) != 1:
        raise RecoveryError("TARGET_REGISTRY_ROW_COUNT_INVALID")
    row = targets[0]
    if any(row.get(k) != pins[k] for k in ("case_id", "attempt_id", "run_id")):
        raise RecoveryError("TARGET_REGISTRY_IDENTITY_MISMATCH")
    if Path(row.get("run_dir", "")).resolve() != paths["run_dir"].resolve():
        raise RecoveryError("TARGET_REGISTRY_RUN_DIR_MISMATCH")
    other_pending = [r for r in rows if r is not row and r.get("state") == "PENDING"]
    active = [r for r in rows if r.get("state") in _ACTIVE_STATES]
    duplicate_attempt = [r for r in rows if r.get("case_id") == pins["case_id"]
                         and r.get("attempt_id") == pins["attempt_id"] and r is not row]
    if other_pending or active or duplicate_attempt:
        raise RecoveryError("OTHER_RUNNER_ACTIVITY_OR_DUPLICATE_ATTEMPT")
    return row, _sha_bytes(_canonical([r for r in rows if r is not row]))


def _read_journal(path, pins, fence):
    if not path.exists():
        return {"schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_JOURNAL_V1",
                "case_id": pins["case_id"], "attempt_id": pins["attempt_id"],
                "run_id": pins["run_id"], "fence_sha256": fence, "events": []}
    journal = _read_json(path)
    if (journal.get("schema") != "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_JOURNAL_V1"
            or any(journal.get(k) != pins[k] for k in ("case_id", "attempt_id", "run_id"))
            or journal.get("fence_sha256") != fence or not isinstance(journal.get("events"), list)):
        raise RecoveryError("RECOVERY_JOURNAL_IDENTITY_INVALID")
    previous = "0" * 64
    seen = set()
    for index, event in enumerate(journal["events"], 1):
        body = {k: v for k, v in event.items() if k != "event_sha256"}
        if (event.get("sequence") != index or event.get("previous_event_sha256") != previous
                or event.get("event_type") in seen
                or event.get("event_sha256") != _sha_bytes(_canonical(body))):
            raise RecoveryError("RECOVERY_JOURNAL_CHAIN_INVALID")
        previous = event["event_sha256"]
        seen.add(event["event_type"])
    return journal


def _append_event(path, journal, event_type, details):
    existing = next((e for e in journal["events"] if e.get("event_type") == event_type), None)
    if existing is not None:
        if existing.get("details") != details:
            raise RecoveryError("RECOVERY_JOURNAL_EVENT_CONFLICT:" + event_type)
        return journal
    previous = journal["events"][-1]["event_sha256"] if journal["events"] else "0" * 64
    event = {"sequence": len(journal["events"]) + 1,
             "event_type": event_type, "timestamp_unix": time.time(),
             "previous_event_sha256": previous, "details": details}
    event["event_sha256"] = _sha_bytes(_canonical(event))
    journal = dict(journal, events=journal["events"] + [event])
    _runner.atomic_json(path, journal)
    return journal


def _validate_initial_files(paths, pins, allow_recovery):
    if not paths["run_dir"].is_dir():
        raise RecoveryError("TARGET_RUN_DIRECTORY_MISSING")
    if paths["active"].exists():
        raise RecoveryError("ACTIVE_RUN_MARKER_PRESENT")
    children = {p.name: p for p in paths["run_dir"].iterdir()}
    required = {"manifest.json", "status.json", "validation.json", "hashes.json", "solver.log"}
    allowed = required | ({_RECOVERY_DIR_NAME} if allow_recovery else set())
    if (not required.issubset(children) or not set(children).issubset(allowed)
            or any(p.is_dir() and p.name != _RECOVERY_DIR_NAME for p in children.values())):
        raise RecoveryError("TARGET_RUN_DIRECTORY_CONTENTS_CHANGED")
    for name in required:
        if not children[name].is_file() or children[name].is_symlink():
            raise RecoveryError("TARGET_RUN_FILE_INVALID:" + name)
    hashes = {
        "manifest": _sha_file(paths["manifest"]),
        "validation": _sha_file(paths["validation"]),
        "hashes": _sha_file(paths["hashes"]),
        "solver_log": _sha_file(paths["solver_log"]),
    }
    if (hashes["manifest"] != pins["manifest_sha256"]
            or hashes["validation"] != pins["pending_doc_sha256"]
            or hashes["hashes"] != pins["pending_doc_sha256"]
            or hashes["solver_log"] != pins["empty_sha256"]):
        raise RecoveryError("TARGET_RUN_ARTIFACT_HASH_MISMATCH")
    manifest = _read_json(paths["manifest"])
    if (manifest.get("case_id") != pins["case_id"]
            or manifest.get("attempt_id") != pins["attempt_id"]
            or manifest.get("run_id") != pins["run_id"]
            or manifest.get("geometry") != [220, 195, 210, 150, 140, 215]
            or manifest.get("physical_contract_sha256") != pins["contract_sha256"]
            or manifest.get("expansion_manifest_sha256") != pins["expansion_sha256"]
            or manifest.get("pre_fsp_sha256") != pins["pre_fsp_sha256"]):
        raise RecoveryError("TARGET_MANIFEST_IDENTITY_MISMATCH")
    validation = _read_json(paths["validation"])
    hashes_doc = _read_json(paths["hashes"])
    if validation != {"state": "PENDING"} or hashes_doc != {"state": "PENDING"}:
        raise RecoveryError("TARGET_SETUP_PROOF_NOT_PENDING")
    pre_fsp = Path(manifest.get("pre_fsp_path", ""))
    if not pre_fsp.is_file() or _sha_file(pre_fsp) != pins["pre_fsp_sha256"]:
        raise RecoveryError("TARGET_PREFSP_CHANGED")
    return hashes


def _current_state(paths, pins, control_provider, process_provider, allow_terminal, registry_other_sha=None):
    external_evidence = _validate_external_artifacts(pins)
    control = _check_control(control_provider(), pins)
    process = _process_evidence(process_provider(), pins["lock_pid"], paths["run_dir"],
                                pins["case_id"], pins["run_id"])
    artifacts = _validate_initial_files(paths, pins, allow_recovery=True)
    registry = _read_json(paths["registry"])
    row, observed_other_sha = _registry_rows(registry, paths, pins)
    status = _read_json(paths["status"])
    identity = (status.get("case_id") == pins["case_id"]
                and status.get("attempt_id") == pins["attempt_id"]
                and status.get("run_id") == pins["run_id"])
    if not identity:
        raise RecoveryError("TARGET_STATUS_IDENTITY_MISMATCH")
    if status.get("state") == "PENDING" and row.get("state") == "PENDING":
        if (status.get("solver_entered") is not False or status.get("solver_invocations") != 0
                or _sha_file(paths["status"]) != pins["pending_status_sha256"]):
            raise RecoveryError("TARGET_NOT_FRESH_PENDING")
        if _sha_file(paths["registry"]) != pins["registry_sha256"]:
            raise RecoveryError("REGISTRY_BASELINE_HASH_MISMATCH")
    elif allow_terminal and status.get("state") == "FAILED_PREENTRY":
        fence = status.get("preentry_recovery_fence_sha256")
        disposition = paths["recovery"] / _DISPOSITION_NAME
        if (not fence or not disposition.is_file()
                or status.get("solver_entered") is not False
                or status.get("solver_invocations") != 0
                or status.get("automatic_replay_count") != 0
                or status.get("preentry_recovery_disposition_sha256") != _sha_file(disposition)):
            raise RecoveryError("TARGET_TERMINAL_STATE_NOT_OWNED_BY_RECOVERY")
        if row.get("state") not in {"PENDING", "FAILED_PREENTRY"}:
            raise RecoveryError("TARGET_REGISTRY_TERMINAL_STATE_INVALID")
        if registry_other_sha is not None and observed_other_sha != registry_other_sha:
            raise RecoveryError("OTHER_REGISTRY_ROWS_CHANGED")
    else:
        raise RecoveryError("TARGET_STATE_NOT_RECOVERABLE")
    return {"external_artifacts": external_evidence,
            "control": control, "process": process, "artifacts": artifacts,
            "registry": registry, "registry_row": row,
            "registry_other_rows_sha256": observed_other_sha,
            "status": status}


def _production_pins():
    target_run_dir = PRODUCTION_ROOT / "runs" / CASE_ID / ATTEMPT_ID / RUN_ID
    envelope_path = COUPLING_PACKET / ("RUN_ENVELOPE_" + RUN_ID + ".json")
    ledger_path = COUPLING_PACKET / "QUEUE_EXECUTION_LEDGER_V1.json"
    source_manifest = CASE_OUTPUT / "source_manifest.json"
    contract = CASE_OUTPUT / "physical_contract.json"
    pre_fsp = CASE_OUTPUT / "setup" / "runtime.fsp"
    return dict(_PRODUCTION_PINS, root=str(PRODUCTION_ROOT), lock_pid=34072,
        external_artifacts={
            "envelope":{"path":str(envelope_path),"sha256":_PRODUCTION_PINS["envelope_sha256"]},
            "ledger":{"path":str(ledger_path),"sha256":_PRODUCTION_PINS["ledger_sha256"]},
            "source_manifest":{"path":str(source_manifest),"sha256":_PRODUCTION_PINS["source_manifest_sha256"]},
            "authority":{"path":str(AUTHORITY_PATH),"sha256":_PRODUCTION_PINS["authority_sha256"]},
            "contract":{"path":str(contract),"sha256":_PRODUCTION_PINS["contract_sha256"]},
            "pre_fsp":{"path":str(pre_fsp),"sha256":_PRODUCTION_PINS["pre_fsp_sha256"]},
        })


def _fence_for(claim_basis):
    return _sha_bytes(_canonical(claim_basis))


def _validate_claim(claim, pins):
    if (claim.get("schema") != "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_CLAIM_V1"
            or any(claim.get(k) != pins[k] for k in ("case_id", "attempt_id", "run_id"))):
        raise RecoveryError("RECOVERY_CLAIM_IDENTITY_INVALID")
    basis = claim.get("fence_basis")
    if not isinstance(basis, dict) or claim.get("fence_sha256") != _fence_for(basis):
        raise RecoveryError("RECOVERY_CLAIM_FENCE_INVALID")
    expected_basis = {
        "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_FENCE_BASIS_V1",
        "case_id": pins["case_id"], "attempt_id": pins["attempt_id"],
        "run_id": pins["run_id"], "lock_sha256": pins["lock_sha256"],
        "registry_sha256": pins["registry_sha256"],
        "status_sha256": pins["pending_status_sha256"],
        "manifest_sha256": pins["manifest_sha256"],
    }
    if any(basis.get(key) != value for key, value in expected_basis.items()):
        raise RecoveryError("RECOVERY_CLAIM_BASELINE_MISMATCH")
    return claim


def _build_disposition(claim, pins, claim_sha256):
    basis = claim["fence_basis"]
    return {
        "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_PREENTRY_DISPOSITION_V1",
        "result": "FAILED_PREENTRY",
        "case_id": pins["case_id"], "attempt_id": pins["attempt_id"], "run_id": pins["run_id"],
        "recovery_fence_sha256": claim["fence_sha256"],
        "classification": "ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY",
        "solver_entered": False, "solver_invocations": 0,
        "physical_solver_entry_count": 0, "automatic_replay_count": 0,
        "truth_created": False, "truth_valid": False,
        "attempt_budget_consumed": False,
        "same_run_id_reuse_supported": False,
        "next_run_policy": "same case_id and attempt_id may use a new run_id only after Coupling ledger reconciliation and fresh official launch revalidation",
        "reason": "Runner status and registry remain PENDING with zero entry count; exact lock owner process is absent; no target process or solver/output/truth artifact exists.",
        "lock_original_sha256": pins["lock_sha256"],
        "claim_sha256": claim_sha256,
        "evidence": {
            "status_sha256_before": basis["status_sha256"],
            "registry_sha256_before": basis["registry_sha256"],
            "manifest_sha256": basis["manifest_sha256"],
            "control_snapshot_sha256": basis["control_snapshot_sha256"],
            "process_census_sha256": basis["process_census_sha256"],
            "coupling_artifacts": claim["immutable_artifacts"],
            "control_generation": pins["control_generation"],
        },
    }


def _record_step(path, journal, event_type, details, failpoint=None):
    journal = _append_event(path, journal, event_type, details)
    if failpoint:
        failpoint(event_type)
    return journal


def _recovered_result(paths, pins, claim_path, disposition_path, journal_path, archive_path,
                      result_name):
    return {
        "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_RESULT_V1",
        "result": result_name,
        "case_id": pins["case_id"], "attempt_id": pins["attempt_id"], "run_id": pins["run_id"],
        "solver_entered": False, "solver_invocations": 0,
        "automatic_replay_count": 0,
        "status_sha256": _sha_file(paths["status"]),
        "registry_sha256": _sha_file(paths["registry"]),
        "claim_sha256": _sha_file(claim_path),
        "disposition_sha256": _sha_file(disposition_path),
        "journal_sha256": _sha_file(journal_path),
        "archived_lock_sha256": _sha_file(archive_path),
        "archived_lock_path": str(archive_path),
        "next_run_id_required": True,
        "next_run_id_must_be_new": True,
        "next_run_must_wait_for_coupling_ledger_reconciliation": True,
    }


def _recover_fixed_run(root, pins, process_provider, control_provider, failpoint=None):
    paths = _target_paths(root, pins)
    recovery = paths["recovery"]
    if not recovery.exists():
        # Initial complete validation happens before creating the recovery area.
        first = _current_state(paths, pins, control_provider, process_provider,
                               allow_terminal=False)
        if _sha_file(paths["lock"]) != pins["lock_sha256"]:
            raise RecoveryError("RUNNER_LOCK_HASH_MISMATCH")
        lock_record = _read_json(paths["lock"])
        if (lock_record.get("pid") != pins["lock_pid"]
                or any(lock_record.get(k) != pins[k] for k in ("case_id", "attempt_id", "run_id"))):
            raise RecoveryError("RUNNER_LOCK_IDENTITY_MISMATCH")
        if _sha_file(paths["registry"]) != pins["registry_sha256"]:
            raise RecoveryError("REGISTRY_BASELINE_HASH_MISMATCH")
        os.mkdir(str(recovery))
    else:
        first = None
    if not recovery.is_dir() or recovery.is_symlink():
        raise RecoveryError("RECOVERY_DIRECTORY_INVALID")
    mutex_path = recovery / _MUTEX_NAME
    mutex = _lock_recovery_mutex(mutex_path)
    try:
        children = {p.name for p in recovery.iterdir()}
        if not children.issubset(_RECOVERY_FILES):
            raise RecoveryError("RECOVERY_DIRECTORY_UNEXPECTED_FILES")
        claim_path = recovery / _CLAIM_NAME
        disposition_path = recovery / _DISPOSITION_NAME
        journal_path = recovery / _JOURNAL_NAME
        archive_path = recovery / _ARCHIVE_NAME
        if not claim_path.exists():
            if first is None:
                first = _current_state(paths, pins, control_provider, process_provider,
                                       allow_terminal=False)
            if _sha_file(paths["lock"]) != pins["lock_sha256"]:
                raise RecoveryError("RUNNER_LOCK_HASH_MISMATCH")
            lock_record = _read_json(paths["lock"])
            if (lock_record.get("pid") != pins["lock_pid"]
                    or any(lock_record.get(k) != pins[k] for k in ("case_id", "attempt_id", "run_id"))):
                raise RecoveryError("RUNNER_LOCK_IDENTITY_MISMATCH")
            if _sha_file(paths["registry"]) != pins["registry_sha256"]:
                raise RecoveryError("REGISTRY_BASELINE_HASH_MISMATCH")
            basis = {
                "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_FENCE_BASIS_V1",
                "case_id": pins["case_id"], "attempt_id": pins["attempt_id"], "run_id": pins["run_id"],
                "lock_sha256": _sha_file(paths["lock"]),
                "registry_sha256": _sha_file(paths["registry"]),
                "status_sha256": _sha_file(paths["status"]),
                "manifest_sha256": _sha_file(paths["manifest"]),
                "control_snapshot_sha256": first["control"]["snapshot_sha256"],
                "process_census_sha256": first["process"]["process_census_sha256"],
            }
            fence = _fence_for(basis)
            claim = {
                "schema": "APCD_GPU_RUNNER_V1_P05_ORPHAN_RECOVERY_CLAIM_V1",
                "case_id": pins["case_id"], "attempt_id": pins["attempt_id"], "run_id": pins["run_id"],
                "fence_basis": basis, "fence_sha256": fence,
                "started_unix": time.time(),
                "immutable_artifacts": first["external_artifacts"],
                "target_artifacts": first["artifacts"],
                "registry_other_rows_sha256": first["registry_other_rows_sha256"],
                "control_snapshot": first["control"],
                "process_snapshot": first["process"],
            }
            _write_exclusive_json(claim_path, claim)
            claim = _validate_claim(_read_json(claim_path), pins)
            _write_exclusive_json(disposition_path,
                                  _build_disposition(claim, pins, _sha_file(claim_path)))
        claim = _validate_claim(_read_json(claim_path), pins)
        fence = claim["fence_sha256"]
        if not disposition_path.is_file():
            # The claim is durable. Reconstruct the deterministic disposition if
            # interruption occurred between the two atomic file writes.
            _write_exclusive_json(disposition_path,
                                  _build_disposition(claim, pins, _sha_file(claim_path)))
        disposition = _read_json(disposition_path)
        if (disposition.get("recovery_fence_sha256") != fence
                or disposition.get("claim_sha256") != _sha_file(claim_path)):
            raise RecoveryError("RECOVERY_DISPOSITION_BINDING_INVALID")
        if archive_path.exists() and _sha_file(archive_path) != pins["lock_sha256"]:
            raise RecoveryError("ARCHIVED_LOCK_HASH_MISMATCH")
        journal = _read_journal(journal_path, pins, fence)
        if archive_path.is_file() and not paths["lock"].exists():
            status_after = _read_json(paths["status"])
            registry_after = _read_json(paths["registry"])
            target_rows = [row for row in registry_after.get("runs", [])
                           if isinstance(row, dict) and row.get("run_id") == pins["run_id"]]
            event_types = {event.get("event_type") for event in journal["events"]}
            if (len(target_rows) == 1
                    and status_after.get("state") == "FAILED_PREENTRY"
                    and status_after.get("preentry_recovery_fence_sha256") == fence
                    and status_after.get("preentry_recovery_disposition_sha256") == _sha_file(disposition_path)
                    and status_after.get("solver_entered") is False
                    and status_after.get("solver_invocations") == 0
                    and target_rows[0].get("state") == "FAILED_PREENTRY"
                    and target_rows[0].get("preentry_recovery_fence_sha256") == fence
                    and target_rows[0].get("preentry_recovery_disposition_sha256") == _sha_file(disposition_path)
                    and "RELEASE_READY" in event_types and "LOCK_RELEASE_INTENT" in event_types):
                return _recovered_result(paths, pins, claim_path, disposition_path,
                                         journal_path, archive_path, "ALREADY_RECOVERED")
        current = _current_state(paths, pins, control_provider, process_provider,
                                 allow_terminal=True,
                                 registry_other_sha=claim["registry_other_rows_sha256"])
        journal = _record_step(journal_path, journal, "CLAIMED", {
            "claim_sha256": _sha_file(claim_path), "disposition_sha256": _sha_file(disposition_path),
            "fence_sha256": fence,
        }, failpoint)

        status = current["status"]
        row = current["registry_row"]
        terminal_details = {"fence_sha256": fence,
                            "disposition_sha256": _sha_file(disposition_path),
                            "solver_entered": False, "solver_invocations": 0,
                            "automatic_replay_count": 0}
        if status.get("state") == "PENDING":
            journal = _record_step(journal_path, journal, "STATUS_TERMINALIZATION_INTENT",
                                   terminal_details, failpoint)
            # Recheck immutable inputs, controller hold, lock owner process, and exact inputs
            # at the mutation boundary. The only runner lock is still the pinned stale lock.
            _current_state(paths, pins, control_provider, process_provider,
                           allow_terminal=False,
                           registry_other_sha=claim["registry_other_rows_sha256"])
            if not paths["lock"].is_file() or _sha_file(paths["lock"]) != pins["lock_sha256"]:
                raise RecoveryError("RUNNER_LOCK_CHANGED_BEFORE_TERMINALIZATION")
            status = _runner._transition(
                paths["run_dir"], status, "FAILED_PREENTRY",
                failure="ORPHANED_RUNNER_LOCK_BEFORE_SOLVER_ENTRY",
                solver_entered=False, solver_invocations=0, automatic_replay_count=0,
                preentry_recovery_fence_sha256=fence,
                preentry_recovery_disposition_sha256=_sha_file(disposition_path),
                preentry_recovery_claim_sha256=_sha_file(claim_path),
                preentry_recovery_unix=time.time())
            if failpoint:
                failpoint("AFTER_STATUS_WRITE")
        journal = _record_step(journal_path, journal, "STATUS_TERMINALIZED", {
            **terminal_details, "status_sha256": _sha_file(paths["status"]),
        }, failpoint)

        registry = _read_json(paths["registry"])
        row, other_sha = _registry_rows(registry, paths, pins)
        if other_sha != claim["registry_other_rows_sha256"]:
            raise RecoveryError("OTHER_REGISTRY_ROWS_CHANGED")
        if row.get("state") == "PENDING":
            journal = _record_step(journal_path, journal, "REGISTRY_TERMINALIZATION_INTENT",
                                   terminal_details, failpoint)
            row.update(state="FAILED_PREENTRY",
                       preentry_recovery_fence_sha256=fence,
                       preentry_recovery_disposition_sha256=_sha_file(disposition_path),
                       solver_entered=False, solver_invocations=0,
                       automatic_replay_count=0)
            _runner.atomic_json(paths["registry"], registry)
            if failpoint:
                failpoint("AFTER_REGISTRY_WRITE")
        elif (row.get("state") != "FAILED_PREENTRY"
              or row.get("preentry_recovery_fence_sha256") != fence
              or row.get("preentry_recovery_disposition_sha256") != _sha_file(disposition_path)
              or row.get("solver_entered") is not False
              or row.get("solver_invocations") != 0):
            raise RecoveryError("REGISTRY_TERMINALIZATION_CONFLICT")
        journal = _record_step(journal_path, journal, "REGISTRY_TERMINALIZED", {
            **terminal_details, "registry_sha256": _sha_file(paths["registry"]),
        }, failpoint)

        final_status = _read_json(paths["status"])
        final_registry = _read_json(paths["registry"])
        final_row, final_other_sha = _registry_rows(final_registry, paths, pins)
        if (final_status.get("state") != "FAILED_PREENTRY"
                or final_status.get("preentry_recovery_fence_sha256") != fence
                or final_status.get("solver_entered") is not False
                or final_status.get("solver_invocations") != 0
                or final_status.get("automatic_replay_count") != 0
                or final_row.get("state") != "FAILED_PREENTRY"
                or final_row.get("preentry_recovery_fence_sha256") != fence
                or final_other_sha != claim["registry_other_rows_sha256"]):
            raise RecoveryError("TERMINAL_STATE_VERIFY_FAILED")
        if _sha_file(paths["status"]) == pins["pending_status_sha256"]:
            raise RecoveryError("STATUS_NOT_TERMINALIZED")
        journal = _record_step(journal_path, journal, "RELEASE_READY", {
            **terminal_details,
            "status_sha256": _sha_file(paths["status"]),
            "registry_sha256": _sha_file(paths["registry"]),
            "lock_archive_path": str(archive_path),
        }, failpoint)
        journal = _record_step(journal_path, journal, "LOCK_RELEASE_INTENT", {
            **terminal_details,
            "original_lock_sha256": pins["lock_sha256"],
            "archive_path": str(archive_path),
        }, failpoint)

        # Final fail-closed check. The global lock is released only after both durable
        # terminal records and the release intent exist. os.replace archives exact bytes.
        _validate_external_artifacts(pins)
        _check_control(control_provider(), pins)
        _process_evidence(process_provider(), pins["lock_pid"], paths["run_dir"],
                          pins["case_id"], pins["run_id"])
        if paths["active"].exists():
            raise RecoveryError("ACTIVE_RUN_MARKER_APPEARED")
        if paths["lock"].exists():
            if archive_path.exists() or _sha_file(paths["lock"]) != pins["lock_sha256"]:
                raise RecoveryError("RUNNER_LOCK_CHANGED_BEFORE_RELEASE")
            os.replace(str(paths["lock"]), str(archive_path))
        if not archive_path.is_file() or _sha_file(archive_path) != pins["lock_sha256"]:
            raise RecoveryError("RUNNER_LOCK_ARCHIVE_VERIFY_FAILED")
        if paths["lock"].exists():
            raise RecoveryError("RUNNER_LOCK_STILL_PRESENT")
        if failpoint:
            failpoint("AFTER_LOCK_ARCHIVE")
        # No filesystem mutation follows the atomic lock rename; the archived lock is
        # the durable completion marker for the final release action.
        return _recovered_result(paths, pins, claim_path, disposition_path,
                                 journal_path, archive_path, "RECOVERED_FAILED_PREENTRY")
    finally:
        _unlock_recovery_mutex(mutex)


def _windows_control_provider():
    try:
        import adapter
        return adapter.read_global_entry_control()
    except Exception as exc:
        raise RecoveryError("OFFICIAL_CONTROL_READ_FAILED:" + type(exc).__name__) from exc


def recover_d6_p05_orphan_preentry_production():
    """Official fixed identity API. Zero solver calls; no caller-selectable target."""
    pins = _production_pins()
    return _recover_fixed_run(PRODUCTION_ROOT, pins, _windows_process_census,
                              _windows_control_provider)


if __name__ == "__main__":
    print(json.dumps(recover_d6_p05_orphan_preentry_production(), sort_keys=True, indent=2))
