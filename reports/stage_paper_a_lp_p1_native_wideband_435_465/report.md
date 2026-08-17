# Paper A LP Gate A-prime MDC Source-Weighted Viability

## Verdict

PAPER_A_GATE_A_PRIME_FAIL_LP_ROUTE_FREEZE

Zero-solver salvage gate. The frozen intrinsic result remains PAPER_A_GATE_A_FAIL_LP_BROADBAND_INSUFFICIENT for the flat 435-465 nm Native-M1 window and is not reclassified as broadband PASS.

## MDC source authority

The weighting uses real FDTD output for ZL-1 alternative (P1_ZL1_ALTERNATIVE_G3_A3), field r12_normalized_output, normalization fixed_physical_r12nm_box. Weights are normalized within the real 435-465 nm overlap and do not represent absolute emitted power.

- Source grid: 420-480 nm, 301 points at 0.2 nm
- MDC FDTD peak: 447.8 nm
- MDC FDTD output FWHM: 18.7821 nm
- Relative source weight inside 435-465 nm: 0.633468
- Effective weighted center: 448.036 nm
- Effective weighted sigma: 7.444 nm
- Formal LP weights: 31 points, max point weight 0.053894

## Source-weighted coherency comparison

| Candidate | DoLP weighted | Useful LP weighted | x-fidelity weighted | Leakage fraction | DoLP in MDC-FWHM | Gate A-prime |
|---|---:|---:|---:|---:|---:|---|
| H1C1B_V2_009 | 0.369997 | 0.381170 | 0.684951 | 0.315049 | 0.425839 | FAIL |
| H1C1B_V2_015 | 0.317001 | 0.441897 | 0.658478 | 0.341522 | 0.417787 | FAIL |
| H1C1B_V2_010 | 0.377728 | 0.397275 | 0.688602 | 0.311398 | 0.465175 | FAIL |

Formal results sum Stokes/coherency components, not w-weighted per-wavelength DoLP. Per-wavelength Stokes and all 31 weights are preserved in mdc_weighted_lp_stokes.csv.

## Window diagnostics

The continuous MDC-FWHM window is 438.409-457.191 nm and uses LP formal points 439-457. The 440-460 nm and 443-457 nm diagnostics are in the gate JSON and do not alter the intrinsic 435-465 nm verdict.

All three candidates show x-state sign flip within the MDC-FWHM formal points. Leakage is not dominant by weighted mass and no result is supported by a single 1-nm point; the decisive failure is polarization purity/state stability.

## Decision

No candidate satisfies the numerical thresholds together with the state-sign requirement. No source-weighted primary or runner-up is frozen. Freeze/re-scope review is required: do not reopen LP geometry search, expand FDTD, restore K6, start LP angular sweep, or start integrated closure. The MDC coupling branch remains independent and unmodified.
