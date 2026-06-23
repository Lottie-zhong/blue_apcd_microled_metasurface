# Stage13-7C LP center_x controlled source-coupling diagnostic

## Scope

- Only x-oriented dipoles were run; no center_y, +/-q, DBR/RCLED, geometry change, optimization, or x-y sweep.
- A_small remains 3 x 19 tiles (342 dimers / 684 nanopillars), +z emission/monitor, 450 nm, grid 101.
- Complex Ex/Ey/Ez was required; Ez is excluded from LP projection and included only in total vector power.

## Case selection

- `center_x_repeat`: source=(0.0, 0.0, -200.0) nm; Stage13-4 reproducibility control
- `center_mid_120_180_x`: source=(0.0, 0.0, -350.0) nm; deeper diagnostic source to soften local coupling
- `source_shift_to_cell_mid_x`: source=(-50.0, 0.0, -200.0) nm; safe lateral shift maximizing nearest-pillar distance
- Case 3 selected shift: -50.0 nm; nearest-pillar distance 165.953893 nm; selected: maximum nearest-pillar distance among safe central-region candidates.

## Repeat gate

- center_x_repeat reproduced Stage13-4: `True`.
- Repeat comparison: `{"passed": true, "max_abs_lp_fraction_delta": 0.0, "max_relative_target_power_delta": 0.0, "peak_grid_delta": 0.0}`.

## Peak results

| case | peak ux | peak uy | distance to +target (deg) | nearest order |
| --- | ---: | ---: | ---: | --- |
| center_x_repeat | -0.33999999999999997 | -0.11999999999999995 | 30.736468388405292 | other |
| center_mid_120_180_x | -0.36 | -0.13999999999999999 | 32.23562102902156 | other |
| source_shift_to_cell_mid_x | 0.0 | 0.020000000000000035 | 10.064786890245724 | zero_order |

## Normal-cone LP fraction

| case | cone (deg) | LP_fraction |
| --- | ---: | ---: |
| center_x_repeat | 5.0 | 0.8604256419672854 |
| center_x_repeat | 10.0 | 0.8483519779267704 |
| center_x_repeat | 20.0 | 0.8211746124169129 |
| center_mid_120_180_x | 5.0 | 0.7510404008887671 |
| center_mid_120_180_x | 10.0 | 0.7713170819469348 |
| center_mid_120_180_x | 20.0 | 0.8036541461690137 |
| source_shift_to_cell_mid_x | 5.0 | 0.8528385688342651 |
| source_shift_to_cell_mid_x | 10.0 | 0.8422569285107798 |
| source_shift_to_cell_mid_x | 20.0 | 0.8305834757948923 |

## Resolved +target comparison

| case | +target Ex power, 5 deg | peak distance to +target (deg) |
| --- | ---: | ---: |
| center_x_repeat | 1.059505230551244e-15 | 30.736468388405292 |
| center_mid_120_180_x | 2.8718167299566284e-15 | 32.23562102902156 |
| source_shift_to_cell_mid_x | 9.421854797114529e-16 | 10.064786890245724 |

## Mechanism classification

- source_coupling_can_restore_steering: `False`.
- source_depth_sensitivity: `False`.
- source_center_local_bias_confirmed: `True`.
- local_source_correction_not_sufficient: `True`.

## Single recommended next step

**Stage13-7B: tiny A_small finite-patch plane-wave sanity FDTD with the same +z complex-vector extraction**

Do not run +/-q or add DBR/RCLED before that separately authorized step.

## Jones/APCD evidence boundary

- These are finite-patch dipole angular-power diagnostics, not a new incident-wave order-resolved J_xy/APCD measurement.
- No alpha/beta conversion or t_{alpha*<-alpha}^order claim is made.
