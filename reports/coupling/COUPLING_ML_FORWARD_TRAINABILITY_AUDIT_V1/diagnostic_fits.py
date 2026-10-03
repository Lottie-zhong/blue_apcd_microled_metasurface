import os,sys,json,hashlib,subprocess,importlib.util,random,datetime,io
os.environ["CUDA_VISIBLE_DEVICES"]="-1";os.environ["OMP_NUM_THREADS"]="1";os.environ["MKL_NUM_THREADS"]="1";os.environ["OPENBLAS_NUM_THREADS"]="1"
from pathlib import Path
import numpy as np
import torch
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
NAME="COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1"
OUT=ROOT/"reports"/"coupling"/NAME
G0=ROOT/"reports"/"coupling"/"COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1"
C0=ROOT/"reports"/"coupling"/"COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1"
PCOP=ROOT/"scripts"/"coupling_ml"/"coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py"
HYBP=ROOT/"scripts"/"coupling_ml"/"coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py"
GMP=G0/"g0_ordered_periodic_model.py"
SNAPS=[0,10,50,100,300,750,1500]
torch.set_num_threads(1)
assert torch.empty(0).device.type=="cpu" and not torch.cuda.is_available()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_bytes(path,data):
 p=Path(path);tmp=Path(str(p)+".tmp")
 with open(tmp,"wb") as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def atomic_json(path,obj):
 atomic_bytes(path,(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n").encode("utf-8"))
def atomic_torch(path,obj):
 p=Path(path);tmp=Path(str(p)+".tmp")
 torch.save(obj,tmp)
 os.replace(tmp,p)
def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,str(path));mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def git(*args):return subprocess.run(["git","-C",str(ROOT),*args],capture_output=True,text=True,check=True).stdout.strip()
def status_base():
 raw=subprocess.run(["git","-C",str(ROOT),"status","--porcelain=v1","-z","--untracked-files=all"],capture_output=True,check=True).stdout
 prefix=("reports/coupling/"+NAME+"/").encode()
 entries=sorted(e for e in raw.split(b"\0") if e and not e[3:].replace(b"\\",b"/").startswith(prefix))
 return {"count":len(entries),"sha256":hashlib.sha256(b"\0".join(entries)).hexdigest()}
def atomic_npz(path,**arrays):
 p=Path(path);tmp=Path(str(p)+".tmp.npz");np.savez_compressed(tmp,**arrays);os.replace(tmp,p)
def flat(model):return np.concatenate([p.detach().cpu().numpy().reshape(-1) for p in model.parameters()]).astype(np.float32)
def clone_state(model):return {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
def param_count(model):return sum(p.numel() for p in model.parameters())
def summarize(v):
 a=np.asarray(v,float)
 return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"worst":float(np.max(a)),"min":float(np.min(a)),"mean":float(np.mean(a))}
def lossfn(pred,y,sd):return torch.mean(((pred-y)/sd)**2)
def latent_metrics(y,p,sd):
 yt=y.detach().cpu().numpy().astype(float);yp=p.detach().cpu().numpy().astype(float)
 vy=np.var(yt,axis=0);vp=np.var(yp,axis=0);rat=vp/np.maximum(vy,1e-30);corr=[]
 for j in range(yt.shape[1]):
  corr.append(None if np.std(yt[:,j])<=1e-15 or np.std(yp[:,j])<=1e-15 else float(np.corrcoef(yt[:,j],yp[:,j])[0,1]))
 cf=np.asarray([x for x in corr if x is not None],float)
 return {"raw_latent_mse":float(np.mean((yp-yt)**2)),"standardized_latent_mse":float(lossfn(p,y,sd).detach().cpu()),
  "original_loss":float(lossfn(p,y,sd).detach().cpu()),"output_variance_by_coordinate":vp.tolist(),
  "target_variance_by_coordinate":vy.tolist(),"output_to_target_variance_ratio_by_coordinate":rat.tolist(),
  "output_to_target_variance_ratio_summary":summarize(rat),
  "prediction_target_correlation_by_coordinate":corr,
  "prediction_target_correlation_summary":summarize(cf) if cf.size else None}
def state_metrics(hyb,M,poc,yhat,pcs,c4,ids):
 dec=poc.c0_decode(M,yhat,pcs);vals=[]
 for j in range(len(ids)):vals.append(float(hyb.state_detail(c4[j],dec[j])["state"]))
 return {"per_geometry":{ids[j]:vals[j] for j in range(len(ids))},"summary":summarize(vals)}
def save_flat(path,model):
 atomic_npz(path,parameters=flat(model))
def get_step_number(v):
 return int(v.item()) if hasattr(v,"item") else int(v)
def fit_one(label,model_factory,x_np,y_np,sd_np,loss_module,decoder_module,pcs,c4,case_ids,poc,hyb,protocol_hash):
 registry_path=OUT/"fit_registry.json";resume_path=OUT/(label+"_resume.pt");snap_path=OUT/(label+"_snapshots.json")
 registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
 if registry.get(label,{}).get("status")=="COMPLETE":
  return registry[label]["summary"]
 resume=None
 if resume_path.exists():
  resume=torch.load(resume_path,map_location="cpu",weights_only=True)
  assert resume["fit_id"]==label and resume["protocol_sha256"]==protocol_hash and resume["target_case_ids"]==case_ids
  model=model_factory();model.load_state_dict(resume["model_state"]);model.cpu()
  opt=torch.optim.AdamW(model.parameters(),lr=0.002,weight_decay=0.0001)
  opt.load_state_dict(resume["optimizer_state"])
  start=int(resume["step"]);initial_state=resume["initial_state"];min_state=resume["min_state"]
  min_loss=float(resume["min_loss"]);min_step=int(resume["min_step"])
  histories=resume["histories"];clip_count=int(resume["clip_count"])
  snaps=json.loads(snap_path.read_text()) if snap_path.exists() else []
 else:
   preupdate_retry=label in registry
   assert not preupdate_retry or (registry[label].get("status")=="STARTED" and not resume_path.exists()), "unexpected prior fit state; inspect before continuing"
   random.seed(0);np.random.seed(0);torch.manual_seed(0)
   model=model_factory().cpu();opt=torch.optim.AdamW(model.parameters(),lr=0.002,weight_decay=0.0001)
   start=0;initial_state=clone_state(model);snaps=[];histories={"loss":[ ],"gradient_norm":[ ],"update_norm":[ ]}
   clip_count=0
   if not preupdate_retry:
    registry[label]={"fit_id":label,"status":"STARTED","start_count":1,"seed":0,"steps_planned":1500,"target_case_ids":case_ids,"start_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(registry_path,registry)
    ck=json.loads((OUT/"checkpoint.json").read_text())
    ck["phase"]="FITS_RUNNING";ck["new_fit_count"]=int(ck.get("new_fit_count",0))+1;ck["current_fit"]=label
    atomic_json(OUT/"checkpoint.json",ck)
   else:
    registry[label]["preupdate_reconstruction_count"]=int(registry[label].get("preupdate_reconstruction_count",0))+1
    registry[label]["restart_reason"]="same deterministic initialization reconstructed after pre-update input-shape failure; persisted optimizer step was zero"
    atomic_json(registry_path,registry)
    ck=json.loads((OUT/"checkpoint.json").read_text())
    ck["phase"]="FITS_RUNNING";ck["current_fit"]=label;ck["current_fit_step"]=0
    atomic_json(OUT/"checkpoint.json",ck)
   x=torch.as_tensor(x_np,dtype=torch.float32,device="cpu");y=torch.as_tensor(y_np,dtype=torch.float32,device="cpu");sd=torch.as_tensor(sd_np,dtype=torch.float32,device="cpu")
   assert param_count(model)==(2684 if label=="T0" else 2444)
   model.train()
   with torch.no_grad():initial_loss=float(lossfn(model(x),y,sd).item())
   min_loss=initial_loss;min_step=0;min_state=clone_state(model)
   atomic_json(snap_path,[])
   save_flat(OUT/(label+"_initial_weights.npz"),model)
   resume={"fit_id":label,"protocol_sha256":protocol_hash,"target_case_ids":case_ids,"step":0,"model_state":clone_state(model),"optimizer_state":opt.state_dict(),"initial_state":initial_state,"min_state":min_state,"min_loss":min_loss,"min_step":min_step,"initial_loss":initial_loss,"last_update_norm":None,"last_update_gradient_norm":None,"histories":histories,"clip_count":clip_count,"snapshots":snaps}
   atomic_torch(resume_path,resume)
 if "x" not in locals():
  x=torch.as_tensor(x_np,dtype=torch.float32,device="cpu");y=torch.as_tensor(y_np,dtype=torch.float32,device="cpu");sd=torch.as_tensor(sd_np,dtype=torch.float32,device="cpu")
 assert param_count(model)==(2684 if label=="T0" else 2444)
 model_ids={id(p) for p in model.parameters()};opt_ids={id(p) for g in opt.param_groups for p in g["params"]}
 assert model_ids==opt_ids and len(model_ids)==len(list(model.parameters()))
 def snapshot(step,last_update,last_grad):
  model.train()
  opt.zero_grad(set_to_none=True)
  pred=model(x);ls=lossfn(pred,y,sd);ls.backward()
  grads=[p.grad for p in model.parameters()]
  assert all(g is not None for g in grads)
  assert all(torch.isfinite(g).all() for g in grads)
  gnorm=float(torch.sqrt(sum(torch.sum(g.detach()**2) for g in grads)).item())
  opt.zero_grad(set_to_none=True)
  model.eval()
  with torch.no_grad():pred_eval=model(x);loss=float(lossfn(pred_eval,y,sd).item())
  lm=latent_metrics(y,pred_eval,sd);st=state_metrics(hyb,decoder_module,poc,pred_eval.detach().cpu().numpy(),pcs,c4,case_ids)
  rec={"fit":label,"step":int(step),"loss_semantics":"post-update state; step 0 is initialization","train_loss":loss,
   "gradient_norm_at_snapshot_no_update":gnorm,"last_update_gradient_norm_before_clip":last_grad,
   "last_update_parameter_l2_norm":last_update,"cumulative_parameter_l2_change_from_initial":float(np.linalg.norm(flat(model)-np.concatenate([v.detach().cpu().numpy().reshape(-1) for k,v in initial_state.items() if k in dict(model.named_parameters())]).astype(np.float32))) if label=="T0" else None,
   "train_state_error":st,**lm}
  if label=="T1":
   initial_flat=np.concatenate([initial_state[k].numpy().reshape(-1) for k,_ in model.named_parameters()]).astype(np.float32)
   rec["cumulative_parameter_l2_change_from_initial"]=float(np.linalg.norm(flat(model)-initial_flat))
  return rec
 if start==0 and not snaps:
  rec=snapshot(0,None,None);snaps.append(rec);atomic_json(snap_path,snaps)
 for step in range(start+1,1501):
  model.train();opt.zero_grad(set_to_none=True);pred=model(x);loss=lossfn(pred,y,sd)
  assert torch.isfinite(loss)
  loss.backward()
  grads=[p.grad for p in model.parameters()]
  assert all(g is not None for g in grads) and all(torch.isfinite(g).all() for g in grads)
  raw_gnorm=float(torch.nn.utils.clip_grad_norm_(model.parameters(),5.0).item())
  if raw_gnorm>5.0:clip_count+=1
  before=flat(model).copy();opt.step();after=flat(model)
  update_norm=float(np.linalg.norm(after-before))
  model.eval()
  with torch.no_grad():postloss=float(lossfn(model(x),y,sd).item())
  assert np.isfinite(postloss)
  histories["loss"].append(postloss);histories["gradient_norm"].append(raw_gnorm);histories["update_norm"].append(update_norm)
  if postloss<min_loss:
   min_loss=postloss;min_step=step;min_state=clone_state(model)
  resume={"fit_id":label,"protocol_sha256":protocol_hash,"target_case_ids":case_ids,"step":step,"model_state":clone_state(model),"optimizer_state":opt.state_dict(),"initial_state":initial_state,"min_state":min_state,"min_loss":min_loss,"min_step":min_step,"initial_loss":float(resume["initial_loss"]),"last_update_norm":update_norm,"last_update_gradient_norm":raw_gnorm,"histories":histories,"clip_count":clip_count,"snapshots":snaps}
  atomic_torch(resume_path,resume)
  ck=json.loads((OUT/"checkpoint.json").read_text());ck.update({"phase":"FITS_RUNNING","new_fit_count":int(ck.get("new_fit_count",0)),"optimizer_steps":int(ck.get("optimizer_steps",0))+1,"current_fit":label,"current_fit_step":step});atomic_json(OUT/"checkpoint.json",ck)
  if step in SNAPS:
   rec=snapshot(step,update_norm,raw_gnorm);snaps.append(rec);atomic_json(snap_path,snaps)
   resume["snapshots"]=snaps;atomic_torch(resume_path,resume)
   print(label,"step",step,"loss",f"{rec['train_loss']:.8g}","state_med",f"{rec['train_state_error']['summary']['median']:.8g}","grad",f"{raw_gnorm:.5g}","update",f"{update_norm:.5g}",flush=True)
 model.eval()
 assert int(resume["step"])==1500 and len(histories["loss"])==1500
 steps=[]
 for state in opt.state.values():
  if "step" in state:steps.append(get_step_number(state["step"]))
 assert steps and set(steps)=={1500} and len(steps)==len(list(model.parameters()))
 final_state=clone_state(model)
 atomic_npz(OUT/(label+"_final_weights.npz"),parameters=flat(model))
 atomic_torch(OUT/(label+"_final_checkpoint.pt"),{"fit_id":label,"step":1500,"model_state":final_state,"protocol_sha256":protocol_hash})
 atomic_npz(OUT/(label+"_minloss_weights.npz"),parameters=np.concatenate([min_state[k].numpy().reshape(-1) for k,_ in model.named_parameters()]).astype(np.float32))
 atomic_torch(OUT/(label+"_minloss_checkpoint.pt"),{"fit_id":label,"step":min_step,"model_state":min_state,"protocol_sha256":protocol_hash})
 with torch.no_grad(): final_pred=model(x);final_state_err=state_metrics(hyb,decoder_module,poc,final_pred.cpu().numpy(),pcs,c4,case_ids)
 initial_flat=np.concatenate([initial_state[k].numpy().reshape(-1) for k,_ in model.named_parameters()]).astype(np.float32)
 delta=float(np.linalg.norm(flat(model)-initial_flat)/max(np.linalg.norm(initial_flat),1e-30))
 summary={"status":"COMPLETE","optimizer_steps":1500,"optimizer_state_steps_min":min(steps),"optimizer_state_steps_max":max(steps),
  "parameter_count":param_count(model),"optimizer_parameter_tensor_count":len(opt_ids),"model_parameter_tensor_count":len(model_ids),
  "all_parameter_tensors_received_gradient":True,"gradient_clip_count":clip_count,
  "initial_loss":float(resume["initial_loss"]),"final_train_loss":float(histories["loss"][-1]),"minimum_postupdate_train_loss":float(min_loss),"minimum_loss_step":int(min_step),
  "final_state_error":final_state_err,"relative_parameter_l2_change_from_initial":delta,
  "gradient_norm_over_updates":summarize(histories["gradient_norm"]),"update_norm_over_updates":summarize(histories["update_norm"]),
  "resume_checkpoint":resume_path.name,"final_checkpoint":label+"_final_checkpoint.pt","minloss_checkpoint":label+"_minloss_checkpoint.pt"}
 registry=json.loads(registry_path.read_text());registry[label].update({"status":"COMPLETE","end_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"summary":summary});atomic_json(registry_path,registry)
 ck=json.loads((OUT/"checkpoint.json").read_text());ck.update({"phase":"FIT_COMPLETE","optimizer_steps":int(ck.get("optimizer_steps",0)),"current_fit":None,"current_fit_step":None});atomic_json(OUT/"checkpoint.json",ck)
 return summary
def main():
 assert git("branch","--show-current")=="work/mdc-np-coupling-ml-v1" and git("rev-parse","HEAD")=="f0f47023af9c306590414232155c0d539c3dfa4d"
 protocol=json.loads((OUT/"protocol.json").read_text(encoding="utf-8-sig"));assert protocol["status"].startswith("FROZEN_BEFORE")
 assert status_base()==protocol["preexisting_worktree_status_excluding_this_task"]
 protocol_hash=sha(OUT/"protocol.json")
 poc=loadmod("fit_poc",PCOP);hyb=loadmod("fit_hyb",HYBP);M=poc.import_model();gm=loadmod("fit_g0_model",GMP)
 ctx=poc.load_context();fold=ctx["folds"][0];trainids=fold["train_geometry_ids"];selected=protocol["outer_fold"]["selected_case_ids"]
 assert fold["test_geometry_id"]==protocol["outer_fold"]["test_geometry_id"]
 outer=[ctx["ids"].index(g) for g in trainids];local_c=ctx["c"][outer];local_geo=ctx["geometry"][outer]
 pcs,Y=poc.build_c0_basis(M,local_c,list(range(31)))
 c0p=json.loads((C0/"seed_progress.json").read_text(encoding="utf-8-sig"))["outer_pca"][fold["test_geometry_id"]]
 ratios=np.asarray([p.explained_variance_ratio_ for p in pcs],float)
 assert float(np.max(np.abs(ratios-np.asarray(c0p["c0_order_rank2_explained_variance_ratio"],float))))<1e-12
 xform=M.Xform().fit(local_geo);X=xform.transform(local_geo)
 positions={g:i for i,g in enumerate(trainids)};pick=[positions[g] for g in selected]
 y4=np.asarray(Y[pick],np.float32);x4=np.asarray(X[pick],float);c4=np.asarray(local_c[pick],complex)
 sd=np.maximum(np.std(y4,axis=0),1e-12)
 registry=OUT/"fit_registry.json"
 existing=json.loads(registry.read_text()) if registry.exists() else {}
 assert len(existing)<=2 and all(k in ("T0","T1") for k in existing)
 t0=fit_one("T0",M.Net,x4,y4,sd,M,M,pcs,c4,selected,poc,hyb,protocol_hash)
 t1=fit_one("T1",gm.OrderedPeriodicG0,gm.node_features(x4),y4,sd,gm,M,pcs,c4,selected,poc,hyb,protocol_hash)
 rows=[]
 for label in ("T0","T1"):
  recs=json.loads((OUT/(label+"_snapshots.json")).read_text())
  rows.extend(recs)
 import csv
 fields=["fit","step","train_loss","standardized_latent_mse","raw_latent_mse","gradient_norm_at_snapshot_no_update","last_update_gradient_norm_before_clip","last_update_parameter_l2_norm","cumulative_parameter_l2_change_from_initial","state_median","state_q95","state_worst","prediction_variance_ratio_median","prediction_variance_ratio_q95","prediction_target_corr_median"]
 with open(OUT/"diagnostic_curves.csv","w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:
   w.writerow({"fit":r["fit"],"step":r["step"],"train_loss":r["train_loss"],"standardized_latent_mse":r["standardized_latent_mse"],"raw_latent_mse":r["raw_latent_mse"],"gradient_norm_at_snapshot_no_update":r["gradient_norm_at_snapshot_no_update"],"last_update_gradient_norm_before_clip":r["last_update_gradient_norm_before_clip"],"last_update_parameter_l2_norm":r["last_update_parameter_l2_norm"],"cumulative_parameter_l2_change_from_initial":r["cumulative_parameter_l2_change_from_initial"],"state_median":r["train_state_error"]["summary"]["median"],"state_q95":r["train_state_error"]["summary"]["q95"],"state_worst":r["train_state_error"]["summary"]["worst"],"prediction_variance_ratio_median":r["output_to_target_variance_ratio_summary"]["median"],"prediction_variance_ratio_q95":r["output_to_target_variance_ratio_summary"]["q95"],"prediction_target_corr_median":r["prediction_target_correlation_summary"]["median"]})
 summary={"task":NAME,"fit_count":2,"optimizer_updates_total":3000,"configs":{"T0":t0,"T1":t1},"diagnostic_only":True,"outer_heldout_truth_used":False,"validation_used":False,"zero_solver":True}
 atomic_json(OUT/"fit_summary.json",summary)
 ck=json.loads((OUT/"checkpoint.json").read_text());ck.update({"phase":"FITS_COMPLETE","new_fit_count":2,"optimizer_steps":3000,"current_fit":None,"current_fit_step":None,"fit_status":{"T0":"COMPLETE","T1":"COMPLETE"},"zero_solver":True,"zero_full_logo":True,"resume":"diagnostic fits complete; read fit_summary.json and continuation"})
 atomic_json(OUT/"checkpoint.json",ck)
 print(json.dumps(summary,indent=2))
if __name__=="__main__":
 main()
