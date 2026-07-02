# R2-4A target and validation criteria

Target: normal-direction RCLED source module around 453 nm for later APCD input.

Valid MQW incoherent pair: simulation_x + simulation_z_outofplane. The simulation_y cavity-normal dipole is invalid for this 2D MQW pair.

## Ideal final criteria

- incoherent peak_abs_angle_deg <= 5
- incoherent angular_FWHM_deg <= 10
- incoherent normal_offaxis_ratio > 1.5
- spectral_FWHM_nm <= 6

## Acceptable final criteria

- incoherent peak_abs_angle_deg <= 10
- incoherent angular_FWHM_deg <= 25
- incoherent normal_offaxis_ratio > 1.0
- spectral_FWHM_nm <= 8

Spectral FWHM must be evaluated in near-normal angular windows, for example |theta| <= 5 deg and |theta| <= 10 deg. Do not evaluate spectral FWHM at the rejected +/-36 deg off-axis lobe.
