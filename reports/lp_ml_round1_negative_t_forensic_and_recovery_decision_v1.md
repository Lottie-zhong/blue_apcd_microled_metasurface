# LP_ML Round-1 negative-T forensic and recovery decision

## Classification

`SINGLE_CASE_RUNTIME_FAILURE_PRIOR_DATA_CLEAN`

## Accounting

- Planned: 240 geometries / 480 subruns
- Entered: 92; accepted: 91; failed: 1
- Complete: 61 geometries (16 smoke + 45 production)
- Untouched candidates: 194
- Remaining full x/y pairs: 194
- Missing y rerun: 1
- Prospective budget if separately authorized: 389

## Negative-T audit

All 123 accepted checkpoints were scanned. Accepted cases have finite weighted fields, exact nine-point wavelength vectors, matching geometry hashes, Native-M1/configuration gates, and no non-positive T. The failed y case has no raw T vector, raw weighted fields, checkpoint, or FSP, so its root cause remains `INDETERMINATE_SOURCE_EVIDENCE`. No `abs(T)`, clipping, interpolation, model fill, or physics rewrite was used.

## Recovery

`LPML_R1_GLOBAL_SOBOL_054_x` is retained as accepted. `LPML_R1_GLOBAL_SOBOL_054_y` is quarantined and not rerun. The recovery budget is offline-only and unauthorized. Partial models remain `DIAGNOSTIC_ONLY_NOT_PROMOTABLE`. Solver calls in this task: 0.

Protected hashes: `d0b9dc84dd5daa0e3144dd0e02b65b1e4228abafa6798c217a7e571e17505161`, `ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708`
