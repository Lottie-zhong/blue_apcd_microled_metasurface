# R2-4A merit function definition

A later TMM/STACK implementation should maximize a normal-RCLED merit proxy:

`M = positive_terms - penalty_terms`

## Positive terms

- high normal-window power near lambda = 453 nm
- high normal/off-axis ratio
- small peak_abs_angle_deg
- small angular_FWHM_deg
- small spectral_FWHM_nm in near-normal window
- adequate upward extraction proxy

## Penalty terms

- dominant peak outside |theta| <= 10 deg
- strong off-axis power in |theta| = 20 to 60 deg
- spectral peak outside 450 to 456 nm
- spectral_FWHM_nm > 8
- angular_FWHM_deg > 25
- too-high-Q / too-low-extraction designs
- layer thickness outside fabrication constraints
