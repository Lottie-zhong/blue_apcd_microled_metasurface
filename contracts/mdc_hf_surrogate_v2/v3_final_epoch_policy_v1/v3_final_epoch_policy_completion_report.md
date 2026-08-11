# MDC HF Surrogate V3 final-epoch policy closeout

Status: `MDC_HF_SURROGATE_V3_FINAL_EPOCH_POLICY_FROZEN_200G1200C_READY_FOR_OOF_AUTHORIZATION`

Readiness is verified from the real AL64 completion metadata: DOE96 96/576, V2 Test40 40/240 and AL64 64/384, totaling 200 geometries / 1200 cases. Geometry/case identities, six-case grouping, source-position/orientation coverage, hash/grid/tensor integrity, missing/duplicate/unexpected checks and V3-Test40 overlap are PASS.

The only permitted checkpoint is the argmin of the inner-stop validation geometry-level profile-only composite over epochs 50–400. Machine-equal minima select the earliest epoch. Outer-held-out folds, power, auxiliary targets, final-development loss and V3-Test40 are forbidden.

For selected V3-A/B/C, exactly 15 valid leakage-free OOF fits (5 folds × 3 seeds) provide eligible epochs. The full-development epoch is `round_half_up(median(eligible_best_epoch_i))`, constrained to 50–400. Full-development training is fixed to 200/1200 with no validation split, early stopping or checkpoint hunting. Median 400 emits `MAX_EPOCH_SATURATION_WARNING` without automatic budget or epoch changes.

Final seed/ensemble membership is explicitly `NOT_FROZEN_PRE_FINAL_TRAINING_ITEM`; it must be separately frozen before final training and was not invented here.

This task dispatched zero solver calls, zero neural fits, zero optimizer/backward calls and zero PCA/scaler fits. V3-Test40 labels remain `NOT_GENERATED / NOT_READ`; HF15/R12 reads remain zero.
