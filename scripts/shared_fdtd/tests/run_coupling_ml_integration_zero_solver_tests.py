from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.resources import ResourceSnapshot
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue, recover_failed_preentry
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.reconciler import closeout_owned_postentry_no_truth
from shared_fdtd.engine.state_machine import replay_allowed, release_count

SCHEMA = PKG / "control_v3" / "schema.sql"

def init_db(root: Path) -> ControlDB:
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    return db

def queue_row(db, branch, case, attempt, state, lease):
    with db.immediate() as con:
        con.execute(
            "INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,slot_id,lease_token_hash,fencing_generation,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (branch, case, attempt, state, "{}", lease.slot_id, lease.token_hash, lease.fencing_generation, "t", "t"),
        )

def test_postentry_no_truth_closeout(root: Path):
    db = init_db(root)
    case, attempt = "NO_TRUTH", "attempt_001"
    attempt_root = root / case / attempt
    attempt_root.mkdir(parents=True)
    allocator = Allocator(db)
    lease = allocator.acquire("coupling_ml", case, attempt)
    allocator.mark_entered(lease)
    queue_row(db, "coupling_ml", case, attempt, "SCIENTIFIC_SOLVER_RUNNING", lease)
    events = attempt_root / "events.jsonl"
    append_event(events, "SCIENTIFIC_SOLVER_ENTERED", solver_runs=1)
    append_event(events, "SOLVER_RETURNED")
    append_event(events, "POSTENTRY_FAILURE_ADJUDICATED")
    append_event(events, "TRUTH_PRESERVATION_COMPLETE")
    roots = {(case, attempt): attempt_root}
    result = closeout_owned_postentry_no_truth(db, "coupling_ml", roots, process_probe=lambda state: [])
    assert result and result[0]["status"] == "POSTENTRY_NO_TRUTH", result
    assert allocator.list_slots_readonly()[1]["state"] == "FREE"
    with db.connect(readonly=True) as con:
        row = con.execute("SELECT state FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()
        releases = con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='LEASE_RELEASED'", (case,)).fetchone()[0]
    assert row["state"] == "POSTENTRY_NO_TRUTH"
    assert releases == 1
    rows = read_events(events)
    assert not replay_allowed(rows)
    assert release_count(rows) == 0
    assert (attempt_root / "terminal.json").is_file()
    second = closeout_owned_postentry_no_truth(db, "coupling_ml", roots, process_probe=lambda state: [])
    assert second == [], second
    return {"status": "PASS", "release_events": releases, "replay": 0}

def test_autorefill(root: Path):
    db = init_db(root)
    launched = []
    enqueue(db, "coupling_ml", "A", "attempt_001")
    enqueue(db, "coupling_ml", "B", "attempt_001")
    enqueue(db, "coupling_ml", "C", "attempt_001")
    first = dispatch_once(db, "coupling_ml", lambda row, lease: launched.append((row["logical_case_id"], lease)))
    assert first == ["A", "B"], first
    with db.connect(readonly=True) as con:
        rows = [dict(x) for x in con.execute("SELECT * FROM slots WHERE owner_branch='coupling_ml' ORDER BY slot_id")]
    a = next(x for x in rows if x["logical_case_id"] == "A")
    a_lease = next(lease for case, lease in launched if case == "A")
    allocator = Allocator(db)
    allocator.mark_entered(a_lease)
    allocator.release_pending(a_lease, "TEST_TRUTH_DURABLE")
    allocator.release_owned(a_lease, scientific_terminal="SCIENTIFIC_VALID")
    with db.immediate() as con:
        con.execute("UPDATE branch_queue SET state='RELEASED' WHERE logical_case_id='A'")
    second = dispatch_once(db, "coupling_ml", lambda row, lease: launched.append((row["logical_case_id"], lease)))
    assert second == ["C"], second
    assert len(launched) == 3
    return {"status": "PASS", "first": first, "second": second, "active_ml": 2}

def test_wait_resource_rechecks(root: Path):
    db = init_db(root)
    payload = {
        "production_science": True, "resource_class": "HEAVY",
        "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000,
        "mpi_ranks": 12, "threads": 1, "integrated_pw": False,
    }
    enqueue(db, "coupling_ml", "WAIT", "attempt_001", payload)
    import shared_fdtd.engine.dispatcher as dispatcher
    low = ResourceSnapshot("PASS", "t", 10000, 10, 10000, 10, 9990, 10, 0, 0, 0, 0, 0)
    high = ResourceSnapshot("PASS", "t", 10000, 10000, 10000, 10000, 0, 10000, 0, 0, 0, 0, 0)
    dispatcher.read_resource_snapshot = lambda: low
    assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
    with db.connect(readonly=True) as con:
        assert con.execute("SELECT state FROM branch_queue WHERE logical_case_id='WAIT'").fetchone()["state"] == "WAIT_RESOURCE_CAPACITY"
    dispatcher.read_resource_snapshot = lambda: high
    assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == ["WAIT"]
    return {"status": "PASS", "reevaluated": True}

def test_same_wait_attempt_after_foreign_release(root: Path):
    db = init_db(root)
    allocator = Allocator(db)
    traditional = allocator.acquire("traditional", "TRAD", "attempt_001")
    payload = {
        "production_science": True, "resource_class": "HEAVY",
        "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000,
        "mpi_ranks": 12, "threads": 1, "integrated_pw": False,
    }
    case, attempt = "PW_PLANAR_STACK_REAL_CANARY", "attempt_002"
    enqueue(db, "coupling_ml", case, attempt, payload)
    import shared_fdtd.engine.dispatcher as dispatcher
    low = ResourceSnapshot("PASS", "t", 10000, 10, 10000, 10, 9990, 10, 0, 0, 0, 0, 0)
    high = ResourceSnapshot("PASS", "t", 10000, 10000, 10000, 10000, 0, 10000, 0, 0, 0, 0, 0)
    dispatcher.read_resource_snapshot = lambda: low
    assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
    with db.connect(readonly=True) as con:
        row = con.execute("SELECT state,attempt_id FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()
        assert (row["state"], row["attempt_id"]) == ("WAIT_RESOURCE_CAPACITY", attempt)
    allocator.release_owned(traditional, scientific_terminal="FAILED_PREENTRY")
    launched = []
    dispatcher.read_resource_snapshot = lambda: high
    assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append((row["logical_case_id"], row["attempt_id"]))) == [case]
    assert launched == [(case, attempt)]
    with db.connect(readonly=True) as con:
        count = con.execute("SELECT COUNT(*) FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()[0]
        entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'", (case,)).fetchone()[0]
    assert count == 1
    assert entries == 0
    return {"status": "PASS", "same_attempt": True, "scientific_entries": entries}



def test_controller_restart_preserves_waiting_case(root: Path):
    db = init_db(root)
    case, attempt = "RESTART_WAIT", "attempt_002"
    payload = {
        "production_science": True, "resource_class": "HEAVY",
        "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000,
        "mpi_ranks": 12, "threads": 1, "integrated_pw": True,
    }
    enqueue(db, "coupling_ml", case, attempt, payload)
    import shared_fdtd.engine.dispatcher as dispatcher
    low = ResourceSnapshot("PASS", "t", 10000, 10, 10000, 10, 9990, 10, 0, 0, 0, 0, 0)
    high = ResourceSnapshot("PASS", "t", 10000, 10000, 10000, 10000, 0, 10000, 0, 0, 0, 0, 0)
    dispatcher.read_resource_snapshot = lambda: low
    assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
    reopened = ControlDB(db.path)
    launches = []
    dispatcher.read_resource_snapshot = lambda: high
    assert dispatch_once(
        reopened, "coupling_ml",
        lambda row, lease: launches.append((row["logical_case_id"], row["attempt_id"])),
    ) == [case]
    assert dispatch_once(
        reopened, "coupling_ml",
        lambda row, lease: launches.append((row["logical_case_id"], row["attempt_id"])),
    ) == []
    with reopened.connect(readonly=True) as con:
        row = con.execute(
            "SELECT state,attempt_id FROM branch_queue WHERE branch_id=? AND logical_case_id=?",
            ("coupling_ml", case),
        ).fetchone()
        copies = con.execute(
            "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=?",
            ("coupling_ml", case),
        ).fetchone()[0]
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            ("coupling_ml", case),
        ).fetchone()[0]
    assert launches == [(case, attempt)]
    assert (row["state"], row["attempt_id"]) == ("HOST_STARTED", attempt)
    assert copies == 1 and entries == 0
    return {"status": "PASS", "restart_preserved": True, "same_attempt": True, "scientific_entries": entries}


def test_preentry_boundary_preserves_wait(root: Path):
    db = init_db(root)
    case, attempt = "PW_PLANAR_STACK_REAL_CANARY", "attempt_002"
    enqueue(db, "coupling_ml", case, attempt, {})
    allocator = Allocator(db)
    observed = []

    def launch(row, lease):
        observed.append((row["logical_case_id"], row["attempt_id"], lease.slot_id))
        allocator.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
        return {"queue_state": "WAIT_RESOURCE_CAPACITY", "preentry_boundary": True}

    assert dispatch_once(db, "coupling_ml", launch) == []
    with db.connect(readonly=True) as con:
        row = con.execute("SELECT state,attempt_id FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone()
        free = con.execute("SELECT COUNT(*) FROM slots WHERE state='FREE'").fetchone()[0]
        entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'", (case,)).fetchone()[0]
    assert len(observed) == 1 and observed[0][:2] == (case, attempt) and observed[0][2].startswith("GLOBAL_SLOT_")
    assert (row["state"], row["attempt_id"]) == ("WAIT_RESOURCE_CAPACITY", attempt)
    assert free == 3
    assert entries == 0
    return {"status": "PASS", "same_attempt": True, "solver_entries": entries, "released": True}


def test_same_attempt_reuses_released_reservation(root: Path):
    db = init_db(root)
    case, attempt = "REUSE", "attempt_002"
    payload = {
        "production_science": True, "resource_class": "HEAVY",
        "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000,
        "mpi_ranks": 12, "threads": 1, "integrated_pw": True,
    }
    enqueue(db, "coupling_ml", case, attempt, payload)
    import shared_fdtd.engine.dispatcher as dispatcher
    dispatcher.read_resource_snapshot = lambda: ResourceSnapshot(
        "PASS", "t", 10000, 10000, 10000, 10000, 0, 10000, 0, 0, 0, 0, 0
    )
    allocator = Allocator(db)
    launches = []

    def launch(row, lease):
        launches.append(lease.slot_id)
        allocator.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
        return {"queue_state": "WAIT_RESOURCE_CAPACITY"}

    assert dispatch_once(db, "coupling_ml", launch) == []
    assert dispatch_once(db, "coupling_ml", launch) == []
    with db.connect(readonly=True) as con:
        reservations = con.execute(
            "SELECT COUNT(*) FROM resource_reservations WHERE branch_id='coupling_ml' AND logical_case_id=? AND attempt_id=?",
            (case, attempt),
        ).fetchone()[0]
        acquired = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id=? AND attempt_id=? AND event_type='LEASE_ACQUIRED'",
            (case, attempt),
        ).fetchone()[0]
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            (case, attempt),
        ).fetchone()[0]
        state = con.execute(
            "SELECT state FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id=? AND attempt_id=?",
            (case, attempt),
        ).fetchone()["state"]
    assert len(launches) == 2 and len(set(launches)) == 1 and launches[0].startswith("GLOBAL_SLOT_"), launches
    assert reservations == 1
    assert acquired == 2
    assert entries == 0
    assert state == "WAIT_RESOURCE_CAPACITY"
    return {"status": "PASS", "reservation_rows": reservations, "reacquisitions": acquired, "scientific_entries": entries}



def test_async_host_wait_clears_released_refs(root: Path):
    db = init_db(root)
    case, attempt = "ASYNC_HOST_WAIT", "attempt_003"
    enqueue(db, "coupling_ml", case, attempt)
    lease = Allocator(db).acquire("coupling_ml", case, attempt)
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='HOST_START_INTENT',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, "coupling_ml", case, attempt),
        )
    Allocator(db).release_owned(lease, scientific_terminal="FAILED_PREENTRY")
    from shared_fdtd.tools.v3_g2_host import queue_state
    queue_state(db, {"branch": "coupling_ml", "case": case, "attempt": attempt}, "WAIT_RESOURCE_CAPACITY")
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT state,slot_id,lease_token_hash,fencing_generation FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            ("coupling_ml", case, attempt),
        ).fetchone()
    assert row["state"] == "WAIT_RESOURCE_CAPACITY"
    assert row["slot_id"] is None and row["lease_token_hash"] is None and row["fencing_generation"] is None
    assert all(x["state"] == "FREE" for x in Allocator(db).list_slots_readonly())
    return {"status": "PASS", "scientific_entries": 0, "stale_refs": 0}


def test_zero_solver_host_start_recovery(root: Path):
    db = init_db(root)
    case, attempt = "ABANDONED_HOST", "attempt_002"
    attempt_root = root / case / attempt
    attempt_root.mkdir(parents=True)
    enqueue(db, "coupling_ml", case, attempt, {"attempt_root": str(attempt_root)})
    (attempt_root / "attempt_ledger.json").write_text(json.dumps({
        "solver_entered": False, "run_invocation_count": 0,
    }), encoding="utf-8")
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='HOST_START_INTENT' WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            ("coupling_ml", case, attempt),
        )
    result = recover_failed_preentry(db, "coupling_ml", case, attempt, attempt_root)
    assert result["status"] == "RECOVERED_WAIT_RESOURCE_CAPACITY", result
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT state,slot_id,fencing_generation FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            ("coupling_ml", case, attempt),
        ).fetchone()
    assert row["state"] == "WAIT_RESOURCE_CAPACITY"
    assert row["slot_id"] is None and row["fencing_generation"] is None
    return {"status": "PASS", "same_attempt": True, "scientific_entries": 0}


def test_zero_solver_entry_intent_recovery(root: Path):
    db = init_db(root)
    case, attempt = "ENTRY_INTENT_RECOVERY", "attempt_002"
    attempt_root = root / case / attempt
    attempt_root.mkdir(parents=True)
    enqueue(db, "coupling_ml", case, attempt, {"attempt_root": str(attempt_root)})
    lease = Allocator(db).acquire("coupling_ml", case, attempt)
    (attempt_root / "attempt_ledger.json").write_text(json.dumps({
        "solver_entered": False, "run_invocation_count": 0,
    }), encoding="utf-8")
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='SOLVER_ENTRY_INTENT',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, "coupling_ml", case, attempt),
        )
    result = recover_failed_preentry(db, "coupling_ml", case, attempt, attempt_root)
    assert result["status"] == "RECOVERED_WAIT_RESOURCE_CAPACITY", result
    with db.connect(readonly=True) as con:
        row = con.execute(
            "SELECT state,slot_id,fencing_generation FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            ("coupling_ml", case, attempt),
        ).fetchone()
        releases = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='LEASE_RELEASED'",
            ("coupling_ml", case, attempt),
        ).fetchone()[0]
    assert row["state"] == "WAIT_RESOURCE_CAPACITY"
    assert row["slot_id"] is None and row["fencing_generation"] is None
    assert next(x for x in Allocator(db).list_slots_readonly() if x["slot_id"] == lease.slot_id)["state"] == "FREE"
    assert releases == 1
    return {"status": "PASS", "scientific_entries": 0, "release_events": releases}


def test_foreign_traditional_unchanged(root: Path):
    db = init_db(root)
    allocator = Allocator(db)
    trad = allocator.acquire("traditional", "TRAD", "attempt_001")
    before = allocator.list_slots_readonly()
    from shared_fdtd.control_v3.allocator import Lease
    foreign = Lease(trad.slot_id, "coupling_ml", trad.logical_case_id, trad.attempt_id, trad.lease_token, trad.fencing_generation)
    try:
        allocator.release_postentry_no_truth(foreign, reason="wrong branch")
    except Exception:
        pass
    else:
        raise AssertionError("foreign release unexpectedly succeeded")
    after = allocator.list_slots_readonly()
    assert before == after
    return {"status": "PASS", "foreign_mutation_count": 0}

def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="coupling-ml-integration-", dir=PKG.parent) as td:
        root = Path(td)
        for name, fn in (
            ("postentry_no_truth_closeout", test_postentry_no_truth_closeout),
            ("multislot_autorefill", test_autorefill),
            ("wait_resource_rechecks", test_wait_resource_rechecks),
            ("same_wait_attempt_after_foreign_release", test_same_wait_attempt_after_foreign_release),
            ("preentry_boundary_preserves_wait", test_preentry_boundary_preserves_wait),
            ("controller_restart_preserves_waiting_case", test_controller_restart_preserves_waiting_case),
            ("same_attempt_reuses_released_reservation", test_same_attempt_reuses_released_reservation),
            ("async_host_wait_clears_released_refs", test_async_host_wait_clears_released_refs),
            ("zero_solver_host_start_recovery", test_zero_solver_host_start_recovery),
            ("zero_solver_entry_intent_recovery", test_zero_solver_entry_intent_recovery),
            ("foreign_traditional_unchanged", test_foreign_traditional_unchanged),
        ):
            try:
                rows.append({"test": name, **fn(root / name)})
            except Exception as exc:
                rows.append({"test": name, "status": "FAIL", "error": repr(exc)})
    result = {
        "status": "PASS" if all(x["status"] == "PASS" for x in rows) else "FAIL",
        "tests": rows, "solver_runs": 0, "scientific_solver_entries": 0,
        "replays": 0, "foreign_mutation_count": 0,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
