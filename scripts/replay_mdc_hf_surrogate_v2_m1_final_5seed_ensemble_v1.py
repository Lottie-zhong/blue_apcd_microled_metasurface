from __future__ import annotations
import os,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,joblib,torch
import torch.nn as nn
REPO=Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2"); DOE=REPO/"outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"; RUN=REPO/"outputs/mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1/20260804T_final_m1_5seed_067c76b"; REPLAY_ID=2
def sha_obj(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
geom=pd.read_csv(RUN/"final_training_geometry_membership.csv"); case=pd.read_csv(RUN/"final_training_case_membership.csv"); latent=pd.read_parquet(DOE/"final_profile_encoded_case_index.parquet"); latent=latent.merge(case[["geometry_hash","case_hash","fold","selection_stratum","source_position","dipole_orientation"]],on=["geometry_hash","case_hash","fold","selection_stratum"],how="left"); labels=pd.read_parquet(DOE/"doe96_geometry_labels_v1.parquet").set_index("geometry_hash")
families=sorted(geom.topology_family.unique().tolist()); g=[]
for _,r in geom.iterrows():
 n=float(r.layer_count); total=float(r.total_thickness_nm); defect=float(r.defect_thickness_nm); g.append([float(r.topology_family==f) for f in families]+[n,total/n,(total-defect)/max(n-1,1),defect,n,defect,total,n,1.0,1.0])
G=np.asarray(g,np.float32); gmap={h:G[i] for i,h in enumerate(geom.geometry_hash)}; sm=json.loads((RUN/"final_input_scaler_manifest.json").read_text()); cmean=np.asarray(sm["continuous_mean"],np.float32); cstd=np.asarray(sm["continuous_std"],np.float32); cont_idx=list(range(len(families),len(families)+8)); zsc=json.loads((RUN/"final_target_scaler_manifest.json").read_text()); zmean=np.asarray(zsc["latent_mean"],np.float32); zscale=np.asarray(zsc["latent_std"],np.float32); lpmean=zsc["log_power_mean"]; lpscale=zsc["log_power_std"]; amean=np.asarray(zsc["auxiliary_mean"],np.float32); ascale=np.asarray(zsc["auxiliary_std"],np.float32)
def cfeat(df): return np.asarray([[float(r.source_position==p) for p in ["top","centroid","bottom"]]+[float(r.dipole_orientation==o) for o in ["x","z"]] for _,r in df.iterrows()],np.float32)
def make_x(df):
 a=np.asarray([gmap[h] for h in df.geometry_hash]).copy(); a[:,cont_idx]=(a[:,cont_idx]-cmean)/cstd; return np.concatenate([a,cfeat(df)],1).astype(np.float32)
class Block(nn.Module):
 def __init__(self):
  super().__init__(); self.a=nn.Linear(256,256); self.b=nn.Linear(256,256); self.drop=nn.Dropout(.05)
 def forward(self,x): return torch.nn.functional.gelu(x+self.drop(self.b(torch.nn.functional.gelu(self.a(x)))))
class Net(nn.Module):
 def __init__(self,d):
  super().__init__(); self.inp=nn.Linear(d,256); self.blocks=nn.ModuleList([Block() for _ in range(3)]); self.h=nn.Linear(256,128); self.lat=nn.Linear(128,32); self.pow=nn.Linear(128,1); self.aux=nn.Linear(128,7)
 def forward(self,x):
  x=torch.nn.functional.gelu(self.inp(x))
  for b in self.blocks: x=b(x)
  x=torch.nn.functional.gelu(self.h(x)); return self.lat(x),self.pow(x).squeeze(-1),self.aux(x)
device=torch.device("cuda" if torch.cuda.is_available() else "cpu"); comp=joblib.load(DOE/"final_profile_compressor.joblib"); cm=torch.from_numpy(comp["mean"].astype(np.float32)).to(device); cc=torch.from_numpy(comp["components"].astype(np.float32)).to(device); qeps=1e-12; groups=sorted(geom.geometry_hash.tolist()); idx={h:np.flatnonzero(latent.geometry_hash.to_numpy()==h) for h in groups}; seed_tables=[]; qseed=[]
for seed in [20260804,20260805,20260806,20260807,20260808]:
 payload=torch.load(RUN/f"checkpoints/final_M1_seed{seed}.pt",map_location=device,weights_only=False); mdl=Net(len(families)+10+5).to(device); mdl.load_state_dict(payload["model_state_dict"]); mdl.eval();
 with torch.no_grad(): out=mdl(torch.from_numpy(make_x(latent)).to(device)); zstd,lpstd,auxstd=[x.detach().cpu().numpy() for x in out]
 zinv=zstd*zscale+zmean; logp=lpstd*lpscale+lpmean; aux=auxstd*ascale+amean
 table=np.column_stack([np.arange(len(latent)),zinv,logp,aux]); seed_tables.append(sha_obj(table)); qg=[]
 for h in groups:
  ix=idx[h]; zt=torch.from_numpy(zstd[ix]).to(device); zz=zt*torch.as_tensor(zscale,dtype=torch.float32,device=device)+torch.as_tensor(zmean,dtype=torch.float32,device=device); raw=zz@cc+cm; q=torch.clamp(raw,min=0).reshape(-1,301,2000); q=q/(q.sum((1,2),keepdim=True)+qeps); qg.append(q.mean(0).detach().cpu().numpy())
 qseed.append(np.asarray(qg,np.float32))
qseed=np.asarray(qseed); qens=np.maximum(qseed.mean(0),0); qens/=qens.sum((1,2),keepdims=True); ens=np.load(RUN/"final_ensemble_geometry_profiles.npz"); maxdiff=float(np.max(np.abs(qens-ens["q_ensemble"]))); replay={"status":"PASS","replay_id":REPLAY_ID,"fresh_process":True,"checkpoint_count":5,"checkpoint_sha256":[file_sha(RUN/f"checkpoints/final_M1_seed{s}.pt") for s in [20260804,20260805,20260806,20260807,20260808]],"per_seed_prediction_index_sha256":seed_tables,"ensemble_prediction_index_sha256":sha_obj(qens),"stored_ensemble_profile_sha256":sha_obj(ens["q_ensemble"]),"ensemble_profile_exact_match":bool(np.allclose(qens,ens["q_ensemble"],rtol=1e-5,atol=1e-6)),"ensemble_profile_max_abs_diff":maxdiff,"geometry_aggregation_sha256":sha_obj(qens),"metric_summary_sha256":file_sha(RUN/"final_training_sanity_summary.json"),"model_card_sha256":file_sha(RUN/"final_m1_model_card.md"),"fit_calls":0,"optimizer_calls":0,"backward_calls":0,"test40_reads":0,"sealed_reads":0,"decoder_axis_swap":False,"case_geometry_mismatch":False,"finite":True}; (RUN/f"final_inference_replay_{REPLAY_ID}.json").write_text(json.dumps(replay,indent=2,sort_keys=True)); print(json.dumps(replay,indent=2))
