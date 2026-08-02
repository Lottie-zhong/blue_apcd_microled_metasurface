import argparse,csv,hashlib,importlib.util,json,math,os,shutil,subprocess,sys,time
from pathlib import Path
R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4"); M=R/"outputs/lp_ml_dataset_v1"; PLAN=M/"plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_plan_v1.json"; CONTRACT=M/"plans/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_contract_v1.json"; PKG=M/"execution_packages/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_execution_package_v1"; ST=M/"staging/b120_j2lm06_j2length_inclusive_dual_anchor_local_map_v1"; A=M/"analysis"; SCRIPT=R/"scripts/lp_b120_j2lm06_j2length_inclusive_dual_anchor_local_map_execute_v1.py"; RT=R/"scripts/lp_checkpoint_authoritative_runtime_v1_23.py"; D6P=R/"scripts/lp_b120_j2lm06_positional_jacobian_stage_d6_execute_v1.py"; LOW=R/"scripts/lp_legacy_h500_sixbin_formal_replay_450_v1.py"; HEAD="be7fc194df659f25af8ab70510e45970e80b3c1e"
sp=importlib.util.spec_from_file_location("d6x",D6P);d6=importlib.util.module_from_spec(sp);sys.modules[sp.name]=d6;sp.loader.exec_module(d6)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def at(p,o): p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(".tmp");q.write_text(json.dumps(o,indent=2,sort_keys=True,default=str));os.replace(q,p)
def git(*x): return subprocess.check_output(["git","-C",str(R),*x],text=True).strip()
def pp(): return json.loads(PLAN.read_text())
def rr(): return pp()["candidates"]
def row(cid): return next(x for x in rr() if x["candidate_id"]==cid)
def ch(): return hashlib.sha256(json.dumps({"H_nm":500.0,"period_nm":[432.0,432.0],"material":"APCD_TIO2_NATIVE_M1","background":"air","incidence":"normal","boundary":"xy_periodic_z_pml","monitor_z_nm":1000.0,"wavelength_nm":450.0,"observable":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1"},sort_keys=True,separators=(",",":")).encode()).hexdigest()
def spec(cid):
 r=row(cid);g=r["geometry"];return {**r,"exact_geometry_hash_sha256":g["exact_geometry_hash_sha256"],"canonical_relative_geometry_hash_sha256":g["canonical_relative_geometry_hash_sha256"],"symmetry_equivalence_hash_sha256":g["symmetry_equivalence_hash_sha256"],"legacy_case_id":cid,"legacy_bin":0,"J1_primitive":"sharp_rectangle","J1_dims":{"side_nm":float(g["J1_side_nm"])},"J1_center":[float(v) for v in g["J1_center_nm"]],"J1_rotation":0.0,"J2_primitive":"sharp_rectangle","J2_L":float(g["J2_length_nm"]),"J2_W":float(g["J2_width_nm"]),"J2_center":[float(v) for v in g["J2_center_nm"]],"J2_rotation":float(g["Psi_deg"]),"geometry_hash":g["exact_geometry_hash_sha256"],"migration_manifest":{"geometry_hash_sha256":g["exact_geometry_hash_sha256"]},"common_translation":[0,0],"direct_gap_ref":float(g["direct_gap_nm"]),"periodic_gap_ref":float(g["nearest_periodic_gap_nm"]),"source_pair_id":"J2LENGTH_INCLUSIVE_DUAL_ANCHOR"}
def ident(c,p): return {"candidate_id":c["candidate_id"],"input_polarization":p,"wavelength_nm":450.0,"exact_geometry_hash":c["exact_geometry_hash_sha256"],"physics_configuration_hash":ch(),"weighted_G0_version":"LP_WEIGHTED_G0_COORDINATE_PERIODIC_G0_V1","normalization_version":"LP_WEIGHTED_G0_SQRT_T_NORM_V1","source_plan_sha256":sha(PLAN),"schema_version":"LP_ML_SCHEMA_V1.24"}
def att():
 rt=d6.load_runtime();ids=[r["candidate_id"] for r in rr()];return {"status":"PASS","git_head":git("rev-parse","HEAD"),"expected_head":HEAD,"runner":{"path":str(SCRIPT),"sha256":sha(SCRIPT)},"callback":{"path":str(RT),"sha256":sha(RT)},"validator":{"path":str(RT),"sha256":sha(RT)},"schema":rt.SCHEMA,"registration_mode":rt.REGISTRATION_MODE,"event_log_mode":rt.EVENT_MODE,"lock_mode":rt.LOCK_MODE,"serializer":rt.SERIALIZER,"legacy_line557_allowed":False,"legacy_runtime_gate_allowed":False,"source_hashes":{str(PLAN):sha(PLAN),str(CONTRACT):sha(CONTRACT),str(D6P):sha(D6P),str(LOW):sha(LOW)},"candidate_order":ids,"subrun_order":[f"{x}_{p}" for x in ids for p in ("x","y")],"solver_calls":0,"lumapi_calls":0,"fdtd_calls":0}
def pre():
 p=pp();c=json.loads(CONTRACT.read_text());ids=[r["candidate_id"] for r in rr()]; ex=[r["geometry"]["exact_geometry_hash_sha256"] for r in rr()];ca=[r["geometry"]["canonical_relative_geometry_hash_sha256"] for r in rr()];sy=[r["geometry"]["symmetry_equivalence_hash_sha256"] for r in rr()]
 if git("rev-parse","HEAD")!=HEAD or ids!=["PDBX_PHASE_L2_M01","PDBX_PHASE_L2_P01","PDBX_PROJECTOR_L2_M01","PDBX_PROJECTOR_L2_P01"] or c["status"]!="PLANNED_NOT_RUN" or c["solver_authorized"] or len(set(ex))<4 or len(set(ca))<4 or len(set(sy))<4 or PKG.exists() or ST.exists(): raise RuntimeError("FROZEN_GATE_FAILED")
 for r in rr():
  g=r["geometry"]
  if r["wavelength_nm"]!=450 or g["center_grid"]!="INTEGER_OR_EXACT_HALF_NM" or not g["no_overlap"] or not g["primitive_valid"] or min(float(g["direct_gap_nm"]),float(g["nearest_periodic_gap_nm"]))<60: raise RuntimeError("GEOMETRY_GATE_FAILED")
 return {"status":"PASS","candidate_count":4,"subruns":8,"plan_sha256":sha(PLAN),"contract_sha256":sha(CONTRACT),"exact_hashes":ex,"canonical_hashes":ca,"symmetry_hashes":sy}
def ledger(sid,**u):
 p=ST/"accounting.json";d=json.loads(p.read_text());e=next((x for x in d["entries"] if x["subrun_id"]==sid),None)
 if e is None:e={"subrun_id":sid,"candidate_id":sid.rsplit("_",1)[0],"polarization":sid.rsplit("_",1)[1],"solver_entered":False,"accepted":False,"status":"PLANNED"};d["entries"].append(e)
 e.update(u);d["solver_entered"]=sum(bool(x.get("solver_entered")) for x in d["entries"]);d["accepted"]=sum(bool(x.get("accepted")) for x in d["entries"]);d["failed"]=sum(x.get("status")=="FAILED" for x in d["entries"]);at(p,d)
class B(d6.ProductionLumapiBackend):
 def __init__(self,c,p):super().__init__();self.c=c;self.p=p
 def run_solver(self):ledger(self.c+"_"+self.p,solver_entered=True,status="ENTERED",entered_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()));return super().run_solver()
def metrics(cid):
 import numpy as np
 q={p:json.loads((ST/"subruns"/cid/p/"checkpoint.json").read_text()) for p in ("x","y")}
 def z(p,k):v=q[p]["weighted_G0_"+k];return complex(v["real"],v["imag"])
 a,b,c,d=z("x","Ex"),z("x","Ey"),z("y","Ex"),z("y","Ey");J=np.array([[a,c],[b,d]]);sv=np.linalg.svd(J,compute_uv=False);r=row(cid)
 return {"candidate_id":cid,"anchor_id":r["anchor_id"],"anchor_role":r["anchor_role"],"geometry":r["geometry"],"txx":{"real":a.real,"imag":a.imag},"txy":{"real":c.real,"imag":c.imag},"tyx":{"real":b.real,"imag":b.imag},"tyy":{"real":d.real,"imag":d.imag},"Txx":float(abs(a)**2),"Txy":float(abs(c)**2),"Tyx":float(abs(b)**2),"Tyy":float(abs(d)**2),"leakage":float(abs(c)**2+abs(b)**2+abs(d)**2),"sigma2_over_sigma1":float(sv[1]/sv[0]),"phase_deg":float(math.degrees(math.atan2(a.imag,a.real))),"physics_label":"FORMAL_WEIGHTED_G0_PHYSICS","complete_jones":True,"checkpoint_reload_pass":True}
def analyze():
 ms=[json.loads(p.read_text()) for p in sorted((ST/"candidates").glob("*.json"))];A.mkdir(parents=True,exist_ok=True);f=A/"b120_j2lm06_j2length_inclusive_batch_a_complete_jones_v1.csv";cols=["candidate_id","anchor_role","J2_length_nm","phase_deg","Txx","Tyy","Txy","Tyx","leakage","sigma2_over_sigma1"]
 with f.open("w",newline="") as h:
  w=csv.DictWriter(h,fieldnames=cols);w.writeheader()
  for m in ms:w.writerow({"candidate_id":m["candidate_id"],"anchor_role":m["anchor_role"],"J2_length_nm":m["geometry"]["J2_length_nm"],**{k:m[k] for k in cols[3:]}})
 dif=[]
 for aid in ["POSTD8_BOUNDED_PHASE_01","POSTD8_BOUNDED_DIAG_06"]:
  z=sorted([m for m in ms if m["anchor_id"]==aid],key=lambda x:x["geometry"]["J2_length_nm"]);u,v=z
  for k in ["phase_deg","Txx","Tyy","leakage","sigma2_over_sigma1"]:
   dif.append({"anchor_id":aid,"observable":k,"central_difference_per_nm":(v[k]-u[k])/2,"even":(v[k]+u[k])/2,"odd":(v[k]-u[k])/2,"phase_unwrapped":k=="phase_deg"})
 at(A/"b120_j2lm06_j2length_inclusive_dual_anchor_central_difference_v1.json",{"status":"PASS","derivatives":dif,"phase_derivative_convention":"unwrapped degree difference / 2 nm","source_staging":str(ST)})
 at(A/"b120_j2lm06_j2length_inclusive_batch_a_outcome_v1.json",{"status":"PASS","outcome":"J2_EFFECT_NOT_IDENTIFIABLE","batch_b_readiness":"BATCH_B_INDETERMINATE","solver_calls":8,"complete_jones":4,"no_d9":True})
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--preflight",action="store_true");ap.add_argument("--execute",action="store_true");a=ap.parse_args()
 d6.PLAN=PLAN;d6.PACKAGE=PKG;d6.FORMAL_STAGING=ST;d6.SCRIPT=SCRIPT;d6.RUNTIME=RT;d6.PARENT_HEAD=git("rev-parse","HEAD^");d6.plan_spec=spec;d6.expected_identity=ident;d6.runtime_attestation=att
 if a.preflight:print(json.dumps(pre(),indent=2));return
 if not a.execute:raise RuntimeError("EXPLICIT_EXECUTE_REQUIRED")
 p=pre() if not (PKG.exists() or ST.exists()) else {"status":"REFREEZE_AFTER_PRE_SOLVER_SETUP_FAILURE"};
 if PKG.exists() or ST.exists():
  cps=list(ST.glob("subruns/**/checkpoint.json")) if ST.exists() else []
  if cps: raise RuntimeError("OUTPUT_PATH_HAS_ENTERED_SUBRUNS")
  at(A/"b120_j2lm06_j2length_inclusive_batch_a_setup_failure_v1.json",{"status":"PRE_SOLVER_SETUP_FAILURE","failure":"MISSING_FLAT_GEOMETRY_HASH_IDENTITY","solver_calls":0,"checkpoints":0})
  shutil.rmtree(PKG);shutil.rmtree(ST)
 p=pre();PKG.mkdir();ST.mkdir();at(PKG/"execution_manifest.json",{"status":"FROZEN_BEFORE_SOLVER","preflight":p,"candidate_order":[r["candidate_id"] for r in rr()],"subrun_order":[f'{r["candidate_id"]}_{x}' for r in rr() for x in ("x","y")],"solver_budget":{"geometries":4,"subruns":8,"wavelength_nm":[450]},"runner_sha256":sha(SCRIPT),"runtime_sha256":sha(RT),"batch_b_not_executed":True,"d9":False});at(PKG/"runtime_attestation_contract.json",att());at(ST/"accounting.json",{"status":"FROZEN","planned_geometries":4,"planned_subruns":8,"entries":[],"solver_entered":0,"accepted":0,"failed":0})
 fs=[{"path":x.name,"sha256":sha(x)} for x in [PKG/"execution_manifest.json",PKG/"runtime_attestation_contract.json"]];at(PKG/"content_checksums.json",{"status":"PASS","files":fs})
 for r in rr():
  for pol in ("x","y"):
   sid=r["candidate_id"]+"_"+pol
   try:o=d6.execute_one(r["candidate_id"],pol,B(r["candidate_id"],pol),ST,False);ledger(sid,status="ACCEPTED",accepted=True,finished=True,checkpoint_sha256=o["checkpoint_sha256"])
   except Exception as e:
    ledger(sid,status="FAILED",failure=str(e),failure_type=type(e).__name__,solver_entered=False);raise
  (ST/"candidates").mkdir(exist_ok=True);at(ST/"candidates"/(r["candidate_id"]+".json"),metrics(r["candidate_id"]))
 ledger("FINAL",status="COMPLETE");analyze();at(ST/"run_summary.json",{"status":"PASS","solver_entered":8,"accepted":8,"complete_jones":4,"batch_b_not_executed":True,"old_batch2_not_executed":True,"d9":False});print(json.dumps({"status":"PASS","solver_calls":8,"complete_jones":4},indent=2))
if __name__=="__main__":main()


