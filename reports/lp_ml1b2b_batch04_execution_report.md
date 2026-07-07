# LP-ML1B2B batch-04 execution report

Batch: LPML1B2A_BATCH_04

## Candidate table

| candidate_id | target_bin | sampling_group | H_nm | wavelengths | polarizations | subruns |
|---|---:|---|---:|---:|---:|---:|
| LPML1A4_0270_B240_exploration_B240_H600 | 240 | B240_exploration | 600 | 9 | 2 | 18 |
| LPML1A4_0279_B240_exploration_B240_H500 | 240 | B240_exploration | 500 | 9 | 2 | 18 |
| LPML1A4_0283_B240_exploration_B240_H650 | 240 | B240_exploration | 650 | 9 | 2 | 18 |
| LPML1A4_0511_global_escape_lhs_B120_H500 | 120 | global_escape_lhs | 500 | 9 | 2 | 18 |
| LPML1A4_0524_global_escape_lhs_B180_H600 | 180 | global_escape_lhs | 600 | 9 | 2 | 18 |
| LPML1A4_0536_global_escape_lhs_B180_H500 | 180 | global_escape_lhs | 500 | 9 | 2 | 18 |

## Runtime
- expected subruns: 108
- actual subrun records: 108
- run this invocation: 108
- reused subruns: 0
- expected merged Jones rows: 54
- merged Jones rows: 54
- total runtime seconds: 2358.14
- failures: 0
- anomalies: 0
- temporary .fsp files: 108 in D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b2b_36case_pilot\batch_04\fdtd_tmp
- smoke overlap policy: rerun_in_B2B_output_schema_for_clean_independent_dataset

## Ranking

| candidate_id | target | nearest mode | Tx mean | ratio median | phase err @452 | anomalies | status |
|---|---:|---:|---:|---:|---:|---:|---|
| LPML1A4_0279_B240_exploration_B240_H500 | 240 | 240 | 0.386713 | 3.267402 | 7.641174 | 0 | usable |
| LPML1A4_0511_global_escape_lhs_B120_H500 | 120 | 120 | 0.748726 | 0.994878 | 19.728549 | 0 | weak |
| LPML1A4_0283_B240_exploration_B240_H650 | 240 | 120 | 0.911493 | 40.805510 | 107.542245 | 0 | phase_wrong |
| LPML1A4_0524_global_escape_lhs_B180_H600 | 180 | 60 | 0.813230 | 1.685024 | 157.404876 | 0 | phase_wrong |
| LPML1A4_0536_global_escape_lhs_B180_H500 | 180 | 300 | 0.507860 | 0.525229 | 138.254233 | 0 | phase_wrong |
| LPML1A4_0270_B240_exploration_B240_H600 | 240 | 120 | 0.336603 | 0.338204 | 116.299679 | 0 | phase_wrong |

## Boundaries
- No full 36-case run was executed.
- No 600-candidate run was executed.
- No GUI, FMM solve, ML training, K=6, or coverage run was executed.
- Heavy .fsp files are runtime artifacts under outputs and were not committed.
