import os,sys,json,hashlib,subprocess,importlib.util,statistics
os.environ["CUDA_VISIBLE_DEVICES"]="-1";os.environ["OMP_NUM_THREADS"]="1";os.environ["MKL_NUM_THREADS"]="1";os.environ["OPENBLAS_NUM_THREADS"]="1"
from pathlib import Path
import numpy as np,torch
R=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1");N="COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1";O=R/"reports"/"coupling"/N
G=R/"reports"/"coupling"/"COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1";C=R/"reports"/"coupling"/"COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1"
PC=R/"scripts"/"coupling_ml"/"coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py";HY=R/"scripts"/"coupling_ml"/"coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py";GM=G/"g0_ordered_periodic_model.py"
torch.set_num_threads(1)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atom(p,x):
 t=Path(str(p)+".tmp");t.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8");os.replace(t,p)
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,str(p));m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
def statusbase():
 raw=subprocess.run(["git","status","--porcelain=v1","-z","--untracked-files=all"],cwd=str(R),capture_output=True,check=True).stdout
 q=("reports/coupling/"+N+"/").encode()
 es=sorted(e for e in raw.split(b"\0") if e and not e[3:].replace(b"\\",b"/").startswith(q))
 return {"count":len(es),"sha256":hashlib.sha256(b"\0".join(es)).hexdigest()}
def loss(y,p,s):return float(np.mean(((p-y)/s)**2))
def flatten(m):return np.concatenate([p.detach().cpu().numpy().reshape(-1) for p in m.parameters()]).astype(np.float32)
assert subprocess.run(["git","rev-parse","HEAD"],cwd=str(R),capture_output=True,text=True,check=True).stdout.strip()=="f0f47023af9c306590414232155c0d539c3dfa4d"
pr=json.loads((O/"protocol.json").read_text(encoding="utf-8-sig"));assert statusbase()==pr["preexisting_worktree_status_excluding_this_task"]
mismatch={k:{"expected":v,"actual":sha(R/Path(k))} for k,v in pr["input_sha256"].items() if sha(R/Path(k))!=v};assert not mismatch
poc=mod("fin_poc",PC);hyb=mod("fin_hyb",HY);M=poc.import_model();gm=mod("fin_gm",GM);ctx=poc.load_context()
fold=ctx["folds"][0];assert fold["test_geometry_id"]==pr["outer_fold"]["test_geometry_id"]
trainids=fold["train_geometry_ids"];selected=pr["outer_fold"]["selected_case_ids"];assert fold["test_geometry_id"] not in selected
ix=[ctx["ids"].index(g) for g in trainids];cl=ctx["c"][ix];gl=ctx["geometry"][ix]
pcs,Y=poc.build_c0_basis(M,cl,list(range(31)))
savedc=json.loads((C/"seed_progress.json").read_text(encoding="utf-8-sig"))["outer_pca"][fold["test_geometry_id"]]["c0_order_rank2_explained_variance_ratio"]
pca_delta=float(np.max(np.abs(np.asarray([x.explained_variance_ratio_ for x in pcs])-np.asarray(savedc))))
assert pca_delta<1e-12
xf=M.Xform().fit(gl);X=xf.transform(gl);loc={g:i for i,g in enumerate(trainids)};pick=[loc[g] for g in selected]
x4=X[pick];y4=np.asarray(Y[pick],np.float32);c4=cl[pick];sd=np.maximum(np.std(y4,axis=0),1e-12)
def statevals(pred):
 out=poc.c0_decode(M,pred,pcs)
 return [float(hyb.state_detail(c4[i],out[i])["state"]) for i in range(4)]
summary=json.loads((O/"fit_summary.json").read_text());reg=json.loads((O/"fit_registry.json").read_text())
assert set(reg)=={"T0","T1"} and summary["fit_count"]==2 and summary["optimizer_updates_total"]==3000
assert all(reg[k]["status"]=="COMPLETE" and reg[k]["start_count"]==1 for k in ("T0","T1"))
assert reg["T1"].get("preupdate_reconstruction_count")==1
checks={}
for label,model_cls,xin in [("T0",M.Net,x4),("T1",gm.OrderedPeriodicG0,gm.node_features(x4))]:
 rec=reg[label]["summary"];rs=torch.load(O/(label+"_resume.pt"),map_location="cpu",weights_only=True)
 assert int(rs["step"])==1500 and rs["fit_id"]==label and rs["protocol_sha256"]==sha(O/"protocol.json")
 optstate=rs["optimizer_state"]["state"]
 steps=[int(v["step"].item()) if hasattr(v["step"],"item") else int(v["step"]) for v in optstate.values()]
 assert len(steps)==rec["optimizer_parameter_tensor_count"] and set(steps)=={1500}
 fin=torch.load(O/(label+"_final_checkpoint.pt"),map_location="cpu",weights_only=True)
 mn=torch.load(O/(label+"_minloss_checkpoint.pt"),map_location="cpu",weights_only=True)
 assert int(fin["step"])==1500 and int(mn["step"])==rec["minimum_loss_step"]
 net=model_cls().cpu();net.load_state_dict(fin["model_state"]);net.eval()
 with torch.no_grad():pf=net(torch.as_tensor(xin,dtype=torch.float32)).cpu().numpy().astype(float)
 final_loss=loss(y4,pf,sd);fstate=statevals(pf)
 netm=model_cls().cpu();netm.load_state_dict(mn["model_state"]);netm.eval()
 with torch.no_grad():pm=netm(torch.as_tensor(xin,dtype=torch.float32)).cpu().numpy().astype(float)
 min_loss=loss(y4,pm,sd)
 assert abs(final_loss-rec["final_train_loss"])<1e-6 and abs(min_loss-rec["minimum_postupdate_train_loss"])<1e-6
 assert abs(float(np.median(fstate))-rec["final_state_error"]["summary"]["median"])<1e-12
 assert np.array_equal(np.load(O/(label+"_final_weights.npz"),allow_pickle=False)["parameters"],flatten(net))
 assert np.array_equal(np.load(O/(label+"_minloss_weights.npz"),allow_pickle=False)["parameters"],flatten(netm))
 snaps=json.loads((O/(label+"_snapshots.json")).read_text());assert [int(x["step"]) for x in snaps]==[0,10,50,100,300,750,1500]
 assert rec["optimizer_steps"]==1500 and rec["model_parameter_tensor_count"]==rec["optimizer_parameter_tensor_count"] and rec["all_parameter_tensors_received_gradient"]
 checks[label]={"final_loss_parity_abs_delta":abs(final_loss-rec["final_train_loss"]),"minloss_parity_abs_delta":abs(min_loss-rec["minimum_postupdate_train_loss"]),"final_state_median_parity_abs_delta":abs(float(np.median(fstate))-rec["final_state_error"]["summary"]["median"]),"weights_npz_match_pt":True,"optimizer_state_steps":1500,"snapshots":[0,10,50,100,300,750,1500]}
gp=json.loads((G/"seed_progress.json").read_text(encoding="utf-8-sig"));gf=list(gp["final_completed"].values());gi=list(gp["inner_completed"].values())
assert len(gf)==96 and len(gi)==288
for x in gf:assert int(x["selected_epochs"])==int(statistics.median(x["inner_best_epochs"]))
inner_steps=sum(int(x["epochs_executed"]) for x in gi);outer_steps=sum(int(x["selected_epochs"]) for x in gf)
total=int(json.loads((G/"checkpoint.json").read_text())["actual_optimizer_steps"]);assert inner_steps+outer_steps==total==20786
source=json.loads((O/"source_audit.json").read_text())
e=source["G0_early_stop_audit"];e["sum_inner_optimizer_updates"]=inner_steps;e["sum_outer_refit_optimizer_updates"]=outer_steps
e["outer_refit_updates_reconciled_with_total_step_count"]=(total-inner_steps)==outer_steps
e["outer_refit_steps_exactly_match_selected_epoch_count"]=(total-inner_steps)==outer_steps
e["all_final_refit_counts_equal_median_inner_best_epoch"]=True
atom(O/"source_audit.json",source)
fix={"status":"RESOLVED_NONSCIENTIFIC_DIAGNOSTIC_HARNESS_ISSUES","scientific_path_changed":False,"historical_authority_changed":False,"historical_results_affected":False,"issues":[
{"issue":"T0 step-0 state snapshot referenced undefined decoder module","fix":"Pass the frozen C0 decoder module explicitly through the snapshot helper.","optimizer_updates_before_fix":0,"recovery":"Reused persisted T0 step-0 model and optimizer state."},
{"issue":"T1 initial geometry tensor had shape [4,6], while G0 requires node features [4,6,2].","fix":"Pass the frozen G0 node_features conversion at the T1 callsite.","optimizer_updates_before_fix":0,"recovery":"Reconstructed the same seed-0 initial state under the same T1 run ID; no optimizer update had occurred."},
{"issue":"T1 snapshot first routed inverse-PCA decoding through the G0 candidate module.","fix":"Pass the frozen C0 decoder separately from the G0 candidate module.","optimizer_updates_before_fix":0,"recovery":"Resumed from persisted T1 step-0 model and optimizer state."}],
"fit_ids_started_once":{"T0":reg["T0"]["start_count"],"T1":reg["T1"]["start_count"]},"optimizer_updates_completed":{"T0":1500,"T1":1500}}
atom(O/"implementation_fix_log.json",fix)
aud={"status":"PASS","start_head":pr["start_head"],"branch":pr["branch"],"protocol_sha256":sha(O/"protocol.json"),"input_hash_mismatches":mismatch,
"zero_solver":True,"solver_invocations":0,"gpu_runner_invocations":0,"new_hf_invocations":0,"reserve_cases":0,"inverse_search_invocations":0,"P_scale_fit_invocations":0,"full_logo_reruns":0,
"new_fit_ids":["T0","T1"],"new_fit_count":2,"optimizer_updates":{"T0":1500,"T1":1500,"total":3000},
"outer_fold_index_zero_based":0,"heldout_geometry_id":fold["test_geometry_id"],"heldout_truth_used":False,"training_geometry_ids":selected,"PCA_and_scaler_fit_ids":trainids,
"PCA_saved_outer_fold_explained_variance_ratio_max_abs_delta":pca_delta,"PCA_parity":"PASS","checkpoint_reconstruction_parity":checks,
"G0_existing_step_reconciliation":{"inner_steps":inner_steps,"outer_refit_steps":outer_steps,"total_steps":total,"checkpoint_total_match":True},
"preexisting_worktree_status_excluding_task":statusbase(),"exact_allowlist_commit_pending":True}
atom(O/"reconstruction_and_training_audit.json",aud)
ck=json.loads((O/"checkpoint.json").read_text());ck.update({"phase":"AUDIT_COMPLETE","new_fit_count":2,"optimizer_steps":3000,"zero_solver":True,"audit_status":"PASS","resume":"read final report, audit.json and artifact_hashes.json; task ready for exact allowlist commit/push"});atom(O/"checkpoint.json",ck)
print(json.dumps({"audit":aud,"T0":reg["T0"]["summary"],"T1":reg["T1"]["summary"],"G0_early_stop":{"selected_epoch_median":e["selected_outer_refit_epoch_distribution"]["median"],"inner_best_epoch_median":e["inner_best_epoch_distribution"]["median"],"inner_epochs_executed_median":e["inner_epochs_executed_distribution"]["median"],"steps":total}},indent=2))
