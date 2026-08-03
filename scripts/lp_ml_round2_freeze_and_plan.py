from __future__ import annotations
import csv,json,hashlib,math,os,random
from pathlib import Path
import numpy as np
R=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4");O=R/"outputs/lp_ml_dataset_v1";A=O/"analysis";P=O/"plans";M=O/"model_runtime_round1_frozen_v1";A.mkdir(parents=True,exist_ok=True);P.mkdir(parents=True,exist_ok=True);M.mkdir(parents=True,exist_ok=True)
DS=O/"lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv";NORM=A/"lp_ml_dataset_v1_round1_train_only_normalization_v1.json";MLPJ=A/"lp_ml_round1_full_residual_mlp_5seed_v1.json"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_csv(p):
 with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def write_csv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True);fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open("w",encoding="utf-8",newline="") as f:w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rows)
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
rows=read_csv(DS);ids=sorted({r["candidate_id"] for r in rows})
if len(ids)!=255 or any("054" in i for i in ids):raise SystemExit("ROUND1_DATASET_GATE")
feat=["J1_side_nm","J2_length_nm","J2_width_nm","D_nm","sin_Psi","cos_Psi","wavelength_nm"];targ=["txx_real","txx_imag","txy_real","txy_imag","tyx_real","tyx_imag","tyy_real","tyy_imag"]
def fx(r):
 p=math.radians(float(r["Psi_deg"]));return [float(r["J1_side_nm"]),float(r["J2_length_nm"]),float(r["J2_width_nm"]),float(r["D_nm"]),math.sin(p),math.cos(p),float(r["wavelength_nm"])]
X=np.asarray([fx(r) for r in rows],np.float64);Y=np.asarray([[float(r[k]) for k in targ] for r in rows],np.float64);train=np.asarray([i for i,r in enumerate(rows) if r.get("split_geometry_level")=="train"],int);val=np.asarray([i for i,r in enumerate(rows) if r.get("split_geometry_level")=="validation"],int);norm=json.loads(NORM.read_text(encoding="utf-8"));mu=np.asarray(norm["mean"],float);sd=np.asarray(norm["std"],float);Xz=(X-mu)/sd
import torch,torch.nn as nn
device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
class B(nn.Module):
 def __init__(self):
  super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class N(nn.Module):
 def __init__(self):
  super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
 def forward(self,x):return self.c(self.b(self.a(x)))
def lossfn(pr,t):
 raw=nn.functional.smooth_l1_loss(pr,t);pt=pr[:,0]**2+pr[:,1]**2;yt=t[:,0]**2+t[:,1]**2;py=pr[:,6]**2+pr[:,7]**2;yy=t[:,6]**2+t[:,7]**2;rel=torch.mean(torch.abs(pr-t)/(torch.abs(t)+1e-3));power=torch.mean(torch.abs(pt-yt)+torch.abs(py-yy));rank=torch.mean(torch.abs(torch.sqrt(pt+py+1e-8)-torch.sqrt(yt+yy+1e-8)));pp=(pr[:,2]**2+pr[:,3]**2+pr[:,4]**2+pr[:,5]**2)/(pt+py+1e-6);qq=(t[:,2]**2+t[:,3]**2+t[:,4]**2+t[:,5]**2)/(yt+yy+1e-6);projection=torch.mean(torch.abs(pp-qq));phase=torch.mean(1-torch.cos(torch.atan2(pr[:,1],pr[:,0])-torch.atan2(t[:,1],t[:,0])));return raw+.25*rel+.10*power+.05*rank+.05*projection+.05*phase
seeds=[11,22,33,44,55];ck=[]
if not all((M/f"residual_mlp_seed_{s}.pt").exists() for s in seeds):
 Xt=torch.tensor(Xz,dtype=torch.float32,device=device);Yt=torch.tensor(Y,dtype=torch.float32,device=device);ti=torch.tensor(train,device=device);vi=torch.tensor(val,device=device)
 for seed in seeds:
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
  model=N().to(device);opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda e:(e+1)/10 if e<10 else 1e-6/3e-4+(1-1e-6/3e-4)*(.5*(1+math.cos(math.pi*(e-10)/(500-10)))));scaler=torch.cuda.amp.GradScaler(enabled=torch.cuda.is_available());best=float("inf");bs=None;bad=0
  for ep in range(500):
   model.train();perm=ti[torch.randperm(len(ti),device=device)]
   for st in range(0,len(perm),64):
    b=perm[st:st+64];opt.zero_grad()
    with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):loss=lossfn(model(Xt[b]),Yt[b])
    scaler.scale(loss).backward();scaler.unscale_(opt);nn.utils.clip_grad_norm_(model.parameters(),1.0);scaler.step(opt);scaler.update()
   sched.step();model.eval()
   with torch.no_grad():v=float(nn.functional.smooth_l1_loss(model(Xt[vi]),Yt[vi]).detach().cpu())
   if v<best-1e-7:best=v;bad=0;bs={k:x.detach().cpu().clone() for k,x in model.state_dict().items()}
   else:bad+=1
   if bad>=50:break
  if bs:model.load_state_dict(bs)
  path=M/f"residual_mlp_seed_{seed}.pt";torch.save(model.state_dict(),path);ck.append({"seed":seed,"checkpoint_path":str(path.relative_to(R)).replace("\\","/"),"checkpoint_sha256":sha(path),"best_validation_raw_smoothl1":best,"epochs":ep+1})
else:
 for s in seeds:
  p=M/f"residual_mlp_seed_{s}.pt";ck.append({"seed":s,"checkpoint_path":str(p.relative_to(R)).replace("\\","/"),"checkpoint_sha256":sha(p)})
freeze={"freeze_version":"LP_ML_ROUND1_MODEL_FREEZE_V1","dataset_path":str(DS.relative_to(R)).replace("\\","/"),"dataset_sha256":sha(DS),"normalization_path":str(NORM.relative_to(R)).replace("\\","/"),"normalization_sha256":sha(NORM),"mlp_json_path":str(MLPJ.relative_to(R)).replace("\\","/"),"mlp_json_sha256":sha(MLPJ),"architecture":"7->256 + 4 residual blocks width256 SiLU LayerNorm dropout0.03 -> 8","feature_order":feat,"target_order":targ,"train_geometry_count":len({rows[i]["candidate_id"] for i in train}),"validation_geometry_count":len({rows[i]["candidate_id"] for i in val}),"from_scratch":True,"warm_start":False,"device":str(device),"cuda_name":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"seeds":ck,"selection_frozen_before_solver":True,"geometry_054_excluded":True};dump(A/"lp_ml_round1_model_freeze_v1.json",freeze)
existing=set()
for c in ids:
 r=next(r for r in rows if r["candidate_id"]==c);existing.add((int(float(r["J1_side_nm"])),int(float(r["J2_length_nm"])),int(float(r["J2_width_nm"])),round(float(r["D_nm"]),6),round(float(r["Psi_deg"]),6),round(float(r.get("J2_center_x_nm",0)),6),round(float(r.get("J2_center_y_nm",0)),6)))
models=[]
for s in seeds:
 m=N();m.load_state_dict(torch.load(M/f"residual_mlp_seed_{s}.pt",map_location="cpu"));m.eval();models.append(m)
rng=np.random.default_rng(20260803);pool=[];seen=set()
for _ in range(700000):
 j1=int(rng.integers(104,113));L=int(rng.integers(106,113));W=int(rng.integers(97,105));ax=float(rng.integers(192,207))/2.;ay=float(rng.integers(-7,8))/2.
 if ax<=0:continue
 D=2*math.hypot(ax,ay);psi=math.degrees(math.atan2(-ay,ax));direct=D-max(j1,L);periodic=432-D-max(j1,L)
 if direct<60 or periodic<60:continue
 key=(j1,L,W,round(D,6),round(psi,6),round(ax,6),round(ay,6))
 if key in seen or key in existing:continue
 seen.add(key);pr=[]
 for wl in [450+i*.5 for i in range(9)]:
  a=math.radians(psi);pr.append([j1,L,W,D,math.sin(a),math.cos(a),wl])
 Pz=(np.asarray(pr)-mu)/sd
 with torch.no_grad():
  xt=torch.tensor(Pz,dtype=torch.float32)
  vv=[m(xt).numpy() for m in models]
 vv=np.asarray(vv);cm=vv.mean(0);cs=vv.std(0);mid=cm[4];u=float(np.linalg.norm(cs[4]));J=np.array([[complex(mid[0],mid[1]),complex(mid[2],mid[3])],[complex(mid[4],mid[5]),complex(mid[6],mid[7])]]);sv=np.linalg.svd(J,compute_uv=False);phase=float(((math.degrees(math.atan2(J[0,0].imag,J[0,0].real))+180)%360)-180);Txx=float(abs(J[0,0])**2);Tyy=float(abs(J[1,1])**2);cross=float(abs(J[0,1])**2+abs(J[1,0])**2);leak=Tyy+cross;sig=float(sv[1]/sv[0]) if sv[0]>0 else 1.;proj=float(1-abs(J[0,0])**2/(np.linalg.norm(J)**2+1e-12))
 geom={"J1_side_nm":j1,"J2_length_nm":L,"J2_width_nm":W,"D_nm":D,"Psi_deg":psi,"J1_center_x_nm":-ax,"J1_center_y_nm":-ay,"J2_center_x_nm":ax,"J2_center_y_nm":ay,"H_nm":500.,"period_x_nm":432.,"period_y_nm":432.,"material":"APCD_TIO2_NATIVE_M1"}
 exact=hashlib.sha256(json.dumps(geom,sort_keys=True,separators=(",",":")).encode()).hexdigest();canon=hashlib.sha256(json.dumps({"J1_side_nm":j1,"J2_length_nm":L,"J2_width_nm":W,"D_nm":round(D,6),"Psi_abs_deg":round(abs(psi),6)},sort_keys=True,separators=(",",":")).encode()).hexdigest();sym=hashlib.sha256(json.dumps({"J1_side_nm":j1,"J2_length_nm":L,"J2_width_nm":W,"D_nm":round(D,6),"Psi_abs_deg":round(abs(psi),6),"axis_swap":False},sort_keys=True,separators=(",",":")).encode()).hexdigest()
 pool.append({**geom,"exact_geometry_hash_sha256":exact,"canonical_relative_geometry_hash_sha256":canon,"symmetry_equivalence_geometry_hash_sha256":sym,"direct_gap_nm":direct,"periodic_gap_nm":periodic,"geometry_legality":"PASS","manufacturing_pass":"True","pred_phase_deg":phase,"pred_Txx":Txx,"pred_Tyy":Tyy,"pred_cross_power":cross,"pred_combined_leakage":leak,"pred_sigma2_over_sigma1":sig,"pred_projection_error":proj,"ensemble_uncertainty":u})
 if len(pool)>=60000:break
if len(pool)<50000:raise SystemExit("POOL_TOO_SMALL:"+str(len(pool)))
def vec(q):return np.array([q["J1_side_nm"],q["J2_length_nm"],q["J2_width_nm"],q["D_nm"],math.sin(math.radians(q["Psi_deg"])),math.cos(math.radians(q["Psi_deg"]))])
scale=np.array([8.,8.,8.,14.,2.,2.]);chosen=[]
def dist(q,chs):return float(min(np.linalg.norm((vec(q)-vec(x))/scale) for x in chs)) if chs else 0.
def pick(cat,n,score):
 cand=sorted(pool,key=score,reverse=True);sel=[]
 for q in cand:
  if len(sel)>=n:break
  if q["exact_geometry_hash_sha256"] in {x["exact_geometry_hash_sha256"] for x in chosen}:continue
  if not sel or min(np.linalg.norm((vec(q)-vec(x))/scale) for x in sel)>=.12:
   z=dict(q);z["category"]=cat;z["acquisition_score"]=float(score(q));sel.append(z);chosen.append(z)
 if len(sel)<n:
  for q in cand:
   if len(sel)>=n:break
   if q["exact_geometry_hash_sha256"] not in {x["exact_geometry_hash_sha256"] for x in chosen}:
    z=dict(q);z["category"]=cat;z["acquisition_score"]=float(score(q));sel.append(z);chosen.append(z)
 return sel
groups=[];groups+=pick("HIGH_UNCERTAINTY",20,lambda q:q["ensemble_uncertainty"]+.05*dist(q,chosen));groups+=pick("LOW_PHASE_AND_SIX_BIN_COVERAGE",16,lambda q:-abs(q["pred_phase_deg"])+.2*dist(q,chosen));groups+=pick("PROJECTOR_FAVORABLE_TRADEOFF",12,lambda q:q["pred_Txx"]-1.5*q["pred_combined_leakage"]-.5*q["pred_sigma2_over_sigma1"]+.1*dist(q,chosen));groups+=pick("BOUNDARY_AND_HIGH_GRADIENT",8,lambda q:q["ensemble_uncertainty"]+1/(q["direct_gap_nm"]-59.5)+1/(q["periodic_gap_nm"]-59.5));groups+=pick("DIVERSITY_CONTROLS",8,lambda q:dist(q,chosen))
if len(groups)!=64:raise SystemExit("SELECTION_COUNT:"+str(len(groups)))
for i,q in enumerate(groups):
 q["candidate_id"]=f"LPML_R2_{q['category']}_{i+1:03d}";q["candidate_order"]=i+1;q["solver_status"]="PLANNED_NOT_RUN";q["physics_status"]="ABSENT_NOT_SIMULATED";q["prediction_status"]="MODEL_PREDICTION_NOT_PHYSICS_LABEL";q["wavelength_authorization"]="450.0-454.0_nm_step_0.5_nm";q["run_polarizations"]="x,y";q["geometry_054_excluded"]="True";q["no_replacement"]="True";q["source_model_freeze_sha256"]=sha(A/"lp_ml_round1_model_freeze_v1.json")
write_csv(A/"lp_ml_round2_feasible_candidate_pool_60000_v1.csv",pool);write_csv(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv",groups);ph=sha(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv")
dump(P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.json",{"plan_version":"LP_ML_ROUND2_64_TARGETED_ACTIVE_LEARNING_V1","candidate_count":64,"subrun_ceiling":128,"wavelengths_nm":[450+i*.5 for i in range(9)],"strata_quota":{"HIGH_UNCERTAINTY":20,"LOW_PHASE_AND_SIX_BIN_COVERAGE":16,"PROJECTOR_FAVORABLE_TRADEOFF":12,"BOUNDARY_AND_HIGH_GRADIENT":8,"DIVERSITY_CONTROLS":8},"plan_csv_sha256":ph,"pool_csv_sha256":sha(A/"lp_ml_round2_feasible_candidate_pool_60000_v1.csv"),"round1_model_freeze_sha256":sha(A/"lp_ml_round1_model_freeze_v1.json"),"geometry_054_excluded":True,"existing_geometry_count":255,"new_geometry_hash_unique":len({q["exact_geometry_hash_sha256"] for q in groups})==64,"solver_authorized":True,"no_dynamic_replacement":True,"selection_frozen_before_solver":True})
dump(P/"lp_ml_dataset_v1_round2_execution_contract_v1.json",{"execution_contract_version":"LP_ML_ROUND2_EXECUTION_V1","attempt_id":"LP_ML_ROUND2_ACTIVE_LEARNING_ATTEMPT1_V1","plan_path":str((P/"lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv").relative_to(R)).replace("\\","/"),"plan_sha256":ph,"authorized_geometries":64,"authorized_new_subruns_max":128,"wavelengths_nm":[450+i*.5 for i in range(9)],"physics_contract":"frozen broadband Native-M1 weighted-G0, transmission field monitor z=1000 nm, sqrt(T)/norm(weighted Ex,Ey), endpoint deduplication, periodic reclosure","material":"APCD_TIO2_NATIVE_M1","H_nm":500.,"period_nm":432.,"split_before_retraining":{"external_test_geometry_count":8,"augmentation_train_geometry_count":48,"augmentation_validation_geometry_count":8},"geometry_054_policy":"permanently quarantined; no retry or replacement","entered_failure_policy":"ISOLATED_ENTERED_FAILURE_QUARANTINE_AND_CONTINUE_V1","forbidden":["Round-3 solver","inverse-candidate FDTD","six-bin promotion","K6","D9","Batch B","old Batch2","protected report rewrite","geometry replacement","plan expansion"],"solver_calls_at_freeze":0})
dump(A/"lp_ml_provenance_exception_attestation_v1.json",{"exception_version":"LP_ML_PROVENANCE_EXCEPTION_ACCEPTED_V1","authorized_date":"2026-08-03","affected_artifact":"reports/lp_ml1a3_git_history_geometry_reconstruction.md","historical_expected_sha256":"21c6884f71bad6bd6779d7ccc90cec55ab1a94e239f849ea74a942bdd50edd6a","task_start_sha256":"d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161","current_sha256":"171033e0d2c73865d0f8610e81d5a33de56d7deb79d8d38aa2f925f7e17e8321","classification":"UNRECOVERABLE_DERIVED_REPORT_BYTE_IDENTITY_EXCEPTION_ACCEPTED","physics_evidence_unchanged":True,"protected_report_2_sha256":"ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708","does_not_authorize_physics_contract_weakening":True})
dump(A/"lp_ml_round2_candidate_prediction_freeze_v1.json",{"plan_sha256":ph,"model_freeze_sha256":sha(A/"lp_ml_round1_model_freeze_v1.json"),"candidate_count":64,"prediction_frozen_before_solver":True,"model_checkpoint_hashes":[x["checkpoint_sha256"] for x in ck]})
print(json.dumps({"pool":len(pool),"selected":len(groups),"plan_sha256":ph,"device":str(device),"model_freeze":sha(A/"lp_ml_round1_model_freeze_v1.json")},indent=2))
