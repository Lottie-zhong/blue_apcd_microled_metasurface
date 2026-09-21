from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path
from shared_fdtd.control_v3.allocator import Allocator, BranchCapReached, NoFreeSlot
from shared_fdtd.control_v3.db import utc_now
from shared_fdtd.control_v3.resources import ResourceCapacityWait, ResourceRequest, read_resource_snapshot

def enqueue(db,branch,case,attempt,payload=None):
    with db.immediate() as con:
        now=utc_now(); con.execute("INSERT OR IGNORE INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,'QUEUED',?,?,?)",(branch,case,attempt,json.dumps(payload or {}),now,now))

def dispatch_once(db,branch,launch):
    allocator=Allocator(db); launched=[]
    with db.connect(readonly=True) as con:
        rows=[dict(r) for r in con.execute("SELECT * FROM branch_queue WHERE branch_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY') ORDER BY queue_id",(branch,))]
    for row in rows:
        payload=json.loads(row["payload_json"] or "{}")
        request=ResourceRequest.from_payload(payload)
        try:
            lease=allocator.acquire(branch,row["logical_case_id"],row["attempt_id"],resource_request=request,resource_snapshot=read_resource_snapshot() if request is not None else None)
        except ResourceCapacityWait:
            with db.immediate() as con:
                con.execute("UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',updated_at=? WHERE queue_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')",(utc_now(),row["queue_id"]))
            continue
        except (BranchCapReached,NoFreeSlot): break
        with db.immediate() as con:
            changed=con.execute("UPDATE branch_queue SET state='HOST_START_INTENT',slot_id=?,lease_token_hash=?,fencing_generation=?,updated_at=? WHERE queue_id=? AND state IN ('QUEUED','WAIT_RESOURCE_CAPACITY')",(lease.slot_id,lease.token_hash,lease.fencing_generation,utc_now(),row["queue_id"])).rowcount
        if changed!=1:
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY"); continue
        try:
            launch_result = launch(row,lease)
            next_state = "HOST_STARTED"
            if isinstance(launch_result, dict):
                next_state = str(launch_result.get("queue_state") or next_state)
            with db.immediate() as con:
                if next_state == "WAIT_RESOURCE_CAPACITY":
                    con.execute(
                        "UPDATE branch_queue SET state=?,slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE queue_id=?",
                        (next_state, utc_now(), row["queue_id"]),
                    )
                else:
                    con.execute(
                        "UPDATE branch_queue SET state=?,updated_at=? WHERE queue_id=?",
                        (next_state, utc_now(), row["queue_id"]),
                    )
            if next_state == "HOST_STARTED":
                launched.append(row["logical_case_id"])
        except Exception:
            with db.immediate() as con: con.execute("UPDATE branch_queue SET state='FAILED_PREENTRY',updated_at=? WHERE queue_id=?",(utc_now(),row["queue_id"]))
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY")
    return launched

def recover_failed_preentry(db, branch, case, attempt, attempt_root=None):
    from shared_fdtd.engine.event_log import append_event
    with db.immediate() as con:
        row = con.execute(
            "SELECT state FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()
        if row is None:
            return {"status": "NOT_FOUND", "case": case, "attempt": attempt}
        eligible_states = {
            "FAILED_PREENTRY",
            "AMBIGUOUS_QUARANTINED",
            "HOST_START_INTENT",
            "SOLVER_ENTRY_INTENT",
        }
        if row["state"] not in eligible_states:
            return {"status": "NOT_ELIGIBLE", "state": row["state"], "case": case, "attempt": attempt}
        if row["state"] in {"AMBIGUOUS_QUARANTINED", "HOST_START_INTENT", "SOLVER_ENTRY_INTENT"}:
            if not attempt_root:
                raise RuntimeError("ZERO_SOLVER_RECOVERY_REQUIRES_ATTEMPT_ROOT")
            ledger_path = Path(attempt_root) / "attempt_ledger.json"
            if not ledger_path.is_file():
                raise RuntimeError("ZERO_SOLVER_RECOVERY_MISSING_LEDGER")
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            if ledger.get("solver_entered") is not False or int(ledger.get("run_invocation_count", -1)) != 0:
                raise RuntimeError("ZERO_SOLVER_RECOVERY_LEDGER_NOT_ZERO")
        entries = con.execute(
            "SELECT COUNT(*) FROM lease_events WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND event_type='SCIENTIFIC_SOLVER_ENTERED'",
            (branch, case, attempt),
        ).fetchone()[0]
        copies = con.execute(
            "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id=?",
            (branch, case, attempt),
        ).fetchone()[0]
        active_other = con.execute(
            "SELECT COUNT(*) FROM branch_queue WHERE branch_id=? AND logical_case_id=? AND attempt_id<>? AND state NOT IN ('RELEASED','FAILED_PREENTRY','FAILED_AFTER_ENTRY','POSTENTRY_NO_TRUTH','TERMINAL_QUARANTINED','AMBIGUOUS_QUARANTINED')",
            (branch, case, attempt),
        ).fetchone()[0]
        if entries != 0:
            raise RuntimeError("PREENTRY_RECOVERY_BLOCKED_AFTER_SCIENTIFIC_ENTRY")
        if copies != 1 or active_other != 0:
            raise RuntimeError("PREENTRY_RECOVERY_BLOCKED_CASE_DUPLICATION")
        con.execute(
            "UPDATE branch_queue SET state='WAIT_RESOURCE_CAPACITY',slot_id=NULL,lease_token_hash=NULL,fencing_generation=NULL,updated_at=? WHERE branch_id=? AND logical_case_id=? AND attempt_id=? AND state IN ('FAILED_PREENTRY','AMBIGUOUS_QUARANTINED','HOST_START_INTENT','SOLVER_ENTRY_INTENT')",
            (utc_now(), branch, case, attempt),
        )
    if attempt_root:
        append_event(
            Path(attempt_root) / "events.jsonl",
            "PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY",
            branch_id=branch, case_id=case, attempt_id=attempt,
            scientific_solver_entry_count=0, replay=0,
        )
    return {"status": "RECOVERED_WAIT_RESOURCE_CAPACITY", "case": case, "attempt": attempt, "scientific_solver_entry_count": 0, "replay": 0}

def task_scheduler_launch(task_name,python_exe,host_script,args):
    command='"{}" "{}" {}'.format(python_exe,host_script," ".join('"'+str(x).replace('"','')+'"' for x in args))
    create=subprocess.run(["schtasks.exe","/Create","/TN",task_name,"/TR",command,"/SC","ONCE","/SD","2099/01/01","/ST","00:00","/F"],capture_output=True,text=True)
    if create.returncode: raise RuntimeError(create.stderr or create.stdout)
    run=subprocess.run(["schtasks.exe","/Run","/TN",task_name],capture_output=True,text=True)
    if run.returncode: raise RuntimeError(run.stderr or run.stdout)
