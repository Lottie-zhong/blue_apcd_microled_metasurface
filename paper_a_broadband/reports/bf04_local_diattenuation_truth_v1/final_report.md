# BF04 local diattenuation redesign initial truth

Status: PASS. This is an 8-entry current-Native-M1 FDTD truth batch; no conditional case was run.

The comparison uses source-weighted coherency integration over the frozen MDC weighting and the existing axis-free LP useful-power definition `P_LP_axisfree = 0.5*(S0 + sqrt(S1^2 + S2^2))`. U1 adjacent overlap is the absolute inner product, consistent with the fixed BF04 authority. No composite score, phase criterion, K6 criterion, or data repair was used.

| Rank | Candidate | MDC DoLP | MDC axis-free useful LP | FWHM psi span (deg) | FWHM DoLP worst | U1 overlap worst | U1 drift max (deg) | Promising |
|---:|---|---:|---:|---:|---:|---:|---:|:---:|
| 1 | BF04R_I03 | 0.623701 | 0.483545 | 5.024438 | 0.334085 | 0.982726 | 10.664927 | YES |
| 2 | BF04R_I04 | 0.419054 | 0.479223 | 0.405904 | 0.204456 | 0.004879 | 89.720449 | NO |
| 3 | BF04R_I02 | 0.326614 | 0.468725 | 1.899183 | 0.045004 | 0.028224 | 88.382665 | NO |
| 4 | BF04R_I01 | 0.521554 | 0.480519 | 40.221122 | 0.037783 | 0.642613 | 50.013073 | NO |

## Mechanism interpretation

- I01 increases A_mean but does not improve the combined FWHM axis-stability/U1 reference: the DoLP gain is not sufficient for promotion.
- I02 decreases A_mean and is a counterfactual degradation in the initial truth set.
- I03 increases Delta_A and is the local promising direction: it improves source-weighted DoLP and useful LP power while meeting the frozen psi-flatness and BF04-like U1 reference comparison.
- I04 decreases/reverses Delta_A: a flatter psi alone is not sufficient because U1 stability and DoLP remain inadequate.

This is local BF04-neighborhood evidence, not a universal geometric law. C01/C02 remain unrun and require a separate scientific authorization.

Recommended zero-solver decision: `BF04_LOCAL_REDESIGN_PROMISING_CONDITIONAL_BATCH_JUSTIFIED`. Recommended candidate: `BF04R_I03`.

Solver accounting: 8 authorized new entries, 8 entered, 8 returned, 8 V2-valid; one entered case used immutable returned-run artifact recovery and was not replayed. RCWA=0, ML=0, conditional entries=0, BF04 baseline rerun=false.

Native Auto Shutoff trajectory was not captured in the controller stream. A provenance-only lifecycle record is retained for each case; V2 acceptance is based on the persisted independent instrumented time-series evidence.
