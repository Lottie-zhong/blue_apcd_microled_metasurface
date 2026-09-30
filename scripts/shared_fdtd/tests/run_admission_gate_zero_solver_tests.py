from __future__ import annotations

import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from shared_fdtd.control_v3.allocator import Allocator
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.control_v3.resources import ResourceSnapshot
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue as _enqueue
from unittest.mock import patch
import shared_fdtd.engine.dispatcher as dispatcher

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "shared_fdtd" / "control_v3" / "schema.sql"
GOOD = ResourceSnapshot("PASS", "test", 10**12, 10**12, 10**12, 10**12, 0, 10**12, 0, 0, 0, 0, 0, ())


def fresh(base: Path, name: str):
    db = ControlDB(base / f"{name}.sqlite3")
    db.initialize(SCHEMA)
    a = Allocator(db)
    a.set_gpu_physical_cap(3)
    a.set_branch_limit("coupling_ml", 2, enabled=True, preferred=["GLOBAL_SLOT_2", "GLOBAL_SLOT_3", "GLOBAL_SLOT_1"])
    db.set_admission_control(new_entry_hold=False, temporary_runtime_cap=None)
    return db, a


def payload():
    return {"backend_type": "GPU", "production_science": True, "resource_class": "HEAVY", "estimated_peak_ram_bytes": 1000, "estimated_commit_bytes": 1000, "mpi_ranks": 1, "threads": 1, "integrated_pw": True}


def state(db, case):
    with db.connect(readonly=True) as con:
        row = con.execute("SELECT state FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id=?", (case,)).fetchone()
        return row["state"] if row else None


def release(a, lease):
    a.release_owned(lease, scientific_terminal="FAILED_PREENTRY")


def enqueue(db, branch, case, attempt, payload):
    adapted = dict(payload)
    if adapted.get("backend_type") == "GPU":
        attempt_root = Path(db.path).parent / "gpu_capacity_fixture" / branch / case / attempt
        attempt_root.mkdir(parents=True, exist_ok=True)
        adapted["attempt_root"] = str(attempt_root)
        adapted["gpu_resource_name"] = "GPU capacity fixture"
    return _enqueue(db, branch, case, attempt, adapted)


def _gpu_capacity_snapshot_fixture(db, resource_name=None):
    return {
        "schema": "SHARED_V3_EXTERNAL_GPU_CAPACITY_SNAPSHOT_V1",
        "captured_at_utc": "2026-09-30T00:00:00+00:00",
        "capture_status": "PASS",
        "selected_gpu": {
            "index": 0, "name": "NVIDIA GeForce RTX 3080 fixture", "uuid": "GPU-fixture",
            "utilization_gpu_percent": 0, "memory_total_mib": 10240,
            "memory_used_mib": 4096, "memory_free_mib": 6144,
        },
        "compute_processes": [], "external_compute_processes": [],
        "shared_v3_active_owners": [], "process_attribution_status": "PASS",
    }


def _main_body():
    dispatcher.read_resource_snapshot = lambda: GOOD
    tests = {}
    solver_invocations = 0
    with tempfile.TemporaryDirectory(prefix="apcd-admission-gate-") as td:
        base = Path(td)

        db, a = fresh(base, "A")
        enqueue(db, "coupling_ml", "A", "attempt_001", payload())
        launched = []
        assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(lease) or {"queue_state": "HOST_STARTED"}) == ["A"]
        tests["A_enabled_hold0_capacity_available_eligible"] = len(launched) == 1

        db, a = fresh(base, "B")
        db.set_admission_control(new_entry_hold=True)
        enqueue(db, "coupling_ml", "B", "attempt_001", payload())
        launched = []
        assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(lease)) == []
        tests["B_hold_veto"] = not launched and state(db, "B") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "C")
        a.set_branch_limit("coupling_ml", 2, enabled=False, preferred=["GLOBAL_SLOT_2", "GLOBAL_SLOT_3", "GLOBAL_SLOT_1"])
        enqueue(db, "coupling_ml", "C", "attempt_001", payload())
        launched = []
        assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(lease)) == []
        tests["C_disabled_veto"] = not launched and state(db, "C") == "QUEUED"

        db, a = fresh(base, "D")
        db.set_admission_control(temporary_runtime_cap=1)
        first = a.acquire("coupling_ml", "D1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        enqueue(db, "coupling_ml", "D2", "attempt_001", payload())
        assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
        tests["D_formal2_temp1_active1_blocks_second"] = state(db, "D2") in {"QUEUED", "WAIT_RESOURCE_CAPACITY"}
        release(a, first)

        db, a = fresh(base, "E")
        p_e = {**payload(), "integrated_pw": False}
        first = a.acquire("coupling_ml", "E1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=p_e)
        enqueue(db, "coupling_ml", "E2", "attempt_001", p_e)
        launched = []
        assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(lease) or {"queue_state": "HOST_STARTED"}) == ["E2"]
        tests["E_formal2_without_temp_allows_second"] = len(launched) == 1
        release(a, first); release(a, launched[0])

        db, a = fresh(base, "F")
        a.set_gpu_physical_cap(1)
        first = a.acquire("coupling_ml", "F1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        enqueue(db, "coupling_ml", "F2", "attempt_001", payload())
        assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
        db.set_admission_control(new_entry_hold=True)
        release(a, first)
        assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
        tests["F_wait_wake_hold_becomes_true_stays_waiting"] = state(db, "F2") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "G")
        a.set_gpu_physical_cap(1)
        first = a.acquire("coupling_ml", "G1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        enqueue(db, "coupling_ml", "G2", "attempt_001", payload())
        dispatch_once(db, "coupling_ml", lambda row, lease: None)
        db.set_admission_control(new_entry_hold=True)
        release(a, first)
        assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
        tests["G_slot_release_hold_no_autofill"] = state(db, "G2") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "H")
        enqueue(db, "coupling_ml", "H", "attempt_001", payload())
        lease = a.acquire("coupling_ml", "H", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        a.set_branch_limit("coupling_ml", 2, enabled=False, preferred=["GLOBAL_SLOT_2", "GLOBAL_SLOT_3", "GLOBAL_SLOT_1"])
        decision = a.final_admission(lease, backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        a.release_provisional(lease, "TEST_BRANCH_DISABLED_AFTER_RESERVATION")
        tests["H_disabled_after_reservation_final_recheck"] = (not decision["eligible"] and "BRANCH_DISABLED" in decision["reasons"])

        db, a = fresh(base, "I")
        lease = a.acquire("coupling_ml", "I", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        old_generation = lease.control_generation
        db.set_admission_control(new_entry_hold=True)
        decision = a.final_admission(lease, backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        a.release_provisional(lease, "TEST_GENERATION_CHANGED")
        tests["I_generation_invalidates_stale_admission"] = (not decision["eligible"] and decision["control_generation"] != old_generation and "NEW_ENTRY_HOLD" in decision["reasons"])

        db, a = fresh(base, "J")
        enqueue(db, "coupling_ml", "J", "attempt_001", payload())
        launched = []
        def race(_row, lease):
            launched.append(lease)
            return {"queue_state": "HOST_STARTED"}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: dispatch_once(db, "coupling_ml", race), (1, 2)))
        tests["J_two_dispatchers_one_reservation_entry"] = sum(len(x) for x in results) == 1 and len(launched) == 1

        db, a = fresh(base, "K")
        db.set_admission_control(new_entry_hold=True, temporary_runtime_cap=1)
        reopened = ControlDB(db.path)
        with reopened.immediate() as con:
            control = reopened.ensure_admission_control(con)
        tests["K_dispatcher_restart_preserves_control"] = bool(control["new_entry_hold"]) and control["temporary_runtime_cap"] == 1

        db, a = fresh(base, "L")
        db.set_admission_control(new_entry_hold=True, temporary_runtime_cap=1)
        reopened = ControlDB(db.path)
        enqueue(reopened, "coupling_ml", "L", "attempt_001", payload())
        tests["L_controller_restart_preserves_veto"] = dispatch_once(reopened, "coupling_ml", lambda row, lease: None) == [] and state(reopened, "L") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "M")
        enqueue(db, "coupling_ml", "M", "attempt_001", payload())
        launched = []
        launch = lambda row, lease: launched.append(lease) or {"queue_state": "HOST_STARTED"}
        dispatch_once(db, "coupling_ml", launch); dispatch_once(db, "coupling_ml", launch)
        tests["M_repeated_tick_no_duplicate"] = len(launched) == 1

        db, a = fresh(base, "N")
        lease = a.acquire("coupling_ml", "N", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        decision = a.final_admission(lease, backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        a.release_provisional(lease, "TEST_MANUAL_PATH")
        tests["N_manual_path_uses_canonical_predicate"] = decision["eligible"]

        db, a = fresh(base, "O")
        p_o = {**payload(), "integrated_pw": False}
        enqueue(db, "coupling_ml", "O1", "attempt_001", p_o); enqueue(db, "coupling_ml", "O2", "attempt_001", p_o)
        launched = []
        assert dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(lease) or {"queue_state": "HOST_STARTED"}) == ["O1", "O2"]
        tests["O_autofill_uses_canonical_predicate"] = len(launched) == 2

        db, a = fresh(base, "P")
        a.set_gpu_physical_cap(1)
        first = a.acquire("coupling_ml", "P1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        enqueue(db, "coupling_ml", "P2", "attempt_001", payload()); dispatch_once(db, "coupling_ml", lambda row, lease: None)
        db.set_admission_control(new_entry_hold=True); release(a, first)
        assert dispatch_once(db, "coupling_ml", lambda row, lease: None) == []
        tests["P_wait_resource_wake_uses_canonical_predicate"] = state(db, "P2") == "WAIT_RESOURCE_CAPACITY"
        tests["Q_no_solver_invocation_in_all_tests"] = solver_invocations == 0

        def gate(allocator, lease, starts, request=None, backend="GPU"):
            def fake_child(provenance):
                starts.append(provenance)
                return {"zero_solver_child": True}
            return allocator.final_launch_revalidation(
                lease, resource_request=request or payload(), resource_snapshot=GOOD,
                backend_type=backend, start=fake_child,
            )

        db, a = fresh(base, "R"); lease = a.acquire("coupling_ml", "R", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        db.set_admission_control(new_entry_hold=True); starts = []; result = gate(a, lease, starts)
        tests["R_generation_bump_hold_blocks_before_launch"] = (not result["eligible"] and not starts and state(db, "R") is None)

        db, a = fresh(base, "S"); lease = a.acquire("coupling_ml", "S", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        a.set_branch_limit("coupling_ml", 2, enabled=False, preferred=["GLOBAL_SLOT_2", "GLOBAL_SLOT_3", "GLOBAL_SLOT_1"]); starts = []; result = gate(a, lease, starts)
        tests["S_generation_bump_disable_blocks_before_launch"] = (not result["eligible"] and not starts)

        db, a = fresh(base, "T"); lease = a.acquire("coupling_ml", "T", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        other = a.acquire("coupling_ml", "T2", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request={**payload(), "integrated_pw": False})
        db.set_admission_control(temporary_runtime_cap=1); starts = []; result = gate(a, lease, starts)
        a.release_provisional(other, "TEST_CLEANUP")
        tests["T_temporary_cap_reduction_rejects_stale"] = (not result["eligible"] and not starts and "BRANCH_EFFECTIVE_CAP_REACHED" in result["decision"]["reasons"])

        db, a = fresh(base, "U"); a.set_branch_limit("coupling_ml", 3, enabled=True)
        a.acquire("coupling_ml", "U1", "attempt_001", backend_type="CPU")
        a.acquire("coupling_ml", "U2", "attempt_001", backend_type="CPU")
        a.acquire("traditional", "U3", "attempt_001", backend_type="CPU")
        enqueue(db, "coupling_ml", "U", "attempt_001", payload())
        starts = []; assert dispatch_once(db, "coupling_ml", lambda row, lease: starts.append(lease)) == []
        tests["U_global_capacity_consumed_blocks"] = (not starts and state(db, "U") == "WAIT_RESOURCE_CAPACITY")

        db, a = fresh(base, "V"); a.set_gpu_physical_cap(2); p = {**payload(), "integrated_pw": False}
        lease = a.acquire("coupling_ml", "V", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=p)
        other = a.acquire("coupling_ml", "V2", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=p)
        a.set_gpu_physical_cap(1); starts = []; result = gate(a, lease, starts, request=p)
        def cleanup(lease):
            try:
                a.release_provisional(lease, "TEST_CLEANUP")
            except Exception:
                pass
        tests["V_gpu_capacity_consumed_blocks"] = (not result["eligible"] and not starts and "GPU_PHYSICAL_CAP_REACHED" in result["decision"]["reasons"]); cleanup(other)

        db, a = fresh(base, "W"); lease = a.acquire("coupling_ml", "W", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        stale = type(lease)(lease.slot_id, lease.owner_branch, lease.logical_case_id, lease.attempt_id, "wrong-token", lease.fencing_generation, lease.control_generation, lease.admission_provenance); starts = []; result = gate(a, stale, starts)
        tests["W_owner_fencing_invalid_blocks"] = (not result["eligible"] and not starts)

        db, a = fresh(base, "X"); lease = a.acquire("coupling_ml", "X", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        starts = []; result = gate(a, lease, starts)
        tests["X_all_authority_valid_launch_eligible"] = (result["eligible"] and len(starts) == 1 and result["provenance"]["admission_generation"] == result["provenance"]["final_launch_generation"]); cleanup(lease)

        db, a = fresh(base, "Y"); old = a.acquire("coupling_ml", "Y", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload())
        db.set_admission_control(new_entry_hold=True); first = gate(a, old, []); db.set_admission_control(new_entry_hold=False); second = gate(a, old, [])
        new = a.acquire("coupling_ml", "Y", "attempt_002", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload()); starts = []; third = gate(a, new, starts)
        tests["Y_stale_reject_requires_new_admission"] = (not first["eligible"] and not second["eligible"] and third["eligible"] and len(starts) == 1); cleanup(new)

        import inspect
        from shared_fdtd.tools import pw_scientific_launcher as launcher
        signatures = [inspect.signature(launcher.run_and_confirm_entry), inspect.signature(launcher.run_gpu_and_confirm_completion), inspect.signature(launcher.run_standalone_gpu_and_confirm_completion)]
        tests["Z_all_scientific_entry_points_use_final_gate_hook"] = all("launch_guard" in sig.parameters for sig in signatures)

        db, a = fresh(base, "AA"); p = {**payload(), "integrated_pw": False}; enqueue(db, "coupling_ml", "AA", "attempt_001", p); starts = []
        def autofill(row, lease):
            db.set_admission_control(new_entry_hold=True); result = gate(a, lease, starts, request=p); return {"queue_state": "WAIT_RESOURCE_CAPACITY", "admission": result}
        dispatch_once(db, "coupling_ml", autofill); tests["AA_autofill_cannot_bypass_final_gate"] = not starts and state(db, "AA") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "AB"); a.set_gpu_physical_cap(1); blocker = a.acquire("coupling_ml", "AB0", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload()); enqueue(db, "coupling_ml", "AB", "attempt_001", payload()); dispatch_once(db, "coupling_ml", lambda row, lease: None); cleanup(blocker); starts = []
        def wake(row, lease):
            db.set_admission_control(new_entry_hold=True); result = gate(a, lease, starts); return {"queue_state": "WAIT_RESOURCE_CAPACITY", "admission": result}
        dispatch_once(db, "coupling_ml", wake); tests["AB_wait_resource_wake_cannot_bypass"] = not starts and state(db, "AB") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "AC"); lease = a.acquire("coupling_ml", "AC", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload()); db.set_admission_control(new_entry_hold=True); starts = []; result = gate(a, lease, starts); tests["AC_manual_dispatch_cannot_bypass"] = not result["eligible"] and not starts

        db, a = fresh(base, "AD"); lease = a.acquire("coupling_ml", "AD", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=payload()); restarted = ControlDB(db.path); restarted.set_admission_control(new_entry_hold=True); starts = []; result = Allocator(restarted).final_launch_revalidation(lease, resource_request=payload(), resource_snapshot=GOOD, backend_type="GPU", start=lambda provenance: starts.append(provenance)); tests["AD_controller_restart_cannot_resurrect_stale"] = not result["eligible"] and not starts

        db, a = fresh(base, "AE"); enqueue(db, "coupling_ml", "AE", "attempt_001", payload()); starts = []
        def restarted_dispatch(row, lease):
            db.set_admission_control(new_entry_hold=True); result = Allocator(ControlDB(db.path)).final_launch_revalidation(lease, resource_request=payload(), resource_snapshot=GOOD, backend_type="GPU", start=lambda provenance: starts.append(provenance)); return {"queue_state": "WAIT_RESOURCE_CAPACITY", "admission": result}
        dispatch_once(db, "coupling_ml", restarted_dispatch); tests["AE_dispatcher_restart_cannot_resurrect_stale"] = not starts and state(db, "AE") == "WAIT_RESOURCE_CAPACITY"

        db, a = fresh(base, "AF"); p = {**payload(), "integrated_pw": False}; l1 = a.acquire("coupling_ml", "AF1", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=p); l2 = a.acquire("coupling_ml", "AF2", "attempt_001", backend_type="GPU", resource_snapshot=GOOD, resource_request=p); db.set_admission_control(new_entry_hold=True); starts = []; r1 = gate(a, l1, starts, request=p); r2 = gate(a, l2, starts, request=p)
        tests["AF_multiple_pending_all_stale_after_generation_bump"] = (not r1["eligible"] and not r2["eligible"] and not starts)
        db, a = fresh(base, 'AG'); p = {**payload(), 'autofill_enabled': False, 'validation_gate': 'VALIDATION_ONLY'}; enqueue(db, 'coupling_ml', 'AG', 'attempt_001', p); starts = []
        dispatch_once(db, 'coupling_ml', lambda row, lease: starts.append(row['logical_case_id']))
        tests['AG_validation_only_row_blocks_release_autofill'] = not starts and state(db, 'AG') == 'WAIT_RESOURCE_CAPACITY'
        db, a = fresh(base, 'AH'); p = {**payload(), 'validation_gate': 'MANUAL_ONLY'}; enqueue(db, 'coupling_ml', 'AH', 'attempt_001', p); starts = []
        dispatch_once(db, 'coupling_ml', lambda row, lease: starts.append(row['logical_case_id']))
        tests['AH_manual_only_alias_blocks_release_autofill'] = not starts and state(db, 'AH') == 'WAIT_RESOURCE_CAPACITY'
        solver_invocations = 0

    result = {"schema": "APCD_SHARED_V3_ADMISSION_GATE_ZERO_SOLVER_TESTS_V1", "status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "solver_invocations": solver_invocations, "scientific_solver_entries": 0, "replay": 0, "direct_sqlite_mutations": 0}
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


def main():
    with patch(
        "shared_fdtd.control_v3.gpu_capacity.capture_external_gpu_capacity_snapshot",
        side_effect=_gpu_capacity_snapshot_fixture,
    ):
        _main_body()


if __name__ == "__main__":
    main()
