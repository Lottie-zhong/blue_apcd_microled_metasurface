# 2026-06 Current Frozen Baseline: Blue-10K6 APCD-ML-RCWA Directional Metagrating

## Frozen Baseline

- wavelength_nm = 450
- steering_angle_deg = +10
- K_dimers_per_supercell = 6
- supercell_period_nm ≈ 2591.45 nm
- dimer_pitch_x_nm ≈ 431.91 nm
- period_y_nm = 432
- phase_states_deg = [0, 60, 120, 180, 240, 300]

This is the current default baseline for the blue MicroLED APCD-inspired spin-selective directional metagrating route.

## Current Geometry Baseline

- placement_mode = literature_ingan2026_oblique
- dimer_angle_deg = 60
- literature seed distance = 170 nm
- engineering-repaired distance = 190 nm
- reason for d=190: d=170 gap too small; d=190 gives min intra-dimer gap ≈26.70 nm with healthy margins
- height_nm = 500
- metasurface_index = 2.6

The local dimer pitch is subwavelength-like, while the full K=6 supercell is intentionally a metagrating period.

## Mapping Names

- MAPAB / A-B 对应映射方案: A柱 L180_W90_H500_N260 对应文献 element_1；B柱 L230_W100_H500_N260 对应文献 element_2。
- MAPBA / B-A 交换映射方案: B柱 L230_W100_H500_N260 对应文献 element_1；A柱 L180_W90_H500_N260 对应文献 element_2。

## Completed Checkpoints

- Blue-10K6 static geometry skeleton generated.
- py432 preferred over py348.
- d-sweep selected d=190 nm.
- D190 boundary preflight passed.
- MAPAB / A-B 对应映射方案 x/y FDTD simulations completed successfully.
- saved FSP files exist for MAPAB x and y incidence.
- current missing link: saved-FSP complex Jones extraction.

## Immediate Next Priority

Do not run full K=6 FDTD.
Do not recreate static generator.

Immediate next priority is:

saved-FSP → complex Jones extraction → circular-basis APCD metrics for MAPAB / A-B 对应映射方案.

## Jones Convention

J_linear rows = output x/y
J_linear columns = input x/y

J = [[t_xx, t_xy],
     [t_yx, t_yy]]

Circular convention:

R = (x - i y)/sqrt(2)
L = (x + i y)/sqrt(2)

## Legacy / Archive Unless Explicitly Requested

- 633 nm route
- +15 degree route
- K=5 / K=7 exploratory routes
- p_x≈348 nm as default route
- p_x≈518 nm as default route
- old K6/K7 setup groups
