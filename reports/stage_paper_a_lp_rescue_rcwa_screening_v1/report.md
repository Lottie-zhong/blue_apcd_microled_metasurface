# Paper A LP rescue RCWA scientific-authority correction

## Status

- Current RCWA scientific authority: `SUPERSEDED_BY_RCWA_CALIBRATION_FAILURE`
- RCWA calibration remains: `RCWA_SCREENING_NOT_CALIBRATED`
- Zero-solver correction: no FDTD, RCWA, or other solver started
- Paper A scope remains: `FROZEN_NOT_PROMOTED`

## Authority correction

The prior `PAPER_A_LP_RCWA_RESCUE_FAIL_NO_FDTD_PROMOTION` verdict is superseded. The RCWA provider failed harmonic/Jones convergence and therefore cannot formally promote or reject `GLOBAL_018` or `H1C1B_V2_012`.

The observed MDC-main-region state flips for both rescue candidates are retained only as `RCWA_NEGATIVE_INDICATION_ONLY`. They are not FDTD-confirmed failures, production rejections, or scientific vetoes.

## Restored forensic authority

The prior formal forensic batch authority is restored:

`PAPER_A_LP_FORENSIC_RESCUE_BATCH1_READY`

Primary candidates:

- `GLOBAL_018`
- `H1C1B_V2_012`

Current state:

`PAPER_A_LP_RESCUE_STATE = BATCH1_FDTD_TRUTH_PENDING_RESOURCE_AND_USER_AUTHORIZATION`

Future truth budget is at most 4 FDTD jobs: 2 geometries x/y. Current admission is not authorized and current FDTD started = 0.

## Paper A scope guard

The 009/015/010 intrinsic Gate A failure and MDC-weighted Gate A-prime failure remain valid. This correction does not reopen Paper A, does not erase the frozen `FROZEN_NOT_PROMOTED` status, and does not authorize CP, angular sweep, ML, geometry search, or any other follow-on physics stage.

## RCWA scheduling authority

Scientific calibration failure is kept separate from scheduler concurrency success. The real observation reached peak active RCWA = 3, with no license hard gate, no observed FDTD starvation in read-only sampling, and stable controller/registry behavior. Therefore retain:

- `CURRENT_PRODUCTION_RCWA_SCHEDULING_CAP = 3`
- `RCWA_BRANCH_LOCAL_CAP = 3`
- `APCD_GLOBAL_RCWA_SCHEDULING_POLICY_V1_PERMANENT_CAP3_COMPLETE`

The cap-3 authority was not rolled back.

## Frozen prior conclusions

- `PAPER_A_GATE_A_FAIL_LP_BROADBAND_INSUFFICIENT`
- `PAPER_A_GATE_A_PRIME_FAIL_LP_ROUTE_FREEZE`
- `CURRENT_PAPER_A_SCOPE_STATUS = FROZEN_NOT_PROMOTED`
