from pathlib import Path
import json,sys,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';D=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD';rd=lambda p:json.loads(Path(p).read_text());M=rd(D/'METRICS_FIXED124.json');G=rd(D/'FROZEN_H1_DIAGNOSTIC.json');L=rd(D/'FIT_LEDGER.json');z=np.load(B/'COMPLEX_DATASET.npz');ids=list(z['case_ids']);folds=rd(B/'FOLDS.json');old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');vi=np.array([ids.index(s) for f in old for s in f['heldout_old_ids']]);ff={s:f['fold']-1 for f in folds for s in f['heldout_ids']}
sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
dec=H.load_h2_decoder();oracle={};truth=z['C_hat'][vi];pt=z['P_scale'][vi];power=z['absolute_H2'][vi];base=np.load(B/'PREDICTIONS_B.npz');leaf=np.load(D/'Leaf1_PREDICTIONS.npz')
for name,a,ck,pk in [('ExtraTrees',base,'ExtraTrees_C_hat','ExtraTrees_P_scale'),('Leaf1',leaf,'C_hat','P_scale')]:
 cp=np.array([a[ck][ff[ids[i]],i] for i in vi]);ps=np.array([a[pk][ff[ids[i]],i] for i in vi]);a1=H.reconstruct_h2(cp,pt,dec);a2=H.reconstruct_h2(truth,ps,dec);a3=H.reconstruct_h2(abs(cp)*np.exp(1j*np.angle(truth)),ps,dec);h=H.reconstruct_h2(cp,ps,dec)
 oracle[name]={'predC_trueP_PplusMAE':float(abs(a1['absolute_order'][:,:,4]-power[:,:,4]).mean()),'trueC_predP_PplusMAE':float(abs(a2['absolute_order'][:,:,4]-power[:,:,4]).mean()),'predMagnitude_truePhase_eta_change_max':float(abs(a3['eta']-h['eta']).max())}
(D/'H2_ORACLE_DIAGNOSTIC.json').write_text(json.dumps(oracle,indent=2))
summary={}
def findg(v,path=''):
 out={}
 if isinstance(v,dict):
  for k,w in v.items():
   if 'pass' in k.lower() or k in ['status','verdict']:out[path+'/'+k]=w
   elif isinstance(w,dict):out.update(findg(w,path+'/'+k))
 return out
for k,v in G.items():summary[k]=findg(v)
(D/'H1_GATE_SUMMARY.json').write_text(json.dumps(summary,indent=2))
text='''# TM complex forward diagnostic and lightweight contrasts — 272G

## Verdict
Offline branch complete; NEW_FDTD=0. Formal target remains Geometry+wavelength → Cartesian complex Floquet state + log(P_scale) → frozen H2. No direct-eta/power formal predictor was trained. Frozen H1 main accuracy requirements remain HOLD. No estimator is certified for inverse design or production optimization.

## Fixed evaluation and preregistration
The unchanged 272G cached truth, four family-purged folds and original 124 heldout geometries are reused. Old32 remain train-only as permitted by prior contract; the S31 heldout-connected family is purged. All 21 wavelengths of a geometry stay together. Inputs and Balanced output scaling use train-fold statistics only. Baseline Mean/KRR/ET predictions are reused without fitting. Exactly 24 additional ExtraTrees fits (two preregistered candidates × four folds × seeds17/29/43), CPU two threads, ET128, no hyperparameter search. Leaf1 differs only in min_samples_leaf=1 instead of3; Balanced retains leaf3 but equalizes training active-TM Cartesian variances and reduces logP relative weight. The official target is inverted exactly before H2. Frozen seed aggregation uses complex arithmetic mean and physical P_scale arithmetic mean after exp, unchanged.

## Quantitative comparison (same124 geometry OOF)

|Model|Complex NRMSE|TM amplitude RMSE|All-order Routing MAE|relative phase MAE deg|Pscale MAE|P+ MAE|450nm meanfold rho|Top20 recall|TM geometry variance ratio|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
'''
for k,v in M.items():
 vals=[v[x] for x in ['complex_NRMSE','TM_magnitude_RMSE','routing_MAE','relative_phase_power_weighted_MAE_deg','P_scale_MAE','Pplus_MAE','rho450_mean','top20_recall','TM_between_geometry_variance_ratio']];text+='|'+k+'|'+'|'.join('NA' if x is None else f'{x:.6f}' for x in vals)+'|\n'
text+='''
## Shrinkage and target-scale attribution
The baseline ET weighted modal norm averages0.4553, versus truth1; TM between-geometry magnitude variance is only11.29% of truth. Leaf1 raises these to0.4680 and14.18%, and lowers complex NRMSE1.80%, TM amplitude RMSE3.31%, Routing MAE8.68%, P+ MAE2.42%. This is consistent with leaf-level averaging contributing, but does not uniquely prove that all shrinkage arises from leaf size: tree partitions, Cartesian phase cancellation, sparse geometry coverage, and intrinsic approximation errors remain possible. Leaf1 is the best small contrast on most error metrics but Top20 recall worsens; this is exploratory OOF selection, not nested external model certification.

Raw train-fold output variance shares are TM Cartesian69.3–69.5%, logP30.5–30.7%, TE about6e-10. These describe root-node multi-output squared-error contributions, not cumulative tree impurity reductions. Near-zero TE does not dominate the raw objective. Balanced produces TM93.33%, logP6.67%, leaving TE unamplified; complex/routing modestly improve but Pscale and ranking degrade. A simple target-scale change is insufficient. Training-fold contributions are in TRAIN_FOLD_TARGET_VARIANCE.json.

Projection onto the truth weighted unit-norm sphere changes no H2 routing (maximum eta change below6e-16), and worsens raw complex error for baseline and Leaf1. Projection corrects a structural norm identity, not learned per-order magnitudes, and is not adopted as a scientific improvement. H2 order powers depend on weighted per-channel squared magnitudes; arbitrary channel phase replacement alone leaves power unchanged. Phase remains essential in the609D scientific contract and phase cancellation can indirectly affect regression amplitudes, so it must be evaluated with active-mode energy weights. Near-zero TE phase is not optimized or interpreted as learned phase.

## Disagreement and sampling value
Baseline three-seed complex disagreement vs per-geometry P+ error has Spearman0.1128; Leaf1 only0.0486. This weak observed relation does not support using seed disagreement as the sole next-batch selector or a calibrated uncertainty. Coverage must remain dominant. Use multi-model active-TM/mode-allocation discrepancies together with coverage and stratified exploration; avoid ranking only by predicted high efficiency. Mode-specific errors and variance are saved for all seven TM orders in TM_ORDER_DIAGNOSTIC.csv.

## H2 attribution and scientific status
'''+json.dumps(oracle,indent=2)+'''

Truth-C/predicted-P and predicted-C/truth-P are retrospective oracle decompositions, never deployable predictors. Main H1 gates are independently evaluated through the frozen loader, retained in FROZEN_H1_DIAGNOSTIC.json and H1_GATE_SUMMARY.json. Neither improved MAE nor nonnegative H2 output certifies independent energy closure, strict numerical convergence, or unknown-domain reliability.

## Recommendation and CVAE checker
Retain frozen B29 leaf3 as preregistered CVAE exploratory checker to avoid choosing a checker after seeing generated candidates. Leaf1 can be retained as an uncertainty/ablation companion for later independent evaluation. Any checker must be trained only on the same CVAE training fold; heldout geometry/family truth must never enter the checker fit. Proxy scores remain exploratory, not FDTD certification. Saved per-fold models contain exact train/heldout/purged IDs; model files are large runtime artifacts and should not be copied into Git or the local report bundle.

For a future approximately50G proposal, prioritize multidimensional coverage, low/high active-TM magnitude-variance corners, cross-model Routing disagreement, and a small number of complete independent local families. Avoid near-zero-mode phase targeting. No Case/Entry/Manifest or budget was created in this branch.

## Reproducibility and boundary
TRAIN_AND_ANALYZE.py; PREREGISTRATION.json; FIT_LEDGER.json; Balanced/Leaf1_PREDICTIONS.npz; METRICS_FIXED124.json; per-fold target scales and estimators; TM_ORDER_DIAGNOSTIC.csv; GEOMETRY_DIAGNOSTIC.csv. Fit+predict+compressed-estimator/checkpoint persistence elapsed '''+f'{sum(x["seconds"] for x in L):.2f}'+''' seconds, not pure estimator compute time. All24 fits complete and unique; no previous fits rerun. No solver, GPU, FSP/H5, sealed response, Runner edits, or Git mutation. DIAG2=1/2, A2 HOLD, DOE56 HOLD; next batch authorization0.
'''
(D/'FORWARD_DIAGNOSTIC_REPORT.md').write_text(text,encoding='utf-8');print('REPORT_WRITTEN',len(text));print(json.dumps(summary));print(json.dumps(oracle))
