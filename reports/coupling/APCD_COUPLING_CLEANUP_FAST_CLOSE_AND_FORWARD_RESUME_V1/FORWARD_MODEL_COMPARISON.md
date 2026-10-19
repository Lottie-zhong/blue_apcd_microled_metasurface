# 272G forward-model comparison

## 29D NN convergence

The formal route remains **Geometry + wavelength → 29D complex Floquet response → 609D state + P_scale → frozen H2**. The NN used the existing 7→64→64→29 tanh/Adam architecture. For each outer fold and seed, a separate 18% geometry-grouped inner split, preserving local-family components, selected the epoch by normalized 29D validation MSE (min improvement 1e-4, patience 60, cap 800). X/Y scalers were fit on the inner training subset for epoch selection, then refit on the full outer training set for the selected epoch. 12 fits stopped by patience; selected epochs were 238–304, mean 273.6. The fixed NN3 reference used the already-saved three seeds at 300 epochs.

## Fixed-124 development comparison

|609D态模型 + Pscale|复数 NRMSE|TM幅度 MAE|相对相位 °|全阶 routing MAE|Pscale MAE|P(+1) MAE|450nm Spearman|Top20 召回|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|NN3_Current_Joint|0.56104|0.12101|40.89|0.06682|0.06002|0.02060|0.71168|0.738|
|NN_EarlyStop_Joint|0.56694|0.12282|41.27|0.06765|0.06072|0.02076|0.71221|0.702|
|NN3_Current_ResidualRidge|0.56104|0.12101|40.89|0.06682|0.05223|0.02025|0.72025|0.702|
|NN3_Current_ResidualMLP|0.56104|0.12101|40.89|0.06682|0.05322|0.02031|0.71806|0.738|
|NN_EarlyStop_PhysicalMeanP|0.56694|0.12282|41.27|0.06765|0.05343|0.02093|0.71255|0.667|
|NN_EarlyStop_LogTrendP|0.56694|0.12282|41.27|0.06765|0.05309|0.02070|0.71255|0.667|
|NN_EarlyStop_ResidualRidge|0.56694|0.12282|41.27|0.06765|0.05223|0.02058|0.71349|0.702|
|NN_EarlyStop_ResidualMLP|0.56694|0.12282|41.27|0.06765|0.05322|0.02057|0.70640|0.702|
|NN_EarlyStop_FrozenLeaf1P|0.56694|0.12282|41.27|0.06765|0.05312|0.02060|0.71089|0.667|

The early-stopped NN does not improve the existing NN3: complex NRMSE, TM magnitude, relative phase, routing, Pscale, and P(+1) are slightly worse; Spearman changes by less than 0.001 and Top20 recall falls from 0.738 to 0.702. The selected epoch near 274 is consistent with the prior 300-epoch setting; this is not evidence for a longer optimization budget or architecture change.

## H2 decomposition by P estimator

Holding the saved current NN3 complex state fixed, the P estimator changes only absolute order power. Same-fold aggregation gives:

|P estimator|Pscale MAE|eta(+1) MAE|P(+1) MAE|450nm Spearman|Top20 recall|
|---|---:|---:|---:|---:|---:|
|NN3_Current_Joint|0.06002|0.06532|0.02060|0.71168|0.738|
|NN3_Current_PhysicalMeanP|0.05343|0.06532|0.02064|0.72225|0.702|
|NN3_Current_LogTrendP|0.05309|0.06532|0.02040|0.72225|0.702|
|NN3_Current_ResidualRidge|0.05223|0.06532|0.02025|0.72025|0.702|
|NN3_Current_ResidualMLP|0.05322|0.06532|0.02031|0.71806|0.738|

The residual Ridge is the best Pscale MAE in this small comparison. Its modest improvement in P(+1) comes with lower Top20 recall; the residual MLP keeps Top20 at the current NN3 value but does not beat Ridge's Pscale MAE. The H2 decoder and 609D state definition were unchanged. No direct eta or P(+1) regressor was used.

## Frozen H1 check

The new 29D NN remains **H1 HOLD**. For early-stop joint: state relative-RMSE median/q95 = 0.551/0.702 (median exceeds the frozen 0.50 limit); routing median/q95 = 0.093/0.128 with Pearson 0.801 (limits 0.05/0.10 and 0.95); absolute-order median/q95 = 0.035/0.059 (passes); thresholded absolute-order median/q95 = 0.536/0.720 (median exceeds 0.30); total-power median/q95 = 0.264/0.774 with Pearson 0.915 (limits 0.15/0.30 and 0.95). Residual P combinations leave state and routing failures and do not close the conjunction. Seed-stability passes, but that does not override other failed gates.

This is still the reused 124-geometry development OOF set, not an independent final test. Historical OOF remains development evidence; final generalization is not certified. No model was installed or promoted to production.

Machine-readable details: `FORWARD_MODEL_FOLD_METRICS.csv`, `FORWARD_MODEL_COMPARISON.csv`, `FORWARD_MODEL_SEED_STABILITY.csv`, `CURRENT_NN3_H2_P_ABLATION.csv`, and `H1_DEVELOPMENT_DIAGNOSTIC.json`.
