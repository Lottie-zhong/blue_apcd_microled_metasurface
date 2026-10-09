"""Generic, hash-bound closeout for one-entry post-entry failures without truth."""
import hashlib, json, os
from pathlib import Path

SCHEMA = "APCD_GPU_RUNNER_V1_POSTENTRY_FAILURE_CLOSEOUT_RECEIPT_V1"
VERIFY_SCHEMA = "APCD_GPU_RUNNER_V1_POSTENTRY_FAILURE_CLOSEOUT_VERIFICATION_V1"

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")

def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def sha_file(path): return sha_bytes(Path(path).read_bytes())
def self_hash(value, field):
    body=dict(value); claimed=body.pop(field,None)
    return claimed == sha_bytes(canonical(body))
def _write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    os.replace(str(temp),str(path))
def _identity(doc):
    return {k:doc.get(k) for k in ("case_id","attempt_id","run_id")}
def _row(root,status):
    reg=json.loads((Path(root)/"registry.json").read_text(encoding="utf-8"))
    rows=[x for x in reg.get("runs",[]) if isinstance(x,dict) and _identity(x)==_identity(status)]
    if len(rows)!=1: raise ValueError("REGISTRY_TARGET_ROW_NOT_UNIQUE")
    return rows[0]
def _assert_no_active_markers(root):
    root=Path(root)
    for path in (root/"active_run.json",root/".runner.lock",root/"scheduler_worker_v1.lock"):
        if path.exists(): raise ValueError("ACTIVE_RUNNER_MARKER_PRESENT:"+path.name)
def _truth_files(run_dir):
    suffixes={".h5",".hdf5",".npz",".mat",".csv"}
    return sorted(str(p) for p in Path(run_dir).rglob("*") if p.is_file() and p.suffix.lower() in suffixes)
def _request_result(request_dir, status):
    request_dir=Path(request_dir)
    request=json.loads((request_dir/"request.json").read_text(encoding="utf-8"))
    result=json.loads((request_dir/"result.json").read_text(encoding="utf-8"))
    claim=json.loads((request_dir/"worker_claim.json").read_text(encoding="utf-8"))
    ident=_identity(status)
    if request.get("request_id")!=result.get("request_id") or request.get("request_id")!=claim.get("request_id"):
        raise ValueError("REQUEST_ID_MISMATCH")
    if request.get("identity")!=ident:
        raise ValueError("REQUEST_RUN_IDENTITY_MISMATCH")
    request_sha=request.get("request_sha256")
    if not request_sha or result.get("request_sha256")!=request_sha or claim.get("request_sha256")!=request_sha:
        raise ValueError("REQUEST_HASH_CHAIN_MISMATCH")
    if result.get("state") not in (None,"TERMINAL") and result.get("terminal") is not True:
        raise ValueError("REQUEST_RESULT_NOT_TERMINAL")
    rs=result.get("run_status",{})
    if (result.get("solver_entered") is not True or rs.get("state")!="FAILED_POSTENTRY"
            or rs.get("solver_invocations")!=1 or result.get("solver_invocations",rs.get("solver_invocations"))!=1):
        raise ValueError("REQUEST_RESULT_POSTENTRY_STATE_MISMATCH")
    return request,result,claim
def create_postentry_failure_closeout(root, run_dir, request_dir,
                                      process_census_path, controller_state_path,
                                      authorization_source):
    root=Path(root).resolve(); run_dir=Path(run_dir).resolve()
    status_path=run_dir/"status.json"; status=json.loads(status_path.read_text(encoding="utf-8"))
    if (status.get("state")!="FAILED_POSTENTRY" or status.get("solver_entered") is not True
            or status.get("solver_invocations")!=1): raise ValueError("TARGET_NOT_SINGLE_FAILED_POSTENTRY")
    _assert_no_active_markers(root)
    if (run_dir/".runner.lock").exists(): raise ValueError("RUN_LOCK_PRESENT")
    manifest_path=run_dir/"manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if _identity(manifest)!=_identity(status): raise ValueError("MANIFEST_STATUS_IDENTITY_MISMATCH")
    pre_sha=manifest.get("pre_fsp_sha256")
    fsp=run_dir/"run.fsp"
    if not fsp.is_file() or sha_file(fsp)!=pre_sha or status.get("pre_fsp_sha256")!=pre_sha:
        raise ValueError("FSP_DIFFERS_FROM_ENTERED_PRE_FSP")
    if _truth_files(run_dir): raise ValueError("TRUTH_ARTIFACT_PRESENT_NO_AUTO_CLOSEOUT")
    for pending in ("validation.json","hashes.json"):
        value=json.loads((run_dir/pending).read_text(encoding="utf-8"))
        if value.get("state")!="PENDING": raise ValueError("TRUTH_VALIDATION_NOT_PENDING")
    exception_path=run_dir/"failure_exception_v1.json"
    exception=json.loads(exception_path.read_text(encoding="utf-8"))
    if (_identity(exception)!=_identity(status) or exception.get("solver_entered") is not True
            or exception.get("solver_invocations")!=1): raise ValueError("FAILURE_EXCEPTION_IDENTITY_MISMATCH")
    request,result,claim=_request_result(request_dir,status)
    if status.get("failure")!=str(exception.get("exception_type"))+":"+str(exception.get("exception")):
        raise ValueError("STATUS_EXCEPTION_MISMATCH")
    row=_row(root,status)
    census_path=Path(process_census_path).resolve(strict=True)
    census=json.loads(census_path.read_text(encoding="utf-8"))
    for key in ("engine_processes","queue_execution_processes","runner_active_processes","related_processes"):
        if census.get(key)!=[]: raise ValueError("ACTIVE_PROCESS_CENSUS:"+key)
    controller_path=Path(controller_state_path).resolve(strict=True)
    controller=json.loads(controller_path.read_text(encoding="utf-8"))
    if controller.get("state") not in ("STOPPED_RECONCILED","CONTROLLER_EXITED_NEEDS_RECONCILIATION"):
        raise ValueError("CONTROLLER_NOT_STOPPED")
    request_dir=Path(request_dir).resolve()
    inputs={
        "status":status_path,"manifest":manifest_path,"failure_exception":exception_path,
        "run_fsp":fsp,"validation":run_dir/"validation.json","hashes":run_dir/"hashes.json",
        "request":request_dir/"request.json","result":request_dir/"result.json",
        "worker_claim":request_dir/"worker_claim.json","process_census":census_path,
        "controller_state":controller_path,
    }
    evidence={key:{"path":str(path),"sha256":sha_file(path)} for key,path in inputs.items()}
    row_sha=sha_bytes(canonical(row))
    close_dir=run_dir/"postentry_failure_closeout_v1"
    receipt_path=close_dir/"receipt.json"; verification_path=close_dir/"verification.json"
    if receipt_path.exists() or verification_path.exists(): raise ValueError("CLOSEOUT_ALREADY_EXISTS")
    body={"schema":SCHEMA,"result":"CLOSED","disposition":"FAILED_POSTENTRY_NO_TRUTH",
          **_identity(status),"request_id":request["request_id"],"failure":status["failure"],
          "solver_entry_count":1,"solver_invocations":1,"automatic_replay_count":0,
          "recovery_solver_invocations":0,"truth_available":False,"scientific_valid":False,
          "training_admitted":False,"lineage_disposition":"NOT_RECONSTRUCTED",
          "physical_gpu_engine_entry_count":"UNKNOWN","runner_slot_closed":True,
          "registry_row_sha256":row_sha,"evidence":evidence,
          "authorization_source":str(authorization_source)}
    receipt=dict(body,receipt_sha256=sha_bytes(canonical(body)))
    checks={"single_failed_postentry_entry":True,"request_result_terminal_and_bound":True,
            "pre_fsp_unchanged":True,"truth_artifacts_absent":True,"active_markers_absent":True,
            "active_execution_processes_absent":True,"controller_stopped":True,
            "registry_row_matches":True,"automatic_replay_zero":True}
    verify_body={"schema":VERIFY_SCHEMA,"receipt_path":str(receipt_path),
                 "receipt_self_sha256":receipt["receipt_sha256"],"checks":checks,
                 "process_census":census,"controller_state":controller,
                 "request_result":{"request_id":request["request_id"],
                   "result_sha256":result.get("result_sha256"),"exit_code":result.get("exit_code")}}
    _write_json(receipt_path,receipt)
    verify_body["receipt_file_sha256"]=sha_file(receipt_path)
    verification=dict(verify_body,verification_sha256=sha_bytes(canonical(verify_body)))
    _write_json(verification_path,verification)
    return {"receipt_path":str(receipt_path),"receipt_sha256":sha_file(receipt_path),
            "receipt_self_sha256":receipt["receipt_sha256"],
            "verification_path":str(verification_path),"verification_sha256":sha_file(verification_path),
            "case_id":status["case_id"],"attempt_id":status["attempt_id"],"run_id":status["run_id"]}

def validate_postentry_failure_closeout(root, status_path, status):
    try:
        root=Path(root).resolve(); status_path=Path(status_path).resolve()
        run_dir=status_path.parent; close_dir=run_dir/"postentry_failure_closeout_v1"
        receipt_path=close_dir/"receipt.json"; verification_path=close_dir/"verification.json"
        if not receipt_path.is_file() or not verification_path.is_file():
            return _validate_legacy_closeout(root,status_path,status)
        _assert_no_active_markers(root)
        if status.get("state")!="FAILED_POSTENTRY" or status.get("solver_entered") is not True or status.get("solver_invocations")!=1: return False
        receipt=json.loads(receipt_path.read_text(encoding="utf-8")); verification=json.loads(verification_path.read_text(encoding="utf-8"))
        if not self_hash(receipt,"receipt_sha256") or not self_hash(verification,"verification_sha256"): return False
        if receipt.get("schema")!=SCHEMA or receipt.get("result")!="CLOSED" or receipt.get("disposition")!="FAILED_POSTENTRY_NO_TRUTH": return False
        if _identity(receipt)!=_identity(status) or receipt.get("failure")!=status.get("failure"): return False
        if (receipt.get("solver_entry_count")!=1 or receipt.get("solver_invocations")!=1
                or receipt.get("automatic_replay_count")!=0 or receipt.get("recovery_solver_invocations")!=0
                or receipt.get("truth_available") is not False or receipt.get("scientific_valid") is not False
                or receipt.get("training_admitted") is not False or receipt.get("runner_slot_closed") is not True
                or receipt.get("lineage_disposition")!="NOT_RECONSTRUCTED"): return False
        if sha_file(status_path)!=receipt.get("evidence",{}).get("status",{}).get("sha256"): return False
        row=_row(root,status)
        if sha_bytes(canonical(row))!=receipt.get("registry_row_sha256"): return False
        evidence=receipt.get("evidence",{})
        for item in evidence.values():
            if not isinstance(item,dict) or not Path(item.get("path","")).is_file() or sha_file(item["path"])!=item.get("sha256"): return False
        request,result,claim=_request_result(Path(evidence["request"]["path"]).parent,status)
        if request.get("request_id")!=receipt.get("request_id"): return False
        checks=verification.get("checks")
        if (verification.get("schema")!=VERIFY_SCHEMA or verification.get("receipt_self_sha256")!=receipt.get("receipt_sha256")
                or verification.get("receipt_path")!=str(receipt_path) or verification.get("receipt_file_sha256")!=sha_file(receipt_path)): return False
        if not isinstance(checks,dict) or not checks or any(v is not True for v in checks.values()): return False
        census=verification.get("process_census",{})
        if any(census.get(k)!=[] for k in ("engine_processes","queue_execution_processes","runner_active_processes","related_processes")): return False
        if _truth_files(run_dir): return False
        return True
    except Exception:
        return False


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description="Create a hash-bound one-entry failure closeout; no solver is called.")
    parser.add_argument("--runner-root",required=True); parser.add_argument("--run-dir",required=True)
    parser.add_argument("--request-dir",required=True); parser.add_argument("--process-census",required=True)
    parser.add_argument("--controller-state",required=True); parser.add_argument("--authorization-source",required=True)
    args=parser.parse_args(argv)
    print(json.dumps(create_postentry_failure_closeout(args.runner_root,args.run_dir,args.request_dir,args.process_census,args.controller_state,args.authorization_source),sort_keys=True))

if __name__ == "__main__":
    main()

def _validate_legacy_closeout(root,status_path,status):
    """Read prior receipt versions by their content, without a case-specific allowlist."""
    try:
        run_dir=Path(status_path).parent; close_dir=run_dir/"postentry_closeout_v1"
        rp=close_dir/"receipt.json"; vp=close_dir/"post_closeout_verification_v2.json"
        if not rp.is_file() or not vp.is_file(): return False
        receipt=json.loads(rp.read_text(encoding="utf-8-sig")); verification=json.loads(vp.read_text(encoding="utf-8-sig"))
        schema=receipt.get("schema","")
        if not (schema.startswith("APCD_GPU_RUNNER_V1_") and schema.endswith("_POSTENTRY_CLOSEOUT_RECEIPT_V1")): return False
        if (not self_hash(receipt,"receipt_sha256") or receipt.get("result")!="CLOSED"
                or receipt.get("disposition")!="FAILED_POSTENTRY_NO_TRUTH" or _identity(receipt)!=_identity(status)):
            return False
        if (status.get("state")!="FAILED_POSTENTRY" or status.get("solver_entered") is not True
                or status.get("solver_invocations")!=1 or receipt.get("solver_entry_count")!=1
                or receipt.get("solver_invocations")!=1 or receipt.get("automatic_replay_count")!=0
                or receipt.get("runner_slot_closed") is not True or receipt.get("truth_available") is not False
                or receipt.get("scientific_valid") is not False or receipt.get("training_admitted") is not False
                or receipt.get("status_sha256")!=sha_file(status_path)):
            return False
        row=_row(root,status)
        if (row.get("state")!="FAILED_POSTENTRY" or os.path.normcase(os.path.abspath(row.get("run_dir","")))
                !=os.path.normcase(os.path.abspath(run_dir))): return False
        if not self_hash(verification,"verification_sha256"): return False
        if (verification.get("receipt_path") is None or os.path.normcase(os.path.abspath(verification["receipt_path"]))
                !=os.path.normcase(os.path.abspath(rp)) or verification.get("receipt_file_sha256")!=sha_file(rp)
                or verification.get("receipt_self_sha256")!=receipt.get("receipt_sha256")
                or verification.get("runner_status_sha256")!=sha_file(status_path)):
            return False
        checks=verification.get("checks")
        if not isinstance(checks,dict) or not checks or any(value is not True for value in checks.values()): return False
        counts=verification.get("execution_counts",{})
        if (counts.get("solver_entries")!=1 or counts.get("fdtd_runs_during_recovery")!=0
                or counts.get("solver_invocations_after_recovery")!=0 or counts.get("automatic_replays")!=0): return False
        census=verification.get("process_census",{})
        if any(census.get(k)!=[] for k in ("engine_processes","queue_execution_processes","related_processes")): return False
        rs=verification.get("runner_request_state",{}); req=rs.get("request",{}); result=rs.get("result",{})
        if (rs.get("state")!="TERMINAL" or req.get("request_id")!=receipt.get("request_id")
                or req.get("identity")!=_identity(status) or result.get("solver_entered") is not True
                or result.get("run_status",{}).get("state")!="FAILED_POSTENTRY"):
            return False
        _assert_no_active_markers(root)
        return not _truth_files(run_dir)
    except Exception:
        return False
