# Test40 external evaluation completion

Status: MDC_HF_SURROGATE_V2_TEST40_EXTERNAL_EVALUATION_COMPLETED_RANKING_SCREENING_ONLY

Case identity remained test_case_uid; all 240 cases across 40 geometries completed with 0 failed cases. Predictions were frozen before label generation and extraction was replayed in two fresh processes with identical case/tensor/profile/grid hashes.

Scope: MDC_HF_SURROGATE_V2_TEST40_RANKING_SCREENING_ONLY. No frozen quantitative acceptance threshold was available for post-lock Test40. Raw FDTD upward-power values are not on the M1 source-normalized power scale; therefore absolute-power/profile results are descriptive and no quantitative external acceptance claim is made.

Measured summaries: case profile JS mean 0.267155, geometry profile JS mean 0.231131, case power rank Spearman 0.112941, geometry power rank Spearman 0.12833, log-power MAE/RMSE/bias 21.5355 / 21.819 / 21.5355.

Safety counters: HF15 formal/diagnostic reads 0, sealed-test reads 0, TMM/RCWA/NP solver calls 0, new fits 0. Test40 label reads occurred only after prediction lock.
