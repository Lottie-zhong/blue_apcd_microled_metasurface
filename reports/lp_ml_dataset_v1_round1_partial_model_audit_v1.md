# LP_ML_DATASET_V1 Round-1 partial model audit

## Status

`LP_ML_ROUND1_DATA_OR_MODEL_FIX_REQUIRED`

## Production solver accounting

- Planned: 240 geometries / 480 subruns
- Entered: 92
- Accepted: 91
- Failed: 1
- Retry: 0
- Failed subrun: `LPML_R1_GLOBAL_SOBOL_054_y`
- Failure: `ValueError: math domain error`

## Dataset and split

- Smoke retained: 16 geometries / 144 rows
- Production complete: 45 geometries / 405 rows
- Combined partial: 61 geometries / 549 rows
- Split: train 387 rows, validation 81 rows, test 81 rows; geometry and alias groups kept together.

## Baselines

| model | test MAE | relative Frobenius mean | phase MAE (deg) |
|---|---:|---:|---:|
| ExtraTreesRegressor | 0.0418383 | 0.174706 | 5.22213 |\n| HistGradientBoostingRegressor | 0.04026 | 0.164156 | 5.14933 |\n| SimpleMLPRegressor | 0.0399383 | 0.161932 | 4.95986 |\n
## Residual MLP ensemble

- 5 seeds: 11, 22, 33, 44, 55
- Architecture: 7→256, four residual blocks, SiLU, LayerNorm, dropout 0.03
- AdamW 3e-4, weight decay 1e-4, cosine to 1e-6, max 500 epochs, patience 50, gradient clip 1.0
- Composite loss: 1.00 raw SmoothL1 + .25 relative Jones + .10 power + .05 rank + .05 projection + .05 circular phase masked by train-only 10th percentile amplitude
- Ensemble test MAE: 0.0400107
- Relative Frobenius mean: 0.164408
- Phase MAE: 4.98893 deg
- Uncertainty/error correlation: 0.0459857

The ensemble was trained only as a partial-coverage diagnostic. It is not promoted to a Round-1 forward surrogate.

## Round-2 proposal

Offline proposal written with zero runnable candidates because the production hard gate remains unresolved. No active-learning solver was launched.

## Hard gates

- No entered-case retry.
- No model-filled physics rows.
- No D9, inverse design, K6, Batch B, old Batch2, or canonical v1.21 change.
- Protected reports unchanged.
