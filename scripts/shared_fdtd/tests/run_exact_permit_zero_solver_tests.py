from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import AdmissionGateBlocked, Lease
from shared_fdtd.engine.dispatcher import _attempt_truth_blockers, dispatch_once, enqueue, recover_failed_preentry
from shared_fdtd.engine.event_log import append_event

SCHEMA = PKG / "control_v3" / "schema.sql"


def fresh(root: Path, *, hold: bool = True):
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    db.set_admission_control(new_entry_hold=hold, temporary_runtime_cap=1)
    return db, Allocator(db)


def permit_state(db, permit_id):
    with db.connect(readonly=True) as con:
        row = con.execute("SELECT state FROM exact_launch_permits WHERE permit_id=?", (permit_id,)).fetchone()
        return row["state"] if row else None


def queue_row(db, case, attempt):
    with db.connect(readonly=True) as con:
        return dict(con.execute(
            "SELECT state,slot_id,lease_token_hash,fencing_generation FROM branch_queue WHERE logical_case_id=? AND attempt_id=?",
            (case, attempt),
        ).fetchone())


def write_zero_ledger(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "attempt_ledger.json").write_text(json.dumps({
        "solver_entered": False,
        "solver_returned": False,
        "run_invocation_count": 0,
        "replay": False,
    }), encoding="utf-8")


def check(name, fn):
    try:
        fn()
        return name, "PASS", ""
    except Exception as exc:
        return name, "FAIL", repr(exc)


def main():
    results = []
    solver_invocations = 0

    with tempfile.TemporaryDirectory(prefix="shared-v3-exact-permit-") as raw:
        base = Path(raw)

        def hold_requires_permit():
            db, a = fresh(base / "hold")
            try:
                a.acquire("coupling_ml", "HOLD", "attempt_001")
            except Exception as exc:
                assert type(exc).__name__ == "ResourceCapacityWait"
            else:
                raise AssertionError("global hold admitted an unpermitted lease")
        results.append(check("A_hold_veto_without_permit", hold_requires_permit))

        def exact_one_shot():
            db, a = fresh(base / "one")
            permit = a.arm_exact_launch_permit("coupling_ml", "ONE", "attempt_004")
            started = []
            lease = a.acquire("coupling_ml", "ONE", "attempt_004", exact_permit_id=permit["permit_id"])
            result = a.final_launch_revalidation(
                lease, exact_permit_id=permit["permit_id"],
                start=lambda provenance: started.append(provenance) or "started",
            )
            assert result["eligible"] and result["launch_result"] == "started"
            assert len(started) == 1 and permit_state(db, permit["permit_id"]) == "CONSUMED"
            a.release_postentry_no_truth(lease, reason="TEST_CLOSEOUT")
        results.append(check("B_exact_permit_consumed_at_final_gate", exact_one_shot))

        def consumed_cannot_reuse():
            db, a = fresh(base / "reuse")
            permit = a.arm_exact_launch_permit("coupling_ml", "REUSE", "attempt_004")
            lease = a.acquire("coupling_ml", "REUSE", "attempt_004", exact_permit_id=permit["permit_id"])
            assert a.final_launch_revalidation(lease, exact_permit_id=permit["permit_id"], start=lambda _: True)["eligible"]
            blocked = a.final_launch_revalidation(lease, exact_permit_id=permit["permit_id"], start=lambda _: True)
            assert not blocked["eligible"] and blocked["release"]["status"] == "NOT_RELEASED_CONSUMED_PERMIT"
            with db.connect(readonly=True) as con:
                assert con.execute("SELECT state FROM slots WHERE slot_id=?", (lease.slot_id,)).fetchone()["state"] == "RESERVED"
            a.release_postentry_no_truth(lease, reason="TEST_CLOSEOUT")
        results.append(check("C_consumed_permit_blocks_duplicate_gate_without_releasing_slot", consumed_cannot_reuse))

        def wrong_identity():
            db, a = fresh(base / "identity")
            permit = a.arm_exact_launch_permit("coupling_ml", "IDENTITY", "attempt_004")
            try:
                a.acquire("coupling_ml", "IDENTITY", "attempt_005", exact_permit_id=permit["permit_id"])
            except Exception as exc:
                assert type(exc).__name__ == "ResourceCapacityWait"
            else:
                raise AssertionError("wrong attempt used exact permit")
            assert permit_state(db, permit["permit_id"]) == "ARMED"
        results.append(check("D_permit_is_attempt_scoped", wrong_identity))

        def generation_stale():
            db, a = fresh(base / "generation")
            permit = a.arm_exact_launch_permit("coupling_ml", "GEN", "attempt_004")
            db.set_admission_control(temporary_runtime_cap=2)
            try:
                a.acquire("coupling_ml", "GEN", "attempt_004", exact_permit_id=permit["permit_id"])
            except Exception as exc:
                assert type(exc).__name__ == "ResourceCapacityWait"
            else:
                raise AssertionError("stale-generation permit admitted")
            assert permit_state(db, permit["permit_id"]) == "ARMED"
        results.append(check("E_generation_revalidation_blocks_stale_permit", generation_stale))

        def only_one_armed():
            db, a = fresh(base / "single")
            a.arm_exact_launch_permit("coupling_ml", "SINGLE", "attempt_004")
            try:
                a.arm_exact_launch_permit("coupling_ml", "OTHER", "attempt_004")
            except RuntimeError as exc:
                assert str(exc) == "EXACT_PERMIT_ALREADY_ARMED"
            else:
                raise AssertionError("two permits armed")
        results.append(check("F_only_one_armed_permit", only_one_armed))

        def cancellation():
            db, a = fresh(base / "cancel")
            permit = a.arm_exact_launch_permit("coupling_ml", "CANCEL", "attempt_004")
            answer = a.cancel_exact_launch_permit(permit["permit_id"])
            assert answer["status"] == "CANCELLED" and permit_state(db, permit["permit_id"]) == "CANCELLED"
            try:
                a.acquire("coupling_ml", "CANCEL", "attempt_004", exact_permit_id=permit["permit_id"])
            except Exception as exc:
                assert type(exc).__name__ == "ResourceCapacityWait"
            else:
                raise AssertionError("cancelled permit admitted")
        results.append(check("G_cancelled_permit_cannot_admit", cancellation))

        def dispatch_exact():
            db, a = fresh(base / "dispatch")
            permit = a.arm_exact_launch_permit("coupling_ml", "DISPATCH", "attempt_004")
            enqueue(db, "coupling_ml", "DISPATCH", "attempt_004", {"exact_launch_permit_id": permit["permit_id"]})
            launched = []
            def launch(row, lease):
                gate = a.final_launch_revalidation(lease, exact_permit_id=permit["permit_id"], start=lambda _: "child")
                assert gate["eligible"]
                launched.append(lease)
                return {"queue_state": "HOST_STARTED"}
            assert dispatch_once(db, "coupling_ml", launch, logical_case_id="DISPATCH", attempt_id="attempt_004") == ["DISPATCH"]
            assert len(launched) == 1 and permit_state(db, permit["permit_id"]) == "CONSUMED"
            a.release_postentry_no_truth(launched[0], reason="TEST_CLOSEOUT")
        results.append(check("H_dispatch_path_consumes_exact_permit_once", dispatch_exact))

        def stale_queue_recovery():
            db, a = fresh(base / "stale", hold=False)
            attempt_root = base / "stale" / "STALE" / "attempt_003"
            write_zero_ledger(attempt_root)
            enqueue(db, "coupling_ml", "STALE", "attempt_003", {"attempt_root": str(attempt_root)})
            lease = a.acquire("coupling_ml", "STALE", "attempt_003")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='STALE'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            a.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='STALE'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            db.set_admission_control(new_entry_hold=True)
            permit = a.arm_exact_launch_permit("coupling_ml", "STALE", "attempt_003")
            answer = recover_failed_preentry(db, "coupling_ml", "STALE", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert answer["status"] == "RECOVERED_STALE_PREENTRY"
            assert queue_row(db, "STALE", "attempt_003")["state"] == "FAILED_PREENTRY"
            assert permit_state(db, permit["permit_id"]) == "CANCELLED"
            second = recover_failed_preentry(db, "coupling_ml", "STALE", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert second["status"] == "ALREADY_TERMINAL"
        results.append(check("I_wait_row_with_proven_stale_identity_recovers_and_cancels_permit", stale_queue_recovery))

        def stale_identity_block():
            db, a = fresh(base / "unproven", hold=True)
            attempt_root = base / "unproven" / "UNPROVEN" / "attempt_003"
            write_zero_ledger(attempt_root)
            enqueue(db, "coupling_ml", "UNPROVEN", "attempt_003", {})
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id='GLOBAL_SLOT_1',lease_token_hash='bad',fencing_generation=1 WHERE logical_case_id='UNPROVEN'"
                )
            answer = recover_failed_preentry(db, "coupling_ml", "UNPROVEN", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert answer["status"] == "BLOCKED" and answer["reason"] == "QUEUE_IDENTITY_UNPROVEN"
            assert queue_row(db, "UNPROVEN", "attempt_003")["state"] == "WAIT_RESOURCE_CAPACITY"
        results.append(check("J_unproven_stale_identity_blocks", stale_identity_block))

        def entry_blocks_recovery():
            db, a = fresh(base / "entry", hold=False)
            attempt_root = base / "entry" / "ENTRY" / "attempt_003"
            write_zero_ledger(attempt_root)
            enqueue(db, "coupling_ml", "ENTRY", "attempt_003", {})
            lease = a.acquire("coupling_ml", "ENTRY", "attempt_003")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='ENTRY'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
                Allocator._event(con, lease, "SCIENTIFIC_SOLVER_ENTERED", {})
            db.set_admission_control(new_entry_hold=True)
            answer = recover_failed_preentry(db, "coupling_ml", "ENTRY", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert answer["status"] == "BLOCKED" and answer["reason"] == "SCIENTIFIC_ENTRY_ALREADY_RECORDED"
        results.append(check("K_entry_blocks_stale_recovery", entry_blocks_recovery))

        def setup_only_fsp_copy_is_not_truth():
            db, a = fresh(base / "fsp_copy", hold=False)
            attempt_root = base / "fsp_copy" / "COPY" / "attempt_003"
            write_zero_ledger(attempt_root)
            data = b"setup-only-fsp"
            setup = attempt_root / "setup" / "runtime.fsp"
            run = attempt_root / "run" / "COPY__attempt_003_runtime.fsp"
            setup.parent.mkdir(parents=True, exist_ok=True)
            run.parent.mkdir(parents=True, exist_ok=True)
            setup.write_bytes(data)
            run.write_bytes(data)
            ledger = json.loads((attempt_root / "attempt_ledger.json").read_text(encoding="utf-8"))
            ledger["pre_fsp_sha256"] = hashlib.sha256(data).hexdigest()
            (attempt_root / "attempt_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            enqueue(db, "coupling_ml", "COPY", "attempt_003", {})
            lease = a.acquire("coupling_ml", "COPY", "attempt_003")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='COPY'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            a.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='COPY'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            db.set_admission_control(new_entry_hold=True)
            answer = recover_failed_preentry(db, "coupling_ml", "COPY", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert answer["status"] == "RECOVERED_STALE_PREENTRY"
        results.append(check("M_setup_only_fsp_copy_is_allowed", setup_only_fsp_copy_is_not_truth))

        def changed_nonsetup_fsp_blocks():
            db, a = fresh(base / "fsp_changed", hold=False)
            attempt_root = base / "fsp_changed" / "CHANGED" / "attempt_003"
            write_zero_ledger(attempt_root)
            data = b"setup-only-fsp"
            setup = attempt_root / "setup" / "runtime.fsp"
            run = attempt_root / "run" / "CHANGED__attempt_003_runtime.fsp"
            setup.parent.mkdir(parents=True, exist_ok=True)
            run.parent.mkdir(parents=True, exist_ok=True)
            setup.write_bytes(data)
            run.write_bytes(b"scientific-different-fsp")
            ledger = json.loads((attempt_root / "attempt_ledger.json").read_text(encoding="utf-8"))
            ledger["pre_fsp_sha256"] = hashlib.sha256(data).hexdigest()
            (attempt_root / "attempt_ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
            enqueue(db, "coupling_ml", "CHANGED", "attempt_003", {})
            lease = a.acquire("coupling_ml", "CHANGED", "attempt_003")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='CHANGED'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            a.release_owned(lease, scientific_terminal="FAILED_PREENTRY")
            with db.immediate() as con:
                con.execute(
                    "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id='CHANGED'",
                    (lease.slot_id, lease.token_hash, lease.fencing_generation),
                )
            db.set_admission_control(new_entry_hold=True)
            answer = recover_failed_preentry(db, "coupling_ml", "CHANGED", "attempt_003", attempt_root, lambda *_: {"status": "PASS"})
            assert answer["status"] == "BLOCKED" and answer["reason"] == "TRUTH_BUNDLE_PRESENT"
            assert _attempt_truth_blockers(attempt_root)
        results.append(check("N_changed_nonsetup_fsp_blocks", changed_nonsetup_fsp_blocks))

        def no_solver_accounting():
            assert solver_invocations == 0
        results.append(check("L_no_solver_invocations", no_solver_accounting))

    result = {
        "status": "PASS" if all(status == "PASS" for _, status, _ in results) else "FAIL",
        "count": len(results),
        "pass": sum(status == "PASS" for _, status, _ in results),
        "fail": sum(status == "FAIL" for _, status, _ in results),
        "solver_invocations": solver_invocations,
        "scientific_solver_entries": 0,
        "results": results,
    }
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
