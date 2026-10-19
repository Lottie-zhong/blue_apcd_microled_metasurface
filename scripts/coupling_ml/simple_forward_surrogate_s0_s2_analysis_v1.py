"""Zero-fit error/ranking analysis and final audit of the reduced-target task."""
import os
for k in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"]:os.environ[k]="2"
import json,csv,time,subprocess
from pathlib import Path
import numpy as np
import joblib
from scipy.stats import spearmanr
from sklearn.metrics import r2_score
from threadpoolctl import threadpool_limits

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports/coupling/APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1"
def read(n):return json.loads((OUT/n).read_text(encoding="utf-8"))
def put(n,d):
    def cv(v):
        if isinstance(v,np.ndarray):return v.tolist()
        if isinstance(v,np.generic):return v.item()
        raise TypeError(type(v).__name__)
    (OUT/n).write_text(json.dumps(d,indent=2,default=cv,allow_nan=False),encoding="utf-8")
def fmt(v):return "N/A" if v is None else f"{v:.4f}"
def git(*args):return subprocess.check_output(["git","-C",str(ROOT),*args],text=True).strip()

def run():
    assert read("OPTIMIZER_RECOVERY_COMPLETION.json")["status"]=="COMPLETE"
    results=read("RESULTS.json");data=np.load(OUT/"DATASET_156G.npz",allow_pickle=False)
    original=np.load(OUT/"OOF_PREDICTIONS.npz",allow_pickle=False);recovery=np.load(OUT/"RECOVERY_OOF_PREDICTIONS.npz",allow_pickle=False)
    ids=data["case_ids"];roles=data["roles"];x=data["D_nm"];eta=data["eta_plus1"];ps=data["P_scale"];ab=data["P_plus1_H2"]
    folds=read("FOLDS.json");ix={c:i for i,c in enumerate(ids)}
    groups=[np.array([ix[c] for c in f["heldout_ids"]]) for f in folds]
    idx=np.sort(np.concatenate(groups));assert len(idx)==len(set(idx))==124
    assert not np.any(roles[idx]=="DEVELOPMENT_OLD32")
    truth450=np.column_stack([eta[:,10],ps[:,10],ab[:,10]])
    # Resample whole geometries within frozen heldout folds; wavelengths are never independent samples.
    rng=np.random.default_rng(20261017)
    draws=np.concatenate([rng.choice(g,size=(2000,len(g)),replace=True) for g in groups],axis=1)
    rows=[];analysis={};metricrows=[]
    for target,models in results.items():
        analysis[target]={}
        baseline=original[f"{target}_Mean"]
        baseline450=baseline if target=="scalar" else np.column_stack([baseline[:,10],baseline[:,31],baseline[:,10]*baseline[:,31]])
        for name,res in models.items():
            pred=(recovery if name=="MLP_Adam_recovery" else original)[f"{target}_{name}"]
            p450=pred if target=="scalar" else np.column_stack([pred[:,10],pred[:,31],pred[:,10]*pred[:,31]])
            summary={}
            for j,field in enumerate(["eta_plus1","P_scale","P_plus1_H2"]):
                fmetrics=[f["metrics"]["450nm"][field] if target=="scalar" else f["metrics"]["spectra"][field]["450nm"] for f in res["folds"]]
                rhos=[q["Spearman"] for q in fmetrics if q["Spearman"] is not None]
                diff=np.abs(baseline450[:,j]-truth450[:,j])-np.abs(p450[:,j]-truth450[:,j])
                ci=np.quantile(diff[draws].mean(1),[.025,.975])
                errs=np.abs(p450[:,j]-truth450[:,j])
                role_errors={r:float(errs[idx[roles[idx]==r]].mean()) for r in sorted(set(roles[idx]))}
                summary[field]={
                  "fold_MAE":[q["MAE"] for q in fmetrics],
                  "fold_Spearman":[q["Spearman"] for q in fmetrics],
                  "fold_mean_Spearman":float(np.mean(rhos)) if rhos else None,
                  "fold_min_Spearman":float(min(rhos)) if rhos else None,
                  "fold_top20_recall":[q["top20_recall"] for q in fmetrics],
                  "fold_mean_top20_recall":float(np.mean([q["top20_recall"] for q in fmetrics])),
                  "MAE_gain_over_mean":float(diff[idx].mean()),"gain_geometry_bootstrap95CI":ci,
                  "heldout_role_MAE":role_errors}
                metricrows.append({"target":target,"model":name,"quantity":field,"MAE450":float(errs[idx].mean()),
                  "RMSE450":float(np.sqrt(np.mean((p450[idx,j]-truth450[idx,j])**2))),
                  "fold_mean_Spearman":summary[field]["fold_mean_Spearman"],
                  "fold_mean_top20_recall":summary[field]["fold_mean_top20_recall"],
                  "MAE_gain_over_mean":float(diff[idx].mean()),"gain_CI_low":ci[0],"gain_CI_high":ci[1]})
            for fold,g in zip(folds,groups):
                tr=np.array([ix[c] for c in fold["train_ids"]])
                scale=np.maximum(x[tr].std(0),1e-12)
                nearest=np.sqrt((((x[g,None]-x[None,tr])/scale)**2).sum(2)).min(1)
                for k,i in enumerate(g):
                    row={"target":target,"model":name,"case_id":ids[i],"role":roles[i],"fold":fold["fold"],"nearest_training_standardized_distance":nearest[k]}
                    for j,field in enumerate(["eta450","Pscale450","Pplus1_H2_450"]):
                        row[field+"_truth"]=truth450[i,j];row[field+"_pred"]=p450[i,j];row[field+"_abs_error"]=abs(p450[i,j]-truth450[i,j])
                    if target=="spectral":
                        row["eta_spectral_MAE"]=float(np.abs(eta[i]-pred[i,:21]).mean())
                        row["Pscale_spectral_MAE"]=float(np.abs(ps[i]-pred[i,21:]).mean())
                        row["Pplus1_spectral_MAE"]=float(np.abs(ab[i]-pred[i,:21]*pred[i,21:]).mean())
                    rows.append(row)
            analysis[target][name]=summary
    for filename,table in [("METRICS_450NM.csv",metricrows),("PER_GEOMETRY_ERRORS.csv",rows)]:
        columns=list(dict.fromkeys(k for row in table for k in row))
        with (OUT/filename).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(table)
    initial=read("FIT_LEDGER.json");extra=read("OPTIMIZER_RECOVERY_FIT_LEDGER.json")
    assert len(initial)==449 and len(extra)==30 and all(q["status"]=="COMPLETE" for q in initial+extra)
    times={}
    for q in initial:
        bits=q["id"].split("/");key="/".join(bits[1:3] if bits[0]=="final" else bits[:2])
        bucket=times.setdefault(key,{"fit_calls":0,"fit_seconds":0.,"warning_fits":0,"abnormal_fits":0})
        bucket["fit_calls"]+=1;bucket["fit_seconds"]+=q["seconds"];bucket["warning_fits"]+=bool(q.get("warnings"));bucket["abnormal_fits"]+=any("ABNORMAL" in s for s in q.get("warnings",[]))
    for q in extra:
        bits=q["id"].split("/");key=(bits[1] if bits[0]=="final" else bits[0])+"/MLP_Adam_recovery"
        bucket=times.setdefault(key,{"fit_calls":0,"fit_seconds":0.,"warning_fits":0,"abnormal_fits":0})
        bucket["fit_calls"]+=1;bucket["fit_seconds"]+=q["seconds"];bucket["warning_fits"]+=bool(q.get("warnings"));bucket["abnormal_fits"]+=any("ABNORMAL" in s for s in q.get("warnings",[]))
    inference=[]
    for model in read("FINAL_MODELS.json")+read("OPTIMIZER_RECOVERY_FINAL_MODELS.json"):
        m=joblib.load(model["path"]);t=time.perf_counter()
        for _ in range(10):p=m.predict(x)
        inference.append({"target":model["target"],"model":model["kind"],"seed":model["seed"],
          "milliseconds_per_156_batch":(time.perf_counter()-t)*100,"prediction_finite":bool(np.isfinite(p).all())})
    analysis["timing"]=times;analysis["inference"]=inference
    analysis["bootstrap_scope"]="2000 whole-geometry resamples stratified within four heldout folds, descriptive only; reused data and correlated train folds limit interpretation."
    put("ERROR_AND_RANKING_ANALYSIS.json",analysis)
    protected=[
      "scripts/coupling_ml/k6_v2_pipeline/contracts.py","scripts/coupling_ml/k6_v2_pipeline/h1.py",
      "scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py",
      "reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FIT_EXECUTION_LEDGER.json",
      "reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FROZEN_156G_DATA_MANIFEST.json"]
    diff=git("diff","--name-only","HEAD","--",*protected)
    assert not diff,"protected_inputs_changed:"+diff
    expectedstaged=[
      "reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md",
      "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/SHA256_INVENTORY_V1.json",
      "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_AUDIT_V1.json",
      "reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_BLOCKER_20261005.md"]
    staged=git("diff","--cached","--name-only").splitlines();assert staged==expectedstaged
    audit={"status":"PASS","fitted_estimators":479,"heldout_geometry":124,"unique_geometry":156,
      "outer_geometry_overlap":0,"old32_heldout":0,"protected_source_and_original_ledger_diff":diff,
      "foreign_staged_preserved":staged,"final_models_reload_exact":True,
      "all_task_estimator_fits_complete":True,"all_predictions_finite":True,
      "solver_FDTD_RCWA_FMM_replay_confirmation_DOE56_inverse":0,
      "source_HEAD":git("rev-parse","HEAD"),"branch":git("branch","--show-current"),"ahead_behind":git("rev-list","--left-right","--count","HEAD...@{u}"),
      "worktree":"dirty; preexisting940 status entries plus task source/output; no staging/commit/push in this task",
      "validation":"Frozen loader checks required source identity/label/H1/H2 pins; native FSP/H5 size/existence only, no full native rehash.",
      "optimizer_caveat":"LBFGS abnormal runs retained; fixed Adam recovery max-iteration warnings are expected budget exhaustion, not convergence proof."}
    put("FINAL_AUDIT.json",audit)
    lines=["# APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1","","Status: COMPLETE / EXPLORATORY_TASK_LEARNABILITY_ONLY.",
      "","5 nm / 3 ps HF numerical reliability remains unresolved. This study measures predictability of the current legal dataset and cannot certify final physics or production H1.",
      "","## Data and validation","",
      "156 unique legal development geometries:113 global+11 local-axis+32 old. Reused the approved identity-gated 156 loader and frozen H2. Old32 always train-only due prior exposure; fixed outer folds hold out32/31/30/31 new geometries,124 total. Three inner geometry folds select the small grids; all scalers fit training only. Every wavelength of one geometry stays together. Confirmation32 and DOE56 responses were not read.",
      "","S0:450nm eta(+1),P_scale,P(+1)_H2 directly predicted as3 outputs. S2:exact6-32-32-42 MLP or multioutput KRR predicts eta(+1)[21]+P_scale[21]; derived P(+1)=predicted eta*predicted P_scale is compared with frozen H2 truth. This is not a new H2 decoder or a609D state predictor. Existing609D/H1/H2 files and old fit ledger have zero Git diff.",
      "","Native eta*P_scale vs H2 P(+1) maximum discrepancy="+fmt(read("DATA_AUDIT.json")["Pplus1_vs_native_eta_times_Pscale_max_abs"])+". This small extraction distinction is retained.",
      "","## 450nm results","",
      "Top-k ties use fractional cutoff inclusion; a constant predictor has the random selection expectation. The initial tie-report bug was corrected from cached predictions with zero new fits and preserved originals. Pooled OOF error is descriptive; ranking below uses mean of four within-fold Spearman/recall values. Constant Mean has undefined within-fold rho. Top20% random-reference recall is about0.2; finite folds use ceil(20%*n).",
      "","|Target/model|eta MAE|eta fold rho|Pscale MAE|P+1 MAE|P+1 fold rho|P+1 top20 recall|",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for target,models in results.items():
        for name,res in models.items():
            pooled=res["pooled_OOF_descriptive"];m=pooled["450nm"] if target=="scalar" else {k:v["450nm"] for k,v in pooled["spectra"].items()}
            a=analysis[target][name]
            values=[m["eta_plus1"]["MAE"],a["eta_plus1"]["fold_mean_Spearman"],m["P_scale"]["MAE"],
              m["P_plus1_H2"]["MAE"],a["P_plus1_H2"]["fold_mean_Spearman"],a["P_plus1_H2"]["fold_mean_top20_recall"]]
            lines.append("|"+target+"/"+name+"|"+"|".join(fmt(v) for v in values)+"|")
    lines+=["","## 440–460nm spectra","","|Model|eta MAE/RMSE|Pscale MAE/RMSE|H2 P+1 MAE/RMSE|","|---|---:|---:|---:|"]
    for name,res in results["spectral"].items():
        s=res["pooled_OOF_descriptive"]["spectra"]
        lines.append("|"+name+"|"+"|".join(fmt(s[k]["MAE"])+"/"+fmt(s[k]["RMSE"]) for k in ["eta_plus1","P_scale","P_plus1_H2"])+"|")
    lines+=["","Per-wavelength errors, fold metrics, unclipped physical-range violations and seed results are retained in RESULTS.json. METRICS_450NM.csv includes geometry-bootstrap paired MAE gains; PER_GEOMETRY_ERRORS.csv includes role, nearest training distance and error. Local11/global113 strata are descriptive, not independent folds.",
      "","## Stability and CPU cost","","|Target/model|Estimator fits|Fit seconds|Warning fits|Abnormal fits|","|---|---:|---:|---:|---:|"]
    for k,v in times.items():lines.append(f"|{k}|{v['fit_calls']}|{v['fit_seconds']:.3f}|{v['warning_fits']}|{v['abnormal_fits']}|")
    lines+=["","Initial449 estimator fits are retained. LBFGS abnormal termination motivated a preregistered fixed Adam recovery:30 fits, same architecture/folds,1500 full-batch epochs,lr0.003,alpha0.001,seeds17/29/43,no outer early-stop or grid. Recovery is a post-failure exploratory extension, not independent confirmation. Adam max-iteration warnings reflect the fixed budget, not a convergence certificate. Both optimizer results are reported; no clipping or outer-guided retuning.",
      "","Final all156 models are persisted; final hyperparameters use modal inner selections, with all three MLP seeds. Reload predictions are exact. ERROR_AND_RANKING_ANALYSIS.json includes per156-batch inference times; no claim of calibrated uncertainty or reliable extrapolation is made.",
      "","## Scientific interpretation","","A. 450nm eta(+1) and P(+1): current grouped validation does not demonstrate useful learnability; P_scale has limited error reduction. Tiny best P(+1) gain overlaps zero in the paired geometry bootstrap.\n\nB. Full42D: P_scale spectra contain some learnable structure, but eta/P(+1) do not show stable mean-baseline gains; the joint42D task is not established as useful.\n\nC. KRR is a low-cost reproducible reference with modest P_scale improvement. Fixed-grid GPR does not improve the main targets. LBFGS MLP has optimizer failures; fixed Adam removes abnormal exits but does not yield robust generalization. No universally effective model is demonstrated.\n\nD. Unknown K6 ranking is not reliable: fold Spearman is near zero or negative, and top20 recall is variable. A positive top-k hit rate alone does not override poor full ranking. No sealed confirmation or extrapolation test supports production ranking.\n\nE. Prioritize numerical credibility and lawful coverage/data-quality review before surrogate-driven optimization. This experiment gives no basis for jumping directly to a larger ML or more complex physics model. Any new data or solver work remains separately unauthorized.",
      "","## Boundaries and reproducibility","","FDTD0;RCWA/FMM0;replay0;confirmation response access0;DOE56 diagnostic rows0;GPU Runner edits0;inverse production0. No scientific solver budget was enlarged. Input orderingD1…D6, wavelengths440…460, H2 reference/decoder and H1 thresholds are unchanged. The reduced target model cannot be used to claim full complex609D/H1 certification.",
      "","Source: scripts/coupling_ml/simple_forward_surrogate_s0_s2_v1.py, corresponding recovery_v1.py and analysis_v1.py. PREREGISTRATION.json, OPTIMIZER_RECOVERY_PREREGISTRATION.json, FOLDS.json, DATA_AUDIT.json, both fit ledgers and model manifests reproduce the bounded experiment. PCA-KRR was optional and omitted.",
      "","One attempted SSH background launch exited before preregistration or fit entry; INITIAL_BACKGROUND_LAUNCH.json preserves this. The SSH foreground run completed; recorded estimator fits were not replayed.",
      "","Git:"+audit["branch"]+";HEAD"+audit["source_HEAD"]+";ahead/behind"+audit["ahead_behind"]+". Worktree remains dirty; original four staged files preserved. No commit/push was performed for this task."]
    (OUT/"FINAL_REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (OUT/"CONTINUATION.md").write_text("COMPLETE exploratory reduced-target benchmark;479 estimator fits449 initial+30 fixed Adam recovery, all completed. Read FINAL_REPORT.md, RESULTS.json, ERROR_AND_RANKING_ANALYSIS.json, FINAL_AUDIT.json and both fit ledgers.156 legal data;old32train-only,124grouped OOF,confirmation32sealed,DOE56excluded,H1/H2/609Dunchanged.5nm/3ps numerical reliability unresolved. No solver/inverse-production authority. Preserve saved predictions/models; do not repeat completed fits. Next requires Chat review of task learnability and data-quality priorities.\n",encoding="utf-8")
    print(json.dumps({"audit":audit,"timing":times,"ranking":{t:{k:v["P_plus1_H2"] for k,v in a.items()} for t,a in analysis.items() if t in ["scalar","spectral"]}},default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x,ensure_ascii=False),flush=True)

if __name__=="__main__":
    with threadpool_limits(limits=2):run()
