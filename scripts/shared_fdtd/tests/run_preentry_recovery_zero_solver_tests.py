from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.control_v3.allocator import Lease
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue, recover_failed_preentry
from shared_fdtd.engine.event_log import read_events

SCHEMA = PKG / "control_v3" / "schema.sql"


def fresh(root: Path) -> ControlDB:
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    db.set_admission_control(new_entry_hold=False, temporary_runtime_cap=1)
    return db


def fixture(root: Path, case=None, attempt="attempt_001"):
    root.mkdir(parents=True, exist_ok=True)
    case = case or root.name
    db = fresh(root)
    attempt_root = root / case / attempt
    attempt_root.mkdir(parents=True)
    enqueue(db, "coupling_ml", case, attempt, {"attempt_root": str(attempt_root)})
    lease = Allocator(db).acquire("coupling_ml", case, attempt)
    with db.immediate() as con:
        con.execute(
            "UPDATE branch_queue SET state='HOST_STARTED',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id=? AND attempt_id=?",
            (lease.slot_id, lease.token_hash, lease.fencing_generation, case, attempt),
        )
    db.set_admission_control(new_entry_hold=True)
    return db, attempt_root, lease


def probe(*results):
    values = list(results)
    def call(_root, _events):
        return values.pop(0) if values else {"status": "PASS", "processes": []}
    return call


def state(db, case="A", attempt="attempt_001"):
    with db.connect(readonly=True) as con:
        queue = con.execute(
            "SELECT state,slot_id,lease_token_hash,fencing_generation FROM branch_queue WHERE logical_case_id=? AND attempt_id=?",
            (case, attempt),
        ).fetchone()
        slots = con.execute("SELECT slot_id,state,owner_branch,logical_case_id,attempt_id FROM slots ORDER BY slot_id").fetchall()
        released = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND attempt_id=? AND event_type='LEASE_RELEASED'",
            (case, attempt),
        ).fetchone()[0]
    return {
        "queue": dict(queue) if queue else None,
        "slots": [dict(row) for row in slots],
        "released": released,
    }


def db_event(db, lease: Lease, event_type: str):
    with db.immediate() as con:
        Allocator._event(con, lease, event_type, {})


def check(name, function):
    try:
        function()
        return name, "PASS", ""
    except Exception as exc:
        return name, "FAIL", repr(exc)


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="preentry_recovery_zero_solver_") as raw:
        root = Path(raw)

        def recovered():
            db, attempt_root, _ = fixture(root / "A")
            result = recover_failed_preentry(db, "coupling_ml", "A", "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert result["status"] == "RECOVERED_FAILED_PREENTRY"
            current = state(db)
            assert current["queue"]["state"] == "FAILED_PREENTRY" and all(row["state"] == "FREE" for row in current["slots"])
            assert current["queue"]["slot_id"] is None and current["queue"]["fencing_generation"] is None
            assert current["released"] == 1
        results.append(check("A_dead_host_zero_entry_terminalizes_and_releases", recovered))

        def idempotent():
            db, attempt_root, _ = fixture(root / "B")
            first = recover_failed_preentry(db, "coupling_ml", "B", "attempt_001", attempt_root, probe({"status": "PASS"}))
            second = recover_failed_preentry(db, "coupling_ml", "B", "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert first["status"] == "RECOVERED_FAILED_PREENTRY" and second["status"] == "ALREADY_TERMINAL"
            assert state(db, "B")["released"] == 1
        results.append(check("B_repeated_recovery_is_idempotent", idempotent))

        def blocked_probe(result, name):
            db, attempt_root, _ = fixture(root / name)
            answer = recover_failed_preentry(db, "coupling_ml", name, "attempt_001", attempt_root, probe(result))
            assert answer["status"] == "BLOCKED" and state(db, name)["queue"]["state"] == "HOST_STARTED"
        results.append(check("C_host_alive_blocks", lambda: blocked_probe({"status": "BLOCKED", "reason": "HOST_ALIVE"}, "C")))
        results.append(check("D_descendant_alive_blocks", lambda: blocked_probe({"status": "BLOCKED", "reason": "DESCENDANT_ALIVE"}, "D")))

        def entry_blocks(event_type, name):
            db, attempt_root, lease = fixture(root / name)
            db_event(db, lease, event_type)
            answer = recover_failed_preentry(db, "coupling_ml", name, "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert answer["status"] == "BLOCKED"
        results.append(check("E_scientific_entry_blocks", lambda: entry_blocks("SCIENTIFIC_SOLVER_ENTERED", "E")))
        results.append(check("F_gpu_entry_blocks", lambda: entry_blocks("GPU_ENGINE_ENTRY_CONFIRMED", "F")))

        def truth_blocks():
            db, attempt_root, _ = fixture(root / "G")
            truth = attempt_root / "native" / "truth.h5"
            truth.parent.mkdir()
            truth.write_bytes(b"truth")
            assert recover_failed_preentry(db, "coupling_ml", "G", "attempt_001", attempt_root, probe({"status": "PASS"}))["status"] == "BLOCKED"
        results.append(check("G_native_truth_blocks", truth_blocks))

        def pending_blocks():
            db, attempt_root, lease = fixture(root / "H")
            db_event(db, lease, "NATIVE_TRUTH_PERSISTING")
            assert recover_failed_preentry(db, "coupling_ml", "H", "attempt_001", attempt_root, probe({"status": "PASS"}))["status"] == "BLOCKED"
        results.append(check("H_persistence_pending_blocks", pending_blocks))

        def mismatch_blocks():
            db, attempt_root, lease = fixture(root / "I")
            with db.immediate() as con:
                con.execute("UPDATE branch_queue SET fencing_generation=fencing_generation+1 WHERE logical_case_id='I'")
            assert recover_failed_preentry(db, "coupling_ml", "I", "attempt_001", attempt_root, probe({"status": "PASS"}))["status"] == "BLOCKED"
        results.append(check("I_fencing_mismatch_blocks", mismatch_blocks))

        def foreign_slot_blocks():
            db, attempt_root, lease = fixture(root / "J")
            with db.immediate() as con:
                con.execute("UPDATE slots SET owner_branch='foreign',logical_case_id='FOREIGN',attempt_id='attempt_999' WHERE slot_id=?", (lease.slot_id,))
            assert recover_failed_preentry(db, "coupling_ml", "J", "attempt_001", attempt_root, probe({"status": "PASS"}))["status"] == "BLOCKED"
        results.append(check("J_foreign_slot_blocks", foreign_slot_blocks))

        def newer_blocks():
            db, attempt_root, _ = fixture(root / "K")
            enqueue(db, "coupling_ml", "K", "attempt_002")
            assert recover_failed_preentry(db, "coupling_ml", "K", "attempt_001", attempt_root, probe({"status": "PASS"}))["status"] == "BLOCKED"
        results.append(check("K_newer_attempt_blocks", newer_blocks))

        results.append(check("L_pid_reuse_ambiguity_blocks", lambda: blocked_probe({"status": "AMBIGUOUS", "reason": "PID_REUSED"}, "L")))

        def revalidation_process_change_blocks():
            db, attempt_root, _ = fixture(root / "M")
            answer = recover_failed_preentry(db, "coupling_ml", "M", "attempt_001", attempt_root, probe({"status": "PASS"}, {"status": "BLOCKED", "reason": "PROCESS_APPEARED"}))
            assert answer["status"] == "BLOCKED" and state(db, "M")["queue"]["state"] == "HOST_STARTED"
        results.append(check("M_process_appears_before_final_revalidation_blocks", revalidation_process_change_blocks))

        def hold_blocks_successor():
            db, attempt_root, _ = fixture(root / "N")
            answer = recover_failed_preentry(db, "coupling_ml", "N", "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert answer["status"] == "RECOVERED_FAILED_PREENTRY"
            enqueue(db, "coupling_ml", "N2", "attempt_001")
            launched = []
            dispatch_once(db, "coupling_ml", lambda row, lease: launched.append(row["logical_case_id"]))
            assert launched == []
        results.append(check("N_hold_prevents_waiting_successor_launch", hold_blocks_successor))

        def release_failure_is_recoverable():
            db, attempt_root, _ = fixture(root / "O")
            original = Allocator.release_owned_idempotent
            Allocator.release_owned_idempotent = lambda self, lease, **kwargs: {"status": "RELEASE_FAILED"}
            try:
                first = recover_failed_preentry(db, "coupling_ml", "O", "attempt_001", attempt_root, probe({"status": "PASS"}))
            finally:
                Allocator.release_owned_idempotent = original
            assert first["status"] == "RECOVERY_PENDING_RELEASE"
            assert state(db, "O")["queue"]["state"] == "FAILED_PREENTRY"
            second = recover_failed_preentry(db, "coupling_ml", "O", "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert second["status"] == "RECOVERED_FAILED_PREENTRY" and state(db, "O")["released"] == 1
        results.append(check("O_release_failure_leaves_terminal_retryable_state", release_failure_is_recoverable))

        def hold_required():
            db, attempt_root, _ = fixture(root / "P")
            db.set_admission_control(new_entry_hold=False)
            answer = recover_failed_preentry(db, "coupling_ml", "P", "attempt_001", attempt_root, probe({"status": "PASS"}))
            assert answer["status"] == "BLOCKED"
        results.append(check("P_recovery_requires_hold", hold_required))

    failed = [row for row in results if row[1] != "PASS"]
    print(json.dumps({"count": len(results), "pass": len(results) - len(failed), "fail": len(failed), "results": results}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
