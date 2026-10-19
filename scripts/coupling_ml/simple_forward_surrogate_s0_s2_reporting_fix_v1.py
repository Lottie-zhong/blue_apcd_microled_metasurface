"""Zero-fit correction: tie-aware top-k metrics from existing predictions."""
import json,importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
OUT=ROOT/"reports/coupling/APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1"
source=ROOT/"scripts/coupling_ml/simple_forward_surrogate_s0_s2_v1.py"
assert not (OUT/"ZERO_FIT_METRIC_CORRECTION.json").exists()
(OUT/"TRAINING_SOURCE_BEFORE_TIE_REPORT_FIX.py").write_bytes(source.read_bytes())
text=source.read_text(encoding="utf-8");a=text.index("def metric(y,p):");b=text.index("\ndef evaluate(",a)
new='''def metric(y,p):
    y=np.asarray(y);p=np.asarray(p);e=p-y
    rho=None if np.std(p)<1e-14 or np.std(y)<1e-14 else float(spearmanr(y,p).statistic)
    k=max(1,int(np.ceil(len(y)*.2)))
    def inclusion(s):
        cutoff=np.partition(s,-k)[-k]
        w=(s>cutoff).astype(float);ties=s==cutoff
        w[ties]=(k-w.sum())/ties.sum()
        return w
    tw,pw=inclusion(y),inclusion(p);overlap=float(np.sum(tw*pw))
    return {"MAE":float(np.abs(e).mean()),"RMSE":float(np.sqrt((e*e).mean())),"R2":float(r2_score(y,p)),
      "Spearman":rho,"top20_recall":overlap/k,"top20_precision":overlap/k,
      "top20_mean_true":float(np.sum(y*pw)/k),"oracle_top20_mean":float(np.sum(y*tw)/k),
      "true_mean":float(y.mean()),"best_selected_regret":float(y.max()-y[p==p.max()].mean()),
      "error_q95":float(np.quantile(np.abs(e),.95)),
      "top20_tie_handling":"fractional inclusion at cutoff; constant prediction equals random selection expectation"}
'''
source.write_text(text[:a]+new+text[b:],encoding="utf-8")
spec=importlib.util.spec_from_file_location("s0_report_fixed",source);B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
d=np.load(OUT/"DATASET_156G.npz",allow_pickle=False);z=np.load(OUT/"OOF_PREDICTIONS.npz",allow_pickle=False);rec=np.load(OUT/"RECOVERY_OOF_PREDICTIONS.npz",allow_pickle=False)
ids=d["case_ids"];ix={c:i for i,c in enumerate(ids)};folds=json.loads((OUT/"FOLDS.json").read_text());idx=z["heldout_indices"]
eta,ps,ab=d["eta_plus1"],d["P_scale"],d["P_plus1_H2"]
(OUT/"RESULTS_BEFORE_TIE_REPORT_FIX.json").write_bytes((OUT/"RESULTS.json").read_bytes())
r=json.loads((OUT/"RESULTS.json").read_text())
for target,models in r.items():
    for kind,res in models.items():
        p=(rec if kind=="MLP_Adam_recovery" else z)[f"{target}_{kind}"]
        res["pooled_OOF_descriptive"]=B.evaluate(target,p[idx],eta,ps,ab,idx)
        for f,fold in zip(res["folds"],folds):
            va=np.array([ix[c] for c in fold["heldout_ids"]]);f["metrics"]=B.evaluate(target,p[va],eta,ps,ab,va)
        if kind=="MLP_Adam_recovery":
            for seed in [17,29,43]:
                pseed=rec[f"{target}_Adam_seed{seed}"]
                res["seed_stability"]["per_seed"][str(seed)]=B.evaluate(target,pseed[idx],eta,ps,ab,idx)
B.put("RESULTS.json",r)
test=B.metric(np.arange(31,dtype=float),np.ones(31))
assert abs(test["top20_recall"]-7/31)<1e-14 and test["Spearman"] is None
assert len(json.loads((OUT/"FIT_LEDGER.json").read_text()))==449
assert len(json.loads((OUT/"OPTIMIZER_RECOVERY_FIT_LEDGER.json").read_text()))==30
B.put("ZERO_FIT_METRIC_CORRECTION.json",{"status":"PASS","new_fits":0,"reason":"argsort arbitrarily selected constant Mean top-k ties. Replaced with fractional cutoff inclusion for all cached OOF predictions.","constant_predictor_expected_recall":7/31,"actual":test["top20_recall"],"original_source_and_results_preserved":True})
analysis=ROOT/"scripts/coupling_ml/simple_forward_surrogate_s0_s2_analysis_v1.py"
s=analysis.read_text(encoding="utf-8")
s=s.replace("Pending final Chat-readable A–E assessment based on the complete tables above.",
 "A. 450nm eta(+1) and P(+1): current grouped validation does not demonstrate useful learnability; P_scale has limited error reduction. Tiny best P(+1) gain overlaps zero in the paired geometry bootstrap.\\n\\nB. Full42D: P_scale spectra contain some learnable structure, but eta/P(+1) do not show stable mean-baseline gains; the joint42D task is not established as useful.\\n\\nC. KRR is the cheapest reproducible reference with modest P_scale improvement. Fixed-grid GPR does not improve the main targets. LBFGS MLP has optimizer failures; fixed Adam removes abnormal exits but does not yield robust generalization. No universally effective model is demonstrated.\\n\\nD. Unknown K6 ranking is not reliable: fold Spearman is near zero or negative, and top20 recall is variable. A positive top-k hit rate alone does not override poor full ranking. No sealed confirmation or extrapolation test supports production ranking.\\n\\nE. Prioritize numerical credibility and lawful coverage/data-quality review before surrogate-driven optimization. This experiment gives no basis for jumping directly to a larger ML or more complex physics model. Any new data or solver work remains separately unauthorized.")
s=s.replace("Pooled OOF error is descriptive;", "Top-k ties use fractional cutoff inclusion; a constant predictor has the random selection expectation. The initial tie-report bug was corrected from cached predictions with zero new fits and preserved originals. Pooled OOF error is descriptive;")
analysis.write_text(s,encoding="utf-8")
import runpy
runpy.run_path(str(analysis),run_name="__main__")
