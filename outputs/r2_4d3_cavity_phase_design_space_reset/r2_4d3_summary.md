# R2-4D3 Cavity-phase and Design-space Reset Analysis

No FDTD, Lumerical, lumapi, heavy files, or new large optimization was run.

## No-pass Cause Breakdown

| cause | count | percent_of_candidates |
| --- | --- | --- |
| spectral FWHM too broad | 12686 | 95.026 |
| spectral peak outside 450-456 nm | 12406 | 92.929 |
| normal_offaxis_ratio_below_threshold | 9336 | 69.933 |
| 30-40 deg resonance risk too high | 8491 | 63.603 |
| angular FWHM too broad | 8202 | 61.438 |
| normal-window response too low | 8026 | 60.12 |
| peak_abs_angle above threshold | 7892 | 59.116 |
| 20-60 deg off-axis response too high | 6754 | 50.592 |
| layer/fabrication constraint issue | 13 | 0.097 |

## Near-pass Candidates

| candidate_id | failed_rule_count | failure_mode | corrected_proxy_peak_abs_angle_deg | corrected_proxy_angular_FWHM_deg | spectral_peak_nm_normal_window | spectral_fwhm_nm_normal_window | score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R2_4D2_OPT_04463 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.0 | 9.492 | 450.25 | 7.855 | -19.291036 |
| R2_4D2_OPT_11775 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.5 | 7.002 | 450.5 | 6.9 | -21.474728 |
| R2_4D2_OPT_12488 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.0 | 7.014 | 451.5 | 5.453 | -24.944722 |
| R2_4D2_OPT_12312 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.0 | 9.84 | 452.0 | 7.591 | -27.531887 |
| R2_4D2_OPT_12277 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 7.0 | 7.486 | 451.5 | 6.697 | -27.645491 |
| R2_4D2_OPT_09487 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 7.0 | 7.266 | 454.25 | 5.718 | -27.723518 |
| R2_4D2_OPT_12500 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.5 | 8.862 | 450.0 | 4.836 | -28.10633 |
| R2_4D2_OPT_09406 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.0 | 8.776 | 450.5 | 5.124 | -28.256491 |
| R2_4D2_OPT_12308 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.0 | 9.922 | 451.0 | 7.373 | -28.929165 |
| R2_4D2_OPT_03038 | 3 | offaxis20_60_above_threshold;offaxis30_40_above_threshold;30_40_to_normal_above_threshold | 6.5 | 9.121 | 456.0 | 7.319 | -29.873768 |

## Design-variable Coverage

| variable | all_mean | near_pass_mean | low_boundary_fraction | high_boundary_fraction | recommendation |
| --- | --- | --- | --- | --- | --- |
| top_pair_count | 7.1277 | 7.9 | 0.1363 | 0.1527 | constrain only after next focused phase sweep |
| bottom_pair_count | 8.0601 | 8.2 | 0.1106 | 0.1231 | constrain only after next focused phase sweep |
| cavity_spacer_nm | 271.4678 | 272.3 | 0.0504 | 0.0572 | shift or expand cavity_spacer_nm; near-pass spectral peaks cluster away from 453 |
| top_termination_nm | 45.4626 | 54.9333 | 0.0481 | 0.0537 | allow independent termination material/thickness choices |
| bottom_termination_nm | 45.4688 | 52.6667 | 0.05 | 0.0511 | allow independent termination material/thickness choices |
| top_high_scale | 0.9917 |  | 0.0577 | 0.0468 | keep scale bounds but add phase/source-position surrogate |
| top_low_scale | 0.9909 |  | 0.0599 | 0.0503 | keep scale bounds but add phase/source-position surrogate |
| bottom_high_scale | 0.9929 |  | 0.055 | 0.0456 | keep scale bounds but add phase/source-position surrogate |
| bottom_low_scale | 0.9919 |  | 0.056 | 0.0479 | keep scale bounds but add phase/source-position surrogate |
| top_chirp | 0.0013 |  | 0.052 | 0.0581 | allow stronger chirp/apodization only with off-axis guard |
| bottom_chirp | -0.0002 |  | 0.0469 | 0.0496 | allow stronger chirp/apodization only with off-axis guard |
| source_position_fraction |  |  |  |  | add as an optimization variable or surrogate before FDTD shortlist |
| aperture/source-position surrogate |  |  |  |  | add explicit x-line source-position risk surrogate |

## Threshold Sanity

Keep the negative-sample protections. The most suspicious proxy-only strictness is population-relative thresholding and too-narrow spectral centering during exploratory diagnosis.

## Decision

Preferred next route: R2-4D4 focused cavity-phase sweep around normal-mode condition.

## Stop

No R2-4D2 FSP setup or FDTD should be run from the no-pass list.
