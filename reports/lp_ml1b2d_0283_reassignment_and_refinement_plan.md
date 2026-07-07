# LP-ML1B2D 0283 reassignment and local refinement plan

## Decision
`LPML1A4_0283_B240_exploration_B240_H650` should be treated as `strong_B120_reassigned_seed`.
It is not a B240 success. Its selected-channel phase is stably assigned to B120 over the sampled wavelengths.

## Key metrics
- phase_err_to_120_at_452_deg: 12.457755
- phase_err_to_240_at_452_deg: 107.542245
- nearest_bin_counts: `{'120': 9}`
- Tx_median: 0.917259
- ratio_median: 40.805510
- y_direct_leakage_median: 0.015377
- matrix_error_median: 0.161157

## Geometry and constraints
- H/L1/W1/theta1: 650 / 210.0 / 150.0 / 80.0
- L2/W2/theta2: 120.0 / 100.0 / 160.0
- center_dx_nm: 210.0
- period_x_nm, period_y_nm: 431.907786, 431.907786
- edge_margin_nm: 18.860253
- aabb_gap_x_nm: 44.423795
- aspect_ratio_H_over_minW: 6.500000
- geometry_valid: True, flags: `[]`

## Local refinement candidate count
Generated 16 proposed candidates. These are planning rows only; they are not added to the frozen B2A 36-case plan and were not simulated.

## Recommended next action
Run a small 0283-local refinement batch before broad batch-05. The goal should be B120 cleanup and phase-anchor mapping around the strong projector backbone.
Do not declare K=6 readiness from this single reassigned seed.

No FDTD, GUI, FMM, ML training, K=6, coverage, or heavy output generation was performed in this B2D audit.
