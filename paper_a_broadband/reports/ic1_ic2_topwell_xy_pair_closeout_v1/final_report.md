# IC1 + IC2 top-well incoherent pair closeout

## Status

- IC1: `VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH`
- IC2: `VALID_FOR_IC2_INTEGRATED_TRUTH`
- Pair contract: `PASS`
- Pair verdict: `PAPER_A_IC2_PAIR_PHYSICS_VALID_BUT_LP_WEAK`

## Combination

Equal incoherent source weights were used: `w_x = 0.5`, `w_y = 0.5`. Stokes/coherency and source-normalized powers were combined; electric fields were not added, and DoLP/psi were not averaged.

## 450 nm anchor

- S0/S1/S2/S3 (sourcepower-normalized): `3.64790879e+00` / `1.12370656e-01` / `8.03998523e-02` / `-6.09035445e-02`
- DoLP: `0.03787684`
- psi: `17.79163215 deg`
- DoCP: `-0.01669547`
- useful axis-free LP: `1.89304003e+00`
- upward/source-normalized power: `7.39292200e-03`
- far-field center-direction DoLP/psi/DoCP: `0.22183357` / `101.62028163 deg` / `0.09296034`

## Broadband pair

- DoLP mean / worst: `0.04271630` / `0.00338719` at `425.000 nm`
- useful LP mean / worst: `2.00035717e+00` / `1.40275415e+00`
- max absolute DoCP: `0.01819330`
- maximum circular psi step: `84.30566970 deg`
- upward/source-normalized power mean / worst: `8.23679369e-03` / `6.29938713e-03`

Far-field intensity grid identity and finiteness passed. The preserved far-field artifact supports angular intensity and the validated center-direction Ex/Ey sample; it does not contain Ex/Ey polarization arrays for every angular pixel, so no full-angle polarization claim is made.

`W_emit = UNRESOLVED_FOR_PRODUCTION_CLOSURE`; no production emitter-weighted metric, absolute LEE, or full-device performance is claimed.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called_delta=0`, `solver_entered_delta=0`, `RCWA=0`, `ML=0`, `replay=0`.
