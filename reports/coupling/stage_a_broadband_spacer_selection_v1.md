# Stage-A broadband spacer selection

Scope: x-polarization, normal incidence, kx/k0=0, exact 445--455 nm at 1 nm spacing.
Only broadband rows enter ranking; monochromatic 450 nm results are diagnostic-only.

| Rank | t_extra (nm) | mean eta+1 | min eta+1 | std eta+1 | mean directionality | mean R | mean T |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 237 | 0.279281109 | 0.150288902 | 0.073141484 | 0.994785500 | 0.116053469 | 0.321223025 |
| 2 | 79 | 0.267586644 | 0.117798301 | 0.079852940 | 0.996466894 | 0.121582026 | 0.310370144 |
| 3 | 0 | 0.222587044 | 0.117479100 | 0.070294664 | 0.977691667 | 0.145723119 | 0.259068271 |

Final freeze: **237 nm** extra SiO2, total SiO2 separation **316 nm**.

All candidates passed exact-grid, order-closure, power-closure, sign, provenance, and same broadband implementation-contract checks. No solver was run by this comparison step.

Physical interpretation: T237 has the highest broadband mean and minimum eta+1 and a lower eta+1 standard deviation than T79. This is a three-candidate screen, not an interpolation or production-transfer authorization.
