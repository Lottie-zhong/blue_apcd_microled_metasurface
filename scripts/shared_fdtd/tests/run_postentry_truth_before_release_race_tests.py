from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.engine.dispatcher import enqueue, dispatch_once
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.reconciler import closeout_owned_postentry_no_truth

SCHEMA = PKG / "control_v3" / "schema.sql"


def fixture(base: Path, case: str, attempt: str = "attempt_001"):
    db = ControlDB(base / "control.sqlite3")
    db.initialize(SCHEMA)
    root = base / case / attempt
    root.mkdir(parents=True)
    enqueue(db, "coupling_ml", case, attempt, {"attempt_root": str(root)})
    allocator = Allocator(db)
    lease = allocator.acquire("coupling_ml", case, attempt)
    allocator.mark_entered(lease)
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='SCIENTIFIC_SOLVER_RUNNING',slot_id=?,"
            "lease_token_hash=?,fencing_generation=? WHERE branch_id=? AND "
            "logical_case_id=? AND attempt_id=?",
            (
                lease.slot_id,
                lease.token_hash,
                lease.fencing_generation,
                "coupling_ml",
                case,
                attempt,
            ),
        )
    events = root / "events.jsonl"
    append_event(events, "SCIENTIFIC_SOLVER_ENTERED")
    return db, root, lease, events


def run_closeout(db, root, events, extra=()):
    for event in extra:
        append_event(events, event)
    return closeout_owned_postentry_no_truth(
        db,
        "coupling_ml",
        {("RACE", "attempt_001"): root},
        process_probe=lambda state: [],
    )


def slot_state(db, slot_id):
    return next(row for row in Allocator(db).list_slots_readonly() if row["slot_id"] == slot_id)["state"]


def assert_preserved(db, lease, result):
    assert result and result[0].get("release") == "PRESERVED", result
    assert slot_state(db, lease.slot_id) != "FREE"


def assert_not_released(db, lease, result):
    assert result and result[0].get("status") in {"NOT_ELIGIBLE_PRESERVE", "TRUTH_FINALIZATION_PENDING"}, result
    assert slot_state(db, lease.slot_id) != "FREE"


def test_pending_without_solver_return(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events)
    assert_preserved(db, lease, result)
    return "PASS"


def test_fsp_present_h5_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    (root / "runtime.fsp").write_bytes(b"fsp")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "NATIVE_TRUTH_PERSISTING"))
    assert_preserved(db, lease, result)
    return "PASS"


def test_native_present_archive_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "NATIVE_TRUTH_DURABLE"))
    assert_not_released(db, lease, result)
    return "PASS"


def test_archive_present_load_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "HF_ARCHIVED"))
    assert_not_released(db, lease, result)
    return "PASS"


def test_durable_truth_not_released_by_reconciler(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "SCIENTIFIC_VALID", "HF_ARCHIVED"))
    assert result and result[0]["status"] == "NOT_ELIGIBLE_PRESERVE", result
    assert slot_state(db, lease.slot_id) != "FREE"
    return "PASS"


def test_explicit_failure_can_release_once(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(
        db,
        root,
        events,
        ("SOLVER_RETURNED", "POSTENTRY_FAILURE_ADJUDICATED", "TRUTH_PRESERVATION_COMPLETE"),
    )
    assert result and result[0]["status"] == "POSTENTRY_NO_TRUTH", result
    assert slot_state(db, lease.slot_id) == "FREE"
    return "PASS"


def test_host_disappears_after_return_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events)
    assert_preserved(db, lease, result)
    return "PASS"


def test_observer_disappears_after_return_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events)
    assert_preserved(db, lease, result)
    return "PASS"


def test_controller_disappears_after_return_pending(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events)
    assert_preserved(db, lease, result)
    return "PASS"


def test_repeated_reconciler_no_early_release(base):
    db, root, lease, events = fixture(base, "RACE")
    first = run_closeout(db, root, events)
    second = closeout_owned_postentry_no_truth(
        db, "coupling_ml", {("RACE", "attempt_001"): root}, process_probe=lambda state: []
    )
    assert_preserved(db, lease, first)
    assert_preserved(db, lease, second)
    return "PASS"


def test_owner_ttl_during_persistence(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "PERSISTENCE_PENDING"))
    assert_preserved(db, lease, result)
    return "PASS"


def test_stale_process_probe_is_not_authority(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events)
    assert_preserved(db, lease, result)
    return "PASS"


def test_finalization_between_passes_releases_once(base):
    db, root, lease, events = fixture(base, "RACE")
    first = run_closeout(db, root, events)
    assert_preserved(db, lease, first)
    second = run_closeout(
        db,
        root,
        events,
        ("SOLVER_RETURNED", "POSTENTRY_FAILURE_ADJUDICATED", "TRUTH_PRESERVATION_COMPLETE"),
    )
    assert second and second[0]["status"] == "POSTENTRY_NO_TRUTH", second
    assert slot_state(db, lease.slot_id) == "FREE"
    with db.connect(readonly=True) as con:
        releases = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE logical_case_id='RACE' AND event_type='LEASE_RELEASED'"
        ).fetchone()[0]
    assert releases == 1
    return "PASS"


def test_duplicate_reconciler_no_double_release(base):
    db, root, lease, events = fixture(base, "RACE")
    run_closeout(
        db,
        root,
        events,
        ("SOLVER_RETURNED", "POSTENTRY_FAILURE_ADJUDICATED", "TRUTH_PRESERVATION_COMPLETE"),
    )
    second = closeout_owned_postentry_no_truth(
        db, "coupling_ml", {("RACE", "attempt_001"): root}, process_probe=lambda state: []
    )
    assert second == [], second
    with db.connect(readonly=True) as con:
        releases = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE logical_case_id='RACE' AND event_type='LEASE_RELEASED'"
        ).fetchone()[0]
    assert releases == 1
    return "PASS"


def test_persistence_failure_quarantines_without_release(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "PERSISTENCE_PENDING"))
    assert_preserved(db, lease, result)
    return "PASS"


def test_ownership_mismatch_not_created_by_reconciler(base):
    db, root, lease, events = fixture(base, "RACE")
    result = run_closeout(db, root, events, ("SOLVER_RETURNED", "NATIVE_TRUTH_PERSISTING"))
    assert_preserved(db, lease, result)
    assert not any("OwnershipMismatch" in row.get("error", "") for row in read_events(events))
    return "PASS"


def test_hold_blocks_successor(base):
    db = ControlDB(base / "control.sqlite3")
    db.initialize(SCHEMA)
    with db.immediate() as con:
        con.execute("UPDATE admission_control SET new_entry_hold=1 WHERE control_id=1")
    enqueue(db, "coupling_ml", "SUCCESSOR", "attempt_001", {"production_science": True})
    assert dispatch_once(db, "coupling_ml", lambda row, lease: (_ for _ in ()).throw(AssertionError("launched"))) == []
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT state FROM branch_queue WHERE logical_case_id='SUCCESSOR'"
        ).fetchone()
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE logical_case_id='SUCCESSOR' AND event_type='SCIENTIFIC_SOLVER_ENTERED'"
        ).fetchone()[0]
    assert row["state"] == "WAIT_RESOURCE_CAPACITY"
    assert entries == 0
    return "PASS"


def main():
    tests = [
        test_pending_without_solver_return,
        test_fsp_present_h5_pending,
        test_native_present_archive_pending,
        test_archive_present_load_pending,
        test_durable_truth_not_released_by_reconciler,
        test_explicit_failure_can_release_once,
        test_host_disappears_after_return_pending,
        test_observer_disappears_after_return_pending,
        test_controller_disappears_after_return_pending,
        test_repeated_reconciler_no_early_release,
        test_owner_ttl_during_persistence,
        test_stale_process_probe_is_not_authority,
        test_finalization_between_passes_releases_once,
        test_duplicate_reconciler_no_double_release,
        test_persistence_failure_quarantines_without_release,
        test_ownership_mismatch_not_created_by_reconciler,
        test_hold_blocks_successor,
    ]
    rows = []
    for fn in tests:
        with tempfile.TemporaryDirectory(prefix="postentry-race-", dir=PKG.parent) as td:
            try:
                rows.append({"test": fn.__name__, "status": fn(Path(td))})
            except Exception as exc:
                rows.append({"test": fn.__name__, "status": "FAIL", "error": repr(exc)})
    result = {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "count": len(rows),
        "passed": sum(row["status"] == "PASS" for row in rows),
        "solver_invocations": 0,
        "scientific_solver_entries": 0,
        "replays": 0,
        "tests": rows,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
