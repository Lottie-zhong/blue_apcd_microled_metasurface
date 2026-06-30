# R2-0 RCLED R1 Closeout and R2 Target Package

## R1 Closeout

The m8 + bottomDBR99 route is no longer the main route. It showed plane-wave spectral selectivity near 453 nm, but full dipole RCLED/FDTD produced symmetric 20-30 degree off-normal lobes. The STACK/TMM interpretation is that the cavity phase favors off-axis resonance rather than normal resonance.

## C2_cav230 Fallback

`R1C2_C2_cav230` is frozen only as a Level C fallback. It uses top_pair_count=6, bottom_pair_count=0, cavity_span_nm=230, termination=TiO2_50nm, and recommended source_y_offset=0 nm. It was validated at 450, 453, and 456 nm and gives near-normal peaks with useful eta20/eta30. Its angular FWHM is still broad, especially about 46 deg at 450/453 nm, so it is not the high-Q final source-module target.

## R2 Target

R2 should target a 453 nm high-Q RCLED/DBR source module with spectral_FWHM <= 6 nm, angular_FWHM <= 10 deg ideal or 10-25 deg acceptable, peak_abs_angle <= 5 deg ideal or <=10 deg acceptable, normal/off-axis resonance ratio > 1, and stable x/y dipole incoherent average.

## R2-1 Plan

Start with STACK/TMM redesign. Screen R2A/R2B/R2C/R2D candidate families using I_proxy(lambda, theta), normal 0-5 deg strength, off-axis 20-30 deg strength, normal/off-axis ratio, spectral FWHM near theta=0, angular FWHM at 453 nm, and peak_angle_abs.
