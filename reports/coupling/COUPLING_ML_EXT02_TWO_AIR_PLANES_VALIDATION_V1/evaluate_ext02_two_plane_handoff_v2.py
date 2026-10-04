from __future__ import annotations
import copy,hashlib,json,math,platform,sys
from pathlib import Path
import h5py,numpy as np
PROJECT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
RUNNER=Path(r"D:\project\worktrees\blue_apcd_gpu_production_runner_v1")
TASK=PROJECT/r"reports\coupling\COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1"
OUT=TASK
CASE="K6V1_EXT02_TWO_AIR_PLANES_DIAG"; ATT="attempt_001"; RUN="EXT02_DIAG_20261004T141216Z_1b4ce0df234b"
HAND=RUNNER/r"reports\apcd_gpu_production_runner_v1\PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1\EXT02_COUPLING_HANDOFF_V1.json"
PROT=TASK/"DIAGNOSTIC_PROTOCOL_V1.json"
OFF=PROJECT/r"scripts\shared_fdtd\tools\pw_complex_floquet_state_v1.py"
EVSRC=PROJECT/r"scripts\coupling_ml\k6_v2_pipeline\evaluators.py"
CONSRC=PROJECT/r"scripts\coupling_ml\k6_v2_pipeline\contracts.py"
MONAUD=PROJECT/r"reports\coupling\COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1\POSTNP_MONITOR_VALIDITY_AUDIT_REPORT_V1.md"
SETUP=PROJECT/r"outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001"
OLD=PROJECT/r"outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_EXT02\attempt_001"
RD=Path(r"D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001")/RUN
NEAR=RD/r"monitor_extraction\final_v1\MON_POSTNP_complex_fields_v1.npz"
NMeta=RD/r"monitor_extraction\final_v1\MON_POSTNP_complex_fields_v1.json"
FAR=RD/r"monitor_extraction\final_v1\EXT02_POSTNP_DIAG_Z2000_complex_fields_v1.npz"
FMeta=RD/r"monitor_extraction\final_v1\EXT02_POSTNP_DIAG_Z2000_complex_fields_v1.json"
TRUTH=RD/"truth.h5"; RAW=RD/r"raw\K6V1_EXT02_TWO_AIR_PLANES_DIAG__attempt_001_raw_complex_fields.npz"
RFSP=RD/"run.fsp"; RH5=RD/r"run\run_output.h5"
ORAW=OLD/r"raw\K6V1_EXT02__attempt_001_raw.json"
OSTJ=OLD/r"state\K6V1_EXT02__attempt_001_pw_complex_floquet_state.json"
OSTN=OLD/r"state\K6V1_EXT02__attempt_001_pw_complex_floquet_state.npz"
OPRE=OLD/"pre_entry_manifest.json"
RESULT=TASK/"EXT02_TWO_AIR_PLANES_EVALUATION_V2.json"
REPORT=TASK/"EXT02_TWO_AIR_PLANES_EVALUATION_REPORT_V2.md"
EXP={
"hand":"2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75",
"prot":"fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8",
"off":"b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15",
"ev":"44568f7741c9790b3b07ded1545a8489f51415cf95f04de30b021989e30572f4",
"re":"616f857a6b620460b370904ca3f3825d28090f712413240b9b3a4f15a61611ef",
"truth":"05495a2d202795fd215474ac63c461558269efed05581e528048ed383627eb25",
"rfsp":"68ae5cd34144bbe908fc57a5628ac041a4bef2be35058fc614133f58233b27df",
"rh5":"3ae7828f30ec1edcd6e8493461064325163ecd3fa993bb7baefb7cf212551077",
"raw":"159a9d3413b72791d9ecca51df8d8e4ca84c12f8765191e132a080ae399b07d7",
"near":"9746a3c41174f16aac7994e322cc76086fda6b4318dc6876c996b4f1d3a646b7",
"nm":"9c5c8e27d8ea624aad20935c67bc228afc857b02fb1df7aed3abfe8d9034a3ba","near_meta":"9c5c8e27d8ea624aad20935c67bc228afc857b02fb1df7aed3abfe8d9034a3ba",
"far":"84186284d4320bf3966af14a823918e85a53cfc89f350ae5ca07d6ac2cd24ce7",
"fm":"d04f7e07b533542b12ff8c55d9f67a289e7d381b1c248066a6b5873e71b5fd20","far_meta":"d04f7e07b533542b12ff8c55d9f67a289e7d381b1c248066a6b5873e71b5fd20",
"contract":"58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68",
"manifest":"877b105b61cbab60681abb93d436946cd919b5f2afc6fb9000f1104fe648ce0e",
"load":"e4b9e36a372670140b571c4970078739854d0dae8a7aacd432a1ebf6482c9530",
"ma":"7069c764e780f8e5a98f980a026e0cd497268705a211da596bab38c8bb05e71f",
"oraw":"204c98703d9dddddbf3acfa7fd0d175cb7d206fdbb18ce6c1374a0c7310cc7bd",
"ostj":"0fef469ddcf518034dc6a1ce23fcb172e8a8421d186af7a35f151fca351ce8cf",
"ostn":"bcb4d2c3d48bb6d033396cc0725eca9e1bfbe57759c5f002b0347e3ccfc61cf4"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def chk(name,p,key=None):
 if not p.is_file():raise FileNotFoundError(str(p))
 s=sha(p)
 if key and s!=EXP.get(key,key):raise ValueError("hash mismatch "+name+" "+s)
 return {"path":str(p),"sha256":s,"bytes":p.stat().st_size}
def hjson(d):
 x=d[()];return json.loads(x.decode("utf-8") if isinstance(x,bytes) else str(x))
def finite(a):
 a=np.asarray(a);return bool(np.isfinite(a.real).all() and np.isfinite(a.imag).all())
def loadplane(p):
 with np.load(p,allow_pickle=False) as z:
  need={"x_nm","y_nm","z_actual_nm","wavelength_nm","frequency_hz","Ex","Ey","Ez","Hx","Hy","Hz"}
  if set(z.files)!=need:raise ValueError("monitor schema mismatch "+p.name)
  x=np.asarray(z["x_nm"],float);y=np.asarray(z["y_nm"],float);zv=np.asarray(z["z_actual_nm"],float)
  w=np.asarray(z["wavelength_nm"],float);f=np.asarray(z["frequency_hz"],float)
  if zv.shape!=(1,) or w.shape!=(21,) or f.shape!=(21,):raise ValueError("monitor axis shape")
  if not np.allclose(w,np.arange(440.,461.),rtol=0,atol=1e-9) or not np.allclose(299792458./f*1e9,w,rtol=0,atol=1e-8):raise ValueError("wavelength frequency mismatch")
  r={"x":x*1e-9,"y":y*1e-9,"z":zv*1e-9,"f":f}
  for k in ("Ex","Ey","Ez","Hx","Hy","Hz"):
   a=np.asarray(z[k])
   if a.shape!=(x.size,y.size,1,21) or not np.iscomplexobj(a) or not finite(a):raise ValueError("invalid field "+k)
   r[k]=a[:,:,0,:]
  coords={"x":[float(x[0]),float(x[-1])],"y":[float(y[0]),float(y[-1])],"z_nm":float(zv[0])}
 return r,coords
def obj(name,raw,n,coef,ex,ev):
 fields,axes=ex.canonicalize_plane_raw(raw)
 p=ex._plane_projection(raw,n,orders=ex.DEFAULT_ORDERS,z_reference_nm=None,period_x_m=ex.PERIOD_X_M,period_y_m=ex.PERIOD_Y_M)
 sf={k:v[:,:,p["frequency_order"]] for k,v in fields.items()}
 return ev.PlaneProjection(name,float(p["z_sample_m"]),float(p["z_reference_m"]),np.asarray(p["wavelengths_nm"],float),
  np.asarray(p["orders"],int),ev.DIRECTIONS,ev.POLARIZATIONS,np.asarray(coef,complex),np.asarray(p["mode_kz_rad_m"],complex),
  np.asarray(p["mode_power_z_per_abs_e2"],float),np.asarray(p["propagating_mask"],bool),np.asarray(p["basis_condition"],float),
  np.asarray(n,complex),p["axis_contract"],np.asarray(axes["x_m"],float),np.asarray(axes["y_m"],float),sf)
def safe(v,bad):
 if isinstance(v,dict):return {str(k):safe(x,bad) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [safe(x,bad) for x in v]
 if isinstance(v,np.ndarray):return safe(v.tolist(),bad)
 if isinstance(v,np.integer):return int(v)
 if isinstance(v,np.bool_):return bool(v)
 if isinstance(v,(float,np.floating)):
  x=float(v)
  if not math.isfinite(x):bad.append("nonfinite");return None
  return x
 return v
def histcompare(cur,old,mp,orders):
 om={tuple(map(int,x)):i for i,x in enumerate(orders)}
 ix=np.array([om[x] for x in [(-3,0),(-2,0),(-1,0),(0,0),(1,0),(2,0),(3,0)]])
 c=np.asarray(cur)[:,ix,0,:];h=np.asarray(old)[:,ix,0,:]
 s=np.linalg.norm((c-h).reshape(21,-1),axis=1)/np.maximum(np.linalg.norm(h.reshape(21,-1),axis=1),1e-30)
 ac,ah=np.abs(c),np.abs(h);ph=np.angle(c*np.conj(h));sh=ah**2/np.maximum(np.sum(ah**2,axis=(1,2),keepdims=True),1e-300)
 mask=sh>=1e-4;wt=np.where(mask,ah,0.)
 pw=np.asarray(mp)[:,ix,0,:];pc=np.sum(pw*ac**2,axis=-1);po=np.sum(pw*ah**2,axis=-1)
 tc,to=pc.sum(axis=1),po.sum(axis=1);rc=pc/np.maximum(tc[:,None],1e-300);ro=po/np.maximum(to[:,None],1e-300)
 return {"scope":"descriptive one-pair cross-run; no frozen threshold","phase_alignment":"none",
  "state_relative_l2_by_wavelength":s.tolist(),"state_median":float(np.median(s)),"state_q95":float(np.quantile(s,.95)),"state_max":float(np.max(s)),
  "routing_max_abs_difference":float(np.max(abs(rc-ro))),"absolute_order_power_max_abs_difference":float(np.max(abs(pc-po))),
  "total_power_relative_difference_max":float(np.max(abs(tc-to)/np.maximum(abs(to),1e-300))),
  "amplitude_absolute_difference_max":float(np.max(abs(ac-ah))),
  "significant_phase_weighted_rmse_rad":float(np.sqrt(np.sum(wt*ph**2)/max(float(wt.sum()),1e-300))),
  "per_wavelength":[{"wavelength_nm":440+i,"state_relative_l2":float(s[i]),"routing_max_abs_difference":float(np.max(abs(rc[i]-ro[i]))),
  "total_power_relative_difference":float(abs(tc[i]-to[i])/max(abs(to[i]),1e-300))} for i in range(21)]}
def main():
 if RESULT.exists() or REPORT.exists():raise FileExistsError("refuse overwrite V2 evaluation artifacts")
 TASK.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(PROJECT))
 from scripts.shared_fdtd.tools import pw_complex_floquet_state_v1 as ex
 from scripts.coupling_ml.k6_v2_pipeline import evaluators as ev,contracts
 ins={
 "handoff":chk("handoff",HAND,"hand"),"protocol":chk("protocol",PROT,"prot"),"official_extractor":chk("extractor",OFF,"off"),
 "evaluator":chk("evaluator",EVSRC,"ev"),"contract_constants":chk("contracts",CONSRC),
 "runner_extractor":chk("runner extractor",Path(json.loads(HAND.read_text(encoding="utf-8"))["extractor"]["path"]),"re"),
 "truth_h5":chk("truth",TRUTH,"truth"),"run_fsp":chk("run fsp",RFSP,"rfsp"),"run_output_h5":chk("run h5",RH5,"rh5"),
 "raw_fields":chk("raw",RAW,"raw"),"near_npz":chk("near",NEAR,"near"),"near_metadata":chk("near meta",NMeta,"nm"),
 "far_npz":chk("far",FAR,"far"),"far_metadata":chk("far meta",FMeta,"fm"),
 "physical_contract":chk("contract",SETUP/"physical_contract.json","contract"),"source_manifest":chk("manifest",SETUP/"source_manifest.json","manifest"),
 "load_proof":chk("load proof",SETUP/"pre_entry_setup_load_proof.json","load"),"monitor_audit":chk("monitor audit",MONAUD,"ma"),
 "historical_raw":chk("old raw",ORAW,"oraw"),"historical_state_json":chk("old state json",OSTJ,"ostj"),
 "historical_state_npz":chk("old state npz",OSTN,"ostn")}
 hand=json.loads(HAND.read_text(encoding="utf-8"));prot=json.loads(PROT.read_text(encoding="utf-8"))
 if hand["status"]!="GPU_TRUTH_AND_TWO_PLANE_FIELDS_READY_FOR_FROZEN_COUPLING_EVALUATION":raise ValueError("handoff status")
 if (hand["identity"]["case_id"],hand["identity"]["attempt_id"],hand["identity"]["run_id"])!=(CASE,ATT,RUN):raise ValueError("handoff identity")
 run=hand["runner"]
 if not run["solver_entered"] or run["solver_invocations"]!=1 or run["run_one_calls"]!=1 or run["automatic_replays"]!=0:raise ValueError("solver/replay evidence")
 if hand["authorization"]["automatic_replays"]!=0 or hand["authorization"]["k6_v2_solver_authorized_cases"]!=0:raise ValueError("authorization mismatch")
 with h5py.File(TRUTH,"r") as hf:tr=hjson(hf["raw_json"]);met=hjson(hf["metrics_json"])
 if tr["case_id"]!=CASE or tr["attempt_id"]!=ATT or tr["canonical_state"]["schema_version"]!="PW_COMPLEX_FLOQUET_STATE_V1":raise ValueError("truth schema")
 normt=tr["canonical_state"]["normalization"]
 if normt["normalization"]!=ev.SOURCE_NORMALIZATION or met["lossy_gan"]["status"]!="PASS":raise ValueError("truth normalization/index")
 ng=np.asarray([complex(x["real"],x["imag"]) for x in met["lossy_gan"]["n_gan"]])
 with np.load(RAW,allow_pickle=False) as z:
  ri={"x":z["IN_x"],"y":z["IN_y"],"z":z["IN_z"],"f":np.asarray(z["IN_f"]).reshape(-1)}
  for k in ("Ex","Ey","Ez","Hx","Hy","Hz"):ri[k]=z["IN_"+k]
  if not np.allclose(299792458./ri["f"]*1e9,np.arange(440.,461.),rtol=0,atol=1e-8):raise ValueError("source wavelength order")
 pi=ex._plane_projection(ri,ng,orders=ex.DEFAULT_ORDERS,z_reference_nm=-50.,period_x_m=ex.PERIOD_X_M,period_y_m=ex.PERIOD_Y_M)
 rn,cn=loadplane(NEAR);rf,cf=loadplane(FAR)
 if not np.allclose(rn["x"],rf["x"],rtol=0,atol=1e-15) or not np.allclose(rn["y"],rf["y"],rtol=0,atol=1e-15):raise ValueError("monitor grids differ")
 for c,o,label in [(cn,hand["planes"]["MON_POSTNP"],"near"),(cf,hand["planes"]["EXT02_POSTNP_DIAG_Z2000"],"far")]:
  if abs(c["z_nm"]-float(o["actual_z_nm"][0]))>1e-8:raise ValueError(label+" z mismatch")
 if abs(cn["z_nm"]-float(prot["planes"]["existing_postnp"]["actual_sample_z_nm"]))>1e-9:raise ValueError("frozen near z mismatch")
 if cn["x"]!=[-870.,870.] or cn["y"]!=[-145.,145.]:raise ValueError("monitor spans")
 air=np.ones(21,complex)
 pn=ex._plane_projection(rn,air,orders=ex.DEFAULT_ORDERS,z_reference_nm=None,period_x_m=ex.PERIOD_X_M,period_y_m=ex.PERIOD_Y_M)
 pf=ex._plane_projection(rf,air,orders=ex.DEFAULT_ORDERS,z_reference_nm=None,period_x_m=ex.PERIOD_X_M,period_y_m=ex.PERIOD_Y_M)
 coeff,norm=ex._normalize_plane_coefficients({"IN":pi,"POSTNP":pn,"EXT02_POSTNP_DIAG_Z2000":pf},("POSTNP","EXT02_POSTNP_DIAG_Z2000"))
 ip=np.asarray(norm["incident_power_per_area"]);ip0=np.asarray(normt["incident_power_per_area"])
 gd=np.angle(np.exp(1j*(np.asarray(norm["gauge_phase_rad"])-np.asarray(normt["gauge_phase_rad"]))))
 ncheck={"method":"official IN E/H Floquet projection to -50 nm and official source normalization",
 "max_relative_incident_power_delta_vs_truth":float(np.max(abs(ip-ip0)/np.maximum(abs(ip0),1e-300))),
 "max_wrapped_gauge_delta_rad_vs_truth":float(np.max(abs(gd))),
 "parity_tolerance":{"rtol":1e-10,"atol":1e-12,"source":"frozen evaluator coefficient parity check, not physical threshold"},
 "power_matches":bool(np.allclose(ip,ip0,rtol=1e-10,atol=1e-12)),"gauge_matches":bool(np.allclose(gd,0,rtol=0,atol=1e-10))}
 if not ncheck["power_matches"] or not ncheck["gauge_matches"]:raise ValueError("normalization parity")
 no=obj("POSTNP",rn,air,coeff[0],ex,ev);fo=obj("EXT02_POSTNP_DIAG_Z2000",rf,air,coeff[1],ex,ev)
 cpath=Path(tr["canonical_state"]["npz_path"]);ins["current_saved_state"]=chk("current state",cpath,tr["canonical_state"]["sha256"])
 with np.load(cpath,allow_pickle=False) as z:saved=np.asarray(z["coefficients_real"])+1j*np.asarray(z["coefficients_imag"]);orders=np.asarray(z["orders"],int)
 om={tuple(map(int,r)):i for i,r in enumerate(orders)};ix=np.asarray([om[tuple(o)] for o in ev.ORDER_MN])
 nr=ev._deembed(no,1722.); old_same=saved[2][:,ix,0,:];new_same=nr[:,ix,0,:]
 same=np.linalg.norm((new_same-old_same).reshape(21,-1),axis=1)/np.maximum(np.linalg.norm(old_same.reshape(21,-1),axis=1),1e-30)
 inp=ev.TwoPlaneInput(CASE,ATT,contracts.STATE_SCHEMA,EXP["off"],EXP["prot"],ev.SOURCE_NORMALIZATION,1722.,ev.PERIOD_X_M,ev.PERIOD_Y_M,
  ip,no,fo,{"handoff":EXP["hand"],"truth":EXP["truth"],"raw":EXP["raw"],"near":EXP["near"],"far":EXP["far"],
  "near_meta":EXP["nm"],"far_meta":EXP["fm"],"runner_extractor":EXP["re"]},np.asarray(norm["gauge_phase_rad"]))
 cmp=ev.evaluate_two_plane_consistency(inp)
 oldraw=json.loads(ORAW.read_text(encoding="utf-8"));oldmeta=json.loads(OSTJ.read_text(encoding="utf-8"))
 cc=json.loads((SETUP/"physical_contract.json").read_text(encoding="utf-8"));base=copy.deepcopy(cc);added=base["monitors"].pop("diagnostic",None)
 if base!=oldraw["contract"]:raise ValueError("historical base contract mismatch")
 with np.load(OSTN,allow_pickle=False) as z:old=np.asarray(z["coefficients_real"])+1j*np.asarray(z["coefficients_imag"]);oo=np.asarray(z["orders"],int)
 if not np.array_equal(orders,oo) or old.shape!=(3,21,81,2,2):raise ValueError("historical state shape")
 hm=histcompare(nr,old[2],no.mode_power_z_per_abs_e2,no.orders_mn)
 hn=oldmeta["normalization"]
 hm["source_normalization_delta"]={"max_relative_incident_power":float(np.max(abs(ip-np.asarray(hn["incident_power_per_area"]))/np.maximum(abs(np.asarray(hn["incident_power_per_area"],float)),1e-300))),
  "max_wrapped_gauge_rad":float(np.max(abs(np.angle(np.exp(1j*(np.asarray(norm["gauge_phase_rad"])-np.asarray(hn["gauge_phase_rad"])))))))}
 pre=json.loads(OPRE.read_text(encoding="utf-8"));spec=json.loads((SETUP/"five_nm_case_spec.json").read_text(encoding="utf-8"))
 hm["setup_provenance"]={"base_contract_equal_after_added_monitor_removed":True,"added_monitor":added["name"],
 "historical_setup_fsp_sha256":pre["setup_fsp_sha256"],"new_pre_fsp_sha256":spec["pre_fsp_sha256"],
 "historical_mesh_contract_sha256":"not recorded","new_mesh_contract_sha256":spec["mesh_contract_sha256"]}
 if "z_min=1212 nm" not in MONAUD.read_text(encoding="utf-8") or "z_max=1712 nm" not in MONAUD.read_text(encoding="utf-8"):raise ValueError("NP z extents absent")
 zn=cn["z_nm"];zf=cf["z_nm"]
 geom={"np_z_nm":[1212,1712],"near_np_top_clearance_nm":zn-1712,"far_np_top_clearance_nm":zf-1712,
 "reference_np_top_clearance_nm":10,"actual_separation_nm":zf-zn,"far_actual_minus_nominal_nm":zf-2000,
 "configured_np_mesh_z_range_nm":[1112,1812],"near_from_configured_mesh_top_nm":zn-1812,"far_from_configured_mesh_top_nm":zf-1812,
 "monitor_coordinate_dx_nm":[float(np.min(np.diff(rn["x"])*1e9)),float(np.median(np.diff(rn["x"])*1e9)),float(np.max(np.diff(rn["x"])*1e9))],
 "monitor_coordinate_dy_nm":[float(np.min(np.diff(rn["y"])*1e9)),float(np.median(np.diff(rn["y"])*1e9)),float(np.max(np.diff(rn["y"])*1e9))],
 "configured_zmax_nm":3000,"far_to_zmax_nm":3000-zf,"actual_pml_inner_face":"NOT_CAPTURED",
 "previous_layout_estimate_pml_inner_nm":2806.1667,"far_to_estimated_pml_inner_nm":2806.1667-zf,
 "actual_local_fdtd_mesh_transition":"NOT_CAPTURED"}
 for key,p in [("truth",TRUTH),("raw",RAW),("near",NEAR),("far",FAR),("near_meta",NMeta),("far_meta",FMeta)]:
  if sha(p)!=EXP[key]:raise ValueError("input changed "+key)
 bad=[]
 payload={"schema":"COUPLING_ML_EXT02_TWO_AIR_PLANES_EVALUATION_V2",
 "scope":"single-run cross-height; historical cross-run comparison separate and descriptive",
 "execution":{"runner_solver_entries":1,"automatic_replays":0,"new_solver_entries":0,"training_fits":0,"P_scale_fits":0,"confirmation_response_reads":0,"oracle_phase_alignment":False,"fitted_power_scaling":False},
 "identity":hand["identity"],"authority":{"runner_handoff_sha256":EXP["hand"],"protocol_sha256":EXP["prot"],"extractor_sha256":EXP["off"],
 "coupling_input_head":"8019c12c9627dad414bbbfff3579a0bffcda6aa4","runner_head":"9485d92e220abe277f08e65ac25f0b329ef624d9"},
 "normalization_reproduction":ncheck,"same_run_saved_POSTNP_parity":{"role":"implementation parity only","reference_plane_nm":1722,"l2_relative_by_wavelength":same.tolist(),"max":float(np.max(same))},
 "cross_height":cmp,"historical_cross_run":hm,"actual_planes_clearances":geom,"inputs":ins,
 "runtime":{"python":sys.version,"numpy":np.__version__,"h5py":h5py.__version__,"platform":platform.platform()},
 "serialization":{"nonfinite_as_null":True,"nonfinite_paths":bad}}
 payload=safe(payload,bad);payload["serialization"]["nonfinite_paths"]=bad
 RESULT.write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
 m=cmp["metrics"];st=m["propagating_state_relative_l2_by_wavelength"]
 lines=["# EXT02 two-air-plane evaluation V2","",
 "- Scope: one authorized diagnostic run; saved-field post-processing only.",
 f"- Run: {RUN}; case {CASE} / {ATT}.",
 f"- Cross-height result: {cmp['overall_result']}; readiness: {cmp['evaluation_readiness']}.",
 "- Frozen limits are one-case consistency criteria, not H1 or production-admission gates.","",
 "## Execution and authority","",
 "- Runner handoff: DONE / SCIENTIFIC_VALID; solver entries=1, run-one calls=1, automatic replays=0.",
 "- This evaluation added zero solver entries, training fits, or P_scale fits; no confirmation response was accessed.",
 f"- Handoff SHA256: {EXP['hand']}; protocol SHA256: {EXP['prot']}.",
 "- No global phase alignment or fitted power rescaling was used.","",
 "## Actual planes and geometry","",
 f"- MON_POSTNP actual z={zn:.12f} nm (nominal 1800); diagnostic actual z={zf:.12f} nm (nominal 2000).",
 f"- Actual separation={zf-zn:.9f} nm; shared reference=1722 nm.",
 f"- NP z=1212-1712 nm per pinned monitor audit; plane clearances above NP top={zn-1712:.6f} and {zf-1712:.6f} nm.",
 "- Each monitor stores six complex E/H fields, 349 x 59 x 1 x 21, across the full 1740 x 290 nm period.",
 f"- Monitor-coordinate interval medians dx={geom['monitor_coordinate_dx_nm'][1]:g} nm and dy={geom['monitor_coordinate_dy_nm'][1]:g} nm; these are not the underlying solver mesh.",
 f"- Configured NP-derived mesh region ends at 1812 nm; far sample is {zf-1812:.6f} nm above that configured boundary. Actual mesh transition is unknown.",
 f"- Configured z max=3000 nm, {3000-zf:.6f} nm above far plane. Actual PML inner face is unknown; 2806.1667 nm is a prior layout estimate only.","",
 "## Normalization and same-run parity","",
 f"- Official input E/H reprojection to the frozen -50 nm reference reproduced truth normalization: max relative incident-power delta={ncheck['max_relative_incident_power_delta_vs_truth']:.6g}; max wrapped gauge delta={ncheck['max_wrapped_gauge_delta_rad_vs_truth']:.6g} rad.",
 f"- Near-plane state after deembedding matches the same-run saved POSTNP state with max relative L2={np.max(same):.6g}; implementation parity, not independent validation.","",
 "## Frozen cross-height thresholds","","| Metric | Observed | Maximum | Result |","|---|---:|---:|---|"]
 for k,v in cmp["thresholds"].items():lines.append(f"| {k} | {v['value']:.8g} | {v['max']:.8g} | {v['pass']} |")
 lines += ["",f"- State relative L2 median/q95/max={np.median(st):.8g} / {np.quantile(st,.95):.8g} / {np.max(st):.8g}.",
 "- JSON includes all wavelength/order/TE/TM sample and deembedded complex values, amplitude/phase differences, per-order power/routing, and directionality.",
 "- Significant mask and near-amplitude phase weights follow the frozen protocol; no oracle phase alignment.","",
 "## Fit, power, and evanescent diagnostics","",
 "- JSON includes periodic endpoint closure, official LS residual/rank/condition, trapezoid half-weights, Poynting vs modal power, downward state, and evanescent fits.",
 "- Evanescent channels are diagnostic only and receive no far-field power or propagating threshold.",
 "- Continuous-medium kz deembedding approximates FDTD numerical dispersion; actual local mesh and PML inner-face readbacks are missing.","",
 "## Historical EXT02 cross-run comparison","",
 "- New near-plane state was compared directly, without phase alignment, with historical EXT02 stored POSTNP at 1722 nm.",
 "- Common base contract fields match after removing the added diagnostic monitor.",
 "- Descriptive single pair only, no pass threshold. Setup FSP hashes differ and the historical mesh-contract hash is absent; this is not controlled repeatability and does not replace historical truth.","",
 "## Limits","","This result addresses single-case cross-height extraction consistency only. It does not establish absolute convergence, controlled cross-run repeatability, global label validity, H1, or production admission. No training or additional solver entry occurred.",""]
 REPORT.write_text("\n".join(lines),encoding="utf-8",newline="\n")
 print(json.dumps({"result":str(RESULT),"report":str(REPORT),"overall":cmp["overall_result"],"thresholds":cmp["thresholds"],
  "state":{"median":float(np.median(st)),"q95":float(np.quantile(st,.95)),"max":float(np.max(st))},
  "normalization":ncheck,"same_run_max_l2":float(np.max(same)),
  "historical":{k:hm[k] for k in ["state_median","state_q95","state_max","routing_max_abs_difference","absolute_order_power_max_abs_difference","total_power_relative_difference_max","significant_phase_weighted_rmse_rad"]},
  "geometry":geom,"nonfinite_count":len(bad)},indent=2,sort_keys=True,allow_nan=False))
if __name__=="__main__":main()
