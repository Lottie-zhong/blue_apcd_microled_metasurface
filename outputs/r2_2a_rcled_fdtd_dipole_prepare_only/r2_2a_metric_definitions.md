# R2-2A Metric Definitions

Later extraction must report:
- `spectral_FWHM_nm`: Full width at half maximum of spectral response near 453 nm.
- `angular_FWHM_deg`: Angular full width at half maximum at 453 nm.
- `peak_abs_angle_deg`: Absolute value of the peak emission angle.
- `eta5/eta10/eta20/eta30`: Cone collection efficiencies within +/-5, +/-10, +/-20, +/-30 deg.
- `I_normal_0_5deg`: Integrated or averaged intensity proxy over 0-5 deg.
- `I_offaxis_20_30deg`: Integrated or averaged intensity proxy over 20-30 deg.
- `normal_offaxis_ratio`: I_normal_0_5deg / I_offaxis_20_30deg.
- `x/y incoherent average`: Add x- and y-dipole powers only; do not add fields coherently.

Success bands:
- `angular_FWHM_deg`: ideal <=10; acceptable <=25.
- `peak_abs_angle_deg`: ideal <=5; acceptable <=10.
- `normal_offaxis_ratio`: ideal >1.5; acceptable >1.
- `spectral_FWHM_nm`: ideal <=6; acceptable <=8.

Do not use eta20/eta30 alone as success criteria.
