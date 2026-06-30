# R2-2A Prepare-Only Package

This package prepares the first 2D FDTD dipole validation plan for the three primary R2 RCLED source-module candidates from R2-1B.

No FDTD was run. Lumerical was not launched. No `.fsp`, `.ldf`, or raw monitor data were created.

## Planned first-run cases

- Candidates: `R2_1_00227`, `R2_1_00223`, `R2_1_04067`
- Wavelength: 453 nm only
- Source position: center only
- Dipoles: x and y separately
- Total planned cases: 6

## Controls recorded but not included

- `R2_1_00359`: top-filter control, not a true RCLED cavity.
- `R2_1_02653`: C2 fallback control, high-resolution angular FWHM failed.

## Success logic for later FDTD

The target is narrow near-normal emission. eta20/eta30 alone is not enough.

- angular_FWHM <= 10 deg ideal, <= 25 deg acceptable
- peak_abs_angle <= 5 deg ideal, <= 10 deg acceptable
- normal/offaxis ratio > 1.5 ideal, > 1 acceptable
- spectral FWHM <= 6 nm ideal, <= 8 nm acceptable

## Open mapping uncertainty

The main uncertainty is converting TMM `cavity_span_nm` into the exact FDTD vertical GaN/cavity geometry while preserving clean interfaces and the prior 2D mapping. The later FDTD runner should explicitly audit vertical layer placement before solving.
