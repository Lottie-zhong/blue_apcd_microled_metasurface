# LP-ML1B2E scout-01 selectivity-first ranking

Target is the reassigned B120 bin, not original B240.

| candidate_id | family | H | nearest | Tx_mean | ratio_median | matrix | phase_err_120@452 | stability | class | next_use |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| LPML1B2D_B2D_0283_B01 | phase_tuning_scout | 650.000000 | 120 | 0.962714 | 51.763038 | 0.160828 | 5.587859 | 1 | strong_B120_refined_seed | strong_B120_refined_seed |
| LPML1B2D_B2D_0283_A01 | reassigned_B120_cleanup | 650.000000 | 120 | 0.934846 | 43.642480 | 0.152362 | 11.709756 | 1 | strong_B120_refined_seed | strong_B120_refined_seed |
| LPML1B2D_B2D_0283_A02 | reassigned_B120_cleanup | 650.000000 | 120 | 0.888478 | 39.440819 | 0.164258 | 12.893512 | 1 | strong_B120_refined_seed | usable_B120_refined_seed |
| LPML1B2D_B2D_0283_A05 | reassigned_B120_cleanup | 650.000000 | 120 | 0.908652 | 33.740962 | 0.177334 | 12.938249 | 1 | strong_B120_refined_seed | usable_B120_refined_seed |
| LPML1B2D_B2D_0283_A04 | reassigned_B120_cleanup | 650.000000 | 120 | 0.919513 | 36.222012 | 0.169585 | 12.997340 | 1 | strong_B120_refined_seed | usable_B120_refined_seed |
| LPML1B2D_B2D_0283_A03 | reassigned_B120_cleanup | 650.000000 | 120 | 0.911735 | 48.884536 | 0.148975 | 14.377977 | 1 | strong_B120_refined_seed | usable_B120_refined_seed |
| LPML1B2D_B2D_0283_C02 | fabrication_friendly_H_check | 600.000000 | 60 | 0.741935 | 1.846774 | 0.824186 | 33.959032 | 1 | failed_or_negative | negative_sample |
| LPML1B2D_B2D_0283_C05 | fabrication_friendly_H_check | 500.000000 | 0 | 0.268998 | 0.274381 | 1.934412 | 119.539197 | 1 | failed_or_negative | negative_sample |

## Decision
- candidates improving B120 phase over parent while preserving projector: 2
- H600/H500 variants preserving projector: 0
- Do not declare K=6 readiness from scout-01.
