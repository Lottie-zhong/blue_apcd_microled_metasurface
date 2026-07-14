# MDC GaN Native-M1 TMM angle convention audit v1

## Decision

- `air_side_far_field_angle_convention_validated`.
- The frozen P1 input is `theta_air_deg`, not GaN internal angle: it maps `theta_GaN=asin(sin(theta_air)/2.41)` and therefore conserves real `kx/k0=sin(theta_air)`.
- Native-M1 uses the same real output-air kx, with complex GaN represented only by passive forward `kz=sqrt(n^2-kx^2)`.

## Symmetry-aware peak semantics

- The signed -60 to +60 degree grid can have equal physical maxima at plus/minus theta. `argmax` is retained only as `maximum_angle_raw_argmax_deg`; formal output is the deterministic `maximum_angle_set_deg`.
- Tie tolerance is a floating-point roundoff bound and does not broaden a one-degree grid point. A plus/minus tie is not reported as unilateral beam steering.

## Ratio provenance

- `normal_to_40_60_ratio = mean[T_unpol(0,5,10 deg)] / mean[T_unpol(40,45,50,55,60 deg)]`.
- Source: `scripts/run_mdc_p1_asymmetric_tmm_spectral_v1.py:111-119`, commit `cfa72d7`.

## Native-M1 raw-table 450 nm

|structure|angular FWHM deg|max angle set deg|T0/Tmax|ratio|
|---|---:|---:|---:|---:|
|P1_EXPLICIT_FAB_G3_A3|26.619014|[-3.0,3.0]|0.997378|40.115520|
|P1_ZL1_ALTERNATIVE_G3_A3|14.996580|[0.0]|1.000000|45.666605|
|P1_ZL1_NOMINAL_G3_A3|17.826891|[-4.0,4.0]|0.963524|63.088795|

## Scope

- Plane-wave TMM output angle is air-side and may be compared geometrically with FDTD farfield angle, but this does not prove that a Lumerical source-angle property equals theta_air.
- No finite GaN propagation, FDTD, Lumerical, RCWA, FMMAX, or material-policy change was used.
