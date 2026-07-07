# LP-ML1B1A smoke result sanity audit

Purpose: numerical sanity audit of completed LP-ML1B1 smoke-test Jones results before any LP-ML1B2 expansion.

## Input files
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_smoke_results.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_smoke_summary.json
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_failure_log.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_runtime_manifest.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b0_runner_planning\lp_ml1b0_expected_result_schema.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b0_runner_planning\lp_ml1b0_smoke_test_recommendation.csv

Row count: 18
Candidate count: 2

## Candidate-level summary
| candidate_id | target | Tx mean | phase err @452 | nearest bin mode | ratio median | anomalies |
|---|---:|---:|---:|---:|---:|---:|
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | 0.261044 | 29.250068 | 300 | 0.412745 | 0 |
| LPML1A4_0234_B240_exploration_B240_H600 | 240 | 0.476181 | 126.415068 | 120 | 2.127896 | 9 |

## Key metric ranges
- selected_Tx: min=0.113130, mean=0.368612, median=0.407575, max=0.507032
- leakage_xin_to_yout: min=0.001477, mean=0.042015, median=0.038648, max=0.109887
- leakage_yin_to_xout: min=0.001405, mean=0.125952, median=0.130378, max=0.317261
- y_direct_leakage: min=0.022067, mean=0.327310, median=0.398931, max=0.472584
- conversion_to_leakage_ratio: min=0.156922, mean=2.528623, median=0.784180, max=20.544575
- phase_error_deg: min=22.622079, mean=77.656564, median=74.773353, max=141.073996
- matrix_error: min=0.256851, mean=1.231469, median=1.193799, max=2.709969

## Anomaly summary
- total anomaly flags: 9
- extraction/schema anomaly flags: 0
- physical-performance anomaly flags: 9

## Recompute consistency check
- recompute mismatch count: 0

## Phase/bin consistency check
- nearest bins were recomputed from selected_phase_deg using bins 0, 60, 120, 180, 240, 300.

## Runtime summary
- LP-ML1B1 prior total runtime: about 637.29 s.

Decision: template_ok_but_candidate_performance_poor_still_can_proceed_to_pilot

No FDTD was run.
No FMM solver was executed.
No heavy files were committed.
