from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path
from shared_fdtd.control_v3.allocator import Allocator, BranchCapReached, Lease, NoFreeSlot
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.control_v3.resources import ResourceCapacityWait, ResourceRequest, read_resource_snapshot
from shared_fdtd.engine.event_log import append_event, read_events

_PREENTRY_TERMINAL_STATES = {
    "RELEASED", "FAILED_PREENTRY", "FAILED_AFTER_ENTRY", "POSTENTRY_NO_TRUTH",
    "TERMINAL_QUARANTINED", "AMBIGUOUS_QUARANTINED", "RECOVERED_ADOPTED",
}
_PREENTRY_PENDING_EVENTS = {
    "NATIVE_TRUTH_PERSISTING", "POSTPROCESSING", "RELEASE_PENDING",
    "PENDING_RECONCILE", "PERSISTENCE_PENDING", "FRESH_LOAD_PENDING",
}


def _attempt_truth_blockers(attempt_root):
    root = Path(attempt_root)
    if not root.is_dir():
        return ["MISSING_ATTEMPT_ROOT"]
    blockers = []
    setup_hashes = set()
    ledger_path = root / "attempt_ledger.json"
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        ledger = {}
    declared = str(ledger.get("pre_fsp_sha256") or "").strip().lower()
    if len(declared) == 64 and all(char in "0123456789abcdef" for char in declared):
        setup_hashes.add(declared)
    setup_dir = root / "setup"
    for setup_path in setup_dir.glob("*.fsp"):
        try:
            setup_hashes.add(hashlib.sha256(setup_path.read_bytes()).hexdigest().lower())
        except OSError:
            pass
    truth_names = {
        "terminal.json", "terminal_failure.json", "postentry_no_truth_closeout.json",
        "fresh_load_validation.json", "fresh_load.json",
    }
    truth_dirs = {"native", "raw", "archive", "hf", "truth", "post"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        parts = {part.lower() for part in path.relative_to(root).parts[:-1]}
        suffix = path.suffix.lower()
        if name == "terminal_failure.json":
            try:
                failure = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                failure = None
            if not (
                isinstance(failure, dict)
                and failure.get("solver_entered") is False
                and failure.get("solver_returned") is False
                and failure.get("queue_state") == "FAILED_PREENTRY"
                and failure.get("rerun") is False
            ):
                blockers.append(str(path))
        elif name in truth_names or suffix in {".h5", ".hdf5"}:
            blockers.append(str(path))
        elif suffix == ".fsp" and "setup" not in parts:
            try:
                setup_only_copy = hashlib.sha256(path.read_bytes()).hexdigest().lower() in setup_hashes
            except OSError:
                setup_only_copy = False
            if not setup_only_copy:
                blockers.append(str(path))
        elif parts & truth_dirs:
            blockers.append(str(path))
        elif name.endswith(".pending") or "persistence_pending" in name:
            blockers.append(str(path))
    return sorted(set(blockers))


def _default_preentry_process_probe(attempt_root, events):
    import psutil

    host_event = next((event for event in reversed(events) if event.get("event_type") == "HOST_PROCESS_STARTED"), None)
    host_pid = int(host_event["host_pid"]) if host_event and host_event.get("host_pid") else None
    attempt_token = Path(attempt_root).name.lower()
    case_token = Path(attempt_root).parent.name.lower()
    root_token = str(Path(attempt_root)).lower()

    def lineage_contains(pid, ancestor):
        seen = set()
        current = pid
        for _ in range(64):
            if current in seen:
                return False
            seen.add(current)
            if current == ancestor:
                return True
            try:
                current = psutil.Process(current).ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        return False

    matches = []
    for process in psutil.process_iter(["pid", "ppid", "name", "cmdline", "create_time"]):
        try:
            info = process.info
            pid = int(info["pid"])
            command = " ".join(info.get("cmdline") or [])
            lowered = command.lower()
            name = str(info.get("name") or "").lower()
            observer_or_controller = any(token in lowered for token in (
                "external_process_watcher.py", "gpu_telemetry.py",
                "v3_dispatcher_service.py", "v3_reconciler_service.py",
            ))
            candidate_name = name in {
                "python.exe", "pythonw.exe", "fdtd-solutions.exe",
                "fdtd-engine-msmpi.exe", "fdtd-engine.exe", "mpiexec.exe", "smpd.exe",
            }
            relevant = (
                pid == host_pid
                or (host_pid is not None and candidate_name and lineage_contains(pid, host_pid))
                or (not observer_or_controller and root_token in lowered)
                or (not observer_or_controller and case_token in lowered and attempt_token in lowered)
            )
            if relevant:
                matches.append({
                    "pid": pid,
                    "ppid": info.get("ppid"),
                    "name": info.get("name"),
                    "cmdline": command,
                    "create_time": info.get("create_time"),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if matches:
        return {"status": "BLOCKED", "reason": "PROCESS_FAMILY_ALIVE_OR_PID_REUSED", "processes": matches}
    return {"status": "PASS", "processes": [], "recorded_host_pid": host_pid}


def _call_preentry_process_probe(process_probe, attempt_root, events):
    result = (process_probe or _default_preentry_process_probe)(attempt_root, events)
    if isinstance(result, list):
        return {"status": "BLOCKED" if result else "PASS", "processes": result}
    if not isinstance(result, dict) or result.get("status") not in {"PASS", "BLOCKED", "AMBIGUOUS"}:
        return {"status": "BLOCKED", "reason": "INVALID_PROCESS_PROBE_RESULT"}
    return result


def _event_sources(attempt_root, runtime_root=None):
    roots = [Path(attempt_root)]
    if runtime_root is not None and Path(runtime_root) not in roots:
        roots.append(Path(runtime_root))
    events = []
    for root in roots:
        events.extend(read_events(root / "events.jsonl"))
    return events


def _write_json_durable(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    with tmp.open("r+b") as handle:
        os.fsync(handle.fileno())
    tmp.replace(path)


def _active_attempt_resource_refs(con, branch, case, attempt):
    active = ("RESERVED", "LIVE", "RELEASE_PENDING", "OWNER_QUARANTINED")
    result = {"resource_reservations": [], "gpu_capacity_leases": []}
    for table, key in (("resource_reservations", "resource_reservations"), ("gpu_capacity_leases", "gpu_capacity_leases")):
        exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists:
            rows = con.execute(
                f"SELECT * FROM {table} WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state IN (?,?,?,?)",
                (branch, case, attempt, *active),
            ).fetchall()
            result[key] = [dict(row) for row in rows]
    return result


def _stale_preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe):
    row = con.execute(
        "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (branch, case, attempt),
    ).fetchone()
    if row is None:
        return {"ok": False, "status": "NOT_FOUND", "case": case, "attempt": attempt}
    state = row["state"]
    if state not in {"QUEUED", "WAIT_RESOURCE_CAPACITY", "SLOT_ACQUIRED", "HOST_START_INTENT"}:
        return {"ok": False, "status": "NOT_ELIGIBLE", "state": state, "case": case, "attempt": attempt}
    copies = con.execute(
        "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (branch, case, attempt),
    ).fetchone()[0]
    if copies != 1:
        return {"ok": False, "status": "BLOCKED", "reason": "DUPLICATE_QUEUE_ROWS", "count": copies, "case": case, "attempt": attempt}
    control = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
    if control is None or int(control["new_entry_hold"]) != 1:
        return {"ok": False, "status": "BLOCKED", "reason": "RECOVERY_REQUIRES_NEW_ENTRY_HOLD"}
    ledger_path = Path(attempt_root) / "attempt_ledger.json"
    if not ledger_path.is_file():
        return {"ok": False, "status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_MISSING_LEDGER", "case": case, "attempt": attempt}
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"ok": False, "status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_INVALID_LEDGER", "case": case, "attempt": attempt}
    if (
        ledger.get("solver_entered") is not False
        or ledger.get("solver_returned") is not False
        or int(ledger.get("run_invocation_count", -1)) != 0
    ):
        return {"ok": False, "status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_LEDGER_NOT_ZERO", "case": case, "attempt": attempt}
    entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
        (branch, case, attempt),
    ).fetchone()[0]
    gpu_entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='GPU_ENGINE_ENTRY_CONFIRMED'",
        (branch, case, attempt),
    ).fetchone()[0]
    if entries or gpu_entries:
        return {"ok": False, "status": "BLOCKED", "reason": "SCIENTIFIC_ENTRY_ALREADY_RECORDED", "scientific_entry_count": entries, "gpu_engine_entry_count": gpu_entries}
    newer = con.execute(
        "SELECT logical_case_id,attempt_id,state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id<>? AND state NOT IN ({})".format(
            ",".join("?" for _ in _PREENTRY_TERMINAL_STATES)
        ),
        (branch, case, attempt, *_PREENTRY_TERMINAL_STATES),
    ).fetchall()
    if newer:
        return {"ok": False, "status": "BLOCKED", "reason": "NEWER_ATTEMPT_ACTIVE", "newer_attempts": [dict(item) for item in newer]}
    events = read_events(Path(attempt_root) / "events.jsonl")
    event_types = {event.get("event_type") for event in events}
    db_event_types = {
        item[0]
        for item in con.execute(
            "SELECT event_type FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchall()
    }
    pending = sorted((event_types | db_event_types) & _PREENTRY_PENDING_EVENTS)
    truth_blockers = _attempt_truth_blockers(attempt_root)
    if pending:
        return {"ok": False, "status": "BLOCKED", "reason": "PERSISTENCE_OR_POSTPROCESS_PENDING", "pending_events": pending}
    if truth_blockers:
        return {"ok": False, "status": "BLOCKED", "reason": "TRUTH_BUNDLE_PRESENT", "truth_blockers": truth_blockers}
    process = _call_preentry_process_probe(process_probe, attempt_root, events)
    if process.get("status") != "PASS":
        return {"ok": False, "status": "BLOCKED", "reason": process.get("reason", "PROCESS_FAMILY_ALIVE_OR_AMBIGUOUS"), "process": process}
    resources = _active_attempt_resource_refs(con, branch, case, attempt)
    permit_rows = []
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='exact_launch_permits'").fetchone():
        permit_rows = [dict(item) for item in con.execute(
            "SELECT * FROM exact_launch_permits WHERE branch_id=? AND logical_case_id=? AND attempt_id=? ORDER BY created_at",
            (branch, case, attempt),
        ).fetchall()]
    lease = None
    refs = (row["slot_id"], row["lease_token_hash"], row["fencing_generation"])
    if any(value is not None for value in refs) and not all(value is not None for value in refs):
        return {"ok": False, "status": "BLOCKED", "reason": "PARTIAL_STALE_QUEUE_IDENTITY"}
    if row["slot_id"]:
        slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
        if slot is None:
            return {"ok": False, "status": "BLOCKED", "reason": "MISSING_SLOT"}
        historical = con.execute(
            "SELECT event_id FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='LEASE_ACQUIRED' AND slot_id=? AND lease_token_hash=? AND fencing_generation=? ORDER BY event_id DESC LIMIT 1",
            (branch, case, attempt, row["slot_id"], row["lease_token_hash"], row["fencing_generation"]),
        ).fetchone()
        if historical is None:
            return {"ok": False, "status": "BLOCKED", "reason": "QUEUE_IDENTITY_UNPROVEN"}
        if slot["state"] == "FREE":
            if resources["resource_reservations"] or resources["gpu_capacity_leases"]:
                return {"ok": False, "status": "BLOCKED", "reason": "ACTIVE_RESERVATION_WITHOUT_OWNER", "resources": resources}
        else:
            matches = (
                slot["owner_branch"] == branch
                and slot["logical_case_id"] == case
                and slot["attempt_id"] == attempt
                and slot["lease_token"]
                and hashlib.sha256(slot["lease_token"].encode()).hexdigest() == row["lease_token_hash"]
                and int(slot["fencing_generation"]) == int(row["fencing_generation"])
            )
            if not matches:
                return {"ok": False, "status": "BLOCKED", "reason": "OWNER_OR_FENCING_MISMATCH"}
            lease = Lease(slot["slot_id"], branch, case, attempt, slot["lease_token"], int(slot["fencing_generation"]), int(control["control_generation"]))
    elif resources["resource_reservations"] or resources["gpu_capacity_leases"]:
        return {"ok": False, "status": "BLOCKED", "reason": "ACTIVE_RESERVATION_WITHOUT_QUEUE_OWNER", "resources": resources}
    return {
        "ok": True,
        "row": dict(row),
        "lease": lease,
        "events": events,
        "process": process,
        "ledger": ledger,
        "permit_rows": permit_rows,
        "resources": resources,
    }


def _dead_host_snapshot(con, branch, case, attempt, attempt_root, runtime_root=None, process_probe=None):
    """Strict snapshot for a host that died before creating an attempt ledger."""
    row = con.execute(
        "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (branch, case, attempt),
    ).fetchone()
    if row is None:
        return {"ok": False, "status": "NOT_FOUND", "case": case, "attempt": attempt}
    if row["state"] != "HOST_STARTED":
        return {"ok": False, "status": "NOT_ELIGIBLE", "state": row["state"], "case": case, "attempt": attempt}
    control = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
    if control is None:
        return {"ok": False, "status": "BLOCKED", "reason": "MISSING_ADMISSION_CONTROL"}
    copies = con.execute(
        "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (branch, case, attempt),
    ).fetchone()[0]
    if copies != 1:
        return {"ok": False, "status": "BLOCKED", "reason": "DUPLICATE_QUEUE_ROWS", "count": copies}
    entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
        (branch, case, attempt),
    ).fetchone()[0]
    gpu_entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='GPU_ENGINE_ENTRY_CONFIRMED'",
        (branch, case, attempt),
    ).fetchone()[0]
    events = _event_sources(attempt_root, runtime_root)
    event_types = {event.get("event_type") for event in events}
    if entries or gpu_entries or {"SCIENTIFIC_SOLVER_ENTERED", "GPU_ENGINE_ENTRY_CONFIRMED"} & event_types:
        return {"ok": False, "status": "BLOCKED", "reason": "SCIENTIFIC_ENTRY_ALREADY_RECORDED", "scientific_entry_count": entries, "gpu_engine_entry_count": gpu_entries}
    if "HOST_PROCESS_STARTED" not in event_types:
        return {"ok": False, "status": "BLOCKED", "reason": "MISSING_HOST_PROCESS_START_EVIDENCE"}
    pending = sorted(event_types & _PREENTRY_PENDING_EVENTS)
    if pending:
        return {"ok": False, "status": "BLOCKED", "reason": "PERSISTENCE_OR_POSTPROCESS_PENDING", "pending_events": pending}
    truth_blockers = _attempt_truth_blockers(attempt_root)
    if truth_blockers:
        return {"ok": False, "status": "BLOCKED", "reason": "TRUTH_BUNDLE_PRESENT", "truth_blockers": truth_blockers}
    process = _call_preentry_process_probe(process_probe, attempt_root, events)
    if process.get("status") != "PASS":
        return {"ok": False, "status": "BLOCKED", "reason": process.get("reason", "PROCESS_FAMILY_ALIVE_OR_AMBIGUOUS"), "process": process}
    refs = (row["slot_id"], row["lease_token_hash"], row["fencing_generation"])
    if not all(value is not None for value in refs):
        return {"ok": False, "status": "BLOCKED", "reason": "PARTIAL_STALE_QUEUE_IDENTITY"}
    slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
    if slot is None or slot["state"] == "FREE":
        return {"ok": False, "status": "BLOCKED", "reason": "MISSING_ACTIVE_OWNER"}
    matches = (
        slot["owner_branch"] == branch and slot["logical_case_id"] == case and slot["attempt_id"] == attempt
        and slot["lease_token"]
        and hashlib.sha256(slot["lease_token"].encode()).hexdigest() == row["lease_token_hash"]
        and int(slot["fencing_generation"]) == int(row["fencing_generation"])
    )
    if not matches:
        return {"ok": False, "status": "BLOCKED", "reason": "OWNER_OR_FENCING_MISMATCH"}
    control_generation = int(control["control_generation"])
    lease = Lease(slot["slot_id"], branch, case, attempt, slot["lease_token"], int(slot["fencing_generation"]), control_generation)
    host_event = next((event for event in reversed(events) if event.get("event_type") == "HOST_PROCESS_STARTED"), {})
    return {"ok": True, "row": dict(row), "slot": dict(slot), "lease": lease, "events": events, "process": process, "host_event": host_event}


def reconcile_dead_preentry_host(db, branch, case, attempt, attempt_root, runtime_root=None, process_probe=None):
    """Terminalize a dead pre-entry host through the normal allocator/fence path."""
    with db.connect(readonly=True) as con:
        initial = _dead_host_snapshot(con, branch, case, attempt, attempt_root, runtime_root, process_probe)
    if not initial.get("ok"):
        return initial
    with db.immediate() as con:
        final = _dead_host_snapshot(con, branch, case, attempt, attempt_root, runtime_root, process_probe)
        if not final.get("ok"):
            return final
        changed = con.execute(
            "UPDATE branch_queue SET state='FAILED_PREENTRY',updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='HOST_STARTED' AND slot_id=? AND fencing_generation=?",
            (utc_now(), branch, case, attempt, final["row"]["slot_id"], final["row"]["fencing_generation"]),
        ).rowcount
        if changed != 1:
            return {"status": "BLOCKED", "reason": "PREENTRY_RECOVERY_QUEUE_REVALIDATION_FAILED", "case": case, "attempt": attempt}
    lease = final["lease"]
    released = Allocator(db).release_owned_idempotent(lease, scientific_terminal="FAILED_PREENTRY")
    if released["status"] not in {"RELEASED", "ALREADY_FREE"}:
        return {"status": "RECOVERY_PENDING_RELEASE", "release": released, "case": case, "attempt": attempt}
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='FAILED_PREENTRY'",
            (utc_now(), branch, case, attempt),
        )
    host_event = final.get("host_event") or {}
    evidence = {
        "schema": "APCD_SHARED_V3_PREENTRY_HOST_EXIT_V1",
        "classification": "PRE_ENTRY_HOST_LAUNCH_FAILURE",
        "queue_state": "FAILED_PREENTRY",
        "branch_id": branch,
        "case_id": case,
        "attempt_id": attempt,
        "host_pid": host_event.get("host_pid"),
        "launch_timestamp_utc": host_event.get("launch_timestamp_utc") or host_event.get("timestamp"),
        "exit_detection_timestamp_utc": utc_now(),
        "return_code": None,
        "stdout_path": host_event.get("stdout_path"),
        "stderr_path": host_event.get("stderr_path"),
        "scientific_solver_entry_count": 0,
        "solver_entered": False,
        "retry_eligibility": "PENDING_ZERO_SOLVER_VALIDATION",
        "release": released,
        "process_probe": final.get("process"),
    }
    _write_json_durable(Path(attempt_root) / "preentry_host_exit.json", evidence)
    _write_json_durable(Path(attempt_root) / "terminal_failure.json", {
        **evidence,
        "status": "PRE_ENTRY_HOST_LAUNCH_FAILURE",
        "solver_returned": False,
        "rerun": False,
    })
    roots = [Path(attempt_root)]
    if runtime_root is not None and Path(runtime_root) not in roots:
        roots.append(Path(runtime_root))
    for root in roots:
        append_event(root / "events.jsonl", "PRE_ENTRY_HOST_EXIT", **evidence)
    return {
        "status": "RECOVERED_DEAD_PREENTRY_HOST",
        "case": case,
        "attempt": attempt,
        "scientific_solver_entry_count": 0,
        "retry_eligibility": "PENDING_ZERO_SOLVER_VALIDATION",
        "release": released,
        "host_pid": evidence["host_pid"],
    }


def mark_preentry_retry_eligible(db, branch, case, attempt, attempt_root, validation_manifest):
    """Promote a recorded zero-entry pre-entry failure only after validation evidence passes."""
    manifest = Path(validation_manifest)
    try:
        validation = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"status": "BLOCKED", "reason": "ZERO_SOLVER_VALIDATION_MANIFEST_INVALID"}
    if not (
        validation.get("status") == "PASS"
        and int(validation.get("solver_runs", -1)) == 0
        and int(validation.get("scientific_solver_entries", -1)) == 0
    ):
        return {"status": "BLOCKED", "reason": "ZERO_SOLVER_VALIDATION_NOT_PASS"}
    evidence_path = Path(attempt_root) / "preentry_host_exit.json"
    failure_path = Path(attempt_root) / "terminal_failure.json"
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        failure = json.loads(failure_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"status": "BLOCKED", "reason": "PREENTRY_FAILURE_EVIDENCE_MISSING"}
    if not (
        evidence.get("classification") == "PRE_ENTRY_HOST_LAUNCH_FAILURE"
        and evidence.get("scientific_solver_entry_count") == 0
        and failure.get("solver_entered") is False
        and failure.get("solver_returned") is False
        and failure.get("rerun") is False
    ):
        return {"status": "BLOCKED", "reason": "PREENTRY_FAILURE_NOT_ZERO_ENTRY"}
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type IN ('SCIENTIFIC_SOLVER_ENTERED','GPU_ENGINE_ENTRY_CONFIRMED')",
            (branch, case, attempt),
        ).fetchone()[0]
    if row is None:
        return {"status": "NOT_FOUND", "case": case, "attempt": attempt}
    if row["state"] != "FAILED_PREENTRY" or row["slot_id"] is not None or entries:
        return {"status": "BLOCKED", "reason": "RETRY_ELIGIBILITY_STATE_CHANGED", "state": row["state"], "entries": entries}
    with db.immediate() as con:
        changed = con.execute(
            "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='FAILED_PREENTRY' AND slot_id IS NULL",
            (utc_now(), branch, case, attempt),
        ).rowcount
        if changed != 1:
            return {"status": "BLOCKED", "reason": "RETRY_ELIGIBILITY_QUEUE_REVALIDATION_FAILED"}
    append_event(
        Path(attempt_root) / "events.jsonl",
        "PREENTRY_RETRY_ELIGIBLE",
        branch_id=branch, case_id=case, attempt_id=attempt,
        scientific_solver_entry_count=0, replay=0,
        validation_manifest=str(manifest), validation_status="PASS",
    )
    return {
        "status": "PREENTRY_RETRY_ELIGIBLE",
        "case": case, "attempt": attempt,
        "scientific_solver_entry_count": 0, "replay": 0,
        "validation_manifest": str(manifest),
    }


def _recover_stale_preentry(db, branch, case, attempt, attempt_root, process_probe):
    with db.connect(readonly=True) as con:
        initial = _stale_preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe)
    if not initial.get("ok"):
        return initial
    with db.immediate() as con:
        final = _stale_preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe)
        if not final.get("ok"):
            return final
        row = final["row"]
        changed = con.execute(
            "UPDATE branch_queue SET state='FAILED_PREENTRY',slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state=?",
            (utc_now(), branch, case, attempt, row["state"]),
        ).rowcount
        if changed != 1:
            return {"status": "BLOCKED", "reason": "STALE_PREENTRY_QUEUE_REVALIDATION_FAILED", "case": case, "attempt": attempt}
    lease = final.get("lease")
    if lease is not None:
        released = Allocator(db).release_owned_idempotent(lease, scientific_terminal="FAILED_PREENTRY")
        if released["status"] not in {"RELEASED", "ALREADY_FREE"}:
            return {"status": "RECOVERY_PENDING_RELEASE", "release": released, "case": case, "attempt": attempt}
    else:
        released = {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
    permit_cleanup = Allocator(db).cancel_exact_launch_permit_for_attempt(branch, case, attempt)
    existing = read_events(Path(attempt_root) / "events.jsonl")
    if not any(event.get("event_type") == "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY" for event in existing):
        append_event(
            Path(attempt_root) / "events.jsonl",
            "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY",
            branch_id=branch, case_id=case, attempt_id=attempt,
            terminal_state="FAILED_PREENTRY", scientific_solver_entry_count=0, replay=0,
            stale_queue_state=final["row"]["state"], stale_queue_identity={
                "slot_id": final["row"]["slot_id"],
                "lease_token_hash": final["row"]["lease_token_hash"],
                "fencing_generation": final["row"]["fencing_generation"],
            },
            release=released, permit_cleanup=permit_cleanup,
        )
    return {
        "status": "RECOVERED_STALE_PREENTRY",
        "case": case, "attempt": attempt,
        "scientific_solver_entry_count": 0, "replay": 0,
        "release": released, "permit_cleanup": permit_cleanup,
        "stale_queue_state": final["row"]["state"],
    }


def _preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe):
    row = con.execute(
        "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
        (branch, case, attempt),
    ).fetchone()
    if row is None:
        return {"ok": False, "status": "NOT_FOUND", "case": case, "attempt": attempt}
    state = row["state"]
    if state not in {"HOST_STARTED", "FAILED_PREENTRY"}:
        return {"ok": False, "status": "NOT_ELIGIBLE", "state": state, "case": case, "attempt": attempt}
    control = con.execute(
        "SELECT new_entry_hold FROM admission_control WHERE control_id=1"
    ).fetchone()
    if control is None or int(control["new_entry_hold"]) != 1:
        return {"ok": False, "status": "BLOCKED", "reason": "RECOVERY_REQUIRES_NEW_ENTRY_HOLD"}
    entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
        (branch, case, attempt),
    ).fetchone()[0]
    gpu_entries = con.execute(
        "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='GPU_ENGINE_ENTRY_CONFIRMED'",
        (branch, case, attempt),
    ).fetchone()[0]
    if entries or gpu_entries:
        return {"ok": False, "status": "BLOCKED", "reason": "SCIENTIFIC_ENTRY_ALREADY_RECORDED", "scientific_entry_count": entries, "gpu_engine_entry_count": gpu_entries}
    newer = con.execute(
        "SELECT logical_case_id,attempt_id,state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id<>? AND state NOT IN ({})".format(
            ",".join("?" for _ in _PREENTRY_TERMINAL_STATES)
        ),
        (branch, case, attempt, *_PREENTRY_TERMINAL_STATES),
    ).fetchall()
    if newer:
        return {"ok": False, "status": "BLOCKED", "reason": "NEWER_ATTEMPT_ACTIVE", "newer_attempts": [dict(item) for item in newer]}
    events = read_events(Path(attempt_root) / "events.jsonl")
    event_types = {event.get("event_type") for event in events}
    db_event_types = {
        item[0]
        for item in con.execute(
            "SELECT event_type FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchall()
    }
    pending = sorted((event_types | db_event_types) & _PREENTRY_PENDING_EVENTS)
    truth_blockers = _attempt_truth_blockers(attempt_root)
    if pending:
        return {"ok": False, "status": "BLOCKED", "reason": "PERSISTENCE_OR_POSTPROCESS_PENDING", "pending_events": pending}
    if truth_blockers:
        return {"ok": False, "status": "BLOCKED", "reason": "TRUTH_BUNDLE_PRESENT", "truth_blockers": truth_blockers}
    process = _call_preentry_process_probe(process_probe, attempt_root, events)
    if process.get("status") != "PASS":
        return {"ok": False, "status": "BLOCKED", "reason": process.get("reason", "PROCESS_FAMILY_ALIVE_OR_AMBIGUOUS"), "process": process}
    if state == "FAILED_PREENTRY" and row["slot_id"] is None:
        return {"ok": True, "already_terminal": True, "row": dict(row), "lease": None, "events": events, "process": process}
    lease = None
    if row["slot_id"]:
        slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
        if slot is None:
            return {"ok": False, "status": "BLOCKED", "reason": "MISSING_SLOT"}
        if slot["state"] == "FREE":
            if state == "FAILED_PREENTRY":
                return {"ok": True, "already_terminal": True, "row": dict(row), "slot": dict(slot), "events": events}
            return {"ok": False, "status": "BLOCKED", "reason": "HOST_STARTED_WITH_FREE_SLOT"}
        matches = (
            slot["owner_branch"] == branch
            and slot["logical_case_id"] == case
            and slot["attempt_id"] == attempt
            and slot["lease_token"]
            and hashlib.sha256(slot["lease_token"].encode()).hexdigest() == row["lease_token_hash"]
            and int(slot["fencing_generation"]) == int(row["fencing_generation"] or -1)
        )
        if not matches:
            return {"ok": False, "status": "BLOCKED", "reason": "OWNER_OR_FENCING_MISMATCH"}
        lease = Lease(slot["slot_id"], branch, case, attempt, slot["lease_token"], int(slot["fencing_generation"]))
    elif not (state == "FAILED_PREENTRY" and row["slot_id"] is None):
        return {"ok": False, "status": "BLOCKED", "reason": "MISSING_ACTIVE_OWNER"}
    return {"ok": True, "already_terminal": False, "row": dict(row), "lease": lease, "events": events, "process": process}


def _recover_legacy_preentry(db, branch, case, attempt, attempt_root):
    ledger_path = Path(attempt_root) / "attempt_ledger.json"
    if not ledger_path.is_file():
        return {"status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_MISSING_LEDGER", "case": case, "attempt": attempt}
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger.get("solver_entered") is not False or int(ledger.get("run_invocation_count", -1)) != 0:
        return {"status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_LEDGER_NOT_ZERO", "case": case, "attempt": attempt}
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT * FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            (branch, case, attempt),
        ).fetchone()[0]
        copies = con.execute(
            "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()[0]
        active_other = con.execute(
            "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id<>? AND state NOT IN ({})".format(
                ",".join("?" for _ in _PREENTRY_TERMINAL_STATES)
            ),
            (branch, case, attempt, *_PREENTRY_TERMINAL_STATES),
        ).fetchone()[0]
        if row is None:
            return {"status": "NOT_FOUND", "case": case, "attempt": attempt}
        if entries or copies != 1 or active_other:
            return {"status": "BLOCKED", "reason": "LEGACY_PREENTRY_RECOVERY_SAFETY_GATE", "case": case, "attempt": attempt}
        lease = None
        if row["slot_id"]:
            slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (row["slot_id"],)).fetchone()
            if slot is None or slot["state"] == "FREE":
                return {"status": "BLOCKED", "reason": "LEGACY_PREENTRY_RECOVERY_MISSING_OWNER", "case": case, "attempt": attempt}
            matches = (
                slot["owner_branch"] == branch
                and slot["logical_case_id"] == case
                and slot["attempt_id"] == attempt
                and slot["lease_token"]
                and hashlib.sha256(slot["lease_token"].encode()).hexdigest() == row["lease_token_hash"]
                and int(slot["fencing_generation"]) == int(row["fencing_generation"] or -1)
            )
            if not matches:
                return {"status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_FOREIGN_SLOT", "case": case, "attempt": attempt}
            lease = Lease(slot["slot_id"], branch, case, attempt, slot["lease_token"], int(slot["fencing_generation"]))
    if lease is not None:
        released = Allocator(db).release_owned_idempotent(lease, scientific_terminal="FAILED_PREENTRY")
        if released["status"] not in {"RELEASED", "ALREADY_FREE"}:
            return {"status": "RECOVERY_PENDING_RELEASE", "release": released, "case": case, "attempt": attempt}
    else:
        released = {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
    with db.immediate() as con:
        changed = con.execute(
            "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state IN ('HOST_START_INTENT','SOLVER_ENTRY_INTENT','AMBIGUOUS_QUARANTINED')",
            (utc_now(), branch, case, attempt),
        ).rowcount
        if changed != 1:
            return {"status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_QUEUE_CHANGED", "case": case, "attempt": attempt}
    existing = read_events(Path(attempt_root) / "events.jsonl")
    if not any(event.get("event_type") == "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY" for event in existing):
        append_event(Path(attempt_root) / "events.jsonl", "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY", branch_id=branch, case_id=case, attempt_id=attempt, scientific_solver_entry_count=0, replay=0, release=released)
    return {"status": "RECOVERED_WAIT_RESOURCE_CAPACITY", "case": case, "attempt": attempt, "scientific_solver_entry_count": 0, "replay": 0, "release": released}

def _autofill_gate(payload, exact_permit_id=None):
    # Explicit validation-only rows never become scientific entries through release refill.
    gate = str(payload.get('validation_gate') or '').upper()
    blocked = gate in {'VALIDATION_ONLY', 'MANUAL_ONLY'} or payload.get('autofill_enabled') is False
    if blocked and not exact_permit_id:
        return {'status': 'WAIT_RESOURCE_CAPACITY', 'reason': 'AUTOFILL_DISABLED_VALIDATION_GATE', 'validation_gate': gate or None, 'autofill_enabled': payload.get('autofill_enabled'), 'exact_permit_required': True}
    return None


def enqueue(db,branch,case,attempt,payload=None):
    with db.immediate() as con:
        now=utc_now(); con.execute("INSERT OR IGNORE INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,'QUEUED',?,?,?)",(branch,case,attempt,json.dumps(payload or {}),now,now))

def dispatch_once(db,branch,launch,logical_case_id=None,attempt_id=None,exact_permit_id=None):
    allocator=Allocator(db); launched=[]
    with db.connect(readonly=True) as con:
        query="SELECT * FROM branch_queue WHERE branch_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')"
        params=[branch]
        if logical_case_id is not None:
            query += " AND logical_case_id=?"
            params.append(logical_case_id)
        if attempt_id is not None:
            query += " AND attempt_id=?"
            params.append(attempt_id)
        query += " ORDER BY queue_id"
        rows=[dict(r) for r in con.execute(query,tuple(params))]
    for row in rows:
        payload=json.loads(row["payload_json"] or "{}")
        permit_id = exact_permit_id or payload.get("exact_launch_permit_id")
        autofill_gate = _autofill_gate(payload, permit_id)
        if autofill_gate is not None:
            wait_payload = dict(payload)
            wait_payload["_v3_admission"] = {**autofill_gate, "updated_utc": utc_now()}
            with db.immediate() as con:
                con.execute("UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',payload_json=?,updated_at=? WHERE queue_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')", (json.dumps(wait_payload, sort_keys=True), utc_now(), row["queue_id"]))
            continue
        if permit_id:
            payload["exact_launch_permit_id"] = permit_id
        request=ResourceRequest.from_payload(payload)
        try:
            backend_type = payload.get("backend_type")
            if backend_type is None and (payload.get("production_science") or branch == "traditional"):
                backend_type = "CPU"
            lease=allocator.acquire(
                branch, row["logical_case_id"], row["attempt_id"],
                resource_request=request,
                resource_snapshot=read_resource_snapshot() if (request is not None or backend_type is not None) else None,
                resource_policy=payload.get("resource_policy"),
                backend_type=backend_type,
                exact_permit_id=permit_id,
            )
        except ResourceCapacityWait as exc:
            wait_payload = dict(payload)
            wait_payload["_v3_admission"] = {**dict(exc.evidence or {}), "updated_utc": utc_now()}
            with db.immediate() as con:
                con.execute("UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',payload_json=?,updated_at=? WHERE queue_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')", (json.dumps(wait_payload, sort_keys=True), utc_now(), row["queue_id"]))
            continue
        except (BranchCapReached,NoFreeSlot): break
        with db.immediate() as con:
            changed=con.execute("UPDATE branch_queue SET state='HOST_START_INTENT',slot_id=?,lease_token_hash=?,fencing_generation=?,updated_at=? WHERE queue_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')",(lease.slot_id,lease.token_hash,lease.fencing_generation,utc_now(),row["queue_id"])).rowcount
        if changed!=1:
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY"); continue
        final_snapshot = read_resource_snapshot() if (request is not None or backend_type is not None) else None
        final_admission = allocator.final_admission(
            lease, resource_request=request, resource_snapshot=final_snapshot,
            resource_policy=payload.get("resource_policy"), backend_type=backend_type,
            exact_permit_id=permit_id,
        )
        if not final_admission["eligible"]:
            allocator.release_provisional(lease, "FINAL_ADMISSION_RECHECK_BLOCKED")
            wait_payload = dict(payload)
            wait_payload["_v3_admission"] = final_admission
            with db.immediate() as con:
                con.execute("UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',payload_json=?,slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE queue_id=?", (json.dumps(wait_payload, sort_keys=True), utc_now(), row["queue_id"]))
            continue
        try:
            launch_row = dict(row)
            launch_row["payload_json"] = json.dumps(payload, sort_keys=True)
            launch_result = launch(launch_row,lease)
            next_state = "HOST_STARTED"
            if isinstance(launch_result, dict):
                next_state = str(launch_result.get("queue_state") or next_state)
            with db.immediate() as con:
                if next_state == "WAIT_RESOURCE_CAPACITY":
                    con.execute(
                        "UPDATE branch_queue SET state=?,slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE queue_id=?",
                        (next_state, utc_now(), row["queue_id"]),
                    )
                else:
                    con.execute(
                        "UPDATE branch_queue SET state=?,updated_at=? WHERE queue_id=?",
                        (next_state, utc_now(), row["queue_id"]),
                    )
            if next_state == "HOST_STARTED":
                launched.append(row["logical_case_id"])
        except Exception:
            with db.immediate() as con: con.execute("UPDATE branch_queue SET state='FAILED_PREENTRY',updated_at=? WHERE queue_id=?",(utc_now(),row["queue_id"]))
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY")
    return launched

def recover_failed_preentry(db, branch, case, attempt, attempt_root=None, process_probe=None):
    if not attempt_root:
        return {"status": "BLOCKED", "reason": "ZERO_SOLVER_RECOVERY_REQUIRES_ATTEMPT_ROOT", "case": case, "attempt": attempt}
    with db.connect(readonly=True) as con:
        current = con.execute(
            "SELECT state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()
    if current is not None and current["state"] in {"QUEUED", "WAIT_RESOURCE_CAPACITY", "SLOT_ACQUIRED"}:
        return _recover_stale_preentry(db, branch, case, attempt, attempt_root, process_probe)
    if current is not None and current["state"] in {"HOST_START_INTENT", "SOLVER_ENTRY_INTENT", "AMBIGUOUS_QUARANTINED"}:
        return _recover_legacy_preentry(db, branch, case, attempt, attempt_root)
    with db.connect(readonly=True) as con:
        initial = _preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe=process_probe)
    if not initial.get("ok"):
        return initial
    with db.immediate() as con:
        final = _preentry_snapshot(con, branch, case, attempt, attempt_root, process_probe=process_probe)
        if not final.get("ok"):
            return final
        row = final["row"]
        lease = final.get("lease")
        if row["state"] == "HOST_STARTED" and not final.get("already_terminal"):
            changed = con.execute(
                "UPDATE branch_queue SET state='FAILED_PREENTRY',updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='HOST_STARTED' AND slot_id=? AND fencing_generation=?",
                (utc_now(), branch, case, attempt, row["slot_id"], row["fencing_generation"]),
            ).rowcount
            if changed != 1:
                return {"status": "BLOCKED", "reason": "PREENTRY_RECOVERY_QUEUE_REVALIDATION_FAILED", "case": case, "attempt": attempt}
    if lease is not None:
        released = Allocator(db).release_owned_idempotent(lease, scientific_terminal="FAILED_PREENTRY")
        if released["status"] not in {"RELEASED", "ALREADY_FREE"}:
            return {"status": "RECOVERY_PENDING_RELEASE", "release": released, "case": case, "attempt": attempt}
    else:
        released = {"status": "ALREADY_FREE", "duplicate_side_effects": 0}
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state='FAILED_PREENTRY'",
            (utc_now(), branch, case, attempt),
        )
    if attempt_root:
        existing = read_events(Path(attempt_root) / "events.jsonl")
        if not any(event.get("event_type") == "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY" for event in existing):
            append_event(
                Path(attempt_root) / "events.jsonl",
                "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY",
                branch_id=branch, case_id=case, attempt_id=attempt,
                terminal_state="FAILED_PREENTRY", scientific_solver_entry_count=0, replay=0,
                release=released,
            )
    return {
        "status": "ALREADY_TERMINAL" if initial.get("already_terminal") else "RECOVERED_FAILED_PREENTRY",
        "case": case, "attempt": attempt, "scientific_solver_entry_count": 0,
        "replay": 0, "release": released,
    }

def task_scheduler_launch(task_name,python_exe,host_script,args):
    command='"{}" "{}" {}'.format(python_exe,host_script," ".join('"'+str(x).replace('"','')+'"' for x in args))
    create=subprocess.run(["schtasks.exe","/Create","/TN",task_name,"/TR",command,"/SC","ONCE","/SD","2099/01/01","/ST","00:00","/F"],capture_output=True,text=True)
    if create.returncode: raise RuntimeError(create.stderr or create.stdout)
    run=subprocess.run(["schtasks.exe","/Run","/TN",task_name],capture_output=True,text=True)
    if run.returncode: raise RuntimeError(run.stderr or run.stdout)
