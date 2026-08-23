# NP K6 final freeze and coupling handoff closeout v1

## Status

`NP_K6_FROZEN_FORWARD_PROVIDER_COUPLING_HANDOFF_READY`

## Frozen normal-incidence provider

Provider: `NP_K6_NORMAL_INCIDENCE_SCREENING_PROVIDER_V1`. Scope is `u_x = 0`, `k_y = 0`, explicit P/S, and 445–455 nm. The authority contains 22 geometries, 44 paired P/S logical cases, and 484 exact spectral rows. Ranking uses `LF_only / ensemble_raw`; spectral estimation uses `LF_ridge_residual / ensemble_raw`. These are distinct provider components, not a single universal surrogate.

## Capability boundary

Supported: geometry ranking, coarse screening, and normal-incidence spectral estimation. Not supported: FDTD replacement, quantitative coupled-device prediction, angular generalization, Jones-matrix prediction, or integrated MDC–NP truth.

## Angular coupling handoff

The frozen sparse angular calibration contains 55 rows across five logical cases: ALT1 at `u_x = +0.2241379310` S, `+0.3786893999` P/S, and `-0.3786893999` P/S. The `+0.2241379310` P case remains unresolved and is not truth; no attempt 003 is authorized. `u_x = -0.4827586206` remains a Rayleigh stress test only and is not a quantitative anchor.

Contract: `NP_K6_COUPLING_HANDOFF_CONTRACT_V1`. Recommended use is RCWA baseline + sparse FDTD calibration + coupling residual learning.

## Archived development state

- Normal-incidence HF expansion: FROZEN
- Standalone surrogate optimization: FROZEN
- External HF: HOLD
- Inverse design: NOT STARTED

## Zero-compute audit

This closeout performs freeze/audit/handoff only: new FDTD = 0, new RCWA = 0, new training = 0, external HF = 0, inverse = 0, and data regeneration = 0.
