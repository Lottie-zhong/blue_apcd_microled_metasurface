# APCD MDC-NP Coupling V1 Stage-A spacer sensitivity report

## ??

PASS. S79/S158/S237 each entered and completed exactly once; existing t_extra=0 B3 was read-only. No replay occurred. Formal state: `STAGE_A_SPACER_SENSITIVITY_COMPLETE`.

## Spacer results

| Case | t_extra (nm) | total SiO2 separation (nm) | R | T | residual | eta(+1) | eta(0) | eta(-1) | theta(+1) | directionality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B3_TEXTRA0 | 0 | 79 | 0.115330140299 | 0.332909083774 | 0.551760775927 | 0.290305555168 | 0.008603709728 | 0.003159508023 | 14.988234482305 | 0.989233784802 |
| S79 | 79 | 158 | 0.054772508789 | 0.432451253529 | 0.512776237682 | 0.374984608207 | 0.002055220737 | 0.000412684190 | 14.988234482305 | 0.998900673504 |
| S158 | 158 | 237 | 0.098083895645 | 0.359364940556 | 0.542551163799 | 0.310756400068 | 0.007288291081 | 0.001772531953 | 14.988234482305 | 0.994328422839 |
| S237 | 237 | 316 | 0.054402359726 | 0.432279604702 | 0.513318035572 | 0.378139777787 | 0.000272468720 | 0.000467083005 | 14.988234482305 | 0.998766311302 |

NP_R0 reference: eta(+1)=0.745970692811, directionality=0.992344118101; authoritative R/T are N/A.

## Physical attribution

- S79 vs t0: ??(+1)=0.084679053040, ?T=0.099542169755, ?R=-0.060557631510, ?directionality=0.009666888702.
- S158 vs t0: ??(+1)=0.020450844900, ?T=0.026455856782, ?R=-0.017246244654, ?directionality=0.005094638037.
- S237 vs t0: ??(+1)=0.087834222619, ?T=0.099370520928, ?R=-0.060927780573, ?directionality=0.009532526500.
The response is non-monotonic: S79 and S237 recover +1 power, while S158 falls back. The gain is accompanied by higher T and lower R/residual for S79/S237, with order redistribution including m=+2 and other higher orders. Directionality remains high and improves relative to t0; this supports phase/interference sensitivity rather than simple attenuation.

## Candidate decision

BEST_450NM_SPACER_CANDIDATE: `S237`, t_extra=237 nm, eta(+1) gain versus t0 = 0.087834222619. This is only a single-point 450 nm screen; `FINAL_SPACER_FREEZE` is false and 445-455 nm x-pol narrowband confirmation is required.

## Framework / safety / Git

The same declarative fixture, generic builder, runner, monitor setup, order extractor, result schema, comparison engine, mutation audit and provenance registry were reused. Tests and all setup/post-FSP gates passed. FDTD entered/completed/replay = 3/3/0; other solver/training/sweep modes = 0. FSP/raw arrays remain untracked.

## ???

`REQUEST_STAGE_A_445_455_XPOL_SPACER_CONFIRMATION_AUTHORIZATION`
