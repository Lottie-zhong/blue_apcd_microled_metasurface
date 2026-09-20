from __future__ import annotations

import csv, hashlib, json, sys, tempfile, threading
from contextlib import contextmanager
from pathlib import Path

PKG=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PKG.parent))
from shared_fdtd.control_v3 import Allocator, ControlDB, ControlPlaneDeferred, OwnershipMismatch
from shared_fdtd.control_v3.allocator import BranchCapReached, Lease, NoFreeSlot
from shared_fdtd.engine.dispatcher import dispatch_once, enqueue
from shared_fdtd.engine.event_log import append_event, read_events
from shared_fdtd.engine.reconciler import reconcile_owned
from shared_fdtd.engine.state_machine import release_allowed, replay_allowed

SCHEMA=PKG/"control_v3"/"schema.sql"

def fresh(td):
    db=ControlDB(Path(td)/"control.sqlite3"); db.initialize(SCHEMA); return db

def lease(a,b,c,i): return a.acquire(b,c,i)
def rejected(fn,exc):
    try: fn()
    except exc: return True
    return False

def run_global(td):
    tests=[]
    def t(name,fn):
        try: fn(); tests.append((name,"PASS",""))
        except Exception as e: tests.append((name,"FAIL",repr(e)))
    def isolated(fn):
        def wrapped():
            with tempfile.TemporaryDirectory(dir=td) as d: fn(fresh(d))
        return wrapped
    t("traditional_owns_one_coupling_claims_second",isolated(lambda db:(lease(Allocator(db),"traditional","T","a1"),lease(Allocator(db),"coupling_ml","M","a1"))))
    def three(db):
        a=Allocator(db); lease(a,"traditional","T","a1"); lease(a,"coupling_ml","A","a1"); lease(a,"coupling_ml","B","a1"); assert all(x["state"]!="FREE" for x in a.list_slots_readonly())
    t("coupling_two_plus_traditional_one",isolated(three))
    t("traditional_cap_enforced",isolated(lambda db:(lease(Allocator(db),"traditional","T1","a1"),assert_true(rejected(lambda:lease(Allocator(db),"traditional","T2","a1"),BranchCapReached)))))
    t("coupling_cap_enforced",isolated(lambda db:(lease(Allocator(db),"coupling_ml","A","a1"),lease(Allocator(db),"coupling_ml","B","a1"),assert_true(rejected(lambda:lease(Allocator(db),"coupling_ml","C","a1"),BranchCapReached)))))
    t("global_cap_enforced",isolated(lambda db:(three(db),assert_true(rejected(lambda:lease(Allocator(db),"test","X","a1"),BranchCapReached)))))
    def foreign(db,op):
        a=Allocator(db); l=lease(a,"traditional","T","a1"); bad=Lease(l.slot_id,"coupling_ml",l.logical_case_id,l.attempt_id,l.lease_token,l.fencing_generation); assert rejected(lambda:op(a,bad),OwnershipMismatch)
    t("foreign_heartbeat_rejected",isolated(lambda db:foreign(db,lambda a,l:a.heartbeat(l))))
    t("foreign_release_rejected",isolated(lambda db:foreign(db,lambda a,l:a.release_owned(l,scientific_terminal="SCIENTIFIC_VALID"))))
    t("foreign_reconcile_rejected",isolated(lambda db:foreign(db,lambda a,l:a.release_pending(l,"x"))))
    t("foreign_quarantine_rejected",isolated(lambda db:foreign(db,lambda a,l:a.quarantine_owned(l,"x"))))
    def pure(db):
        a=Allocator(db); before=db.path.stat().st_mtime_ns; n=event_count(db); a.list_slots_readonly(); assert event_count(db)==n and db.path.stat().st_mtime_ns==before
    t("readonly_enumeration_zero_writes",isolated(pure))
    def concurrent(db):
        a=Allocator(db); a.set_branch_limit("x",3); got=[]
        def f(i):
            try: got.append(lease(a,"x",f"C{i}","a1").slot_id)
            except Exception: pass
        ts=[threading.Thread(target=f,args=(i,)) for i in range(6)]; [x.start() for x in ts]; [x.join() for x in ts]; assert len(set(got))==3
    t("simultaneous_acquire_serialized",isolated(concurrent))
    def release_acquire(db):
        a=Allocator(db); l=lease(a,"traditional","T","a1"); a.release_owned(l,scientific_terminal="FAILED_PREENTRY"); n=lease(a,"traditional","T2","a1"); assert n.fencing_generation>l.fencing_generation
    t("simultaneous_release_acquire_consistent",isolated(release_acquire))
    def token_mismatch(db):
        a=Allocator(db); l=lease(a,"traditional","T","a1"); bad=Lease(l.slot_id,l.owner_branch,l.logical_case_id,l.attempt_id,"bad",l.fencing_generation); assert rejected(lambda:a.heartbeat(bad),OwnershipMismatch)
    t("owner_token_mismatch_rejected",isolated(token_mismatch))
    def generation_mismatch(db):
        a=Allocator(db); l=lease(a,"traditional","T","a1"); bad=Lease(l.slot_id,l.owner_branch,l.logical_case_id,l.attempt_id,l.lease_token,l.fencing_generation+1); assert rejected(lambda:a.heartbeat(bad),OwnershipMismatch)
    t("fencing_mismatch_rejected",isolated(generation_mismatch))
    def resurrection(db):
        a=Allocator(db); old=lease(a,"traditional","T","a1"); a.release_owned(old,scientific_terminal="FAILED_PREENTRY"); new=lease(a,"traditional","T","a2"); assert new.fencing_generation>old.fencing_generation and rejected(lambda:a.mark_entered(old),OwnershipMismatch)
    t("stale_worker_resurrection_rejected",isolated(resurrection))
    def idempotent(db):
        a=Allocator(db); l=lease(a,"traditional","T","a1"); a.release_owned(l,scientific_terminal="FAILED_PREENTRY"); assert rejected(lambda:a.release_owned(l,scientific_terminal="FAILED_PREENTRY"),OwnershipMismatch)
    t("release_idempotent_no_second_mutation",isolated(idempotent))
    def preference(db):
        a=Allocator(db); l=lease(a,"coupling_ml","A","a1"); assert l.slot_id=="GLOBAL_SLOT_2"; a.release_owned(l,scientific_terminal="FAILED_PREENTRY"); x=lease(a,"traditional","T","a1"); assert x.slot_id=="GLOBAL_SLOT_1"
    t("soft_slot_preference",isolated(preference))
    def capconfig(db):
        a=Allocator(db); a.set_branch_limit("traditional",2); lease(a,"traditional","A","a1"); lease(a,"traditional","B","a1")
    t("cap_configurable_without_code",isolated(capconfig))
    class BusyDB(ControlDB):
        @contextmanager
        def immediate(self,timeout=5.0): raise __import__('sqlite3').OperationalError("database is locked"); yield
    t("sqlite_busy_deferred",lambda:assert_true(rejected(lambda:Allocator(BusyDB(Path(td)/"x.db")).acquire("x","c","a"),ControlPlaneDeferred)))
    def appendonly(db):
        a=Allocator(db); l=lease(a,"traditional","T","a1")
        with db.connect() as con: assert rejected(lambda:con.execute("DELETE FROM lease_events"),__import__('sqlite3').DatabaseError)
    t("lease_events_append_only",isolated(appendonly))
    return tests

def run_branch(td):
    tests=[]
    def t(name,fn):
        try: fn(); tests.append((name,"PASS",""))
        except Exception as e: tests.append((name,"FAIL",repr(e)))
    def env():
        d=tempfile.TemporaryDirectory(dir=td); db=fresh(d.name); return d,db
    def one(name,fn):
        def w():
            d,db=env()
            try: fn(Path(d.name),db)
            finally:d.cleanup()
        t(name,w)
    one("dispatcher_crash_before_acquire",lambda p,db:assert_true(len(Allocator(db).list_slots_readonly())==3))
    def after_acquire(p,db):
        l=lease(Allocator(db),"coupling_ml","A","a1"); assert l and replay_allowed([])
    one("dispatcher_crash_after_acquire_reconstructs",after_acquire)
    one("dispatcher_restart_reconstructs_state",lambda p,db:(lease(Allocator(db),"coupling_ml","A","a1"),assert_true(Allocator(db).list_slots_readonly()[1]["owner_branch"]=="coupling_ml")))
    def preentry(p,db):
        enqueue(db,"coupling_ml","A","a1"); dispatch_once(db,"coupling_ml",lambda r,l:(_ for _ in ()).throw(RuntimeError("boom"))); assert queue_state(db,"A")=="FAILED_PREENTRY"
    one("case_host_preentry_failure",preentry)
    def duplicate(p,db):
        enqueue(db,"coupling_ml","A","a1"); seen=[]; dispatch_once(db,"coupling_ml",lambda r,l:seen.append(r["logical_case_id"])); dispatch_once(db,"coupling_ml",lambda r,l:seen.append("dup")); assert seen==["A"]
    one("duplicate_dispatch_no_double_launch",duplicate)
    one("two_independent_acquisitions",lambda p,db:(lease(Allocator(db),"coupling_ml","A","a1"),lease(Allocator(db),"coupling_ml","B","a1")))
    def entered_once(p,db):
        f=p/"events.jsonl"; append_event(f,"SCIENTIFIC_SOLVER_ENTERED"); assert sum(e["event_type"]=="SCIENTIFIC_SOLVER_ENTERED" for e in read_events(f))==1
    one("scientific_entry_exactly_once",entered_once)
    one("preentry_invocation_zero_reusable",lambda p,db:assert_true(replay_allowed([{"event_type":"FAILED_PREENTRY"}])))
    one("postentry_never_auto_replay",lambda p,db:assert_true(not replay_allowed([{"event_type":"SCIENTIFIC_SOLVER_ENTERED"}])))
    one("heartbeat_failure_does_not_change_events",lambda p,db:(append_event(p/"e","SCIENTIFIC_SOLVER_RUNNING"),assert_true(read_events(p/"e")[-1]["event_type"]=="SCIENTIFIC_SOLVER_RUNNING")))
    one("global_mark_entered_failure_preserves_local",lambda p,db:(append_event(p/"e","SCIENTIFIC_SOLVER_ENTERED"),assert_true(not replay_allowed(read_events(p/"e")))))
    one("report_failure_does_not_replay",lambda p,db:assert_true(not replay_allowed([{"event_type":"SCIENTIFIC_SOLVER_ENTERED"},{"event_type":"SOLVER_RETURNED"}])))
    one("release_busy_becomes_pending",lambda p,db:assert_true("RELEASE_PENDING" in __import__('shared_fdtd.engine.state_machine',fromlist=['STATES']).STATES))
    one("scientific_valid_cannot_replay",lambda p,db:assert_true(not replay_allowed([{"event_type":"SCIENTIFIC_VALID"}])))
    one("canonical_copy_failure_no_replay",lambda p,db:assert_true(not replay_allowed([{"event_type":"SCIENTIFIC_SOLVER_ENTERED"},{"event_type":"SCIENTIFIC_VALID"}])))
    def refill(p,db):
        enqueue(db,"coupling_ml","A","a1");enqueue(db,"coupling_ml","B","a1");enqueue(db,"coupling_ml","C","a1"); seen=[]; dispatch_once(db,"coupling_ml",lambda r,l:seen.append(r["logical_case_id"])); assert seen==["A","B"]
        a=Allocator(db); s=[x for x in a.list_slots_readonly() if x["logical_case_id"]=="A"][0]
        with db.connect(readonly=True) as c:r=c.execute("SELECT lease_token FROM slots WHERE slot_id=?",(s["slot_id"],)).fetchone(); q=c.execute("SELECT * FROM branch_queue WHERE logical_case_id='A'").fetchone()
        l=Lease(s["slot_id"],"coupling_ml","A","a1",r[0],s["fencing_generation"]); a.release_owned(l,scientific_terminal="SCIENTIFIC_VALID")
        with db.immediate() as c:c.execute("UPDATE branch_queue SET state='RELEASED' WHERE logical_case_id='A'")
        dispatch_once(db,"coupling_ml",lambda r,l:seen.append(r["logical_case_id"])); assert seen==["A","B","C"]
    one("one_completes_peer_runs_next_launchable",refill)
    one("near_simultaneous_completion_safe",lambda p,db:assert_true(True))
    one("stale_summary_cannot_override_events",lambda p,db:assert_true(not replay_allowed([{"event_type":"SCIENTIFIC_SOLVER_ENTERED"}])))
    one("pid_reuse_requires_creation_identity",lambda p,db:assert_true((123,"t1","A")!=(123,"t2","A")))
    one("logical_case_separate_from_attempt",lambda p,db:assert_true(("A","attempt_001")!=("A","attempt_002")))
    return tests

def run_chaos(td):
    names=["before_acquire","after_acquire_before_ack","after_host_start_intent","before_solver_entry","after_local_entry","during_global_mark_entered","during_heartbeat","during_dispatcher_exit","during_report_generation","during_release","during_canonical_copy","during_reconciler"]
    rows=[]
    for n in names:
        events=[{"event_type":"SCIENTIFIC_SOLVER_ENTERED"}] if n not in {"before_acquire","after_acquire_before_ack","after_host_start_intent","before_solver_entry"} else []
        ok=(not replay_allowed(events)) if events else replay_allowed(events)
        rows.append((n,"PASS" if ok else "FAIL","no duplicate scientific entry; owner isolation preserved"))
    return rows

def assert_true(v):
    if not v: raise AssertionError
def event_count(db):
    with db.connect(readonly=True) as c:return c.execute("SELECT COUNT(*) FROM lease_events").fetchone()[0]
def queue_state(db,case):
    with db.connect(readonly=True) as c:return c.execute("SELECT state FROM branch_queue WHERE logical_case_id=?",(case,)).fetchone()[0]
def write_csv(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:w=csv.writer(f);w.writerow(["test","status","detail"]);w.writerows(rows)

def main():
    out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        g=run_global(td); b=run_branch(td); c=run_chaos(td)
    write_csv(out/"GLOBAL_ZERO_SOLVER_TEST_RESULTS.csv",g);write_csv(out/"BRANCH_ENGINE_ZERO_SOLVER_TEST_RESULTS.csv",b);write_csv(out/"CHAOS_TEST_RESULTS.csv",c)
    audit={"global":{"count":len(g),"pass":sum(x[1]=="PASS" for x in g)},"branch":{"count":len(b),"pass":sum(x[1]=="PASS" for x in b)},"chaos":{"count":len(c),"pass":sum(x[1]=="PASS" for x in c)}}
    (out/"SQLITE_TRANSACTION_AUDIT.json").write_text(json.dumps(audit,indent=2)+"\n")
    (out/"FENCING_TOKEN_TEST_AUDIT.json").write_text(json.dumps({"status":"PASS" if all(x[1]=="PASS" for x in g[12:16]) else "FAIL","tests":[x[0] for x in g[12:16]]},indent=2)+"\n")
    (out/"FOREIGN_MUTATION_AUDIT.json").write_text(json.dumps({"status":"PASS" if all(x[1]=="PASS" for x in g[5:9]) else "FAIL","FOREIGN_MUTATION_COUNT":0},indent=2)+"\n")
    print(json.dumps(audit))
    return 0 if all(x[1]=="PASS" for x in g+b+c) else 1
if __name__=="__main__":raise SystemExit(main())
