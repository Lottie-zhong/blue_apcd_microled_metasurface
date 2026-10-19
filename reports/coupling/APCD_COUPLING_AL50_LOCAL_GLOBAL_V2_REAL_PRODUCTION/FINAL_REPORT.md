# AL50 Local + Global V2 real production

## Production
50/50 real entries; 50 valid labels; 0 invalid; 0 replay. FAST dataset 172 → 222 independent geometries. Solver-call time 7.979 h; summed entry-to-science time 9.750 h; first-entry to last-acceptance wall 17.929 h. Timing definitions differ; solver-call time is not kernel-only GPU time.

All original V2 identities retained; V1 superseded cases excluded. G001 then L001 were accepted before the remaining entries. Source/physics identities agree across frozen Manifest, canonical entries and science receipts. No historical raw files or protected ledgers changed.

## Matched evaluation
Same 124 validation geometries; family members purged from training; matched 172 baseline refit once. Published legacy unpurged metrics are a separate reference, not this before/after comparator. Fold-specific counts and purged identities are saved alongside predictions.

|Model|P(+1) MAE before|After|450nm rho before|After|
|---|---:|---:|---:|---:|
|Mean|0.0312150|0.0318741|None|None|
|KRR|0.0398162|0.0403647|-0.14981987561937504|-0.13461516584083325|
|ExtraTrees|0.0328885|0.0325760|-0.09394055263424005|0.07240557690363031|
|MLP|0.0430270|0.0412265|-0.20986639195065226|-0.1657757356658914|

## Local sampling ablation
Negative MAE deltas favor the mixed local/global allocation at equal nominal 40 acquisitions. Per-fold training counts differ under family purging. These comparisons are exploratory with one eligible local validation family.

```json
{
  "KRR": {
    "mixed40_minus_global40_Pplus_MAE": -0.0007151857648294568,
    "all50_minus_global40_Pplus_MAE": -0.00010282808455144149,
    "negative_means_lower_error": true,
    "independent_local_test_families": 1,
    "not_causal_against_unrun_V1": true
  },
  "ExtraTrees": {
    "mixed40_minus_global40_Pplus_MAE": 0.0004726678601080364,
    "all50_minus_global40_Pplus_MAE": 0.00011335407028487815,
    "negative_means_lower_error": true,
    "independent_local_test_families": 1,
    "not_causal_against_unrun_V1": true
  },
  "MLP": {
    "mixed40_minus_global40_Pplus_MAE": -0.002137819602092743,
    "all50_minus_global40_Pplus_MAE": -0.0011283687699509687,
    "negative_means_lower_error": true,
    "independent_local_test_families": 1,
    "not_causal_against_unrun_V1": true
  }
}
```

## Local information and limits
23 complete local edges and 2 full four-corner truth experiments. Truth interaction is Yij−Yi−Yj+Y0. Per-wavelength truth and model errors are in STAGE_50. Nonadditivity does not uniquely identify a near-field mechanism. S31 is truth-only for local generalization because its original anchor is train-only. Only G059 is an eligible held-out local family; wavelengths are not independent experimental replicates.

Whether local sampling adds predictive value must use the saved GLOBAL_ONLY_ABLATION and equal nominal 40-acquisition mixed view, local delta/direction errors and held-out interaction error together. These are limited ablations, not causal proof against the unrun V1 removed cases. Local response amplitude is compared with observed A1 time sensitivity only; different geometry and unresolved grid error prevent interpreting that comparison as an uncertainty bound.

Recommend retaining global coverage as the default and using a small bounded local fraction until independent held-out local families establish repeatable gains. Do not raise local share solely because physical interactions are measurable. Next batch requires separate entry authorization. No automatic budget increase follows model stagnation.

## Data and artifacts
CASE_RESULTS.csv and NATIVE_ARTIFACT_INDEX.json enumerate every FSP/H5/609D and receipt. STAGE_16/32/50 contain fixed-124 metrics, Mean baseline, target MAE/RMSE, ranking, top recall, local errors, ablations, fit timing/warnings and family partitions. Figures show saved truth, interactions and learning curves. ML_TRAINING_GRADE; strict numerical convergence is not certified; fabrication UNRESOLVED.

## Frozen boundaries
DIAG2 1/2; A2 HOLD; DOE56 HOLD; sealed confirmation not accessed; Runner unchanged; no further production entries authorized.
