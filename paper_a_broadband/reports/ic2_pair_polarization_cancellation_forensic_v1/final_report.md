# IC1/IC2 polarization-cancellation forensic

## Status

`PASS` — zero-solver forensic attribution completed.

## 450 nm source decomposition

- IC1-x raw Stokes: `{'S0': 8.7160570827685e-15, 'S1': 3.847888817732426e-15, 'S2': 4.990504727738823e-17, 'S3': -3.0748301375527163e-16}`; DoLP=`0.44150840`
- IC2-y raw Stokes: `{'S0': 8.099812386907693e-15, 'S1': -3.3298905915575444e-15, 'S2': 3.2071645122124613e-16, 'S3': 2.6734203004427825e-17}`; DoLP=`0.41300953`
- x/y S0 ratio: `1.07608135` (`NEARLY_EQUAL`)
- linear-Stokes angle: `173.75550640 deg`; `C_linear=0.08854257`
- Poincare dot/separation: `-0.18138171` / `100.45025108 deg`

## Angular pair at 450 nm

- normal-centered 5/10/20 deg DoLP: `0.07423939` / `0.44386868` / `0.31589251`
- full available upper-angle DoLP: `0.05403786`
- peak direction: theta=`0.54382339 deg`, phi=`45.00000000 deg`; peak-centered 5 deg DoLP=`0.07333360`
- peak-pixel pair DoLP/DoCP/raw psi: `0.23464890` / `0.09818604` / `101.10943122 deg`
- angular cancellation `C_angular`: `0.08612762`
- pair local DoLP power-weighted before angular integration: `0.62741613`

## Broadband pair

- 400–500 nm global pair DoLP mean/worst: `0.04271630` / `0.00338719`
- 400–500 nm source `C_linear` mean/worst/max: `0.12779753` / `0.00739567` / `0.31746318`
- 400–500 nm Poincare separation mean/max: `97.97065668 deg` / `105.56471819 deg`
- max absolute global pair DoCP: `0.01819330`
- raw psi retained; global maximum circular psi step is inherited from the pair closeout. Low linear-Stokes regions are marked by continuous `Lmag/S0` and a diagnostic `DoLP>=0.10` confidence flag; no points were deleted.

## Attribution

`BOTH_SOURCE_AND_ANGULAR_CANCELLATION`. The result is quantitatively based on source `C_linear=0.08854257`, angular `C_angular=0.08612762`, and full-angle pair DoLP `0.05403786`. This distinguishes x/y source Stokes cancellation from subsequent angular integration.

Intrinsic periodic/full-Jones I03 truth is not equivalent to finite integrated top-well x/y truth. Differences include finite 5x5 I03 versus periodic cell, dipole angular spectrum, finite mesa/PML, near-field coupling, MDC conditioning, angular integration, and incoherent spontaneous-source semantics. The stored truth does not include the field immediately incident on I03, so source-to-I03 angular-spectrum attribution is not proven.

## Boundary and next step

`W_emit = UNRESOLVED_FOR_PRODUCTION_CLOSURE`; no emitter-weighted DoLP, absolute LEE, or full-device claim is made.

Recommendation: `INTEGRATED_AWARE_LP_REDESIGN_REQUIRED`. It is not executed here. No new well, CP, Bare+I03, redesign, or solver was started.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called_delta=0`, `solver_entered_delta=0`, `FDTD=0`, `RCWA=0`, `ML=0`, `replay=0`.
