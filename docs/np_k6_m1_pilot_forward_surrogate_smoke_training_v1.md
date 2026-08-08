# NP K6 M1 pilot forward-surrogate smoke training v1

Status: `NP_K6_M1_PILOT_SURROGATE_SMOKE_TRAINING_COMPLETE_ACTIVE_LEARNING_READY`.

The six-case FDTD-only pilot dataset (66 observations: three development geometries × two polarizations × 11 exact wavelengths) was audited and used for real CUDA smoke training. No FDTD solver, sealed-test data, or bulk MDC training was accessed.

## Data and split

- Formal HF observations: 66; all rows have training_label=true and diagnostic_only=false; generator and interface-stack identities match.
- Leave-one-geometry-out CV: 3 folds, 44 training rows and 22 validation rows per fold; geometry-group leakage=false; normalization uses only training geometries.
- Fold mapping: A holds out RUN3A (seed 17), B RUN3B (seed 29), C RUN3C (seed 43).

## CUDA and model

- Torch `2.5.1+cu121`, CUDA `12.1`, GPU `NVIDIA GeForce RTX 3080`, actual device `cuda:0`.
- Peak allocated/reserved memory: `21352448` / `44040192` bytes.
- DataLoader pin_memory and non-blocking CUDA transfer were enabled; AMP was disabled.
- Primary CNN: three circular Conv1d layers, kernel 3, hidden channels 32, GELU, structured T/R and transmitted/reflected order heads.

## CV metrics (macro across held-out geometries)

| model | eta(+1) MAE | eta(+1) RMSE | all-order MAE | T MAE | R MAE | directionality MAE |
|---|---:|---:|---:|---:|---:|---:|
| CNN | 0.085381 | 0.099449 | 0.015572 | 0.048956 | 0.047745 | 0.093914 |
| MLP | 0.071002 | 0.089773 | 0.018748 | 0.085073 | 0.092402 | 0.190878 |
| LF DFT | 0.346839 | 0.356927 | 0.047055 | 0.069126 | 0.068789 | 0.482101 |

Architecture classification: `PILOT_DATA_TOO_SMALL_FOR_ARCHITECTURE_CONCLUSION`. The tiny three-geometry sample is insufficient for a final architecture claim; LF DFT remains baseline-only.

## Acquisition ensemble

- Three full-data CNN seeds `[17, 29, 43]`; purpose `ACQUISITION_ONLY`; checkpoint count `3`.
- Checkpoints remain runtime artifacts outside Git; each manifest entry records SHA256, seed, epoch, config hash, dataset manifest hash, geometry hashes, and CUDA device.

## Gate and next action

- real_training_started=true; pilot smoke completed; final performance model=false; inverse-design model=false; bulk MDC-compatible model=false; sealed test untouched; solver calls=0.
- Physics constraints: nonnegative structured powers, order sums constrained to T/R, no NaN/Inf, complete stratified metrics and worst-case retention.

Next action: `WAIT_FOR_NP_K6_M2_ACTIVE_LEARNING_BATCH1_SELECTION`.
