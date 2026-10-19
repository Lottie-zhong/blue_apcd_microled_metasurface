"""Task-sized CPU benchmark on approved 156G; no solver or confirmation API."""
import os
for key in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS"]:
    os.environ[key]="2"
import sys,json,time,warnings,csv,subprocess
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF,WhiteKernel
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
from threadpoolctl import threadpool_limits
import joblib

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports/coupling/APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1"
sys.path.insert(0,str(ROOT/"scripts/coupling_ml"))
from k6_v2_pipeline.amended156 import adapter as A
from k6_v2_pipeline import h1,contracts as C

def put(name,obj):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    def convert(x):
        if isinstance(x,np.ndarray):return x.tolist()
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x).__name__)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,default=convert,allow_nan=False),encoding="utf-8");tmp.replace(p)

LEDGER=[]
def fit(model,x,y,tag):
    row={"id":tag,"status":"STARTED","n_geometry":len(x),"outputs":y.shape[1]}
    LEDGER.append(row);put("FIT_LEDGER.json",LEDGER)
    t=time.perf_counter()
    try:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always");model.fit(x,y)
        row.update(status="COMPLETE",seconds=time.perf_counter()-t,warnings=[str(w.message) for w in ws])
    except BaseException as exc:
        row.update(status="FAILED",error=repr(exc));put("FIT_LEDGER.json",LEDGER);raise
    put("FIT_LEDGER.json",LEDGER)
    return row

def model(kind,param=None,seed=17):
    if kind=="Mean":reg=DummyRegressor()
    elif kind=="kNN":reg=KNeighborsRegressor(n_neighbors=int(param),weights="distance")
    elif kind=="KRR":reg=KernelRidge(kernel="rbf",gamma=param[0],alpha=param[1])
    elif kind=="GPR":reg=GaussianProcessRegressor(kernel=RBF(param[0],length_scale_bounds="fixed")+WhiteKernel(param[1],noise_level_bounds="fixed"),optimizer=None,alpha=1e-8,normalize_y=False,random_state=seed)
    elif kind=="MLP":reg=MLPRegressor(hidden_layer_sizes=(32,32),activation="tanh",solver="lbfgs",alpha=float(param),max_iter=600,max_fun=20000,tol=1e-6,random_state=seed)
    else:raise ValueError(kind)
    return TransformedTargetRegressor(regressor=Pipeline([("x",StandardScaler()),("model",reg)]),transformer=StandardScaler())

GRID={
 "Mean":[None],"kNN":[3,7,15],
 "KRR":[[g,a] for g in [1/24,1/6,2/3] for a in [.01,.1,1.]],
 "GPR":[[l,n] for l in [1.,3.] for n in [.01,.1]],
 "MLP":[1.,10.]
}

def metric(y,p):
    y=np.asarray(y);p=np.asarray(p);e=p-y
    rho=None if np.std(p)<1e-14 or np.std(y)<1e-14 else float(spearmanr(y,p).statistic)
    k=max(1,int(np.ceil(len(y)*.2)));a=set(np.argsort(y)[-k:]);b=set(np.argsort(p)[-k:])
    return {"MAE":float(np.abs(e).mean()),"RMSE":float(np.sqrt((e*e).mean())),"R2":float(r2_score(y,p)),
      "Spearman":rho,"top20_recall":len(a&b)/k,"top20_precision":len(a&b)/k,
      "top20_mean_true":float(y[list(b)].mean()),"oracle_top20_mean":float(y[list(a)].mean()),
      "true_mean":float(y.mean()),"best_selected_regret":float(y.max()-y[np.argmax(p)]),
      "error_q95":float(np.quantile(np.abs(e),.95))}

def evaluate(target,pred,eta,ps,ab,indices):
    idx=np.asarray(indices)
    if target=="scalar":t=np.column_stack([eta[idx,10],ps[idx,10],ab[idx,10]]);p=pred
    else:t=np.column_stack([eta[idx],ps[idx]]);p=pred
    out={"overall_MAE":float(np.abs(p-t).mean()),"overall_RMSE":float(np.sqrt(np.mean((p-t)**2)))}
    if target=="scalar":
        out["450nm"]={name:metric(t[:,j],p[:,j]) for j,name in enumerate(["eta_plus1","P_scale","P_plus1_H2"])}
    else:
        out["spectra"]={}
        for name,y,q in [("eta_plus1",eta[idx],p[:,:21]),("P_scale",ps[idx],p[:,21:]),("P_plus1_H2",ab[idx],p[:,:21]*p[:,21:])]:
            out["spectra"][name]={"MAE":float(np.abs(y-q).mean()),"RMSE":float(np.sqrt(np.mean((y-q)**2))),
                "450nm":metric(y[:,10],q[:,10]),"band_mean_ranking":metric(y.mean(1),q.mean(1)),
                "per_wavelength_MAE":np.abs(y-q).mean(0),"per_wavelength_RMSE":np.sqrt(((y-q)**2).mean(0))}
    ep=p[:,0] if target=="scalar" else p[:,:21]
    out["physical_violation"]={"negative_prediction_count":int((p<0).sum()),"eta_above_one_count":int((ep>1).sum()),"clipping_applied":False}
    return out

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"RESULTS.json").exists():raise ValueError("completed_task_exists_do_not_refit")
    if (OUT/"FIT_LEDGER.json").exists():raise ValueError("existing_fit_ledger_review_before_resume")
    put("PREREGISTRATION.json",{
      "authority":"User task APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1, 2026-10-17",
      "data":"Only existing frozen development 156G; old32 train-only; no confirmation or DOE56",
      "validation":"Existing frozen 4 outer folds, 124 distinct new geometries held out exactly once; 3 inner folds on new training geometries; old32 always training-only",
      "grid":GRID,"selection":"mean inner validation MSE standardized by inner-training target std; equal output weights; no outer response selection",
      "MLP":"6-32-32-3 scalar or 6-32-32-42 spectra; tanh/LBFGS; max600 iterations; alpha1 or10; outer seeds17,29,43",
      "spectral_output":"21 native eta(+1) then21 physical P_scale; P(+1) prediction=eta_hat*P_scale_hat compared to frozen H2 truth",
      "scalar_output":"450nm native eta(+1), P_scale, frozen H2 P(+1); joint 3-output regression",
      "rank":"Within each outer fold primary; pooled OOF descriptive. Top20% recall/precision; no wavelength pseudoreplication",
      "GPR":"Scalar only, fixed RBF length scales/noises selected inner; optimizer disabled",
      "final_models":"All156 using modal inner-selected hyperparameters; no sealed predictions",
      "limits":"Task learnability only;5nm/3ps HF numerical reliability unresolved; H1/H2 unchanged; no scientific final admission",
      "CPU_threads":2,"new_solver_budget":0,"finite_estimator_fit_calls":449})
    col=A.load_collection(False);cases=col.training_cases();plan=A.build_plan()
    ids=np.array([c.case_id for c in cases]);roles=np.array([c.role for c in cases]);x=np.array([c.ordered_D_nm for c in cases],float)
    assert len(cases)==156 and len(set(map(tuple,x)))==156
    dec=h1.load_h2_decoder()
    decoded=h1.reconstruct_h2(np.array([c.c_hat for c in cases]),np.array([c.p_scale for c in cases]),dec)
    eta=np.array([c.eta[:,4] for c in cases]);ps=np.array([c.p_scale for c in cases]);ab=decoded["absolute_order"][:,:,4]
    assert eta.shape==ps.shape==ab.shape==(156,21)
    assert np.isfinite(eta).all() and np.isfinite(ps).all() and np.all(ps>0)
    np.savez_compressed(OUT/"DATASET_156G.npz",case_ids=ids,roles=roles,D_nm=x,wavelengths_nm=np.arange(440,461),eta_plus1=eta,P_scale=ps,P_plus1_H2=ab)
    put("DATA_AUDIT.json",{"cases":156,"unique_geometry":156,"roles":{r:int((roles==r).sum()) for r in set(roles)},
        "manifest":col.manifest_sha256,"H2_decoder":C.H2_DECODER_SHA256,"H1":C.H1_AUTHORITY_SHA256,
        "Pplus1_vs_native_eta_times_Pscale_max_abs":float(np.max(np.abs(ab-eta*ps))),
        "old32_train_only":True,"confirmation_response_access":0,"DOE56_rows":0,"FDTD_runs":0,"RCWA_FMM_runs":0})
    index={s:i for i,s in enumerate(ids)};folds=[];seen=[]
    for f in range(1,5):
        va=np.array([index[s] for s in plan.outer_validation_ids[f]])
        tr=np.array([i for i in range(156) if i not in set(va)])
        assert not set(tr)&set(va) and not np.any(roles[va]==C.ROLE_OLD32)
        seen.extend(va);folds.append((f,tr,va))
    assert len(seen)==len(set(seen))==124
    put("FOLDS.json",[{"fold":f,"train_ids":ids[tr],"heldout_ids":ids[va]} for f,tr,va in folds])
    results={};allpred={};selected={};timings=[]
    for target in ["scalar","spectral"]:
        y=np.column_stack([eta[:,10],ps[:,10],ab[:,10]]) if target=="scalar" else np.column_stack([eta,ps])
        kinds=["Mean","kNN","KRR","GPR","MLP"] if target=="scalar" else ["Mean","kNN","KRR","MLP"]
        results[target]={};selected[target]={}
        for kind in kinds:
            pp=np.full((156,y.shape[1]),np.nan);seedpred={s:np.full_like(pp,np.nan) for s in [17,29,43]} if kind=="MLP" else {}
            foldmetrics=[];choices=[];trainrows=[]
            for f,tr,va in folds:
                old=tr[roles[tr]==C.ROLE_OLD32];new=tr[roles[tr]!=C.ROLE_OLD32]
                inner=list(KFold(n_splits=3,shuffle=True,random_state=20261017+f).split(new))
                scores=[]
                for j,param in enumerate(GRID[kind]):
                    loss=[]
                    if len(GRID[kind])>1:
                        for z,(a,b) in enumerate(inner):
                            ti=np.concatenate([old,new[a]]);vi=new[b]
                            assert not set(xi for xi in map(tuple,x[ti]))&set(map(tuple,x[vi]))
                            m=model(kind,param);fit(m,x[ti],y[ti],f"{target}/{kind}/fold{f}/param{j}/inner{z}")
                            sc=np.maximum(y[ti].std(0),1e-12);loss.append(float(np.mean(((m.predict(x[vi])-y[vi])/sc)**2)))
                    scores.append(float(np.mean(loss)) if loss else 0.)
                param=GRID[kind][int(np.argmin(scores))];choices.append(param)
                preds=[]
                for seed in ([17,29,43] if kind=="MLP" else [17]):
                    m=model(kind,param,seed);row=fit(m,x[tr],y[tr],f"{target}/{kind}/fold{f}/seed{seed}")
                    start=time.perf_counter();pv=m.predict(x[va]);row["predict_seconds"]=time.perf_counter()-start
                    preds.append(pv)
                    if kind=="MLP":seedpred[seed][va]=pv
                    timings.append({**row,"kind":kind,"target":target,"fold":f})
                    trainrows.append(float(np.sqrt(np.mean((m.predict(x[tr])-y[tr])**2))))
                pv=np.mean(preds,0);pp[va]=pv
                foldmetrics.append({"fold":f,"n_train":len(tr),"n_test":len(va),"param":param,"inner_losses":scores,
                    "metrics":evaluate(target,pv,eta,ps,ab,va)})
                put("PROGRESS.json",{"target":target,"model":kind,"completed_outer_fold":f,"completed_fit_calls":len(LEDGER)})
            idx=np.array(sorted(seen));assert np.isfinite(pp[idx]).all()
            results[target][kind]={"pooled_OOF_descriptive":evaluate(target,pp[idx],eta,ps,ab,idx),"folds":foldmetrics,
                "train_RMSE_mean":float(np.mean(trainrows)),"selected_params":choices}
            if seedpred:
                perseed={str(s):evaluate(target,v[idx],eta,ps,ab,idx) for s,v in seedpred.items()}
                results[target][kind]["seed_stability"]={"per_seed":perseed,"mean_prediction_sd":float(np.std(np.stack([v[idx] for v in seedpred.values()]),axis=0).mean())}
            allpred[f"{target}_{kind}"]=pp;selected[target][kind]=choices
            put("RESULTS_PARTIAL.json",results)
    # Final model choices use only the nested-CV parameter selections, no outer loss retuning.
    final=[]
    (OUT/"models").mkdir(exist_ok=True)
    for target in selected:
        y=np.column_stack([eta[:,10],ps[:,10],ab[:,10]]) if target=="scalar" else np.column_stack([eta,ps])
        for kind,choices in selected[target].items():
            keys=[json.dumps(p) for p in choices];key=max(dict.fromkeys(keys),key=keys.count);param=json.loads(key)
            for seed in ([17,29,43] if kind=="MLP" else [17]):
                m=model(kind,param,seed);row=fit(m,x,y,f"final/{target}/{kind}/seed{seed}")
                path=OUT/f"models/FINAL_{target}_{kind}_seed{seed}.joblib";joblib.dump(m,path)
                reload=joblib.load(path);assert np.array_equal(m.predict(x),reload.predict(x))
                final.append({"target":target,"kind":kind,"seed":seed,"param":param,"path":str(path),"fit_seconds":row["seconds"],"reload_exact":True})
    assert len(LEDGER)==449
    np.savez_compressed(OUT/"OOF_PREDICTIONS.npz",case_ids=ids,roles=roles,heldout_indices=np.array(sorted(seen)),**allpred)
    put("RESULTS.json",results);put("FINAL_MODELS.json",final);put("TIMINGS.json",timings)
    put("EXECUTION_COUNTS.json",{"fit_calls":len(LEDGER),"complete":sum(r["status"]=="COMPLETE" for r in LEDGER),
       "convergence_warning_fits":sum(bool(r.get("warnings")) for r in LEDGER),"FDTD":0,"RCWA_FMM":0,"GPU_Runner_edits":0,"confirmation_responses":0,"DOE56_rows":0,"inverse_optimization":0,
       "prior_268_fit_ledger_modified":False})
    # Human-readable compact result table; fold details and seed stability remain in JSON.
    lines=["# APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1","","Status: COMPLETE; scientific status: EXPLORATORY_TASK_LEARNABILITY_ONLY.",
      "","5nm/3ps HF numerical credibility remains unresolved. No formal H1/H2 pass, unknown-domain guarantee, solver or inverse-production admission is claimed.",
      "","156 legal geometries loaded; 32 old cases always train-only; 124 unique new geometries receive grouped out-of-fold predictions. Fixed historical folds and reuse of previously studied data mean this is not independent confirmation.",
      "","42D output is eta(+1)[21] + P_scale[21]. Spectral P(+1) prediction is their product, compared with frozen H2 P(+1); scalar P(+1) is directly regressed. No C_hat/H1/H2 modification or output clipping.",
      "","|Target/model|eta450 MAE|eta450 rho|Pscale450 MAE|P+1 450 MAE|P+1 rho|P+1 top20 recall|","|---|---:|---:|---:|---:|---:|---:|"]
    for target,models in results.items():
        for kind,v in models.items():
            q=v["pooled_OOF_descriptive"];a=q["450nm"] if target=="scalar" else {n:s["450nm"] for n,s in q["spectra"].items()}
            vals=[a["eta_plus1"]["MAE"],a["eta_plus1"]["Spearman"],a["P_scale"]["MAE"],a["P_plus1_H2"]["MAE"],a["P_plus1_H2"]["Spearman"],a["P_plus1_H2"]["top20_recall"]]
            lines.append("|"+target+"/"+kind+"|"+"|".join("N/A" if v is None else f"{v:.5f}" for v in vals)+"|")
    lines+=["","Spectral MAE/RMSE, per-wavelength errors, fold results, physical violations and seed variation: RESULTS.json. CPU fit/prediction times: TIMINGS.json. Every attempted fit: FIT_LEDGER.json.",
      "","No confirmation response, DOE56 diagnostic, new FDTD/RCWA/FMM, GPU Runner mutation, budget expansion or inverse production was used.",
      "","All preprocessing was fitted per inner/outer training split. Three seeds assess MLP optimizer sensitivity; deterministic KRR/GPR variability is assessed across folds. Hyperparameters were selected only within each outer training set.",
      "","PREREGISTRATION.json fixes grids and criteria before fits. No PCA-KRR was added because it is optional and direct multioutput KRR is sufficient for this bounded benchmark.",
      "","Git source baseline: "+subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()+". Existing foreign staged/dirty files preserved; task files only are newly generated."]
    (OUT/"FINAL_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    put("COMPLETION.json",{"status":"COMPLETE","fits":len(LEDGER),"heldout_geometry":124,"elapsed_fit_seconds":sum(r.get("seconds",0) for r in LEDGER)})
    (OUT/"CONTINUATION.md").write_text("Completed exploratory 156G reduced-target forward benchmark. Read FINAL_REPORT.md, RESULTS.json, DATA_AUDIT.json, FOLDS.json, FIT_LEDGER.json and EXECUTION_COUNTS.json. Confirmation32 remains sealed, DOE56 excluded, original H1/H2/609D untouched. 5nm/3ps HF numerical reliability remains unresolved. No solver, inverse optimization or new physical-budget authority. Do not rerun completed fits; final sklearn models and OOF predictions are saved. Any next scientific action needs Chat direction.\n",encoding="utf-8")
    print(json.dumps({"status":"COMPLETE","out":str(OUT),"fits":len(LEDGER)}),flush=True)

if __name__=="__main__":
    with threadpool_limits(limits=2):run()
