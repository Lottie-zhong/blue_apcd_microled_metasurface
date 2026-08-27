# BF04 local redesign conditional truth audit

Status: PASS. Four authorized conditional current-Native-M1 FDTD entries completed; no additional candidate or next phase was run.

The conditional test evaluates repeatability of the I03 local mechanism. BF04 and I01-I04 are read from their frozen initial truth artifacts; C01/C02 are the only new solver truth. Ranking is scientific lexicographic ordering with no composite score.

| Rank | Candidate | MDC DoLP | MDC axis-free useful LP | FWHM psi span (deg) | FWHM DoLP worst | U1 overlap worst | U1 drift max (deg) | Promising |
|---:|---|---:|---:|---:|---:|---:|---:|:---:|
| 1 | BF04R_I03 | 0.623701 | 0.483545 | 5.024438 | 0.334085 | 0.982726 | 10.664927 | YES |
| 2 | BF04R_C01 | 0.615761 | 0.479364 | 14.532987 | 0.155064 | 0.939529 | 20.027357 | YES |
| 3 | BF04R_C02 | 0.585115 | 0.482659 | 8.226128 | 0.050145 | 0.698566 | 45.687922 | NO |
| 4 | BF04R_I04 | 0.419054 | 0.479223 | 0.405904 | 0.204456 | 0.004879 | 89.720449 | NO |
| 5 | BF04R_I02 | 0.326614 | 0.468725 | 1.899183 | 0.045004 | 0.028224 | 88.382665 | NO |
| 6 | BF04R_I01 | 0.521554 | 0.480519 | 40.221122 | 0.037783 | 0.642613 | 50.013073 | NO |

## Conditional interpretation

- C01 (reduced D): retains the complete promising phenotype; its measured DoLP is 0.615761 and U1 overlap worst is 0.939529.
- C02 (small theta perturbation): fails the complete promising criteria; this is the high-delta-theta-alone counterfactual.
- I03 remains supported as the locally positive increased-Delta_A lever.
- Local-basin classification: `I03_LOCAL_BASIN_CONFIRMED`.

Recommended next phase: `PROMOTE_LP_CANDIDATE_TO_INTEGRATED_SOURCE_CLOSURE`. This recommendation is not an execution authorization.

The complete S1/S2/S3 trajectories and 31-point spectra remain in each candidate metrics JSON/CSV; frozen initial files are referenced, not rewritten.

Solver accounting: 4 authorized, 4 entered, 4 returned, 4 V2-valid, replay 0, RCWA 0, ML 0. Fluent was not modified.
