from __future__ import annotations
import hashlib, importlib.util, json, math, sys
from pathlib import Path
from typing import Any, Dict, List

ROOT=Path(__file__).resolve().parents[2]
BUILDER_PATH=ROOT/"scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py"
SPEC=importlib.util.spec_from_file_location("pw5_builder",str(BUILDER_PATH))
BUILDER=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(BUILDER)

def _value(x: Any) -> Any:
 if hasattr(x,"tolist"): return x.tolist()
 if isinstance(x,(str,int,float,bool)) or x is None: return x
 return str(x)

def _get(fd: Any,name: str,prop: str) -> Any:
 try: return _value(fd.getnamed(name,prop))
 except Exception as exc: return {"error":str(exc)}

def _nm(value: Any) -> float:
 return round(float(value)*1e9,9)

def _object_names(fd: Any) -> List[str]:
 fd.selectall()
 return [x.split("::")[-1] for x in fd.getid().splitlines()]

def inspect_fsp(path: Path,spec: Dict[str,Any]) -> Dict[str,Any]:
 c=BUILDER.normalize_spec(spec)
 if not path.is_file(): raise FileNotFoundError(str(path))
 lumapi=BUILDER.import_lumapi()
 fd=lumapi.FDTD(str(path),hide=True)
 try:
  names=_object_names(fd)
  types={name:_get(fd,name,"type") for name in names}
  monitor_contract=BUILDER.load_json(BUILDER.MONITOR_CONTRACT)
  monitor_names=c["pw_contract"]["contract"]["monitors"]
  monitor_objects=[monitor_names["input"],monitor_names["pre"],monitor_names["output"],"MON_REFLECTION"]
  source_names=list(BUILDER.SOURCE_PROFILE["names"])
  pillar_names=["NP_D{}".format(i) for i in range(1,7)]
  mdc_names=["MDC_LAYER_{:02d}".format(i) for i in range(1,13)]
  mesh_names=sorted(name for name,typ in types.items() if typ=="Mesh")
  plane_sources=sorted(name for name,typ in types.items() if typ=="PlaneSource")
  geometry={}
  for i,name in enumerate(pillar_names):
   geometry[name]={
    "type":types.get(name),"x_nm":_nm(_get(fd,name,"x")),"y_nm":_nm(_get(fd,name,"y")),
    "diameter_nm":round(_nm(_get(fd,name,"radius"))*2.,9),
    "z_min_nm":_nm(_get(fd,name,"z min")),"z_max_nm":_nm(_get(fd,name,"z max")),
    "material":_get(fd,name,"material")}
  layers={}
  for name in ["GaN_substrate"]+mdc_names+["SPACER_LAYER"]:
   layers[name]={"type":types.get(name),"material":_get(fd,name,"material"),
    "x_span_nm":_nm(_get(fd,name,"x span")),"y_span_nm":_nm(_get(fd,name,"y span")),
    "z_min_nm":_nm(_get(fd,name,"z min")),"z_max_nm":_nm(_get(fd,name,"z max"))}
  source_readback={}
  source_props=["enabled","plane wave type","injection axis","direction","polarization angle","angle theta","angle phi",
   "z","x span","y span","wavelength start","wavelength stop","amplitude","phase",
   "use global source settings","override global source settings","frequency dependent profile","pulse type"]
  for name in source_names:
   raw={key:_get(fd,name,key) for key in source_props}
   source_readback[name]={
    "type":types.get(name),"enabled":raw["enabled"],"plane_wave_type":raw["plane wave type"],
    "injection_axis":raw["injection axis"],"direction":raw["direction"],
    "polarization_angle_deg":raw["polarization angle"],"theta_deg":raw["angle theta"],"phi_deg":raw["angle phi"],
    "x_nm":_nm(raw["x"] if "x" in raw else _get(fd,name,"x")),"y_nm":_nm(raw["y"] if "y" in raw else _get(fd,name,"y")),
    "z_nm":_nm(raw["z"]),"x_span_nm":_nm(raw["x span"]),"y_span_nm":_nm(raw["y span"]),
    "wavelength_start_nm":_nm(raw["wavelength start"]),"wavelength_stop_nm":_nm(raw["wavelength stop"]),
    "amplitude":raw["amplitude"],"phase_deg":raw["phase"],
    "use_global_source_settings":raw["use global source settings"],
    "override_global_source_settings":raw["override global source settings"],
    "frequency_dependent_profile":raw["frequency dependent profile"],"pulse_type":raw["pulse type"]}
  monitors={}
  monitor_props=["enabled","monitor type","x","y","z","x span","y span","frequency points",
   "override global monitor settings","use source limits","use wavelength spacing","output power"]
  for name in monitor_objects:
   raw={key:_get(fd,name,key) for key in monitor_props}
   monitors[name]={"type":types.get(name),"enabled":raw["enabled"],"monitor_type":raw["monitor type"],
    "x_nm":_nm(raw["x"]),"y_nm":_nm(raw["y"]),"z_nm":_nm(raw["z"]),
    "x_span_nm":_nm(raw["x span"]),"y_span_nm":_nm(raw["y span"]),
    "frequency_points":raw["frequency points"],
    "override_global_monitor_settings":raw["override global monitor settings"],
    "use_source_limits":raw["use source limits"],"use_wavelength_spacing":raw["use wavelength spacing"],
    "output_power":raw["output power"]}
  meshes={}
  for name in mesh_names:
   meshes[name]={"type":types[name],"center_nm":[_nm(_get(fd,name,p)) for p in ("x","y","z")],
    "span_nm":[_nm(_get(fd,name,p)) for p in ("x span","y span","z span")],
    "step_nm":[_nm(_get(fd,name,p)) for p in ("dx","dy","dz")],
    "override":[_get(fd,name,p) for p in ("override x mesh","override y mesh","override z mesh")],
    "set_maximum_mesh_step":_get(fd,name,"set maximum mesh step")}
  materials={}
  for name in ("APCD_GAN_NATIVE_M1","APCD_TIO2_NATIVE_M1","APCD_SIO2_NATIVE_M1"):
   try:
    import numpy as np
    samples=np.asarray(fd.getmaterial(name,"sampled data"))
    materials[name]={"shape":list(samples.shape),"dtype":str(samples.dtype),
     "sampled_data_sha256":hashlib.sha256(np.ascontiguousarray(samples).tobytes()).hexdigest()}
   except Exception as exc: materials[name]={"error":str(exc)}
  fprops={key:_get(fd,"FDTD",key) for key in ("dimension","x span","y span","z min","z max",
   "x min bc","x max bc","y min bc","y max bc","z min bc","z max bc",
   "pml layers","mesh accuracy","mesh refinement","simulation time","auto shutoff min","dt stability factor")}
  fdtd={"dimension":fprops["dimension"],"x_span_nm":_nm(fprops["x span"]),"y_span_nm":_nm(fprops["y span"]),
   "z_min_nm":_nm(fprops["z min"]),"z_max_nm":_nm(fprops["z max"]),
   "boundaries":{k:fprops[k] for k in ("x min bc","x max bc","y min bc","y max bc","z min bc","z max bc")},
   "pml_layers":fprops["pml layers"],"mesh_accuracy":fprops["mesh accuracy"],"mesh_refinement":fprops["mesh refinement"],
   "simulation_time_s":fprops["simulation time"],"auto_shutoff_min":fprops["auto shutoff min"],
   "dt_stability_factor":fprops["dt stability factor"]}
  ref=monitor_contract["plane_authority"]["reference_planes_nm"]
  sample=monitor_contract["plane_authority"]["sample_planes_nm"]
  refs={"sample_planes_nm":sample,"reference_planes_nm":ref}
  wavelengths=list(range(440,461))
  return {"case_id":c["case_id"],"attempt_id":c["attempt_id"],"ordered_D_nm":c["ordered_D_nm"],
   "geometry_hash_sha256":c["geometry_hash_sha256"],"fsp":str(path),"fsp_sha256":BUILDER.sha256_file(path),
   "object_names":names,"object_types":types,"fdtd":fdtd,"geometry":geometry,"stack":layers,
   "source_names":plane_sources,"sources":source_readback,"monitor_names":monitor_objects,"monitors":monitors,
   "wavelengths_nm":wavelengths,"sample_reference_planes":refs,"mesh_names":mesh_names,"meshes":meshes,
   "materials":materials,"mesh_coverage":c["geometry_validation"],"run_called":False,"save_called_by_validator":False}
 finally:
  fd.close()

def semantic_projection(row: Dict[str,Any]) -> Dict[str,Any]:
 fdtd_keys=("dimension","x_span_nm","y_span_nm","z_min_nm","z_max_nm","boundaries","pml_layers","mesh_accuracy","mesh_refinement")
 return {"ordered_D_nm":row["ordered_D_nm"],"geometry_hash_sha256":row["geometry_hash_sha256"],
  "fdtd":{key:row["fdtd"][key] for key in fdtd_keys},"geometry":row["geometry"],"stack":row["stack"],
  "source_names":row["source_names"],"sources":row["sources"],"monitor_names":row["monitor_names"],
  "monitors":row["monitors"],"wavelengths_nm":row["wavelengths_nm"],
  "sample_reference_planes":row["sample_reference_planes"],"mesh_names":row["mesh_names"],
  "meshes":row["meshes"],"materials":row["materials"]}

def _diff(left: Any,right: Any,path: str="",out: List[str]=None) -> List[str]:
 if out is None: out=[]
 if isinstance(left,dict) and isinstance(right,dict):
  if set(left)!=set(right):
   out.append(path+": key sets differ"); return out
  for key in left: _diff(left[key],right[key],path+"/"+str(key),out)
 elif isinstance(left,list) and isinstance(right,list):
  if len(left)!=len(right): out.append(path+": lengths differ"); return out
  for i,(a,b) in enumerate(zip(left,right)): _diff(a,b,path+"/"+str(i),out)
 elif isinstance(left,(int,float)) and isinstance(right,(int,float)) and not isinstance(left,bool) and not isinstance(right,bool):
  if not math.isclose(float(left),float(right),rel_tol=1e-9,abs_tol=1e-8): out.append(path+": {} != {}".format(left,right))
 elif left!=right: out.append(path+": {} != {}".format(left,right))
 return out

def compare_semantics(baseline: Dict[str,Any],candidate: Dict[str,Any]) -> Dict[str,Any]:
 mismatches=_diff(semantic_projection(baseline),semantic_projection(candidate))
 return {"status":"PASS" if not mismatches else "FAIL","mismatch_count":len(mismatches),"mismatches":mismatches}

def validate_expected(row: Dict[str,Any],spec: Dict[str,Any]) -> Dict[str,Any]:
 c=BUILDER.normalize_spec(spec); errors=[]
 if row["ordered_D_nm"]!=c["ordered_D_nm"]: errors.append("ordered D1...D6 differ")
 if row["geometry_hash_sha256"]!=c["geometry_hash_sha256"]: errors.append("geometry hash differs")
 expected_fdtd={"dimension":"3D","x_span_nm":1740.,"y_span_nm":290.,"z_min_nm":-600.,"z_max_nm":3000.,
  "boundaries":{"x min bc":"Periodic","x max bc":"Periodic","y min bc":"Periodic","y max bc":"Periodic","z min bc":"PML","z max bc":"PML"},
  "pml_layers":8.,"mesh_accuracy":4.,"mesh_refinement":"conformal variant 0","simulation_time_s":3e-12,"auto_shutoff_min":1e-6}
 for key,value in expected_fdtd.items():
  actual=row["fdtd"].get(key)
  if isinstance(value,(int,float)) and not isinstance(value,bool):
   if not math.isclose(float(actual),float(value),rel_tol=1e-9,abs_tol=1e-15): errors.append("FDTD {} mismatch".format(key))
  elif actual!=value: errors.append("FDTD {} mismatch".format(key))
 source_expected=BUILDER.SOURCE_PROFILE
 if row["source_names"]!=sorted(source_expected["names"]): errors.append("source count/name mismatch")
 for name in source_expected["names"]:
  src=row["sources"].get(name,{})
  checks={"type":"PlaneSource","enabled":1.,"plane_wave_type":source_expected["plane_wave_type"],
   "injection_axis":source_expected["injection_axis"],"direction":source_expected["direction"],
   "polarization_angle_deg":0.,"theta_deg":0.,"phi_deg":0.,"x_nm":0.,"y_nm":0.,
   "z_nm":source_expected["z_nm"],"x_span_nm":1740.,"y_span_nm":290.,
   "wavelength_start_nm":440.,"wavelength_stop_nm":460.,"amplitude":1.,"phase_deg":0.}
  for key,value in checks.items():
   actual=src.get(key)
   if isinstance(value,(int,float)) and not isinstance(value,bool):
    if not isinstance(actual,(int,float)) or not math.isclose(float(actual),float(value),rel_tol=1e-9,abs_tol=1e-8): errors.append("{} {} mismatch".format(name,key))
   elif actual!=value: errors.append("{} {} mismatch".format(name,key))
 contract=BUILDER.load_json(BUILDER.MONITOR_CONTRACT)
 sample=contract["plane_authority"]["sample_planes_nm"]; refs=contract["plane_authority"]["reference_planes_nm"]
 expected_refs={"sample_planes_nm":sample,"reference_planes_nm":refs}
 if row["sample_reference_planes"]!=expected_refs: errors.append("sample/reference plane contract mismatch")
 monitor_names=c["pw_contract"]["contract"]["monitors"]
 expected_monitors=[monitor_names["input"],monitor_names["pre"],monitor_names["output"],"MON_REFLECTION"]
 if row["monitor_names"]!=expected_monitors: errors.append("monitor list mismatch")
 expected_z={"MON_IN":sample["MON_IN"],"MON_PRENP":sample["MON_PRENP"],"MON_POSTNP":sample["MON_POSTNP"],"MON_REFLECTION":sample["MON_REFLECTION"]}
 for name,z_nm in expected_z.items():
  mon=row["monitors"].get(name,{})
  checks={"type":"DFTMonitor","enabled":1.,"monitor_type":"2D Z-normal","x_nm":0.,"y_nm":0.,
   "z_nm":z_nm,"x_span_nm":1740.,"y_span_nm":290.,"frequency_points":21.,
   "override_global_monitor_settings":1.,"use_source_limits":1.,"use_wavelength_spacing":1.,"output_power":1.}
  for key,value in checks.items():
   actual=mon.get(key)
   if isinstance(value,(int,float)) and not isinstance(value,bool):
    if not isinstance(actual,(int,float)) or not math.isclose(float(actual),float(value),rel_tol=1e-9,abs_tol=1e-8): errors.append("{} {} mismatch".format(name,key))
   elif actual!=value: errors.append("{} {} mismatch".format(name,key))
 if row["wavelengths_nm"]!=list(range(440,461)): errors.append("wavelength grid mismatch")
 centers=BUILDER.pillar_centers_nm(float(c["pw_contract"]["p_nm"]),6)
 for i,(name,d,x) in enumerate(zip(["NP_D{}".format(i) for i in range(1,7)],c["ordered_D_nm"],centers),1):
  g=row["geometry"].get(name,{})
  checks={"type":"Circle","x_nm":x,"y_nm":0.,"diameter_nm":float(d),"z_min_nm":1212.,"z_max_nm":1712.,"material":"APCD_TIO2_NATIVE_M1"}
  for key,value in checks.items():
   actual=g.get(key)
   if isinstance(value,(int,float)) and not isinstance(value,bool):
    if not isinstance(actual,(int,float)) or not math.isclose(float(actual),float(value),rel_tol=1e-9,abs_tol=1e-8): errors.append("{} {} mismatch".format(name,key))
   elif actual!=value: errors.append("{} {} mismatch".format(name,key))
 expected_layers=c["pw_contract"]["contract"]["stack_layers"]
 z=0.
 for i,(material,thickness) in enumerate(expected_layers,1):
  name="MDC_LAYER_{:02d}".format(i); layer=row["stack"].get(name,{})
  if layer.get("material")!=material or not math.isclose(layer.get("z_min_nm",-1e9),z,abs_tol=1e-8) or not math.isclose(layer.get("z_max_nm",-1e9),z+float(thickness),abs_tol=1e-8):
   errors.append(name+" stack mismatch")
  z+=float(thickness)
 substrate=row["stack"].get("GaN_substrate",{})
 if substrate.get("material")!="APCD_GAN_NATIVE_M1" or not math.isclose(substrate.get("z_min_nm",-1e9),-600.,abs_tol=1e-8) or not math.isclose(substrate.get("z_max_nm",-1e9),0.,abs_tol=1e-8): errors.append("GaN substrate mismatch")
 spacer=row["stack"].get("SPACER_LAYER",{})
 if spacer.get("material")!="APCD_SIO2_NATIVE_M1" or not math.isclose(spacer.get("z_min_nm",-1e9),975.,abs_tol=1e-8) or not math.isclose(spacer.get("z_max_nm",-1e9),1212.,abs_tol=1e-8): errors.append("spacer mismatch")
 if row["mesh_names"]!=sorted([BUILDER.CORE_MESH["name"],BUILDER.BACKGROUND_MESH["name"]]): errors.append("mesh object inventory mismatch")
 for name,expected in ((BUILDER.CORE_MESH["name"],BUILDER.CORE_MESH),(BUILDER.BACKGROUND_MESH["name"],BUILDER.BACKGROUND_MESH)):
  mesh=row["meshes"].get(name,{})
  if mesh.get("center_nm")!=expected["center_nm"] or mesh.get("span_nm")!=expected["span_nm"] or mesh.get("step_nm")!=expected["step_nm"]:
   errors.append(name+" definition mismatch")
 expected_material_hashes={
  "APCD_GAN_NATIVE_M1":"d7441c8d6a6a798316022db3d00b52b557570d1fc21e3208224cc50b88644ede",
  "APCD_TIO2_NATIVE_M1":"be07202748e8e32365e2e017ef4910af24be2a738efedbd88ffb7c60b260f953",
  "APCD_SIO2_NATIVE_M1":"c3976c2be1aaa32d2df160e86781aff978092ff0f61aede1331dd742fded49cf"}
 for name,digest in expected_material_hashes.items():
  if row["materials"].get(name,{}).get("sampled_data_sha256")!=digest: errors.append("native material sample mismatch: "+name)
 if not all(x["inside_mesh"] for x in row["mesh_coverage"]["pillar_coverage"]): errors.append("pillar outside core mesh")
 if row["mesh_coverage"]["minimum_lateral_margin_nm"]<30.-1e-9: errors.append("lateral margin < 30 nm")
 if row["mesh_coverage"]["minimum_vertical_margin_nm"]<100.-1e-9: errors.append("vertical margin < 100 nm")
 return {"status":"PASS" if not errors else "FAIL","errors":errors}

def main() -> int:
 import argparse
 p=argparse.ArgumentParser(description="Fresh LOAD-only full-period mesh validation.")
 p.add_argument("--fsp",required=True);p.add_argument("--spec-json",required=True)
 a=p.parse_args();row=inspect_fsp(Path(a.fsp),BUILDER.load_json(Path(a.spec_json)))
 result=validate_expected(row,BUILDER.load_json(Path(a.spec_json)))
 print(json.dumps({"validation":result,"readback":row},indent=2,sort_keys=True))
 return 0 if result["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
