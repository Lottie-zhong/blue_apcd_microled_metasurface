# Frozen-H2 order and high-P_scale diagnostics

This is a zero-solver, zero-fit follow-up over the existing 272G dataset and saved OOF predictions. Frozen H2 was reloaded from its pinned module and recomputed for every model/seed prediction. Maximum parity difference against stored OOF H2 outputs was exactly 0 for both eta and absolute-order power. There were 336 order rows (4 models × 4 folds × 3 seeds × 7 orders) and 48 high-P_scale rows. All are development-fold evidence, not an independent test.

## Per-order H2 MAE: baseline A versus candidate D

Means pool the fixed fold × seed rows descriptively. Lower is better.

| Order m | A eta MAE | D eta MAE | D−A | A absolute-power MAE | D absolute-power MAE | D−A |
|---:|---:|---:|---:|---:|---:|---:|
| -3 | 0.04830 | 0.03711 | -0.01119 | 0.01529 | 0.01166 | -0.00363 |
| -2 | 0.07223 | 0.05159 | -0.02064 | 0.02256 | 0.01708 | -0.00548 |
| -1 | 0.07725 | 0.06073 | -0.01652 | 0.02681 | 0.02179 | -0.00502 |
| +0 | 0.12339 | 0.08332 | -0.04007 | 0.04615 | 0.03066 | -0.01549 |
| +1 | 0.07362 | 0.05469 | -0.01893 | 0.02339 | 0.01835 | -0.00504 |
| +2 | 0.06525 | 0.05188 | -0.01337 | 0.02036 | 0.01627 | -0.00410 |
| +3 | 0.04651 | 0.03406 | -0.01246 | 0.01470 | 0.01081 | -0.00389 |

The propagating center order `m=0` has the largest eta and order-power MAE in both A and D; D reduces its eta MAE from 0.12339 to 0.08332 and absolute-order power MAE from 0.04615 to 0.03066. D lowers both errors for all seven orders in these fixed-fold means. This describes current validation predictions only.

## High-P_scale underestimation

For each fold, the high region is validation points with true `P_scale` at or above the 75th percentile of training-fold `P_scale` pooled over training geometries and wavelengths. The cut is fitted on training values only; validation truth is used solely to define the evaluated subgroup. Table entries are descriptive means across the 12 fold-seed rows per model. Average high-region sample count is 147 per fold-seed row.

| Model | Train q75 cut | High-region MAE | Prediction−truth bias | Underprediction fraction | Mean truth | Mean prediction |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.4946 | 0.1000 | -0.0304 | 0.609 | 0.6271 | 0.5968 |
| B | 0.4946 | 0.0745 | -0.0387 | 0.688 | 0.6271 | 0.5884 |
| C | 0.4946 | 0.0743 | -0.0296 | 0.648 | 0.6271 | 0.5975 |
| D | 0.4946 | 0.0658 | -0.0351 | 0.689 | 0.6271 | 0.5920 |

D improves high-region absolute error versus A (0.1000 to 0.0658), while the signed bias remains negative (-0.0351) and underprediction occurs in about 69% of high-region points. Thus the absolute-error gain does not remove the high-`P_scale` underestimation pattern. The overall P_scale MAE also improves (0.06543 to 0.05066).

## Artifacts and limits

- `CYCLIC_H2_ORDER_METRICS.csv`: fold × seed × model × order eta and absolute-power metrics.
- `CYCLIC_PSCALE_HIGH_REGION_DIAGNOSTICS.csv`: train-fold q75 cut and validation tail metrics.
- `CYCLIC_H2_PSCALE_DIAGNOSTICS.json`: H2 parity identity, row counts and aggregate values.
- `CYCLIC_H5_COORDINATE_AUDIT.json`: representative native/canonical H5 coordinate ranges and receipt lineage.

The repeated development folds are correlated and have been reused for model selection. These diagnostics do not certify final generalization or authorize a new dataset batch.
