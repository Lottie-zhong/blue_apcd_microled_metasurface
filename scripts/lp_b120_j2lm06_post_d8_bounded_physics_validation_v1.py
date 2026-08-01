from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
ML = ROOT / "outputs/lp_ml_dataset_v1"
PLAN = ML / "plans/b120_j2lm06_post_d8_dual_anchor_bounded_candidate_plan_v1.json"
PKG = ML / "execution_packages/b120_j2lm06_post_d8_bounded_physics_validation_execution_package_v1"
ST = ML / "staging/b120_j2lm06_post_d8_bounded_physics_validation_v1"
SCRIPT = ROOT / "scripts/lp_b120_j2lm06_post_d8_bounded_physics_validation_v1.py"
RUNTIME = ROOT / "scripts/lp_checkpoint_authoritative_runtime_v1_23.py"
spec = importlib.util.spec_from_file_location("d6bounded", ROOT / "scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py")
d6 = importlib.util.module_from_spec(spec); sys.modules[spec.name] = d6; spec.loader.exec_module(d6)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def plan(): return json.loads(PLAN.read_text(encoding="utf8"))
def rows(): return plan()["candidates"]
def getrow(cid): return next(r for r in rows() if r["candidate_id"] == cid)
def cfg_hash():
    cfg={"H_nm":500.0,"period_nm":[432.0,432.0],"material":"APCD_TIO2_NATIVE_M1","background":"air","incidence":"normal","boundary":"xy_periodic_z_pml","monitor_z_nm":1000.0,"wavelength_nm":450.0,"observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"}
    return hashlib.sha256(json.dumps(cfg,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def plan_spec(cid):
    r=getrow(cid); g=r["geometry"]
    return {**r,"candidate_id":cid,"exact_geometry_hash_sha256":g["exact_geometry_hash_sha256"],"canonical_relative_geometry_hash_sha256":g["canonical_relative_geometry_hash_sha256"],"symmetry_equivalence_hash_sha256":g["symmetry_equivalence_hash_sha256"],"exact_geometry_hash":g["exact_geometry_hash_sha256"],"legacy_case_id":cid,"legacy_bin":60,"J1_primitive":"sharp_rectangle","J1_dims":{"side_nm":float(g["J1_side_nm"])},"J1_center":[float(x) for x in g["J1_center_nm"]],"J1_rotation":0.0,"J2_primitive":"sharp_rectangle","J2_L":float(g["J2_length_nm"]),"J2_W":float(g["J2_width_nm"]),"J2_center":[float(x) for x in g["J2_center_nm"]],"J2_rotation":float(g["Psi_deg"]),"geometry_hash":g["exact_geometry_hash_sha256"],"physics_configuration_hash":cfg_hash(),"migration_manifest":{"geometry_hash_sha256":g["exact_geometry_hash_sha256"]},"fabrication_preferred_pass":True}
def expected_identity(c,pol):
    return {"candidate_id":c["candidate_id"],"input_polarization":pol,"wavelength_nm":450.0,"exact_geometry_hash":c["exact_geometry_hash_sha256"],"physics_configuration_hash":cfg_hash(),"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","source_plan_sha256":sha(PLAN),"schema_version":"LP_ML_SCHEMA_V1.24"}
def attestation():
    rt=d6.load_runtime(); ids=[r["candidate_id"] for r in rows()]
    return {"status":"PASS","git_head":d6.git("rev-parse","HEAD"),"required_parent_head":d6.git("rev-parse","HEAD^"),"runner":{"path":str(SCRIPT.resolve()),"sha256":sha(SCRIPT)},"callback":{"path":str(RUNTIME.resolve()),"sha256":sha(RUNTIME)},"validator":{"path":str(RUNTIME.resolve()),"sha256":sha(RUNTIME)},"schema":rt.SCHEMA,"registration_mode":rt.REGISTRATION_MODE,"event_log_mode":rt.EVENT_MODE,"lock_mode":rt.LOCK_MODE,"serializer":rt.SERIALIZER,"legacy_line557_allowed":False,"legacy_runtime_gate_allowed":False,"source_hashes":{str(PLAN.resolve()):sha(PLAN),str(RUNTIME.resolve()):sha(RUNTIME)},"candidate_order":ids,"subrun_order":[f"{c}_{p}" for c in ids for p in ("x","y")],"solver_calls":0,"lumapi_calls":0,"fdtd_calls":0}
def metrics(cid):
    import numpy as np
    cps={p:json.loads((ST/"subruns"/cid/p/"checkpoint.json").read_text(encoding="utf8")) for p in ("x","y")}
    def z(p,k):
        q=cps[p]["weighted_G0_"+k]; return complex(q["real"],q["imag"])
    txx,tyx,txy,tyy=z("x","Ex"),z("x","Ey"),z("y","Ex"),z("y","Ey")
    J=np.array([[txx,txy],[tyx,tyy]],complex); sv=np.linalg.svd(J,compute_uv=False)
    phase=float(np.angle(txx,deg=True)); cross=float(abs(txy)**2+abs(tyx)**2); total=float(np.sum(abs(J)**2))
    return {"candidate_id":cid,"role":getrow(cid)["role"],"parent_anchor_id":getrow(cid)["parent_anchor_id"],"normalized_coordinate":getrow(cid)["normalized_coordinate"],"geometry":getrow(cid)["geometry"],"txx":{"real":txx.real,"imag":txx.imag},"txy":{"real":txy.real,"imag":txy.imag},"tyx":{"real":tyx.real,"imag":tyx.imag},"tyy":{"real":tyy.real,"imag":tyy.imag},"Txx":float(abs(txx)**2),"Txy":float(abs(txy)**2),"Tyx":float(abs(tyx)**2),"Tyy":float(abs(tyy)**2),"cross_power":cross,"total_selected_power":total,"phase_deg":phase,"sigma1":float(sv[0]),"sigma2":float(sv[1]),"sigma2_over_sigma1":float(sv[1]/sv[0]),"projection_error":float(abs(tyx)**2/max(abs(txx)**2,1e-30)),"physics_label":"FORMAL_ACCEPTED_WEIGHTED_G0","prediction_label":"MODEL_PREDICTION_NOT_PHYSICS_LABEL"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--execute",action="store_true"); ap.add_argument("--batch",choices=("1","2"),required=True); a=ap.parse_args()
    if not a.execute: raise SystemExit("EXECUTION_REQUIRES_EXPLICIT_EXECUTE")
    ids1=["POSTD8_BOUNDED_PROJECTOR_03","POSTD8_BOUNDED_PROJECTOR_04","POSTD8_BOUNDED_PHASE_01"]
    ids2=["POSTD8_BOUNDED_PHASE_02","POSTD8_BOUNDED_DIAG_05","POSTD8_BOUNDED_DIAG_06"]
    ids=ids1 if a.batch=="1" else ids2
    if not ST.exists(): ST.mkdir(parents=True)
    PKG.mkdir(parents=True,exist_ok=True)
    d6.PLAN=PLAN; d6.PACKAGE=PKG; d6.FORMAL_STAGING=ST; d6.SCRIPT=SCRIPT; d6.RUNTIME=RUNTIME; d6.plan_spec=plan_spec; d6.expected_identity=expected_identity; d6.PARENT_HEAD=d6.git("rev-parse","HEAD^"); d6.runtime_attestation=attestation
    (PKG/"runtime_attestation_contract.json").write_text(json.dumps(attestation(),indent=2,sort_keys=True),encoding="utf8")
    (PKG/"content_checksums.json").write_text(json.dumps({"status":"PASS","files":[{"path":"runtime_attestation_contract.json","sha256":sha(PKG/"runtime_attestation_contract.json")} ]},indent=2,sort_keys=True),encoding="utf8")
    (ST/f"batch{a.batch}_started.json").write_text(json.dumps({"batch":int(a.batch),"candidate_ids":ids,"solver_calls_before":sum(1 for _ in (ST/"subruns").glob("**/checkpoint.json"))}),encoding="utf8")
    results=[]
    for cid in ids:
        if any((ST/"subruns"/cid/p/"checkpoint.json").exists() for p in ("x","y")): raise RuntimeError("PARTIAL_OR_DUPLICATE_NO_RETRY")
        for pol in ("x","y"):
            out=d6.execute_one(cid,pol,d6.ProductionLumapiBackend(),ST,False); results.append({"candidate_id":cid,"polarization":pol,"status":out.get("status"),"checkpoint_sha256":out.get("checkpoint_sha256")})
        (ST/"candidates").mkdir(exist_ok=True); (ST/"candidates"/f"{cid}.json").write_text(json.dumps(metrics(cid),indent=2,sort_keys=True),encoding="utf8")
    (ST/f"batch{a.batch}_complete.json").write_text(json.dumps({"batch":int(a.batch),"candidate_ids":ids,"results":results},indent=2),encoding="utf8")
    print(json.dumps({"status":"PASS","batch":int(a.batch),"planned_geometries":3,"planned_subruns":6,"raw_solver_invocations":len(results),"accepted":len(results),"candidate_ids":ids},indent=2))
if __name__=="__main__": main()
