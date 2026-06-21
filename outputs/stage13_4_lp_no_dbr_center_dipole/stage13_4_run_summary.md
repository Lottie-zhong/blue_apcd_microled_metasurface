# Stage13-4 LP No-DBR Center Dipole Diagnostic

## Scope and resolved setup

- Frozen candidate: `H500_LP_APCD_K6_XGRAD_FROZEN_STAGE12`; patch `A_small` = `3 x 19` tiles.
- Geometry: `342` dimers / `684` nanopillars.
- Source: `(0.0, 0.0, -200.0) nm`; source-z is a diagnostic placeholder relative to pillar-base z=0.
- Coordinate system: x-y metasurface, z height, +z emission/monitor, x gradient, target x-LP.
- Wavelength `450.0` nm; height `500.0` nm; object-defined dielectric index `2.6`.
- Background: `default background only; no substrate/device-stack object`.
- DBR: off; RCLED: off; no optimization; no source-position sweep.
- FDTD spans: x `9062.432362` nm, y `9401.000000` nm, z `-900.0` to `1800.0` nm.
- Monitor: +z plane at `1000.0` nm.
- Solver processes: `4` (limited to avoid oversubscribing the concurrent 12-worker external job).

## Run gate

- center_x status: `ok`.
- center_y status: `ok`.
- center_y was permitted only after center_x run and complex-vector extraction succeeded.

## LP fractions

| case | cone | LP_fraction | target/leakage | extraction |
| --- | ---: | ---: | ---: | --- |
| center_x | 5.0 | 0.8604256419672854 | 6.164639795553362 | complex_vector_ok |
| center_x | 10.0 | 0.8483519779267704 | 5.5942172296656025 | complex_vector_ok |
| center_x | 20.0 | 0.8211746124169129 | 4.592047155694674 | complex_vector_ok |
| center_y | 5.0 | 0.12053375799449416 | 0.13705330828802814 | complex_vector_ok |
| center_y | 10.0 | 0.10749123089998588 | 0.12043717061556453 | complex_vector_ok |
| center_y | 20.0 | 0.14826750456849208 | 0.174077548248733 | complex_vector_ok |

## Center incoherent result

| cone | LP_fraction | pass >0.60 |
| ---: | ---: | --- |
| 5.0 | 0.5645978012557092 | False |
| 10.0 | 0.4971830235434377 | False |
| 20.0 | 0.4622843043218509 | False |

- Stage interpretation: `fail_or_near_balance`.
- Recommendation: Stop for mechanism diagnosis before +/-q cases.
- This is a finite-patch angular-cone LP diagnostic, not an order-resolved Jones-matrix/APCD claim.
