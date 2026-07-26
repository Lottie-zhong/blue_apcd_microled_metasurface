from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,shutil,socket,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
from lp_b120_j2lm06_stage_d5_y_salvage_anchor_source_forensic_v1 import v121_postsolver_acceptance

R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4");O=R/"outputs";ML=O/"lp_ml_dataset_v1";A=ML/"analysis";P=ML/"plans"
ST=ML/"staging/b120_j2lm06_local_planar_size_jacobian_stage_d5_v2_attempt3_single_y_recovery_lp_ml_schema_v1_21";ROOT=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v2_attempt3_single_y_recovery";SUB=ROOT/"subruns";CAND=ROOT/"candidates";RUN=ROOT/"runtime"
SCRIPT=R/"scripts/lp_b120_j2lm06_stage_d5_single_y_recovery_jacobian_closure_v2.py";SALV=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_failed_x_forensic_v1/salvaged_checkpoints/LP_H500_D5_J2LM06_J2_width_nmP01_x_salvaged.json";TARGET="LP_H500_D5_J2LM06_J2_width_nmP01"
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
old=load(R/"scripts/lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_execute_v1.py","d5old");base,legacy=old.base,old.legacy
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp."+uuid.uuid4().hex);t.write_text(json.dumps(x,indent=2,sort_keys=True,default=str),encoding="utf8")
 with t.open("r+b") as f:os.fsync(f.fileno())
 os.replace(t,p)
def ev(p,s,**kw):
 with Path(p).open("a",encoding="utf8") as f:f.write(json.dumps({"utc":datetime.now(timezone.utc).isoformat(),"state":s,**kw},sort_keys=True,default=str)+"\n");f.flush();os.fsync(f.fileno())
def preflight():
 st=json.loads((A/"b120_j2lm06_stage_d5_offline_recovery_state_v1.json").read_text());sa=json.loads((A/"b120_j2lm06_stage_d5_failed_x_salvage_audit_v1.json").read_text());ct=json.loads((P/"b120_j2lm06_stage_d5_minimal_missing_subrun_execution_contract_v2.json").read_text());z=json.loads(SALV.read_text())
 return {"head":base.git("rev-parse","HEAD")=="1b247e9282fe06f2cc3994600596b0f1a7bc52a0","salvage_sha":sha(SALV)=="aa71ec3fc9ed9ae2e11b44ccf36c88d8744ab417b52402213eb0a16be006623d","salvage_identity":z.get("candidate_id")==TARGET and z.get("input_polarization")=="x" and z.get("checkpoint_acceptance")=="PASS","accepted_11":st.get("formal_accepted")==11 and sa.get("formal_accepted_subruns")==11,"only_y":ct.get("missing_key_set")==[TARGET+"/y"] and ct.get("solver_budget")==1,"target_absent":not ST.exists() and not ROOT.exists()}
def configure():
 old.ROOT,old.SUB,old.CAND,old.RUNTIME,old.ST=ROOT,SUB,CAND,RUN,ST;old.CSVOUT=O/"lp_b120_j2lm06_stage_d5_v2_attempt3_single_y_recovery.csv";old.JSONOUT=O/"lp_b120_j2lm06_stage_d5_v2_attempt3_single_y_recovery.json";old.SCRIPT=SCRIPT;old.configure();old.runtime_config();legacy.POST_SOLVER_ACCEPTANCE=v121_postsolver_acceptance
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--execute",action="store_true");a=ap.parse_args();c=preflight();atomic(A/"b120_j2lm06_stage_d5_attempt3_preflight_accepted_state_v1.json",{"status":"PASS" if all(c.values()) else "FAIL","checks":c,"solver_calls":0});print(json.dumps({"preflight":c,"solver_calls":0}),flush=True)
 if not all(c.values()):return 2
 if not a.execute:return 0
 ST.mkdir(parents=True);ROOT.mkdir();SUB.mkdir();CAND.mkdir();RUN.mkdir();lock=ST/"execution.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,json.dumps({"pid":os.getpid(),"host":socket.gethostname(),"token":uuid.uuid4().hex}).encode());os.close(fd);e=ST/"events.ndjson";ev(e,"PLANNED",candidate_id=TARGET,input_polarization="y");ev(e,"RUNNING",candidate_id=TARGET,input_polarization="y")
 try:
  configure();spec=next(s for s in old.plan_specs()[0] if s["candidate_id"]==TARGET);static=base.static_gate(spec);runtime=legacy.load_runtime_config(R/"configs/runtime.yaml");ev(e,"SOLVER_CALLED",candidate_id=TARGET,input_polarization="y");run=legacy.run_one(runtime,spec,static,"y");p=Path(run.get("checkpoint_path",""))
  if run.get("status")!="PASS" or not p.is_file():ev(e,"FAILED",detail=run);raise RuntimeError("SINGLE_Y_RUN_FAILED")
  cp=json.loads(p.read_text());rowfile=ST/"subrun_records_v1.csv";rows=list(csv.DictReader(rowfile.open(encoding="utf8")));match=[r for r in rows if r.get("subrun_id")==cp["run_id"] and r.get("checkpoint_sha256")==sha(p)]
  ok=cp.get("status")=="PASS" and cp.get("checkpoint_reload")=="PASS" and cp.get("input_basis")=="y" and cp.get("candidate_id")==TARGET and len(match)==1
  if not ok:ev(e,"FAILED",detail={"matcher":len(match),"checkpoint":str(p)});raise RuntimeError("SINGLE_Y_ACCEPTANCE_FAILED")
  ev(e,"CHECKPOINT_WRITTEN",checkpoint=str(p),sha256=sha(p));ev(e,"VALIDATED",matcher_rows=len(match));ev(e,"ACCEPTED",candidate_id=TARGET,input_polarization="y");atomic(A/"b120_j2lm06_stage_d5_attempt3_single_y_acceptance_audit_v1.json",{"status":"PASS","candidate_id":TARGET,"input_polarization":"y","solver_calls":1,"checkpoint_path":str(p),"checkpoint_sha256":sha(p),"formal_row_path":str(rowfile),"exact_one_row_match":True,"weighted_G0":"PASS","normalization":"PASS"});print(json.dumps({"status":"PASS","solver_calls":1,"checkpoint":str(p)}));return 0
 except Exception as x:
  atomic(A/"b120_j2lm06_stage_d5_attempt3_single_y_acceptance_audit_v1.json",{"status":"FAIL","solver_calls":1,"exception_type":type(x).__name__,"exception_message":str(x)});raise
 finally:
  shutil.rmtree(RUN,ignore_errors=True)
  if lock.exists():lock.rename(ST/("execution.lock.released."+datetime.now().strftime("%Y%m%dT%H%M%S")))
if __name__=="__main__":raise SystemExit(main())
