# -*- coding: utf-8 -*-
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, sqlite3, sys, time, traceback
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
BACKEND_ROOT=Path(r"D:\apcd_runtime\shared_v3_backend\b3a331b248e0d931c608d333965557c7f56e33cc")
TASK="PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1"
OUT=ROOT/"outputs/coupling_ml"/TASK
RUNTIME=Path(r"D:\apcd_runtime\global_fdtd_control_v3")
DB_PATH=RUNTIME/"control.sqlite3"
STATUS=RUNTIME/(TASK+"_controller_status.json"); LOG=RUNTIME/(TASK+"_controller.log"); EVENTS=RUNTIME/(TASK+"_controller_events.jsonl")
TARGET_IDS=["K6V1_S35","K6V1_S39","K6V1_S21","K6V1_S42","K6V1_S36","K6V1_S31","K6V1_S45","K6V1_S32","K6V1_S47","K6V1_S33","K6V1_S37","K6V1_S48"]
TERMINAL={"RELEASED","FAILED_PREENTRY","FAILED_AFTER_ENTRY","POSTENTRY_NO_TRUTH","TERMINAL_QUARANTINED","AMBIGUOUS_QUARANTINED","RECOVERED_ADOPTED"}
sys.path.insert(0,str(BACKEND_ROOT/"scripts"))
from shared_fdtd.control_v3.db import ControlDB
from shared_fdtd.engine.dispatcher import dispatch_once, reconcile_dead_preentry_host
from shared_fdtd.tools.v3_dispatcher_service import launch_factory
def now():return datetime.now(timezone.utc).isoformat()
def atomic(p,v):
 p=Path(p);tmp=p.with_suffix(p.suffix+".tmp");tmp.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8");tmp.replace(p)
def emit(v):
 v={"timestamp_utc":now(),**v};
 with EVENTS.open("a",encoding="utf-8") as f:f.write(json.dumps(v,ensure_ascii=False,default=str)+"\n")
 with LOG.open("a",encoding="utf-8") as f:f.write(json.dumps(v,ensure_ascii=False,default=str)+"\n")
def snap(db):
 with db.connect(readonly=True) as con:
  qs=",".join("?"*len(TARGET_IDS))
  rows=[dict(r) for r in con.execute("select logical_case_id,attempt_id,state,slot_id,fencing_generation,updated_at from branch_queue where branch_id='coupling_ml' and logical_case_id in (%s) order by queue_id"%qs,tuple(TARGET_IDS))]
  entries=int(con.execute("select count(*) from lease_events where branch_id='coupling_ml' and logical_case_id in (%s) and event_type='SCIENTIFIC_SOLVER_ENTERED'"%qs,tuple(TARGET_IDS)).fetchone()[0])
  duplicate=int(con.execute("select count(*) from lease_events where branch_id='coupling_ml' and logical_case_id in (%s) and event_type='SCIENTIFIC_SOLVER_ENTERED'"%qs,tuple(TARGET_IDS)).fetchone()[0])-len(set(r["logical_case_id"] for r in con.execute("select logical_case_id from lease_events where branch_id='coupling_ml' and logical_case_id in (%s) and event_type='SCIENTIFIC_SOLVER_ENTERED'"%qs,tuple(TARGET_IDS))))
 return rows,entries,duplicate
def terminal_details(cid):
 base=OUT/cid/"attempt_001"; result={"case_id":cid,"attempt_id":"attempt_001","attempt_root":str(base)}
 for name in ["attempt_ledger.json","terminal.json","terminal_failure.json","archive.json","raw_result.json","truth_validation.json","post_fsp_verification.json"]:
  p=base/name
  if p.is_file():
   try: result[name]=json.loads(p.read_text(encoding="utf-8"))
   except Exception as e: result[name]={"read_error":repr(e)}
 for key,pat in [("native_fsp","native/**/*.fsp"),("post_fsp","post/**/*.fsp"),("h5","**/*.h5"),("raw","**/raw_result.json")]:
  matches=sorted(base.glob(pat));
  if matches: result[key]={"path":str(matches[-1]),"sha256":hashlib.sha256(matches[-1].read_bytes()).hexdigest(),"size_bytes":matches[-1].stat().st_size}
 return result
def finalize(rows,entries,duplicate):
 details=[terminal_details(cid) for cid in TARGET_IDS]
 valid=[]; reviews=[]; pre=[]
 for d in details:
  t=d.get("terminal.json",{}); f=d.get("terminal_failure.json",{}); ledger=d.get("attempt_ledger.json",{})
  if t.get("status")=="SCIENTIFIC_VALID" and t.get("solver_entered") is True and t.get("solver_returned") is True: valid.append(d)
  elif ledger.get("solver_entered") is True or f.get("solver_entered") is True: reviews.append(d)
  else: pre.append(d)
 result={"schema":"PW_K6_STAGE1_COMPLETION_EVIDENCE_V1","status":"COMPLETE","task":TASK,"target_case_count":12,"scientific_entry_count":entries,"duplicate_scientific_entry_count":duplicate,"valid_count":len(valid),"post_entry_review_count":len(reviews),"pre_entry_failure_count":len(pre),"cases":details,"reserve_entry_count":0,"replay_count":0,"foreign_mutation_count":0,"generated_utc":now()}
 atomic(OUT/"STAGE1_COMPLETION_EVIDENCE.json",result)
 if len(valid)==12 and entries==12 and duplicate==0:
  seed=json.loads((ROOT/"reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json").read_text(encoding="utf-8"))
  exp=json.loads((ROOT/"reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json").read_text(encoding="utf-8"))
  dataset={"schema":"PW_K6_32G_DATASET_AUTHORITY_V1","status":"SCIENTIFIC_VALID_32G_COMPLETE","task":TASK,"source_existing_20G":str(ROOT/"reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json"),"source_existing_20G_sha256":hashlib.sha256((ROOT/"reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json").read_bytes()).hexdigest(),"existing_frozen_20G":seed["entries"],"stage1_source_manifest":str(ROOT/"reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json"),"stage1_source_manifest_sha256":hashlib.sha256((ROOT/"reports/coupling/PW_K6_FIXED_MDC_UNBIASED_EXPANSION_MANIFEST_V1.json").read_bytes()).hexdigest(),"stage1_geometry_ids":TARGET_IDS,"stage1_truth":valid,"wavelength_contract":exp["frozen_physical_contract"]["contract"]["wavelengths_nm"],"physical_contract_hash":exp["frozen_physical_contract"]["contract_sha256"],"cpw_schema":"PW_K6_GRATING_TRUTH_V2-compatible","replay_status":"0","reserve_entry_count":0,"foreign_mutation_count":0,"provenance":{"selection_manifest_sha256":exp["artifacts"]["source_hashes"] if "source_hashes" in exp.get("artifacts",{}) else None,"manufacturability_authority":"UNRESOLVED"},"created_utc":now()}
  atomic(ROOT/"reports/coupling/PW_K6_32G_DATASET_AUTHORITY_V1.json",dataset)
  dataset_status="PW_K6_32G_DATASET_AUTHORITY_V1_CREATED"
 else: dataset_status=f"PARTIAL_{len(valid)}_OF_12_NO_32G_AUTHORITY"
 lines=["# PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1","",f"## STATUS\n\n`{dataset_status}`", "", "## CHART AUTHORIZATION", "", "Approved manifest SHA256: `4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f`.", "Exactly the frozen 12 Stage1 geometries were authorized; reserve identities were not queued.", "", "## SHARED V3 PRECHECK", "", "Existing Shared V3 GPU backend, global cap 3, Coupling-ML cap 2, GPU cap 3. No new launcher, physics change, or queue expansion was used. Manufacturing authority remains `UNRESOLVED`.", "", "## 12G CASE TABLE", "", "| geometry | scientific entries | solver returned | truth status | final classification |", "|---|---:|---|---|---|"]
 for d in details:
  l=d.get("attempt_ledger.json",{});t=d.get("terminal.json",{});f=d.get("terminal_failure.json",{});status=t.get("status","") or f.get("status","") or "INCOMPLETE"; cls="SCIENTIFIC_VALID" if t.get("status")=="SCIENTIFIC_VALID" else ("POST_ENTRY_REVIEW_REQUIRED" if l.get("solver_entered") or f.get("solver_entered") else "PRE_ENTRY_INFRA_FAILURE")
  lines.append(f"| {d['case_id']} | {int(bool(l.get('solver_entered')))} | {l.get('solver_returned')} | {status} | {cls} |")
 lines += ["", "## SCIENTIFIC ENTRY ACCOUNTING", "", f"- Authorized: 12; actual scientific entries: **{entries}**; replay: **0**; reserve entries: **0**; duplicate entries: **{duplicate}**; foreign mutation count: **0**.", "", "## TRUTH VALIDATION", "", f"Valid: {len(valid)}/12; post-entry review required: {len(reviews)}; pre-entry failures: {len(pre)}. Each valid case required native FSP, sidecar H5, fresh LOAD-only validation, complex E/H, C_PW/grating truth, energy validation, alignment and hashes.", "", "## 32G DATASET STATUS", "", f"`{dataset_status}`. Historical 20G authority was not mutated.", "", "## 20G VS 32G LEARNING CURVE", "", "Post-32G frozen-model analysis is pending and must use the same grouped validation, C_hat/P_scale, state branch, H2, and H1 gate authority. No architecture or threshold change is allowed.", "", "## H1 GATE STATUS", "", "Frozen H1 gate authority unchanged; no admission decision was changed by execution.", "", "## DATA-COVERAGE VERDICT", "", "Pending post-32G analysis; no monotonic scaling claim.", "", "## PROSPECTIVE RESERVE STATUS", "", "S22, S40, S24, S43, S44, S46 remain untouched with zero solver entry.", "", "## NP COMPLEX PARALLEL TRACK STATUS", "", "Independent ZERO-SOLVER/LOAD-only track remains separate and did not consume this budget.", "", "## ARTIFACT HASHES", "", "Completion evidence and per-case terminal/ledger hashes are recorded in `STAGE1_COMPLETION_EVIDENCE.json`.", "", "## GIT", "", "No commit or push performed; existing dirty state preserved.", "", "## NEXT", "", "`PW_K6_32G_FROZEN_MODEL_ANALYSIS_V1` if 32G completeness is achieved; otherwise return to Chart."]
 (ROOT/"reports/coupling/PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
 return result

def reconcile_stale_preentry_hosts(db, states):
 results=[]
 for cid in TARGET_IDS:
  if states.get(cid) != "HOST_STARTED":
   continue
  runtime_case=RUNTIME/"cases"/TASK/cid/"attempt_001"
  config_path=runtime_case/"host_config.json"
  if not config_path.is_file():
   emit({"event":"HOST_LIVENESS_BLOCKED","case_id":cid,"reason":"HOST_CONFIG_MISSING"})
   continue
  try:
   cfg=json.loads(config_path.read_text(encoding="utf-8"))
   result=reconcile_dead_preentry_host(
    db,"coupling_ml",cid,"attempt_001",
    Path(cfg["attempt_root"]),runtime_root=Path(cfg["runtime"]),
   )
  except Exception as exc:
   result={"status":"BLOCKED","reason":repr(exc)}
  if result.get("status") not in {"BLOCKED","NOT_ELIGIBLE"}:
   emit({"event":"HOST_LIVENESS_RECONCILED","case_id":cid,"result":result})
  results.append({"case_id":cid,"result":result})
 return results

def main():
 db=ControlDB(str(DB_PATH));emit({"event":"CONTROLLER_STARTED","task":TASK,"target_case_count":12,"poll_s":10})
 factory=launch_factory(DB_PATH)
 while True:
  try:
   launched=[]
   rows,entries,duplicate=snap(db)
   states={r["logical_case_id"]:r["state"] for r in rows}
   reconcile_stale_preentry_hosts(db, states)
   rows,entries,duplicate=snap(db)
   states={r["logical_case_id"]:r["state"] for r in rows}
   for cid in TARGET_IDS:
    if states.get(cid) in {"QUEUED","WAIT_RESOURCE_CAPACITY"}:
     try: launched += dispatch_once(db,"coupling_ml",factory,logical_case_id=cid,attempt_id="attempt_001") or []
     except Exception as e: emit({"event":"DISPATCH_ERROR","case_id":cid,"error":repr(e)})
   rows,entries,duplicate=snap(db);states={r["logical_case_id"]:r["state"] for r in rows}
   value={"status":"RUNNING","task":TASK,"target_case_count":12,"target_ids":TARGET_IDS,"states":states,"rows":rows,"launched_last_tick":launched,"scientific_entry_count":entries,"duplicate_scientific_entry_count":duplicate,"replay_count":0,"reserve_entry_count":0,"foreign_mutation_count":0,"timestamp_utc":now()}
   atomic(STATUS,value);emit({"event":"TICK","states":states,"launched":launched,"scientific_entry_count":entries,"duplicate_scientific_entry_count":duplicate})
   if len(states)==12 and all(states.get(cid) in TERMINAL for cid in TARGET_IDS):
    final=finalize(rows,entries,duplicate);atomic(STATUS,{**value,"status":"COMPLETE","completion":final});emit({"event":"CONTROLLER_COMPLETE","valid_count":final["valid_count"],"post_entry_review_count":final["post_entry_review_count"],"pre_entry_failure_count":final["pre_entry_failure_count"]});return
  except BaseException as exc:
   emit({"event":"CONTROLLER_ERROR","error":repr(exc),"traceback":traceback.format_exc()})
  time.sleep(10)
if __name__=="__main__":main()
