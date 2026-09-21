from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB, ResourceCapacityWait, ResourceRequest, ResourceSnapshot
from shared_fdtd.control_v3.allocator import OwnershipMismatch, Lease
from shared_fdtd.control_v3.resources import runtime_resource_sample
from shared_fdtd.engine.host_lifecycle import ScientificHostLifecycle

SCHEMA = PKG / "control_v3" / "schema.sql"


def fresh(root: Path) -> ControlDB:
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    return db


def snap(ram: int = 10_000, commit: int = 10_000, *, status: str = "PASS") -> ResourceSnapshot:
    return ResourceSnapshot(status, "test", 20_000, ram, 20_000, commit, 20_000 - commit, commit, 3, 900, 1, 1, 5, ())


def request(*, integrated: bool = True, ram: int = 1_000, commit: int = 1_000) -> ResourceRequest:
    return ResourceRequest("HEAVY", ram, commit, 12, 1, integrated, 0.25)


def count_entries(db: ControlDB) -> int:
    with db.connect(readonly=True) as con:
        return int(con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0])


def test_insufficient_ram(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    try:
        a.acquire("coupling_ml", "ram", "a1", resource_request=request(), resource_snapshot=snap(ram=100))
    except ResourceCapacityWait as exc:
        assert "PHYSICAL_RAM_HEADROOM" in exc.evidence["reasons"]
    else:
        raise AssertionError("RAM gate admitted an unsafe request")
    assert all(row["state"] == "FREE" for row in a.list_slots_readonly())


def test_insufficient_commit(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    try:
        a.acquire("coupling_ml", "commit", "a1", resource_request=request(), resource_snapshot=snap(commit=100))
    except ResourceCapacityWait as exc:
        assert "COMMIT_HEADROOM" in exc.evidence["reasons"]
    else:
        raise AssertionError("commit gate admitted an unsafe request")


def test_traditional_plus_one_heavy_pw(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    traditional = a.acquire("traditional", "traditional", "a1", resource_request=request(integrated=False, ram=500, commit=500), resource_snapshot=snap())
    pw = a.acquire("coupling_ml", "pw-1", "a1", resource_request=request(), resource_snapshot=snap())
    assert {traditional.slot_id, pw.slot_id} == {"GLOBAL_SLOT_1", "GLOBAL_SLOT_2"}
    a.release_owned(pw, scientific_terminal="FAILED_PREENTRY")
    a.release_owned(traditional, scientific_terminal="FAILED_PREENTRY")


def test_second_integrated_pw_blocked(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    traditional = a.acquire("traditional", "traditional", "a1", resource_request=request(integrated=False, ram=500, commit=500), resource_snapshot=snap())
    first = a.acquire("coupling_ml", "pw-1", "a1", resource_request=request(), resource_snapshot=snap())
    try:
        a.acquire("coupling_ml", "pw-2", "a1", resource_request=request(), resource_snapshot=snap())
    except ResourceCapacityWait as exc:
        assert "PW_INTEGRATED_CONCURRENCY_LIMIT" in exc.evidence["reasons"]
    else:
        raise AssertionError("second integrated PW was admitted")
    a.release_owned(first, scientific_terminal="FAILED_PREENTRY")
    a.release_owned(traditional, scientific_terminal="FAILED_PREENTRY")


def test_monitor_failure_does_not_change_ownership(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    lease = a.acquire("coupling_ml", "monitor", "a1", resource_request=request(), resource_snapshot=snap())
    sample = runtime_resource_sample(request(), snapshot_provider=lambda: (_ for _ in ()).throw(RuntimeError("monitor")))
    assert sample["event_type"] == "RESOURCE_MONITOR_DEGRADED"
    assert sample["scientific_solver_action"] == "NONE"
    assert a.list_slots_readonly()[1]["state"] == "RESERVED"
    a.release_owned(lease, scientific_terminal="FAILED_PREENTRY")


def test_resource_pressure_blocks_new_entry(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    try:
        a.acquire("coupling_ml", "pressure", "a1", resource_request=request(), resource_snapshot=snap(ram=100, commit=100))
    except ResourceCapacityWait:
        pass
    else:
        raise AssertionError("resource pressure did not block admission")
    assert count_entries(db) == 0


def test_heartbeat_failure_does_not_close_owner(tmp: Path) -> None:
    lifecycle = ScientificHostLifecycle(tmp / "events.jsonl", {"owner_branch": "coupling_ml"})
    lifecycle.mark_entered()
    assert not lifecycle.control_plane("heartbeat", lambda: (_ for _ in ()).throw(RuntimeError("sqlite locked")))
    assert lifecycle.entered and not lifecycle.can_close()


def test_stale_fencing_and_foreign_traditional_are_read_only(tmp: Path) -> None:
    db = fresh(tmp); a = Allocator(db)
    old = a.acquire("traditional", "traditional", "a1")
    foreign = Lease(old.slot_id, "coupling_ml", old.logical_case_id, old.attempt_id, old.lease_token, old.fencing_generation)
    before = a.list_slots_readonly()
    try:
        a.heartbeat(foreign)
    except OwnershipMismatch:
        pass
    else:
        raise AssertionError("foreign Traditional lease was mutated")
    a.release_owned(old, scientific_terminal="FAILED_PREENTRY")
    new = a.acquire("traditional", "traditional-new", "a2")
    try:
        a.release_owned(old, scientific_terminal="FAILED_PREENTRY")
    except OwnershipMismatch:
        pass
    else:
        raise AssertionError("stale lease released newer fencing generation")
    assert before[0]["owner_branch"] == "traditional"
    a.release_owned(new, scientific_terminal="FAILED_PREENTRY")


def main() -> int:
    tests = [
        test_insufficient_ram,
        test_insufficient_commit,
        test_traditional_plus_one_heavy_pw,
        test_second_integrated_pw_blocked,
        test_monitor_failure_does_not_change_ownership,
        test_resource_pressure_blocks_new_entry,
        test_heartbeat_failure_does_not_close_owner,
        test_stale_fencing_and_foreign_traditional_are_read_only,
    ]
    results = []
    with tempfile.TemporaryDirectory() as root:
        for test in tests:
            try:
                with tempfile.TemporaryDirectory(dir=root) as case:
                    test(Path(case))
                results.append({"test": test.__name__, "status": "PASS"})
            except Exception as exc:
                results.append({"test": test.__name__, "status": "FAIL", "error": repr(exc)})
    out = {"status": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL", "tests": results, "solver_runs": 0, "scientific_solver_entries": 0}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
