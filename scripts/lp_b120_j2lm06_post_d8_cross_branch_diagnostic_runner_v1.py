from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, shutil, sys
from pathlib import Path
ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML=ROOT/"outputs/lp_ml_dataset_v1"
PLAN=ML/"plans/b120_j2lm06_post_d8_cross_branch_diagnostic_plan_v1.json"
PKG=ML/"execution_packages/b120_j2lm06_post_d8_cross_branch_diagnostic_execution_package_v1"
ST=ML/"staging/b120_j2lm06_post_d8_cross_branch_diagnostic_v1"
SCRIPT=ROOT/"scripts/lp_b120_j2lm06_post_d8_cross_branch_diagnostic_runner_v1.py"
RUNTIME=ROOT/"scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
D6PATH=ROOT/"scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py"
spec=importlib.util.spec_from_file_location("d6_cross",D6PATH); d6=importlib.util.module_from_spec(spec); sys.modules[spec.name]=d6; spec.loader.exec_module(d6)
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def plan(): return json.loads(PLAN.read_text(encoding="utf8"))
def rows(): return plan()["candidates"]
def row(cid): return next(r for r in rows() if r["candidate_id"]==cid)
def plan_spec(cid):
 r=row(cid); g=r["geometry"]
 return {**r,"candidate_id":cid,"exact_geometry_hash_sha256":r["exact_geometry_hash_sha256"],"canonical_relative_geometry_hash_sha256":r["canonical_relative_geometry_hash_sha256"],"symmetry_equivalence_hash_sha256":r["symmetry_equivalence_hash_sha256"],"legacy_case_id":cid,"legacy_bin":60,"J1_primitive":"sharp_rectangle","J1_dims":{"side_nm":float(g["J1_side_nm"])},"J1_center":[float(x) for x in g["J1_center_nm"]],"J1_rotation":float(g["J1_rotation_deg"]),"J2_primitive":"sharp_rectangle","J2_L":float(g["J2_length_nm"]),"J2_W":float(g["J2_width_nm"]),"J2_center":[float(x) for x in g["J2_center_nm"]],"J2_rotation":float(g["Psi_deg"]),"geometry_hash":r["exact_geometry_hash_sha256"],"exact_geometry_hash":r["exact_geometry_hash_sha256"],"migration_manifest":{"geometry_hash_sha256":r["exact_geometry_hash_sha256"]},"fabrication_preferred_pass":True}
def expected_identity(c,pol):
 cfg={"H_nm":500.0,"period_nm":[432.0,432.0],"material":"APCD_TIO2_NATIVE_M1","background":"air","incidence":"normal","boundary":"xy_periodic_z_pml","monitor_z_nm":1000.0,"wavelength_nm":450.0,"observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"}
 return {"candidate_id":c["candidate_id"],"input_polarization":pol,"wavelength_nm":450.0,"exact_geometry_hash":c["exact_geometry_hash_sha256"],"physics_configuration_hash":hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","source_plan_sha256":sha(PLAN),"schema_version":"LP_ML_SCHEMA_V1.24"}
def attestation():
 rt=d6.load_runtime(); ids=[r["candidate_id"] for r in rows()]
 return {"status":"PASS","git_head":d6.git("rev-parse","HEAD"),"required_parent_head":d6.git("rev-parse","HEAD^") ,"runner":{"path":str(SCRIPT.resolve()),"sha256":sha(SCRIPT),"qualname":"main"},"callback":{"path":str(RUNTIME.resolve()),"sha256":sha(RUNTIME)},"validator":{"path":str(RUNTIME.resolve()),"sha256":sha(RUNTIME)},"schema":rt.SCHEMA,"registration_mode":rt.REGISTRATION_MODE,"event_log_mode":rt.EVENT_MODE,"lock_mode":rt.LOCK_MODE,"serializer":rt.SERIALIZER,"legacy_line557_allowed":False,"legacy_runtime_gate_allowed":False,"source_hashes":{str(PLAN.resolve()):sha(PLAN),str(RUNTIME.resolve()):sha(RUNTIME)},"candidate_order":ids,"subrun_order":[f"{c}_{p}" for c in ids for p in ("x","y")],"solver_calls":0,"lumapi_calls":0,"fdtd_calls":0}
def freeze_package():
 PKG.mkdir(parents=True,exist_ok=True); rt=d6.load_runtime()
 files={"execution_authorization.json":{"status":"READY_FOR_EXPLICIT_CROSS_BRANCH_EXECUTION","required_parent_head":d6.git("rev-parse","HEAD^"),"candidate_count":18,"subrun_budget":36,"wavelength_nm":450.0,"no_d9":True,"prospective_only":True},"route_contract.json":{"evidence_tier":"PROSPECTIVE_DIAGNOSTIC_EVIDENCE","no_historical_full_jones_claim":True,"route_decision_only":True,"no_d9_candidate_plan":True,"no_additional_solver_authorization":False,"historical_hard_gate":"HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE"},"plan_identity.json":{"plan_path":str(PLAN),"plan_sha256":sha(PLAN),"candidate_ids":[r["candidate_id"] for r in rows()]}}
 for n,v in files.items(): rt.atomic_json(PKG/n,v)
 att=attestation(); rt.atomic_json(PKG/"runtime_attestation_contract.json",att)
 checks=[{"path":n,"sha256":sha(PKG/n),"bytes":(PKG/n).stat().st_size} for n in sorted(files)]
 checks.append({"path":"runtime_attestation_contract.json","sha256":sha(PKG/"runtime_attestation_contract.json"),"bytes":(PKG/"runtime_attestation_contract.json").stat().st_size})
 rt.atomic_json(PKG/"content_checksums.json",{"status":"PASS","files":checks})
 rt.atomic_json(PKG/"package_manifest.json",{"status":"READY_FOR_EXPLICIT_CROSS_BRANCH_EXECUTION","content_checksums_sha256":sha(PKG/"content_checksums.json"),"file_count":len(checks)})
def metrics(cid):
 import numpy as np
 cps={p:json.loads((ST/"subruns"/cid/p/"checkpoint.json").read_text()) for p in ("x","y")}
 def z(p,k): q=cps[p]["weighted_G0_"+k]; return complex(q["real"],q["imag"])
 txx,tyx,txy,tyy=z("x","Ex"),z("x","Ey"),z("y","Ex"),z("y","Ey"); J=np.array([[txx,txy],[tyx,tyy]],complex); sv=np.linalg.svd(J,compute_uv=False); g=row(cid)["geometry"]
 return {"candidate_id":cid,"group":row(cid)["group"],"role":row(cid)["role"],"normalized_coordinate":row(cid)["normalized_coordinate"],"geometry":g,"txx":{"real":txx.real,"imag":txx.imag},"txy":{"real":txy.real,"imag":txy.imag},"tyx":{"real":tyx.real,"imag":tyx.imag},"tyy":{"real":tyy.real,"imag":tyy.imag},"Txx":abs(txx)**2,"Txy":abs(txy)**2,"Tyx":abs(tyx)**2,"Tyy":abs(tyy)**2,"cross_power":abs(txy)**2+abs(tyx)**2,"leakage":abs(txy)**2+abs(tyx)**2+abs(tyy)**2,"sigma1":float(sv[0]),"sigma2":float(sv[1]),"sigma2_over_sigma1":float(sv[1]/sv[0]),"determinant":{"real":float(np.linalg.det(J).real),"imag":float(np.linalg.det(J).imag)},"physics_label":"PROSPECTIVE_CROSS_BRANCH_DIAGNOSTIC_PHYSICS","observable_label":"FORMAL_WEIGHTED_G0_JONES","historical_claim":False,"d9_promotion":False,"projector_lineage":"projector_preserved_from_backbone"}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--preflight",action="store_true"); ap.add_argument("--execute",action="store_true"); ap.add_argument("--batch",choices=("A","B","C","ALL")); a=ap.parse_args()
 d6.PLAN=PLAN; d6.PACKAGE=PKG; d6.FORMAL_STAGING=ST; d6.SCRIPT=SCRIPT; d6.RUNTIME=RUNTIME; d6.plan_spec=plan_spec; d6.expected_identity=expected_identity; d6.PARENT_HEAD=d6.git("rev-parse","HEAD^"); d6.runtime_attestation=attestation
 if a.preflight:
  freeze_package(); print(json.dumps({"status":"READY","candidate_count":len(rows()),"subruns":36,"package":str(PKG),"staging":str(ST),"solver_calls":0},indent=2)); return 0
 if not a.execute or not a.batch: raise RuntimeError("EXECUTION_REQUIRES_BATCH_A_B_C_OR_ALL")
 if not (PKG/"content_checksums.json").exists(): raise RuntimeError("PACKAGE_NOT_FROZEN")
 wanted={"A":[r["candidate_id"] for r in rows() if r["group"]=="PHASE_LOCAL"],"B":[r["candidate_id"] for r in rows() if r["group"]=="PROJECTOR_LOCAL"],"C":[r["candidate_id"] for r in rows() if r["group"]=="BRIDGE"],"ALL":[r["candidate_id"] for r in rows()]}[a.batch]
 ST.mkdir(parents=True,exist_ok=True); (ST/"candidates").mkdir(exist_ok=True); results=[]
 for cid in wanted:
  done=[(ST/"subruns"/cid/p/"checkpoint.json").exists() for p in ("x","y")]
  if any(done):
   if not all(done): raise RuntimeError("PARTIAL_SUBRUN_UNCERTAIN_NO_RETRY")
   continue
  for pol in ("x","y"):
   o=d6.execute_one(cid,pol,d6.ProductionLumapiBackend(),ST,False); results.append({"candidate_id":cid,"polarization":pol,"status":o.get("status"),"checkpoint_sha256":o.get("checkpoint_sha256")})
  d6.load_runtime().atomic_json(ST/"candidates"/(cid+".json"),metrics(cid))
 d6.load_runtime().atomic_json(ST/("batch_"+a.batch.lower()+"_results.json"),{"batch":a.batch,"candidate_ids":wanted,"subruns":results,"solver_calls":len(results)})
 allm=[json.loads(p.read_text()) for p in sorted((ST/"candidates").glob("*.json"))]; d6.load_runtime().atomic_json(ST/"candidate_metrics.json",allm)
 print(json.dumps({"status":"PASS","batch":a.batch,"planned_geometries":len(wanted),"raw_invocations":len(results),"complete_jones":len(allm),"staging":str(ST)},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())

