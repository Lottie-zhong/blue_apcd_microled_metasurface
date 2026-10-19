
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np

ML=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SOURCE=Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
BASE_PATH=SOURCE/r"scripts\run_mdc_hf_surrogate_v3_al64_joint_profile_v1.py"
MONITOR_PATH=SOURCE/r"scripts\mdc_fdtd_2d_monitor_contract_v1.py"
NATIVE_PATH=SOURCE/r"scripts\run_mdc_native_m1_2d_dipole_device_comparison_v1.py"
sys.path.insert(0,str(SOURCE/"scripts"))
spec=importlib.util.spec_from_file_location("frozen_al64_builder",BASE_PATH)
base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
if not hasattr(np,"trapezoid"): np.trapezoid=np.trapz

def now(): return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic_json(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_name(p.name+".tmp")
 tmp.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+chr(10),encoding="utf-8"); os.replace(tmp,p)
def ps_json(cmd):
 r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,encoding="utf-8",errors="replace")
 try:x=json.loads(r.stdout) if r.stdout.strip() else []
 except Exception:x=[]
 return x if isinstance(x,list) else [x]
def resource_snapshot(admitted):
 procs=ps_json("Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine,CreationDate | ConvertTo-Json -Compress")
 names={"fluent.exe","cx2510.exe","fl2510.exe","smpd.exe"}
 fluent=[p for p in procs if str(p.get("Name","")).lower() in names or str(p.get("Name","")).lower().startswith("fl_mpi")]
 fdtd=[p for p in procs if str(p.get("Name","")).lower().startswith("fdtd-engine") or str(p.get("Name","")).lower()=="fdtd-solutions.exe"]
 heavy=[p for p in procs if any(x in (str(p.get("Name",""))+" "+str(p.get("CommandLine",""))).lower() for x in ["matlab","comsol","lumerical","fdtd","fluent","mathematica","ansysedt"]) and p not in fluent and p not in fdtd]
 oi=ps_json("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress")[0]
 ci=ps_json("Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress")[0]
 total=float(oi.get("TotalVisibleMemorySize") or 0)/1024/1024; free=float(oi.get("FreePhysicalMemory") or 0)/1024/1024; logical=int(os.cpu_count() or 0); cpu=float(ci.get("PercentProcessorTime") or 0)
 regpath=Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json"); reg={}
 if regpath.exists():
  try:reg=json.loads(regpath.read_text(encoding="utf-8"))
  except Exception:reg={}
 active=[]
 if isinstance(reg,dict):
  for key in ["active_slots","active","leases","entries","jobs","records"]:
   v=reg.get(key)
   if isinstance(v,list):active.extend(v)
   elif isinstance(v,dict):active.extend(v.values())
 def active_item(x):
  s=json.dumps(x,ensure_ascii=False).lower()
  return any(k in s for k in ["active","running","entered"]) and not any(k in s for k in ["complete","finished","closed","released"])
 active=[x for x in active if active_item(x)]
 cap=3; existing=max(len(active),len(fdtd)) if active else len(fdtd); slots_left=max(0,cap-existing); threads=12
 projected=cpu+slots_left*threads/logical*100 if logical else 100
 cpu_supported=3 if logical>=threads and projected<=80 else max(0,min(3,int((80-cpu)*logical/(threads*100)))) if logical else 0
 reserve=32.0; mem_supported=3 if free-slots_left*reserve>=reserve else max(0,min(3,int(free/reserve)-1))
 supported=max(0,min(slots_left,cpu_supported,mem_supported)); safe=min(max(0,cap-len(active)),supported)
 return {"timestamp_utc":now(),"authority":"RESOURCE-AWARE MAXIMUM SAFE SLOT UTILIZATION","fluent_detected":bool(fluent),"fluent_process_count":len(fluent),"fluent_processes":fluent,"system_logical_cpu":logical,"system_cpu_utilization_percent_total":cpu,"available_memory_before_admission":free,"available_memory_before_admission_gib":free,"total_physical_memory_gib":total,"active_apcd_fdtd_slots_before_admission":len(active),"observed_fdtd_engine_processes_before_admission":len(fdtd),"other_heavy_scientific_process_count":len(heavy),"other_heavy_scientific_processes":heavy,"production_hard_cap":cap,"job_slot_contract":"12 MPI x 1 thread = 1 APCD FDTD slot","resource_policy":{"projected_cpu_ceiling_percent":80.0,"per_slot_reserved_memory_gib":reserve,"cpu_headroom_supported_slots":cpu_supported,"memory_headroom_supported_slots":mem_supported,"projected_cpu_percent_at_cap":projected},"resource_headroom_supported_slots":supported,"safe_new_slots":safe,"admitted_fdtd_slots":admitted,"fluent_protection":"NO_TERMINATE_NO_PAUSE_NO_AFFINITY_CHANGE_NO_PRIORITY_CHANGE_NO_INTERFERENCE"}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--manifest",required=True); args=ap.parse_args()
 manifest_path=Path(args.manifest); m=json.loads(manifest_path.read_text(encoding="utf-8"))
 if m["case_id"]!="MDC_BOTTOM_X_TARGET_GEOMETRY_445_455_V1" or not m["pilot"]: raise RuntimeError("pilot_manifest_identity_mismatch")
 if m["solver_entered"] or m["attempt_budget"]!=1 or m["retry_allowed"]: raise RuntimeError("pilot_manifest_not_fresh")
 if m["exact_contract"]["geometry_hash"]!="2743ba872a6865519e555f99131220415afb076d653db11f1fe2ef658286c7d8": raise RuntimeError("pilot_geometry_hash_mismatch")
 case_dir=Path(m["output_root"]); case_dir.mkdir(parents=True,exist_ok=True)
 pre=case_dir/"attempt_1__pre.fsp"; post=case_dir/"attempt_1__post.fsp"; npz=case_dir/"attempt_1__raw.npz"
 if (case_dir/"M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json").exists() or npz.exists() or (case_dir/"case_result.json").exists(): raise RuntimeError("pilot_output_exists_or_solver_already_entered")
 seq=[(str(x[0]),float(x[1])) for x in m["exact_contract"]["geometry_sequence_nm"]]
 structure={"structure_key":m["exact_contract"]["geometry_hash"][:16],"structure_id":"MDC_TARGET_GEOMETRY_2743","kind":"target_mdc_stack","sequence":seq,"geometry_hash":m["exact_contract"]["geometry_hash"],"total_thickness_nm":sum(x[1] for x in seq),"layer_count":len(seq),"realization_hash":hashlib.sha256(json.dumps({"geometry_hash":m["exact_contract"]["geometry_hash"],"sequence":seq,"material_policy":"MDC_NATIVE_M1"},sort_keys=True,separators=(",",":")).encode()).hexdigest()}
 case={"case_id":m["case_id"],"case_hash":m["physical_contract_hash"],"geometry_hash":m["exact_contract"]["geometry_hash"],"geometry_id":"MDC_TARGET_GEOMETRY_2743","source_position":m["exact_contract"]["source_position"],"source_position_nm":str(m["exact_contract"]["source_z_nm"]),"dipole_orientation":m["exact_contract"]["source_orientation"],"case_uid":m["case_id"]}
 base_sha=sha(BASE_PATH); monitor_sha=sha(MONITOR_PATH); native_sha=sha(NATIVE_PATH); mat_sha=sha(base.MATERIAL_CONFIG)
 if base_sha!=m["source_provenance"]["builder"]["sha256"] or monitor_sha!=m["source_provenance"]["monitor_contract"]["sha256"] or native_sha!=m["source_provenance"]["native_builder_primitives"]["sha256"] or mat_sha!=m["source_provenance"]["material_config"]["sha256"]: raise RuntimeError("source_sha_drift")
 physical_fields={"case_id":case["case_id"],"geometry_hash":case["geometry_hash"],"geometry_sequence_nm":seq,"source_position":case["source_position"],"source_z_nm":float(m["exact_contract"]["source_z_nm"]),"source_orientation":case["dipole_orientation"],"source_lateral_condition":m["exact_contract"]["source_lateral_condition"],"wavelength_grid_acquisition_nm":[420.0,480.0,301],"wavelength_grid_target_nm":m["exact_contract"]["wavelength_grid_target_nm"],"interpolation":False,"normalization_contract":"MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1; raw-first; p_up_raw and p_box_raw retained; no pre-normalization","aggregation_contract":"fixed_v2_aggregation_contract_v1; raw position x/z and raw geometry top/centroid/bottom aggregation before normalization","reference_plane":"MDC provider upward_monitor above stack top z=975 nm; reconciliation to Level2A NP pillar bottom is a post-acquisition contract audit, never a substitution","physical_order_mapping":"direct MDC angular axis is native farfieldangle from +y air-side normal; no order relabeling or interpolation in acquisition","source_class":"MDC_NATIVE_M1_2D_FDTD_DIPOLE","solver_contract":"12 MPI x 1 thread; one solver entry; no retry","builder_contract":{"builder_source_sha256":base_sha,"monitor_source_sha256":monitor_sha,"native_builder_source_sha256":native_sha,"material_config_sha256":mat_sha}}
 if hashlib.sha256(json.dumps(physical_fields,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=m["physical_contract_hash"]: raise RuntimeError("physical_contract_hash_drift")
 lu=base.lumapi()
 if pre.exists() and post.exists():
  if sha(pre)!=sha(post): raise RuntimeError("existing_pre_post_fsp_mismatch")
 else:
  setup_f=lu.FDTD(hide=True)
  try:
   setup=base.build_case(setup_f,case,structure); setup_f.save(str(pre))
  finally: setup_f.close()
  shutil.copy2(pre,post)
 pre_sha=sha(pre)
 fresh=lu.FDTD(hide=True)
 try:
  fresh.load(str(post))
  readback={"fdtd_count":int(fresh.getnamednumber("FDTD")),"upward_monitor_count":int(fresh.getnamednumber("upward_monitor")),"box_monitor_counts":{n:int(fresh.getnamednumber(n)) for n in ("emit_box_12nm_top","emit_box_12nm_bottom","emit_box_12nm_left","emit_box_12nm_right")},"fresh_load":"PASS"}
  if readback["fdtd_count"]!=1 or readback["upward_monitor_count"]!=1 or any(v!=1 for v in readback["box_monitor_counts"].values()): raise RuntimeError("pilot_monitor_readback_failed")
  resource_path=case_dir/"M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_RECHECK_V1.json"; admission=resource_snapshot(1); atomic_json(resource_path,admission)
  if admission["safe_new_slots"]<1 or admission["active_apcd_fdtd_slots_before_admission"]>=3: raise RuntimeError("pilot_resource_admission_blocked")
  entered=now(); entry={"schema_version":"M0F_DIRECT_MDC_SOLVER_ENTRY_V1","case_id":case["case_id"],"attempt_id":m["attempt_id"],"solver_entered":True,"solver_entered_at":entered,"pre_fsp_path":str(pre),"pre_fsp_sha256":pre_sha,"physical_contract_hash":m["physical_contract_hash"],"builder_source_sha256":base_sha,"adapter_script_path":str(Path(__file__)),"adapter_script_sha256":sha(Path(__file__)),"solver_contract":"12 MPI x 1 thread; one APCD FDTD slot","resource_admission_path":str(case_dir/"M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_V1.json"),"resource_admission_sha256":sha(case_dir/"M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_V1.json"),"fluent_protection":admission["fluent_protection"]}
  entry_path=case_dir/"M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json"; atomic_json(entry_path,entry)
  ledger=case_dir.parent.parent/"M0F_DIRECT_MDC_CASE_ATTEMPT_LEDGER_V1.jsonl"; ledger.parent.mkdir(parents=True,exist_ok=True)
  with ledger.open("a",encoding="utf-8") as f: f.write(json.dumps(entry,ensure_ascii=False,sort_keys=True)); f.write(chr(10)); f.flush(); os.fsync(f.fileno())
  atomic_json(case_dir/"M0F_DIRECT_MDC_RUNTIME_STATE_V1.json",{"status":"RUNNING","solver_entered":True,"case_id":case["case_id"],"attempt_id":m["attempt_id"],"solver_entry_path":str(entry_path),"solver_entry_sha256":sha(entry_path)})
  fresh.run(); fresh.save(str(post)); post_sha=sha(post)
  mon=setup["monitor_name"]; freq=np.asarray(fresh.getdata(mon,"f"),float).reshape(-1); lam=299792458.0/freq*1e9; order=np.argsort(lam); lam=lam[order]
  p_up=base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,mon),"Linear X"); p_up=np.asarray(p_up,float).reshape(-1)[order]
  side={s:base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,"emit_box_12nm_"+s),"Linear X" if s in ("top","bottom") else "Linear Y") for s in ("top","bottom","left","right")}; p_box=np.asarray(base.monitor_contract.calculate_box_outward_flux(side)["net_outward"],float).reshape(-1)[order]
  if len(lam)!=base.POINTS or not np.all(np.isfinite(lam)) or not np.all(np.isfinite(p_up)) or not np.all(np.isfinite(p_box)): raise RuntimeError("pilot_raw_spectrum_invalid")
  angle,joint,joint_rows=base.extract_joint(fresh,mon,lam,p_up)
  spectral=np.trapezoid(joint,np.radians(angle),axis=1); angular=np.trapezoid(joint,np.radians(lam),axis=0)
  np.savez_compressed(npz,wavelength_nm=lam,angle_deg=angle,joint_raw=joint,spectral_marginal_raw=spectral,angular_marginal_raw=angular,p_up_raw=p_up,p_box_raw=p_box)
  target=np.asarray(m["exact_contract"]["wavelength_grid_target_nm"],float); idx=[]; mismatch=[]
  for w in target:
   j=int(np.argmin(np.abs(lam-w))); idx.append(j); mismatch.append(float(lam[j]-w))
  if any(abs(x)>1e-9 for x in mismatch): raise RuntimeError("pilot_target_grid_not_exact")
  result={"schema_version":"M0F_DIRECT_MDC_CASE_RESULT_V1","status":"COMPLETE","case_id":case["case_id"],"attempt_id":m["attempt_id"],"solver_entered":True,"solver_status":"COMPLETE","accepted":True,"geometry_hash":case["geometry_hash"],"geometry_sequence_nm":seq,"source_position":case["source_position"],"source_position_nm":float(case["source_position_nm"]),"dipole_orientation":case["dipole_orientation"],"builder_source_path":str(BASE_PATH),"builder_source_sha256":base_sha,"adapter_script_path":str(Path(__file__)),"adapter_script_sha256":sha(Path(__file__)),"monitor_contract_path":str(MONITOR_PATH),"monitor_contract_sha256":monitor_sha,"native_builder_path":str(NATIVE_PATH),"native_builder_sha256":native_sha,"material_config_path":str(base.MATERIAL_CONFIG),"material_config_sha256":mat_sha,"start_timestamp":entered,"end_timestamp":now(),"pre_fsp_path":str(pre),"pre_fsp_sha256":pre_sha,"post_fsp_path":str(post),"post_fsp_sha256":post_sha,"raw_npz_path":str(npz),"raw_npz_sha256":sha(npz),"fresh_load_status":"PASS","object_readback":readback,"raw_spectral_output_status":"PASS","raw_angular_output_status":"PASS","joint_tensor_status":"PASS","extraction_status":"PASS","wavelength_points":int(len(lam)),"wavelength_grid_min_nm":float(lam.min()),"wavelength_grid_max_nm":float(lam.max()),"wavelength_grid_step_nm":float(np.median(np.diff(lam))),"target_wavelength_grid_nm":[float(x) for x in target],"target_sample_indices":idx,"target_grid_mismatch_nm":mismatch,"angle_points":int(len(angle)),"joint_shape":[int(x) for x in joint.shape],"joint_nonfinite_ratio":float(np.mean(~np.isfinite(joint))),"joint_negative_count":int(np.sum(joint<0)),"spectral_marginal_recovered_from_joint":True,"angular_marginal_recovered_from_joint":True,"p_up_raw_finite":bool(np.all(np.isfinite(p_up))),"p_box_raw_finite":bool(np.all(np.isfinite(p_box))),"normalization_before_aggregation":False,"filter_identity":setup["filter_id"],"monitor_identity":setup["monitor_name"],"tensor_axis_order":setup["tensor_axis_order"],"tensor_units":setup["tensor_units"],"raw_upward_power_median":float(np.median(p_up)),"raw_box_power_median":float(np.median(p_box)),"physical_contract_hash":m["physical_contract_hash"],"resource_admission_path":str(case_dir/"M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_V1.json"),"resource_admission_sha256":sha(case_dir/"M0F_RESOURCE_ADMISSION_AT_SOLVER_ENTRY_V1.json"),"solver_contract":"12 MPI x 1 thread; one entry; no retry","retry_allowed":False,"source_worktrees_read_only":True,"no_raw_fsp_copy_from_source":True}
  atomic_json(case_dir/"case_result.json",result); atomic_json(case_dir/"M0F_DIRECT_MDC_RUNTIME_STATE_V1.json",{"status":"COMPLETE","solver_entered":True,"solver_status":"COMPLETE","case_id":case["case_id"],"attempt_id":m["attempt_id"],"post_fsp_sha256":post_sha,"raw_npz_sha256":sha(npz)})
  atomic_json(case_dir.parent/"M0F_PILOT_COMPLETION_SUMMARY_V1.json",{"status":"COMPLETE","case_id":case["case_id"],"solver_entered":True,"solver_returned":True,"post_fsp_path":str(post),"raw_npz_path":str(npz),"case_result_path":str(case_dir/"case_result.json"),"solver_entry_path":str(entry_path)})
  print(json.dumps(result,ensure_ascii=False,indent=2))
 except Exception as exc:
  err={"schema_version":"M0F_DIRECT_MDC_CASE_FAILURE_V1","status":"FAILED_AFTER_ENTRY" if (case_dir/"M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json").exists() else "FAILED_BEFORE_ENTRY","case_id":case["case_id"],"attempt_id":m["attempt_id"],"solver_entered":(case_dir/"M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json").exists(),"error":repr(exc),"traceback":traceback.format_exc(),"pre_fsp_path":str(pre) if pre.exists() else "","pre_fsp_sha256":sha(pre) if pre.exists() else "","post_fsp_path":str(post) if post.exists() else "","post_fsp_sha256":sha(post) if post.exists() else ""}
  atomic_json(case_dir/"case_failure.json",err); print(json.dumps(err,ensure_ascii=False,indent=2)); raise
 finally: fresh.close()

if __name__=="__main__": main()
