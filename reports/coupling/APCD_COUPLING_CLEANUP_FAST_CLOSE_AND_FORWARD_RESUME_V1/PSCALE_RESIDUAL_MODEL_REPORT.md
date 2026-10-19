# P_scale residual trend study — 272G

## Scope and split

The study reuses the existing 272G FAST complex dataset and the same fixed 124 development geometries and four geometry/family-purged outer folds (32/31/30/31). All 21 wavelengths stayed together per geometry. Every fit, scaler, wavelength trend, and residual model used its outer training IDs only. Inner stopping split training geometries by connected local-family component; validation labels were not supplied to fitting or stopping. The 124 set is development evidence because it has been reused for model selection; it is not final generalization certification.

`P_scale` was modelled in log space as `mu_train(lambda) + r(D, lambda)`, with `mu_train` computed from outer-training geometries. Two residual learners were evaluated: (i) Ridge, alpha=1, over standardized six-diameter features, centered wavelength, wavelength squared, and diameter-by-wavelength interactions; (ii) 7→32→32→1 tanh MLP, with family-grouped inner early stopping, patience 60, up to 800 epochs, seeds 17/29/43. A physical-mean wavelength baseline, log-mean wavelength trend, prior joint 29D NN3, and saved Leaf1 predictions were reused without retraining.

## Same 124 geometry OOF results

|P预测器|Pscale MAE|偏差|几何方差比|真峰 MAE|训练 q90 高值区 MAE / 偏差|
|---|---:|---:|---:|---:|---:|
|PhysicalMean|0.05343|0.01419|0.000|0.06900|0.10203 / -0.10203|
|LogTrendOnly|0.05309|0.00664|0.000|0.07149|0.10967 / -0.10967|
|ResidualRidge|0.05223|0.00560|0.039|0.07087|0.11208 / -0.11208|
|ResidualMLP|0.05322|0.00284|0.131|0.07647|0.10815 / -0.10815|
|JointNN3|0.06002|0.00447|0.313|0.09298|0.11462 / -0.11431|
|FrozenLeaf1P|0.05312|-0.00015|0.067|0.07457|0.11635 / -0.11635|

`geometry variance ratio` is predicted between-geometry variance divided by true between-geometry variance over wavelengths. The high-value region is defined by each fold's **training-only** q90 threshold; its validation subset is reported as a diagnostic. All compared methods still underestimate that region.

The residual Ridge lowers Pscale MAE from the log trend's 0.05309 to 0.05223 (about 1.6%), but retains only 3.9% of true between-geometry variance and has q90-region bias −0.1121. The residual MLP retains more variance (13.1%) but does not beat the log trend's Pscale MAE, has worse true-peak MAE, and its selected epochs vary from 1 to 115. It does not show repeatable improvement over a simple trend.

## Interpretation

- Public wavelength structure still dominates Pscale prediction. A wavelength-only trend remains a strong baseline.
- The small Ridge residual gives a modest pooled MAE reduction, but does not resolve high-P underprediction or establish robust geometry ranking.
- The residual MLP's greater variance is not sufficient evidence of better signal: Pscale MAE, peak error, and fold-to-fold behavior do not improve consistently.
- No validation-based recalibration or clipping was applied. P predictions stayed positive by exponentiating the predicted log values.
- These results do not validate FAST labels as strictly converged numerical truth and do not change H1.

Artifacts: `PSCALE_RESIDUAL_FOLD_METRICS.csv`, `PSCALE_RESIDUAL_MODEL_COMPARISON.csv`, `NN_EARLY_STOPPING_FITS.csv`, `NN_EARLY_STOPPING_CURVES.csv`, and `PREREGISTRATION.json`.
