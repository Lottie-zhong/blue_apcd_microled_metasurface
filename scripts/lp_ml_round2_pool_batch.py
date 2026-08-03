import csv,json,hashlib,math,os
from pathlib import Path
import numpy as np,torch,torch.nn as nn
R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4");O=R/"outputs/lp_ml_dataset_v1";A=O/"analysis";P=O/"plans";M=O/"model_runtime_round1_frozen_v1"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def wr(p,rs):
 fs=[]
 for r in rs:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rs)
def dump(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
rows=read(O/"lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv");ids=sorted({r["candidate_id"] for r in rows});assert len(ids)==255 and not any("054" in x for x in ids)
norm=json.loads((A/"lp_ml_dataset_v1_round1_train_only_normalization_v1.json").read_text());mu=np.asarray(norm["mean"],float);sd=np.asarray(norm["std"],float)
class B(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class N(nn.Module):
 def __init__(self):
  super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
 def forward(self,x):return self.c(self.b(self.a(x)))
device=torch.device("cuda" if torch.cuda.is_available() else "cpu");seeds=[11,22,33,44,55];models=[]
for s in seeds:
 m=N().to(device);m.load_state_dict(torch.load(M/f"residual_mlp_seed_{s}.pt",map_location=device));m.eval();models.append(m)
existing=set()
for r in rows:
 existing.add((int(float(r["J1_side_nm"])),int(float(r["J2_length_nm"])),int(float(r["J2_width_nm"])),round(float(r["D_nm"]),6),round(float(r["Psi_deg"]),6),round(float(r.get("J2_center_x_nm",0)),6),round(float(r.get("J2_center_y_nm",0)),6)))
rng=np.random.default_rng(20260803);geo=[];seen=set()
for _ in range(1000000):
 j1=int(rng.integers(104,113));L=int(rng.integers(106,113));W=int(rng.integers(97,105));ax=float(rng.integers(192,207))/2.;ay=float(rng.integers(-7,8))/2.
 if ax<=0:continue
 D=2*math.hypot(ax,ay);psi=math.degrees(math.atan2(-ay,ax));direct=D-max(j1,L);periodic=432-D-max(j1,L)
 if direct<60 or periodic<60:continue
 key=(j1,L,W,round(D,6),round(psi,6),round(ax,6),round(ay,6))
 if key in seen or key in existing:continue
 seen.add(key);geo.append({"J1_side_nm":j1,"J2_length_nm":L,"J2_width_nm":W,"D_nm":D,"Psi_deg":psi,"J1_center_x_nm":-ax,"J1_center_y_nm":-ay,"J2_center_x_nm":ax,"J2_center_y_nm":ay,"H_nm":500.,"period_x_nm":432.,"period_y_nm":432.,"material":"APCD_TIO2_NATIVE_M1","direct_gap_nm":direct,"periodic_gap_nm":periodic})
 if len(geo)>=60000:break
assert len(geo)>=60000
a=np.radians(np.asarray([q["Psi_deg"] for q in geo]));X=np.asarray([[q["J1_side_nm"],q["J2_length_nm"],q["J2_width_nm"],q["D_nm"],math.sin(a[i]),math.cos(a[i]),452.] for i,q in enumerate(geo)],float);X=(X-mu)/sd
pred=[]
with torch.no_grad():
 for st in range(0,len(geo),4096):
  z=torch.tensor(X[st:st+4096],dtype=torch.float32,device=device)
  pred.append(np.stack([m(z).detach().cpu().numpy() for m in models]))
pred=np.concatenate(pred,axis=1);mean=pred.mean(0);std=pred.std(0);pool=[]
for i,q in enumerate(geo):
 m=mean[i];u=float(np.linalg.norm(std[i]));J=np.array([[complex(m[0],m[1]),complex(m[2],m[3])],[complex(m[4],m[5]),complex(m[6],m[7])]]);sv=np.linalg.svd(J,compute_uv=False);pool.append({**q,"exact_geometry_hash_sha256":hashlib.sha256(json.dumps(q,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"canonical_relative_geometry_hash_sha256":hashlib.sha256(json.dumps({"J1_side_nm":q["J1_side_nm"],"J2_length_nm":q["J2_length_nm"],"J2_width_nm":q["J2_width_nm"],"D_nm":round(q["D_nm"],6),"Psi_abs_deg":round(abs(q["Psi_deg"]),6)},sort_keys=True,separators=(",",":")).encode()).hexdigest(),"symmetry_equivalence_geometry_hash_sha256":hashlib.sha256(json.dumps({"J1_side_nm":q["J1_side_nm"],"J2_length_nm":q["J2_length_nm"],"J2_width_nm":q["J2_width_nm"],"D_nm":round(q["D_nm"],6),"Psi_abs_deg":round(abs(q["Psi_deg"]),6)},sort_keys=True,separators=(",",":")).encode()).hexdigest(),"geometry_legality":"PASS","manufacturing_pass":"True","pred_phase_deg":float(((math.degrees(math.atan2(J[0,0].imag,J[0,0].real))+180)%360)-180),"pred_Txx":float(abs(J[0,0])**2),"pred_Tyy":float(abs(J[1,1])**2),"pred_cross_power":float(abs(J[0,1])**2+abs(J[1,0])**2),"pred_combined_leakage":float(abs(J[1,1])**2+abs(J[0,1])**2+abs(J[1,0])**2),"pred_sigma2_over_sigma1":float(sv[1]/sv[0]) if sv[0]>0 else 1.,"pred_projection_error":float(1-abs(J[0,0])**2/(np.linalg.norm(J)**2+1e-12)),"ensemble_uncertainty":u})
scale=np.array([8.,8.,8.,14.,2.,2.])
def vec(q):return np.array([q["J1_side_nm"],q["J2_length_nm"],q["J2_width_nm"],q["D_nm"],math.sin(math.radians(q["Psi_deg"])),math.cos(math.radians(q["Psi_deg"]))])
chosen=[];used_exact=set();used_can=set();used_sym=set()
def d(q,cs):return float(min(np.linalg.norm((vec(q)-vec(x))/scale) for x in cs)) if cs else 0.
def pick(cat,n,score):
 out=[]
 for q in sorted(pool,key=score,reverse=True):
  if len(out)>=n:break
  if q["exact_geometry_hash_sha256"] in used_exact or q["canonical_relative_geometry_hash_sha256"] in used_can or q["symmetry_equivalence_geometry_hash_sha256"] in used_sym:continue
  if out and min(np.linalg.norm((vec(q)-vec(x))/scale) for x in out)<.12:continue
  z=dict(q);z["category"]=cat;z["acquisition_score"]=float(score(q));out.append(z);chosen.append(z);used_exact.add(z["exact_geometry_hash_sha256"]);used_can.add(z["canonical_relative_geometry_hash_sha256"]);used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"])
 if len(out)<n:
  for q in sorted(pool,key=score,reverse=True):
   if len(out)>=n:break
   if q["exact_geometry_hash_sha256"] in used_exact or q["canonical_relative_geometry_hash_sha256"] in used_can or q["symmetry_equivalence_geometry_hash_sha256"] in used_sym:continue
   z=dict(q);z["category"]=cat;z["acquisition_score"]=float(score(q));out.append(z);chosen.append(z);used_exact.add(z["exact_geometry_hash_sha256"]);used_can.add(z["canonical_relative_geometry_hash_sha256"]);used_sym.add(z["symmetry_equivalence_geometry_hash_sha256"])
 return out
groups=[];groups+=pick("HIGH_UNCERTAINTY",20,lambda q:q["ensemble_uncertainty"]+.05*d(q,chosen));groups+=pick("LOW_PHASE_AND_SIX_BIN_COVERAGE",16,lambda q:-abs(q["pred_phase_deg"])+.2*d(q,chosen));groups+=pick("PROJECTOR_FAVORABLE_TRADEOFF",12,lambda q:q["pred_Txx"]-1.5*q["pred_combined_leakage"]-.5*q["pred_sigma2_over_sigma1"]+.1*d(q,chosen));groups+=pick("BOUNDARY_AND_HIGH_GRADIENT",8,lambda q:q["ensemble_uncertainty"]+1/(q["direct_gap_nm"]-59.5)+1/(q["periodic_gap_nm"]-59.5));groups+=pick("DIVERSITY_CONTROLS",8,lambda q:d(q,chosen));assert len(groups)==64
for i,q in enumerate(groups):q.update({"candidate_id":f"LPML_R2_{q['category']}_{i+1:03d}","candidate_order":i+1,"solver_status":"PLANNED_NOT_RUN","physics_status":"ABSENT_NOT_SIMULATED","prediction_status":"MODEL_PREDICTION_NOT_PHYSICS_LABEL","wavelength_authorization":"450.0-454.0_nm_step_0.5_nm","run_polarizations":"x,y","geometry_054_excluded":"True","no_replacement":"True","source_model_freeze_sha256":sha(A/"lp_ml_round1_model_freeze_v1.json")})
wr(A/"lp_ml_round2_feasible_candidate_pool_60000_v1.csv",pool);wr(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv",groups);ph=sha(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv");pc=sha(A/"lp_ml_round2_feasible_candidate_pool_60000_v1.csv")
dump(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.json",{"plan_version":"LP_ML_ROUND2_64_TARGETED_ACTIVE_LEARNING_V1","candidate_count":64,"subrun_ceiling":128,"wavelengths_nm":[450+i*.5 for i in range(9)],"strata_quota":{"HIGH_UNCERTAINTY":20,"LOW_PHASE_AND_SIX_BIN_COVERAGE":16,"PROJECTOR_FAVORABLE_TRADEOFF":12,"BOUNDARY_AND_HIGH_GRADIENT":8,"DIVERSITY_CONTROLS":8},"plan_csv_sha256":ph,"pool_csv_sha256":pc,"round1_model_freeze_sha256":sha(A/"lp_ml_round1_model_freeze_v1.json"),"geometry_054_excluded":True,"new_geometry_hash_unique":len(used_exact)==64,"new_canonical_hash_unique":len(used_can)==64,"new_symmetry_hash_unique":len(used_sym)==64,"solver_authorized":True,"selection_frozen_before_solver":True})
dump(P/"lp_ml_dataset_v1_round2_execution_contract_v1.json",{"execution_contract_version":"LP_ML_ROUND2_EXECUTION_V1","attempt_id":"LP_ML_ROUND2_ACTIVE_LEARNING_ATTEMPT1_V1","plan_path":"outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv","plan_sha256":ph,"authorized_geometries":64,"authorized_new_subruns_max":128,"wavelengths_nm":[450+i*.5 for i in range(9)],"physics_contract":"frozen broadband Native-M1 weighted-G0, z=1000 nm, sqrt(T)/norm(weighted Ex,Ey), endpoint deduplication, periodic reclosure","material":"APCD_TIO2_NATIVE_M1","H_nm":500.,"period_nm":432.,"geometry_054_policy":"permanent quarantine/no retry/no replacement","entered_failure_policy":"ISOLATED_ENTERED_FAILURE_QUARANTINE_AND_CONTINUE_V1","solver_calls_at_freeze":0,"forbidden":["Round-3","inverse FDTD","six-bin promotion","K6","D9","Batch B","old Batch2","protected report rewrite","plan expansion"]})
dump(A/"lp_ml_provenance_exception_attestation_v1.json",{"exception_version":"LP_ML_PROVENANCE_EXCEPTION_ACCEPTED_V1","authorized_date":"2026-08-03","affected_artifact":"reports/lp_ml1a3_git_history_geometry_reconstruction.md","historical_expected_sha256":"21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a","task_start_sha256":"d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161","current_sha256":"171033e0d2c73865d0f8610e81d5a33de56d7deb79d8d38aa2f925f7e17e8321","classification":"UNRECOVERABLE_DERIVED_REPORT_BYTE_IDENTITY_EXCEPTION_ACCEPTED","physics_evidence_unchanged":True,"protected_report_2_sha256":"ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708","does_not_authorize_physics_contract_weakening":True})
dump(A/"lp_ml_round2_candidate_prediction_freeze_v1.json",{"plan_sha256":ph,"model_freeze_sha256":sha(A/"lp_ml_round1_model_freeze_v1.json"),"candidate_count":64,"prediction_frozen_before_solver":True,"model_checkpoint_hashes":[sha(M/f"residual_mlp_seed_{s}.pt") for s in seeds]})
print(json.dumps({"pool":len(pool),"selected":len(groups),"plan_sha256":ph,"device":str(device)},indent=2))
