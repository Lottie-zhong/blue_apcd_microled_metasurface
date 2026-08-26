# BF04 polarization mechanism diagnostic v1

## Status

Zero-solver mechanism diagnostic using only authoritative BF01-BF04 current-Native full-Jones truth. No BF05-BF08 execution.

## Root mechanism

STABLE_DOMINANT_POLARIZATION_AXIS_BUT_INSUFFICIENT_DIATTENUATION

BF04 is the only candidate in this initial set with a narrow canonical MDC-FWHM psi span (39.625 deg), high U1 reference overlap (mean 0.9879; worst 0.8311), and high adjacent U1 overlap (mean 0.9734). Its low linear DoLP points co-locate with reduced singular separation: the bottom-quartile diagnostic gap mean is 0.0694 versus 0.2586 across all formal points, while the corresponding U1 reference-overlap mean remains 0.9722 versus 0.9905. The Pearson diagnostic correlation between linear DoLP and normalized singular gap is 0.9658; the correlation with reference overlap is 0.2607. Therefore channel degeneracy is the primary observed failure mode, with residual U1 ellipticity/rotation retained as secondary evidence.

The authoritative raw canonical FWHM psi span remains 39.6246 deg. Low-DoLP wavelengths were not removed; they are only marked using the bottom quartile of the 31 formal DoLP values, which is diagnostic and not a new qualification threshold.

## Singular-value and stability summary

| Candidate | mean sigma1 | mean sigma2 | mean sigma1/sigma2 | mean normalized gap | worst normalized gap | FWHM psi span (deg) | FWHM U1 reference overlap worst |
|---|---:|---:|---:|---:|---:|---:|---:|
| BF01 | 0.9305 | 0.6896 | 1.5951 | 0.1700 | 0.0036 | 90.000 | 0.0000 |
| BF02 | 0.9737 | 0.5369 | 9.7697 | 0.3780 | 0.0134 | 165.222 | 0.6403 |
| BF03 | 0.9110 | 0.6765 | 4.2922 | 0.2028 | 0.0091 | 229.842 | 0.5980 |
| BF04 | 0.9827 | 0.6226 | 2.7075 | 0.2586 | 0.0264 | 39.625 | 0.8311 |

The initial ordering is not a monotonic delta-theta law: BF02 has the largest mean singular separation, yet its axis is much less stable than BF04; BF03 has a larger FWHM axis span than BF02. The result is therefore classified OBSERVED_IN_THIS_INITIAL_SET only.

## BF04 low-DoLP attribution

- Bottom-quartile diagnostic cutoff: 0.162054; wavelengths: 435, 437, 453, 461, 462, 463, 464, 465 nm.
- Low-DoLP mean normalized gap: 0.069401; all-point mean: 0.258558.
- Low-DoLP mean U1 reference overlap: 0.972158; all-point mean: 0.990550.
- Low-DoLP mean |U1 DoCP|: 0.353276; all-point mean: 0.242467; U1 FWHM maximum |DoCP|: 0.928245.
- BF04 FWHM output max |S3/S0|: 0.217328.

The low-DoLP set is consistent with both reduced channel separation and some increased ellipticity at selected wavelengths, but not with the strong dominant-axis rotation seen in BF01-BF03. No post-hoc threshold was applied.

## Future recommendation

BF04_LOCAL_REDESIGN_JUSTIFIED_AXIS_STABLE_NEEDS_STRONGER_DIATTENUATION

If a future scope is explicitly opened, target only existing geometric variables around the BF04 mechanism: local perturbations of L1/W1, L2/W2, dimer displacement D, and delta-theta centered on the observed 82.727 deg stratum. The objective should be to increase the wavelength-resolved singular gap and suppress selected U1 ellipticity while retaining the stable axis basin. Keep current Native-M1 materials, height, source/monitor, mesh/boundary, and clearance rules fixed. This is a future zero-solver proposal only; no new candidate was created here.

## Safety and provenance

- Source: authoritative full_jones_order_0_0_spectra.csv; exact 435-465 nm grid, 31 points, zero order [0, 0].
- SVD: J = U Sigma V^H, with phase-invariant U1 overlaps.
- Existing canonical diattenuation definition: none found in current authority. derived_power_diattenuation is explicitly diagnostic only.
- BF05_BF08_admitted = false.
- New FDTD budget: 0; solver_run_called: false; solver_entered: 0; RCWA: 0; ML: 0.

## Figure QA contract

- Four Python/matplotlib figures cover singular separation, dominant-channel stability, normalized Stokes trajectories, and BF04 failure attribution.
- All 31 wavelengths are retained; no interpolation or selective deletion was used.
- SVG/PDF preserve editable text; TIFF is 600 dpi; PNG is a 300 dpi preview.
- No uncertainty intervals apply: these are deterministic wavelength-resolved truth points, not replicate estimates.

## Artifacts

- svd_stokes_wavelength_metrics.csv
- bf04_low_dolp_failure_attribution.csv
- trajectory_descriptors.csv
- mechanism_diagnostic_summary.json
- figure_contract.json
- figure_svd_channel_separation.{svg,pdf,tiff,png}
- figure_dominant_channel_stability.{svg,pdf,tiff,png}
- figure_poincare_stokes_trajectories.{svg,pdf,tiff,png}
- figure_bf04_failure_attribution.{svg,pdf,tiff,png}
