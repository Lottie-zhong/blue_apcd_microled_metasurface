from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_ID = "PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1"
PHYSICAL_CONTRACT_SHA256 = "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5"
SEED_MANIFEST = ROOT / "reports/coupling/PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json"
MONITOR_CONTRACT = ROOT / "contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json"
TEMPORAL_CONTRACT = ROOT / "contracts/coupling/medium_pw/MEDIUM_PW_TEMPORAL_CONTRACT_V1.json"
MATERIAL_MODULE = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts\apcd_native_materials.py")
MATERIAL_MODULE_SHA256 = "12a1b183380137b50d0d381e6c93c1877ae5ed552d8b3807deb8a06fb297b07a"
MATERIAL_POLICY = MATERIAL_MODULE.parents[1] / "configs/mdc_defect_450_material_policy.json"
MATERIAL_POLICY_SHA256 = "73d1ab830795dd7bcd5ed7fa49f2f84653a151151a823a82969e2ab5ee8f98ee"
MATERIAL_TABLE = MATERIAL_MODULE.parents[1] / "outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled_mdc_native_m1.csv"
MATERIAL_TABLE_SHA256 = "16cf9219c577ad264c10d0e9933a40e9b9f1a43775878ae52806cecc47a4f4b6"
MATERIAL_REPO_COMMIT = "7f34bd767adee8ed37c2d907ac0546d47430631e"
LUMERICAL_API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
EXPECTED = {
 "seed_manifest": "463ceaece52121b1a968d22881944c082a26041c16b4489c25b6a0b8f44db62b",
 "monitor_contract": "a84d8526889084f2b3b09022402ca93b2947939cb744f071a4b19bc6eb09172f",
 "temporal_contract": "f1abd94a21e12207fc48c6b66660526841b999e8b8497d98994cdff9837683fd",
}
CORE_MESH = {"name":"NP_DERIVED_BASELINE_N2","center_nm":[0.,0.,1462.],"span_nm":[1740.,290.,700.],"step_nm":[5.,5.,5.]}
BACKGROUND_MESH = {"name":"MESH_NP_MDC_SPACER_BASELINE","center_nm":[0.,0.,1462.],"span_nm":[1740.,290.,750.],"step_nm":[10.,10.,10.]}
FDTD_SETUP = {"x_span_nm":1740.,"y_span_nm":290.,"z_min_nm":-600.,"z_max_nm":3000.,"pml_layers":8,"mesh_accuracy":4,"mesh_refinement":"conformal variant 0","dt_stability_factor":0.99}
SOURCE_PROFILE = {
 "names":["PW_SOURCE_X_FORWARD","PW_SRC_X_FORWARD"],"plane_wave_type":"Bloch/periodic",
 "injection_axis":"z-axis","direction":"Forward","z_nm":-250.,"polarization_angle_deg":0.,
 "theta_deg":0.,"phi_deg":0.,"amplitude":1.,"phase_deg":0.,"wavelength_nm":[440.,460.],
 "frequency_dependent_profile":0,"pulse_type":"standard"
}

def sha256_bytes(data: bytes) -> str:
 return hashlib.sha256(data).hexdigest()

def sha256_file(path: Path) -> str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""): h.update(block)
 return h.hexdigest()

def load_json(path: Path) -> Dict[str, Any]:
 return json.loads(path.read_text(encoding="utf-8"))

def geometry_hash(diameters_nm: Sequence[int]) -> str:
 vals=[int(v) for v in diameters_nm]
 return sha256_bytes(",".join(str(v) for v in vals).encode("ascii"))

def pillar_centers_nm(pitch_nm: float, count: int) -> List[float]:
 return [(i-(count-1)/2.)*pitch_nm for i in range(count)]

def core_bounds_nm() -> Dict[str,List[float]]:
 c,s=CORE_MESH["center_nm"],CORE_MESH["span_nm"]
 return {axis:[center-span/2.,center+span/2.] for axis,center,span in zip(("x","y","z"),c,s)}

def mesh_coverage(diameters_nm: Sequence[int], pitch_nm: float=290., height_nm: float=500.) -> List[Dict[str,Any]]:
 b=core_bounds_nm(); xs=pillar_centers_nm(pitch_nm,len(diameters_nm)); z0=1212.; z1=z0+height_nm
 rows=[]
 for i,(x,d) in enumerate(zip(xs,diameters_nm),1):
  r=float(d)/2.
  m={"x_minus_nm":x-r-b["x"][0],"x_plus_nm":b["x"][1]-x-r,
     "y_minus_nm":-r-b["y"][0],"y_plus_nm":b["y"][1]-r,
     "z_minus_nm":z0-b["z"][0],"z_plus_nm":b["z"][1]-z1}
  rows.append({"pillar":i,"diameter_nm":int(d),"center_x_nm":x,"margins_nm":m,
   "minimum_lateral_margin_nm":min(m[k] for k in ("x_minus_nm","x_plus_nm","y_minus_nm","y_plus_nm")),
   "minimum_vertical_margin_nm":min(m["z_minus_nm"],m["z_plus_nm"]),
   "inside_mesh":min(m.values())>=0.})
 return rows

def validate_geometry(diameters_nm: Sequence[int], declared_hash: str=None) -> Dict[str,Any]:
 if len(diameters_nm)!=6: raise ValueError("ordered_D_nm must contain exactly six D1...D6 values")
 vals=[int(v) for v in diameters_nm]
 if any(v<100 or v>230 or v%5 for v in vals): raise ValueError("D values must be 5 nm grid values in [100,230] nm")
 h=geometry_hash(vals)
 if declared_hash and declared_hash!=h: raise ValueError("geometry hash does not match ordered D1...D6")
 rows=mesh_coverage(vals)
 if any(not x["inside_mesh"] for x in rows): raise ValueError("pillar outside validated full-period mesh")
 if min(x["minimum_lateral_margin_nm"] for x in rows)<30.-1e-9: raise ValueError("lateral margin < observed 30 nm")
 if min(x["minimum_vertical_margin_nm"] for x in rows)<100.-1e-9: raise ValueError("vertical margin < observed 100 nm")
 return {"ordered_D_nm":vals,"geometry_hash_sha256":h,"pillar_coverage":rows,
  "minimum_lateral_margin_nm":min(x["minimum_lateral_margin_nm"] for x in rows),
  "minimum_vertical_margin_nm":min(x["minimum_vertical_margin_nm"] for x in rows)}

def normalize_spec(spec: Dict[str,Any]) -> Dict[str,Any]:
 case_id=str(spec.get("case_id","")).strip()
 ds=spec.get("ordered_D_nm")
 contract=spec.get("pw_contract") or spec.get("physical_contract")
 if not case_id or not isinstance(ds,list) or not isinstance(contract,dict): raise ValueError("case_id, ordered_D_nm, and pw_contract are required")
 if contract.get("contract_sha256")!=PHYSICAL_CONTRACT_SHA256: raise ValueError("scientific contract hash mismatch")
 if spec.get("physical_contract_hash") not in (None,PHYSICAL_CONTRACT_SHA256): raise ValueError("spec physical contract hash mismatch")
 declared=spec.get("geometry_hash_sha256") or spec.get("geometry_hash")
 geo=validate_geometry(ds,declared)
 wavelengths=list(range(440,461)); nested=contract.get("contract",{})
 if contract.get("wavelengths_nm")!=wavelengths or nested.get("wavelengths_nm")!=wavelengths: raise ValueError("wavelength grid must be exactly 440-460 nm at 1 nm")
 if int(contract.get("K",0))!=6 or float(contract.get("p_nm",0))!=290. or float(contract.get("H_nm",0))!=500. or float(contract.get("spacer_nm",0))!=237.: raise ValueError("K6 physical contract mismatch")
 if abs(sum(float(x[1]) for x in nested.get("stack_layers",[]))-975.)>1e-9: raise ValueError("MDC layer stack does not sum to 975 nm")
 expected={"substrate":"APCD_GAN_NATIVE_M1","mdc_tio2":"APCD_TIO2_NATIVE_M1","mdc_sio2":"APCD_SIO2_NATIVE_M1","superstrate":"Air"}
 if nested.get("materials")!=expected: raise ValueError("native material contract mismatch")
 return {"case_id":case_id,"attempt_id":str(spec.get("attempt_id","attempt_001")),
  "ordered_D_nm":geo["ordered_D_nm"],"geometry_hash_sha256":geo["geometry_hash_sha256"],
  "physical_contract_hash":PHYSICAL_CONTRACT_SHA256,"pw_contract":contract,"geometry_validation":geo}

def verify_authority_inputs() -> Dict[str,Any]:
 paths={"seed_manifest":SEED_MANIFEST,"monitor_contract":MONITOR_CONTRACT,"temporal_contract":TEMPORAL_CONTRACT,
  "native_material_module":MATERIAL_MODULE,"native_material_policy":MATERIAL_POLICY,"native_material_table":MATERIAL_TABLE}
 result={}
 for key,path in paths.items():
  if not path.is_file(): raise FileNotFoundError(str(path))
  h=sha256_file(path)
  if key in EXPECTED and h!=EXPECTED[key]: raise ValueError("{} hash mismatch: {}".format(key,h))
  if key=="native_material_module" and h!=MATERIAL_MODULE_SHA256: raise ValueError("material module hash mismatch: "+h)
  if key=="native_material_policy" and h!=MATERIAL_POLICY_SHA256: raise ValueError("material policy hash mismatch: "+h)
  if key=="native_material_table" and h!=MATERIAL_TABLE_SHA256: raise ValueError("material table hash mismatch: "+h)
  result[key]={"path":str(path),"sha256":h}
 manifest=load_json(SEED_MANIFEST)
 if manifest.get("physical_contract",{}).get("contract_sha256")!=PHYSICAL_CONTRACT_SHA256: raise ValueError("seed manifest physical contract mismatch")
 result["native_material_repo_commit"]=MATERIAL_REPO_COMMIT
 return result

def import_lumapi():
 if str(LUMERICAL_API) not in sys.path: sys.path.insert(0,str(LUMERICAL_API))
 import lumapi
 return lumapi

def register_native_materials(fd: Any) -> None:
 s=importlib.util.spec_from_file_location("apcd_native_materials_authority_v1",str(MATERIAL_MODULE))
 if s is None or s.loader is None: raise RuntimeError("cannot load pinned Native-M1 helper")
 module=importlib.util.module_from_spec(s); s.loader.exec_module(module)
 for name in ("APCD_GAN_NATIVE_M1","APCD_TIO2_NATIVE_M1","APCD_SIO2_NATIVE_M1"):
  module.register_lumerical_sampled_material(fd,name)

def set_props(fd: Any,props: Dict[str,Any]) -> None:
 for key,value in props.items(): fd.set(key,value)

def add_rectangle(fd: Any,name: str,material: str,z0: float,z1: float) -> None:
 fd.addrect()
 set_props(fd,{"name":name,"material":material,"x":0.,"y":0.,
  "x span":FDTD_SETUP["x_span_nm"]*1e-9,"y span":FDTD_SETUP["y_span_nm"]*1e-9,
  "z min":z0*1e-9,"z max":z1*1e-9})

def add_mesh(fd: Any,mesh: Dict[str,Any]) -> None:
 fd.addmesh()
 set_props(fd,{"name":mesh["name"],"x":mesh["center_nm"][0]*1e-9,"y":mesh["center_nm"][1]*1e-9,
  "z":mesh["center_nm"][2]*1e-9,"x span":mesh["span_nm"][0]*1e-9,"y span":mesh["span_nm"][1]*1e-9,
  "z span":mesh["span_nm"][2]*1e-9,"override x mesh":1,"override y mesh":1,"override z mesh":1,
  "set maximum mesh step":1,"dx":mesh["step_nm"][0]*1e-9,"dy":mesh["step_nm"][1]*1e-9,"dz":mesh["step_nm"][2]*1e-9})

def build_setup(spec: Dict[str,Any],output_fsp: Path,overwrite: bool=False) -> Dict[str,Any]:
 c=normalize_spec(spec); inputs=verify_authority_inputs()
 if output_fsp.exists() and not overwrite: raise FileExistsError("refusing to overwrite: "+str(output_fsp))
 output_fsp.parent.mkdir(parents=True,exist_ok=True)
 temporal=load_json(TEMPORAL_CONTRACT); monitor=load_json(MONITOR_CONTRACT); lumapi=import_lumapi()
 fd=lumapi.FDTD(hide=True)
 try:
  register_native_materials(fd); fd.addfdtd()
  set_props(fd,{"dimension":"3D","x span":FDTD_SETUP["x_span_nm"]*1e-9,"y span":FDTD_SETUP["y_span_nm"]*1e-9,
   "z min":FDTD_SETUP["z_min_nm"]*1e-9,"z max":FDTD_SETUP["z_max_nm"]*1e-9,
   "x min bc":"Periodic","x max bc":"Periodic","y min bc":"Periodic","y max bc":"Periodic","z min bc":"PML","z max bc":"PML",
   "pml layers":FDTD_SETUP["pml_layers"],"mesh accuracy":FDTD_SETUP["mesh_accuracy"],"mesh refinement":FDTD_SETUP["mesh_refinement"],
   "simulation time":temporal["maximum_physical_simulation_time_s"],"auto shutoff min":temporal["auto_shutoff_min"],
   "dt stability factor":FDTD_SETUP["dt_stability_factor"]})
  nested=c["pw_contract"]["contract"]; mat=nested["materials"]
  z=0.; add_rectangle(fd,"GaN_substrate",mat["substrate"],-600.,0.)
  for i,(material,thickness) in enumerate(nested["stack_layers"],1):
   add_rectangle(fd,"MDC_LAYER_{:02d}".format(i),material,z,z+float(thickness)); z+=float(thickness)
  spacer_top=z+float(c["pw_contract"]["spacer_nm"])
  add_rectangle(fd,"SPACER_LAYER",mat["mdc_sio2"],z,spacer_top)
  pillar_top=spacer_top+float(c["pw_contract"]["H_nm"])
  for i,(x,d) in enumerate(zip(pillar_centers_nm(float(c["pw_contract"]["p_nm"]),6),c["ordered_D_nm"]),1):
   fd.addcircle()
   set_props(fd,{"name":"NP_D{}".format(i),"material":mat["mdc_tio2"],"x":x*1e-9,"y":0.,
    "radius":float(d)*0.5e-9,"z min":spacer_top*1e-9,"z max":pillar_top*1e-9})
  for name in SOURCE_PROFILE["names"]:
   fd.addplane()
   set_props(fd,{"name":name,"plane wave type":SOURCE_PROFILE["plane_wave_type"],
    "injection axis":SOURCE_PROFILE["injection_axis"],"direction":SOURCE_PROFILE["direction"],
    "polarization angle":SOURCE_PROFILE["polarization_angle_deg"],"angle theta":SOURCE_PROFILE["theta_deg"],
    "angle phi":SOURCE_PROFILE["phi_deg"],"x":0.,"y":0.,"z":SOURCE_PROFILE["z_nm"]*1e-9,
    "x span":FDTD_SETUP["x_span_nm"]*1e-9,"y span":FDTD_SETUP["y_span_nm"]*1e-9,
    "wavelength start":SOURCE_PROFILE["wavelength_nm"][0]*1e-9,"wavelength stop":SOURCE_PROFILE["wavelength_nm"][1]*1e-9,
    "amplitude":SOURCE_PROFILE["amplitude"],"phase":SOURCE_PROFILE["phase_deg"],"use global source settings":0,
    "override global source settings":1,"frequency dependent profile":0})
  planes=monitor["plane_authority"]["sample_planes_nm"]; names=c["pw_contract"]["contract"]["monitors"]
  plane_rows=[(names["input"],planes["MON_IN"]),(names["pre"],planes["MON_PRENP"]),
   (names["output"],planes["MON_POSTNP"]),("MON_REFLECTION",planes["MON_REFLECTION"])]
  for name,z_nm in plane_rows:
   fd.addpower()
   set_props(fd,{"name":name,"monitor type":"2D Z-normal","x":0.,"y":0.,"z":float(z_nm)*1e-9,
    "x span":FDTD_SETUP["x_span_nm"]*1e-9,"y span":FDTD_SETUP["y_span_nm"]*1e-9,
    "override global monitor settings":1,"use source limits":1,"use wavelength spacing":1,
    "frequency points":len(c["pw_contract"]["wavelengths_nm"]),"output power":1})
  add_mesh(fd,BACKGROUND_MESH); add_mesh(fd,CORE_MESH)
  fd.save(str(output_fsp))
 finally: fd.close()
 return {"status":"SETUP_ONLY_SAVED","authority":AUTHORITY_ID,"case_id":c["case_id"],"attempt_id":c["attempt_id"],
  "ordered_D_nm":c["ordered_D_nm"],"geometry_hash_sha256":c["geometry_hash_sha256"],
  "physical_contract_hash":c["physical_contract_hash"],"fsp":str(output_fsp),"fsp_sha256":sha256_file(output_fsp),
  "solver_run_called":False,"scientific_entry_count":0,"authority_inputs":inputs,"geometry_validation":c["geometry_validation"]}

def main() -> int:
 parser=argparse.ArgumentParser(description="Build a deterministic setup-only K6 full-period 5 nm pre-FSP.")
 parser.add_argument("--spec-json",required=True); parser.add_argument("--output-fsp",required=True)
 args=parser.parse_args(); print(json.dumps(build_setup(load_json(Path(args.spec_json)),Path(args.output_fsp)),indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
