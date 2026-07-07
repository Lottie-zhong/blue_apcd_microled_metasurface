# LP-ML1B2C selectivity-first ranking

## Hierarchy implemented
1. Hard gate 1: extraction/schema pass.
2. Hard gate 2: projector/selectivity pass using selected_Tx, selected-to-leakage ratio, y_direct leakage budget, and matrix_error.
3. Hard gate 3: phase-bin pass using nearest_bin_mode and phase_err_at_452nm.
4. Hard gate 4: wavelength stability pass using nearest-bin mode count.
5. Soft ranking: Tx, ratio, matrix_error, phase error, and stability.

## Batch result
- candidate_count: 6
- class_counts: `{'projector_pass_phase_wrong': 1, 'high_Tx_but_nonselective': 2, 'phase_near_but_nonselective': 2, 'phase_drifted_nonselective': 1}`
- strong_or_usable_count: 0

| candidate_id | target | nearest | Tx_mean | ratio_median | matrix_error | phase_err_452 | class |
|---|---:|---:|---:|---:|---:|---:|---|
| LPML1A4_0283_B240_exploration_B240_H650 | 240 | 120 | 0.911493 | 40.805510 | 0.161157 | 107.542245 | projector_pass_phase_wrong |
| LPML1A4_0524_global_escape_lhs_B180_H600 | 180 | 0 | 0.813230 | 1.685024 | 0.797972 | 157.404876 | high_Tx_but_nonselective |
| LPML1A4_0536_global_escape_lhs_B180_H500 | 180 | 300 | 0.507860 | 0.525229 | 1.405088 | 138.254233 | high_Tx_but_nonselective |
| LPML1A4_0279_B240_exploration_B240_H500 | 240 | 240 | 0.386713 | 3.267402 | 0.800285 | 7.641174 | phase_near_but_nonselective |
| LPML1A4_0511_global_escape_lhs_B120_H500 | 120 | 120 | 0.748726 | 0.994878 | 1.019870 | 19.728549 | phase_near_but_nonselective |
| LPML1A4_0270_B240_exploration_B240_H600 | 240 | 120 | 0.336603 | 0.338204 | 2.187993 | 116.299679 | phase_drifted_nonselective |

## Next action
LPML1B2A_BATCH_04 remains the recommended next FDTD batch if another batch is authorized, because batch-02 is still B300 continuation / statistical failure mapping.
Do not declare K=6 readiness. Do not modify the frozen B2A plan.

No FDTD was run by this ranker. No GUI, FMM, ML training, K=6, coverage, or heavy output generation was performed by ranking.
