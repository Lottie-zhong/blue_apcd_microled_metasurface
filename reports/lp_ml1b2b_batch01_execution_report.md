# LP-ML1B2B batch-01 execution report

Batch: LPML1B2A_BATCH_01

## Candidate table

| candidate_id | target_bin | sampling_group | H_nm | wavelengths | polarizations | subruns |
|---|---:|---|---:|---:|---:|---:|
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | B300_exploration | 600 | 9 | 2 | 18 |
| LPML1A4_0049_B300_exploration_B300_H500 | 300 | B300_exploration | 500 | 9 | 2 | 18 |
| LPML1A4_0093_B300_exploration_B300_H500 | 300 | B300_exploration | 500 | 9 | 2 | 18 |
| LPML1A4_0157_B300_exploration_B300_H500 | 300 | B300_exploration | 500 | 9 | 2 | 18 |
| LPML1A4_0178_B300_exploration_B300_H650 | 300 | B300_exploration | 650 | 9 | 2 | 18 |
| LPML1A4_0196_B300_exploration_B300_H500 | 300 | B300_exploration | 500 | 9 | 2 | 18 |

## Runtime
- expected subruns: 108
- actual subrun records: 108
- run this invocation: 108
- reused subruns: 0
- expected merged Jones rows: 54
- merged Jones rows: 54
- total runtime seconds: 2058.82
- failures: 0
- anomalies: 0
- temporary .fsp files: 108 in D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b2b_36case_pilot\batch_01\fdtd_tmp
- smoke overlap policy: rerun_in_B2B_output_schema_for_clean_independent_dataset

## Ranking

| candidate_id | target | nearest mode | Tx mean | ratio median | phase err @452 | anomalies | status |
|---|---:|---:|---:|---:|---:|---:|---|
| LPML1A4_0196_B300_exploration_B300_H500 | 300 | 300 | 0.153109 | 0.153982 | 25.473485 | 0 | weak |
| LPML1A4_0157_B300_exploration_B300_H500 | 300 | 240 | 0.596152 | 1.525693 | 45.543915 | 0 | phase_wrong |
| LPML1A4_0049_B300_exploration_B300_H500 | 300 | 120 | 0.412817 | 1.377731 | 178.091363 | 0 | phase_wrong |
| LPML1A4_0178_B300_exploration_B300_H650 | 300 | 60 | 0.912648 | 1.006323 | 90.452269 | 0 | phase_wrong |
| LPML1A4_0093_B300_exploration_B300_H500 | 300 | 180 | 0.779973 | 0.899749 | 111.201295 | 0 | phase_wrong |
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | 300 | 0.261044 | 0.412745 | 29.250068 | 0 | phase_wrong |

## Boundaries
- No full 36-case run was executed.
- No 600-candidate run was executed.
- No GUI, FMM solve, ML training, K=6, or coverage run was executed.
- Heavy .fsp files are runtime artifacts under outputs and were not committed.
