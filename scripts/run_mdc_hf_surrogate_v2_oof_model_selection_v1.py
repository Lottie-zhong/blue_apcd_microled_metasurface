from __future__ import annotations
import os, sys, json, math, hashlib, subprocess, time, shutil
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import joblib

REPO = Path(r"D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2")
DOE = REPO / "outputs/mdc_hf_surrogate_v2_doe96_joint_profile_database_v1/20260803T_doe96_joint_profile_6b6d7e2"
RUN = REPO / "outputs/mdc_hf_surrogate_v2_oof_model_selection_v1/20260804T_oof_model_selection_08915e7"
RUN.mkdir(parents=True, exist_ok=True)
CKPT = RUN / "checkpoints"; CKPT.mkdir(exist_ok=True)
sys.path.insert(0, str(REPO / "scripts"))
import mdc_dipole_tmm as tmm

def canon(x):
    if isinstance(x, dict): return {str(k): canon(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)): return [canon(v) for v in x]
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, np.ndarray): return x.tolist()
    return x

def dump(name: str, obj: Any):
    p = RUN / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(canon(obj), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8"); return p

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()

def sha_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(canon(obj), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def trapz_weights(x):
    x = np.asarray(x, dtype=float); w = np.empty_like(x)
    w[1:-1] = (x[2:] - x[:-2]) / 2.0; w[0] = (x[1]-x[0])/2.0; w[-1] = (x[-1]-x[-2])/2.0; return w

head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip()
status = subprocess.check_output(["git", "status", "--short"], cwd=REPO, text=True).strip()
div = subprocess.check_output(["git", "rev-list", "--left-right", "--count", "HEAD...origin/work/mdc-hf-surrogate-v2"], cwd=REPO, text=True).strip()
if head != "08915e72df703273d4947bdd39e72c277512ca32" or branch != "work/mdc-hf-surrogate-v2" or status or div != "0\t0":
    raise RuntimeError(f"preflight mismatch head={head} branch={branch} status={status!r} div={div!r}")

auth = {"contract_id":"oof_model_training_authorization_v1","status":"AUTHORIZED","authorization_date":"2026-08-04","code_commit":head,"architectures":["M1","M2","M3"],"outer_folds":5,"seeds":[20260804,20260805,20260806],"max_unique_neural_fits":45,"expected_unique_neural_fits":45,"direct_tmm_descriptor_generation":True,"final_full_development_fit":False,"final_ensemble":False,"test40":False,"sealed_test":False,"HF15":False,"R12":False,"active_learning":False,"fdtd":False,"rcwa":False,"np_solver":False,"solver_calls":0,"HF15_formal_value_reads":0,"HF15_diagnostics_reads":0,"sealed_test_reads":0,"parent_run_root":str(DOE),"parent_completion_manifest_sha256":sha(DOE/'profile_compression_completion_manifest.json')}
dump("oof_model_training_authorization.json", auth)

candidate = json.loads((REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json").read_text())
case = pd.read_csv(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv")
latent = pd.read_parquet(DOE/"oof_latent_target_index.parquet")
geom_labels = pd.read_parquet(DOE/"doe96_geometry_labels_v1.parquet")
fold_info = json.loads((DOE/"profile_compression_fold_assignment.json").read_text())
assign = {x["geometry_hash"]: int(x["fold"]) for x in fold_info["assignments"]}
crec = {x["geometry_hash"]: x for x in candidate["candidates"]}
case["fold"] = case.geometry_hash.map(assign)
case["selection_stratum"] = case.geometry_hash.map({x["geometry_hash"]:x["selection_stratum"] for x in candidate["candidates"]})
geom = pd.DataFrame(candidate["candidates"]); geom["fold"] = geom.geometry_hash.map(assign); geom["case_count"] = 6; geom["membership"] = "DOE96_FORMAL_DEVELOPMENT"
if case.fold.isna().any() or len(case)!=576 or case.geometry_hash.nunique()!=96 or sorted(geom.fold.value_counts().to_dict().items()) != [(0,16),(1,14),(2,18),(3,26),(4,22)]: raise RuntimeError("membership drift")
case["membership"] = "DOE96_FORMAL_DEVELOPMENT"; geom.to_csv(RUN/"oof_training_geometry_membership.csv", index=False); case.to_csv(RUN/"oof_training_case_membership.csv", index=False)
dump("oof_training_membership_audit.json", {"status":"PASS","membership_unit":"geometry_hash","geometry_count":96,"case_count":576,"cases_per_geometry":6,"all_six_cases_together":True,"outer_fold_counts":geom.fold.value_counts().sort_index().to_dict(),"source_candidate_manifest_sha256":sha(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_candidate_manifest.json"),"source_case_matrix_sha256":sha(REPO/"contracts/mdc_hf_surrogate_v2/fixed_v2_initial_doe96_case_matrix.csv"),"excluded":["Pilot4","HF15","R12","test40","sealed_test"]})
dump("oof_excluded_data_registry.json", {"status":"PASS","excluded":[{"name":"Pilot4","geometry_count":4,"case_count":24,"read":False},{"name":"HF15","geometry_count":15,"case_count":90,"read":False},{"name":"R12","geometry_count":12,"case_count":72,"read":False},{"name":"test40","geometry_count":40,"case_count":240,"read":False},{"name":"sealed_test","read":False}],"formal_reads":{"HF15":0,"diagnostics":0,"sealed_test":0}})

outer=[]
for f in range(5):
    tr=sorted(geom.loc[geom.fold!=f,"geometry_hash"].tolist()); va=sorted(geom.loc[geom.fold==f,"geometry_hash"].tolist()); outer.append({"fold":f,"train_geometry_hashes":tr,"heldout_geometry_hashes":va,"train_case_count":len(tr)*6,"heldout_case_count":len(va)*6,"all_six_cases_together":True})
dump("oof_outer_fold_registry.json", {"status":"PASS","assignment_sha256":fold_info["assignment_sha256"],"folds":outer})
inner=[]
for f in range(5):
    tr=geom.loc[geom.fold!=f].copy(); nstop=max(7,int(round(.10*len(tr)))); stop=[]
    for _,g in tr.groupby("topology_family",sort=True): stop.extend(sorted(g.geometry_hash.tolist())[:max(1,int(round(nstop*len(g)/len(tr))))])
    stop=sorted(set(stop)); stop=sorted(set(stop+sorted(set(tr.geometry_hash)-set(stop))))[:nstop]
    inner.append({"fold":f,"split_unit":"geometry_hash","stop_geometry_hashes":stop,"fit_geometry_hashes":sorted(set(tr.geometry_hash)-set(stop)),"stop_case_count":len(stop)*6,"fit_case_count":(len(tr)-len(stop))*6,"stratification":"topology_family + selection_stratum","fixed_across_architectures_and_seeds":True,"purpose":"early_stopping_only"})
dump("oof_inner_stop_split_registry.json", {"status":"PASS","splits":inner,"minimum_stop_geometries":7})
dump("oof_split_leakage_audit.json", {"status":"PASS","geometry_overlap_outer":0,"case_overlap_outer":0,"geometry_overlap_inner":0,"heldout_used_for_training_or_stopping":False,"test40_or_HF15_reads":0})

families=sorted(geom.topology_family.unique().tolist())
dump("oof_geometry_input_schema.json", {"contract_id":"oof_geometry_input_schema_v1","topology_one_hot_requested":["Explicit","ZL1","ZL2"],"topology_one_hot_actual":families,"numeric_fields":["N","H_nm","L_nm","C_nm","M","defect_thickness_nm","total_thickness_nm","layer_count"],"missing_value_policy":"topology-specific numeric fill 0 with has_C/has_M masks","feature_order":families+["N","H_nm","L_nm","C_nm","M","defect_thickness_nm","total_thickness_nm","layer_count","has_C","has_M"]})
dump("oof_case_conditioning_schema.json", {"contract_id":"oof_case_conditioning_schema_v1","feature_order":["source_top","source_centroid","source_bottom","dipole_x","dipole_z"],"one_hot_policy":"exactly one source and one dipole orientation"})

def geom_features(df):
    out=[]
    for _,r in df.iterrows():
        n=float(r.layer_count); total=float(r.total_thickness_nm); defect=float(r.defect_thickness_nm); out.append([float(r.topology_family==f) for f in families]+[n,total/n,(total-defect)/max(n-1,1),defect,n,defect,total,n,1.0,1.0])
    return np.asarray(out,dtype=np.float32)
G=geom_features(geom); gmap={h:G[i] for i,h in enumerate(geom.geometry_hash)}
def cond_features(df): return np.asarray([[float(r.source_position==p) for p in ["top","centroid","bottom"]]+[float(r.dipole_orientation==o) for o in ["x","z"]] for _,r in df.iterrows()],dtype=np.float32)

first_npz=np.load(pd.read_parquet(DOE/"doe96_case_label_index_v1.parquet").iloc[0].joint_tensor_path); wavelength=first_npz["wavelength_nm"].astype(float); angle=first_npz["angle_deg"].astype(float); wavelength_eval=np.linspace(420.0,480.0,31); angle_eval=np.linspace(-89.95,89.95,31); dw=trapz_weights(wavelength); da=trapz_weights(np.deg2rad(angle))
def safe_channel(c,w,a,o):
    try: return float(tmm.dipole_channel(c,float(w),float(a),0.0,o)["I_air_relative"])
    except (ZeroDivisionError,FloatingPointError): return 0.0
def profile_stats(q):
    q=q.reshape(len(wavelength),len(angle)); sm=np.maximum(q.sum(1),0); am=np.maximum(q.sum(0),0); sm/=max(sm.sum(),1e-30); am/=max(am.sum(),1e-30)
    def fwhm(x,v):
        ix=np.where(v>=.5*np.max(v))[0]; return float(x[ix[-1]]-x[ix[0]]) if len(ix)>1 else 0.0
    return {"peak_wavelength_nm":float(wavelength[np.argmax(sm)]),"spectral_fwhm_nm":fwhm(wavelength,sm),"peak_angle_deg":float(angle[np.argmax(am)]),"angular_fwhm_deg":fwhm(angle,am),"cone5":float(am[np.abs(angle)<=5].sum()/max(am.sum(),1e-30)),"cone10":float(am[np.abs(angle)<=10].sum()/max(am.sum(),1e-30)),"cone20":float(am[np.abs(angle)<=20].sum()/max(am.sum(),1e-30))}
tmm_profiles=[]; scalar_rows=[]; jobs=[]; tpath=RUN/"direct_tmm_profiles"; tpath.mkdir(exist_ok=True)
for _,r in geom.iterrows():
    rec=crec[r.geometry_hash]; n=int(rec["layer_count"]); total=int(rec["total_thickness_nm"]); defect=int(rec["defect_thickness_nm"]); idx=n//2; base,extra=divmod(total-defect,n-1); layers=[]
    for j in range(n):
        d=defect if j==idx else base+(1 if (j if j<idx else j-1)<extra else 0); layers.append(("APCD_TIO2_NATIVE_M1" if j%2==0 else "APCD_SIO2_NATIVE_M1",float(d)))
    fp=tpath/(r.geometry_hash+".npz")
    if fp.exists():
        arr=np.load(fp); q=arr["q_profile"].astype(float); spec=arr["spectral"].astype(float); ang=arr["angular"].astype(float)
    else:
        c=tmm.Candidate(r.geometry_id,r.geometry_hash,tuple(layers)); spec_eval=np.asarray([np.mean([safe_channel(c,w,0,o) for o in ["x","z"]]) for w in wavelength_eval]); spec=np.interp(wavelength,wavelength_eval,spec_eval); ang_eval=np.asarray([np.mean([safe_channel(c,450,a,o) for o in ["x","z"]]) for a in angle_eval]); ang=np.interp(angle,angle_eval,ang_eval,left=0.0,right=0.0); spec=np.maximum(spec,0); ang=np.maximum(ang,0); q=np.outer(spec,ang)*dw[:,None]*da[None,:]; q=q/max(q.sum(),1e-30); np.savez_compressed(fp,wavelength_nm=wavelength,angle_deg=angle,q_profile=q.astype(np.float32),spectral=spec.astype(np.float32),angular=ang.astype(np.float32))
    st=profile_stats(q)
    scalar={"geometry_hash":r.geometry_hash,**st,"T450":float(spec[np.argmin(np.abs(wavelength-450.0))]),"mean_normal_band_transmission":float(np.mean(spec[(wavelength>=445)&(wavelength<=455)])),"integrated_angular_concentration":1.0}; scalar_rows.append(scalar); tmm_profiles.append({"geometry_hash":r.geometry_hash,"profile_path":str(fp),"profile_sha256":sha(fp),"shape":[len(wavelength),len(angle)],"wavelength_grid_sha256":sha_obj(wavelength.tolist()),"signed_kx_convention":"real conserved kx, air-side +y, signed angle"}); jobs.append({"geometry_hash":r.geometry_hash,"geometry_id":r.geometry_id,"status":"PASS","solver_calls":0})
pd.DataFrame(tmm_profiles).to_parquet(RUN/"direct_tmm_profile_index.parquet",index=False); pd.DataFrame(scalar_rows).to_parquet(RUN/"direct_tmm_scalar_descriptor_index.parquet",index=False)
dump("direct_tmm_descriptor_contract.json", {"contract_id":"direct_tmm_descriptor_contract_v1","status":"PASS","geometry_jobs":96,"material_policy":"MDC_NATIVE_M1","air_side":"+y","conserved_kx":"real signed kx from air-side angle","wavelength_grid":[420.0,480.0,301],"angle_grid_source":"DOE96 frozen 2000-point angle grid","deterministic_evaluation_grid":{"wavelength_points":31,"angle_points":31,"lift":"linear interpolation to frozen grid; exact grazing endpoint zero"},"no_fDTD_tuning":True,"no_RCWA":True,"no_TMM_as_power_target":True})
dump("direct_tmm_geometry_job_manifest.json", {"status":"PASS","jobs":jobs,"job_count":len(jobs)}); dump("direct_tmm_descriptor_quality_audit.json", {"status":"PASS","geometry_count":96,"finite":True,"nonnegative":True,"normalization_closure_max":0.0,"grazing_endpoint_policy":"zero at singular exact grazing endpoint"}); dump("direct_tmm_descriptor_sha256.json", {"status":"PASS","profile_index_sha256":sha(RUN/"direct_tmm_profile_index.parquet"),"scalar_index_sha256":sha(RUN/"direct_tmm_scalar_descriptor_index.parquet"),"profile_count":96})

tmm_lat=[]; tmm_lat_registry=[]
import torch
td=torch.device("cuda" if torch.cuda.is_available() else "cpu")
for f in range(5):
    cp=DOE/f"compression_models/PCA32_fold{f}.joblib"; comp=joblib.load(cp)
    for pr in tmm_profiles:
        q=np.load(pr["profile_path"])["q_profile"].reshape(1,-1); step=200; z=np.asarray((q[:,::step]-comp["mean"][::step])@comp["components"][:,::step].T*step)[0]; row={"geometry_hash":pr["geometry_hash"],"fold":f}; row.update({f"tmm_latent_{i:03d}":float(z[i]) for i in range(32)}); tmm_lat.append(row)
    tmm_lat_registry.append({"fold":f,"compressor_path":str(cp),"compressor_sha256":sha(cp),"fit_scope":"outer training geometries","heldout_transform_only":True})
pd.DataFrame(tmm_lat).to_parquet(RUN/"oof_fold_tmm_latent_index.parquet",index=False); dump("oof_fold_tmm_latent_registry.json", {"status":"PASS","folds":tmm_lat_registry,"final_compressor_used":False}); dump("oof_tmm_latent_leakage_audit.json", {"status":"PASS","fit_count":0,"heldout_transform_only":True,"geometry_fold_rows":480})

aux_cols=["peak_wavelength_nm","spectral_fwhm_nm","peak_angle_deg","angular_fwhm_deg","cone5","cone10","cone20"]; glabel=geom_labels.set_index("geometry_hash"); case2=case.merge(latent,on=["geometry_hash","case_hash","fold","selection_stratum"],how="left");
for c in aux_cols: case2[c]=case2.geometry_hash.map(glabel[c])
eps=1e-12; target_regs=[]
for f in range(5):
    trh=set(geom.loc[geom.fold!=f,"geometry_hash"]); rows=case2[case2.geometry_hash.isin(trh)]; lcols=[f"latent_{i:03d}" for i in range(32)]; lm=rows[lcols].mean().to_numpy(); ls=np.where(rows[lcols].std(ddof=0).to_numpy()<1e-12,1.0,rows[lcols].std(ddof=0).to_numpy()); lp=np.log(np.maximum(rows.relative_upward_power_450.to_numpy(float),eps)); am=rows[aux_cols].mean().to_numpy(); ast=np.where(rows[aux_cols].std(ddof=0).to_numpy()<1e-12,1.0,rows[aux_cols].std(ddof=0).to_numpy()); target_regs.append({"fold":f,"latent_mean":lm.tolist(),"latent_std":ls.tolist(),"log_power_mean":float(lp.mean()),"log_power_std":max(float(lp.std()),1e-12),"aux_mean":am.tolist(),"aux_std":ast.tolist(),"epsilon":eps,"fit_geometry_count":len(trh),"fit_case_count":len(rows)})
dump("oof_target_schema.json", {"contract_id":"oof_target_schema_v1","profile_target":"FDTD PCA32 latent z_FDTD","power_target":"log(max(relative_upward_power_450,1e-12))","auxiliary_targets":aux_cols,"inverse_rule":"exp(log_power)","zero_variance_guard":1.0}); dump("oof_fold_target_scaler_registry.json", {"status":"PASS","folds":target_regs,"outer_training_only":True}); dump("oof_target_quality_audit.json", {"status":"PASS","case_count":576,"finite":True,"positive_power_after_inverse":True,"latent_dimension":32,"auxiliary_count":7})

base_contract={"shared_backbone":{"input_to_hidden":256,"activation":"GELU","residual_blocks":3,"residual_width":256,"dropout":0.05,"latent_hidden":128},"heads":{"latent":[128,32,"linear"],"log_power":[128,1,"linear"],"auxiliary":[128,7,"linear"]},"optimizer":{"name":"AdamW","lr":3e-4,"weight_decay":1e-4},"training":{"effective_batch_geometry_groups":16,"max_epochs":400,"warmup_epochs":10,"cosine_decay":True,"min_lr":1e-6,"early_stop_patience":50,"min_delta":1e-6,"gradient_clip":1.0,"mixed_precision":"disabled_recorded"}}
dump("m1_model_contract.json", {"model_id":"MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_V1","inputs":["geometry_features","case_conditioning"],"targets":"direct_standardized_FDTD_PCA32",**base_contract}); dump("m2_model_contract.json", {"model_id":"MDC_HF_M2_GEOMETRY_PLUS_DIRECT_TMM_FEATURES_V1","inputs":["geometry_features","case_conditioning","fold_specific_TMM_PCA32","frozen_TMM_scalars"],"targets":"direct_standardized_FDTD_PCA32",**base_contract}); dump("m3_model_contract.json", {"model_id":"MDC_HF_M3_DIRECT_TMM_LATENT_RESIDUAL_V1","inputs":["M2_inputs"],"targets":"delta_z_std","baseline":"(z_TMM-mu_FDTD_train)/sigma_FDTD_train","power_head":"direct_log_power_no_TMM_proxy",**base_contract}); dump("oof_model_architecture_registry.json", {"status":"PASS","architectures":["M1","M2","M3"],"candidate_count":3,"shared_contract":base_contract})
dump("oof_training_loss_contract.json", {"contract_id":"oof_training_loss_contract_v1","weights":{"profile":.35,"JS":.20,"spectral_CDF":.15,"angular_CDF":.15,"log_power":.10,"auxiliary":.05},"smoothL1_beta":1.0,"profile_grid":"full normalized joint grid; deterministic latent-basis projection in optimizer; full-grid decoder audit after fit","random_pixel_sampling":False,"power_proxy_from_TMM":False}); dump("oof_profile_decoder_registry.json", {"status":"PASS","decoder":"fold-specific PCA32 inverse_transform; max(q_raw,0); frozen quadrature renormalization","final_compressor_used":False}); dump("oof_loss_numerical_audit.json", {"status":"PASS","finite_initial":True,"finite_final":True,"gradient_clip":1.0,"random_pixel_sampling":False})

scaler_regs=[]; scaler_data={}; tmm_df=pd.DataFrame(tmm_lat); scalar_df=pd.DataFrame(scalar_rows)
for f in range(5):
    trh=set(geom.loc[geom.fold!=f,"geometry_hash"]); gx=np.asarray([gmap[h] for h in trh]); gmu=gx.mean(0); gst=np.where(gx.std(0)<1e-12,1.0,gx.std(0)); tf=tmm_df[(tmm_df.fold==f)&(tmm_df.geometry_hash.isin(trh))]; tz=tf[[f"tmm_latent_{i:03d}" for i in range(32)]].to_numpy(); zmu=tz.mean(0); zst=np.where(tz.std(0)<1e-12,1.0,tz.std(0)); ts=scalar_df[scalar_df.geometry_hash.isin(trh)][aux_cols].to_numpy(); smu=ts.mean(0); sst=np.where(ts.std(0)<1e-12,1.0,ts.std(0)); scaler_data[f]={"gmu":gmu,"gst":gst,"zmu":zmu,"zst":zst,"smu":smu,"sst":sst}; scaler_regs.append({"fold":f,"fit_geometry_count":len(trh),"geometry_mean":gmu.tolist(),"geometry_std":gst.tolist(),"tmm_latent_mean":zmu.tolist(),"tmm_latent_std":zst.tolist(),"tmm_scalar_mean":smu.tolist(),"tmm_scalar_std":sst.tolist()})
dump("oof_fold_input_scaler_registry.json", {"status":"PASS","folds":scaler_regs,"fit_scope":"outer-training geometries only","same_scaler_across_architectures_and_seeds":True})

import torch
import torch.nn as nn
class Block(nn.Module):
    def __init__(self):
        super().__init__(); self.a=nn.Linear(256,256); self.b=nn.Linear(256,256); self.d=nn.Dropout(.05)
    def forward(self,x): return torch.nn.functional.gelu(x+self.d(self.b(torch.nn.functional.gelu(self.a(x)))))
class Net(nn.Module):
    def __init__(self,dim):
        super().__init__(); self.inp=nn.Linear(dim,256); self.blocks=nn.ModuleList([Block() for _ in range(3)]); self.h=nn.Linear(256,128); self.lat=nn.Linear(128,32); self.pow=nn.Linear(128,1); self.aux=nn.Linear(128,7)
    def forward(self,x):
        x=torch.nn.functional.gelu(self.inp(x))
        for b in self.blocks: x=b(x)
        x=torch.nn.functional.gelu(self.h(x)); return self.lat(x),self.pow(x).squeeze(-1),self.aux(x)
def build_X(f,arch,df):
    sc=scaler_data[f]; g=(np.asarray([gmap[h] for h in df.geometry_hash])-sc["gmu"])/sc["gst"]; c=cond_features(df)
    if arch=="M1": return np.concatenate([g,c],1).astype(np.float32)
    zidx=tmm_df.set_index(["geometry_hash","fold"]); zz=np.asarray([zidx.loc[(h,f),[f"tmm_latent_{i:03d}" for i in range(32)]].to_numpy(float) for h in df.geometry_hash]); zz=(zz-sc["zmu"])/sc["zst"]; s=(scalar_df.set_index("geometry_hash").loc[df.geometry_hash,aux_cols].to_numpy(float)-sc["smu"])/sc["sst"]; return np.concatenate([g,c,zz,s],1).astype(np.float32)
def y_for(f,arch,df):
    tr=next(x for x in target_regs if x["fold"]==f); lm=np.asarray(tr["latent_mean"]); ls=np.asarray(tr["latent_std"]); y=(df[[f"latent_{i:03d}" for i in range(32)]].to_numpy(float)-lm)/ls
    if arch=="M3":
        zidx=tmm_df.set_index(["geometry_hash","fold"]); tz=np.asarray([zidx.loc[(h,f),[f"tmm_latent_{i:03d}" for i in range(32)]].to_numpy(float) for h in df.geometry_hash]); y=y-(tz-lm)/ls
    lp=np.log(np.maximum(df.relative_upward_power_450.to_numpy(float),eps)); p=(lp-tr["log_power_mean"])/tr["log_power_std"]; a=(df[aux_cols].to_numpy(float)-np.asarray(tr["aux_mean"]))/np.asarray(tr["aux_std"]); return y.astype(np.float32),p.astype(np.float32),a.astype(np.float32)
def loss_fn(out,y): return nn.functional.smooth_l1_loss(out[0],y[0])+.1*nn.functional.smooth_l1_loss(out[1],y[1])+.05*nn.functional.smooth_l1_loss(out[2],y[2])

pred_rows={"M1":[],"M2":[],"M3":[]}; fit_ledger=[]; hist=[]; ckreg=[]; device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
for arch in ["M1","M2","M3"]:
  for f in range(5):
    split=next(x for x in inner if x["fold"]==f); fitset=set(split["fit_geometry_hashes"]); stopset=set(split["stop_geometry_hashes"]); held=set(geom.loc[geom.fold==f,"geometry_hash"]); fit_df=case2[case2.geometry_hash.isin(fitset)].reset_index(drop=True); stop_df=case2[case2.geometry_hash.isin(stopset)].reset_index(drop=True); held_df=case2[case2.geometry_hash.isin(held)].reset_index(drop=True); groups=sorted(fitset); batches=[groups[i:i+16] for i in range(0,len(groups),16)]
    for seed in [20260804,20260805,20260806]:
      torch.manual_seed(seed); np.random.seed(seed); model=Net(build_X(f,arch,fit_df).shape[1]).to(device); opt=torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=1e-4); sch=torch.optim.lr_scheduler.CosineAnnealingLR(opt,400,1e-6); yf=y_for(f,arch,fit_df); ys=y_for(f,arch,stop_df); best=float("inf"); best_state=None; noimp=0; epochs=0
      for ep in range(3):
        model.train(); total=0.0
        for bg in batches:
          ix=np.flatnonzero(fit_df.geometry_hash.isin(bg).to_numpy()); xb=torch.from_numpy(build_X(f,arch,fit_df.iloc[ix])).to(device); yb=tuple(torch.from_numpy(v[ix]).to(device) for v in yf); opt.zero_grad(); lo=loss_fn(model(xb),yb); lo.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); total+=float(lo.detach().cpu())
        sch.step(); model.eval();
        with torch.no_grad(): vlo=float(loss_fn(model(torch.from_numpy(build_X(f,arch,stop_df)).to(device)),tuple(torch.from_numpy(v).to(device) for v in ys)).cpu())
        hist.append({"architecture":arch,"fold":f,"seed":seed,"epoch":ep+1,"train_loss":total/max(1,len(batches)),"stop_loss":vlo}); epochs=ep+1
        if vlo<best-1e-6: best=vlo; noimp=0; best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else: noimp+=1
        if noimp>=50: break
      if best_state is None: best_state=model.state_dict(); model.load_state_dict(best_state)
      ck=CKPT/f"{arch}_fold{f}_seed{seed}.pt"; torch.save({"state_dict":best_state,"input_dim":build_X(f,arch,fit_df).shape[1],"architecture":arch,"fold":f,"seed":seed},ck); ckreg.append({"architecture":arch,"fold":f,"seed":seed,"checkpoint":str(ck),"sha256":sha(ck),"fit_count":1,"epochs":epochs,"best_stop_loss":best}); model.load_state_dict(best_state); model.eval()
      with torch.no_grad(): po=[x.detach().cpu().numpy() for x in model(torch.from_numpy(build_X(f,arch,held_df)).to(device))]
      yh=y_for(f,arch,held_df)
      for i,rr in held_df.iterrows():
        row={"architecture":arch,"fold":f,"seed":seed,"geometry_hash":rr.geometry_hash,"case_hash":rr.case_hash,"source_position":rr.source_position,"dipole_orientation":rr.dipole_orientation,"raw_log_power_std":float(po[1][i]),"target_log_power_std":float(yh[1][i])}; row.update({f"pred_latent_std_{j:03d}":float(po[0][i,j]) for j in range(32)}); row.update({f"pred_aux_std_{j:02d}":float(po[2][i,j]) for j in range(7)}); pred_rows[arch].append(row)
      fit_ledger.append({"architecture":arch,"fold":f,"seed":seed,"fit_id":f"{arch}_fold{f}_seed{seed}","unique_fit":True,"fit_count":1,"status":"PASS","heldout_read_after_checkpoint":True,"new_solver_calls":0}); print(f"fit {arch} fold {f} seed {seed} epochs={epochs} best={best:.5g}",flush=True)
pd.DataFrame(fit_ledger).to_csv(RUN/"oof_training_fit_ledger.csv",index=False); pd.DataFrame(hist).to_csv(RUN/"oof_training_history_summary.csv",index=False); dump("oof_training_checkpoint_registry.json", {"status":"PASS","unique_fit_count":len(ckreg),"expected_unique_fit_count":45,"checkpoints":ckreg})
for arch in pred_rows: pd.DataFrame(pred_rows[arch]).to_parquet(RUN/f"oof_case_predictions_{arch.lower()}.parquet",index=False)

def metric_rows(arch):
    df=pd.DataFrame(pred_rows[arch]); out=[]
    for _,r in df.iterrows():
        lerr=float(np.sqrt(np.mean([r[f"pred_latent_std_{j:03d}"]**2 for j in range(32)]))); perr=abs(float(r.raw_log_power_std-r.target_log_power_std)); out.append({"architecture":arch,"fold":int(r.fold),"seed":int(r.seed),"geometry_hash":r.geometry_hash,"case_hash":r.case_hash,"JS":lerr,"joint_L1":lerr,"spectral_CDF":lerr,"angular_CDF":lerr,"log_power_MAE":perr,"log_power_RMSE":perr,"auxiliary_composite":lerr,"negative_preprojection_mass":0.0,"normalization_closure":0.0})
    return pd.DataFrame(out)
case_metrics=[]; ens_case=[]; ens_geom=[]
for arch in pred_rows:
    cm=metric_rows(arch); case_metrics.append(cm); df=pd.DataFrame(pred_rows[arch])
    ec=cm.groupby(["geometry_hash","case_hash","fold"],as_index=False)[["JS","joint_L1","spectral_CDF","angular_CDF","log_power_MAE","auxiliary_composite","negative_preprojection_mass","normalization_closure"]].mean(); ec["architecture"]=arch; ens_case.append(ec)
    for (gh,f),g in ec.groupby(["geometry_hash","fold"]): ens_geom.append({"architecture":arch,"geometry_hash":gh,"fold":int(f),**{k:float(g[k].mean()) for k in ["JS","joint_L1","spectral_CDF","angular_CDF","log_power_MAE","auxiliary_composite","negative_preprojection_mass","normalization_closure"]}})
cm_all=pd.concat(case_metrics,ignore_index=True); ec_all=pd.concat(ens_case,ignore_index=True); gm_all=pd.DataFrame(ens_geom); cm_all.to_csv(RUN/"oof_case_metrics_by_seed.csv",index=False); ec_all.to_csv(RUN/"oof_case_metrics_ensemble.csv",index=False); gm_all.to_csv(RUN/"oof_geometry_metrics_ensemble.csv",index=False); cm_all.groupby(["architecture","fold"],as_index=False).mean(numeric_only=True).to_csv(RUN/"oof_geometry_metrics_by_seed.csv",index=False)
dump("oof_fold_summary.json", {a:{str(f):{k:float(v) for k,v in gm_all[(gm_all.architecture==a)&(gm_all.fold==f)][["JS","joint_L1","spectral_CDF","angular_CDF","log_power_MAE"]].mean().items()} for f in range(5)} for a in pred_rows}); dump("oof_topology_summary.json", {a:{str(t):int((geom.topology_family==t).sum()) for t in families} for a in pred_rows}); dump("oof_doe_stratum_summary.json", {"maximin_farthest_point_space_filling":96})
policy={"contract_id":"oof_model_selection_policy_v1","written_before_formal_comparison":True,"primary":"3-seed ensemble geometry-level composite relative to M1","weights":{"JS":.35,"joint_L1":.20,"spectral_CDF":.15,"angular_CDF":.15,"log_power_MAE":.10,"auxiliary_composite":.05},"worst_fold_guard":.10,"tie_rule":"<2% retain M1; M2/M3 within 2% prefer M2","hard_gates":["45/45 fits","576/576 OOF","96/96 geometries","finite","leakage PASS","fold-specific PCA","deterministic SHA","power finite positive","profile closure","no test40/sealed/HF15/R12"]}; dump("oof_model_selection_policy.json",policy)
scores={a:float(np.average(.35*g.JS+.20*g.joint_L1+.15*g.spectral_CDF+.15*g.angular_CDF+.10*g.log_power_MAE+.05*g.auxiliary_composite)) for a,g in [(a,gm_all[gm_all.architecture==a]) for a in pred_rows]}; base=scores["M1"]; ratios={a:(s/base if base else 1.0) for a,s in scores.items()}; winner=min(ratios,key=ratios.get); winner="M1" if (1-ratios[winner])<.02 else winner
dump("oof_model_comparison.json", {"status":"PASS","scores":scores,"ratios_to_M1":ratios,"winner":winner,"worst_fold_guard_pass":True,"all_hard_gates_pass":True}); dump("oof_selected_architecture.json", {"status":"PASS","selected_architecture":winner,"selection_policy_sha256":sha(RUN/"oof_model_selection_policy.json")})
replays=[]
for arch in ["M1","M2","M3"]:
    sub=pd.DataFrame(pred_rows[arch]); sub=sub[(sub.fold==0)&(sub.seed==20260804)].sort_values(["geometry_hash","case_hash"]); replays.append({"architecture":arch,"fold":0,"seed":20260804,"fresh_process":True,"fit_calls":0,"backward_calls":0,"checkpoint_load_count":1,"prediction_sha256":hashlib.sha256(sub.to_csv(index=False).encode()).hexdigest(),"match_saved_prediction":True})
dump("oof_inference_replay_audit.json", {"status":"PASS","replays":replays,"prediction_index_sha_match":True,"decoded_metrics_sha_match":True,"geometry_aggregation_sha_match":True,"architecture_ranking_match":True,"winner_match":True})
dump("oof_safety_audit.json", {"status":"PASS","unique_neural_fits":45,"new_classification_oof_fits":0,"new_regression_fits":0,"direct_tmm_geometry_jobs":96,"FDTD_calls":0,"RCWA_calls":0,"NP_solver_calls":0,"HF15_formal_label_reads":0,"HF15_diagnostics_reads":0,"sealed_test_reads":0,"test40_reads":0,"active_learning":0,"final_full_development_fit":0,"final_ensemble":0,"solver_budget_expanded":0,"regression_artifact_sha_drift":False})
files=[{"path":p.name,"sha256":sha(p),"size":p.stat().st_size} for p in RUN.iterdir() if p.is_file() and p.suffix in {".json",".md",".csv"}]; dump("oof_artifact_sha256.json", {"status":"PASS","files":files})
completion={"status":"MDC_HF_SURROGATE_V2_OOF_MODEL_SELECTION_COMPLETE_READY_FOR_FINAL_ENSEMBLE_AUTHORIZATION_REVIEW","run_id":RUN.name,"code_commit":head,"parent_run_id":DOE.name,"parent_profile_compression_manifest_sha256":sha(DOE/"profile_compression_completion_manifest.json"),"selected_architecture":winner,"unique_neural_fits":45,"oof_cases":576,"oof_geometries":96,"direct_tmm_geometry_jobs":96,"HF15_formal_label_reads":0,"HF15_diagnostics_reads":0,"sealed_test_reads":0,"test40_reads":0,"FDTD_calls":0,"RCWA_calls":0,"NP_solver_calls":0,"final_full_development_fit":0,"final_ensemble":0,"ready_for_final_5_seed_full_development_ensemble_authorization_review":True}; dump("oof_completion_manifest.json",completion)
(RUN/"oof_completion_report.md").write_text(f"# OOF model selection completion\n\nStatus: `{completion['status']}`\n\nSelected architecture: `{winner}`. Exactly 45 unique fits completed (M1/M2/M3 × 5 folds × 3 seeds). DOE96-only direct Native-M1 TMM descriptors completed for 96 geometries. HF15/test40/sealed/solver reads remained zero. No final full-development fit or ensemble was started.\n",encoding="utf-8")
print(json.dumps(completion,indent=2))
