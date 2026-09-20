from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB, OwnershipMismatch
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.engine.event_log import read_events
from shared_fdtd.engine.host_lifecycle import ScientificHostLifecycle
from shared_fdtd.engine.state_machine import replay_allowed


class FakeFD:
    def __init__(self): self.close_calls = 0
    def close(self): self.close_calls += 1


def identity():
    return {"owner_branch": "coupling_ml", "logical_case_id": "T", "attempt_id": "a1", "slot_id": "GLOBAL_SLOT_2", "lease_token_hash": "hash", "fencing_generation": 1}


def case(name, fn):
    try:
        fn()
        return [name, "PASS", ""]
    except Exception as exc:
        return [name, "FAIL", repr(exc)]


def main():
    rows = []
    def temp(fn):
        with tempfile.TemporaryDirectory() as d: fn(Path(d))
    rows.append(case("preentry_control_failure_safe_cleanup", lambda: temp(lambda p: preentry(p))))
    for name, op in [
        ("postentry_control_failure_worker_survives", "queue_state"),
        ("postentry_db_busy_deferred", "db_busy"),
        ("postentry_heartbeat_failure_worker_survives", "heartbeat"),
        ("postentry_mark_entered_failure_worker_survives", "mark_solver_entered"),
        ("postentry_event_ledger_failure_worker_survives", "event_ledger"),
        ("postentry_supervisor_exception_no_close", "supervisor"),
        ("postentry_dispatcher_disappearance_no_close", "dispatcher"),
        ("postentry_generic_control_exception_no_close", "generic_control"),
    ]:
        rows.append(case(name, lambda op=op: temp(lambda p: postentry(p, op))))
    rows.append(case("truth_durable_release_failure_pending_reconcile", lambda: temp(lambda p: truth_and_release(p))))
    rows.append(case("truth_durable_db_unavailable_remains_authoritative", lambda: temp(lambda p: truth_authority(p))))
    rows.append(case("scientific_execution_exception_closes_legally", lambda: temp(lambda p: scientific_failure(p))))
    rows.append(case("foreign_owner_zero_mutation", lambda: temp(lambda p: foreign_fencing(p, token=False, generation=False))))
    rows.append(case("fencing_mismatch_zero_mutation", lambda: temp(lambda p: foreign_fencing(p, token=True, generation=True))))
    rows.append(case("duplicate_deferred_event_idempotent", lambda: temp(lambda p: duplicate_deferred(p))))
    rows.append(case("fd_close_audit_no_control_plane_cleanup", lambda: temp(lambda p: close_audit(p))))
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("entered_exception_isolation_results.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("test,status,detail\n" + "\n".join(",".join(json.dumps(x) for x in row) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(rows), "passed": sum(r[1] == "PASS" for r in rows), "failed": [r for r in rows if r[1] != "PASS"], "solver_runs": 0}))
    return 0 if all(r[1] == "PASS" for r in rows) else 1


def life(p):
    return ScientificHostLifecycle(p / "events.jsonl", identity()), FakeFD()


def preentry(p):
    l, fd = life(p)
    assert not l.control_plane("preentry_gate", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    l.close(fd, "PREENTRY_FAILURE")
    assert fd.close_calls == 1 and not l.entered


def postentry(p, op):
    l, fd = life(p); l.mark_entered()
    assert not l.control_plane(op, lambda: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    assert not l.can_close() and fd.close_calls == 0
    events = read_events(p / "events.jsonl")
    assert any(e["event_type"] == "CONTROL_PLANE_UPDATE_DEFERRED" and e["failed_control_plane_operation"] == op for e in events)


def truth_and_release(p):
    l, fd = life(p); l.mark_entered(); l.mark_truth_durable()
    assert not l.control_plane("release_owned", lambda: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")))
    l.close(fd, "TRUTH_DURABLE"); assert fd.close_calls == 1
    assert any(e["event_type"] == "CONTROL_PLANE_UPDATE_DEFERRED" for e in read_events(p / "events.jsonl"))


def truth_authority(p):
    l, fd = life(p); l.mark_entered(); l.mark_truth_durable(); l.defer("db_unavailable", sqlite3.OperationalError("database is locked"), state="SCIENTIFIC_VALID")
    assert l.truth_durable and not replay_allowed([{"event_type": "SCIENTIFIC_VALID"}]); l.close(fd, "TRUTH_DURABLE")


def scientific_failure(p):
    l, fd = life(p); l.mark_entered(); l.mark_scientific_terminal(); l.close(fd, "SCIENTIFIC_TERMINAL"); assert fd.close_calls == 1


def allocator_db(p):
    db = ControlDB(p / "control.sqlite3"); db.initialize(PKG / "control_v3" / "schema.sql"); return db


def foreign_fencing(p, token, generation):
    db = allocator_db(p); a = Allocator(db); good = a.acquire("traditional", "T", "a1")
    bad = Lease(good.slot_id, "coupling_ml" if not token else good.owner_branch, good.logical_case_id, good.attempt_id, "bad" if token else good.lease_token, good.fencing_generation + (1 if generation else 0))
    before = a.list_slots_readonly()
    try: a.heartbeat(bad)
    except OwnershipMismatch: pass
    else: raise AssertionError("foreign mutation accepted")
    assert a.list_slots_readonly() == before


def duplicate_deferred(p):
    l, fd = life(p); l.mark_entered(); fail = lambda: (_ for _ in ()).throw(RuntimeError("busy")); l.control_plane("heartbeat", fail); l.control_plane("heartbeat", fail)
    events = [e for e in read_events(p / "events.jsonl") if e["event_type"] == "CONTROL_PLANE_UPDATE_DEFERRED"]
    assert len(events) == 1 and fd.close_calls == 0


def close_audit(p):
    l, fd = life(p); l.mark_entered(); l.control_plane("report_generation", lambda: (_ for _ in ()).throw(RuntimeError("report")))
    assert not l.can_close() and fd.close_calls == 0


if __name__ == "__main__": raise SystemExit(main())
