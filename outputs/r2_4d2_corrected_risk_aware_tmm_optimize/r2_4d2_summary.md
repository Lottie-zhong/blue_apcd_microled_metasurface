# R2-4D2 Corrected Risk-aware TMM/STACK Proxy Optimization

No FDTD, Lumerical, lumapi, FSP, LDF, MAT/H5, raw monitor data, or full adjoint run was performed.

- Candidates evaluated: 13350
- Runtime: 307.358 s
- Conservative corrected-proxy passes: 0
- Best candidate: `R2_4D2_OPT_13003`
- FDTD-ready shortlist count: 0

## Top 5 Corrected-proxy Candidates

| candidate_id | score | top_pair_count | bottom_pair_count | cavity_spacer_nm | corrected_proxy_peak_abs_angle_deg | corrected_proxy_angular_FWHM_deg | normal_window_response_0_10 | offaxis_20_60_response | offaxis_30_40_response | corrected_normal_offaxis_ratio | spectral_peak_nm_normal_window | spectral_fwhm_nm_normal_window | pass_level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R2_4D2_OPT_13003 | -1.822481 | 8 | 12 | 238.0 | 7.0 | 7.277 | 6.26e-08 | 9.3e-09 | 2.78e-08 | 6.755659 | 459.5 | 2.788 | fail_corrected_proxy |
| R2_4D2_OPT_13010 | -2.190919 | 8 | 11 | 228.0 | 7.5 | 8.388 | 0.000853483 | 0.0001155135 | 0.0003419484 | 7.388602 | 447.25 | 3.493 | fail_corrected_proxy |
| R2_4D2_OPT_13013 | -5.177213 | 6 | 10 | 231.0 | 7.0 | 10.025 | 0.0199636889 | 0.0024536107 | 0.0063688473 | 8.136453 | 447.75 | 3.969 | fail_corrected_proxy |
| R2_4D2_OPT_12232 | -9.785043 | 7 | 11 | 244.0 | 6.0 | 10.657 | 0.1278187217 | 0.0145541759 | 0.031840605 | 8.782271 | 448.5 | 3.846 | fail_corrected_proxy |
| R2_4D2_OPT_03742 | -10.869715 | 8 | 12 | 331 | 6.5 | 8.132 | 0.0451575802 | 0.0060001644 | 0.0165637446 | 7.526057 | 448.0 | 4.359 | fail_corrected_proxy |

## FDTD-ready Shortlist

No rows.

## Interpretation

This is still only a Python proxy. R2-4D1 showed the old proxy failed badly against x-line x-dipole FDTD, so these candidates must be validated first by setup-only FSP generation, GUI inspection, and then x-line x-dipole-only FDTD scout. Do not treat these metrics as physical RCLED evidence.
