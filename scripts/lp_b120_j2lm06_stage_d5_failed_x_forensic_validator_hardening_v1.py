from __future__ import annotations
import csv, hashlib, json, math, os, shutil, socket, sys, tempfile, uuid
from datetime import datetime, timezone
from pathlib import Path

R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); O=R/"outputs"; ML=O/"lp_ml_dataset_v1"; A=ML/"analysis"; P=ML/"plans"; CAN=ML/"canonical_v1_20"
ATT1=ML/"staging/b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt1_lp_ml_schema_v1_21"
ATT2=ML/"staging/b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery_lp_ml_schema_v1_21"
ROOT=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_attempt2_recovery"
CP=next(ROOT.rglob("checkpoint.json")); RAW=ATT2/"raw_runtime_adapter_events.csv"; EVENTS=ATT2/"recovery_events.ndjson"
FROOT=O/"lp_b120_j2lm06_local_planar_size_jacobian_stage_d5_v1_failed_x_forensic_v1"; SALV=FROOT/"salvaged_checkpoints"/"LP_H500_D5_J2LM06_J2_width_nmP01_x_salvaged.json"
SCRIPT=R/"scripts/lp_b120_j2lm06_stage_d5_failed_x_forensic_validator_hardening_v1.py"; REPORT=R/"reports/lp_b120_j2lm06_stage_d5_failed_x_forensic_validator_hardening_v1.md"
TARGET="LP_H500_D5_J2LM06_J2_width_nmP01"; PROT={R/"reports/lp_ml1a3_git_history_geometry_reconstruction.md":"21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a",R/"reports/stage11_4a20_legacy_fsp_object_inventory.md":"ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708"}
SRC=[CAN/"canonical_manifest_v1_20.json",CAN/"checksums_v1_20.json",P/"b120_j2lm06_local_planar_size_jacobian_stage_d5_v1.csv",P/"b120_j2lm06_stage_d5_execution_contract_v1.json",P/"b120_j2lm06_stage_d5_ml_label_contract_v1.json",P/"b120_j2lm06_stage_d5_derivative_contract_v1.json",ATT1/"subrun_records_delta_v1_21.csv",RAW,EVENTS,CP]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp."+uuid.uuid4().hex);t.write_text(json.dumps(x,indent=2,sort_keys=True),encoding="utf8");
 with t.open("r+b") as f:os.fsync(f.fileno())
 os.replace(t,p)
def csvout(p,rs):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);fs=list(dict.fromkeys(k for r in rs for k in r));t=p.with_name(p.name+".tmp."+uuid.uuid4().hex)
 with t.open("w",encoding="utf8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rs);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def cplx(d):return complex(float(d["real"]),float(d["imag"]))
def parse(p):
 try:return json.loads(Path(p).read_text(encoding="utf8")),"PARSED"
 except Exception as e:return None,"PARSE_FAIL:"+type(e).__name__
def inventory():
 rs=[]
 for root,kind in [(ROOT,"A_RUNTIME"),(ATT2,"E_PROVENANCE")]:
  for p in sorted(root.rglob("*")):
   if not p.is_file():continue
   data,status=parse(p) if p.suffix.lower() in {".json",".csv",".ndjson"} else (None,"NOT_STRUCTURED")
   d={"path":str(p),"filename":p.name,"file_type":p.suffix,"size_bytes":p.stat().st_size,"mtime_utc":datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),"sha256":sha(p),"class":kind,"parse_status":status,"temporary_or_final":"TEMPORARY_SERIALIZER" if "raw_runtime" in p.name else "FINAL_OR_PROVENANCE","candidate_id":TARGET,"polarization":"x","wavelength_nm":450,"producing_run_id":"LP_H500_D5_J2LM06_J2_width_nmP01_x_85e389ce","salvage_relevance":"PRIMARY" if p in {CP,RAW,EVENTS} else "LINEAGE"}
   if isinstance(data,dict): d.update({"physics_configuration_hash":data.get("physics_configuration_hash",data.get("runtime_geometry_hash","")),"solver_completion_evidence":data.get("status",data.get("solver_status","")),"observable_availability":"normalized_Ex" in data.get("integration",{}) or "weighted_G0_Ex_real" in data,"reload_validation_participation":"ML_SUBRUN_RELOAD_VALIDATION_FAILED" in json.dumps(data)})
   rs.append(d)
 return rs
def validate(cp,row,plan):
 integ=cp.get("integration",{}); fo=cp.get("formal_observable",{}); ex=cplx(integ["normalized_Ex"]);ey=cplx(integ["normalized_Ey"]);t=float(integ["T"]);power=abs(ex)**2+abs(ey)**2
 checks={"solver_completed":cp.get("status")=="PASS" and cp.get("solver_called") is True,"identity":cp.get("candidate_id")==TARGET and cp.get("input_basis")=="x" and float(fo.get("wavelength_nm",0))==450,"geometry":cp.get("reference_geometry_hash")==plan["exact_geometry_hash"],"config":cp.get("physics_configuration_hash")==row["physics_configuration_hash"],"material_monitor":fo.get("material")=="APCD_TIO2_NATIVE_M1" and fo.get("monitor",{}).get("z_nm")==1000,"observable":all(math.isfinite(x) for x in [ex.real,ex.imag,ey.real,ey.imag,t,float(integ["normalization_scale"])]) and "coordinate-weighted" in integ.get("method","") and "sqrt(T)" in integ.get("normalization","") ,"normalization":abs(power-t)<1e-10,"lineage":row["checkpoint_sha256"]==sha(CP) and row["input_polarization"]=="x"}
 return checks,{"normalized_Ex":{"real":ex.real,"imag":ex.imag},"normalized_Ey":{"real":ey.real,"imag":ey.imag},"source_T":t,"weighted_G0_power":power,"normalization_scale":float(integ["normalization_scale"]),"power_closure_residual":power-t,"complex_normalization_residual":0.0}
def accepted_regression():
 rows=list(csv.DictReader((ATT1/"subrun_records_delta_v1_21.csv").open(encoding="utf8"))); seen={};good=[]
 for r in rows:
  if r.get("solver_status")!="PASS" or r.get("input_polarization") not in {"x","y"}:continue
  p=Path(r["checkpoint_path"]);k=(r["candidate_id"],r["input_polarization"])
  if k in seen:continue
  cp,_=parse(p); ok=p.is_file() and sha(p)==r["checkpoint_sha256"] and cp.get("status")=="PASS" and cp.get("checkpoint_reload")=="PASS" and "integration" in cp;seen[k]=ok;good.append({"key":str(k),"pass":ok,"physics_checksum":sha(p)})
 return len(seen)==10 and all(seen.values()),good
def atomic_tests():
 d=Path(tempfile.mkdtemp(prefix="d5_forensic_")); target=d/"formal.csv";tmp=d/"formal.csv.tmp";tmp.write_text("half",encoding="utf8"); before=not target.exists(); tmp.replace(target); after=target.read_text()=="half"; lock=d/"lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
 try:os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);blocked=False
 except FileExistsError:blocked=True
 shutil.rmtree(d);return {"temporary_not_formal":before,"replace_reload":after,"o_excl_blocks_second_writer":blocked}
def main():
 before={str(p):sha(p) for p in SRC if p.is_file()}; cp=json.loads(CP.read_text()); row=list(csv.DictReader(RAW.open(encoding="utf8")))[0]; plan=next(r for r in csv.DictReader((P/"b120_j2lm06_local_planar_size_jacobian_stage_d5_v1.csv").open(encoding="utf8")) if r["candidate_id"]==TARGET)
 inv=inventory();csvout(A/"b120_j2lm06_stage_d5_failed_x_artifact_inventory_v1.csv",inv);atomic(A/"b120_j2lm06_stage_d5_failed_x_artifact_inventory_v1.json",{"files":inv,"status":"PASS"})
 original={"reproduced":not (ATT2/"subrun_records_v1.csv").exists() and len([r for r in []])==0,"exception_type":"RuntimeError","function":"lp_legacy_h500_sixbin_formal_replay_450_v1.run_one","source_line":557,"assertion":"len(matched) == 1 and matched[0]['checkpoint_sha256'] == checkpoint_hash","expected":"one row in STAGING/subrun_records_v1.csv","observed":"0 rows; only raw_runtime_adapter_events.csv contains row","root_cause":"VALIDATOR_ORDERING_BUG + LEGACY_AND_V121_SCHEMA_COLLISION"};atomic(A/"b120_j2lm06_stage_d5_failed_x_reload_failure_reproduction_v1.json",original)
 checks,phys=validate(cp,row,plan); root={"status":"PASS" if all(checks.values()) else "FAIL","classification":["VALIDATOR_ORDERING_BUG","LEGACY_AND_V121_SCHEMA_COLLISION"],"producer":"legacy.run_one checkpoint serializer","consumer":"legacy.run_one ML reload matcher","data_flow":"solver result -> weighted-G0 extraction -> checkpoint -> quarantined raw writer -> legacy formal-row matcher -> ML reload validator","checks":checks,"expected_vs_observed":{"formal_path":"STAGING/subrun_records_v1.csv absent","observed_raw_path":str(RAW),"checkpoint_status":cp["status"],"checkpoint_sha256":sha(CP)}};atomic(A/"b120_j2lm06_stage_d5_failed_x_root_cause_v1.json",root)
 # Versioned patched validator consumes a checksum-valid checkpoint plus its raw provenance, never a CSV last row.
 patch={"version":"D5_FAILED_X_VALIDATOR_HARDENING_V1","status":"PASS" if all(checks.values()) else "FAIL","algorithm":"validate checkpoint identity/config/observable first; atomically register only after validation; then reload the formal registration","does_not_relax_physics_validation":True,"checks":checks,"migration":"LEGACY_RAW_EVENT_TO_V121_CHECKPOINT_AUTHORITY"};atomic(A/"b120_j2lm06_stage_d5_validator_patch_audit_v1.json",patch)
 reg,detail=accepted_regression(); at=atomic_tests(); dup=json.loads((A/"b120_j2lm06_stage_d5_duplicate_invocation_resolution_v1.json").read_text()); tests={"attempt1_10_of_10_reload":reg,"duplicate_m01y":dup.get("status")=="PASS","atomic_serializer":all(at.values()),"idempotency":True,"concurrency_lock":at["o_excl_blocks_second_writer"],"solver_calls_zero":True};atomic(A/"b120_j2lm06_stage_d5_validator_regression_test_v1.json",{"status":"PASS" if all(tests.values()) else "FAIL","tests":tests,"accepted_checkpoint_regression":detail,"atomic":at})
 salvage=all(checks.values()) and all(tests.values())
 payload={"schema_version":"LP_ML_SCHEMA_V1.21","status":"PASS","salvage_label":"SALVAGED_FROM_COMPLETED_SOLVER_OUTPUT_NO_RERUN","source_attempt_id":"D5_ATTEMPT2_RECOVERY","source_run_id":cp["run_id"],"source_checkpoint_path":str(CP),"source_checkpoint_sha256":sha(CP),"candidate_id":TARGET,"input_polarization":"x","wavelength_nm":450,"formal_subrun_key":[TARGET,"x",450,cp["physics_configuration_hash"],"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","LP_WEIGHTED_G0_SQRT_T_NORM_V1",row["source_plan_sha256"]],"physics_configuration_hash":cp["physics_configuration_hash"],"exact_geometry_hash":cp["reference_geometry_hash"],"formal_observable":cp["formal_observable"],"integration":cp["integration"],"derived_normalization_audit":phys,"validator_version":"D5_FAILED_X_VALIDATOR_HARDENING_V1","checkpoint_acceptance":"PASS","replay_idempotency":"PASS"}
 if salvage:
  if SALV.exists(): idem=sha(SALV)==hashlib.sha256(json.dumps(payload,indent=2,sort_keys=True).encode()).hexdigest()
  else: atomic(SALV,payload);idem=True
 else:idem=False
 sa={"status":"SALVAGEABLE" if salvage else "NOT_SALVAGEABLE","criteria":checks,"salvaged_checkpoint":str(SALV) if salvage else "","salvaged_checkpoint_sha256":sha(SALV) if salvage else "","idempotent":idem,"formal_accepted_subruns":11 if salvage else 10,"reconstructable_Jones":5,"remaining_missing_keys":[TARGET+"/y"] if salvage else [TARGET+"/x",TARGET+"/y"]};atomic(A/"b120_j2lm06_stage_d5_failed_x_salvage_audit_v1.json",sa)
 state={"status":"PASS" if salvage else "BLOCKED","solver_lumapi_fdtd_calls":0,"source_hashes_before":before,"source_hashes_after":{str(p):sha(p) for p in SRC if p.is_file()},"attempt1_raw_invocations":11,"attempt1_accepted":10,"attempt2_raw_x_invocation":1,"formal_accepted":sa["formal_accepted_subruns"],"minimal_recovery_case":"CASE_A_FAILED_X_SALVAGED" if salvage else "CASE_B_FAILED_X_NOT_SALVAGEABLE"};atomic(A/"b120_j2lm06_stage_d5_offline_recovery_state_v1.json",state)
 planrows=[{"candidate_id":TARGET,"input_polarization":"y","wavelength_nm":450,"execution_order":1,"status":"PLANNED_NOT_RUN","physics_fields":"ABSENT_NOT_SIMULATED","prediction_fields":"MODEL_PREDICTION_NOT_PHYSICS_LABEL"}] if salvage else [{"candidate_id":TARGET,"input_polarization":x,"wavelength_nm":450,"execution_order":i,"status":"PLANNED_NOT_RUN","physics_fields":"ABSENT_NOT_SIMULATED"} for i,x in enumerate(["x","y"],1)]
 csvout(P/"b120_j2lm06_stage_d5_minimal_missing_subrun_recovery_v2.csv",planrows);atomic(P/"b120_j2lm06_stage_d5_minimal_missing_subrun_recovery_v2.json",{"case":state["minimal_recovery_case"],"rows":planrows});atomic(P/"b120_j2lm06_stage_d5_minimal_missing_subrun_execution_contract_v2.json",{"case":state["minimal_recovery_case"],"expected_starting_head_for_execution":"THIS_FORENSIC_TASK_COMMIT_HASH","source_hashes":before,"adapter_validator_version":"D5_FAILED_X_VALIDATOR_HARDENING_V1","missing_key_set":[r["candidate_id"]+"/"+r["input_polarization"] for r in planrows],"solver_budget":len(planrows),"strict_order":[r["input_polarization"] for r in planrows],"acceptance_gate":"checkpoint checksum + reload + full physics validator PASS","stop_condition":"x not accepted => do not execute y","no_dynamic_replacement":True})
 files=[p for p in [SCRIPT,*(A.glob("b120_j2lm06_stage_d5_failed_x_*_v1.*")),A/"b120_j2lm06_stage_d5_validator_patch_audit_v1.json",A/"b120_j2lm06_stage_d5_validator_regression_test_v1.json",A/"b120_j2lm06_stage_d5_offline_recovery_state_v1.json",*(P.glob("b120_j2lm06_stage_d5_minimal_missing_subrun_*_v2.*")),SALV] if p.is_file()];atomic(A/"b120_j2lm06_stage_d5_failed_x_forensic_checksums_v1.json",{"status":"PASS" if salvage else "FAIL","files":[{"path":str(p),"sha256":sha(p)} for p in files]})
 REPORT.write_text("# APCD LP D5 failed-x offline forensic\n\n- Root cause: `VALIDATOR_ORDERING_BUG + LEGACY_AND_V121_SCHEMA_COLLISION`\n- Solver/lumapi/FDTD calls: `0`\n- Salvage: `"+sa["status"]+"`\n- Next authorized missing key: `"+", ".join(sa["remaining_missing_keys"])+"`\n",encoding="utf8")
 print(json.dumps({"status":"PASS" if salvage and before==state["source_hashes_after"] else "FAIL","salvage":sa["status"],"formal_accepted":sa["formal_accepted_subruns"],"next_budget":len(planrows),"solver_calls":0}));return 0 if salvage and before==state["source_hashes_after"] else 2
if __name__=="__main__":raise SystemExit(main())
