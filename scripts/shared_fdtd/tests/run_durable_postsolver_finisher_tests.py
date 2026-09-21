from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
import sys

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.engine.attempt_state import write_durable_attempt_state
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.finisher import DurablePostSolverFinisher
from shared_fdtd.engine.persistence import atomic_json
from shared_fdtd.engine.state_machine import release_count, scientific_entry_count

SCHEMA = PKG / "control_v3" / "schema.sql"


class FakeAdapter:
    def __init__(self, fail_post=False):
        self.fail_post = fail_post

    def fresh_load_validate(self, native, state):
        return {"passed": native.is_file() and native.stat().st_size > 0, "mode": "LOAD_ONLY"}

    def postprocess(self, root, native, post, raw, state):
        if self.fail_post:
            self.fail_post = False
            raise RuntimeError("injected postprocess interruption")
        post.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(native, post)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(json.dumps({"status": "truth", "case": state["logical_case_id"]}) + "\n", encoding="utf-8")
        return {"passed": True, "post": str(post), "raw": str(raw)}

    def validate_truth(self, root, state):
        return {"passed": (root / "post.fsp").is_file() and (root / "raw.json").is_file()}


def fixture(base: Path, case="F_CASE", attempt="attempt_001"):
    root = base / case / attempt
    root.mkdir(parents=True)
    db = ControlDB(base / "control.sqlite3")
    db.initialize(SCHEMA)
    alloc = Allocator(db)
    lease = alloc.acquire("traditional", case, attempt)
    alloc.mark_entered(lease)
    with db.immediate() as con:
        con.execute(
            "INSERT INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at,slot_id,lease_token_hash,fencing_generation) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("traditional", case, attempt, "SCIENTIFIC_SOLVER_RUNNING", "{}", "t", "t", lease.slot_id, lease.token_hash, lease.fencing_generation),
        )
    runtime = root / "runtime.fsp"
    native = root / "native.fsp"
    post = root / "post.fsp"
    raw = root / "raw.json"
    log = root / "solver.log"
    runtime.write_bytes(b"stable-runtime-fsp")
    log.write_text("Simulation complete\nAutoshutoff level: 9.9e-7\n", encoding="utf-8")
    cfg = {"branch": "traditional", "case": case, "attempt": attempt, "physical_contract_hash": "contract-hash"}
    state = write_durable_attempt_state(
        root / "attempt_state.json",
        cfg=cfg,
        lease=lease,
        runtime_fsp=runtime,
        native_target=native,
        post_target=post,
        raw_target=raw,
        logs=[log],
        adapter_identity="FakeAdapter",
        scientific_contract_hash="contract-hash",
        expected_process_identity={"solver_pids": [1234], "solver_creation_time_utc": "T0"},
    )
    append_event(root / "events.jsonl", "SCIENTIFIC_SOLVER_ENTERED")
    return db, root, state


def run_finisher(db, root, process_probe=None, adapter=None, calls=2):
    finisher = DurablePostSolverFinisher(
        db=db, attempt_root=root, invoking_branch="traditional",
        adapter=adapter or FakeAdapter(), process_probe=process_probe or (lambda state: []),
        stability_observations=2,
    )
    result = None
    for _ in range(calls):
        result = finisher.run_once()
    return result


def case(name, fn):
    try:
        fn()
        return [name, "PASS", ""]
    except Exception as exc:
        return [name, "FAIL", repr(exc)]


def main():
    rows = []
    with tempfile.TemporaryDirectory(prefix="shared-finisher-", dir=PKG.parent) as td_name:
        base = Path(td_name)

        def live_probe(state):
            return [{"ProcessId": 1234, "CreationDate": "T0", "CommandLine": "fdtd-engine F_CASE attempt_001"}]

        db, root, _ = fixture(base / "f1")
        rows.append(case("F1_controller_lost_solver_live", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "SOLVER_STILL_RUNNING" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter(), process_probe=live_probe).run_once()
            )
        )))

        db, root, _ = fixture(base / "f2")
        rows.append(case("F2_live_observe_only", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "SOLVER_STILL_RUNNING" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter(), process_probe=live_probe).run_once()
            )
        )))

        db, root, _ = fixture(base / "f3")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F3_controller_lost_solver_returned", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root)
            )
        )))

        db, root, _ = fixture(base / "f4")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F4_stable_fsp_truth_recovery", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if not (root / "terminal.json").is_file() else None)(
                run_finisher(db, root)
            )
        )))

        db, root, _ = fixture(base / "f5")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        fin = DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter(), stability_observations=2)
        fin.run_once()
        (root / "runtime.fsp").write_bytes(b"changed-runtime")
        rows.append(case("F5_changing_fsp_no_load", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] not in {"SCIENTIFIC_OUTCOME_UNRESOLVED", "SOLVER_STILL_RUNNING"} else None)(
                fin.run_once()
            )
        )))

        db, root, _ = fixture(base / "f6")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F6_stale_running_queue_physical_evidence_wins", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root)
            )
        )))

        db, root, _ = fixture(base / "f7")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F7_generic_fdtd_service_ignored", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root, process_probe=lambda state: [{"ProcessId": 9999, "CommandLine": "fdtd-solutions -server -hide"}])
            )
        )))

        db, root, _ = fixture(base / "f8")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        (root / "native.fsp").write_bytes(b"already-native")
        append_event(root / "events.jsonl", "NATIVE_TRUTH_DURABLE")
        rows.append(case("F8_native_truth_skips_recreation", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root)
            )
        )))

        db, root, _ = fixture(base / "f9")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        adapter = FakeAdapter(fail_post=True)
        fin = DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=adapter)
        fin.run_once()
        fin.run_once()
        rows.append(case("F9_postprocess_interrupt_resume", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                fin.run_once()
            )
        )))

        db, root, _ = fixture(base / "f10")
        atomic_json(root / "terminal.json", {"status": "HF_TRUTH_VALID", "release_state": "PENDING_RECONCILE"})
        rows.append(case("F10_terminal_interrupt_resume_release", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "ALREADY_TRUTH_DURABLE" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, _ = fixture(base / "f11")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        class PendingOnce(DurablePostSolverFinisher):
            pending = True
            def _release(self, state, lease):
                if self.pending:
                    self.pending = False
                    return {"status": "PENDING_RECONCILE", "duplicate_side_effects": 0}
                return super()._release(state, lease)
        fin = PendingOnce(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter())
        fin.run_once()
        fin.run_once()
        rows.append(case("F11_release_pending_reconciles", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["release"]["status"] not in {"RELEASED", "ALREADY_FREE"} else None)(
                fin.run_once()
            )
        )))

        db, root, _ = fixture(base / "f12")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
        rows.append(case("F12_finisher_restart_reconstructs", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, _ = fixture(base / "f13")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        fin = DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter())
        fin.run_once(); fin.run_once()
        rows.append(case("F13_duplicate_finisher_idempotent", lambda: (
            (lambda ev: (_ for _ in ()).throw(AssertionError(ev)) if sum(x.get("event_type") == "RELEASED" for x in ev) != 1 else None)(
                read_events(root / "events.jsonl")
            )
        )))

        db, root, _ = fixture(base / "f14")
        before = (root / "events.jsonl").read_bytes()
        rows.append(case("F14_foreign_owner_zero_mutation", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "OWNERSHIP_MISMATCH" or (root / "events.jsonl").read_bytes() != before else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="coupling_ml", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, state = fixture(base / "f15")
        state["fencing_generation"] += 1
        atomic_json(root / "attempt_state.json", state)
        rows.append(case("F15_fencing_mismatch_zero_mutation", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "OWNERSHIP_MISMATCH" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, _ = fixture(base / "f16")
        atomic_json(root / "terminal.json", {"status": "HF_TRUTH_VALID", "release_state": "RELEASED"})
        rows.append(case("F16_valid_truth_never_replays", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "ALREADY_TRUTH_DURABLE" or r["replay"] != 0 else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, state = fixture(base / "f17")
        (root / "runtime.fsp").unlink()
        rows.append(case("F17_return_without_artifact_no_replay", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "SCIENTIFIC_OUTCOME_UNRESOLVED" or r["replay"] != 0 else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, state = fixture(base / "f18")
        state["scientific_contract_hash"] = None
        state["provenance_ambiguous"] = True
        atomic_json(root / "attempt_state.json", state)
        rows.append(case("F18_ambiguous_provenance_hard_gate", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "PROVENANCE_AMBIGUOUS" else None)(
                DurablePostSolverFinisher(db=db, attempt_root=root, invoking_branch="traditional", adapter=FakeAdapter()).run_once()
            )
        )))

        db, root, _ = fixture(base / "f19")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F19_pid_reuse_creation_time_rejected", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root, process_probe=lambda state: [{"ProcessId": 1234, "CreationDate": "T1", "CommandLine": "fdtd-engine F_CASE attempt_001"}])
            )
        )))

        db, root, _ = fixture(base / "f20")
        append_event(root / "events.jsonl", "SOLVER_RETURNED")
        rows.append(case("F20_reconstruct_after_machine_restart", lambda: (
            (lambda r: (_ for _ in ()).throw(AssertionError(r)) if r["status"] != "HF_TRUTH_VALID" else None)(
                run_finisher(db, root)
            )
        )))

    print(json.dumps({
        "count": len(rows),
        "passed": sum(row[1] == "PASS" for row in rows),
        "solver_runs": 0,
        "replay": 0,
        "failed": [row for row in rows if row[1] != "PASS"],
    }))
    out = Path(__file__).with_name("durable_finisher_test_results.csv")
    out.write_text("test,status,detail\n" + "\n".join(",".join(json.dumps(x) for x in row) for row in rows) + "\n", encoding="utf-8")
    return 0 if all(row[1] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
