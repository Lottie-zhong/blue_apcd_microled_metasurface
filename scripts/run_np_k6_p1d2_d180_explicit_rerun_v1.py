"""One explicitly authorized, auditable D180 x-polarized rerun; never a retry loop."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_np_k6_p1d2b_broadband_pillar_x_v1 as single
import run_np_k6_p1d2_batch_broadband_pillars_x_v1 as batch

CASE = "NP_P1D2_BROADBAND_PILLAR_H500_D180_X_EXPLICIT_RERUN_V1"
OUT = ROOT / "outputs" / "np_k6_p1d2_d180_explicit_rerun_v1"
RUNTIME = ROOT / "runtime_fsp" / "np_k6_p1d2_d180_explicit_rerun_v1"
PRE, POST = RUNTIME / f"{CASE}_pre.fsp", RUNTIME / f"{CASE}_post.fsp"
OLD = ROOT / "outputs" / "np_k6_p1d2_batch_d120_d230_v1" / "batch_progress.json"

def utc(): return datetime.now(timezone.utc).isoformat()
def fp(p): return {"path":str(p.relative_to(ROOT)).replace("\\","/"),"size":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True); t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(t,p)
def append(x):
    with (OUT/"attempt_ledger.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(x,sort_keys=True)+"\n")
def configure():
    single.CASE=CASE; single.DIAMETER_NM=180; single.OUT=OUT; single.PRE=PRE; single.POST=POST
def old_attempt():
    r=json.loads(OLD.read_text(encoding="utf-8"))["cases"]["180"]
    if r.get("status")!="sealed_failed_case_local" or r.get("solver_entered_count")!=1 or r.get("solver_completed_count")!=0: raise RuntimeError("historical D180 seal contract mismatch")
    return r
def main():
    p=argparse.ArgumentParser(); p.add_argument("--diameter-nm",type=int,required=True); p.add_argument("--polarization",required=True); p.add_argument("--explicit-user-authorization",action="store_true"); p.add_argument("--maximum-new-solver-runs",type=int,required=True); a=p.parse_args()
    if (a.diameter_nm,a.polarization,a.maximum_new_solver_runs,a.explicit_user_authorization)!=(180,"x",1,True): raise ValueError("explicit D180 x authorization, and solver budget 1, are required")
    old=old_attempt(); configure(); s=single.spec()
    if POST.exists(): raise RuntimeError("new-attempt post-FSP already exists; second execution prohibited")
    OUT.mkdir(parents=True,exist_ok=True); RUNTIME.mkdir(parents=True,exist_ok=True)
    contract={"retry_authorization":"explicit_user_authorized_independent_rerun_v1","historical_attempt":old,"explicit_rerun_attempt":1,"case_id":CASE,"diameter_nm":180,"polarization":"x","maximum_new_solver_runs":1,"automatic_retry_prohibited":True,"target_axis_nm":single.shared.target_axis(),"monitor_count":33,"K6":"hard_reject","MDC":"hard_reject","y":"hard_reject"}
    write(OUT/"execution_contract.json",contract); append({"timestamp_utc":utc(),"event":"authorization_recorded","attempt":2})
    single.blank_evidence(); pre=single.build_pre(s); write(OUT/"heartbeat.json",{"stage":"setup_pass","updated_utc":utc(),"pre_fsp":pre["fingerprint"]}); append({"timestamp_utc":utc(),"event":"solver_entered","attempt":2})
    fdtd=single.base._import_lumapi().FDTD(hide=True)
    try:
        fdtd.load(str(PRE)); print("SOLVER_RUN_CALL_ENTERING",flush=True); fdtd.run(); print("SOLVER_RUN_CALL_RETURNED",flush=True); fdtd.save(str(POST))
    finally: fdtd.close()
    post=single.extract(POST)
    if post["fingerprint"] != fp(POST): raise RuntimeError("post-FSP fingerprint changed during read-only extraction")
    batch.write_case(180,s,pre,post,(1,1))
    write(OUT/"attempt_summary.json",{"historical_attempt_count":2,"total_solver_entered":2,"total_solver_completed":1,"latest_attempt_status":"formal_pass","case_status":"formal_pass_after_explicit_authorized_rerun","post_fsp":post["fingerprint"],"result_status":json.loads((batch.case_out(180)/"verification_summary.json").read_text()),"automatic_retry_prohibited":True})
    append({"timestamp_utc":utc(),"event":"formal_pass","attempt":2,"post_fsp":post["fingerprint"]}); write(OUT/"heartbeat.json",{"stage":"formal_pass","updated_utc":utc()})
if __name__ == "__main__": main()
