# R2-4H1E No-run Tri-point X-dipole Plan

Plan only. Do not run in H1E.

Future first validation, if separately approved:
- Candidate: `F:\wc_312\MDC_blue_oujizi.fsp`.
- Source: `source_1` only, electric x-dipole orientation theta=90 deg, phi=0 deg.
- Disable `source` PlaneSource in memory.
- Wavelength: start with 450 nm because the audited dipole source is fixed at 450 nm.
- Positions: begin with center x=0 first, then tri-point x=[-0.7, 0, +0.7] um only if source isolation is verified.
- Do not save the original FSP.
- Ignore all pre-existing analysis-mode results.

Future metrics:
- total transmitted power through monitor
- near-normal cone power if angular farfield can be extracted
- peak angle
- angular FWHM
- normal/off-axis ratio
- 40-60 deg off-axis leakage
- source isolation status
- valid/invalid flag for mixed-source risk

Disallowed until x-dipole passes:
- y-dipole
- z-dipole
- broadband validation
- 5-point or 9-point position sweep
