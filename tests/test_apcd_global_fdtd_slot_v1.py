import importlib.util
import json
import os
from pathlib import Path
import pytest

SPEC=importlib.util.spec_from_file_location("slot",Path(__file__).resolve().parents[1]/"scripts/apcd_global_fdtd_slot_v1.py")
MOD=importlib.util.module_from_spec(SPEC); assert SPEC and SPEC.loader; SPEC.loader.exec_module(MOD)


def test_policy_and_acquisition_are_distinct_from_entry(tmp_path):
    scheduler=MOD.GlobalSlotScheduler(tmp_path/"registry.json",lambda:[])
    lease=scheduler.acquire("work/lp-global-h-manifold-v1",r"D:\lp", "task", "case", pid=os.getpid(), metadata={"attempt_id":"a1","polarization":"x","H_global_nm":400.0})
    try:
        assert MOD.GLOBAL_CAPACITY==2
        assert MOD.MAX_ACTIVE_FDTD_PER_BRANCH==1
        assert MOD.PROCESSES_PER_JOB==4
        assert MOD.THREADS_PER_JOB==1
        assert lease.record["slot_acquired"] is True
        assert lease.record["entered"] is False
        assert lease.record["entered_solver"] is False
        assert lease.record["processes"]==4 and lease.record["threads"]==1
        assert lease.record["attempt_id"]=="a1"
    finally:
        lease.release("PRE_ENTRY_RELEASE")


def test_one_peer_is_allowed_but_capacity_two_waits(tmp_path):
    peer=[{"pid":101,"ppid":0,"name":"fdtd-solutions.exe","cmdline":r"D:\np\blue_apcd_np\case.fsp"}]
    scheduler=MOD.GlobalSlotScheduler(tmp_path/"registry.json",lambda:peer)
    lease=scheduler.acquire("work/lp-global-h-manifold-v1",r"D:\lp", "task", "case", pid=os.getpid())
    try:
        assert lease.record["concurrent_peer_branch"]==["NP"]
    finally:
        lease.release("PRE_ENTRY_RELEASE")
    full=[*peer,{"pid":102,"ppid":0,"name":"mpiexec.exe","cmdline":r"D:\mdc\blue_apcd_mdc\case.fsp"}]
    blocked=MOD.GlobalSlotScheduler(tmp_path/"full.json",lambda:full)
    with pytest.raises(MOD.SlotUnavailable,match="WAIT_GLOBAL_FDTD_CAPACITY"):
        blocked.acquire("work/lp-global-h-manifold-v1",r"D:\lp", "task", "case", pid=os.getpid())


def test_entered_marker_is_persisted_and_stale_entered_is_hard_gate(tmp_path):
    path=tmp_path/"registry.json"
    scheduler=MOD.GlobalSlotScheduler(path,lambda:[])
    lease=scheduler.acquire("work/lp-global-h-manifold-v1",r"D:\lp", "task", "case", pid=os.getpid())
    lease.mark_solver_entered("2026-01-01T00:00:00+00:00")
    data=json.loads(path.read_text(encoding="utf-8"))
    assert data["active_slots"][0]["entered"] is True
    assert data["active_slots"][0]["entered_solver"] is True
    lease.release("SOLVER_COMPLETED")
    stale={**MOD.default_registry(),"active_slots":[{"slot_id":"GLOBAL_SLOT_1","controller_pid":999999999,"case_uid":"case","entered":True,"entered_solver":True}]}
    path.write_text(json.dumps(stale),encoding="utf-8")
    with pytest.raises(MOD.StaleEnteredSlot):
        MOD.GlobalSlotScheduler(path,lambda:[]).acquire("NP",r"D:\np","task","other",pid=os.getpid())


def test_preentry_stale_slot_is_recovered(tmp_path):
    path=tmp_path/"registry.json"
    data={**MOD.default_registry(),"active_slots":[{"slot_id":"GLOBAL_SLOT_1","controller_pid":999999999,"case_uid":"case","entered":False,"entered_solver":False}]}
    path.write_text(json.dumps(data),encoding="utf-8")
    lease=MOD.GlobalSlotScheduler(path,lambda:[]).acquire("NP",r"D:\np","task","other",pid=os.getpid())
    try:
        registry=json.loads(path.read_text(encoding="utf-8"))
        assert registry["active_slots"][0]["slot_id"]=="GLOBAL_SLOT_1"
        assert any(row["completion_release_state"]=="STALE_RECOVERED_PRE_ENTRY" for row in registry["history"])
    finally:
        lease.release("PRE_ENTRY_RELEASE")


def test_controller_without_fsp_is_grouped_with_single_child_fsp_job():
    rows=[
        {"pid":10,"ppid":1,"name":"fdtd-solutions.exe","cmdline":"fdtd-solutions -server"},
        {"pid":20,"ppid":10,"name":"mpiexec.exe","cmdline":r"mpiexec -n 4 D:\project\blue_apcd_np\case_run.fsp"},
        {"pid":21,"ppid":20,"name":"fdtd-engine-msmpi.exe","cmdline":r"fdtd-engine-msmpi D:\project\blue_apcd_np\case_run.fsp"},
    ]
    snap=MOD.live_job_snapshot(lambda: rows)
    assert snap["global_active_jobs"]==1
    assert snap["jobs"][0]["branch"]=="NP"
    assert len(snap["jobs"][0]["processes"])==3


def test_pid_exists_treats_windows_invalid_pid_system_error_as_not_alive(monkeypatch):
    def broken_kill(*args):
        raise SystemError("WinError 87")
    monkeypatch.setattr(MOD.os, "kill", broken_kill)
    assert MOD.pid_exists(999999999) is False


def test_live_entered_peer_slot_is_kept_when_owner_pid_is_not_visible(tmp_path):
    path=tmp_path/"registry.json"
    peer=[{"pid":101,"ppid":0,"name":"fdtd-solutions.exe","cmdline":r"D:\np\blue_apcd_np\case.fsp"}]
    data={**MOD.default_registry(),"active_slots":[{"slot_id":"GLOBAL_SLOT_1","controller_pid":999999999,"pid":999999999,"branch":"NP","case_uid":"NP_CASE","entered":True,"entered_solver":True}]}
    path.write_text(json.dumps(data),encoding="utf-8")
    scheduler=MOD.GlobalSlotScheduler(path,lambda:peer)
    lease=scheduler.acquire("work/lp-global-h-manifold-v1",r"D:\lp","task","case",pid=os.getpid())
    try:
        assert lease.record["concurrent_peer_branch"] == ["NP"]
        assert lease.record["admission_snapshot"]["effective_global_active_jobs_before_acquire"] == 1
    finally:
        lease.release("PRE_ENTRY_RELEASE")


def test_rcwa_is_not_an_fdtd_slot(tmp_path):
    rows=[
        {"pid":101,"ppid":0,"name":"fdtd-solutions.exe","cmdline":r"D:\np\blue_apcd_np\case.fsp"},
        {"pid":102,"ppid":0,"name":"rcwa-solver.exe","cmdline":r"D:\rcwa\run.rcwa"},
    ]
    snap=MOD.live_job_snapshot(lambda: rows)
    assert snap["global_active_jobs"]==1
    lease=MOD.GlobalSlotScheduler(tmp_path/"registry.json",lambda:rows).acquire("work/lp-global-h-manifold-v1",r"D:\lp","task","case",pid=os.getpid())
    lease.release("PRE_ENTRY_RELEASE")


def test_rcwa_parent_controller_is_not_an_fdtd_slot():
    rows=[
        {"pid":301,"ppid":401,"name":"fdtd-solutions.exe","cmdline":r"fdtd-solutions -server -hide"},
        {"pid":401,"ppid":0,"name":"python.exe","cmdline":r"python scripts/coupling/rcwa_p33_oblique_anchor.py --attempt-id attempt_002"},
    ]
    snap=MOD.live_job_snapshot(lambda: rows)
    assert snap["global_active_jobs"]==0
    assert snap["formal_process_count"]==0


def test_two_branches_racing_last_slot_only_one_succeeds(tmp_path):
    import threading
    peer=[{"pid":101,"ppid":0,"name":"fdtd-solutions.exe","cmdline":r"D:\np\blue_apcd_np\case.fsp"}]
    path=tmp_path/"registry.json"
    results=[]
    leases=[]
    lock=threading.Lock()
    release_event=threading.Event()
    def attempt(branch):
        try:
            lease=MOD.GlobalSlotScheduler(path,lambda:peer).acquire(branch,r"D:\branch","task",branch,pid=os.getpid())
            with lock:
                results.append((branch,"ok")); leases.append(lease)
            release_event.wait(timeout=5)
        except MOD.SlotUnavailable as exc:
            with lock:
                results.append((branch,str(exc)))
    threads=[threading.Thread(target=attempt,args=(f"branch-{i}",)) for i in (1,2)]
    for t in threads: t.start()
    for _ in range(50):
        with lock:
            if len(results)==2: break
        release_event.wait(timeout=0.01)
    release_event.set()
    for t in threads: t.join(timeout=5)
    for lease in leases: lease.release("PRE_ENTRY_RELEASE")
    assert sum(value=="ok" for _,value in results)==1
    assert sum(value!="ok" for _,value in results)==1


def test_policy_has_no_thirteen_process_row():
    assert MOD.PROCESSES_PER_JOB==4
    assert MOD.PROCESSES_PER_JOB != 13


def test_completed_entered_stale_slot_is_recovered_with_explicit_evidence(tmp_path):
    path=tmp_path/"registry.json"
    data={**MOD.default_registry(),"active_slots":[{
        "slot_id":"GLOBAL_SLOT_1", "controller_pid":999999999, "pid":999999999,
        "branch":"NP", "case_uid":"NP_CASE", "entered":True, "entered_solver":True,
        "completion_evidence":{"solver_completed":True,"owner_processes_absent":True}
    }]}
    path.write_text(json.dumps(data),encoding="utf-8")
    lease=MOD.GlobalSlotScheduler(path,lambda:[]).acquire("work/lp-global-h-manifold-v1",r"D:\lp","task","case",pid=os.getpid())
    try:
        registry=json.loads(path.read_text(encoding="utf-8"))
        assert any(row["completion_release_state"]=="STALE_RECOVERED_COMPLETED" for row in registry["history"])
    finally:
        lease.release("PRE_ENTRY_RELEASE")
