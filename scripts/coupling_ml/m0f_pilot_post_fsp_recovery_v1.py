
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,sys,time,traceback
from pathlib import Path
import numpy as np
ML=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SOURCE=Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
BASE_PATH=SOURCE/r"scripts\run_mdc_hf_surrogate_v3_al64_joint_profile_v1.py"
MONITOR_PATH=SOURCE/r"scripts\mdc_fdtd_2d_monitor_contract_v1.py"
NATIVE_PATH=SOURCE/r"scripts\run_mdc_native_m1_2d_dipole_device_comparison_v1.py"
sys.path.insert(0,str(SOURCE/"scripts"))
spec=importlib.util.spec_from_file_location("frozen_al64_builder_recovery",BASE_PATH)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
if not hasattr(np,"trapezoid"):np.trapezoid=np.trapz
def now():return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p);tmp=p.with_name(p.name+".tmp");tmp.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+chr(10),encoding="utf-8");os.replace(tmp,p)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--manifest",required=True);a=ap.parse_args()
 m=json.loads(Path(a.manifest).read_text(encoding="utf-8"));case_id=m["case_id"];case_dir=Path(m["output_root"]);pre=case_dir/"attempt_1__pre.fsp";post=case_dir/"attempt_1__post.fsp";npz=case_dir/"attempt_1__raw.npz";entry=case_dir/"M0F_DIRECT_MDC_SOLVER_ENTRY_V1.json";failure=case_dir/"case_failure.json"
 if case_id!="MDC_BOTTOM_X_TARGET_GEOMETRY_445_455_V1" or not entry.exists() or not post.exists() or npz.exists() or (case_dir/"case_result.json").exists():raise RuntimeError("recovery_identity_or_state_gate")
 entry_o=json.loads(entry.read_text(encoding="utf-8"));post_sha=sha(post)
 if entry_o["solver_entered"] is not True:raise RuntimeError("solver_entry_missing")
 lu=base.lumapi();fresh=lu.FDTD(hide=True)
 try:
  fresh.load(str(post));readback={"fdtd_count":int(fresh.getnamednumber("FDTD")),"upward_monitor_count":int(fresh.getnamednumber("upward_monitor")),"box_monitor_counts":{n:int(fresh.getnamednumber(n)) for n in ("emit_box_12nm_top","emit_box_12nm_bottom","emit_box_12nm_left","emit_box_12nm_right")},"fresh_load":"PASS"}
  if readback["fdtd_count"]!=1 or readback["upward_monitor_count"]!=1 or any(v!=1 for v in readback["box_monitor_counts"].values()):raise RuntimeError("recovery_monitor_readback_failed")
  mon="upward_monitor";freq=np.asarray(fresh.getdata(mon,"f"),float).reshape(-1);lam=299792458.0/freq*1e9;order=np.argsort(lam);lam=lam[order]
  p_up=base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,mon),"Linear X");p_up=np.asarray(p_up,float).reshape(-1)[order]
  side={s:base.monitor_contract.integrate_line_poynting_flux(base.monitor_contract.read_fields(fresh,"emit_box_12nm_"+s),"Linear X" if s in ("top","bottom") else "Linear Y") for s in ("top","bottom","left","right")};p_box=np.asarray(base.monitor_contract.calculate_box_outward_flux(side)["net_outward"],float).reshape(-1)[order]
  angle,joint,joint_rows=base.extract_joint(fresh,mon,lam,p_up);spectral=np.trapezoid(joint,np.radians(angle),axis=1);angular=np.trapezoid(joint,np.radians(lam),axis=0)
  np.savez_compressed(npz,wavelength_nm=lam,angle_deg=angle,joint_raw=joint,spectral_marginal_raw=spectral,angular_marginal_raw=angular,p_up_raw=p_up,p_box_raw=p_box)
  target=np.asarray(m["exact_contract"]["wavelength_grid_target_nm"],float);idx=[];mismatch=[]
  for w in target:j=int(np.argmin(np.abs(lam-w)));idx.append(j);mismatch.append(float(lam[j]-w))
  if len(lam)!=301 or joint.shape!=(301,2000) or not np.all(np.isfinite(joint)) or np.any(joint<0) or any(abs(x)>1e-9 for x in mismatch):raise RuntimeError("recovery_raw_contract_failed")
  r={"schema_version":"M0F_DIRECT_MDC_CASE_RESULT_V1","status":"COMPLETE","case_id":case_id,"attempt_id":m["attempt_id"],"solver_entered":True,"solver_status":"COMPLETE","solver_returned":True,"accepted":True,"recovered_from_post_fsp_without_solver":True,"geometry_hash":m["exact_contract"]["geometry_hash"],"geometry_sequence_nm":m["exact_contract"]["geometry_sequence_nm"],"source_position":m["exact_contract"]["source_position"],"source_position_nm":float(m["exact_contract"]["source_z_nm"]),"dipole_orientation":m["exact_contract"]["source_orientation"],"builder_source_path":str(BASE_PATH),"builder_source_sha256":sha(BASE_PATH),"original_solver_adapter_script_path":entry_o["adapter_script_path"],"original_solver_adapter_script_sha256":entry_o["adapter_script_sha256"],"recovery_script_path":str(Path(__file__)),"recovery_script_sha256":sha(Path(__file__)),"monitor_contract_path":str(MONITOR_PATH),"monitor_contract_sha256":sha(MONITOR_PATH),"native_builder_path":str(NATIVE_PATH),"native_builder_sha256":sha(NATIVE_PATH),"material_config_path":str(base.MATERIAL_CONFIG),"material_config_sha256":sha(base.MATERIAL_CONFIG),"solver_entry_path":str(entry),"solver_entry_sha256":sha(entry),"solver_entered_at":entry_o["solver_entered_at"],"end_timestamp":now(),"pre_fsp_path":str(pre),"pre_fsp_sha256":sha(pre),"post_fsp_path":str(post),"post_fsp_sha256":post_sha,"raw_npz_path":str(npz),"raw_npz_sha256":sha(npz),"fresh_load_status":"PASS","object_readback":readback,"raw_spectral_output_status":"PASS_RECOVERED","raw_angular_output_status":"PASS_RECOVERED","joint_tensor_status":"PASS_RECOVERED","extraction_status":"PASS_RECOVERED_FROM_POST_FSP","wavelength_points":int(len(lam)),"wavelength_grid_min_nm":float(lam.min()),"wavelength_grid_max_nm":float(lam.max()),"wavelength_grid_step_nm":float(np.median(np.diff(lam))),"target_wavelength_grid_nm":[float(x) for x in target],"target_sample_indices":idx,"target_grid_mismatch_nm":mismatch,"angle_points":int(len(angle)),"joint_shape":[int(x) for x in joint.shape],"joint_nonfinite_ratio":float(np.mean(~np.isfinite(joint))),"joint_negative_count":int(np.sum(joint<0)),"spectral_marginal_recovered_from_joint":True,"angular_marginal_recovered_from_joint":True,"p_up_raw_finite":bool(np.all(np.isfinite(p_up))),"p_box_raw_finite":bool(np.all(np.isfinite(p_box))),"normalization_before_aggregation":False,"filter_identity":"raw_air_side_unfiltered","monitor_identity":mon,"tensor_axis_order":["wavelength_index","angle_index"],"tensor_units":"raw farfield intensity in native Lumerical export units","raw_upward_power_median":float(np.median(p_up)),"raw_box_power_median":float(np.median(p_box)),"physical_contract_hash":m["physical_contract_hash"],"resource_admission_path":entry_o["resource_admission_path"],"resource_admission_sha256":entry_o["resource_admission_sha256"],"solver_contract":"12 MPI x 1 thread; one entry; no retry","retry_allowed":False,"recovery_solver_calls":0,"source_worktrees_read_only":True,"no_raw_fsp_copy_from_source":True}
  atomic(case_dir/"case_result.json",r);atomic(case_dir/"M0F_PILOT_POST_FSP_RECOVERY_AUDIT_V1.json",{"schema_version":"M0F_PILOT_POST_FSP_RECOVERY_AUDIT_V1","status":"PASS","case_id":case_id,"solver_entry_count":1,"solver_returned":True,"solver_calls_added_by_recovery":0,"post_fsp_exists":True,"post_fsp_sha256":post_sha,"raw_npz_exists":True,"raw_npz_sha256":sha(npz),"fresh_load_status":"PASS","joint_shape":[int(x) for x in joint.shape],"finite_ratio":float(np.mean(np.isfinite(joint))),"negative_count":int(np.sum(joint<0)),"target_grid_exact":True,"recovery_without_new_solver":True,"prior_failure_path":str(failure),"prior_failure_sha256":sha(failure) if failure.exists() else ""})
  atomic(case_dir/"M0F_DIRECT_MDC_RUNTIME_STATE_V1.json",{"status":"COMPLETE_RECOVERED","solver_entered":True,"solver_status":"COMPLETE","extraction_status":"PASS_RECOVERED_FROM_POST_FSP","case_id":case_id,"attempt_id":m["attempt_id"],"post_fsp_sha256":post_sha,"raw_npz_sha256":sha(npz),"recovery_solver_calls":0})
  atomic(case_dir.parent/"M0F_PILOT_COMPLETION_SUMMARY_V1.json",{"status":"COMPLETE_RECOVERED","case_id":case_id,"solver_entered":True,"solver_returned":True,"post_fsp_path":str(post),"raw_npz_path":str(npz),"case_result_path":str(case_dir/"case_result.json"),"solver_entry_path":str(entry),"recovery_without_new_solver":True})
  print(json.dumps(r,ensure_ascii=False,indent=2))
 finally:fresh.close()
if __name__=="__main__":main()
