# Stage11-3B4 H500 LP 240/300 Expanded Search Summary

## Boundary
- H500 LP single-dimer spectral rescue over 449/450/451 nm only.
- No K=6/metagrating, finite patch, dipole, DBR, RCLED, H600/H700, or Stage10 CP modification.

## Completion
- planned_cases = 57
- run_cases = 57
- succeeded = 57
- failed = 0
- stopped_before_fdtd_due_to_cap = False

## Answers
1. 0/60/180 report-level evidence completed: `True`.
2. 120 rescue kept fixed and valid: `true` for `H500DIMER2H_003_B120_y_pair_noswap_G22_O-30`.
3. Best 240 replacement: `H500DIMER12A_012_B240_x_pair_swap_G85_O-32`, failed_gates `ratio;phase`, worst_ratio `4.564178`.
4. Best 300 replacement: `H500DIMER12D_003_B300_x_pair_swap_G90_O-30`, failed_gates `ratio`, worst_ratio `4.507269`.
5. Repaired six-bin tuple passes after expansion: `false`.
6. Tuple failed gates: `ratio;relative_phase;rms_phase;candidate_gate`.
7. Recommended Stage11-3B5: expand 240/300 search further or consider broader H500/H600/H700/material rescue.

## Best Tuple
- tuple_id: `explicit_repaired_after_3b4`
- min_worst_ratio: `4.507269`
- min_worst_Tx: `0.452778`
- max_worst_matrix_error: `0.471025`
- max_relative_phase_error_deg: `35.520283`
