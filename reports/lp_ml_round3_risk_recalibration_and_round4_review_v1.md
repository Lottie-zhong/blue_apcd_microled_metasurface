# LP ML Round-3 risk recalibration and Round-4 planning review v1

## Status

`LP_ML_ROUND3_RECALIBRATED_POOL_READY_FOR_INVERSE_FDTD_PLANNING`

## Round-3 accounting

127 entered / 126 unique / 1 duplicate / 121 accepted / 6 quarantined geometries / 58 complete geometries / 522 admitted rows. Duplicate accounting and all failed evidence are preserved.

## Low-dispersion high-error root cause

Forensic cohort size=27 rows; dispersion threshold=0.315594; error p90 threshold=0.104566. Causes are classified in the forensic CSV/JSON without rewriting physics.

## Calibrated risk model

Monotone bounded-linear rank calibration uses 56 train/validation geometries and excludes frozen tests. Features: seed_dispersion, raw_jones_disagreement, nearest_training_distance, local_density_gap, local_gradient_norm, quantization_sensitivity, wavelength_endpoint_disagreement, manufacturing_boundary_proximity. Risk is an interpretable score, not a probability.

## Calibration performance

Geometry-grouped CV calibrated rank correlation=0.589 vs dispersion-only=-0.178; calibrated high-error low-risk=1 vs dispersion-only=11; calibrated risk classes=['HIGH', 'LOW', 'MODERATE'].

## Per-bin recalibrated risk counts

{
  "0": {
    "CALIBRATED_LOW_RISK": 19,
    "CALIBRATED_MODERATE_RISK": 40,
    "CALIBRATED_HIGH_RISK": 0
  },
  "1": {
    "CALIBRATED_LOW_RISK": 62,
    "CALIBRATED_MODERATE_RISK": 138,
    "CALIBRATED_HIGH_RISK": 63
  },
  "2": {
    "CALIBRATED_LOW_RISK": 1,
    "CALIBRATED_MODERATE_RISK": 19,
    "CALIBRATED_HIGH_RISK": 35
  },
  "3": {
    "CALIBRATED_LOW_RISK": 3,
    "CALIBRATED_MODERATE_RISK": 18,
    "CALIBRATED_HIGH_RISK": 24
  },
  "4": {
    "CALIBRATED_LOW_RISK": 3,
    "CALIBRATED_MODERATE_RISK": 10,
    "CALIBRATED_HIGH_RISK": 33
  },
  "5": {
    "CALIBRATED_LOW_RISK": 14,
    "CALIBRATED_MODERATE_RISK": 25,
    "CALIBRATED_HIGH_RISK": 1
  }
}

## Tuple result

Recalibrated tuple front count=103 (existing combinations considered=749); non-all-high-risk tuple=present.

## Round-4 necessity

Outcome=LP_ML_ROUND3_RECALIBRATED_POOL_READY_FOR_INVERSE_FDTD_PLANNING. No Round-4 solver is run or authorized in this task. Optional plan path=none.

## Hard gates

No solver/FDTD, no physics/split/normalization/checkpoint rewrite, no geometry054/K6/cVAE, no new degree of freedom, and protected reports unchanged.
