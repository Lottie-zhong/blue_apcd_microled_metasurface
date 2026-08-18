# Paper A LP forensic FDTD truth Batch 1

- Status: **PAPER_A_LP_FORENSIC_FDTD_RESCUE_FINAL_FAIL**
- Current Native-M1; existing candidate-specific FSP reused as immutable parents.
- Source/monitor span: 430-470 nm; formal extraction: 435-465 nm, 1 nm, 31 points; 450 nm anchor.
- Full x/y truth: GLOBAL_018 and H1C1B_V2_012; 4/4 authorized FDTD jobs entered and accepted.
- MDC weighting: frozen ZL-1 alternative `r12_normalized_output`, normalized over the true 435-465 nm overlap; no absolute emitted-power claim.
- Coherency/Stokes integration was performed before DoLP; phase/K6 were not used for qualification.

## Source-weighted result

| candidate | weighted DoLP | useful LP power | x fidelity | main-region flip | gate |
|---|---:|---:|---:|---|---|
| GLOBAL_018 | 0.086764 | 0.373006 | 0.543145 | True | False |
| H1C1B_V2_012 | 0.289710 | 0.433180 | 0.644791 | True | False |

## Interpretation

The MDC 435-465 nm overlap fraction is 0.632688; effective center 448.004081 nm and sigma 7.678338 nm. The rescue gate requires weighted DoLP >= 0.80, useful LP >= 0.35, x-fidelity >= 0.85, no main-region target-channel flip, and non-single-point support.

The original intrinsic 435-465 nm LP failure remains unchanged. A failed rescue keeps Paper A LP frozen; it is not an RCWA veto and does not authorize further solver work.
