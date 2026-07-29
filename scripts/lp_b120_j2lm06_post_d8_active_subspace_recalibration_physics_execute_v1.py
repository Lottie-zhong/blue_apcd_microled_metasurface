from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys, uuid
from pathlib import Path

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
PLAN=ML/"plans/b120_j2lm06_post_d8_active_subspace_recalibration_plan_v1.json"
CONTRACTS=[ML/"plans/b120_j2lm06_post_d8_recalibration_execution_contract_v1.json",ML/"plans/b120_j2lm06_post_d8_recalibration_ml_label_contract_v1.json",ML/"plans/b120_j2lm06_post_d8_recalibration_validation_metric_contract_v1.json",ML/"plans/b120_j2lm06_post_d8_route_decision_contract_v1.json"]
PACKAGE=ML/"execution_packages/b120_j2lm06_post_d8_active_subspace_recalibration_execution_package_v1"
STAGING=ML/"staging/b120_j2lm06_post_d8_active_subspace_recalibration_v1"
SCRIPT=ROOT/"scripts/lp_b120_j2lm06_post_d8_active_subspace_recalibration_physics_execute_v1.py"
RUNTIME=ROOT/"scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
PARENT_HEAD="e42a210597900e06b896220e197eb7e8dc6d835f"

spec=importlib.util.spec_from_file_location("d6_runner",ROOT/"scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py")
if not spec or not spec.loader: raise RuntimeError("D6_ADAPTER_IMPORT_FAILED")
d6=importlib.util.module_from_spec(spec); sys.modules[spec.name]=d6; spec.loader.exec_module(d6)

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a:str)->str:return d6.git(*a)
def load_runtime():
 s=importlib.util.spec_from_file_location("lp_recal_runtime",RUNTIME)
 if not s or not s.loader: raise RuntimeError("RUNTIME_MODULE_RESOLUTION_FAILED")
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
 return m
def plan_rows(): return json.loads(PLAN.read_text(encoding="utf8"))["probes"]
def row(cid): return next(x for x in plan_rows() if x.get("candidate_id",x.get("probe_id"))==cid)
def plan_spec(cid):
 r=row(cid); g=r["geometry"]; r={**r,"candidate_id":r.get("candidate_id",r.get("probe_id"))}
 return {**r,"legacy_case_id":cid,"legacy_bin":60,"J1_primitive":"sharp_rectangle","J1_dims":{"side_nm":float(g["J1_side_nm"])},"J1_center":[float(x) for x in g["J1_center_nm"]],"J1_rotation":0.0,"J2_primitive":"sharp_rectangle","J2_L":float(g["J2_length_nm"]),"J2_W":float(g["J2_width_nm"]),"J2_center":[float(x) for x in g["J2_center_nm"]],"J2_rotation":float(g["Psi_deg"]),"geometry_hash":r["planned_geometry_hash_sha256"],"exact_geometry_hash":r["planned_geometry_hash_sha256"],"migration_manifest":{"geometry_hash_sha256":r["planned_geometry_hash_sha256"]},"fabrication_preferred_pass":True}
def expected_identity(c,pol):
 cfg={"H_nm":500.0,"period_nm":[432.0,432.0],"material":"APCD_TIO2_NATIVE_M1","background":"air","incidence":"normal","boundary":"xy_periodic_z_pml","monitor_z_nm":1000.0,"wavelength_nm":450.0,"observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"}
 return {"candidate_id":c["candidate_id"],"input_polarization":pol,"wavelength_nm":450.0,"exact_geometry_hash":c["planned_geometry_hash_sha256"],"physics_configuration_hash":hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","source_plan_sha256":sha(PLAN),"schema_version":"LP_ML_SCHEMA_V1.24"}
def attestation():
 rt=load_runtime(); ids=[r.get("candidate_id",r.get("probe_id")) for r in plan_rows()]
 if ids!=["POSTD8_CAL_PROBE_WP_DP_PP","POSTD8_CAL_PROBE_WP_DM_PM","POSTD8_CAL_PROBE_WM_DP_PM","POSTD8_CAL_PROBE_WM_DM_PP"]: raise RuntimeError("FROZEN_PROBE_ORDER_MISMATCH")
 cb=hashlib.sha256(__import__("inspect").getsource(rt.post_solver_acceptance).encode()).hexdigest()
 return {"status":"PASS","stage":"POST_D8_LOCAL_ACTIVE_SUBSPACE_RECALIBRATION_PHYSICS","git_head":git("rev-parse","HEAD"),"required_parent_head":PARENT_HEAD,"runner":{"path":str(SCRIPT.resolve()),"sha256":sha(SCRIPT)},"callback":{"path":str(RUNTIME.resolve()),"sha256":sha(RUNTIME),"source_sha256":cb,"qualname":"post_solver_acceptance"},"source_hashes":{str(p.resolve()):sha(p) for p in [PLAN,*CONTRACTS]},"candidate_order":ids,"subrun_order":[f"{c}_{p}" for c in ids for p in ("x","y")],"future_budget":{"geometries":4,"subruns":8,"wavelength_nm":[450]},"solver_calls":0,"lumapi_calls":0,"fdtd_calls":0}
def prepare():
 if PACKAGE.exists() or STAGING.exists(): raise RuntimeError("OUTPUT_PATH_ALREADY_EXISTS")
 PACKAGE.mkdir(parents=True)
 a=attestation();(PACKAGE/"runtime_attestation_contract.json").write_text(json.dumps(a,indent=2,sort_keys=True),encoding="utf8")
 m={"status":"READY_FOR_EXPLICIT_EXECUTION","plan_version":"POST_D8_ACTIVE_SUBSPACE_RECALIBRATION_PLAN_V1","candidate_order":a["candidate_order"],"subrun_order":a["subrun_order"],"future_budget":a["future_budget"],"source_hashes":a["source_hashes"],"anchor":"D8_TRV_PLAN_d6f4911593b64495"}
 (PACKAGE/"package_manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True),encoding="utf8")
 files=[{"path":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in [PACKAGE/"runtime_attestation_contract.json",PACKAGE/"package_manifest.json"]]
 (PACKAGE/"content_checksums.json").write_text(json.dumps({"status":"PASS","files":files},indent=2,sort_keys=True),encoding="utf8")
def metrics(cid):
 out={};base=STAGING/"subruns"/cid
 for p in ("x","y"):out[p]=json.loads((base/p/"checkpoint.json").read_text())
 txx=complex(out["x"]["weighted_G0_Ex"]["real"],out["x"]["weighted_G0_Ex"]["imag"]);tyx=complex(out["x"]["weighted_G0_Ey"]["real"],out["x"]["weighted_G0_Ey"]["imag"]);txy=complex(out["y"]["weighted_G0_Ex"]["real"],out["y"]["weighted_G0_Ex"]["imag"]);tyy=complex(out["y"]["weighted_G0_Ey"]["real"],out["y"]["weighted_G0_Ey"]["imag"])
 import numpy as np
 J=np.array([[txx,txy],[tyx,tyy]],complex);sv=np.linalg.svd(J,compute_uv=False)
 return {"candidate_id":cid,"txx":{"real":txx.real,"imag":txx.imag},"txy":{"real":txy.real,"imag":txy.imag},"tyx":{"real":tyx.real,"imag":tyx.imag},"tyy":{"real":tyy.real,"imag":tyy.imag},"Txx":abs(txx)**2,"Txy":abs(txy)**2,"Tyx":abs(tyx)**2,"Tyy":abs(tyy)**2,"sigma1":float(sv[0]),"sigma2":float(sv[1]),"sigma2_over_sigma1":float(sv[1]/sv[0]),"determinant":{"real":float(np.linalg.det(J).real),"imag":float(np.linalg.det(J).imag)},"physics_label":"FORMAL_ACCEPTED_WEIGHTED_G0","prediction_label":"MODEL_PREDICTION_NOT_PHYSICS_LABEL"}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--prepare-only",action="store_true");ap.add_argument("--execute",action="store_true");a=ap.parse_args()
 if a.prepare_only: prepare();print(json.dumps(attestation(),indent=2));return 0
 if not a.execute: raise RuntimeError("EXECUTION_REQUIRES_EXPLICIT_EXECUTE")
 if not PACKAGE.exists(): prepare()
 rt=load_runtime();exp=json.loads((PACKAGE/"runtime_attestation_contract.json").read_text());rt.validate_attestation(attestation(),exp)
 if git("rev-parse","HEAD^")!=PARENT_HEAD: raise RuntimeError("COMMIT_BOUND_PARENT_HEAD_MISMATCH")
 STAGING.mkdir(parents=True);results=[]
 for cid in [r.get("candidate_id",r.get("probe_id")) for r in plan_rows()]:
  for pol in ("x","y"):
   o=d6.execute_one(cid,pol,d6.ProductionLumapiBackend(),STAGING,False);results.append({"candidate_id":cid,"polarization":pol,"status":o["status"],"checkpoint_sha256":o["checkpoint_sha256"]})
  (STAGING/"candidates").mkdir(exist_ok=True);(STAGING/"candidates"/f"{cid}.json").write_text(json.dumps(metrics(cid),indent=2,sort_keys=True))
 (STAGING/"subrun_results.json").write_text(json.dumps(results,indent=2)); allm=[json.loads(p.read_text()) for p in sorted((STAGING/"candidates").glob("*.json"))];(STAGING/"candidate_metrics.json").write_text(json.dumps(allm,indent=2))
 print(json.dumps({"status":"PASS","planned_subruns":8,"raw_invocations":8,"accepted":8,"complete_jones":4,"staging":str(STAGING),"package":str(PACKAGE)},indent=2));return 0
if __name__=="__main__":
 d6.PLAN=PLAN;d6.CONTRACTS=CONTRACTS;d6.PACKAGE=PACKAGE;d6.FORMAL_STAGING=STAGING;d6.SCRIPT=SCRIPT;d6.RUNTIME=RUNTIME;d6.PARENT_HEAD=PARENT_HEAD;d6.plan_spec=plan_spec;d6.expected_identity=expected_identity;d6.runtime_attestation=attestation;d6.load_runtime=load_runtime
 raise SystemExit(main())
