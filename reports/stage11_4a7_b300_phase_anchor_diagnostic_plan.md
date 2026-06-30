# Stage11-4A7 B300 Phase-Anchor Diagnostic Plan

Planning only. No FDTD/Lumerical was run. Scope is H600 B300 only.

## Diagnosis

A6 produced 18 completed B300 rows, with 0 strict, 0 loose, and 5 near-miss candidates.
Best A6 candidate: `H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40`.
Worst ratio: 11.278722; worst Tx: 0.752180; worst matrix error: 0.297811; max phase error: 144.596581 deg.
High-selectivity B300 candidates cluster away from 300 deg; phase anchor is wrong.

## Why Coverage Remains Blocked

B300 has good selectivity but wrong selected-channel phase anchor; coverage 0/60/120/180 should wait until B300 reaches loose/strict or systematic phase-offset correction is proven.

## Future A7 Groups

- S11_4A7_G1_B300_PHASE_ANCHOR_SHIFT: 18 cases, pull selected-channel phase toward 300 without sacrificing ratio/matrix
- S11_4A7_G2_B300_ADJACENT_BIN_ANCHOR_RESCUE: 12 cases, find a better phase anchor if direct B300 pull remains offset
- S11_4A7_G3_B300_ORIENTATION_GAP_FALLBACK: 6 cases, minimal check that orientation/gap can move phase without killing selectivity

Total future cases: 36 / 36.

## Decision Tree

- if B300 becomes loose/strict and B240 loose exists -> run H600 coverage 0/60/120/180 next
- if B300 remains phase-only fail but phase offset becomes systematic -> run one focused phase-offset correction
- if B300 loses selectivity -> redesign B300 search space
- if no improvement -> reconsider LP-Hnew six-bin feasibility

Excluded: B240 rerun, H650, coverage, K=6, finite patch, dipole, DBR/RCLED, H500 rescue.
