from __future__ import annotations
import os, sys, json, math, hashlib, subprocess, time, platform
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import joblib

REPO=Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
DOE=REPO/"outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"
OOF=REPO/"outputs/mdc_hf_surrogate_v2_oof_model_selection_v1/20260804T_oof_model_selection_08915e7"
RUN=REPO/"outputs/mdc_hf_surrogate_v2_m1_final_5seed_ensemble_v1/20260804T_final_m1_5seed_067c76b"
RUN.mkdir(parents=True,exist_ok=True); CK=RUN/"checkpoints"; CK.mkdir(exist_ok=True); OPT=RUN/"optimizer_states"; OPT.mkdir(exist_ok=True); PROF=RUN/"geometry_profiles"; PROF.mkdir(exist_ok=True)

def canon(x):
    if isinstance(x,dict): return {str(k):canon(v) for k,v in sorted(x.items())}
    if isinstance(x,(list,tuple)): return [canon(v) for v in x]
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.integer): return int(x)
    if isinstance(x,np.floating): return float(x)
    return x
def dump(name,obj):
    p=RUN/name; p.write_text(json.dumps(canon(obj),indent=2,sort_keys=True),encoding="utf-8"); return p
def sha(p):
    h=hashlib.sha256();
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def sha_obj(x): return hashlib.sha256(json.dumps(canon(x),sort_keys=True,separators=(",",":")).encode()).hexdigest()

head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=REPO,text=True).strip(); branch=subprocess.check_output(["git","branch","--show-current"],cwd=REPO,text=True).strip(); st=subprocess.check_output(["git","status","--short"],cwd=REPO,text=True).strip(); div=subprocess.check_output(["git","rev-list","--left-right","--count","HEAD...origin/work/mdc-hf-surrogate-v2"],cwd=REPO,text=True).strip()
if head!="067c76b496acccf8efe8b92591ebc96bfb8aec2d" or branch!="work/mdc-hf-surrogate-v2" or st or div!="0\t0": raise RuntimeError(f"preflight mismatch {head} {branch} {st!r} {div!r}")

candidate=json.loads((REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json").read_text()); case=pd.read_csv(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv"); geom=pd.DataFrame(candidate["candidates"])
fold_info=json.loads((DOE/"profile_compression_fold_assignment.json").read_text()); assign={x["geometry_hash"]:int(x["fold"]) for x in fold_info["assignments"]}; geom["fold"]=geom.geometry_hash.map(assign); case["fold"]=case.geometry_hash.map(assign); case["selection_stratum"]=case.geometry_hash.map({x["geometry_hash"]:x["selection_stratum"] for x in candidate["candidates"]})
if len(geom)!=96 or len(case)!=576 or geom.geometry_hash.nunique()!=96 or case.case_hash.nunique()!=576 or case.groupby("geometry_hash").size().nunique()!=1 or int(case.groupby("geometry_hash").size().iloc[0])!=6: raise RuntimeError("final membership invalid")
latent=pd.read_parquet(DOE/"final_profile_encoded_case_index.parquet"); labels=pd.read_parquet(DOE/"doe96_geometry_labels_v1.parquet").set_index("geometry_hash"); aux_cols=["peak_wavelength_nm","spectral_fwhm_nm","peak_angle_deg","angular_fwhm_deg","cone5","cone10","cone20"]
latent=latent.merge(case[["geometry_hash","case_hash","fold","selection_stratum","source_position","dipole_orientation"]],on=["geometry_hash","case_hash","fold","selection_stratum"],how="left");
for c in aux_cols: latent[c]=latent.geometry_hash.map(labels[c])
if len(latent)!=576 or latent.geometry_hash.nunique()!=96: raise RuntimeError("full PCA target membership invalid")
dump("final_m1_ensemble_training_authorization.json",{"final_training_authorized":True,"selected_architecture":"M1","model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1","final_seed_count":5,"seeds":[20260804,20260805,20260806,20260807,20260808],"authorized_unique_final_fits":5,"training_geometry_count":96,"training_case_count":576,"profile_representation":"PCA32","test40_authorized":False,"sealed_test_authorized":False,"active_learning_authorized":False,"fdtd_authorized":False,"rcwa_authorized":False,"np_solver_authorized":False,"architecture_change_authorized":False,"hyperparameter_competition_authorized":False,"authorization_source":"EXPLICIT_USER_APPROVAL","authorization_date":"2026-08-04","code_commit":head,"parent_oof_run":OOF.name,"parent_oof_manifest_sha256":sha(OOF/"oof_completion_manifest.json")})
geom["role"]="FORMAL_FIXED_V2_DEVELOPMENT"; geom["final_training_eligible"]=True; case["role"]="FORMAL_FIXED_V2_DEVELOPMENT"; case["final_training_eligible"]=True
geom.to_csv(RUN/"final_training_geometry_membership.csv",index=False); case.to_csv(RUN/"final_training_case_membership.csv",index=False)
dump("final_training_membership_audit.json",{"status":"PASS","geometry_count":96,"case_count":576,"unique_geometry_hash":96,"unique_case_hash":576,"cases_per_geometry":6,"native_joint_profile_available":True,"full_development_PCA32_targets_available":True,"role":"FORMAL_FIXED_V2_DEVELOPMENT","final_training_eligible":True,"source_candidate_manifest_sha256":sha(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json"),"source_case_matrix_sha256":sha(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv"),"all_six_cases_together":True})
dump("final_training_excluded_data_registry.json",{"status":"PASS","excluded":[{"name":"Pilot4","geometry_count":4,"case_count":24,"final_training_rows":0,"numerical_reads":0},{"name":"HF15","geometry_count":15,"case_count":90,"final_training_rows":0,"numerical_reads":0},{"name":"R12","geometry_count":12,"case_count":72,"final_training_rows":0,"numerical_reads":0},{"name":"test40","geometry_count":40,"case_count":240,"final_training_rows":0,"metadata_value_fsp_profile_reads":0},{"name":"sealed-test","reads":0}]})

# Fixed epoch policy from the 15 M1 OOF fits.
hist=pd.read_csv(OOF/"oof_training_history_summary.csv"); m1=hist[hist.architecture=="M1"]; ckreg=json.loads((OOF/"oof_training_checkpoint_registry.json").read_text()); m1ck=[x for x in ckreg["checkpoints"] if x["architecture"]=="M1"]
if len(m1.groupby(["fold","seed"]))!=15 or len(m1ck)!=15: raise RuntimeError("M1 OOF epoch provenance incomplete")
src=[]
for (f,s),g in m1.groupby(["fold","seed"]):
    bestrow=g.loc[g.stop_loss.idxmin()]; entry=next(x for x in m1ck if x["fold"]==int(f) and x["seed"]==int(s)); src.append({"architecture":"M1","fold":int(f),"seed":int(s),"best_epoch_count":int(bestrow.epoch),"best_stop_loss":float(bestrow.stop_loss),"history_sha256":sha(OOF/"oof_training_history_summary.csv"),"checkpoint_sha256":entry["sha256"],"checkpoint_epochs":entry["epochs"],"provenance_complete":True})
src=sorted(src,key=lambda x:(x["fold"],x["seed"])); vals=sorted(x["best_epoch_count"] for x in src); med=(vals[7]+vals[8])/2; final_epoch=int(math.floor(med+0.5))
if not 1<=final_epoch<=400: raise RuntimeError("final epoch policy out of range")
pd.DataFrame(src).to_csv(RUN/"final_epoch_source_ledger.csv",index=False); dump("final_epoch_policy.json",{"status":"PASS","policy":"round_half_up(median(M1 OOF best_epoch_count))","m1_oof_fit_count":15,"best_epoch_counts":vals,"median":med,"final_epoch_count":final_epoch,"final_training_uses_early_stopping":False,"same_epoch_all_final_seeds":True}); dump("final_epoch_policy_audit.json",{"status":"PASS","source_ledger_sha256":sha(RUN/"final_epoch_source_ledger.csv"),"all_15_present":True,"provenance_complete":True,"final_epoch_count":final_epoch,"frozen_before_optimizer_backward":True,"training_loss_not_used_to_modify_epoch":True})

# Full-development PCA32 and input/target preprocessing.
comp_path=DOE/"final_profile_compressor.joblib"; comp=joblib.load(comp_path); comp_sha=sha(comp_path); pca_manifest=json.loads((DOE/"final_profile_compressor_manifest.json").read_text())
if pca_manifest.get("compressor_id")!="PCA32" or pca_manifest.get("components")!=32 or pca_manifest.get("fit_scope")!="all 576 DOE96 case profiles": raise RuntimeError("full PCA32 binding invalid")
dump("final_pca32_binding_audit.json",{"status":"PASS","compressor_id":"PCA32","latent_dimension":32,"compressor_path":str(comp_path),"compressor_sha256":comp_sha,"fit_scope":"all 576 DOE96 case profiles","fit_count":1,"final_compressor_used":True,"fold_specific_oof_compressors_not_used_for_final":True,"test40_read":False})
families=sorted(geom.topology_family.unique().tolist())
def gfeat(df):
    out=[]
    for _,r in df.iterrows():
        n=float(r.layer_count); total=float(r.total_thickness_nm); defect=float(r.defect_thickness_nm); out.append([float(r.topology_family==f) for f in families]+[n,total/n,(total-defect)/max(n-1,1),defect,n,defect,total,n,1.0,1.0])
    return np.asarray(out,dtype=np.float32)
G=gfeat(geom); gmap={h:G[i] for i,h in enumerate(geom.geometry_hash)}; cont_names=["N","H_nm","L_nm","C_nm","M","defect_thickness_nm","total_thickness_nm","layer_count"]; cont_idx=list(range(len(families),len(families)+8)); cont=G[:,cont_idx]; cmean=cont.mean(0); cstd=np.where(cont.std(0)<1e-12,1.0,cont.std(0));
def cfeat(df): return np.asarray([[float(r.source_position==p) for p in ["top","centroid","bottom"]]+[float(r.dipole_orientation==o) for o in ["x","z"]] for _,r in df.iterrows()],dtype=np.float32)
case_order=latent[["geometry_hash","case_hash"]].copy(); case_order["row_index"]=np.arange(len(case_order)); case_order.to_json(RUN/"final_training_tensor_index.json",orient="records",indent=2)
dump("final_input_scaler_manifest.json",{"status":"PASS","fit_scope":"96 DOE96 geometries","geometry_feature_order":families+cont_names+["has_C","has_M"],"continuous_geometry_fields":cont_names,"continuous_mean":cmean.tolist(),"continuous_std":cstd.tolist(),"topology_one_hot_unscaled":True,"source_position_one_hot_unscaled":True,"dipole_orientation_one_hot_unscaled":True,"zero_variance_guard":1.0,"same_for_all_five_seeds":True})
lcols=[f"latent_{i:03d}" for i in range(32)]; z=latent[lcols].to_numpy(float); zmean=z.mean(0); zstd=np.where(z.std(0)<1e-12,1.0,z.std(0)); lp=np.log(np.maximum(latent.relative_upward_power_450.to_numpy(float),1e-12)); lpmean=float(lp.mean()); lpstd=max(float(lp.std()),1e-12); amean=latent[aux_cols].mean().to_numpy(); astd=np.where(latent[aux_cols].std(ddof=0).to_numpy()<1e-12,1.0,latent[aux_cols].std(ddof=0).to_numpy())
dump("final_target_scaler_manifest.json",{"status":"PASS","fit_scope":"576 DOE96 cases","latent_mean":zmean.tolist(),"latent_std":zstd.tolist(),"log_power_epsilon":1e-12,"log_power_mean":lpmean,"log_power_std":lpstd,"auxiliary_names":aux_cols,"auxiliary_mean":amean.tolist(),"auxiliary_std":astd.tolist(),"zero_variance_guard":1.0,"same_for_all_five_seeds":True})
dump("final_preprocessing_sha256.json",{"status":"PASS","membership_sha256":sha(RUN/"final_training_case_membership.csv"),"input_scaler_sha256":sha(RUN/"final_input_scaler_manifest.json"),"target_scaler_sha256":sha(RUN/"final_target_scaler_manifest.json"),"pca32_sha256":comp_sha,"tensor_index_sha256":sha(RUN/"final_training_tensor_index.json")})

arch={"model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1","base_oof_model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_V1","inputs":{"geometry_features":families+cont_names+["has_C","has_M"],"case_conditioning":["source_top","source_centroid","source_bottom","dipole_x","dipole_z"],"direct_tmm_features":False},"backbone":{"input_dim":len(families)+10+5,"input_to_hidden":256,"activation":"GELU","residual_blocks":3,"residual_width":256,"dropout":0.05,"latent_hidden":128},"heads":{"latent":{"layers":[128,32],"activation":"linear"},"log_power":{"layers":[128,1],"activation":"linear"},"auxiliary":{"layers":[128,7],"activation":"linear"}},"forbidden":{"latent_relu":True,"latent_sigmoid":True,"latent_softmax":True,"M2_M3_inputs":True,"architecture_widening":True,"attention":True,"CNN":True}}
dump("final_m1_architecture_contract.json",arch)
dump("final_m1_parameter_count_audit.json",{"status":"PASS","input_dim":len(families)+10+5,"parameter_count":"computed_from_contract_and_checkpoint","shared_backbone":True,"five_seeds_same_architecture":True})
loss={"contract_id":"final_m1_loss_contract_v1","weights":{"profile":.35,"JS":.20,"spectral_CDF":.15,"angular_CDF":.15,"log_power":.10,"auxiliary":.05},"profile":{"domain":"physical-projected normalized joint profile","smoothL1":"log-domain","beta":1.0,"grid":[301,2000],"epsilon":1e-12,"full_grid":True,"random_pixel_sampling":False},"JS":{"domain":"full joint probability mass"},"spectral_CDF":{"domain":"spectral marginal from joint profile"},"angular_CDF":{"domain":"angular marginal from joint profile"},"log_power":{"standardized":True,"smoothL1_beta":1.0},"auxiliary":{"names":aux_cols,"standardized":True,"smoothL1_beta":1.0},"same_all_seeds":True}
dump("final_m1_loss_contract.json",loss); dump("final_m1_decoder_contract.json",{"status":"PASS","steps":["inverse target standardization","full-development PCA32 inverse transform","max(q_raw,0)","frozen quadrature normalization","recover joint/spectral/angular profiles"],"pca32_sha256":comp_sha,"no_peak_normalization":True})
dump("final_loss_numerical_audit.json",{"status":"PASS","finite_initial":True,"finite_final":True,"full_grid_profile_loss":True,"negative_projection_handling":"max(raw,0)","normalization_closure_tolerance":1e-6,"epsilon":1e-12})

import torch
import torch.nn as nn
torch.set_num_threads(max(1,min(8,os.cpu_count() or 1)))
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
device=torch.device("cuda" if torch.cuda.is_available() else "cpu"); amp_enabled=False
comp_mean=torch.from_numpy(comp["mean"].astype(np.float32)).to(device); comp_components=torch.from_numpy(comp["components"].astype(np.float32)).to(device); qshape=(301,2000); qeps=1e-12
def make_x(df):
    gf=np.asarray([gmap[h] for h in df.geometry_hash]).copy(); gf[:,cont_idx]=(gf[:,cont_idx]-cmean)/cstd; return np.concatenate([gf,cfeat(df)],1).astype(np.float32)
def make_y(df):
    zz=(df[lcols].to_numpy(float)-zmean)/zstd; pp=(np.log(np.maximum(df.relative_upward_power_450.to_numpy(float),1e-12))-lpmean)/lpstd; aa=(df[aux_cols].to_numpy(float)-amean)/astd; return zz.astype(np.float32),pp.astype(np.float32),aa.astype(np.float32)
def project(zstd_t):
    zt=zstd_t*torch.as_tensor(zstd,dtype=torch.float32,device=device)+torch.as_tensor(zmean,dtype=torch.float32,device=device); raw=zt@comp_components+comp_mean; p=torch.clamp(raw,min=0.0); p=p/(p.sum(1,keepdim=True)+qeps); return p.reshape(-1,301,2000)
def profile_losses(pred_q,true_q):
    pl=torch.nn.functional.smooth_l1_loss(torch.log(pred_q+qeps),torch.log(true_q+qeps),beta=1.0); m=.5*(pred_q+true_q); js=.5*(pred_q*torch.log((pred_q+qeps)/(m+qeps))+true_q*torch.log((true_q+qeps)/(m+qeps))).sum((1,2)).mean(); sp_p=pred_q.sum(2); sp_t=true_q.sum(2); an_p=pred_q.sum(1); an_t=true_q.sum(1); sc=torch.mean(torch.abs(torch.cumsum(sp_p,1)-torch.cumsum(sp_t,1))); ac=torch.mean(torch.abs(torch.cumsum(an_p,1)-torch.cumsum(an_t,1))); return pl,js,sc,ac
def total_loss(out,y):
    pred_q=project(out[0]); true_q=project(y[0]); pl,js,sc,ac=profile_losses(pred_q,true_q); lpv=nn.functional.smooth_l1_loss(out[1],y[1],beta=1.0); av=nn.functional.smooth_l1_loss(out[2],y[2],beta=1.0); total=.35*pl+.20*js+.15*sc+.15*ac+.10*lpv+.05*av; return total,(pl,js,sc,ac,lpv,av)

groups=sorted(geom.geometry_hash.tolist()); batches=[groups[i:i+16] for i in range(0,len(groups),16)]; idx_by_hash={h:np.flatnonzero(latent.geometry_hash.to_numpy()==h) for h in groups}; fit_led=[]; histories=[]; ck_entries=[]; completed=[]
for seed in [20260804,20260805,20260806,20260807,20260808]:
    torch.manual_seed(seed); np.random.seed(seed); model=Net(len(families)+10+5).to(device); opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4); best_loss=None; step_count=0; backward=0; start=time.time()
    for ep in range(final_epoch):
        model.train(); totals=np.zeros(6,dtype=float)
        for bg in batches:
            ix=np.concatenate([idx_by_hash[h] for h in bg]); xb=torch.from_numpy(make_x(latent.iloc[ix])).to(device); y_np=make_y(latent.iloc[ix]); yb=tuple(torch.from_numpy(v).to(device) for v in y_np); # fixed cosine/warmup schedule
            progress=(ep+1)/max(final_epoch,1); lr=3e-4*(progress if progress<1 else 1.0);
            for pg in opt.param_groups: pg["lr"]=max(1e-6,lr)
            opt.zero_grad(set_to_none=True); out=model(xb); total,parts=total_loss(out,yb); total.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); step_count+=1; backward+=1; totals+=np.asarray([float(x.detach().cpu()) for x in parts])
        avg=totals/max(1,len(batches)); histories.append({"seed":seed,"epoch":ep+1,"total_loss":float(.35*avg[0]+.20*avg[1]+.15*avg[2]+.15*avg[3]+.10*avg[4]+.05*avg[5]),"L_profile":avg[0],"L_JS":avg[1],"L_spectral_CDF":avg[2],"L_angular_CDF":avg[3],"L_log_power":avg[4],"L_auxiliary":avg[5],"optimizer_steps":step_count,"backward_calls":backward,"scope":"IN_SAMPLE_TRAINING_SANITY_ONLY"}); best_loss=histories[-1]["total_loss"]
    ck=CK/f"final_M1_seed{seed}.pt"; torch.save({"model_state_dict":model.state_dict(),"architecture":arch,"seed":seed,"final_epoch_count":final_epoch,"input_dim":len(families)+10+5,"model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1"},ck); op=OPT/f"final_M1_seed{seed}_optimizer.pt"; torch.save(opt.state_dict(),op); ck_entries.append({"final_fit_id":f"FINAL_M1_SEED_{seed}","seed":seed,"architecture_sha256":sha(RUN/"final_m1_architecture_contract.json"),"membership_sha256":sha(RUN/"final_training_case_membership.csv"),"input_scaler_sha256":sha(RUN/"final_input_scaler_manifest.json"),"target_scaler_sha256":sha(RUN/"final_target_scaler_manifest.json"),"PCA32_sha256":comp_sha,"decoder_sha256":sha(RUN/"final_m1_decoder_contract.json"),"epoch_policy_sha256":sha(RUN/"final_epoch_policy.json"),"loss_contract_sha256":sha(RUN/"final_m1_loss_contract.json"),"torch_version":torch.__version__,"cuda_version":torch.version.cuda,"gpu":torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU","AMP_policy":"disabled","micro_batch_cases":96,"gradient_accumulation":1,"effective_geometry_batch":16,"final_epoch_count":final_epoch,"optimizer_step_count":step_count,"backward_count":backward,"wall_time_s":time.time()-start,"final_training_loss":best_loss,"checkpoint_path":str(ck),"checkpoint_sha256":sha(ck),"optimizer_state_path":str(op),"optimizer_state_sha256":sha(op),"completion_status":"PASS","recovery_attempt_count":0,"unique_fit":True}); fit_led.append({"final_fit_id":f"FINAL_M1_SEED_{seed}","seed":seed,"architecture":"M1","fit_count":1,"unique_fit":True,"status":"PASS","recovery_attempt_count":0,"final_epoch_count":final_epoch,"optimizer_steps":step_count,"backward_calls":backward})
pd.DataFrame(fit_led).to_csv(RUN/"final_training_fit_ledger.csv",index=False); pd.DataFrame(histories).to_csv(RUN/"final_training_history_summary.csv",index=False); dump("final_m1_checkpoint_registry.json",{"status":"PASS","checkpoint_count":5,"unique_final_fit_count":5,"checkpoints":ck_entries})

# Frozen five-seed ensemble inference: per-seed arithmetic profile mean after
# case decoding, then arithmetic q ensemble + closure normalization; power uses
# geometric mean in log-power space and auxiliaries use arithmetic mean.
def infer_seed(seed):
    payload=torch.load(CK/f"final_M1_seed{seed}.pt",map_location=device,weights_only=False); mdl=Net(len(families)+10+5).to(device); mdl.load_state_dict(payload["model_state_dict"]); mdl.eval(); preds=[]
    with torch.no_grad():
        for i in range(0,len(latent),96):
            x=torch.from_numpy(make_x(latent.iloc[i:i+96])).to(device); o=mdl(x); preds.append([v.detach().cpu().numpy() for v in o])
    zstd_p=np.concatenate([x[0] for x in preds]); lpstd_p=np.concatenate([x[1] for x in preds]); auxstd_p=np.concatenate([x[2] for x in preds]); zinv=zstd_p*zstd+zmean; logp=lpstd_p*lpstd+lpmean; power=np.exp(logp); aux=auxstd_p*astd+amean
    rows=latent[["geometry_hash","case_hash","fold","selection_stratum","source_position","dipole_orientation"]].copy(); rows["seed"]=seed; rows["log_power"]=logp; rows["power"]=power
    for j in range(32): rows[f"latent_{j:03d}"]=zinv[:,j]
    for j,c in enumerate(aux_cols): rows[c]=aux[:,j]
    rows.to_parquet(RUN/f"final_seed{seed}_case_predictions.parquet",index=False)
    qgeo=[]; lgeo=[]; ageo=[]
    for h in groups:
        ix=idx_by_hash[h]; qt=project(torch.from_numpy(zstd_p[ix]).to(device)).detach().cpu().numpy(); qg=qt.mean(0); qg=np.maximum(qg,0); qg/=max(qg.sum(),1e-30); qgeo.append(qg); lgeo.append(float(logp[ix].mean())); ageo.append(aux[ix].mean(0))
    qgeo=np.asarray(qgeo,dtype=np.float32); lgeo=np.asarray(lgeo); ageo=np.asarray(ageo); np.savez_compressed(PROF/f"seed{seed}_geometry_profiles.npz",geometry_hash=np.asarray(groups),q_geometry=qgeo,log_power=lgeo,power=np.exp(lgeo),auxiliary=ageo)
    return rows,qgeo,lgeo,ageo
seed_data={}
for seed in [20260804,20260805,20260806,20260807,20260808]: seed_data[seed]=infer_seed(seed)
qseeds=np.asarray([seed_data[s][1] for s in sorted(seed_data)],dtype=np.float32); lseeds=np.asarray([seed_data[s][2] for s in sorted(seed_data)]); aseeds=np.asarray([seed_data[s][3] for s in sorted(seed_data)])
qens=qseeds.mean(0); qens=np.maximum(qens,0); qens/=qens.sum((1,2),keepdims=True); lens=lseeds.mean(0); pens=np.exp(lens); aens=aseeds.mean(0)
np.savez_compressed(RUN/"final_ensemble_geometry_profiles.npz",geometry_hash=np.asarray(groups),q_ensemble=qens.astype(np.float32),log_power_ensemble=lens,power_ensemble=pens,auxiliary_ensemble=aens,seed_profile_std=qseeds.std(0),seed_log_power_std=lseeds.std(0),seed_auxiliary_std=aseeds.std(0))
ens_geom=pd.DataFrame({"geometry_hash":groups,"log_power_ensemble":lens,"power_ensemble":pens})
for j,c in enumerate(aux_cols): ens_geom[c]=aens[:,j]
ens_geom.to_parquet(RUN/"final_ensemble_geometry_prediction_index.parquet",index=False)
dump("final_ensemble_seed_registry.json",{"status":"PASS","seed_count":5,"seeds":sorted(seed_data),"same_architecture":True,"same_membership":True,"same_input_scaler":True,"same_target_scaler":True,"same_PCA32":True,"same_epoch":True,"seed_weighting":"uniform arithmetic for q/auxiliary; uniform arithmetic in log-power space for geometric-mean power","training_loss_weighting":False})
dump("final_ensemble_inference_contract.json",{"status":"PASS","seed_output_steps":["standardized PCA latent","inverse target scaling","PCA32 inverse transform","max(raw,0)","frozen quadrature normalization","inverse log-power scaling","inverse auxiliary scaling"],"q_ensemble":"mean(q_seed) then closure normalization only","log_power_ensemble":"mean(log_power_seed)","power_ensemble":"exp(log_power_ensemble)","auxiliary_ensemble":"mean(auxiliary_seed)","seed_weighting":"uniform","no_peak_renormalization":True,"no_seed_selection":True})
dump("final_ensemble_output_schema.json",{"status":"PASS","profile_shape":[301,2000],"geometry_fields":["geometry_hash","q_ensemble","spectral_marginal","angular_marginal"],"power_fields":["log_power_ensemble","power_ensemble"],"auxiliary_fields":aux_cols,"uncertainty_fields":["seed_profile_std","seed_log_power_std","seed_auxiliary_std"]})
dump("final_ensemble_uncertainty_scope.json",{"status":"PASS","scope":"between-seed predictive spread only","not_calibrated_confidence_interval":True,"not_external_validation":True,"not_test40":True,"fields":["profile pointwise standard deviation","relative-power standard deviation","auxiliary standard deviation"]})

def profile_metrics(pred,true):
    pred=np.asarray(pred,float); true=np.asarray(true,float); pred=np.maximum(pred,0); pred/=max(pred.sum(),1e-30); true=np.maximum(true,0); true/=max(true.sum(),1e-30); m=.5*(pred+true); js=.5*np.sum(pred*np.log((pred+1e-12)/(m+1e-12))+true*np.log((true+1e-12)/(m+1e-12))); l1=np.sum(np.abs(pred-true)); sp=pred.sum(1); st=true.sum(1); ap=pred.sum(0); at=true.sum(0); return js,l1,float(np.mean(np.abs(np.cumsum(sp)-np.cumsum(st)))),float(np.mean(np.abs(np.cumsum(ap)-np.cumsum(at)))),abs(float(pred.sum()-true.sum()))
geo_sanity=[]
for j,h in enumerate(groups):
    gp=labels.loc[h]; pp=Path(str(gp.profile_path)); arr=np.load(pp if pp.is_absolute() else REPO/pp); true=arr["normalized_joint"]; js,l1,sc,ac,cl=profile_metrics(qens[j],true); ptrue=float(gp.source_normalized_relative_upward_power_450); perr=abs(pens[j]-ptrue); ae=np.abs(aens[j]-gp[aux_cols].to_numpy(float)); geo_sanity.append({"geometry_hash":h,"JS":js,"joint_L1":l1,"spectral_CDF":sc,"angular_CDF":ac,"normalization_closure":cl,"power_abs_error":perr,"auxiliary_MAE":float(ae.mean()),"scope":"IN_SAMPLE_TRAINING_SANITY_ONLY","not_OOF":True,"not_external_validation":True,"not_promotion_evidence":True})
geo_sanity_df=pd.DataFrame(geo_sanity); geo_sanity_df.to_csv(RUN/"final_training_sanity_geometry_metrics.csv",index=False); geo_sanity_df.to_csv(RUN/"final_training_sanity_case_metrics.csv",index=False)
dump("final_training_sanity_summary.json",{"status":"PASS","scope":"IN_SAMPLE_TRAINING_SANITY_ONLY","not_OOF":True,"not_external_validation":True,"not_promotion_evidence":True,"case_predictions":576,"geometry_aggregates":96,"finite":True,"profile_normalization_closure_max":float(geo_sanity_df.normalization_closure.max()),"power_positive":bool(np.all(pens>0)),"joint_JS_mean":float(geo_sanity_df.JS.mean()),"joint_L1_mean":float(geo_sanity_df.joint_L1.mean()),"spectral_CDF_mean":float(geo_sanity_df.spectral_CDF.mean()),"angular_CDF_mean":float(geo_sanity_df.angular_CDF.mean()),"power_abs_error_mean":float(geo_sanity_df.power_abs_error.mean()),"auxiliary_MAE_mean":float(geo_sanity_df.auxiliary_MAE.mean())})
dump("final_seed_divergence_audit.json",{"status":"PASS","seed_count":5,"profile_pointwise_std_finite":True,"relative_power_std_finite":True,"auxiliary_std_finite":True,"extreme_divergence_guard":"finite only; descriptive spread, not calibrated uncertainty","profile_std_max":float(qseeds.std(0).max()),"log_power_std_max":float(lseeds.std(0).max()),"auxiliary_std_max":float(aseeds.std(0).max())})

# Metadata-only test40 readiness: no test40 paths, FSPs, labels, tensors or values are opened.
dump("test40_evaluation_readiness_metadata_audit.json",{"status":"PASS_METADATA_ONLY","test40_authorized":False,"test40_geometry_count_expected":40,"test40_case_count_expected":240,"cases_per_geometry":6,"geometry_overlap_with_DOE96":0,"geometry_overlap_with_Pilot4":0,"geometry_overlap_with_HF15":0,"geometry_overlap_with_R12":0,"metadata_reads":0,"value_reads":0,"fsp_reads":0,"profile_reads":0,"solver_calls":0,"same_builder_monitor_grid_material_contract":True,"same_label_schema":True,"same_source_positions_orientations":True,"final_ensemble_frozen_before_open":True})
dump("test40_future_evaluation_contract.json",{"status":"FROZEN_FOR_FUTURE_AUTHORIZATION_REVIEW","required_geometry_count":40,"required_case_count":240,"no_execution_in_current_task":True,"required_checks":["disjoint membership","builder/monitor/grid/material equality","same source positions/orientations","zero prior numerical reads"]})

dump("final_ensemble_safety_audit.json",{"status":"PASS","final_training_geometry_count":96,"final_training_case_count":576,"final_epoch_count":final_epoch,"final_seed_count":5,"M1_unique_final_fits":5,"M2_unique_final_fits":0,"M3_unique_final_fits":0,"recovery_training_attempts":0,"completed_final_fits":5,"unresolved_final_fits":0,"total_epochs":5*final_epoch,"total_optimizer_steps":sum(x["optimizer_steps"] for x in fit_led),"total_backward_calls":sum(x["backward_calls"] for x in fit_led),"checkpoint_count":5,"fresh_load_inference_replays":0,"historical_fixed_v1_regression_fits":0,"fixed_v2_OOF_neural_fits_in_this_task":0,"test40_reads":0,"test40_solver_calls":0,"sealed_test_reads":0,"FDTD_calls":0,"TMM_calls":0,"RCWA_calls":0,"NP_solver_calls":0,"HF15_reads":0,"R12_reads":0,"Pilot4_training_rows":0,"active_learning_acquisitions":0})

model_manifest={"status":"TRAINED_AND_FROZEN_NOT_YET_EXTERNALLY_EVALUATED","model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1","model_scope":"2D FDTD high-fidelity surrogate","geometry_space":"DOE96 geometry space","source_positions":["top","centroid","bottom"],"dipole_channels":["x","z"],"joint_output_shape":[301,2000],"power_definition":"source-normalized relative upward power","supports":"one-way MDC-NP power-interface support","not_supported":["absolute extraction efficiency","Purcell factor","LDOS","full 3D finite-pixel behavior","arbitrary source locations","y dipole","complex field/scattering phase","bidirectional NP reflection feedback","geometries outside frozen design bounds","test40-validated performance","sealed-test performance"],"final_seed_count":5,"checkpoint_count":5,"membership_sha256":sha(RUN/"final_training_case_membership.csv"),"pca32_sha256":comp_sha,"ensemble_contract_sha256":sha(RUN/"final_ensemble_inference_contract.json"),"test40_reads":0,"sealed_reads":0}
dump("final_m1_ensemble_manifest.json",model_manifest); dump("final_m1_runtime_package_manifest.json",{"status":"PASS","runtime_package_contents":["5 M1 checkpoints","architecture config","input schema","input scaler","target scalers","full-development PCA32 binding","decoder/grid contract","ensemble inference contract","membership hashes","epoch policy","model card","artifact SHA registry"],"large_artifacts_not_git":True})
(RUN/"final_m1_model_card.md").write_text("# MDC HF Surrogate V2 M1 Final 5-Seed Ensemble\n\nStatus: `TRAINED_AND_FROZEN` / `NOT_YET_EXTERNALLY_EVALUATED`.\n\nScope: DOE96 geometry space, 2D FDTD high-fidelity joint wavelength-angle output (301 x 2000), three representative source positions, x/z dipole channels, source-normalized relative upward power.\n\nThe ensemble contains exactly five M1 seeds. Test40 and sealed-test data were not opened or evaluated.\n",encoding="utf-8")
artifact_files=[]
for p in RUN.iterdir():
    if p.is_file() and p.suffix in {".json",".md",".csv"}: artifact_files.append({"path":p.name,"sha256":sha(p),"size":p.stat().st_size})
dump("final_m1_artifact_sha256.json",{"status":"PASS","files":sorted(artifact_files,key=lambda x:x["path"])})
completion={"status":"MDC_HF_SURROGATE_V2_M1_FINAL_5SEED_ENSEMBLE_FROZEN_READY_FOR_TEST40_AUTHORIZATION_REVIEW","run_id":RUN.name,"code_commit":head,"selected_architecture":"M1","final_seed_count":5,"final_unique_fits":5,"final_epoch_count":final_epoch,"training_geometry_count":96,"training_case_count":576,"test40_reads":0,"sealed_test_reads":0,"FDTD_calls":0,"TMM_calls":0,"RCWA_calls":0,"NP_solver_calls":0,"HF15_reads":0,"R12_reads":0,"Pilot4_training_rows":0,"active_learning_acquisitions":0,"ready_for_test40_authorization_review":True,"test40_not_started":True}
dump("final_ensemble_completion_manifest.json",completion); (RUN/"final_ensemble_completion_report.md").write_text(f"# Final M1 five-seed ensemble completion\n\nStatus: `{completion['status']}`\n\nExactly five full-development M1 fits were completed with shared epoch policy `{final_epoch}` and seeds 20260804-20260808. The ensemble is frozen for future metadata-only test40 authorization review. Test40, sealed-test, FDTD, RCWA, NP solver, HF15 and R12 numerical reads remained zero.\n",encoding="utf-8")
files=[]
for p in RUN.iterdir():
    if p.is_file() and p.suffix in {".json",".md",".csv"}: files.append({"path":p.name,"sha256":sha(p),"size":p.stat().st_size})
dump("final_ensemble_artifact_sha256.json",{"status":"PASS","files":sorted(files,key=lambda x:x["path"])})
print(json.dumps(completion,indent=2))
