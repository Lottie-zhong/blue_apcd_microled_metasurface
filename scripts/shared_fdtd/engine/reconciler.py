from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Any

from shared_fdtd.control_v3.allocator import Allocator, Lease
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.engine.persistence import atomic_json
from .event_log import append_event, read_events
from .state_machine import (
    release_allowed, replay_allowed, postentry_no_truth_allowed,
    scientific_entry_count, truth_durable,
)

def reconcile_owned(db, branch, attempt_roots):
    allocator = Allocator(db)
    results = []
    for slot in allocator.list_slots_readonly():
        if slot["state"] == "FREE" or slot["owner_branch"] != branch:
            continue
        key = (slot["logical_case_id"], slot["attempt_id"])
        root = attempt_roots.get(key)
        if not root:
            results.append({"slot_id": slot["slot_id"], "status": "OWN_ATTEMPT_UNKNOWN_PRESERVE"})
            continue
        events = read_events(Path(root) / "events.jsonl")
        results.append({
            "slot_id": slot["slot_id"],
            "status": "RELEASE_ELIGIBLE" if release_allowed(events) else "PRESERVE_NO_REPLAY",
            "replay_allowed": replay_allowed(events),
        })
    return results

def _append_once(path: Path, event_type: str, **payload: Any) -> None:
    if any(row.get("event_type") == event_type for row in read_events(path)):
        return
    append_event(path, event_type, **payload)


_TRUTH_FINALIZATION_PENDING_EVENTS = {
    "TRUTH_FINALIZATION_PENDING",
    "NATIVE_TRUTH_PERSISTING",
    "POSTPROCESSING",
    "PERSISTENCE_PENDING",
    "FRESH_LOAD_PENDING",
    "RELEASE_PENDING",
    "PENDING_RECONCILE",
}
_POSTENTRY_FAILURE_EVIDENCE = {
    "POSTENTRY_FAILURE_ADJUDICATED",
    "TRUTH_PRESERVATION_COMPLETE",
}


def _preserve_truth_finalization_pending(db, branch, slot, events_path, *, reason):
    _append_once(
        events_path,
        "TRUTH_FINALIZATION_PENDING",
        reason=reason,
        owner_branch=branch,
        case_id=slot["logical_case_id"],
        attempt_id=slot["attempt_id"],
        slot_id=slot["slot_id"],
        fencing_generation=slot["fencing_generation"],
        release_allowed=False,
    )
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='PENDING_RECONCILE',updated_at=? "
            "WHERE branch_id=? AND logical_case_id=? AND attempt_id=? "
            "AND state IN ('SCIENTIFIC_SOLVER_RUNNING','SOLVER_RETURNED',"
            "'NATIVE_TRUTH_PERSISTING','POSTPROCESSING','RELEASE_PENDING',"
            "'PENDING_RECONCILE')",
            (
                utc_now(),
                branch,
                slot["logical_case_id"],
                slot["attempt_id"],
            ),
        )
    return {
        "slot_id": slot["slot_id"],
        "status": "TRUTH_FINALIZATION_PENDING",
        "reason": reason,
        "release": "PRESERVED",
        "replay": 0,
    }


def closeout_owned_postentry_no_truth(
    db, branch: str, attempt_roots: Mapping[tuple[str, str], str | Path],
    *, process_probe: Callable[[Mapping[str, Any]], list[Mapping[str, Any]]] | None = None,
    reason: str = "NO_ACCEPTED_TRUTH_AFTER_SCIENTIFIC_ENTRY",
):
    # Fenced, idempotent physical-slot release for an entered lineage with no truth.
    # This path never invokes a solver or relabels an entered lineage as pre-entry.
    allocator = Allocator(db)
    results = []
    for slot in allocator.list_slots_readonly():
        if slot["state"] == "FREE" or slot["owner_branch"] != branch:
            continue
        key = (slot["logical_case_id"], slot["attempt_id"])
        root_value = attempt_roots.get(key)
        if not root_value:
            results.append({"slot_id": slot["slot_id"], "status": "OWN_ATTEMPT_UNKNOWN_PRESERVE"})
            continue
        root = Path(root_value)
        if not root.is_dir():
            results.append({"slot_id": slot["slot_id"], "status": "OWN_ATTEMPT_UNKNOWN_PRESERVE"})
            continue
        events_path = root / "events.jsonl"
        events = read_events(events_path)
        if not postentry_no_truth_allowed(events):
            results.append({"slot_id": slot["slot_id"], "status": "NOT_ELIGIBLE_PRESERVE", "replay_allowed": replay_allowed(events)})
            continue
        state = {
            "owner_branch": branch, "logical_case_id": slot["logical_case_id"],
            "attempt_id": slot["attempt_id"], "slot_id": slot["slot_id"],
            "fencing_generation": slot["fencing_generation"],
        }
        if process_probe is None:
            results.append({"slot_id": slot["slot_id"], "status": "PROCESS_PROBE_REQUIRED"})
            continue
        live = list(process_probe(state) or [])
        if live:
            results.append({"slot_id": slot["slot_id"], "status": "SOLVER_STILL_RUNNING", "live_processes": live})
            continue

        event_types = {event.get("event_type") for event in events}
        if "SOLVER_RETURNED" not in event_types:
            results.append(
                _preserve_truth_finalization_pending(
                    db,
                    branch,
                    slot,
                    events_path,
                    reason="SOLVER_RETURN_NOT_PROVEN",
                )
            )
            continue
        pending = sorted(event_types & _TRUTH_FINALIZATION_PENDING_EVENTS)
        if pending and not _POSTENTRY_FAILURE_EVIDENCE.issubset(event_types):
            results.append(
                _preserve_truth_finalization_pending(
                    db,
                    branch,
                    slot,
                    events_path,
                    reason=",".join(pending),
                )
            )
            continue
        if not _POSTENTRY_FAILURE_EVIDENCE.issubset(event_types):
            results.append(
                _preserve_truth_finalization_pending(
                    db,
                    branch,
                    slot,
                    events_path,
                    reason="POSTENTRY_FAILURE_REVIEW_REQUIRED",
                )
            )
            continue
        with db.connect(readonly=True) as con:
            row = con.execute("SELECT * FROM slots WHERE slot_id=?", (slot["slot_id"],)).fetchone()
        if row is None or row["state"] == "FREE":
            results.append({"slot_id": slot["slot_id"], "status": "ALREADY_FREE"})
            continue
        lease = Lease(row["slot_id"], row["owner_branch"], row["logical_case_id"], row["attempt_id"], row["lease_token"], int(row["fencing_generation"]))
        closeout = {
            "status": "POSTENTRY_NO_TRUTH", "reason": reason, "replay": 0,
            "owner_branch": branch, "case_id": lease.logical_case_id,
            "attempt_id": lease.attempt_id, "slot_id": lease.slot_id,
            "fencing_generation": lease.fencing_generation,
            "scientific_entry_count": scientific_entry_count(events),
            "truth_durable": truth_durable(events),
            "release_allowed": release_allowed(events),
            "created_utc": utc_now(),
        }
        atomic_json(root / "postentry_no_truth_closeout.json", closeout)
        _append_once(events_path, "POSTENTRY_NO_TRUTH", **closeout)
        _append_once(events_path, "TERMINAL_QUARANTINED", reason=reason, replay=0)
        release = allocator.release_postentry_no_truth(lease, reason=reason, provenance=closeout)
        with db.immediate() as con:
            con.execute(
                "UPDATE branch_queue SET state=?,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
                ("POSTENTRY_NO_TRUTH", utc_now(), branch, lease.logical_case_id, lease.attempt_id),
            )
        _append_once(events_path, "POSTENTRY_NO_TRUTH_RELEASED", release=release, replay=0)
        closeout.update({"release": release, "terminalized_utc": utc_now()})
        atomic_json(root / "terminal.json", closeout)
        results.append({"slot_id": lease.slot_id, "status": "POSTENTRY_NO_TRUTH", "release": release, "replay": 0})
    return results
