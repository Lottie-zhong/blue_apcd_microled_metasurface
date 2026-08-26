from __future__ import annotations
import json, os, re, subprocess, threading, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

POLICY_ID = "APCD_GLOBAL_FDTD_SCHEDULING_POLICY_V3"
CURRENT_PRODUCTION_FDTD_SCHEDULING_CAP = 3
DEFAULT_MAX_ACTIVE_FDTD_PER_BRANCH = 3
GLOBAL_CAPACITY = CURRENT_PRODUCTION_FDTD_SCHEDULING_CAP
MAX_ACTIVE_FDTD_PER_BRANCH = DEFAULT_MAX_ACTIVE_FDTD_PER_BRANCH
PROCESSES_PER_JOB = 4
THREADS_PER_JOB = 1
RCWA_CONSUMES_FDTD_SLOT = False
DEFAULT_REGISTRY_PATH = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
LOCK_TIMEOUT_S = 30.0
LOCK_STALE_S = 120.0
HEARTBEAT_INTERVAL_S = 5.0
FORMAL_NAMES = {"fdtd-solutions.exe", "fdtd-engine-msmpi.exe", "fdtd-engine.exe", "mpiexec.exe"}
FSP_RE = re.compile(r'(?i)([A-Za-z]:[\\/][^\s"<>|]+\.fspx?)')

class SlotError(RuntimeError): pass
class SlotUnavailable(SlotError): pass
class StaleEnteredSlot(SlotError): pass
class RegistryCorrupt(SlotError): pass

def utc_now(): return datetime.now(timezone.utc).isoformat()
def pid_exists(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError, SystemError):
        return False

def _branch_active_limit(branch, metadata):
    # Permanent V3 policy: branch-local admission is bounded by the
    # shared global cap and never by a branch-specific historical trial.
    return DEFAULT_MAX_ACTIVE_FDTD_PER_BRANCH

def default_registry():
    return {"schema":"APCD_GLOBAL_FDTD_SLOT_REGISTRY_V1","policy_id":POLICY_ID,"global_capacity":GLOBAL_CAPACITY,"max_active_fdtd_per_branch":MAX_ACTIVE_FDTD_PER_BRANCH,"active_slots":[],"history":[],"updated_utc":utc_now()}

def _read(path):
    if not path.exists(): return default_registry()
    try: data=json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc: raise RegistryCorrupt(f"cannot read slot registry: {path}") from exc
    trial_cap_ok = data.get("global_capacity") == GLOBAL_CAPACITY and data.get("policy_id") == POLICY_ID
    if data.get("schema") != "APCD_GLOBAL_FDTD_SLOT_REGISTRY_V1" or not trial_cap_ok or data.get("max_active_fdtd_per_branch") != MAX_ACTIVE_FDTD_PER_BRANCH or not isinstance(data.get("active_slots"),list) or not isinstance(data.get("history",[]),list):
        raise RegistryCorrupt("slot registry schema or policy mismatch")
    return data

def _write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
    os.replace(tmp,path)

@contextmanager
def registry_lock(path,timeout_s=LOCK_TIMEOUT_S):
    lock=Path(str(path)+".lock"); start=time.monotonic(); fd=None
    while fd is None:
        try: fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError:
            try: info=json.loads(lock.read_text(encoding="utf-8")); owner=info.get("pid"); age=time.time()-lock.stat().st_mtime
            except FileNotFoundError:
                # Another atomic acquirer released the lock between the
                # existence check and metadata read; retry acquisition.
                continue
            except Exception as exc: raise SlotError("HARD_GATE_SLOT_LOCK_UNKNOWN_OWNERSHIP") from exc
            if not pid_exists(owner) and age >= LOCK_STALE_S:
                try: lock.unlink()
                except FileNotFoundError: pass
                continue
            if time.monotonic()-start >= timeout_s: raise SlotError("GLOBAL_SLOT_LOCK_BUSY")
            time.sleep(.2)
    try:
        os.write(fd,json.dumps({"pid":os.getpid(),"created_utc":utc_now()}).encode()); os.close(fd); fd=None; yield
    finally:
        if fd is not None: os.close(fd)
        try: lock.unlink()
        except FileNotFoundError: pass

def _ps_snapshot():
    script=r'''$ErrorActionPreference='SilentlyContinue'
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(fdtd-solutions|fdtd-engine-msmpi|fdtd-engine|mpiexec|python).exe$' } | ForEach-Object { [pscustomobject]@{pid=[int]$_.ProcessId;ppid=[int]$_.ParentProcessId;name=[string]$_.Name;cmdline=[string]$_.CommandLine;path=[string]$_.ExecutablePath} } | ConvertTo-Json -Compress'''
    result=subprocess.run(["powershell","-NoProfile","-Command",script],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30)
    if not result.stdout.strip(): return []
    try: rows=json.loads(result.stdout)
    except ValueError: return []
    return [rows] if isinstance(rows,dict) else rows

def _token(row,by_pid):
    match=FSP_RE.search(str(row.get("cmdline") or ""))
    if match: return "fsp:"+match.group(1).lower().replace("/","\\")
    if _is_rcwa_runner(row):
        runner_name = next((part.strip(chr(34)).replace(chr(92), "/").split("/")[-1].lower() for part in str(row.get("cmdline") or "").split() if "rcwa" in part.lower() and part.lower().endswith(".py")), "runner.py")
        return "rcwa:blue_apcd_mdc_np_coupling_v1:" + runner_name
    current=row; seen=set()
    while current and int(current.get("pid",-1)) not in seen:
        pid=int(current.get("pid",-1)); seen.add(pid); name=str(current.get("name") or "").lower()
        if name in {"fdtd-solutions.exe","mpiexec.exe"}: return f"proc:{name}:{pid}"
        current=by_pid.get(int(current.get("ppid",-1)))
    return f"proc:{str(row.get('name') or '').lower()}:{int(row.get('pid',-1))}"

def _classify(cmdline):
    text=str(cmdline or "").lower().replace("/","\\")
    if "blue_apcd_lp_global_h_manifold_v1" in text or "\\lp_global_h_h1a" in text: return "work/lp-global-h-manifold-v1"
    if "blue_apcd_np" in text: return "NP"
    if "blue_apcd_mdc" in text: return "MDC"
    if "coupling" in text: return "Coupling"
    return "EXTERNAL_UNREGISTERED"

def _classify_solver_type(cmdline):
    text=str(cmdline or "").lower().replace("/", "\\")
    # The coupling branch uses RCWA resources even though its launcher may
    # contain Lumerical/FDTD-named controller processes and MPI engines.
    if "blue_apcd_mdc_np_coupling_v1" in text or "np_level1_s_ux" in text or "coupling" in text or "rcwa" in text:
        return "RCWA"
    # A positively identified Fluent MPI lineage is external resource
    # occupancy, not an APCD FDTD job. Keep it visible for audit while
    # preventing it from triggering the unresolved-unknown safety gate.
    if "fluent" in text and ("mpiexec" in text or "fl_mpi" in text or "multiport\\mpi" in text):
        return "EXTERNAL_FLUENT"
    if "blue_apcd_paper_a_lp_cp_broadband_v1" in text or "blue_apcd_np" in text or "blue_apcd_lp_global_h_manifold_v1" in text or "\\lp_global_h" in text:
        return "FDTD"
    return "UNKNOWN"

def _row_solver_type(row):
    explicit=str(row.get("solver_type") or "").upper()
    if explicit in {"FDTD", "RCWA", "UNKNOWN"}:
        return explicit
    text=" ".join(str(row.get(k) or "") for k in ("branch", "worktree", "task_id", "case_uid", "task_class")).lower().replace("/", "\\")
    if "coupling" in text or "mdc" in text or "rcwa" in text or "np_level1_s_ux" in text:
        return "RCWA"
    return "FDTD"

def _branch_key(branch):
    text=str(branch or "").lower()
    if text == "work/lp-global-h-manifold-v1" or "lp_global_h" in text: return "LP"
    if "np" in text: return "NP"
    if "mdc" in text: return "MDC"
    if "coupling" in text: return "COUPLING"
    return text

def _branch_matches(left, right):
    return _branch_key(left) == _branch_key(right)

def _lineage_text(row, by_pid):
    parts=[]; current=row; seen=set()
    while current and int(current.get("pid",-1)) not in seen:
        pid=int(current.get("pid",-1)); seen.add(pid)
        parts.append(str(current.get("name") or ""))
        parts.append(str(current.get("cmdline") or ""))
        current=by_pid.get(int(current.get("ppid",-1)))
    return " ".join(parts).lower().replace("/","\\")

def _is_rcwa_lineage(row, by_pid):
    # RCWA may open an fdtd-solutions controller for messaging, but it is not
    # a production FDTD job and must not consume a validated FDTD slot.
    return "rcwa" in _lineage_text(row, by_pid)

def _is_rcwa_runner(row):
    name=str(row.get("name") or "").lower()
    text=str(row.get("cmdline") or "").lower().replace("/", "\\")
    return name == "python.exe" and "--run" in text and ("rcwa" in text or "coupling" in text)


def _is_server_controller(row):
    # The resident Lumerical server is a controller endpoint, not an active
    # FDTD job. A real formal job is represented by an .fsp-bearing launcher
    # or engine process in the same process group.
    name=str(row.get("name") or "").lower()
    text=str(row.get("cmdline") or "").lower()
    return name == "fdtd-solutions.exe" and ".fsp" not in text and ".fspx" not in text

def live_job_snapshot(provider:Callable[[],list[dict[str,Any]]]|None=None):
    rows=list(provider() if provider else _ps_snapshot())
    by_pid={int(r.get("pid",-1)):r for r in rows}
    formal=[r for r in rows if (str(r.get("name") or "").lower() in FORMAL_NAMES or _is_rcwa_runner(r)) and not _is_server_controller(r)]
    direct_tokens={int(row.get("pid",-1)):_token(row,by_pid) for row in formal}
    direct_fsp_tokens={token for pid,token in direct_tokens.items() if str(by_pid[pid].get("cmdline") or "").lower().find(".fsp") >= 0}
    def ancestors(pid):
        seen=set()
        current=by_pid.get(pid)
        while current and int(current.get("pid",-1)) not in seen:
            current_pid=int(current.get("pid",-1)); seen.add(current_pid)
            parent_pid=int(current.get("ppid",-1))
            current=by_pid.get(parent_pid)
        return seen
    groups={}
    # A controller/server may have no FSP in its own command line while its
    # descendant mpiexec/engine carries the FSP.  Attach that server to the
    # unique descendant FSP job; it must not become a second FDTD job.
    fsp_pid_tokens={pid: direct_tokens[pid] for pid in direct_tokens if direct_tokens[pid] in direct_fsp_tokens}
    for row in formal:
        pid=int(row.get("pid",-1))
        token=direct_tokens[pid]
        if token not in direct_fsp_tokens:
            descendant_tokens={token for other_pid, token in fsp_pid_tokens.items() if pid in ancestors(other_pid)}
            if len(descendant_tokens) == 1:
                token=next(iter(descendant_tokens))
        item=groups.setdefault(token,{"job_token":token,"processes":[],"branch":"EXTERNAL_UNREGISTERED","solver_type":"UNKNOWN"})
        item["processes"].append(row)
        branch=_classify(row.get("cmdline"))
        if branch != "EXTERNAL_UNREGISTERED":
            item["branch"]=branch
        solver_type=_classify_solver_type(row.get("cmdline"))
        if solver_type == "RCWA" or item.get("solver_type") == "UNKNOWN":
            item["solver_type"]=solver_type
    jobs=list(groups.values())
    active_fdtd=sum(j.get("solver_type")=="FDTD" for j in jobs)
    active_rcwa=sum(j.get("solver_type")=="RCWA" for j in jobs)
    unknown=[j for j in jobs if j.get("solver_type")=="UNKNOWN"]
    external_fluent=[j for j in jobs if j.get("solver_type")=="EXTERNAL_FLUENT"]
    return {"timestamp_utc":utc_now(),"global_active_jobs":len(jobs),"active_fdtd_jobs":active_fdtd,"active_rcwa_jobs":active_rcwa,"unknown_solver_jobs":unknown,"external_fluent_jobs":external_fluent,"lp_active_jobs":sum(j["branch"]=="work/lp-global-h-manifold-v1" and j.get("solver_type")=="FDTD" for j in jobs),"jobs":jobs,"formal_process_count":len(formal),"fdtd_engine_process_count":sum(sum(str(p.get("name") or "").lower()=="fdtd-engine-msmpi.exe" for p in j.get("processes",[])) for j in jobs if j.get("solver_type")=="FDTD"),"rcwa_process_count":sum(len(j.get("processes",[])) for j in jobs if j.get("solver_type")=="RCWA")}

def _slot_by_id(data,slot_id): return next((r for r in data["active_slots"] if r.get("slot_id")==slot_id),None)

class SlotLease:
    def __init__(self,scheduler,record):
        self.scheduler=scheduler; self.record=record; self.slot_id=str(record["slot_id"]); self._stop=threading.Event(); self._thread=None; self._released=False
    def heartbeat(self): self.scheduler._update(self.slot_id,{"heartbeat":utc_now()})
    def mark_solver_entered(self,solver_start=None):
        stamp=solver_start or utc_now(); self.scheduler._update(self.slot_id,{"entered":True,"entered_solver":True,"solver_start":stamp,"heartbeat":stamp}); self.record.update({"entered":True,"entered_solver":True,"solver_start":stamp})
    def start_heartbeat(self,interval_s=HEARTBEAT_INTERVAL_S):
        def loop():
            while not self._stop.wait(interval_s):
                try: self.heartbeat()
                except SlotError: return
        self._thread=threading.Thread(target=loop,name=f"slot-heartbeat-{self.slot_id}",daemon=True); self._thread.start()
    def stop_heartbeat(self):
        self._stop.set()
        if self._thread is not None: self._thread.join(timeout=2)
    def release(self,state,solver_complete=None):
        if self._released: return
        self._released=True; self.stop_heartbeat(); self.scheduler.release(self,state,solver_complete)

class GlobalSlotScheduler:
    def __init__(self,registry_path=DEFAULT_REGISTRY_PATH,process_provider=None): self.registry_path=Path(registry_path); self.process_provider=process_provider
    def _update(self,slot_id,changes):
        with registry_lock(self.registry_path):
            data=_read(self.registry_path); row=_slot_by_id(data,slot_id)
            if row is None: raise SlotError(f"slot not active: {slot_id}")
            row.update(changes); data["updated_utc"]=utc_now(); _write(self.registry_path,data)
    def _recover_stale(self,data,live):
        keep=[]; recovered=[]
        live_jobs=live.get("jobs",[])
        for row in data["active_slots"]:
            owner=row.get("controller_pid") or row.get("pid")
            if pid_exists(owner): keep.append(row); continue
            case=str(row.get("case_uid") or "").lower(); branch=str(row.get("branch") or "").lower()
            live_case = bool(case and any(case in json.dumps(job,sort_keys=True).lower() for job in live_jobs))
            live_branch = bool(branch and any(_branch_matches(branch, job.get("branch")) for job in live_jobs))
            if live_case or live_branch:
                keep.append(row)
                continue
            completion_evidence = row.get("completion_evidence") or {}
            if row.get("entered") or row.get("entered_solver"):
                if completion_evidence.get("solver_completed") is True and completion_evidence.get("owner_processes_absent") is True:
                    row.update({"completion_release_state":"STALE_RECOVERED_COMPLETED","slot_release_time":utc_now(),"heartbeat":utc_now()}); recovered.append(row)
                    continue
                raise StaleEnteredSlot("HARD_GATE_STALE_SLOT_ENTERED_OR_LIVE_JOB")
            row.update({"completion_release_state":"STALE_RECOVERED_PRE_ENTRY","slot_release_time":utc_now()}); recovered.append(row)
        data["active_slots"]=keep; data.setdefault("history",[]).extend(recovered)
    def acquire(self,branch,worktree,task_id,case_uid,pid=None,metadata=None):
        pid=int(pid or os.getpid()); metadata=dict(metadata or {})
        with registry_lock(self.registry_path):
            data=_read(self.registry_path); live=live_job_snapshot(self.process_provider); self._recover_stale(data,live); active=data["active_slots"]
            if live.get("unknown_solver_jobs"):
                raise SlotError("SOLVER_TYPE_CLASSIFICATION_REQUIRED")
            fdtd_active_rows=[r for r in active if _row_solver_type(r)=="FDTD"]
            uncovered=[j for j in live["jobs"] if j.get("solver_type")=="FDTD" and not any(_branch_matches(r.get("branch"), j.get("branch")) and _row_solver_type(r)=="FDTD" for r in fdtd_active_rows)]
            effective_fdtd=len(fdtd_active_rows)+len(uncovered)
            effective_lp=sum(_branch_key(r.get("branch"))=="LP" for r in fdtd_active_rows)+sum(_branch_key(j.get("branch"))=="LP" for j in uncovered)
            if branch=="work/lp-global-h-manifold-v1" and effective_lp>=MAX_ACTIVE_FDTD_PER_BRANCH: raise SlotUnavailable("WAIT_LP_ACTIVE_FDTD")
            branch_active_limit=_branch_active_limit(branch, metadata)
            if sum(_branch_matches(r.get("branch"),branch) and _row_solver_type(r)=="FDTD" for r in fdtd_active_rows)>=branch_active_limit: raise SlotUnavailable("WAIT_BRANCH_ACTIVE_FDTD")
            if effective_fdtd>=GLOBAL_CAPACITY: raise SlotUnavailable("WAIT_GLOBAL_FDTD_CAPACITY")
            occupied={str(r.get("slot_id")) for r in active if r.get("slot_id")}
            target_index=effective_fdtd+1
            candidates=([f"GLOBAL_SLOT_{target_index}", f"FDTD_SLOT_{target_index}"]
                        if target_index == 1 else
                        [f"FDTD_SLOT_{target_index}", f"GLOBAL_SLOT_{target_index}"])
            candidates.extend(f"FDTD_SLOT_{i}" for i in range(1,GLOBAL_CAPACITY+1))
            candidates.extend(f"GLOBAL_SLOT_{i}" for i in range(1,GLOBAL_CAPACITY+1))
            slot_id=next((candidate for candidate in candidates if candidate not in occupied),None)
            if slot_id is None: raise SlotUnavailable("WAIT_GLOBAL_SLOT_REGISTRY_FULL")
            peers=[str(r.get("branch","UNKNOWN")) for r in active if r.get("branch")!=branch]+[str(j.get("branch","EXTERNAL_UNREGISTERED")) for j in live["jobs"] if j.get("branch")!=branch]; now=utc_now()
            row={"schema":"APCD_GLOBAL_FDTD_SLOT_V1","slot_id":slot_id,"fdtd_slot_id":slot_id,"slot_class":"FDTD","solver_type":"FDTD","branch":branch,"worktree":worktree,"task_id":task_id,"case_uid":case_uid,"task_class":metadata.get("task_class","FORMAL_FDTD"),"requested_slots":1,"requested_cores":PROCESSES_PER_JOB,"pid":pid,"controller_pid":pid,"slot_acquired":True,"entered":False,"entered_solver":False,"start_time":now,"slot_acquire_time":now,"heartbeat":now,"completion_release_state":"ACTIVE","attempt_id":metadata.get("attempt_id"),"polarization":metadata.get("polarization"),"H_global_nm":metadata.get("H_global_nm"),"processes":PROCESSES_PER_JOB,"threads":THREADS_PER_JOB,"concurrent_peer_branch":sorted(set(peers)),"admission_snapshot":{"registry_active_slots":len(active),"live_global_active_jobs":live["global_active_jobs"],"active_fdtd_jobs":live.get("active_fdtd_jobs"),"active_rcwa_jobs":live.get("active_rcwa_jobs"),"unknown_solver_jobs":len(live.get("unknown_solver_jobs",[])),"live_lp_active_jobs":live["lp_active_jobs"],"effective_global_active_jobs_before_acquire":effective_fdtd,"effective_lp_active_jobs_before_acquire":effective_lp,"effective_global_active_jobs_after_acquire":effective_fdtd+1,"effective_lp_active_jobs_after_acquire":effective_lp+1 if branch=="work/lp-global-h-manifold-v1" else effective_lp,"live_jobs":live["jobs"]}}
            data["active_slots"].append(row); data["updated_utc"]=now; _write(self.registry_path,data)
        return SlotLease(self,row)
    def acquire_wait(self,*args,timeout_s=21600.0,poll_s=15.0,**kwargs):
        start=time.monotonic()
        while True:
            try: return self.acquire(*args,**kwargs)
            except SlotUnavailable:
                if time.monotonic()-start>=timeout_s: raise
                time.sleep(poll_s)
    def release(self,lease,state,solver_complete=None):
        with registry_lock(self.registry_path):
            data=_read(self.registry_path); row=_slot_by_id(data,lease.slot_id)
            if row is None: return
            stamp=solver_complete or utc_now(); row.update({"completion_release_state":state,"solver_complete":stamp,"slot_release_time":utc_now(),"heartbeat":utc_now()}); data["active_slots"]=[r for r in data["active_slots"] if r.get("slot_id")!=lease.slot_id]; data.setdefault("history",[]).append(row); data["updated_utc"]=utc_now(); _write(self.registry_path,data)
