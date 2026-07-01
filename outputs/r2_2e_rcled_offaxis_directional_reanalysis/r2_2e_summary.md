# R2-2E off-axis directional re-analysis

No FDTD or Lumerical run was performed. This stage uses only committed R2-2D lightweight angle-cut CSV data.

## Signed angle convention

Angle-cut headers are `['angle_deg', 'intensity_proxy']`. The data include negative and positive signed angles from -90.000 to 90.000 deg.

## Main result

- Incoherent signed peak: 36.072 deg.
- Target absolute angle: 36.072 deg.
- Dominant-lobe FWHM: 4.449 deg.
- Signed-lobe classification: symmetric_plus_minus_offaxis_double_lobe.
- Normal RCLED source-module classification: fail.
- Off-axis narrow-angle seed classification: promising.
- Dipole contribution at dominant signed target: center_x_dominated.

## Physics note

The literal-spacer cavity appears to support a narrow off-axis leakage/cavity mode. If the +/- lobes are symmetric, this should be called off-axis narrow-angle emission, not unidirectional emission.
