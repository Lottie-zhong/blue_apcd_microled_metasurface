# Integrated-aware LP redesign contract v1

## Status

`INTEGRATED_LOCAL_SPACE_TOO_CONSTRAINED` — zero-solver candidate design only.

## Objective

The primary objective is simultaneous reinforcement of x/y source Stokes and angular polarization axes. No scalar composite score and no optical prediction are used.

## Frozen baseline

At 450 nm, finite integrated I03 x/y pair: DoLP=0.03787684, C_source=0.08854257, C_angular=0.08612762, x/y Poincare separation=100.45025108 deg.
Normal 5/10/20 deg cone DoLP=0.07423939/0.44386868/0.31589251; full-angle DoLP=0.05403786.
This is the finite integrated baseline, not periodic intrinsic truth.

## Local pool

The inherited exact polygon-validity rules produce 2487 feasible geometries after the narrower I03-centered filter. Fixed H=525 nm, Px=Py=432 nm, 5x5 array, and 3000x3000 nm mesa are retained.

| ID | role | mechanism | L1/W1/L2/W2 nm | D / delta_theta | A1 / A2 / A_mean / Delta_A | direct / periodic clearance nm | distance from I03 |
|---|---|---|---:|---:|---:|---:|---:|
| IAR1 | INITIAL_INTEGRATED_AWARE_BOUNDARY_CONTROL | DELTA_A_STRONGER_REQUEST_UNAVAILABLE_BOUNDARY_CONTROL | 262/88/195/80 | 220 / 85.009260625 | 0.497143 / 0.418182 / 0.457662 / 0.078961 | 75.389856 / 67.389856 | 0.324168 |
| IAR2 | INITIAL_INTEGRATED_AWARE_CANDIDATE | DELTA_A_WEAKER | 253/91/202/77 | 220 / 86.547508389 | 0.470930 / 0.448029 / 0.459479 / 0.022902 | 71.364803 / 63.364803 | 1.873872 |
| IAR3 | INITIAL_INTEGRATED_AWARE_CANDIDATE | D_REDUCED_ANISOTROPY_PRESERVED | 262/88/194/80 | 208 / 87.329255640 | 0.497143 / 0.416058 / 0.456601 / 0.081084 | 65.241505 / 81.241505 | 1.053068 |
| IAR4 | INITIAL_INTEGRATED_AWARE_CANDIDATE | DELTA_THETA_ROTATION | 259/87/203/79 | 210 / 82.820909321 | 0.497110 / 0.439716 / 0.468413 / 0.057394 | 60.859361 / 72.859361 | 1.429483 |
| IAR-C1 | CONDITIONAL_INTEGRATED_AWARE_CANDIDATE | D_DELTA_THETA_INTERACTION | 252/88/199/78 | 208 / 88.883733451 | 0.482353 / 0.436823 / 0.459588 / 0.045530 | 63.759112 / 79.759112 | 1.661785 |
| IAR-C2 | CONDITIONAL_INTEGRATED_AWARE_CANDIDATE | DELTA_A_DELTA_THETA_INTERACTION | 258/88/198/78 | 217 / 82.818204313 | 0.491329 / 0.434783 / 0.463056 / 0.056547 | 69.901005 / 67.901005 | 1.034453 |

All six selected records are mathematically non-overlapping, contained, integer-dimensioned, half-grid compatible, and pass the inherited direct/periodic clearance >=60 nm gates. IAR1 is a boundary control only: the requested stronger-Delta_A direction is absent within the inherited parent domain because I03 already reaches the pool maximum. These are geometry-only probes; no candidate is predicted to improve integrated DoLP.

## Future truth contract

The initial batch is 4 geometries x 2 independent top-well dipoles = 8 FDTD entries, but admission is not authorized here and is blocked by the local-space constraint. Both x and y must be valid before pair evaluation; combine Stokes incoherently.

## Limits

W_emit remains `UNRESOLVED_FOR_PRODUCTION_CLOSURE`. The incident field immediately at I03 is unavailable (`INCIDENT_I03_FIELD_NOT_AVAILABLE`), so exact source-to-I03 angular causality is not claimed. No new diagnostic solver is requested here.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called=false`, `solver_entered=0`, `RCWA=0`, `ML=0`; no new MQW well or physics was created.
