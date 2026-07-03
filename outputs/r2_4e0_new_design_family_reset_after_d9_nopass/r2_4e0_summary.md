# R2-4E0 New Design-Family Reset After D9 No-Pass

This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.

## One-Line Conclusion
D9 no-pass closes the old candidate-pool route; R2-4E should reset to new design families that include source-position stability and 30-40 deg lobe suppression from the first proxy screen.

## Evidence Snapshot
- D7 x-line average peak_abs_angle_deg: 14.041304042576005
- D7 x-line average normal/offaxis ratio: 0.18235750919538307
- D7 x-line verdict/status: missing
- D7 source-position peak_abs range/std: missing to missing / missing
- D9 hard pass count: 0 of 40 scored candidates

## New Family Directions
- **E0A_lower_Q_angle_stable_cavity**: lower-Q / broader but more angle-stable cavity family
- **E0B_phase_balanced_DBR_30_40_reject**: stronger top/bottom phase-balanced DBR family with explicit 30-40 deg rejection
- **E0C_MQW_lateral_extent_robust_cavity**: source-position robust cavity family optimized for MQW finite lateral extent
- **E0D_reduced_center_contrast_control**: deliberately reduced center resonance contrast to avoid center-only false positive

## Mandatory Guards From Start
- center + bilateral source stability required
- tri-point guard first: x = [-0.7, 0.0, +0.7] um
- 30-40 deg off-axis lobe suppression
- TE/TM off-axis risk guard
- normal/offaxis lower-bound
- angular FWHM guard
- spectral FWHM guard

## Recommended Next Task
R2-4E1_Python_only_new_family_candidate_generator_proxy_scan
