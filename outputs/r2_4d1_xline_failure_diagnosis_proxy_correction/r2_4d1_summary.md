# R2-4D1 X-line Failure Diagnosis and Proxy Correction

No new FDTD, Lumerical launch, lumapi use, optimization rerun, or heavy file generation was performed.

## Negative Samples

| sample_id | fdtd_peak_abs_angle_deg | fdtd_angular_FWHM_deg | fdtd_normal_offaxis_ratio | failure_mode |
| --- | --- | --- | --- | --- |
| R2_1_00223 | 36.07150156714285 | 4.449120195012995 | 0.4029691292164208 | symmetric +/-36 deg off-axis double-lobe; diagnostic only |
| R2_4B_OPT_06361 | 37.358725261340275 | 4.332020696422504 | 0.12178631481292115 | narrow but strongly off-axis x-line x-dipole lobe near 37 deg |
| R2_4B_OPT_06176 | 9.647365220006636 | 2.009697868501897 | 0.07663416191129037 | near-normal-looking peak angle, but normal-window power collapses and off-axis background dominates |

## Proxy vs FDTD Contradiction

| candidate_id | proxy_peak_abs_angle_deg | fdtd_peak_abs_angle_deg | proxy_normal_offaxis_ratio | fdtd_normal_offaxis_ratio | normal_offaxis_ratio_collapse_factor |
| --- | --- | --- | --- | --- | --- |
| R2_4B_OPT_06361 | 7.0 | 37.358725261340275 | 21.030296 | 0.12178631481292115 | 0.00579099 |
| R2_4B_OPT_06176 | 7.0 | 9.647365220006636 | 19.279846 | 0.07663416191129037 | 0.00397483 |

## Source-position Diagnosis

| candidate_id | peak_angle_mean_deg | peak_angle_std_deg | normal_offaxis_ratio_min | normal_offaxis_ratio_mean | xline_effect |
| --- | --- | --- | --- | --- | --- |
| R2_4B_OPT_06361 | 33.272502599021294 | 3.9451282500574 | 0.11141486242153655 | 0.1261700258331314 | reveals hidden off-axis failure |
| R2_4B_OPT_06176 | 18.475819567171353 | 13.117646922490161 | 0.04193613330364439 | 0.07360716483827184 | reveals source-position instability and weak normal-window power |

## Conclusion

R2-4B proxy over-selected candidates because its normal/offaxis metric did not predict finite-aperture x-line x-dipole behavior. R2-4D2 should rerun the proxy optimization with explicit off-axis, normal-power, multi-peak, and extraction-risk penalties, then generate only 2 to 3 setup-only FSP candidates.
