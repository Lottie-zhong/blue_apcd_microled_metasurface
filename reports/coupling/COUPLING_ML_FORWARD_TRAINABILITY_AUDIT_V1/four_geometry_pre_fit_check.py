import os,sys,json,hashlib,subprocess,importlib.util
os.environ["CUDA_VISIBLE_DEVICES"]="-1";os.environ["OMP_NUM_THREADS"]="1";os.environ["MKL_NUM_THREADS"]="1";os.environ["OPENBLAS_NUM_THREADS"]="1"
from pathlib import Path
import numpy as np,torch
R=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1");O=R/"reports"/"coupling"/"COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1"
PC=R/"scripts"/"coupling_ml"/"coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py"
HY=R/"scripts"/"coupling_ml"/"coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py"
def load(name,path):
 s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def atomic(p,x):
 t=Path(str(p)+".tmp");t.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");os.replace(t,p)
def summ(a):
 a=np.asarray(a,float);return {"median":float(np.median(a)),"q95":float(np.quantile(a,.95)),"worst":float(np.max(a)),"min":float(np.min(a))}
poc=load("prep_poc",PC);hyb=load("prep_hyb",HY);M=poc.import_model();ctx=poc.load_context();fold=ctx["folds"][0];ids=ctx["ids"];ix={g:i for i,g in enumerate(ids)}
tid=fold["test_geometry_id"];trainids=list(fold["train_geometry_ids"]);selected=sorted(trainids)[:4]
assert selected==json.loads((O/"protocol.json").read_text())["outer_fold"]["selected_case_ids"]
outer=np.asarray([ix[g] for g in trainids],int);local_c=ctx["c"][outer];geo=ctx["geometry"][outer]
pcs,Y=poc.build_c0_basis(M,local_c,list(range(len(trainids))))
savedp=json.loads((R/"reports"/"coupling"/"COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1"/"seed_progress.json").read_text(encoding="utf-8-sig"))["outer_pca"][tid]
ratios=np.asarray([p.explained_variance_ratio_ for p in pcs],float)
expected=np.asarray(savedp["c0_order_rank2_explained_variance_ratio"],float)
parity=np.abs(ratios-expected)
assert parity.max()<1e-12, float(parity.max())
xf=M.Xform().fit(geo);X=xf.transform(geo)
assert X.shape==(31,6)
lookup={g:i for i,g in enumerate(trainids)};sel_local=[lookup[g] for g in selected]
c4=local_c[sel_local];y4=Y[sel_local];sd=np.maximum(np.std(y4,axis=0),1e-12)
zero=np.zeros_like(y4);mean=np.broadcast_to(y4.mean(0),y4.shape).copy()
def loss(p): return float(np.mean(((p-y4)/sd)**2))
def states(p):
 dec=poc.c0_decode(M,p,pcs)
 vals=[float(hyb.state_detail(c4[i],dec[i])["state"]) for i in range(4)]
 return {"per_geometry":{selected[i]:vals[i] for i in range(4)},**summ(vals)}
oracle=poc.c0_decode(M,y4,pcs)
c4state=[float(hyb.state_detail(c4[i],oracle[i])["state"]) for i in range(4)]
complex_err=np.abs(oracle-c4)
report={
 "fold_index_zero_based":0,"heldout_geometry_id":tid,"heldout_truth_used":False,
 "outer_train_geometry_count":31,"selected_case_ids":selected,"selection_rule":"lexicographically first four case IDs from frozen outer-train list",
 "training_rows":4,"wavelengths_per_geometry":21,"latent_target_shape":list(y4.shape),"latent_order":"-3 to +3, two Cartesian PCA scores per order",
 "preprocessing":{"PCA_fit_rows":31,"PCA_fit_geometry_ids":trainids,"input_scaler_fit_rows":31,"explained_variance_ratio_max_abs_parity_vs_saved_C0_outer_PCA":float(parity.max()),"PCA_fit_matches_frozen_outer_fold":bool(parity.max()<1e-12),"input_scaler":"same M5 Xform fitted on the 31 outer-train geometries"},
 "loss_scale":{"definition":"population standard deviation per latent coordinate on the four selected training rows, floor 1e-12; denominator-only, no centering","values":sd.tolist(),"minimum":float(sd.min()),"maximum":float(sd.max())},
 "constant_baselines":{"zero_prediction":{"raw_latent_mse":float(np.mean(y4**2)),"original_loss":loss(zero),"state":states(zero)},"train_latent_mean":{"raw_latent_mse":float(np.mean((y4-y4.mean(0))**2)),"original_loss":loss(mean),"state":states(mean)}},
 "oracle_rank2_reconstruction_floor":{"source":"true selected-four latent scores inverse-transformed through the frozen outer-train basis; train-only projection ceiling, not model fit","state_per_geometry":{selected[i]:c4state[i] for i in range(4)}, "state_summary":summ(c4state),"complex_rmse":float(np.sqrt(np.mean(complex_err**2))),"complex_max_abs_error":float(complex_err.max())},
 "leakage":{"truth_geometry_ids_read_for_metrics":selected,"PCA_and_scaler_truth_geometry_ids":trainids,"heldout_geometry_truth_used":False,"wavelength_random_split":False},
 "timestamp_local":"2026-10-03"
}
atomic(O/"four_geometry_pre_fit.json",report)
ck=json.loads((O/"checkpoint.json").read_text());ck.update({"phase":"FOUR_GEOMETRY_PRECHECK_COMPLETE","new_fit_count":0,"optimizer_steps":0,"PCA_parity_verified":True,"four_geometry_floor_saved":True});atomic(O/"checkpoint.json",ck)
print(json.dumps(report,indent=2))
