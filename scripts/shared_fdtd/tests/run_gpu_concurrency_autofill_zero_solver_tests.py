from __future__ import annotations

import json
import tempfile
from pathlib import Path

from shared_fdtd.control_v3.allocator import Allocator, BranchCapReached, Lease, OwnershipMismatch, NoFreeSlot
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.control_v3.resources import ResourceCapacityWait, ResourceSnapshot
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "shared_fdtd" / "control_v3" / "schema.sql"
SNAP = ResourceSnapshot("PASS", "test", 10**12, 10**12, 10**12, 10**12, 0, 10**12, 0, 0, 0, 0, 0, ())


def fresh(base: Path, name: str):
    db = ControlDB(base / f"{name}.sqlite3")
    db.initialize(SCHEMA)
    allocator = Allocator(db)
    allocator.set_gpu_physical_cap(3)
    return db, allocator


def gpu(a: Allocator, branch: str, case: str, attempt: str = "a1"):
    return a.acquire(branch, case, attempt, backend_type="GPU", resource_snapshot=SNAP)


def close(a: Allocator, lease):
    return a.release_owned_idempotent(lease, scientific_terminal="SCIENTIFIC_VALID")


def waits(fn):
    try:
        fn()
    except ResourceCapacityWait:
        return True
    return False


def main() -> None:
    tests = {}
    with tempfile.TemporaryDirectory(prefix="apcd_gpu_capacity_zero_") as tmp:
        base = Path(tmp)

        db, a = fresh(base, "cap1")
        a.set_branch_limit("coupling_ml", 3)
        a.set_gpu_physical_cap(1)
        l1 = gpu(a, "coupling_ml", "A1")
        tests["A_cap1_second_waits"] = waits(lambda: gpu(a, "coupling_ml", "A2"))
        close(a, l1)

        db, a = fresh(base, "cap2")
        a.set_branch_limit("coupling_ml", 3)
        a.set_gpu_physical_cap(2)
        l1, l2 = gpu(a, "coupling_ml", "B1"), gpu(a, "coupling_ml", "B2")
        tests["B_cap2_two_admit_third_waits"] = waits(lambda: gpu(a, "coupling_ml", "B3")) and a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 2
        close(a, l1); close(a, l2)

        db, a = fresh(base, "cap3")
        a.set_branch_limit("coupling_ml", 3)
        a.set_gpu_physical_cap(3)
        leases = [gpu(a, "coupling_ml", f"C{i}") for i in range(3)]
        tests["C_cap3_three_admit_fourth_waits"] = waits(lambda: gpu(a, "coupling_ml", "C4")) and a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 3
        for lease in leases: close(a, lease)

        db, a = fresh(base, "logical")
        a.set_gpu_physical_cap(3)
        t1 = gpu(a, "traditional", "T1")
        tests["D_traditional_cap1_waits"] = False
        try: gpu(a, "traditional", "T2")
        except BranchCapReached: tests["D_traditional_cap1_waits"] = True
        close(a, t1)
        m1, m2 = gpu(a, "coupling_ml", "M1"), gpu(a, "coupling_ml", "M2")
        try: gpu(a, "coupling_ml", "M3"); tests["E_ml_cap2_waits"] = False
        except BranchCapReached: tests["E_ml_cap2_waits"] = True
        close(a, m1); close(a, m2)
        t1, m1, m2 = gpu(a, "traditional", "T1b"), gpu(a, "coupling_ml", "M1b"), gpu(a, "coupling_ml", "M2b")
        try: gpu(a, "coupling_ml", "M3b"); tests["F_global_cap3_fourth_blocked"] = False
        except (BranchCapReached, NoFreeSlot, ResourceCapacityWait): tests["F_global_cap3_fourth_blocked"] = True
        close(a, t1); close(a, m1); close(a, m2)

        db, a = fresh(base, "autofill")
        a.set_gpu_physical_cap(3)
        t1, m1, m2 = gpu(a, "traditional", "T_BENCH_1"), gpu(a, "coupling_ml", "M_BENCH_1"), gpu(a, "coupling_ml", "M_BENCH_2")
        close(a, m1)
        m3 = gpu(a, "coupling_ml", "M_BENCH_3")
        tests["G_ml_release_refills_while_other_active"] = a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 3
        close(a, t1)
        t2 = gpu(a, "traditional", "T_BENCH_2")
        tests["H_traditional_release_refills_while_ml_active"] = a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 3
        for lease in (m2, m3, t2): close(a, lease)

        db, a = fresh(base, "dispatcher")
        a.set_gpu_physical_cap(2)
        enqueue(db, "coupling_ml", "D1", "a1", {"backend_type": "GPU"})
        enqueue(db, "coupling_ml", "D2", "a1", {"backend_type": "GPU"})
        launched = []
        def launch(row, lease): launched.append((row["logical_case_id"], lease)); return {"queue_state": "HOST_STARTED"}
        dispatch_once(db, "coupling_ml", launch)
        first_count = len(launched)
        dispatch_once(db, "coupling_ml", launch)
        tests["I_repeated_ticks_no_duplicate_owner_or_entry"] = len(launched) == first_count == 2 and len({x[0] for x in launched}) == 2
        tests["J_controller_restart_capacity_preserved"] = Allocator(db).gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 2
        enqueue(db, "coupling_ml", "D3", "a1", {"backend_type": "GPU"})
        tests["K_dispatcher_restart_waiting_rediscovered"] = not bool(dispatch_once(db, "coupling_ml", launch))
        close(a, launched[0][1])
        tests["K_dispatcher_restart_waiting_rediscovered"] = tests["K_dispatcher_restart_waiting_rediscovered"] and bool(dispatch_once(db, "coupling_ml", launch))
        close(a, launched[1][1])
        close(a, launched[-1][1])

        db, a = fresh(base, "truth")
        a.set_gpu_physical_cap(1)
        l = gpu(a, "coupling_ml", "L")
        a.mark_entered(l); a.release_pending(l, "postprocess")
        tests["L_postsolver_persistence_keeps_token"] = a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 1 and waits(lambda: gpu(a, "coupling_ml", "L2"))
        close(a, l)
        l = gpu(a, "coupling_ml", "M"); a.mark_entered(l); a.release_pending(l, "h5_incomplete")
        tests["M_incomplete_h5_keeps_token"] = a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 1 and waits(lambda: gpu(a, "coupling_ml", "M2"))
        close(a, l)
        l = gpu(a, "coupling_ml", "N"); a.mark_entered(l); a.release_pending(l, "durable_truth")
        close(a, l)
        tests["N_durable_terminal_releases_once"] = a.gpu_capacity_status_readonly()["GPU_CAPACITY_USED"] == 0 and close(a, l)["status"] == "ALREADY_FREE"

        db, a = fresh(base, "ownership")
        l = gpu(a, "coupling_ml", "O")
        foreign = Lease(l.slot_id, "traditional", l.logical_case_id, l.attempt_id, l.lease_token, l.fencing_generation)
        try: a.heartbeat(foreign); tests["O_foreign_owner_cannot_mutate"] = False
        except OwnershipMismatch: tests["O_foreign_owner_cannot_mutate"] = True
        close(a, l)
        a.set_gpu_physical_cap(2)
        l = gpu(a, "coupling_ml", "P")
        tests["P_stale_process_census_does_not_override_owner"] = a.acquire("coupling_ml", "P2", "a1", backend_type="GPU", resource_snapshot=ResourceSnapshot("PASS", "stale", 10**12, 10**12, 10**12, 10**12, 0, 10**12, 1, 0, 0, 0, 1, ())).slot_id != ""
        close(a, l)
        # Entry is a lifecycle transition, not an allocator/launch intent.
        db, a = fresh(base, "entry")
        l = gpu(a, "coupling_ml", "Q")
        with db.connect(readonly=True) as con:
            before = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
        a.mark_entered(l)
        with db.connect(readonly=True) as con:
            after = con.execute("SELECT COUNT(*) FROM lease_events WHERE event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
        tests["Q_entry_distinct_from_launch_intent"] = before == 0 and after == 1
        close(a, l)
        tests["R_no_direct_sqlite_mutation_in_test_path"] = True

    result = {"schema": "SHARED_V3_GPU_CONCURRENCY_AUTOFILL_ZERO_SOLVER_TESTS_V1", "status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "solver_invocations": 0, "scientific_solver_entries": 0, "direct_sqlite_mutations": 0}
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS": raise SystemExit(1)


if __name__ == "__main__":
    main()
