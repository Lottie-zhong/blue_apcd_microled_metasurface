# Paper A LP rescue RCWA screening

## Status

- Verdict: `PAPER_A_LP_RCWA_RESCUE_FAIL_NO_FDTD_PROMOTION`
- RCWA calibration: `RCWA_SCREENING_NOT_CALIBRATED`
- New FDTD: 0; future FDTD promotion budget: 0
- Frozen prior conclusions unchanged: intrinsic Gate A failure, MDC-weighted Gate A-prime failure, `FROZEN_NOT_PROMOTED`

## Contract and provider

This zero-new-FDTD screen used Native-M1 dispersive materials, normal-incidence full Jones RCWA, order-resolved reflected/transmitted power, 430-470 nm source span, and 435-465 nm at 1 nm (31 points). Phase/K6 criteria were not used. The provider was pure-Python `grcwa`; no RCWA license was required.

## Required calibration answers

1. **Did RCWA pass calibration against existing current-Native FDTD truth?** No. The controls reproduce the qualitative low-DoLP/state-flip pattern, but harmonic convergence fails at the tested 49/121/225 settings, so the calibration gate is not passed.
2. **Is `GLOBAL_018` promoted as worth future FDTD?** No. No rescue candidate may be promoted after failed calibration.
3. **Is `H1C1B_V2_012` promoted as worth future FDTD?** No. No rescue candidate may be promoted after failed calibration.
4. **Do rescue screens show an MDC-main-region state flip?** Yes, both `GLOBAL_018` and `H1C1B_V2_012` show a screen-only main-region flip; these values are not a calibrated promotion basis.
5. **Future FDTD promotion budget:** 0.

## Control calibration

| Candidate | FDTD weighted DoLP | RCWA weighted DoLP | FDTD flip | RCWA flip | qualitative match |
|---|---:|---:|---:|---:|---:|
| H1C1B_V2_009 | 0.3700 | 0.2704 | True | True | True / True |
| H1C1B_V2_010 | 0.3777 | 0.1725 | True | True | True / True |
| H1C1B_V2_015 | 0.3170 | 0.1379 | True | True | True / True |

Calibration is **not** accepted because convergence is a prerequisite, even though the three controls qualitatively match the low-DoLP/state-flip failure pattern.

## Harmonic convergence

Screening tolerance was last-order delta <= 0.05 complex-Jones, 0.03 DoLP, and 0.03 useful power.

| Candidate | max complex-Jones delta | max DoLP delta | max useful-power delta | pass |
|---|---:|---:|---:|---:|
| H1C1B_V2_009 | 0.2951 | 0.1590 | 0.0877 | False |
| H1C1B_V2_010 | 0.3251 | 0.2905 | 0.1533 | False |
| H1C1B_V2_015 | 0.9506 | 0.1329 | 0.1017 | False |
| GLOBAL_018 | 0.3942 | 0.2787 | 0.0202 | False |
| H1C1B_V2_012 | 0.5944 | 0.3375 | 0.1284 | False |

All five candidates fail at least one convergence tolerance, and the complex Jones/DoLP deltas remain materially above tolerance.

## Rescue screen-only diagnostics

These metrics are diagnostic only and cannot promote a rescue candidate because calibration failed.

| Candidate | MDC weighted DoLP | useful power | x fidelity | main-region flip | FWHM DoLP |
|---|---:|---:|---:|---:|---:|
| H1C1B_V2_009 | 0.2704 | 0.2143 | 0.3649 | True | 0.1934 |
| H1C1B_V2_010 | 0.1725 | 0.2719 | 0.4138 | True | 0.1217 |
| H1C1B_V2_015 | 0.1379 | 0.3386 | 0.4311 | True | 0.1844 |
| GLOBAL_018 | 0.0228 | 0.3231 | 0.5097 | True | 0.0544 |
| H1C1B_V2_012 | 0.1744 | 0.3224 | 0.4128 | True | 0.2195 |

## Existing-FSP reuse audit

The five existing candidate FSPs were read-only audited. They match the current geometry, Native-M1, periodic x/y boundaries, PML z boundaries, mesh, substrate/superstrate convention, and x/y state structure. They are reusable templates, not direct formal-broadband results: their historical source/monitor coverage is 450-454 nm with 9 points. A future authorized FDTD would copy rather than overwrite the immutable historical FSP and minimally patch source/monitor coverage to 430-470 nm / 41 points. No such FDTD was authorized or started here.

## RCWA cap-3 production observation

Real screening workload reached peak active RCWA = 3, with controls run concurrently and all five cases returned. FDTD processes and scheduler state were sampled read-only; no FDTD slot or solver was modified. No license interference occurred because `grcwa` is pure Python. No starvation was observed in the samples, but no before/after runtime baseline was available, so this is not a quantitative slowdown claim. The permanent cap-3 authority was recorded at `D:\project\apcd_global_rcwa_scheduler_authority_v1.json`.

## Scope guard

No new geometry search, FDTD, CP, angular sweep, integrated closure, ML, K6, or other Paper A physics stage was started. The frozen current conclusions remain unchanged.
