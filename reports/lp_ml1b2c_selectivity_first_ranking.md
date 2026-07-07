# LP-ML1B2C selectivity-first ranking

## Hierarchy implemented
1. Hard gate 1: extraction/schema pass.
2. Hard gate 2: projector/selectivity pass using selected_Tx, selected-to-leakage ratio, y_direct leakage budget, and matrix_error.
3. Hard gate 3: phase-bin pass using nearest_bin_mode and phase_err_at_452nm.
4. Hard gate 4: wavelength stability pass using nearest-bin mode count.
5. Soft ranking: Tx, ratio, matrix_error, phase error, and stability.

## Batch-01 result
- candidate_count: 6
- class_counts: `{'high_Tx_but_nonselective': 3, 'phase_near_but_nonselective': 2, 'phase_drifted_nonselective': 1}`
- strong_or_usable_count: 0

| candidate_id | target | nearest | Tx_mean | ratio_median | matrix_error | phase_err_452 | class |
|---|---:|---:|---:|---:|---:|---:|---|
| LPML1A4_0157_B300_exploration_B300_H500 | 300 | 240 | 0.596152 | 1.525693 | 0.968701 | 45.543915 | high_Tx_but_nonselective |
| LPML1A4_0093_B300_exploration_B300_H500 | 300 | 180 | 0.779973 | 0.899749 | 1.056853 | 111.201295 | high_Tx_but_nonselective |
| LPML1A4_0178_B300_exploration_B300_H650 | 300 | 60 | 0.912648 | 1.006323 | 0.997636 | 90.452269 | high_Tx_but_nonselective |
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | 300 | 0.261044 | 0.412745 | 1.626343 | 29.250068 | phase_near_but_nonselective |
| LPML1A4_0196_B300_exploration_B300_H500 | 300 | 300 | 0.153109 | 0.153982 | 3.296620 | 25.473485 | phase_near_but_nonselective |
| LPML1A4_0049_B300_exploration_B300_H500 | 300 | 120 | 0.412817 | 1.377731 | 0.905772 | 178.091363 | phase_drifted_nonselective |

## Next action
LPML1B2A_BATCH_04 remains the recommended next FDTD batch if another batch is authorized, because batch-02 is still B300 continuation / statistical failure mapping.
Do not declare K=6 readiness. Do not modify the frozen B2A plan.

No FDTD was run. No GUI, FMM, ML training, K=6, coverage, or heavy output generation was performed.
