# Paper A LP Branch Final Freeze — 2026-08-17

## Status

FROZEN_NOT_PROMOTED

This is a documentation-only freeze. Solver budget is 0; no FDTD, RCWA, ML, geometry search, CP, angular sweep, or integrated closure was started.

## Evidence chain

P0 historical rerank was retained only as an overlap cross-check. P1 current Native-M1 truth: candidates H1C1B_V2_009, H1C1B_V2_015, and H1C1B_V2_010, evaluated over 435-465 nm at 1 nm with 31 points and six real x/y FDTD jobs.

Gate A intrinsic result: PAPER_A_GATE_A_FAIL_LP_BROADBAND_INSUFFICIENT.

Gate A-prime MDC-conditioned check: the final zero-solver evaluation used frozen ZL-1 alternative real FDTD r12 spectral weighting. Gate A-prime result: PAPER_A_GATE_A_PRIME_FAIL_LP_ROUTE_FREEZE.

## Frozen quantitative evidence

| Candidate | MDC-weighted DoLP | MDC-FWHM DoLP | State flip |
|---|---:|---:|---|
| H1C1B_V2_009 | 0.3700 | 0.4258 | true |
| H1C1B_V2_015 | 0.3170 | 0.4178 | true |
| H1C1B_V2_010 | 0.3777 | 0.4652 | true |

MDC weighted effective center: approximately 448.036 nm; effective sigma: approximately 7.444 nm; 435-465 overlap fraction: approximately 0.6335.

The failure is located within the MDC main energy range, not only at remote spectral edges. The primary physical bottleneck is POLARIZATION_STATE_SPECTRAL_INSTABILITY, not THROUGHPUT_ONLY_FAILURE.

## Scope ruling

Paper A is FROZEN_NOT_PROMOTED. It must not automatically continue to new LP geometry search, LP-ML, inverse design, K6, six-phase, grouped-D, J1 rescue, angular sweep, integrated dipole closure, fabrication sweep, additional spectral solver, or Native-M1 CP solver. Frozen CP assets are retained but not executed. A future restart requires an explicit new paper scope decision.

The Coupling/NP branch is independent and was not modified by this freeze.
