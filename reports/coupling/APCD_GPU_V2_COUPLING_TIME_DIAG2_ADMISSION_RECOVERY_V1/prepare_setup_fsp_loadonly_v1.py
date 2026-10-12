from __future__ import annotations
import hashlib, importlib.util, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT = ROOT / "reports/coupling/APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1"
RUNTIME = Path(r"D:\apcd_runtime\coupling_v3_time_diag2_v1\candidate_setups")
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
BUILDER_PATH = ROOT / "scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py"
VALIDATOR_PATH = ROOT / "scripts/coupling_ml/validate_pw_k6_5nm_full_period_prefsp_v1.py"
INVENTORY_PATH = ROOT / "reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/science_admission_setup_review_v1/V3_SOURCE_SETUP_INVENTORY.json"
SOURCES = [
 {"case_id":"K6V3_TIME_DIAG2_A1_5NM_6PS","source_case_id":"K6V3_NUM_REPEAT_A1","attempt_id":"attempt_001","source_fsp":Path(r"D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup\K6V3_NUM_REPEAT_A1\attempt_001\pre.fsp"),"source_sha256":"0e6e522141ddbd0f9a4323cdc470293fd485af9493257a4ccd166383f6a62bb2","spec_path":Path(r"D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup\K6V3_NUM_REPEAT_A1\attempt_001\setup_spec.json"),"source_proof_sha256":"528d8b156a18cea2db65a094678a3df14003fd70f939998590b96f17250caa95","ordered_D_nm":[120,160,165,175,160,195]},
 {"case_id":"K6V3_TIME_DIAG2_A2_5NM_6PS","source_case_id":"K6V3_NUM_REPEAT_A2","attempt_id":"attempt_001","source_fsp":Path(r"D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup\K6V3_NUM_REPEAT_A2\attempt_001\pre.fsp"),"source_sha256":"540ec80315bcec60619afb85f60dc894d46e40bffd87d5f8c6fb38b48a2651d1","spec_path":Path(r"D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup\K6V3_NUM_REPEAT_A2\attempt_001\setup_spec.json"),"source_proof_sha256":"715c2c77208ef2de2af34bd0da72aae68878a1f8a1d99b5ddbc2bef57c751ac5","ordered_D_nm":[210,115,175,115,180,125]},
]

def sha_file(p: Path) -> str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()

def write_json(p: Path,obj):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")

def load_module(name,path):
 sp=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def main():
 if not OUT.is_dir(): raise RuntimeError("preregistered report package missing")
 if not API.is_dir(): raise RuntimeError("pinned Lumerical API path missing: "+str(API))
 if str(API) not in sys.path: sys.path.insert(0,str(API))
 import lumapi
 validator=load_module("diag2_validator",VALIDATOR_PATH)
 inventory=json.loads(INVENTORY_PATH.read_text(encoding="utf-8-sig"))
 result=[]
 for row in SOURCES:
  source=row["source_fsp"]; spec_path=row["spec_path"]
  if not source.is_file() or sha_file(source)!=row["source_sha256"]: raise RuntimeError("source FSP missing or SHA mismatch: "+str(source))
  if not spec_path.is_file(): raise RuntimeError("source spec missing: "+str(spec_path))
  source_row=next(x for x in inventory["cases"] if x["case_id"]==row["source_case_id"] and x["attempt_id"]==row["attempt_id"])
  proof_path=Path(source_row["artifacts"]["load_proof"]["path"]); proof_sha=source_row["artifacts"]["load_proof"]["sha256"]
  if sha_file(proof_path)!=row["source_proof_sha256"] or proof_sha!=row["source_proof_sha256"]: raise RuntimeError("prior source proof SHA mismatch")
  old=proof_path.read_text(encoding="utf-8-sig"); proof=json.loads(old); base_readback=proof["canonical_readback"]
  if base_readback["fsp_sha256"]!=row["source_sha256"] or base_readback["fdtd"]["simulation_time_s"]!=3e-12 or base_readback["fdtd"]["auto_shutoff_min"]!=1e-6: raise RuntimeError("source readback not 3 ps / 1e-6")
  spec=json.loads(spec_path.read_text(encoding="utf-8-sig"))
  if spec["ordered_D_nm"]!=row["ordered_D_nm"]: raise RuntimeError("source geometry mismatch")
  target=RUNTIME/row["case_id"]/row["attempt_id"]/"pre.fsp"
  if target.exists(): raise FileExistsError("refusing overwrite: "+str(target))
  target.parent.mkdir(parents=True,exist_ok=True)
  started=datetime.now(timezone.utc).isoformat(); t0=time.perf_counter()
  fd=lumapi.FDTD(str(source),hide=True)
  try:
   before=float(fd.getnamed("FDTD","simulation time")); shut=float(fd.getnamed("FDTD","auto shutoff min"))
   if before!=3e-12 or shut!=1e-6: raise RuntimeError("source properties changed from pinned 3 ps/1e-6")
   fd.setnamed("FDTD","simulation time",6e-12)
   after=float(fd.getnamed("FDTD","simulation time"))
   if after!=6e-12: raise RuntimeError("failed to set 6 ps maximum time")
   fd.save(str(target))
  finally:
   fd.close()
  source_after=sha_file(source)
  if source_after!=row["source_sha256"]: raise RuntimeError("source FSP changed during setup save")
  if not target.is_file(): raise RuntimeError("candidate FSP not saved")
  candidate_spec=dict(spec); candidate_spec["case_id"]=row["case_id"]; candidate_spec["attempt_id"]=row["attempt_id"]
  readback=validator.inspect_fsp(target,candidate_spec)
  semantics=validator.compare_semantics(base_readback,readback)
  expected_errors=validator.validate_expected(readback,candidate_spec)
  expected_error_list=expected_errors["errors"]
  allowed=["FDTD simulation_time_s mismatch"]
  mesh=readback["meshes"].get("NP_DERIVED_BASELINE_N2",{}).get("step_nm")
  if semantics["status"]!="PASS": raise RuntimeError("semantic readback mismatch: "+json.dumps(semantics["mismatches"]))
  if expected_error_list!=allowed: raise RuntimeError("unexpected frozen-validator mismatch list: "+repr(expected_error_list))
  if readback["fdtd"]["simulation_time_s"]!=6e-12 or readback["fdtd"]["auto_shutoff_min"]!=1e-6: raise RuntimeError("fresh LOAD temporal readback mismatch")
  if mesh!=[5.0,5.0,5.0]: raise RuntimeError("5 nm core mesh override mismatch: "+repr(mesh))
  if readback["run_called"] is not False or readback["save_called_by_validator"] is not False: raise RuntimeError("unexpected validator operation marker")
  elapsed=time.perf_counter()-t0
  readback["case_id"]=row["case_id"]
  payload={"schema":"APCD_COUPLING_V3_TIME_DIAG2_FRESH_NATIVE_LOAD_PROOF_V1","status":"SETUP_LOAD_PASS_NOT_GPU_ADMITTED","case_id":row["case_id"],"attempt_id":row["attempt_id"],"dataset_id":"APCD_COUPLING_V3_TIME_DIAG2_V1","role":"TIME_CONVERGENCE_DIAGNOSTIC_ONLY","source_case_id":row["source_case_id"],"anchor_case_id":"K6GDP2_DEV_G001" if row["source_case_id"].endswith("A1") else "K6GDP2_DEV_G004","ordered_D_nm":row["ordered_D_nm"],"source_fsp_path":str(source),"source_fsp_sha256":row["source_sha256"],"source_proof_sha256":row["source_proof_sha256"],"candidate_fsp_path":str(target),"candidate_fsp_sha256":sha_file(target),"source_unchanged":True,"fresh_native_load":True,"fresh_readback":readback,"semantic_comparison_vs_source_proof":semantics,"frozen_3ps_validator_errors_expected_only":["FDTD simulation_time_s mismatch"],"observed_frozen_validator_errors":expected_error_list,"mesh_override_step_nm":mesh,"simulation_time_s":readback["fdtd"]["simulation_time_s"],"auto_shutoff_min":readback["fdtd"]["auto_shutoff_min"],"solver_api_run_called":False,"scientific_entry_count":0,"replay_count":0,"production_admission":False,"lumerical_api_module":lumapi.__file__,"started_utc":started,"elapsed_load_save_seconds":elapsed}
  proof_out=OUT/("A1_SETUP_LOAD_PROOF.json" if row["source_case_id"].endswith("A1") else "A2_SETUP_LOAD_PROOF.json")
  write_json(proof_out,payload); result.append({"case_id":row["case_id"],"candidate_fsp_path":str(target),"candidate_fsp_sha256":sha_file(target),"proof_path":str(proof_out),"proof_sha256":sha_file(proof_out),"elapsed_load_save_seconds":elapsed})
 print(json.dumps({"schema":"APCD_COUPLING_DIAG2_SETUP_PREPARATION_RESULT_V1","status":"PASS_SETUP_ONLY","solver_api_run_calls":0,"scientific_entries":0,"replays":0,"cases":result},indent=2,ensure_ascii=False))

if __name__=="__main__": main()
