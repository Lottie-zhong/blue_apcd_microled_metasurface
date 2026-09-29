from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from shared_fdtd.control_v3 import Allocator, ControlDB
from shared_fdtd.engine.dispatcher import enqueue, reconcile_dead_preentry_host
from shared_fdtd.engine.event_log import append_event, read_events

SCHEMA = ROOT / "scripts" / "shared_fdtd" / "control_v3" / "schema.sql"


def make_db(root: Path):
    db = ControlDB(root / "control.sqlite3")
    db.initialize(SCHEMA)
    db.set_admission_control(new_entry_hold=True, temporary_runtime_cap=1)
    return db


def state(db, case):
    with db.connect(readonly=True) as con:
        queue = con.execute(
            "SELECT state,slot_id,lease_token_hash,fencing_generation FROM branch_queue WHERE logical_case_id=?",
            (case,),
        ).fetchone()
        slot = con.execute(
            "SELECT state,owner_branch,logical_case_id,attempt_id FROM slots WHERE slot_id=?",
            (queue["slot_id"],),
        ).fetchone() if queue and queue["slot_id"] else None
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE logical_case_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            (case,),
        ).fetchone()[0]
    return {"queue": dict(queue) if queue else None, "slot": dict(slot) if slot else None, "entries": entries}


def main():
    with tempfile.TemporaryDirectory(prefix="preentry_host_liveness_zero_solver_") as raw:
        root = Path(raw)
        db = make_db(root)
        db.set_admission_control(new_entry_hold=False)
        case = "K6V1_TEST_DEAD_HOST"
        attempt_root = root / "outputs" / case / "attempt_001"
        runtime_root = root / "runtime" / case / "attempt_001"
        attempt_root.mkdir(parents=True)
        runtime_root.mkdir(parents=True)
        pre = attempt_root / "setup" / "runtime.fsp"
        pre.parent.mkdir()
        pre.write_bytes(b"setup-only")
        enqueue(db, "coupling_ml", case, "attempt_001", {"attempt_root": str(attempt_root)})
        lease = Allocator(db).acquire("coupling_ml", case, "attempt_001")
        with db.immediate() as con:
            con.execute(
                "UPDATE branch_queue SET state='HOST_STARTED',slot_id=?,lease_token_hash=?,fencing_generation=? WHERE logical_case_id=?",
                (lease.slot_id, lease.token_hash, lease.fencing_generation, case),
            )
        db.set_admission_control(new_entry_hold=True)
        append_event(
            runtime_root / "events.jsonl", "HOST_PROCESS_STARTED",
            host_pid=999999, command="python -u v3g2h.py host_config.json",
            cwd=str(ROOT), stdout_path=str(runtime_root / "host_stdout.log"),
            stderr_path=str(runtime_root / "host_stderr.log"),
            launch_timestamp_utc="2026-09-29T00:00:00+00:00",
        )
        result = reconcile_dead_preentry_host(
            db, "coupling_ml", case, "attempt_001", attempt_root,
            runtime_root=runtime_root, process_probe=lambda _root, _events: {"status": "PASS", "processes": []},
        )
        assert result["status"] == "RECOVERED_DEAD_PREENTRY_HOST"
        current = state(db, case)
        assert current["queue"]["state"] == "FAILED_PREENTRY"
        assert current["queue"]["slot_id"] is None
        assert current["slot"] is None
        assert current["entries"] == 0
        evidence = json.loads((attempt_root / "preentry_host_exit.json").read_text(encoding="utf-8"))
        assert evidence["classification"] == "PRE_ENTRY_HOST_LAUNCH_FAILURE"
        assert evidence["scientific_solver_entry_count"] == 0
        assert evidence["retry_eligibility"] == "PENDING_ZERO_SOLVER_VALIDATION"
        terminal = json.loads((attempt_root / "terminal_failure.json").read_text(encoding="utf-8"))
        assert terminal["solver_entered"] is False and terminal["rerun"] is False
        assert any(e["event_type"] == "PRE_ENTRY_HOST_EXIT" for e in read_events(runtime_root / "events.jsonl"))
        print(json.dumps({
            "status": "PASS",
            "solver_runs": 0,
            "scientific_solver_entries": 0,
            "queue_state": current["queue"]["state"],
            "owner_released": current["slot"] is None,
            "classification": evidence["classification"],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
