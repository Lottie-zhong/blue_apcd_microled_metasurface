import os,sys,json,hashlib,subprocess,importlib.util,statistics,datetime
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
os.environ["OMP_NUM_THREADS"]="1"
os.environ["MKL_NUM_THREADS"]="1"
os.environ["OPENBLAS_NUM_THREADS"]="1"
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
torch.set_num_threads(1)
assert not torch.cuda.is_available()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(path,obj):
 p=Path(path); t=Path(str(p)+".tmp");t.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");os.replace(t,p)
def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,str(path));mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def git(*args):
 return subprocess.run(["git","-C",str(ROOT),*args],capture_output=True,text=True,check=True).stdout.strip()
def status_base():
 raw=subprocess.run(["git","-C",str(ROOT),"status","--porcelain=v1","-z","--untracked-files=all"],capture_output=True,check=True).stdout
 prefix=("reports/coupling/"+NAME+"/").encode()
 entries=sorted(e for e in raw.split(b"\0") if e and not e[3:].replace(b"\\",b"/").startswith(prefix))
 return {"count":len(entries),"sha256":hashlib.sha256(b"\0".join(entries)).hexdigest()}
def summarize(vals):
 a=np.asarray(vals,float);return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"worst":float(np.max(a)),"min":float(np.min(a)),"mean":float(np.mean(a))}
def mse(y,p,sd): return float(np.mean(((p-y)/sd)**2))
def state_vals(hyb,c,pred):
 return [float(hyb.state_detail(c[i],pred[i])["state"]) for i in range(len(c))]
def state_summary(hyb,c,pred):
 return summarize(state_vals(hyb,c,pred))
def latent_diag(y,p,sd):
 var_y=np.var(y,axis=0);var_p=np.var(p,axis=0)
 ratio=var_p/np.maximum(var_y,1e-30)
 corr=[]
 for j in range(y.shape[1]):
  if np.std(y[:,j])<=1e-15 or np.std(p[:,j])<=1e-15: corr.append(None)
  else: corr.append(float(np.corrcoef(y[:,j],p[:,j])[0,1]))
 finite=np.asarray([x for x in corr if x is not None],float)
 return {"raw_latent_mse":float(np.mean((p-y)**2)),"original_standardized_loss":mse(y,p,sd),
  "target_variance_mean":float(np.mean(var_y)),"prediction_variance_mean":float(np.mean(var_p)),
  "prediction_to_target_variance_ratio_by_coordinate":ratio.tolist(),
  "prediction_to_target_variance_ratio_summary":summarize(ratio),
  "prediction_target_correlation_by_coordinate":corr,
  "prediction_target_correlation_summary":summarize(finite) if finite.size else None,
  "correlated_coordinate_count":int(finite.size)}
def assign_flat(model,flat):
 pos=0
 with torch.no_grad():
  for p in model.parameters():
   n=p.numel();p.copy_(torch.as_tensor(flat[pos:pos+n].reshape(tuple(p.shape)),dtype=p.dtype));pos+=n
 assert pos==len(flat)
def flatten(model):
 return np.concatenate([p.detach().cpu().numpy().reshape(-1) for p in model.parameters()]).astype(np.float32)
assert git("branch","--show-current")=="work/mdc-np-coupling-ml-v1"
assert git("rev-parse","HEAD")=="f0f47023af9c306590414232155c0d539c3dfa4d"
protocol=json.loads((OUT/"protocol.json").read_text(encoding="utf-8-sig"))
assert protocol["status"]=="FROZEN_BEFORE_BASELINE_COMPARISON_AND_DIAGNOSTIC_FITS"
assert status_base()==protocol["preexisting_worktree_status_excluding_this_task"]
ckpt=json.loads((OUT/"checkpoint.json").read_text())
ckpt.update({"phase":"BASELINE_AUDIT_RUNNING","new_fit_count":0,"optimizer_steps":0,"zero_solver":True})
atomic(OUT/"checkpoint.json",ckpt)
poc=loadmod("audit_poc",PCOP);hyb=loadmod("audit_h1h2",HYBP);M=poc.import_model();gm=loadmod("audit_g0_model",GMP)
ctx=poc.load_context()
ids=ctx["ids"];idx={g:i for i,g in enumerate(ids)};folds=ctx["folds"]
gp=np.load(G0/"g0_predictions_partial.npz",allow_pickle=False)
params=np.asarray(gp["final_parameters"],np.float32)
g0progress=json.loads((G0/"seed_progress.json").read_text(encoding="utf-8-sig"))
c0progress=json.loads((C0/"seed_progress.json").read_text(encoding="utf-8-sig"))
assert params.shape==(3,32,2444) and len(g0progress["final_completed"])==96
rows=[];state_rows=[];parameter_rel=[];checkpoint_loss=[];init_losses=[];loss_drop=[];variance_medians=[];corr_medians=[]
saved_trainloss_parity=[];saved_stat_parity=[]
outer_mean_const=[];outer_zero_const=[]
for fi,fold in enumerate(folds):
 train_ids=list(fold["train_geometry_ids"]);outer=[idx[g] for g in train_ids]
 local_c=np.asarray(ctx["c"][outer],complex);local_geo=np.asarray(ctx["geometry"][outer],float)
 pcs,Y=poc.build_c0_basis(M,local_c,list(range(len(outer))))
 xf=M.Xform().fit(local_geo);X=xf.transform(local_geo)
 assert Y.shape==(31,14) and np.isfinite(Y).all()
 sd=np.maximum(np.std(Y,axis=0),1e-12)
 zero=np.zeros_like(Y);mean=np.broadcast_to(np.mean(Y,axis=0),Y.shape).copy()
 zero_diag=latent_diag(Y,zero,sd);mean_diag=latent_diag(Y,mean,sd)
 zero_state=state_summary(hyb,local_c,poc.c0_decode(M,zero,pcs))
 mean_state=state_summary(hyb,local_c,poc.c0_decode(M,mean,pcs))
 outer_zero_const.append({"outer_fold":fi,"heldout_geometry_id":fold["test_geometry_id"],"train_geometry_count":len(outer),**zero_diag,"state":zero_state})
 outer_mean_const.append({"outer_fold":fi,"heldout_geometry_id":fold["test_geometry_id"],"train_geometry_count":len(outer),**mean_diag,"state":mean_state})
 xin=torch.as_tensor(gm.node_features(X),dtype=torch.float32)
 for si,seed in enumerate((0,1,2)):
  rec=g0progress["final_completed"][f"{fi}|{seed}"]
  torch.manual_seed(seed);model=gm.OrderedPeriodicG0().cpu();initial=flatten(model)
  init_out=model(xin).detach().cpu().numpy().astype(float)
  init_diag=latent_diag(Y,init_out,sd);assign_flat(model,params[si,fi]);model.eval()
  with torch.no_grad(): pred=model(xin).cpu().numpy().astype(float)
  diag=latent_diag(Y,pred,sd);state=state_summary(hyb,local_c,poc.c0_decode(M,pred,pcs))
  rel=float(np.linalg.norm(params[si,fi]-initial)/max(np.linalg.norm(initial),1e-30))
  row={"outer_fold":fi,"heldout_geometry_id":fold["test_geometry_id"],"seed":seed,
   "zero_loss":zero_diag["original_standardized_loss"],"train_mean_loss":mean_diag["original_standardized_loss"],
   "initial_loss":init_diag["original_standardized_loss"],"saved_checkpoint":diag,"saved_checkpoint_state":state,
   "zero_state":zero_state,"train_mean_state":mean_state,"parameter_relative_l2_change_from_init":rel,
   "saved_progress_train_latent_mse":float(rec["train_latent_mse"]),
   "selected_epochs":int(rec["selected_epochs"]),"checkpoint_parameters_finite":bool(np.isfinite(params[si,fi]).all())}
  rows.append(row);state_rows.extend(state_vals(hyb,local_c,poc.c0_decode(M,pred,pcs)))
  parameter_rel.append(rel);checkpoint_loss.append(diag["original_standardized_loss"]);init_losses.append(init_diag["original_standardized_loss"])
  loss_drop.append(init_diag["original_standardized_loss"]-diag["original_standardized_loss"])
  variance_medians.append(diag["prediction_to_target_variance_ratio_summary"]["median"])
  corr_medians.append(diag["prediction_target_correlation_summary"]["median"] if diag["prediction_target_correlation_summary"] else float("nan"))
  saved_trainloss_parity.append(abs(diag["original_standardized_loss"]-float(rec["train_latent_mse"])))
  all_indices=outer
  savedstate=np.asarray(gp["train_state"][si,fi,all_indices],float)
  recomputed=np.asarray(state_vals(hyb,local_c,poc.c0_decode(M,pred,pcs)),float)
  saved_stat_parity.append(float(np.max(np.abs(savedstate-recomputed))))
# Existing C0 split and selected-epoch provenance: no checkpoint tensors or train losses in its NPZ.
completed=c0progress["completed"]
c0rows=[v for k,v in completed.items() if k.startswith("C0|")]
c0selected=[int(r["selected_epochs"]) for r in c0rows]
c0inner=[int(q["best_epoch"]) for r in c0rows for q in r["inner_folds"]]
g0final=list(g0progress["final_completed"].values());g0inner=list(g0progress["inner_completed"].values())
g0selected=[int(r["selected_epochs"]) for r in g0final]
g0best=[int(r["best_epoch"]) for r in g0inner];g0executed=[int(r["epochs_executed"]) for r in g0inner]
c0audit={
 "completed_seed_fits":len(c0rows),"inner_best_epoch_count":len(c0inner),
 "selected_outer_refit_epoch_distribution":summarize(c0selected),
 "selected_outer_refit_le_10":int(np.sum(np.asarray(c0selected)<=10)),
 "selected_outer_refit_le_20":int(np.sum(np.asarray(c0selected)<=20)),
 "inner_best_epoch_distribution":summarize(c0inner),
 "sum_known_outer_refit_optimizer_updates":int(np.sum(c0selected)),
 "inner_epochs_executed_available":False,"inner_best_validation_losses_available":False,
 "saved_model_parameters_available":False,"saved_final_train_latent_predictions_available":False,
 "train_loss_curves_available":False,"parameter_delta_from_initialization_available":False,
 "reason":"seed_progress stores each C0 selected epoch and three inner best epochs, but not inner executed epochs, validation losses, fitted parameter vectors, or train predictions; predictions_partial.npz contains only complex OOF C0/C1 arrays.",
 "resume_or_recompute":False}
g0audit={
 "final_fits":len(g0final),"inner_fits":len(g0inner),
 "selected_outer_refit_epoch_distribution":summarize(g0selected),
 "outer_refit_le_10":int(np.sum(np.asarray(g0selected)<=10)),
 "outer_refit_le_20":int(np.sum(np.asarray(g0selected)<=20)),
 "inner_best_epoch_distribution":summarize(g0best),
 "inner_epochs_executed_distribution":summarize(g0executed),
 "inner_best_epoch_le_10":int(np.sum(np.asarray(g0best)<=10)),
 "inner_best_epoch_le_20":int(np.sum(np.asarray(g0best)<=20)),
 "sum_inner_and_outer_steps":int(np.sum(g0executed)+np.sum(g0selected)),
 "recorded_actual_optimizer_steps":int(json.loads((G0/"checkpoint.json").read_text())["actual_optimizer_steps"]),
 "outer_refit_steps_exactly_match_selected_epoch_count":int(json.loads((G0/"checkpoint.json").read_text())["actual_optimizer_steps"])-int(np.sum(g0executed))==int(np.sum(g0selected)),
 "checkpoint_parameter_vector_count":int(params.size),"per_fit_parameters":2444,
 "saved_final_train_loss_present":True,"saved_optimizer_moments_present":False,
 "saved_training_curves_present":False}
source={
 "status":"PASS_STATIC_AND_CHECKPOINT_STRUCTURE_AUDIT",
 "target":"one rank-2 Cartesian PCA fit independently for each of seven orders; order slots [-3..3], two scores/order; scores are not whitened or standardized by PCA.",
 "input_scaler":"M5 Xform StandardScaler.fit(geometry/130); scaler fitted on outer train in frozen runners; G0 adds fixed physical positions divided by 1740 nm and keeps six positions ordered.",
 "actual_loss":"mean(((prediction-target)/maximum(std(target, axis=0),1e-12))**2); scale divides only, no target-mean subtraction; weight decay is optimizer-only, not included in reported loss.",
 "C0_source_evidence":{"model":"pw_k6_stage1_32g_frozen_model_v1.py:20-28","loss":"pw_k6_stage1_32g_frozen_model_v1.py:36","inner_fit":"pw_k6_stage1_32g_frozen_model_v1.py:57-70","outer_refit":"pw_k6_stage1_32g_frozen_model_v1.py:72-80","pca":"coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py:237-245","train_fold_and_epoch_conversion":"coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py:264-297"},
 "G0_source_evidence":{"model":"COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1/g0_ordered_periodic_model.py:31-68","loss":"g0_run.py:119-121","inner_fit":"g0_run.py:122-138","outer_refit_and_checkpoint_output":"g0_run.py:140-152","basis_and_selected_epoch_conversion":"g0_run.py:173-204"},
 "optimizer_audit":{"both":"AdamW(model.parameters(), lr=0.002, weight_decay=0.0001); all model parameters are passed through parameters(); loss.backward(); clip_grad_norm_(...,5.0); optimizer.step(); training loss measured before update in each loop body; validation evaluated after update in eval/no_grad mode.","validation":"inner validation is model.eval plus no_grad; final refit is model.train each step then final outputs/loss measured after the last update in eval/no_grad.","detach_audit":"No detach/no_grad is present between model forward and training loss/backward in the fit functions; no known broken gradient path from source."},
 "selection_audit":{"inner_best_epoch":"validation standardized latent MSE is computed after each optimizer update","outer_refit":"reset deterministic initialization, then train on all outer-train rows for integer median of the three inner best epochs","G0_refit_train_loss":"computed after the final update from the final checkpoint outputs","C0_refit_train_loss":"not saved by the frozen run"},
 "G0_checkpoint_load_audit":{"format":"flattened float32 final_parameters array stored by direct model.parameters() iteration order; no optimizer state/checkpoint history saved","reconstructed_saved_parameter_train_loss_max_abs_delta":max(saved_trainloss_parity),
  "reconstructed_saved_train_state_max_abs_delta":max(saved_stat_parity),
  "parameter_relative_l2_change_summary":summarize(parameter_rel),
  "initial_train_loss_summary":summarize(init_losses),"saved_train_loss_summary":summarize(checkpoint_loss),
  "training_loss_drop_summary":summarize(loss_drop),"all_saved_parameters_finite":bool(np.isfinite(params).all())},
 "C0_available_training_audit":c0audit,"G0_early_stop_audit":g0audit,
 "limits":["Prior fold-local PCA/scaler objects were not serialized; this audit reconstructs the deterministic same fit using only the matching outer-train rows and checks saved variance-ratio metadata.","No C0 parameter tensor, optimizer state, outer final train loss, or epoch curves are stored, so those quantities cannot be recovered without a prohibited C0 LOGO refit.","Static source checks show implementation wiring, but do not prove generalization or physical fidelity."]}
baseline={
 "definition":{"outer_train_constant_zero":"predict latent score 0, evaluate exact source loss with sd=std(Y_outer,axis=0); PCA score mean is not subtracted by lossfn","outer_train_mean":"predict per-score mean(Y_outer) evaluated with same sd","state":"inverse transform with matching outer-train PCA then frozen H1 state relative RMSE on each outer-train geometry only"},
 "G0_saved_checkpoint":{"outer_fold_seed_pairs":len(rows),"original_loss_summary":summarize(checkpoint_loss),
  "constant_zero_loss_summary":summarize([x["zero_loss"] for x in rows]),
  "train_mean_constant_loss_summary":summarize([x["train_mean_loss"] for x in rows]),
  "loss_ratio_vs_train_mean_summary":summarize([x["saved_checkpoint"]["original_standardized_loss"]/max(x["train_mean_loss"],1e-30) for x in rows]),
  "initial_loss_summary":summarize(init_losses),"loss_drop_from_initial_summary":summarize(loss_drop),
  "output_to_target_variance_median_per_pair_summary":summarize(variance_medians),
  "per_dimension_prediction_target_correlation_median_summary":summarize([x for x in corr_medians if np.isfinite(x)]),
  "checkpoint_state_train_geometry_summary":summarize(state_rows),
  "max_abs_parity_vs_saved_progress_train_loss":max(saved_trainloss_parity),
  "max_abs_parity_vs_saved_progress_train_state":max(saved_stat_parity),
  "by_outer_fold_seed":rows},
 "outer_train_constant_baseline_by_fold":{"zero":outer_zero_const,"train_mean":outer_mean_const},
 "constant_zero_loss_across_folds":summarize([x["original_standardized_loss"] for x in outer_zero_const]),
 "train_mean_loss_across_folds":summarize([x["original_standardized_loss"] for x in outer_mean_const]),
 "state_constant_zero_across_folds":summarize([x["state"]["median"] for x in outer_zero_const]),
 "state_train_mean_across_folds":summarize([x["state"]["median"] for x in outer_mean_const]),
 "metric_unit":"descriptive across 96 dependent fold-seed checkpoints or 32 paired folds; not independent statistical replicates",
 "folds_use_heldout_truth":False}
atomic(OUT/"constant_baselines.json",baseline)
atomic(OUT/"source_audit.json",source)
ckpt.update({"phase":"BASELINES_COMPLETE","new_fit_count":0,"optimizer_steps":0,"saved_g0_checkpoint_pairs_audited":len(rows),"zero_solver":True})
atomic(OUT/"checkpoint.json",ckpt)
print(json.dumps({"source_audit":source,"baselines_summary":{k:v for k,v in baseline["G0_saved_checkpoint"].items() if k!="by_outer_fold_seed"},"constant_zero_fold_loss":baseline["constant_zero_loss_across_folds"],"train_mean_fold_loss":baseline["train_mean_loss_across_folds"],"c0_selected_epochs":c0audit["selected_outer_refit_epoch_distribution"],"g0_selected_epochs":g0audit["selected_outer_refit_epoch_distribution"],"g0_inner_epochs":g0audit["inner_best_epoch_distribution"],"g0_steps":g0audit["sum_inner_and_outer_steps"]},indent=2))
