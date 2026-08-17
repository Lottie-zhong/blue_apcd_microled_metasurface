# Paper A LP RCWA full-Jones calibration rescue

## Status

- Final verdict: `PAPER_A_LP_RCWA_FULLJONES_CALIBRATION_FINAL_FAIL`
- Provider authority: `PAPER_A_LP_RCWA_PROVIDER = NOT_QUALIFIED_FOR_FULLJONES_RESCUE_SCREENING`
- RCWA calibration: `RCWA_SCREENING_NOT_CALIBRATED`
- New FDTD / geometry / ML: 0

## What was audited

The three existing current-Native FDTD controls were used as calibration authority: `H1C1B_V2_009`, `H1C1B_V2_010`, and `H1C1B_V2_015`. The audit checked the FSP geometry, 432 nm period, 550 nm patterned layer, Native-M1 label, periodic x/y boundaries, air background, source direction, monitor plane, transmitted order, and the stored RCWA Jones/power provenance.

The formal transmitted target is the specular `(m,n)=(0,0)` order. The existing order-resolved artifact reports no other propagating orders in 435-465 nm, so total-power closure is not the primary order-selection error in the formal range.

## Why energy closure did not establish calibration

The RCWA `R+T` closure is excellent, but it only validates power bookkeeping. It does not prove a common complex phase reference, x/y basis and handedness, exact geometry-to-grid rotation/offset mapping, or matching amplitude normalization. The FDTD T/field plane is at z approximately 1000 nm; the prior RCWA spectra do not record a common output plane or propagation-phase correction. Therefore direct complex-Jones identity remains unestablished.

## Finite harmonic ladder

The completed real RCWA control ladder is retained as: pre-level diagnostic 49 harmonics, Level-0 current 121 harmonics, and Level-1 next 225 harmonics. The ladder is stopped after Level-1 because the adjacent 121-to-225 changes remain material; no indefinite harmonic increase is attempted.

For controls, the maximum adjacent changes are:

| Candidate | max complex-Jones delta | max DoLP delta | max useful-power delta |
|---|---:|---:|---:|
| H1C1B_V2_009 | 0.2951 | 0.1590 | 0.0877 |
| H1C1B_V2_010 | 0.3251 | 0.2905 | 0.1533 |
| H1C1B_V2_015 | 0.9506 | 0.1329 | 0.1017 |

These are not production-screening convergence. Jones-derived orientation and state-flip location are likewise not stable enough to seal a provider calibration.

## FDTD qualitative comparison

The controls qualitatively reproduce low-DoLP and state-flip warnings, but this is insufficient: the complex-Jones provider is not converged and the physics identity audit is incomplete. No rescue candidate receives a formal RCWA promotion or rejection.

## Stop-loss and restored authority

The RCWA provider is permanently frozen for full-Jones rescue screening. The previous RCWA rejection is not used as scientific authority. The restored authority is:

`PAPER_A_LP_FORENSIC_RESCUE_BATCH1_READY`

Primary candidates remain `GLOBAL_018` and `H1C1B_V2_012`. Their truth state is:

`PAPER_A_LP_RESCUE_STATE = BATCH1_FDTD_TRUTH_PENDING_RESOURCE_AND_USER_AUTHORIZATION`

Future truth budget is at most 4 current-Native FDTD jobs (2 geometries x/y), but no FDTD is started or automatically authorized.

## Scope and scheduler guard

`CURRENT_PAPER_A_SCOPE_STATUS = FROZEN_NOT_PROMOTED` remains unchanged because the 009/015/010 intrinsic Gate A and MDC-weighted Gate A-prime failures remain valid. CP, angular sweep, ML, geometry search, and additional LP RCWA screening are not started.

The real RCWA observation reached peak active RCWA = 3. The scheduler result remains independent of the scientific failure:

- `CURRENT_PRODUCTION_RCWA_SCHEDULING_CAP = 3`
- `RCWA_BRANCH_LOCAL_CAP = 3`
- `APCD_GLOBAL_RCWA_SCHEDULING_POLICY_V1_PERMANENT_CAP3_COMPLETE`
