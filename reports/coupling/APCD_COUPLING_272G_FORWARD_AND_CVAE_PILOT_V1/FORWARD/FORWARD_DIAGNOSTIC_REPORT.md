# TM complex forward diagnostic and lightweight contrasts — 272G

## Verdict
Offline branch complete; NEW_FDTD=0. Formal target remains Geometry+wavelength → Cartesian complex Floquet state + log(P_scale) → frozen H2. No direct-eta/power formal predictor was trained. Frozen H1 main accuracy requirements remain HOLD. No estimator is certified for inverse design or production optimization.

## Fixed evaluation and preregistration
The unchanged 272G cached truth, four family-purged folds and original 124 heldout geometries are reused. Old32 remain train-only as permitted by prior contract; the S31 heldout-connected family is purged. All 21 wavelengths of a geometry stay together. Inputs and Balanced output scaling use train-fold statistics only. Baseline Mean/KRR/ET predictions are reused without fitting. Exactly 24 additional ExtraTrees fits (two preregistered candidates × four folds × seeds17/29/43), CPU two threads, ET128, no hyperparameter search. Leaf1 differs only in min_samples_leaf=1 instead of3; Balanced retains leaf3 but equalizes training active-TM Cartesian variances and reduces logP relative weight. The official target is inverted exactly before H2. Frozen seed aggregation uses complex arithmetic mean and physical P_scale arithmetic mean after exp, unchanged.

## Quantitative comparison (same124 geometry OOF)

|Model|Complex NRMSE|TM amplitude RMSE|All-order Routing MAE|relative phase MAE deg|Pscale MAE|P+ MAE|450nm meanfold rho|Top20 recall|TM geometry variance ratio|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Mean|0.942921|0.340356|0.198134|91.042326|0.053090|0.043378|NA|NA|0.001511|
|KRR|0.862413|0.226042|0.109577|63.850078|0.072626|0.038966|0.043553|0.297619|0.531014|
|ExtraTrees|0.768557|0.274781|0.126928|49.708285|0.053431|0.029191|0.469040|0.517857|0.112876|
|Balanced|0.765704|0.272779|0.119042|49.384634|0.058941|0.029277|0.407184|0.517857|0.120333|
|Leaf1|0.754712|0.265680|0.115907|49.219550|0.053121|0.028486|0.499227|0.482143|0.141785|

## Shrinkage and target-scale attribution
The baseline ET weighted modal norm averages0.4553, versus truth1; TM between-geometry magnitude variance is only11.29% of truth. Leaf1 raises these to0.4680 and14.18%, and lowers complex NRMSE1.80%, TM amplitude RMSE3.31%, Routing MAE8.68%, P+ MAE2.42%. This is consistent with leaf-level averaging contributing, but does not uniquely prove that all shrinkage arises from leaf size: tree partitions, Cartesian phase cancellation, sparse geometry coverage, and intrinsic approximation errors remain possible. Leaf1 is the best small contrast on most error metrics but Top20 recall worsens; this is exploratory OOF selection, not nested external model certification.

Raw train-fold output variance shares are TM Cartesian69.3–69.5%, logP30.5–30.7%, TE about6e-10. These describe root-node multi-output squared-error contributions, not cumulative tree impurity reductions. Near-zero TE does not dominate the raw objective. Balanced produces TM93.33%, logP6.67%, leaving TE unamplified; complex/routing modestly improve but Pscale and ranking degrade. A simple target-scale change is insufficient. Training-fold contributions are in TRAIN_FOLD_TARGET_VARIANCE.json.

Projection onto the truth weighted unit-norm sphere changes no H2 routing (maximum eta change below6e-16), and worsens raw complex error for baseline and Leaf1. Projection corrects a structural norm identity, not learned per-order magnitudes, and is not adopted as a scientific improvement. H2 order powers depend on weighted per-channel squared magnitudes; arbitrary channel phase replacement alone leaves power unchanged. Phase remains essential in the609D scientific contract and phase cancellation can indirectly affect regression amplitudes, so it must be evaluated with active-mode energy weights. Near-zero TE phase is not optimized or interpreted as learned phase.

## Disagreement and sampling value
Baseline three-seed complex disagreement vs per-geometry P+ error has Spearman0.1128; Leaf1 only0.0486. This weak observed relation does not support using seed disagreement as the sole next-batch selector or a calibrated uncertainty. Coverage must remain dominant. Use multi-model active-TM/mode-allocation discrepancies together with coverage and stratified exploration; avoid ranking only by predicted high efficiency. Mode-specific errors and variance are saved for all seven TM orders in TM_ORDER_DIAGNOSTIC.csv.

## H2 attribution and scientific status
{
  "ExtraTrees": {
    "predC_trueP_PplusMAE": 0.028112302395761513,
    "trueC_predP_PplusMAE": 0.0074912679287361655,
    "predMagnitude_truePhase_eta_change_max": 3.3306690738754696e-16
  },
  "Leaf1": {
    "predC_trueP_PplusMAE": 0.02738261889064997,
    "trueC_predP_PplusMAE": 0.007427821089843005,
    "predMagnitude_truePhase_eta_change_max": 3.3306690738754696e-16
  }
}

Truth-C/predicted-P and predicted-C/truth-P are retrospective oracle decompositions, never deployable predictors. Main H1 gates are independently evaluated through the frozen loader, retained in FROZEN_H1_DIAGNOSTIC.json and H1_GATE_SUMMARY.json. Neither improved MAE nor nonnegative H2 output certifies independent energy closure, strict numerical convergence, or unknown-domain reliability.

## Recommendation and CVAE checker
Retain frozen B29 leaf3 as preregistered CVAE exploratory checker to avoid choosing a checker after seeing generated candidates. Leaf1 can be retained as an uncertainty/ablation companion for later independent evaluation. Any checker must be trained only on the same CVAE training fold; heldout geometry/family truth must never enter the checker fit. Proxy scores remain exploratory, not FDTD certification. Saved per-fold models contain exact train/heldout/purged IDs; model files are large runtime artifacts and should not be copied into Git or the local report bundle.

For a future approximately50G proposal, prioritize multidimensional coverage, low/high active-TM magnitude-variance corners, cross-model Routing disagreement, and a small number of complete independent local families. Avoid near-zero-mode phase targeting. No Case/Entry/Manifest or budget was created in this branch.

## Reproducibility and boundary
TRAIN_AND_ANALYZE.py; PREREGISTRATION.json; FIT_LEDGER.json; Balanced/Leaf1_PREDICTIONS.npz; METRICS_FIXED124.json; per-fold target scales and estimators; TM_ORDER_DIAGNOSTIC.csv; GEOMETRY_DIAGNOSTIC.csv. Fit+predict+compressed-estimator/checkpoint persistence elapsed 209.65 seconds, not pure estimator compute time. All24 fits complete and unique; no previous fits rerun. No solver, GPU, FSP/H5, sealed response, Runner edits, or Git mutation. DIAG2=1/2, A2 HOLD, DOE56 HOLD; next batch authorization0.

## Additional no-fit tree averaging diagnostic
{
  "fold": 1,
  "seed": 17,
  "geometry_count": 32,
  "tree_count": 128,
  "wavelengths": 21,
  "individual_tree_weighted_norm_mean": 1.0,
  "individual_tree_weighted_norm_min": 0.9999999999999994,
  "individual_tree_weighted_norm_max": 1.0000000000000004,
  "forest_mean_weighted_norm_mean": 0.4571282177668988,
  "forest_mean_over_mean_tree_norm": 0.4571282177668988,
  "unit_norm_truth": 1.0,
  "NEW_FITS": 0,
  "interpretation": "actual cross-tree Cartesian mixing strongly contracts norm even with leaf1. Individual tree predictions may pick a training target at a different wavelength: evaluation cos weights differ slightly; this is not assumed exact unit norm per tree. Single fold/seed diagnostic, not entire domain proof."
}

The earlier seed-TM-variance vs TM-MSE correlation (~0.419) and current seed-complex-disagreement vs P+MAE (0.113) involve different target/statistic/sample contracts and are not contradictory; neither is a calibration certificate.
