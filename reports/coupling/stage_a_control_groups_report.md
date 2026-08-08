# APCD MDC-NP Coupling V1 Stage-A control-group report

## ??

PASS. B0/B1/B2 each entered exactly once and completed; B3 is prior golden fixture read-only. B0 required post-FSP save recovery from existing monitor results after a relative-path save error; no solver replay occurred.

## Control results

| Case | Stack | R | T | residual | eta(+1) | eta(0) | eta(-1) | directionality |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | GaN/Air | 0.049629854919 | 0.459657673045 | 0.490712472036 | N/A | N/A | N/A | N/A |
| B1 | GaN/ZL1/Air | 0.030232469200 | 0.506682694147 | 0.463084836652 | N/A | N/A | N/A | N/A |
| B2 | GaN/79nm SiO2/RUN3A/Air | 0.076168880262 | 0.401887474698 | 0.521943645040 | 0.360914347823 | 0.005432901766 | 0.004438647527 | 0.987851071201 |
| B3 | GaN/ZL1/RUN3A/Air | 0.115330140299 | 0.332909083774 | 0.551760775927 | 0.290305555168 | 0.008603709728 | 0.003159508023 | 0.989233784802 |

NP_R0 standalone: eta(+1)=0.745970692811, eta(0)=0.010478489513, eta(-1)=0.005755124074, directionality=0.992344118101; authoritative R/T are N/A in the reference artifact.

Order closure passed for all three new cases; B0/B1 nonzero orders are numerical leakage only.

## Attribution

- MDC-only B1-B0: ?R=-0.019397385719, ?T=0.047025021103, ?residual=-0.027627635384; transmitted m=0 changes from 0.459657673045 to 0.506682694147.
- Finite-support B2-NP_R0: ??(+1)=-0.385056344987, ??(0)=-0.005045587747, ??(-1)=-0.001316476547, ?directionality=-0.004493046900.
- Full-MDC B3-B2: ??(+1)=-0.070608792656, ??(0)=0.003170807962, ??(-1)=-0.001279139504, ?directionality=0.001382713601.
The +1 reduction is already substantial from the finite support/GaN environment (B2 versus NP_R0), with an additional reduction from the full MDC underlayer (B3 versus B2).

## Reusable framework

Declarative control fixture, generic joint builder, common setup builder/readback gate, control runner, post-FSP audit, common order extractor/result schema, and comparison engine are implemented. B0/B1 absence and B2 support/pillar presence are validated by tests.

## Safety / Git

FDTD: 3 authorized, 3 entered, 3 completed, 0 replays. TMM/RCWA/FEM/training/sweeps/y-pol/oblique/broadband: 0. Generated FSP/raw arrays remain untracked artifacts.

## ???

`REQUEST_STAGE_A_SPACER_SENSITIVITY_AUTHORIZATION`
