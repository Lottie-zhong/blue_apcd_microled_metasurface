# NP K6 M3 pilot retraining v1

## Status

`NP_K6_M3_PILOT_RETRAINING_COMPLETE_ACTIVE_LEARNING_REASSESSMENT_READY`

This stage is development-only and zero-solver. It does not authorize Batch2, bulk MDC-compatible training, or real training.

## A. Development HF V2 authority

The historical merged artifact was read-only. A derived, auditable training view was created at:

`outputs/np_k6_m3_pilot_retraining_v1/development_hf_v2_training_view.csv`

It contains exactly 198 rows = 9 geometry hashes × 2 polarizations × 11 wavelengths, with exact 445–455 nm at 1 nm spacing, `u_x=0`, `k_y=0`, the frozen generator `NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2`, and interface `NP_K6_INDEPENDENT_STACK_PILOT_V1`.

All 198 derived rows pass `quality_gate_pass=true`, `training_label=true`, and `diagnostic_only=false`. The 132 Batch1 rows were promoted only in this new view; the historical source remains immutable. Source and target numeric/identity digests are equal. No duplicate, missing, conflicting-provenance, or sealed-target read was found.

## B. Pre-M3 acquisition audit

`pre_m3_acquisition_error_audit_132rows.csv` uses only the frozen M2 selection-time CNN/MLP committee and LF proxy; no M3 prediction was backfilled into the selection audit. Aggregate absolute-error MAE:

| model | T | R | eta(+1) | directionality |
|---|---:|---:|---:|---:|
| CNN | 0.08804 | 0.08024 | 0.48186 | 0.20540 |
| MLP | 0.08679 | 0.07908 | 0.45668 | 0.19208 |

Uncertainty/error Pearson correlations were weak or metric-dependent: CNN (T 0.135, R 0.050, eta(+1) −0.219, directionality 0.165) and MLP (T 0.471, R 0.354, eta(+1) −0.186, directionality 0.285). The eta uncertainty therefore has no demonstrated ranking value. The frozen selection schema has no individual-order predictions; only an aggregate all-order disagreement proxy is available and is explicitly not treated as calibration. Per-geometry and per-polarization results are in the summary JSON.

## C. M3 pilot OOF

The training view was evaluated with 9-fold leave-one-geometry-out CV. All p/s rows and all wavelengths of a geometry stayed in the held-out fold; p and s were retained as separate inputs/outputs. Six development-only committee checkpoints (CNN/MLP, seeds 17/29/43) were created in the runtime directory and are excluded from Git.

Mean fold metrics:

| model | eta(+1) MAE / RMSE | all transmitted-order MAE | T MAE | R MAE | directionality MAE |
|---|---:|---:|---:|---:|---:|
| CNN | 0.06938 / 0.07975 | 0.07054 | 0.08601 | 0.07195 | 0.30740 |
| MLP | 0.13496 / 0.14344 | 0.07431 | 0.07173 | 0.07373 | 0.23674 |
| LF-DFT | 0.26537 / 0.27052 | 0.10411 | 0.08997 | 0.08980 | 0.39696 |

Worst held-out eta(+1) geometry: CNN `K6X_D130_D145_D155_D180_D195_D230` (0.12377); MLP `K6X_D100_D110_D115_D220_D225_D230` (0.45302). M1 comparison is descriptive only: M1 used 66 rows/3 geometry folds while M3 uses 198 rows/9 folds, so no percentage improvement claim is made.

## D. Paired p/s diagnostic

The 9-geometry paired audit contains 99 p/s pairs per metric and retains p/s separately. Classification remains `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; no p=s equivalence claim was made. Aggregate max/mean/median absolute differences are:

| metric | max | mean | median |
|---|---:|---:|---:|
| T | 0.47847 | 0.09881 | 0.06017 |
| R | 0.47954 | 0.09835 | 0.05864 |
| eta(+1) | 0.39135 | 0.07212 | 0.03662 |
| eta(0) | 0.54993 | 0.07034 | 0.01131 |
| eta(−1) | 0.05477 | 0.01088 | 0.00556 |
| directionality | 0.84904 | 0.09426 | 0.01207 |

## E. Runtime and cost

Batch1 accounting includes 13 physical solver invocations: 12 accepted executions, one lost infrastructure execution, and one controlled replacement. Engine runtime (seconds) was count 13, min 880.46, median 5075.98, mean 7232.46, p90 14436.97, max 16145.66. Accepted total wall-clock was count 12, min 886.72, median 4164.53, mean 7254.85, p90 14505.77, max 16153.20. Long tails include G01-P (~4.49 h), G03-P, and the G04-P replacement.

Using accepted total wall-clock median-to-p90 as an experience-only serial interval, paired geometry additions imply:

| added geometries | solver cases (p/s) | interval |
|---:|---:|---:|
| 4 | 8 | 9.3–32.2 h |
| 6 | 12 | 13.9–48.4 h |
| 8 | 16 | 18.5–64.5 h |

These are planning intervals, not a new solver authorization, and do not include concurrency assumptions.

## F. Decision

The 9-geometry set remains PILOT. The evidence supports continuing geometry diversity rather than declaring a model plateau. M3 is pilot-training-authorized only; bulk MDC-compatible training remains false, real training remains false, and Batch2 was not started. The next active-learning decision must be made by Chart/user authority.

## G. Safety and verification

- M3-stage FDTD run invocations: 0; LumAPI run invocations: 0; sealed-target reads: 0.
- A read-only live process audit found no M3-related process. Unrelated external Ansys/MDC processes were observed and left untouched.
- Standalone validator: PASS; stage-specific pytest: 5 passed; frozen M1/M2 relevant tests: 16 passed.
- One historical G04 controlled-recompute test retains a pre-existing assertion expecting a later ledger to be `entered=false`; it was not modified and is outside this M3 stage.
- Evidence directory: `outputs/np_k6_m3_pilot_retraining_v1/`
- Report: `docs/np_k6_m3_pilot_retraining_v1.md`
