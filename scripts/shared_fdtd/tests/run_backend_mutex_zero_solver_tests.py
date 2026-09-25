from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB, ResourceSnapshot
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue

SCHEMA = PKG / "control_v3" / "schema.sql"


def snap(*, engines=0, errors=()):
    return ResourceSnapshot("PASS", "test", 20_000, 20_000, 20_000, 20_000, 0, 20_000, engines, 0, 0, 0, engines, tuple(errors))


def payload(backend):
    return {
        "production_science": True,
        "backend_type": backend,
        "resource_class": "HEAVY",
        "estimated_peak_ram_bytes": 1_000,
        "estimated_commit_bytes": 1_000,
        "mpi_ranks": 12,
        "threads": 1,
        "integrated_pw": False,
    }


def fresh(root):
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    return db


def state(db, case):
    with db.connect(readonly=True) as con:
        return dict(con.execute("SELECT * FROM branch_queue WHERE logical_case_id=?", (case,)).fetchone())


def entries(db):
    with db.connect(readonly=True) as con:
        return con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]


def dispatch(db, snapshot, launched):
    import shared_fdtd.engine.dispatcher as dispatcher
    dispatcher.read_resource_snapshot = lambda: snapshot
    return dispatch_once(db, "coupling_ml", lambda row, lease: launched.append((row["logical_case_id"], lease)))


def test_a_cpu_active_blocks_gpu_and_free_slot_does_not_bypass(root):
    db = fresh(root)
    allocator = Allocator(db)
    cpu = allocator.acquire("traditional", "TRAD_CPU", "attempt_002", backend_type="CPU", resource_snapshot=snap())
    case = "GPU_WAIT_A"
    enqueue(db, "coupling_ml", case, "attempt_001", payload("GPU"))
    launched = []
    assert dispatch(db, snap(), launched) == []
    row = state(db, case)
    assert row["state"] == "WAIT_RESOURCE_CAPACITY"
    evidence = json.loads(row["payload_json"])["_v3_admission"]
    assert "CPU_FDTD_ACTIVE_FOREIGN_OWNER" in evidence["reasons"]
    assert not launched and all(x["state"] == "FREE" for x in allocator.list_slots_readonly() if x["slot_id"] != cpu.slot_id)
    before = allocator.list_slots_readonly()
    allocator.release_owned(cpu, scientific_terminal="FAILED_PREENTRY")
    assert dispatch(db, snap(), launched) == [case]
    assert len(launched) == 1
    allocator.release_owned(launched[0][1], scientific_terminal="FAILED_PREENTRY")
    assert before[0]["owner_branch"] == "traditional"


def test_b_gpu_active_blocks_cpu(root):
    db = fresh(root)
    allocator = Allocator(db)
    gpu_case = "GPU_ACTIVE_B"
    gpu = allocator.acquire("coupling_ml", gpu_case, "attempt_001", backend_type="GPU", resource_request=payload("GPU"), resource_snapshot=snap())
    allocator.mark_entered(gpu)
    cpu_case = "CPU_WAIT_B"
    enqueue(db, "coupling_ml", cpu_case, "attempt_001", payload("CPU"))
    launched = []
    assert dispatch(db, snap(), launched) == []
    evidence = json.loads(state(db, cpu_case)["payload_json"])["_v3_admission"]
    assert "GPU_FDTD_ACTIVE_FOREIGN_OWNER" in evidence["reasons"]
    assert not launched and entries(db) == 1
    allocator.release_owned(gpu, scientific_terminal="FAILED_PREENTRY")


def test_c_auto_wake_d_same_attempt_no_duplicate(root):
    db = fresh(root)
    allocator = Allocator(db)
    cpu = allocator.acquire("traditional", "TRAD_C", "attempt_001", backend_type="CPU", resource_snapshot=snap())
    case = "GPU_WAIT_C"
    enqueue(db, "coupling_ml", case, "attempt_001", payload("GPU"))
    launched = []
    assert dispatch(db, snap(), launched) == []
    assert dispatch(db, snap(), launched) == []
    assert dispatch(db, snap(), launched) == []
    assert launched == []
    allocator.release_owned(cpu, scientific_terminal="FAILED_PREENTRY")
    assert dispatch(db, snap(), launched) == [case]
    assert dispatch(db, snap(), launched) == []
    assert len(launched) == 1 and entries(db) == 0
    allocator.release_owned(launched[0][1], scientific_terminal="FAILED_PREENTRY")


def test_d_gpu_release_allows_waiting_cpu(root):
    db = fresh(root)
    allocator = Allocator(db)
    gpu_case = "GPU_ACTIVE_D"
    gpu = allocator.acquire("coupling_ml", gpu_case, "attempt_001", backend_type="GPU", resource_request=payload("GPU"), resource_snapshot=snap())
    allocator.mark_entered(gpu)
    cpu_case = "CPU_WAIT_D"
    enqueue(db, "coupling_ml", cpu_case, "attempt_001", payload("CPU"))
    launched = []
    assert dispatch(db, snap(), launched) == []
    allocator.release_owned(gpu, scientific_terminal="FAILED_PREENTRY")
    assert dispatch(db, snap(), launched) == [cpu_case]
    assert launched[0][0] == cpu_case
    allocator.release_owned(launched[0][1], scientific_terminal="FAILED_PREENTRY")


def test_e_stale_process_without_lifecycle_blocks(root):
    db = fresh(root)
    case = "STALE_PROCESS_I"
    enqueue(db, "coupling_ml", case, "attempt_001", payload("GPU"))
    launched = []
    assert dispatch(db, snap(engines=1), launched) == []
    evidence = json.loads(state(db, case)["payload_json"])["_v3_admission"]
    assert "BACKEND_PROCESS_WITHOUT_ACTIVE_LIFECYCLE" in evidence["reasons"]
    assert not launched


def test_f_active_lifecycle_missing_census_blocks(root):
    db = fresh(root)
    allocator = Allocator(db)
    cpu = allocator.acquire("traditional", "TRAD_MISSING_CENSUS", "attempt_001", backend_type="CPU", resource_snapshot=snap())
    case = "MISSING_CENSUS_J"
    enqueue(db, "coupling_ml", case, "attempt_001", payload("GPU"))
    launched = []
    assert dispatch(db, snap(errors=("process census unavailable",)), launched) == []
    evidence = json.loads(state(db, case)["payload_json"])["_v3_admission"]
    assert "CPU_FDTD_ACTIVE_FOREIGN_OWNER" in evidence["reasons"]
    assert "BACKEND_PROCESS_CENSUS_UNAVAILABLE" in evidence["reasons"]
    assert not launched
    assert next(x for x in allocator.list_slots_readonly() if x["slot_id"] == cpu.slot_id)["owner_branch"] == "traditional"
    allocator.release_owned(cpu, scientific_terminal="FAILED_PREENTRY")


def test_g_controller_restart_preserves_wait(root):
    db = fresh(root)
    allocator = Allocator(db)
    cpu = allocator.acquire("traditional", "TRAD_RESTART", "attempt_001", backend_type="CPU", resource_snapshot=snap())
    case = "RESTART_GPU_WAIT"
    enqueue(db, "coupling_ml", case, "attempt_001", payload("GPU"))
    launched = []
    assert dispatch(db, snap(), launched) == []
    reopened = ControlDB(db.path)
    allocator.release_owned(cpu, scientific_terminal="FAILED_PREENTRY")
    assert dispatch(reopened, snap(), launched) == [case]
    assert len(launched) == 1 and entries(reopened) == 0
    Allocator(reopened).release_owned(launched[0][1], scientific_terminal="FAILED_PREENTRY")


def main():
    tests = [
        test_a_cpu_active_blocks_gpu_and_free_slot_does_not_bypass,
        test_b_gpu_active_blocks_cpu,
        test_c_auto_wake_d_same_attempt_no_duplicate,
        test_d_gpu_release_allows_waiting_cpu,
        test_e_stale_process_without_lifecycle_blocks,
        test_f_active_lifecycle_missing_census_blocks,
        test_g_controller_restart_preserves_wait,
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="backend-mutex-", dir=PKG.parent) as root:
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
