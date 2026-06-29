# Stage11-4A4 B240 Search-Space Redesign Plan

Planning only: no FDTD, no Lumerical, no B300, no coverage bins, no H650 full sweep, no K=6, no H500 rescue.

## A3 Failure Diagnosis

- ok_rows: 24
- Tx-good rows: 24
- Tx-good but selectivity-bad rows: 24
- ratio failure rows: 24
- matrix failure rows: 24
- phase failure rows: 24
- complete wavelengths: True
- strict/loose/near-miss: 0/0/0

Best A3 candidate:

```json
{
  "candidate_id": "H600B240REC_005_FROM_H500DIMER12A_009_B240_x_pair_swap_G90_O-24",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "1.015991",
  "worst_Tx": "0.988208",
  "worst_matrix_error": "0.992099",
  "max_phase_error_deg": "39.501570",
  "best_pass_level": "fail",
  "near_miss": "false",
  "failed_gates": "ratio;matrix;phase",
  "score": "0.815261"
}
```

A3 mainly proved that height-scaled B240 templates keep Tx high but do not restore LP projection selectivity or phase. The next plan changes the mechanism rather than continuing local B240 recombination.

## Why B300 Remains Blocked

B300 phase pull is blocked because B240 has no loose candidate and no near-miss. Without a viable 240 projection-phase anchor, B300 improvement cannot produce a six-bin library.

## Future A4 Groups

| group | height | cases | purpose |
|---|---:|---:|---|
| S11_4A4_H600_B240_MECHANISM_EXPANSION | 600 | 36 | recover LP projection selectivity before phase tuning |
| S11_4A4_H600_B240_ADJACENT_ANCHOR_RESCUE | 600 | 18 | find a 240 common-phase candidate by relabeling a more selective projection family |
| S11_4A4_H650_B240_ESCAPE_HATCH | 650 | 18 | determine whether H600 is the blocker rather than the LP dimer concept |

Total future cases: 72 / 72.

## Decision Tree

- no near-miss: stop LP-Hnew B240 path and reconsider LP paper positioning
- near-miss: run focused B240 refinement
- loose/strict: resume B300 phase pull

## Thresholds

- strict: ratio >= 6, Tx >= 0.45, matrix_error <= 0.50, phase_error <= 25 deg
- loose: ratio >= 3, Tx >= 0.10, matrix_error <= 1.00, phase_error <= 35 deg
- near-miss: ratio >= 2, Tx >= 0.10, matrix_error <= 1.50, phase_error <= 45 deg
