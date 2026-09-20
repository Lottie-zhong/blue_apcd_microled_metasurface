from __future__ import annotations
import hashlib, json, os, subprocess, sys
from pathlib import Path
from shared_fdtd.control_v3.allocator import Allocator, BranchCapReached, NoFreeSlot
from shared_fdtd.control_v3.db import utc_now

def enqueue(db,branch,case,attempt,payload=None):
    with db.immediate() as con:
        now=utc_now(); con.execute("INSERT OR IGNORE INTO branch_queue(branch_id,logical_case_id,attempt_id,state,payload_json,created_at,updated_at) VALUES(?,?,?,'QUEUED',?,?,?)",(branch,case,attempt,json.dumps(payload or {}),now,now))

def dispatch_once(db,branch,launch):
    allocator=Allocator(db); launched=[]
    with db.connect(readonly=True) as con:
        rows=[dict(r) for r in con.execute("SELECT * FROM branch_queue WHERE branch_id=? AND state='QUEUED' ORDER BY queue_id",(branch,))]
    for row in rows:
        try: lease=allocator.acquire(branch,row["logical_case_id"],row["attempt_id"])
        except (BranchCapReached,NoFreeSlot): break
        with db.immediate() as con:
            changed=con.execute("UPDATE branch_queue SET state='HOST_START_INTENT',slot_id=?,lease_token_hash=?,fencing_generation=?,updated_at=? WHERE queue_id=? AND state='QUEUED'",(lease.slot_id,lease.token_hash,lease.fencing_generation,utc_now(),row["queue_id"])).rowcount
        if changed!=1:
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY"); continue
        try:
            launch(row,lease)
            with db.immediate() as con: con.execute("UPDATE branch_queue SET state='HOST_STARTED',updated_at=? WHERE queue_id=?",(utc_now(),row["queue_id"]))
            launched.append(row["logical_case_id"])
        except Exception:
            with db.immediate() as con: con.execute("UPDATE branch_queue SET state='FAILED_PREENTRY',updated_at=? WHERE queue_id=?",(utc_now(),row["queue_id"]))
            allocator.release_owned(lease,scientific_terminal="FAILED_PREENTRY")
    return launched

def task_scheduler_launch(task_name,python_exe,host_script,args):
    command='"{}" "{}" {}'.format(python_exe,host_script," ".join('"'+str(x).replace('"','')+'"' for x in args))
    create=subprocess.run(["schtasks.exe","/Create","/TN",task_name,"/TR",command,"/SC","ONCE","/SD","2099/01/01","/ST","00:00","/F"],capture_output=True,text=True)
    if create.returncode: raise RuntimeError(create.stderr or create.stdout)
    run=subprocess.run(["schtasks.exe","/Run","/TN",task_name],capture_output=True,text=True)
    if run.returncode: raise RuntimeError(run.stderr or run.stdout)
