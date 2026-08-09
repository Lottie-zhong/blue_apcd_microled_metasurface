# MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1

## Frozen status

This fixed-v2 MDC model is **TRAINED_AND_EXTERNALLY_EVALUATED** with Test40 scope **RANKING_SCREENING_ONLY**. Source commit: `382a73f4e561da8bb7fe36eabccbc1be587f4095`; model-lock commit: `489b54e43bbf2c08ce030a945b9d4b70ee7550f2`. Five-seed ensemble: `20260804, 20260805, 20260806, 20260807, 20260808`; PCA representation: `PCA32`.

## What it may support

Use the predicted joint profile and spectral/angular marginals only for qualitative shape screening, profile-shape similarity, exploratory NP weighting, and prioritizing direct 2D FDTD. Peak/FWHM/cone are auxiliary screening metadata.

## What it must not claim

It is not a quantitative HF surrogate, FDTD replacement, absolute-power predictor, extraction-efficiency predictor, Purcell predictor, or full 3-D device surrogate. Predicted power is `NOT_QUANTITATIVELY_USABLE`; do not expose it as `validated_relative_power`.

## MDC-NP route

Stage A uses `W_pred(lambda, ux)` only in a dimensionless `shape_overlap_score`, without multiplying predicted M1 power. Stage B requires direct Native-M1 FDTD confirmation and then permits `LEVEL1_ONE_WAY_INCOHERENT_POWER`; Level 2 integrated full-wave remains required for a final device claim.

## Test40 provenance

Selection timing: `POST_MODEL_LOCK_PRE_LABEL_PRE_PREDICTION`; selection type: `OUTCOME_BLIND_STRATIFIED_EXTERNAL_HOLDOUT`; identity: `TEST40_CASE_UID_V1`; DOE96 case-hash inheritance: `NOT_USED`. Test40 is not to be called preregistered, retrained, recalibrated, or reevaluated in this closure task.
