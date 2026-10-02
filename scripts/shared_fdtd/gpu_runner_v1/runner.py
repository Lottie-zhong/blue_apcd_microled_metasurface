# -*- coding: utf-8 -*-
"""Filesystem-authoritative serial GPU runner core; independent of V3 control state."""
import hashlib, json, os, re, shutil, time, uuid
from pathlib import Path

PRODUCTION_RUNNER_ROOT = Path(r"D:\apcd_runtime\gpu_production_runner_v1")
GPU_SLOT_COUNT = 1
MAX_CONCURRENT_GPU_JOBS = 1

CONTRACT_SHA256 = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
EXPANSION_SHA256 = "4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f"
GEOMETRIES = {"K6V1_S35": [110,145,225,105,185,215],
              "K6V1_S39": [175,100,125,120,100,230]}
MIN_GPU_FREE_MIB = 1369
MANIFEST_KEYS = {"case_id","attempt_id","run_id","geometry","physical_contract_sha256",
                 "expansion_manifest_sha256","pre_fsp_path","pre_fsp_sha256"}
ENTRY_STATES = {"SOLVER_ENTERED","SOLVER_RETURNED","TRUTH_VALID","DONE","FAILED_POSTENTRY"}
TRANSITIONS = {"PENDING":{"PRECHECK_PASS","FAILED_PREENTRY"},
 "PRECHECK_PASS":{"SOLVER_ENTERED","FAILED_PREENTRY"},
 "SOLVER_ENTERED":{"SOLVER_RETURNED","FAILED_POSTENTRY"},
 "SOLVER_RETURNED":{"TRUTH_VALID","FAILED_POSTENTRY"},
 "TRUTH_VALID":{"DONE","FAILED_POSTENTRY"}}

class RunnerError(RuntimeError):
    pass

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp-"+uuid.uuid4().hex)
    try:
        with open(tmp,"xb") as f:
            f.write((json.dumps(obj,sort_keys=True,indent=2)+"\n").encode("utf-8"))
            f.flush(); os.fsync(f.fileno())
        os.replace(str(tmp),str(path))
    finally:
        try: tmp.unlink()
        except FileNotFoundError: pass

def read_json(path,default=None):
    path=Path(path)
    if not path.exists(): return default
    with path.open("r",encoding="utf-8") as f: return json.load(f)

def validate_manifest(m):
    if not isinstance(m,dict) or set(m)!=MANIFEST_KEYS: raise RunnerError("MANIFEST_KEYS_INVALID")
    for k in ("case_id","attempt_id","run_id"):
        if not isinstance(m[k],str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}",m[k]):
            raise RunnerError("INVALID_"+k.upper())
    if m["case_id"] not in GEOMETRIES or m["geometry"]!=GEOMETRIES[m["case_id"]]:
        raise RunnerError("GEOMETRY_MISMATCH")
    if m["physical_contract_sha256"]!=CONTRACT_SHA256: raise RunnerError("PHYSICAL_CONTRACT_HASH_MISMATCH")
    if m["expansion_manifest_sha256"]!=EXPANSION_SHA256: raise RunnerError("EXPANSION_MANIFEST_HASH_MISMATCH")
    if not isinstance(m["pre_fsp_path"],str) or not m["pre_fsp_path"]: raise RunnerError("PRE_FSP_PATH_MISSING")
    if not re.fullmatch(r"[0-9a-f]{64}",str(m["pre_fsp_sha256"])): raise RunnerError("PRE_FSP_HASH_INVALID")

def _exclusive(path,payload):
    fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as f: f.write(payload); f.flush(); os.fsync(f.fileno())

def _verify_pre_entry_ownership(lock_path,active_path,manifest):
    identity=("run_id","case_id","attempt_id")
    lock_record=read_json(lock_path)
    if (not isinstance(lock_record,dict) or lock_record.get("pid")!=os.getpid()
            or any(lock_record.get(k)!=manifest[k] for k in identity)):
        raise RunnerError("RUNNER_LOCK_OWNERSHIP_MISMATCH")
    active_record=read_json(active_path)
    if (not isinstance(active_record,dict) or active_record.get("pid")!=os.getpid()
            or any(active_record.get(k)!=manifest[k] for k in identity)
            or active_record.get("state")!="PRECHECK_PASS"):
        raise RunnerError("ACTIVE_RUN_OWNERSHIP_MISMATCH")

def _registry(root):
    root=Path(root); p=root/"registry.json"
    if p.exists():
        value=read_json(p)
        if (not isinstance(value,dict) or value.get("schema")!="APCD_GPU_RUNNER_REGISTRY_V1"
                or not isinstance(value.get("runs"),list)):
            raise RunnerError("REGISTRY_INVALID")
        rows=value["runs"]; changed=False
    else:
        value={"schema":"APCD_GPU_RUNNER_REGISTRY_V1","runs":[]}
        rows=value["runs"]; changed=True
    allowed={"PENDING","PRECHECK_PASS","FAILED_PREENTRY"}|ENTRY_STATES
    by_id={}
    for row in rows:
        if (not isinstance(row,dict) or not all(isinstance(row.get(k),str)
                for k in ("case_id","attempt_id","run_id","state"))
                or row["state"] not in allowed or row["run_id"] in by_id):
            raise RunnerError("REGISTRY_INVALID")
        by_id[row["run_id"]]=row
    base=root/"runs"
    if base.exists():
        for sp in sorted(base.glob("*/*/*/status.json")):
            m,s=read_json(sp.parent/"manifest.json"),read_json(sp)
            if not isinstance(m,dict) or not isinstance(s,dict):
                raise RunnerError("REGISTRY_REBUILD_FAILED")
            keys=("case_id","attempt_id","run_id")
            if (not all(isinstance(m.get(k),str) for k in keys)
                    or any(s.get(k)!=m[k] for k in keys)
                    or s.get("state") not in allowed):
                raise RunnerError("REGISTRY_IDENTITY_OR_STATE_INVALID")
            run_id=m["run_id"]; row=by_id.get(run_id)
            if row is None:
                row={k:m[k] for k in keys}; row.update(state=s["state"],run_dir=str(sp.parent))
                rows.append(row); by_id[run_id]=row; changed=True
            else:
                if any(row.get(k)!=m[k] for k in keys):
                    raise RunnerError("REGISTRY_IDENTITY_CONFLICT")
                old=row["state"]; disk=s["state"]
                # Preserve any durable entry evidence if the registry lags or conflicts.
                merged=disk if disk in ENTRY_STATES or old not in ENTRY_STATES else old
                if row.get("run_dir")!=str(sp.parent) or old!=merged:
                    row["run_dir"]=str(sp.parent); row["state"]=merged; changed=True
    if changed: atomic_json(p,value)
    return value

def _transition(run_dir,status,state,**fields):
    if state not in TRANSITIONS.get(status["state"],set()): raise RunnerError("ILLEGAL_STATE_TRANSITION")
    status=dict(status,**fields); status.update(state=state,updated_unix=time.time())
    atomic_json(Path(run_dir)/"status.json",status); return status

def _durable(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size==0: return False
    with p.open("r+b") as f: os.fsync(f.fileno())
    return True

def run_one(manifest,root,solver,fresh_load_validate,gpu_snapshot,runner_owner_probe):
    """Run one manifest with injected adapters; no V3 control-state imports."""
    validate_manifest(manifest)
    root=Path(root).resolve(); root.mkdir(parents=True,exist_ok=True)
    lock=root/".runner.lock"
    lock_record={"pid":os.getpid(),"run_id":manifest["run_id"],
                  "case_id":manifest["case_id"],"attempt_id":manifest["attempt_id"]}
    try: _exclusive(lock,json.dumps(lock_record).encode("utf-8"))
    except FileExistsError: raise RunnerError("RUNNER_LOCKED")
    active=root/"active_run.json"
    run_dir=root/"runs"/manifest["case_id"]/manifest["attempt_id"]/manifest["run_id"]
    status=registry=row=None; entered=False; active_created=False
    try:
        if active.exists(): raise RunnerError("ACTIVE_RUN_PRESENT")
        registry=_registry(root); rows=registry["runs"]
        existing=[r for r in rows if r.get("run_id")==manifest["run_id"]]
        if len(existing)>1: raise RunnerError("REGISTRY_INVALID")
        resume_pending=False
        if run_dir.exists() or existing:
            if not run_dir.is_dir() or not existing:
                raise RunnerError("DUPLICATE_RUN_ID")
            row=existing[0]
            saved_manifest=read_json(run_dir/"manifest.json")
            status=read_json(run_dir/"status.json")
            if saved_manifest!=manifest: raise RunnerError("RUN_ID_MANIFEST_CONFLICT")
            if (row.get("state")!="PENDING" or not isinstance(status,dict)
                    or status.get("state")!="PENDING" or status.get("run_id")!=manifest["run_id"]
                    or status.get("case_id")!=manifest["case_id"]
                    or status.get("attempt_id")!=manifest["attempt_id"]
                    or status.get("solver_entered") is not False
                    or status.get("solver_invocations")!=0):
                raise RunnerError("DUPLICATE_RUN_ID")
            resume_pending=True
        prior=[r for r in rows if r.get("case_id")==manifest["case_id"]
               and r.get("attempt_id")==manifest["attempt_id"]]
        if any(r.get("state") in ENTRY_STATES for r in prior):
            raise RunnerError("POST_ENTRY_REPLAY_FORBIDDEN")
        if any(r.get("state")=="PENDING" and r.get("run_id")!=manifest["run_id"] for r in prior):
            raise RunnerError("PENDING_RUN_ID_CONFLICT")
        if manifest["case_id"]=="K6V1_S39" and not any(
                r.get("case_id")=="K6V1_S35" and r.get("state")=="DONE" for r in rows):
            raise RunnerError("S39_REQUIRES_S35_DONE")
        if not resume_pending:
            if run_dir.exists(): raise RunnerError("DUPLICATE_RUN_ID")
            run_dir.mkdir(parents=True,exist_ok=False)
            atomic_json(run_dir/"manifest.json",manifest)
            (run_dir/"solver.log").write_text("",encoding="utf-8")
            status={"schema":"APCD_GPU_RUN_STATUS_V1","case_id":manifest["case_id"],
             "attempt_id":manifest["attempt_id"],"run_id":manifest["run_id"],"state":"PENDING",
             "solver_entered":False,"solver_invocations":0,"created_unix":time.time()}
            atomic_json(run_dir/"status.json",status)
            atomic_json(run_dir/"validation.json",{"state":"PENDING"})
            atomic_json(run_dir/"hashes.json",{"state":"PENDING"})
            row=dict(case_id=manifest["case_id"],attempt_id=manifest["attempt_id"],
                     run_id=manifest["run_id"],state="PENDING",run_dir=str(run_dir))
            rows.append(row); atomic_json(root/"registry.json",registry)
        try:
            pre=Path(manifest["pre_fsp_path"]).resolve()
            if not pre.is_file(): raise RunnerError("PRE_FSP_MISSING")
            if sha256_file(pre)!=manifest["pre_fsp_sha256"]:
                raise RunnerError("PRE_FSP_HASH_MISMATCH")
            if active.exists() or runner_owner_probe(root):
                raise RunnerError("RUNNER_OWNED_ACTIVITY_PRESENT")
            snap=gpu_snapshot()
            if not isinstance(snap,dict): raise RunnerError("GPU_SNAPSHOT_INVALID")
            try: free_mib=int(snap.get("free_mib",-1))
            except (TypeError,ValueError): free_mib=-1
            snap_hash=hashlib.sha256(
                json.dumps(snap,sort_keys=True,default=str).encode("utf-8")).hexdigest()
            if free_mib<MIN_GPU_FREE_MIB:
                waited=time.time()
                status=dict(status,state="PENDING",solver_entered=False,solver_invocations=0,
                    capacity_wait_reason="INSUFFICIENT_OR_UNKNOWN_GPU_HEADROOM",
                    capacity_wait_unix=waited,updated_unix=waited,
                    gpu_snapshot=snap,gpu_snapshot_sha256=snap_hash)
                atomic_json(run_dir/"status.json",status)
                row["state"]="PENDING"; atomic_json(root/"registry.json",registry)
                return {"run_dir":str(run_dir),"state":"PENDING",
                    "result":"WAIT_GPU_CAPACITY",
                    "result_classification":"NON_SCIENTIFIC_CAPACITY_WAIT",
                    "solver_entered":False,"solver_invocations":0,
                    "gpu_snapshot":snap,"gpu_snapshot_sha256":snap_hash}
            shutil.copyfile(str(pre),str(run_dir/"run.fsp"))
            if sha256_file(run_dir/"run.fsp")!=manifest["pre_fsp_sha256"]:
                raise RunnerError("RUN_FSP_COPY_HASH_MISMATCH")
            status=_transition(run_dir,status,"PRECHECK_PASS",
                pre_fsp_sha256=manifest["pre_fsp_sha256"],
                gpu_snapshot=snap,gpu_snapshot_sha256=snap_hash)
            row["state"]="PRECHECK_PASS"; atomic_json(root/"registry.json",registry)
            atomic_json(active,{"run_id":manifest["run_id"],"case_id":manifest["case_id"],
                "attempt_id":manifest["attempt_id"],"pid":os.getpid(),"state":"PRECHECK_PASS"})
            active_created=True
            _verify_pre_entry_ownership(lock,active,manifest)
            status=_transition(run_dir,status,"SOLVER_ENTERED",solver_entered=True,
                solver_invocations=1,solver_entered_unix=time.time())
            entered=True
            atomic_json(active,{"run_id":manifest["run_id"],"case_id":manifest["case_id"],
                "attempt_id":manifest["attempt_id"],"pid":os.getpid(),"state":"SOLVER_ENTERED"})
            row["state"]="SOLVER_ENTERED"; atomic_json(root/"registry.json",registry)
            result=solver(manifest,run_dir)
            status=_transition(run_dir,status,"SOLVER_RETURNED",solver_returned_unix=time.time(),
                               solver_result=str(result)[:400])
            row["state"]="SOLVER_RETURNED"; atomic_json(root/"registry.json",registry)
            if not _durable(run_dir/"run.fsp"):
                raise RunnerError("POST_FSP_NOT_DURABLE")
            validation=fresh_load_validate(manifest,run_dir)
            flags=("fresh_load_verified","monitors_valid","state_valid","scientific_valid")
            if not isinstance(validation,dict) or any(validation.get(k) is not True for k in flags):
                raise RunnerError("FRESH_LOAD_TRUTH_VALIDATION_FAILED")
            if not _durable(run_dir/"truth.h5"):
                raise RunnerError("TRUTH_ARTIFACT_NOT_DURABLE")
            fsp_hash=sha256_file(run_dir/"run.fsp"); truth_hash=sha256_file(run_dir/"truth.h5")
            validation=dict(validation,run_id=manifest["run_id"],run_fsp_sha256=fsp_hash,
                            truth_h5_sha256=truth_hash,validated_unix=time.time())
            atomic_json(run_dir/"validation.json",validation)
            atomic_json(run_dir/"hashes.json",{"manifest_sha256":sha256_file(run_dir/"manifest.json"),
             "pre_fsp_sha256":manifest["pre_fsp_sha256"],"run_fsp_sha256":fsp_hash,
             "truth_h5_sha256":truth_hash,"validation_sha256":sha256_file(run_dir/"validation.json")})
            status=_transition(run_dir,status,"TRUTH_VALID",run_fsp_sha256=fsp_hash,
                               truth_h5_sha256=truth_hash)
            row["state"]="TRUTH_VALID"; atomic_json(root/"registry.json",registry)
            status=_transition(run_dir,status,"DONE",done_unix=time.time())
            row["state"]="DONE"; atomic_json(root/"registry.json",registry)
            return {"run_dir":str(run_dir),"status":status,"validation":validation}
        except Exception as exc:
            if status is not None and status["state"] not in ("FAILED_PREENTRY","FAILED_POSTENTRY"):
                failed="FAILED_POSTENTRY" if entered else "FAILED_PREENTRY"
                status=_transition(run_dir,status,failed,failure=str(exc),failed_unix=time.time())
                row["state"]=failed; atomic_json(root/"registry.json",registry)
            if isinstance(exc,RunnerError): raise
            raise RunnerError(str(exc)) from exc
    finally:
        if active_created and read_json(active,{}).get("run_id")==manifest["run_id"]:
            try: active.unlink()
            except FileNotFoundError: pass
        try: lock.unlink()
        except FileNotFoundError: pass
