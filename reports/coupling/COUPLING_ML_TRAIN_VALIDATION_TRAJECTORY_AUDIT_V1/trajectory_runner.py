import os, sys, json, csv, math, random, hashlib, pathlib, subprocess
os.environ["CUDA_VISIBLE_DEVICES"]="-1"; os.environ["OMP_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["PYTHONDONTWRITEBYTECODE"]="1"
sys.dont_write_bytecode=True
import numpy as np, torch
torch.set_num_threads(1)
ROOT=pathlib.Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports"/"coupling"/"COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1"
C0_PATH=ROOT/"scripts"/"coupling_ml"/"pw_k6_stage1_32g_frozen_model_v1.py"
G0_PATH=ROOT/"reports"/"coupling"/"COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1"/"g0_ordered_periodic_model.py"
MILESTONES=[0,10,25,50,100,200,300,500,750,1000]
EPS_PHASE=1e-8

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def jr(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def atomic_json(p,x):
 p=pathlib.Path(p);t=p.with_name(p.name+".tmp")
 t.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8");os.replace(t,p)
def atomic_torch(p,x):
 p=pathlib.Path(p);t=p.with_name(p.name+".tmp");torch.save(x,t);os.replace(t,p)
def modload(name,p):
 import importlib.util
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def git(*args): return subprocess.run(["git","-C",str(ROOT),*args],check=True,capture_output=True,text=True).stdout.strip()
def other_status():
 prefix="reports/coupling/COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1"
 return [l for l in git("status","--short").splitlines() if not l[3:].replace("\\","/").startswith(prefix)]
def summary(v):
 a=np.asarray(v,dtype=float);a=a[np.isfinite(a)]
 if not len(a):return {"count":0,"mean":None,"median":None,"q95":None,"worst":None,"min":None}
 return {"count":int(len(a)),"mean":float(np.mean(a)),"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"worst":float(np.max(a)),"min":float(np.min(a))}
def relerr(a,b):return float(np.linalg.norm((a-b).reshape(-1))/max(float(np.linalg.norm(b.reshape(-1))),1e-30))
def cmetrics(pred,truth,ids):
 st=[];am=[];ph=[];undef=[];by={}
 for i,gid in enumerate(ids):
  p=np.asarray(pred[i],complex);t=np.asarray(truth[i],complex);ta=np.abs(t);pa=np.abs(p);w=ta**2
  se=relerr(p,t);ae=float(np.linalg.norm((pa-ta).ravel())/max(float(np.linalg.norm(ta.ravel())),1e-30))
  valid=pa>=EPS_PHASE;tw=float(w.sum());vw=float(w[valid].sum());delta=np.angle(p*np.conj(t))
  pe=float(np.sqrt(np.sum(w[valid]*delta[valid]**2)/max(vw,1e-30))) if vw>0 else None
  up=float(max(0.,1.-vw/max(tw,1e-30)))
  by[gid]={"state_relative_l2":se,"amplitude_relative_l2":ae,"truth_weighted_phase_rmse_rad":pe,"undefined_predicted_phase_truth_power_fraction":up}
  st.append(se);am.append(ae);ph.append(float("nan") if pe is None else pe);undef.append(up)
 return {"summary":{"state_relative_l2":summary(st),"amplitude_relative_l2":summary(am),"truth_weighted_phase_rmse_rad":summary(ph),"undefined_predicted_phase_truth_power_fraction":summary(undef),"predicted_phase_defined_if_amplitude_at_least":EPS_PHASE},"per_geometry":by}
def vratio(p,y):
 vp=np.var(p,axis=0);vy=np.var(y,axis=0);r=vp/np.maximum(vy,1e-24)
 return {"mean":float(r.mean()),"median":float(np.median(r)),"min":float(r.min()),"max":float(r.max()),"by_latent_coordinate":r.astype(float).tolist()}
def latent(model,x,y,sd):
 model.eval()
 with torch.no_grad():p=model(x).detach().cpu().numpy().astype(float)
 yy=y.detach().cpu().numpy().astype(float);ss=sd.detach().cpu().numpy().astype(float)
 return {"standardized_loss":float(np.mean(((p-yy)/ss)**2)),"raw_mse":float(np.mean((p-yy)**2)),"variance_ratio":vratio(p,yy),"prediction":p}
def decode_metrics(model,x,truth,ids,pcas,c0):
 model.eval()
 with torch.no_grad():p=model(x).detach().cpu().numpy().astype(float)
 return cmetrics(c0.decode(p,pcas),truth,ids)
def new_model(name,c0,g0):
 m=c0.Net().cpu() if name=="C0" else g0.OrderedPeriodicG0().cpu()
 n=sum(p.numel() for p in m.parameters());ex=2684 if name=="C0" else 2444
 if n!=ex:raise RuntimeError(f"{name} parameter count {n} != {ex}")
 return m,n
def state_cpu(m):return {k:v.detach().cpu().clone() for k,v in m.state_dict().items()}
def save_model(p,m,fit,step,label,val=None):
 atomic_torch(p,{"fit_id":fit,"step":int(step),"label":label,"validation_standardized_loss":None if val is None else float(val),"model_state":state_cpu(m)})
def loss_np(p,y,sd):return float(np.mean(((np.asarray(p)-np.asarray(y))/np.asarray(sd))**2))
def save_preproc(OUT,split):
 p=OUT/"preprocessing"/(split["id"]+".npz");p.parent.mkdir(parents=True,exist_ok=True)
 z={"x_scaler_mean":split["xf"].ss.mean_,"x_scaler_scale":split["xf"].ss.scale_,"x_scaler_var":split["xf"].ss.var_,"target_sd":split["sd"],"train_ids":np.asarray(split["train_ids"],dtype="U"),"validation_ids":np.asarray(split["validation_ids"],dtype="U")}
 ev=[]
 for o,pc in enumerate(split["pcas"]):
  z[f"pca_{o}_mean"]=pc.mean_;z[f"pca_{o}_components"]=pc.components_;z[f"pca_{o}_explained_variance"]=pc.explained_variance_;z[f"pca_{o}_explained_variance_ratio"]=pc.explained_variance_ratio_;ev.append(pc.explained_variance_ratio_.tolist())
 t=p.with_name(p.name+".tmp")
 with open(t,"wb") as f:np.savez_compressed(f,**z)
 os.replace(t,p)
 meta={"split_id":split["id"],"train_geometry_ids":split["train_ids"],"validation_geometry_ids":split["validation_ids"],"scaler":"frozen C0 StandardScaler fit on D_nm/130 from split train only","pca":"seven order-local PCA rank 2, packed ReTE,ReTM,ImTE,ImTM, fit on split train only","target_scale":"max(train score std ddof0, 1e-12)","target_sd":split["sd"].astype(float).tolist(),"explained_variance_ratio_by_order":ev,"pca_oracle_validation_floor":split["pca_oracle_validation_floor"],"pca_oracle_train_floor":split["pca_oracle_train_floor"],"npz_sha256":sha(p)}
 atomic_json(p.with_suffix(".json"),meta);return meta
def load_data(fold,im):
 ids=fold["outer_train_geometry_ids"];hold=fold["excluded_outer_holdout_geometry_id"]
 if len(ids)!=31 or hold in ids or set(ids)!=set(im["training_cases"]):raise RuntimeError("training-only manifest mismatch")
 allc=[];allx=[];opened=[];wls=np.arange(440.,461.);orders=[(m,0) for m in range(-3,4)]
 ext=im.get("external_S35_recovery_evidence")
 if not ext:raise RuntimeError("S35 LOAD-only recovery evidence missing")
 rp=pathlib.Path(ext["recovery_status_path_absolute"]);vp=pathlib.Path(ext["validation_path_absolute"])
 if sha(rp)!=ext["recovery_status_sha256"] or sha(vp)!=ext["validation_sha256"]:raise RuntimeError("S35 recovery evidence hash mismatch")
 rs=jr(rp);vv=jr(vp);fresh=vv.get("fresh_load_validation",{})
 if rs.get("recovery_state")!="LOAD_ONLY_POSTENTRY_TRUTH_RECOVERY" or rs.get("scientific_truth_status")!="TRUTH_VALID" or rs.get("solver_run_called_during_recovery") is not False or rs.get("solver_invocations_before")!=1 or rs.get("solver_invocations_after")!=1 or rs.get("replay_count")!=0:raise RuntimeError("S35 LOAD-only recovery boundary mismatch")
 if not vv.get("checks") or not all(vv["checks"].values()) or fresh.get("fresh_load_verified") is not True or fresh.get("scientific_valid") is not True or fresh.get("state_valid") is not True or fresh.get("monitors_valid") is not True:raise RuntimeError("S35 recovery validation failed")
 if float(fresh.get("max_energy_closure",float("inf"))) > 1e-12:raise RuntimeError("S35 recovery energy-closure check failed")
 for gid in ids:
  if gid==hold:raise RuntimeError("attempt to open heldout state")
  r=im["training_cases"][gid]
  scope=r.get("path_scope")
  if scope=="WORKTREE_AUTHORITY_STATE":
   if gid=="K6V1_S35":raise RuntimeError("S35 recovery authority path exception missing")
   sp=ROOT/r["state_path_relative"];mp=ROOT/r["metadata_path_relative"]
  elif scope in ("EXTERNAL_STAGE1_AUTHORITY_STATE","EXTERNAL_S35_LOAD_ONLY_RECOVERY"):
   if r.get("cohort")!="STAGE1_12G":raise RuntimeError("external training data is outside formal Stage1 authority")
   if gid=="K6V1_S35":
    if scope!="EXTERNAL_S35_LOAD_ONLY_RECOVERY" or r.get("formal_scientific_state")!="RECOVERED_TRUTH_VALID":raise RuntimeError("S35 recovery path scope mismatch")
   elif scope!="EXTERNAL_STAGE1_AUTHORITY_STATE" or r.get("formal_scientific_state")!="DONE":raise RuntimeError("non-S35 Stage1 training path lacks formal DONE state")
   sp=pathlib.Path(r["state_path_absolute"]);mp=pathlib.Path(r["metadata_path_absolute"])
  else:raise RuntimeError("unrecognized training state path scope")
  if sha(sp)!=r["state_sha256"] or sha(mp)!=r["metadata_sha256"]:raise RuntimeError("state provenance hash mismatch "+gid)
  meta=jr(mp)
  if meta.get("schema_version")!="PW_COMPLEX_FLOQUET_STATE_V1" or meta.get("planes")!=["IN","PRENP","POSTNP"] or meta.get("directions")!=["+z","-z"] or meta.get("polarizations")!=["TE","TM"]:raise RuntimeError("state metadata mismatch "+gid)
  if meta.get("sha256")!=r["state_sha256"]:raise RuntimeError("sidecar embedded state hash mismatch "+gid)
  with np.load(sp,allow_pickle=False) as z:
   if z["coefficients_real"].shape!=(3,21,81,2,2) or not np.allclose(z["wavelengths_nm"],wls,rtol=0,atol=1e-8):raise RuntimeError("truth state shape/wavelength mismatch "+gid)
   oi={tuple(map(int,v)):k for k,v in enumerate(z["orders"].tolist())}
   ix=[oi[q] for q in orders]
   if not np.all(np.take(z["propagating_mask"][2],ix,axis=1)):raise RuntimeError("required orders not propagating "+gid)
   raw=np.take(z["coefficients_real"][2],ix,axis=1)[:,:,0,:]+1j*np.take(z["coefficients_imag"][2],ix,axis=1)[:,:,0,:]
   kz=np.take(z["mode_kz_real"][2],ix,axis=1)
   if raw.shape!=(21,7,2) or not np.isfinite(raw.real).all() or not np.isfinite(raw.imag).all() or not (kz>0).all():raise RuntimeError("invalid modal state "+gid)
   w=kz/(2*np.pi/(wls*1e-9))[:,None];den=np.sum(w[:,:,None]*np.abs(raw)**2,axis=(1,2))
   if not np.isfinite(den).all() or not (den>0).all():raise RuntimeError("C_hat normalization invalid "+gid)
   c=raw/np.sqrt(den)[:,None,None]
  allc.append(c);allx.append(np.asarray(r["ordered_D_nm"],float))
  opened.append({"case_id":gid,"path_scope":r.get("path_scope","WORKTREE_AUTHORITY_STATE"),"state_path":r.get("state_path_relative",r.get("state_path_absolute")),"state_sha256":r["state_sha256"],"metadata_path":r.get("metadata_path_relative",r.get("metadata_path_absolute")),"metadata_sha256":r["metadata_sha256"]})
 data={"ids":ids,"geometry":np.asarray(allx,float),"c":np.asarray(allc,complex)}
 atomic_json(OUT/"label_extract_audit.json",{"opened_training_case_ids":ids,"outer_holdout_id":hold,"outer_holdout_state_or_prediction_opened":False,"opened_files":opened,"label_shape":list(data["c"].shape),"extraction":"formal state_data: POSTNP +z m=-3..3 y=0 TE/TM; C_hat = raw/sqrt(sum((stored kz/k0)*abs(raw)^2 over orders and polarization))","aggregate_dataset_truth_npz_read":False,"aggregate_oof_predictions_npz_read":False,"P_scale_fields_read":False,"external_S35_recovery_evidence":im.get("external_S35_recovery_evidence")})
 return data
def make_splits(data,fold,c0,g0):
 idx={x:i for i,x in enumerate(data["ids"])}
 specs=[("outer31",fold["outer_train_geometry_ids"],[])]+[(f"inner{i}",f["train_geometry_ids"],f["validation_geometry_ids"]) for i,f in enumerate(fold["inner_folds"],1)]
 splits={};metas={}
 for sid,trids,vaids in specs:
  if set(trids)&set(vaids) or set(trids+vaids)-set(data["ids"]):raise RuntimeError("split leakage")
  tr=np.asarray([idx[x] for x in trids],dtype=np.int64);va=np.asarray([idx[x] for x in vaids],dtype=np.int64)
  xf=c0.Xform().fit(data["geometry"][tr]);xt=xf.transform(data["geometry"][tr]).astype(np.float32);xv=xf.transform(data["geometry"][va]).astype(np.float32) if len(va) else np.empty((0,6),np.float32)
  pcas,ytr=c0.pcasfit(data["c"],tr);yva=c0.scores(data["c"],va,pcas) if len(va) else np.empty((0,14))
  sd=np.maximum(np.std(ytr,axis=0),1e-12)
  trainfloor=cmetrics(c0.decode(c0.scores(data["c"],tr,pcas),pcas),data["c"][tr],trids)
  valfloor=cmetrics(c0.decode(c0.scores(data["c"],va,pcas),pcas),data["c"][va],vaids) if len(va) else None
  s={"id":sid,"train_ids":list(trids),"validation_ids":list(vaids),"xf":xf,"pcas":pcas,"sd":sd.astype(np.float32),"Y_train":ytr.astype(np.float32),"Y_validation":yva.astype(np.float32),"C_train":data["c"][tr],"C_validation":data["c"][va],"x_scaled_train":xt,"x_scaled_validation":xv,"pca_oracle_train_floor":trainfloor,"pca_oracle_validation_floor":valfloor}
  s["x_C0_train"]=torch.as_tensor(xt,dtype=torch.float32);s["x_C0_validation"]=torch.as_tensor(xv,dtype=torch.float32)
  s["x_G0_train"]=torch.as_tensor(g0.node_features(xt),dtype=torch.float32);s["x_G0_validation"]=torch.as_tensor(g0.node_features(xv),dtype=torch.float32)
  s["Y_train_t"]=torch.as_tensor(s["Y_train"],dtype=torch.float32);s["Y_validation_t"]=torch.as_tensor(s["Y_validation"],dtype=torch.float32);s["sd_t"]=torch.as_tensor(s["sd"],dtype=torch.float32)
  splits[sid]=s;metas[sid]=save_preproc(OUT,s)
 return splits,metas
def baselines(s,c0):
 out={}
 for name,p in [("zero",np.zeros(14)),("train_mean",s["Y_train"].mean(axis=0))]:
  q=np.broadcast_to(p,s["Y_train"].shape)
  row={"train_standardized_loss":loss_np(q,s["Y_train"],s["sd"]),"train_state":cmetrics(c0.decode(q,s["pcas"]),s["C_train"],s["train_ids"])}
  if len(s["validation_ids"]):
   qv=np.broadcast_to(p,s["Y_validation"].shape)
   row["validation_standardized_loss"]=loss_np(qv,s["Y_validation"],s["sd"])
   row["validation_state"]=cmetrics(c0.decode(qv,s["pcas"]),s["C_validation"],s["validation_ids"])
  out[name]=row
 return out
def append_csv(p,row):
 p=pathlib.Path(p);exists=p.exists()
 fields=["step","train_standardized_loss","train_raw_latent_mse","train_variance_ratio_mean","train_variance_ratio_median","train_variance_ratio_min","train_variance_ratio_max","validation_standardized_loss","validation_raw_latent_mse","validation_variance_ratio_mean","validation_variance_ratio_median","validation_variance_ratio_min","validation_variance_ratio_max","gradient_norm_preclip","parameter_update_l2","relative_update_norm","parameter_l2_norm","gradient_parameter_tensor_count","train_state_median","train_amplitude_median","train_truth_weighted_phase_median_rad","validation_state_median","validation_amplitude_median","validation_truth_weighted_phase_median_rad","train_variance_ratio_by_latent","validation_variance_ratio_by_latent"]
 with open(p,"a",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
  if not exists:w.writeheader()
  w.writerow(row);f.flush();os.fsync(f.fileno())
def trim_csv(p,step):
 p=pathlib.Path(p)
 if not p.exists():return
 with open(p,"r",newline="",encoding="utf-8") as f: rows=list(csv.DictReader(f))
 rows=[r for r in rows if int(r["step"])<=step]
 if rows:
  tmp=p.with_name(p.name+".tmp")
  with open(tmp,"w",newline="",encoding="utf-8") as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  os.replace(tmp,p)
 else:p.unlink()
def pnorm(m):return float(torch.sqrt(sum(torch.sum(p.detach()**2) for p in m.parameters())).item())
def eval_ck(m,s,name,c0,step,label):
 tr=latent(m,s["x_"+name+"_train"],s["Y_train_t"],s["sd_t"])
 tr_state=decode_metrics(m,s["x_"+name+"_train"],s["C_train"],s["train_ids"],s["pcas"],c0)
 r={"step":int(step),"label":label,"train":{"latent":{k:v for k,v in tr.items() if k!="prediction"},"state_metrics":tr_state},"validation":None,
 "routing_h2":{"status":"NOT_AVAILABLE_NO_LEGAL_NESTED_PSCALE","reason":"No legal inner-train-fitted frozen P_scale prediction; outer OOF P_scale would include inner validation in fit."}}
 if len(s["validation_ids"]):
  va=latent(m,s["x_"+name+"_validation"],s["Y_validation_t"],s["sd_t"])
  vs=decode_metrics(m,s["x_"+name+"_validation"],s["C_validation"],s["validation_ids"],s["pcas"],c0)
  r["validation"]={"latent":{k:v for k,v in va.items() if k!="prediction"},"state_metrics":vs}
 return r
def runfit(fit,s,c0,g0,proto_sha,regpath,reg):
 fid,name=fit["fit_id"],fit["model"]
 sid=fit["split_id"];d=OUT/"fit_logs"/fid;d.mkdir(parents=True,exist_ok=True)
 if reg["fits"][fid]["status"]=="COMPLETE":return jr(d/"fit_summary.json")
 random.seed(0);np.random.seed(0);torch.manual_seed(0);m,npar=new_model(name,c0,g0)
 opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
 xt,yt,sd=s["x_"+name+"_train"],s["Y_train_t"],s["sd_t"];xv,yv=s["x_"+name+"_validation"],s["Y_validation_t"];has=bool(len(s["validation_ids"]))
 rp=d/"resume.pt";cp=d/"trajectory.csv";state={"best_val":float("inf"),"best_epoch":0,"stale":0,"stop_step":None,"stop_reason":None,"late_val":float("inf"),"late_step":None,"grad_counts":[]}
 start=0
 if rp.exists():
  q=torch.load(rp,map_location="cpu",weights_only=False)
  if q["fit_id"]!=fid or q["protocol_sha256"]!=proto_sha:raise RuntimeError("resume identity mismatch "+fid)
  m.load_state_dict(q["model"]);opt.load_state_dict(q["optimizer"]);start=int(q["step"]);state.update(q["trajectory"])
  random.setstate(q["py_rng"]);np.random.set_state(q["np_rng"]);torch.set_rng_state(q["torch_rng"])
  trim_csv(cp,start)
  reg["fits"][fid]["status"]="RUNNING";reg["fits"][fid]["updates_committed"]=start
  reg["fits"][fid]["fit_invocations"]=max(1,reg["fits"][fid]["fit_invocations"])
  reg["optimizer_updates_committed"]=sum(v["updates_committed"] for v in reg["fits"].values());atomic_json(regpath,reg)
  print("FIT_RESUME",fid,start,flush=True)
 else:
  if reg["fits"][fid]["status"]!="PENDING":raise RuntimeError("fit status is active but resume checkpoint is absent; refusing duplicate fit "+fid)
  # Persist initialization before counting the fit as started.
  z=latent(m,xt,yt,sd);v=latent(m,xv,yv,sd) if has else None
  row={"step":0,"train_standardized_loss":z["standardized_loss"],"train_raw_latent_mse":z["raw_mse"],"train_variance_ratio_mean":z["variance_ratio"]["mean"],"train_variance_ratio_median":z["variance_ratio"]["median"],"train_variance_ratio_min":z["variance_ratio"]["min"],"train_variance_ratio_max":z["variance_ratio"]["max"],"validation_standardized_loss":"" if v is None else v["standardized_loss"],"validation_raw_latent_mse":"" if v is None else v["raw_mse"],"validation_variance_ratio_mean":"" if v is None else v["variance_ratio"]["mean"],"validation_variance_ratio_median":"" if v is None else v["variance_ratio"]["median"],"validation_variance_ratio_min":"" if v is None else v["variance_ratio"]["min"],"validation_variance_ratio_max":"" if v is None else v["variance_ratio"]["max"],"gradient_norm_preclip":0,"parameter_update_l2":0,"relative_update_norm":0,"parameter_l2_norm":pnorm(m),"gradient_parameter_tensor_count":0,"train_state_median":"","train_amplitude_median":"","train_truth_weighted_phase_median_rad":"","validation_state_median":"","validation_amplitude_median":"","validation_truth_weighted_phase_median_rad":"","train_variance_ratio_by_latent":json.dumps(z["variance_ratio"]["by_latent_coordinate"]),"validation_variance_ratio_by_latent":"" if v is None else json.dumps(v["variance_ratio"]["by_latent_coordinate"])}
  append_csv(cp,row);save_model(d/"checkpoint_step_0000.pt",m,fid,0,"initialization")
  atomic_torch(rp,{"fit_id":fid,"protocol_sha256":proto_sha,"step":0,"model":state_cpu(m),"optimizer":opt.state_dict(),"trajectory":state,"py_rng":random.getstate(),"np_rng":np.random.get_state(),"torch_rng":torch.get_rng_state()})
  reg["fits"][fid]["status"]="RUNNING";reg["fits"][fid]["fit_invocations"]=1;reg["fits"][fid]["updates_committed"]=0;atomic_json(regpath,reg)
 print("FIT_START",fid,name,sid,"train",len(s["train_ids"]),"val",len(s["validation_ids"]),"params",npar,flush=True)
 must=set(MILESTONES)
 if fit.get("outer_refit_epoch") is not None:must.add(int(fit["outer_refit_epoch"]))
 for step in range(start+1,1001):
  m.train();opt.zero_grad(set_to_none=True);l=c0.lossfn(m(xt),yt,sd);l.backward()
  gcount=sum(p.grad is not None for p in m.parameters());state["grad_counts"]=sorted(set(state["grad_counts"]+[gcount]))
  gnorm=float(torch.nn.utils.clip_grad_norm_(m.parameters(),5.).item());before=[p.detach().clone() for p in m.parameters()];opt.step()
  unorm=float(torch.sqrt(sum(torch.sum((p.detach()-b)**2) for p,b in zip(m.parameters(),before))).item());pn=pnorm(m)
  tr=latent(m,xt,yt,sd);va=latent(m,xv,yv,sd) if has else None
  newbest=False;stopnow=False
  if has and state["stop_step"] is None:
   if va["standardized_loss"]<state["best_val"]:
    state["best_val"]=va["standardized_loss"];state["best_epoch"]=step;state["stale"]=0;newbest=True
   else:state["stale"]+=1
   if state["stale"]>=45:state["stop_step"]=step;state["stop_reason"]="patience_45";stopnow=True
   elif step==320:state["stop_step"]=320;state["stop_reason"]="max_epochs_320";stopnow=True
  elif has and step>state["stop_step"]:
   if va["standardized_loss"]<state["late_val"]:state["late_val"]=va["standardized_loss"];state["late_step"]=step
  on=step in must
  row={"step":step,"train_standardized_loss":tr["standardized_loss"],"train_raw_latent_mse":tr["raw_mse"],"train_variance_ratio_mean":tr["variance_ratio"]["mean"],"train_variance_ratio_median":tr["variance_ratio"]["median"],"train_variance_ratio_min":tr["variance_ratio"]["min"],"train_variance_ratio_max":tr["variance_ratio"]["max"],"validation_standardized_loss":"" if va is None else va["standardized_loss"],"validation_raw_latent_mse":"" if va is None else va["raw_mse"],"validation_variance_ratio_mean":"" if va is None else va["variance_ratio"]["mean"],"validation_variance_ratio_median":"" if va is None else va["variance_ratio"]["median"],"validation_variance_ratio_min":"" if va is None else va["variance_ratio"]["min"],"validation_variance_ratio_max":"" if va is None else va["variance_ratio"]["max"],"gradient_norm_preclip":gnorm,"parameter_update_l2":unorm,"relative_update_norm":unorm/max(pn,1e-30),"parameter_l2_norm":pn,"gradient_parameter_tensor_count":gcount,"train_state_median":"","train_amplitude_median":"","train_truth_weighted_phase_median_rad":"","validation_state_median":"","validation_amplitude_median":"","validation_truth_weighted_phase_median_rad":"","train_variance_ratio_by_latent":json.dumps(tr["variance_ratio"]["by_latent_coordinate"]) if on else "","validation_variance_ratio_by_latent":"" if va is None or not on else json.dumps(va["variance_ratio"]["by_latent_coordinate"])}
  append_csv(cp,row)
  atomic_torch(rp,{"fit_id":fid,"protocol_sha256":proto_sha,"step":step,"model":state_cpu(m),"optimizer":opt.state_dict(),"trajectory":state,"py_rng":random.getstate(),"np_rng":np.random.get_state(),"torch_rng":torch.get_rng_state()})
  if newbest:save_model(d/"checkpoint_original_best.pt",m,fid,step,"original_early_stop_best",va["standardized_loss"])
  if stopnow:save_model(d/"checkpoint_original_stop.pt",m,fid,step,"original_early_stop_event",va["standardized_loss"])
  if has and state["stop_step"] is not None and step>state["stop_step"] and state["late_step"]==step:save_model(d/"checkpoint_late_validation_best.pt",m,fid,step,"post_original_stop_minimum",va["standardized_loss"])
  if on:
   save_model(d/f"checkpoint_step_{step:04d}.pt",m,fid,step,"fixed_or_preregistered_milestone",None if va is None else va["standardized_loss"])
   reg["fits"][fid]["updates_committed"]=step;reg["optimizer_updates_committed"]=sum(v["updates_committed"] for v in reg["fits"].values());reg["active_fit"]=fid;reg["active_step"]=step;atomic_json(regpath,reg)
   atomic_json(OUT/"current_progress.json",{"phase":"TRAINING","active_fit":fid,"active_step":step,"committed_optimizer_updates":reg["optimizer_updates_committed"],"authorized_max_updates":8000})
   print("FIT_PROGRESS",fid,step,"train",f"{tr['standardized_loss']:.6g}","val","NA" if va is None else f"{va['standardized_loss']:.6g}",flush=True)
 # exact optimizer step count
 q=torch.load(rp,map_location="cpu",weights_only=False)
 ost=[int(v["step"].max().item()) for v in q["optimizer"]["state"].values() if "step" in v]
 if q["step"]!=1000 or not ost or min(ost)!=1000 or max(ost)!=1000:raise RuntimeError("optimizer count mismatch "+fid)
 if has and (state["best_epoch"]<1 or state["stop_step"] is None):raise RuntimeError("early stop replay incomplete "+fid)
 di={}
 evalsteps=set(MILESTONES)|must
 for k in sorted(evalsteps):
  p=d/f"checkpoint_step_{k:04d}.pt"
  if p.exists():
   z=torch.load(p,map_location="cpu",weights_only=False);m.load_state_dict(z["model_state"]);di[str(k)]=eval_ck(m,s,name,c0,k,"fixed_or_preregistered_milestone")
 for nm,label in [("checkpoint_original_best.pt","original_early_stop_best"),("checkpoint_original_stop.pt","original_early_stop_event"),("checkpoint_late_validation_best.pt","post_original_stop_minimum")]:
  p=d/nm
  if p.exists():
   z=torch.load(p,map_location="cpu",weights_only=False);key=f"{label}_step_{z['step']}"
   if key not in di:m.load_state_dict(z["model_state"]);di[key]=eval_ck(m,s,name,c0,z["step"],label)
 rows=list(csv.DictReader(open(cp,"r",newline="",encoding="utf-8")));curve=[(int(r["step"]),float(r["validation_standardized_loss"])) for r in rows if r["validation_standardized_loss"] not in ("",None)]
 early=None
 if has:
  gstep,gval=min([(x,y) for x,y in curve if x>0],key=lambda z:z[1])
  early={"max_epochs":320,"patience":45,"rule":"strict validation standardized loss improvement; original C0/G0 early-stop source","best_checkpoint_step":int(state["best_epoch"]),"best_checkpoint_validation_loss":float(state["best_val"]),"simulated_stop_step":int(state["stop_step"]),"stop_reason":state["stop_reason"],"post_stop_minimum_step":state["late_step"],"post_stop_minimum_validation_loss":None if not np.isfinite(state["late_val"]) else float(state["late_val"]),"post_stop_beats_selected_checkpoint":bool(np.isfinite(state["late_val"]) and state["late_val"]<state["best_val"]),"post_stop_delta_vs_selected":None if not np.isfinite(state["late_val"]) else float(state["late_val"]-state["best_val"]),"global_validation_minimum_step_through_1000":gstep,"global_validation_minimum_through_1000":gval,"validation_curve_points":len(curve)}
 ini=torch.load(d/"checkpoint_step_0000.pt",map_location="cpu",weights_only=False)["model_state"]
 delta2=base2=0.
 for k,v in q["model"].items():delta2+=float(torch.sum((v.float()-ini[k].float())**2));base2+=float(torch.sum(ini[k].float()**2))
 s0={"fit_id":fid,"model":name,"split_id":sid,"seed":0,"train_geometry_ids":s["train_ids"],"validation_geometry_ids":s["validation_ids"],"parameter_count":npar,"optimizer":{"AdamW":{"lr":.002,"weight_decay":.0001},"gradient_clip_norm":5.0,"full_batch":True},"optimizer_updates":1000,"optimizer_state_step_min":min(ost),"optimizer_state_step_max":max(ost),"all_parameter_tensors_received_grad":len(state["grad_counts"])==1 and state["grad_counts"][0]==len(list(m.parameters())),"gradient_parameter_tensor_counts_seen":state["grad_counts"],"relative_parameter_l2_change_from_initial":float(math.sqrt(delta2)/max(math.sqrt(base2),1e-30)),"original_early_stop_replay":early,"pca_oracle_validation_floor":s["pca_oracle_validation_floor"],"pca_oracle_train_floor":s["pca_oracle_train_floor"],"constant_baselines":baselines(s,c0),"diagnostics_by_step":di,"trajectory_csv":str(cp.relative_to(ROOT)),"resume_checkpoint":str(rp.relative_to(ROOT)),"routing_h2":{"status":"NOT_AVAILABLE_NO_LEGAL_NESTED_PSCALE"}}
 atomic_json(d/"milestone_metrics.json",di);atomic_json(d/"fit_summary.json",s0)
 reg["fits"][fid]["status"]="COMPLETE";reg["fits"][fid]["updates_committed"]=1000;reg["fits"][fid]["fit_invocations"]=max(1,reg["fits"][fid]["fit_invocations"]);reg["fits"][fid]["early_best_epoch"]=None if early is None else early["best_checkpoint_step"];reg["fits"][fid]["simulated_stop_step"]=None if early is None else early["simulated_stop_step"];reg["fits"][fid]["optimizer_state_steps"]=[1000]
 reg["optimizer_updates_committed"]=sum(v["updates_committed"] for v in reg["fits"].values());reg["active_fit"]=fid;reg["active_step"]=1000;atomic_json(regpath,reg)
 print("FIT_COMPLETE",fid,"1000 updates","train",rows[-1]["train_standardized_loss"],"val",rows[-1]["validation_standardized_loss"],flush=True)
 return s0
def final_summary(ss,reg,fold,proto,prep):
 fs={s["fit_id"]:s for s in ss};inner={}
 for i in range(1,4):
  c=fs[f"C0_inner{i}_seed0"];g=fs[f"G0_inner{i}_seed0"]
  cv=c["diagnostics_by_step"]["1000"]["validation"]["state_metrics"]["summary"]["state_relative_l2"]["median"];gv=g["diagnostics_by_step"]["1000"]["validation"]["state_metrics"]["summary"]["state_relative_l2"]["median"]
  inner[str(i)]={"validation_geometry_ids":c["validation_geometry_ids"],"C0_best_epoch":c["original_early_stop_replay"]["best_checkpoint_step"],"G0_best_epoch":g["original_early_stop_replay"]["best_checkpoint_step"],"C0_stop_step":c["original_early_stop_replay"]["simulated_stop_step"],"G0_stop_step":g["original_early_stop_replay"]["simulated_stop_step"],"C0_late_beats_selected":c["original_early_stop_replay"]["post_stop_beats_selected_checkpoint"],"G0_late_beats_selected":g["original_early_stop_replay"]["post_stop_beats_selected_checkpoint"],"C0_validation_state_median_at_1000":cv,"G0_validation_state_median_at_1000":gv,"G0_minus_C0_state_median_at_1000":gv-cv}
 outer={}
 for model in ["C0","G0"]:
  s=fs[f"{model}_outer31_seed0"];epoch=reg["fits"][f"{model}_outer31_seed0"]["outer_refit_epoch"]
  rows=list(csv.DictReader(open(ROOT/s["trajectory_csv"],"r",newline="",encoding="utf-8")))
  by={int(r["step"]):r for r in rows}
  outer[model]={"train_geometry_count":31,"inner_median_refit_epoch":epoch,"zero_baseline_train_standardized_loss":s["constant_baselines"]["zero"]["train_standardized_loss"],"train_mean_baseline_standardized_loss":s["constant_baselines"]["train_mean"]["train_standardized_loss"],"train_loss_at_1000":float(by[1000]["train_standardized_loss"]),"train_loss_at_inner_median_epoch":float(by[epoch]["train_standardized_loss"]),"train_state_median_at_1000":s["diagnostics_by_step"]["1000"]["train"]["state_metrics"]["summary"]["state_relative_l2"]["median"]}
 return {"task":"COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1","status":"COMPLETE_DEVELOPMENT_AUDIT","classification":"one official outer fold and seed 0; not full LOGO, H1 validation, or production admission","zero_solver":True,"zero_new_hf":True,"zero_reserve":True,"zero_inverse":True,"new_model_fits":8,"optimizer_updates":reg["optimizer_updates_committed"],"fold_number":fold["outer_fold_number"],"excluded_outer_holdout_id":fold["excluded_outer_holdout_geometry_id"],"outer_train_count":31,"inner_fold_results":inner,"outer_train_results":outer,"inner_pca_floors":{k:prep[k]["pca_oracle_validation_floor"] for k in ["inner1","inner2","inner3"]},"fit_summaries":fs,"routing_h2":{"status":"NOT_AVAILABLE_NO_LEGAL_NESTED_PSCALE","reason":"No same-outer-fold, inner-train-fitted frozen P_scale artifact exists. Outer OOF P_scale includes these validation geometries in its fit; no P_scale prediction, truth, or oracle was opened."},"selection_limit":"Late minima are diagnostic; no checkpoint is selected for generalization or H1 claims."}
def write_report(s):
 l=["# COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1","","Status: complete one-fold, seed-0 development diagnostic. The outer-held-out truth and prediction were not opened or scored.","",f"- Exact new fits: {s['new_model_fits']}; optimizer updates: {s['optimizer_updates']}.",f"- Fold {s['fold_number']}; outer-train geometries: 31; inner geometry folds: 3.",f"- Excluded holdout ID: {s['excluded_outer_holdout_id']}.","- Solver, new HF, reserve, inverse search and P_scale fit: zero.","","## 31-geometry train-only fits","","| Model | zero baseline loss | train-mean loss | loss at step 1000 | state median at step 1000 | inner-median refit epoch |","|---|---:|---:|---:|---:|---:|"]
 for m in ["C0","G0"]:
  x=s["outer_train_results"][m];l.append(f"| {m} | {x['zero_baseline_train_standardized_loss']:.6g} | {x['train_mean_baseline_standardized_loss']:.6g} | {x['train_loss_at_1000']:.6g} | {x['train_state_median_at_1000']:.6g} | {x['inner_median_refit_epoch']} |")
 l+=["","These train-only values measure fit to the 31 training geometries; they do not estimate outer-held-out generalization.","","## Inner validation and early-stop replay","","| Fold | model | best step | original stop | post-stop minimum | late minimum better? | validation state median at 1000 |","|---:|---|---:|---:|---:|---|---:|"]
 for i in range(1,4):
  for m in ["C0","G0"]:
   z=s["fit_summaries"][f"{m}_inner{i}_seed0"];e=z["original_early_stop_replay"];v=z["diagnostics_by_step"]["1000"]["validation"]["state_metrics"]["summary"]["state_relative_l2"]["median"]
   l.append(f"| {i} | {m} | {e['best_checkpoint_step']} | {e['simulated_stop_step']} ({e['stop_reason']}) | {e['post_stop_minimum_step']} | {e['post_stop_beats_selected_checkpoint']} | {v:.6g} |")
 l+=["","The frozen early-stop rule is replayed over the full 1000-step trajectory: strict validation-loss improvement, maximum 320 updates, patience 45. Later checkpoints are reported as diagnostics and do not enter outer-test selection.","","## Trajectory, state metrics and PCA floors","","Every update records train and validation standardized loss, raw latent MSE, latent variance ratios, gradient norm and parameter update norm in each fit_logs directory. Fixed and replay checkpoints also include state, amplitude and truth-weighted phase metrics. Phase uses truth amplitude-squared weights; predicted phase below the frozen 1e-8 unit-phase threshold is undefined and its truth-power share is reported.","","Each inner fold fits its own input scaler and seven order-local rank-2 PCA bases using inner-train geometries only. The validation PCA floor is the oracle projection/reconstruction of validation C_hat through that train-fitted basis; it is separate from geometry-to-latent prediction error. See summary.json.","","## Routing and interpretation","","No lawful nested P_scale prediction was available for inner validation, so routing/H2 is NOT_AVAILABLE. Existing outer OOF P_scale was not read because it would include inner-validation geometries in its fit; no oracle scale was used.","","This is a development diagnosis for one outer fold and one seed. It cannot establish full LOGO performance, H1 attainment, physical accuracy or production admission.","","Recovery: read CONTINUATION.md, then protocol.json, fit_registry.json and current_progress.json. Completed fits are not rerun."]
 (OUT/"COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1.md").write_text("\n".join(l)+"\n",encoding="utf-8")
def main():
 pp=OUT/"protocol.json";regp=OUT/"fit_registry.json";protocol=jr(pp);reg=jr(regp);psha=sha(pp)
 if reg["protocol_sha256"]!=psha:raise RuntimeError("protocol lock mismatch")
 if git("branch","--show-current")!=protocol["branch"] or git("rev-parse","HEAD")!=protocol["start_head"]:raise RuntimeError("branch/head changed after preregistration")
 stat=other_status()
 if len(stat)!=protocol["preexisting_worktree_status"]["count"] or hashlib.sha256("\n".join(stat).encode()).hexdigest()!=protocol["preexisting_worktree_status"]["sha256"]:raise RuntimeError("preexisting worktree status changed")
 if torch.cuda.is_available():raise RuntimeError("CUDA visible; frozen protocol requires CPU")
 for rel,h in protocol["source_sha256"].items():
  if sha(ROOT/rel)!=h:raise RuntimeError("source hash changed "+rel)
 amendp=OUT/"protocol_amendment_01.json"
 if amendp.exists():
  amend=jr(amendp)
  if sha(amendp)!=reg.get("protocol_amendment_sha256") or amend.get("base_protocol_sha256")!=psha or amend.get("runner_sha256_after")!=reg.get("runner_sha256"):raise RuntimeError("protocol amendment lock mismatch")
  effective_runner=reg["runner_sha256"]
 else:effective_runner=protocol["runner_sha256"]
 if sha(OUT/"trajectory_runner.py")!=effective_runner:raise RuntimeError("runner hash mismatch")
 fold=jr(OUT/"fold_manifest.json");im=jr(OUT/"input_manifest.json")
 if sha(OUT/"fold_manifest.json")!=protocol["fold_manifest_sha256"] or sha(OUT/"input_manifest.json")!=protocol["input_manifest_sha256"]:raise RuntimeError("fold/input manifest changed")
 c0=modload("frozen_c0_trajectory",C0_PATH);g0=modload("frozen_g0_trajectory",G0_PATH)
 if g0.parameter_budget(4)["total"]!=2444:raise RuntimeError("G0 parameter count mismatch")
 g0.preflight()
 for name in ["C0","G0"]:
  random.seed(0);np.random.seed(0);torch.manual_seed(0);m,n=new_model(name,c0,g0)
  xin=torch.zeros((3,6),dtype=torch.float32);x=xin if name=="C0" else torch.as_tensor(g0.node_features(xin.numpy()),dtype=torch.float32)
  y=m(x)
  if y.shape!=(3,14) or not torch.isfinite(y).all():raise RuntimeError("preflight shape failure")
  y.sum().backward()
  if any(p.grad is None for p in m.parameters()):raise RuntimeError("preflight gradient path failure")
 data=load_data(fold,im)
 if data["c"].shape!=(31,21,7,2):raise RuntimeError("training labels shape mismatch")
 splits,prep=make_splits(data,fold,c0,g0)
 atomic_json(OUT/"pretraining_checks.json",{"status":"PASS","optimizer_steps":0,"new_fits_started":0,"outer_holdout_truth_opened":False,"outer_holdout_prediction_opened":False,"training_state_files_opened":31,"training_ids":data["ids"],"cuda_visible":False,"torch_version":torch.__version__,"numpy_version":np.__version__,"sklearn_version":__import__("sklearn").__version__,"C0_parameters":2684,"G0_parameters":2444,"output_shape":[3,14],"all_parameter_tensors_have_gradient_path":True,"split_preprocessing":list(splits),"P_scale_fields_read":False,"aggregate_dataset_truth_npz_read":False,"aggregate_oof_predictions_npz_read":False})
 if os.environ.get("COUPLING_TRAJECTORY_PREFLIGHT_ONLY")=="1":
  print("PREFLIGHT_ONLY_PASS",json.dumps({"optimizer_steps":0,"new_fits_started":0,"splits":list(splits)},separators=(",",":")),flush=True);return
 fitplan=reg["fit_plan"]
 if len(fitplan)!=8 or reg["optimizer_updates_committed"]>8000:raise RuntimeError("fit budget invalid")
 summaries=[]
 for fit in fitplan:
  if fit["split_id"]=="outer31":
   epochs=[reg["fits"][f"{fit['model']}_inner{i}_seed0"].get("early_best_epoch") for i in range(1,4)]
   if any(x is None for x in epochs):raise RuntimeError("outer refit requested before inner fits complete")
   ep=int(np.median(np.asarray(epochs,float)))
   fit["outer_refit_epoch"]=ep;reg["fits"][fit["fit_id"]]["outer_refit_epoch"]=ep;atomic_json(regp,reg)
  summaries.append(runfit(fit,splits[fit["split_id"]],c0,g0,psha,regp,reg))
  reg=jr(regp)
 if len(summaries)!=8 or reg["optimizer_updates_committed"]!=8000 or any(v["status"]!="COMPLETE" for v in reg["fits"].values()):raise RuntimeError("fit total/status mismatch")
 result=final_summary(summaries,reg,fold,protocol,prep);atomic_json(OUT/"summary.json",result);write_report(result)
 reg["phase"]="TRAJECTORIES_COMPLETE";reg["active_fit"]=None;reg["active_step"]=None;atomic_json(regp,reg)
 atomic_json(OUT/"current_progress.json",{"phase":"TRAJECTORIES_COMPLETE","completed_fits":8,"committed_optimizer_updates":8000,"authorized_max_updates":8000,"zero_solver":True,"zero_p_scale_fit":True})
 print("TRAJECTORY_AUDIT_COMPLETE",json.dumps({"fits":8,"updates":8000,"inner":result["inner_fold_results"],"outer":result["outer_train_results"]},separators=(",",":")),flush=True)
if __name__=="__main__":main()
