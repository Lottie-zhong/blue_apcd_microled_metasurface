"""Fixed Adam optimizer recovery, retaining all initial LBFGS evidence."""
import os
for k in ["OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS"]:os.environ[k]="2"
import sys,json,time,warnings,importlib.util
from pathlib import Path
import numpy as np
import joblib
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from threadpoolctl import threadpool_limits

ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports/coupling/APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1"
spec=importlib.util.spec_from_file_location("s0_benchmark",ROOT/"scripts/coupling_ml/simple_forward_surrogate_s0_s2_v1.py")
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)

def run():
    assert not (OUT/"OPTIMIZER_RECOVERY_FIT_LEDGER.json").exists(),"do_not_repeat_recovery"
    old=json.loads((OUT/"FIT_LEDGER.json").read_text())
    abnormal=[q for q in old if any("ABNORMAL" in s for s in q.get("warnings",[]))]
    assert abnormal,"recovery_only_for_observed_optimizer_failure"
    B.put("OPTIMIZER_RECOVERY_PREREGISTRATION.json",{
      "reason":"Observed LBFGS ABNORMAL termination, retained as original evidence. Fixed Adam sensitivity comparison; not selected on recovery outer results.",
      "original_abnormal_fits":len(abnormal),"original_estimator_fits":449,
      "config":{"architecture":"6-32-32-3 or 6-32-32-42","activation":"tanh","solver":"adam","alpha":.001,"lr":.003,"epochs":1500,"batch":"full train split","shuffle":False,"early_stopping":False},
      "folds":"unchanged frozen4; old32 train-only; no added hyperparameter search",
      "seeds":[17,29,43],"finite_extra_fit_calls":30,"reporting":"keep both optimizers; exploratory post-failure extension, not independent confirmation"})
    (OUT/"RESULTS_LBFGS_ORIGINAL.json").write_bytes((OUT/"RESULTS.json").read_bytes())
    data=np.load(OUT/"DATASET_156G.npz",allow_pickle=False)
    ids=data["case_ids"];x=data["D_nm"];eta=data["eta_plus1"];ps=data["P_scale"];ab=data["P_plus1_H2"]
    folds=json.loads((OUT/"FOLDS.json").read_text());by={c:i for i,c in enumerate(ids)}
    results=json.loads((OUT/"RESULTS.json").read_text());ledger=[];saved={};final=[]
    def make(y,seed,n):
        return TransformedTargetRegressor(regressor=Pipeline([("x",StandardScaler()),("model",MLPRegressor(hidden_layer_sizes=(32,32),activation="tanh",solver="adam",alpha=.001,learning_rate_init=.003,max_iter=1500,batch_size=n,shuffle=False,early_stopping=False,tol=0.,n_iter_no_change=1600,random_state=seed))]),transformer=StandardScaler())
    def fit(m,xx,yy,tag):
        row={"id":tag,"status":"STARTED","n_geometry":len(xx),"outputs":yy.shape[1]};ledger.append(row);B.put("OPTIMIZER_RECOVERY_FIT_LEDGER.json",ledger)
        start=time.perf_counter()
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always");m.fit(xx,yy)
        est=m.regressor_.named_steps["model"]
        row.update(status="COMPLETE",seconds=time.perf_counter()-start,n_iter=int(est.n_iter_),loss=float(est.loss_),warnings=[str(w.message) for w in ws])
        assert np.isfinite(m.predict(xx)).all()
        B.put("OPTIMIZER_RECOVERY_FIT_LEDGER.json",ledger)
        return row
    for target in ["scalar","spectral"]:
        y=np.column_stack([eta[:,10],ps[:,10],ab[:,10]]) if target=="scalar" else np.column_stack([eta,ps])
        seeds={s:np.full_like(y,np.nan) for s in [17,29,43]};perfold=[];trainerr=[]
        for fold in folds:
            tr=np.array([by[c] for c in fold["train_ids"]]);va=np.array([by[c] for c in fold["heldout_ids"]])
            preds=[]
            for s in seeds:
                m=make(y,s,len(tr));row=fit(m,x[tr],y[tr],f"{target}/fold{fold['fold']}/seed{s}")
                start=time.perf_counter();p=m.predict(x[va]);row["predict_seconds"]=time.perf_counter()-start
                seeds[s][va]=p;preds.append(p)
                trainerr.append(float(np.sqrt(np.mean((m.predict(x[tr])-y[tr])**2))))
            perfold.append({"fold":fold["fold"],"n_train":len(tr),"n_test":len(va),"param":"fixed Adam recovery","metrics":B.evaluate(target,np.mean(preds,0),eta,ps,ab,va)})
            B.put("RECOVERY_PROGRESS.json",{"target":target,"fold":fold["fold"],"fits":len(ledger)})
        idx=np.where(np.isfinite(seeds[17]).all(1))[0]
        pp=np.mean(list(seeds.values()),axis=0)
        results[target]["MLP_Adam_recovery"]={"pooled_OOF_descriptive":B.evaluate(target,pp[idx],eta,ps,ab,idx),"folds":perfold,
          "train_RMSE_mean":float(np.mean(trainerr)),"seed_stability":{"per_seed":{str(s):B.evaluate(target,p[idx],eta,ps,ab,idx) for s,p in seeds.items()},"mean_prediction_sd":float(np.std(np.stack([p[idx] for p in seeds.values()]),axis=0).mean())}}
        saved[target+"_MLP_Adam_recovery"]=pp
        for s,p in seeds.items():saved[f"{target}_Adam_seed{s}"]=p
        for s in seeds:
            m=make(y,s,156);row=fit(m,x,y,f"final/{target}/seed{s}")
            path=OUT/f"models/FINAL_{target}_MLP_Adam_recovery_seed{s}.joblib";joblib.dump(m,path)
            assert np.array_equal(m.predict(x),joblib.load(path).predict(x))
            final.append({"target":target,"kind":"MLP_Adam_recovery","seed":s,"path":str(path),"fit_seconds":row["seconds"],"reload_exact":True})
    assert len(ledger)==30
    np.savez_compressed(OUT/"RECOVERY_OOF_PREDICTIONS.npz",**saved)
    B.put("RESULTS.json",results);B.put("OPTIMIZER_RECOVERY_FINAL_MODELS.json",final)
    counts=json.loads((OUT/"EXECUTION_COUNTS.json").read_text());counts.update(fit_calls=479,initial_fits=449,optimizer_recovery_fits=30,complete=479,recovery_max_iter_warnings_expected=True)
    B.put("EXECUTION_COUNTS.json",counts)
    B.put("OPTIMIZER_RECOVERY_COMPLETION.json",{"status":"COMPLETE","fits":30,"fit_seconds":sum(q["seconds"] for q in ledger),"all_seeds_finite":True})
    print(json.dumps({"recovery":"COMPLETE","fits":30}),flush=True)

if __name__=="__main__":
    with threadpool_limits(limits=2):run()
