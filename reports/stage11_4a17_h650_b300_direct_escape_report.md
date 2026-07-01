# Stage11-4A17 H650 B300 Direct Escape Scout

Scope: only A16 G1, 12 H650 B300 direct escape cases. No G2, coverage, H600 rerun, K=6, H500 rescue.

planned = 12
run = 0
failed = 0
missing = 0
strict = 0
loose = 0
near_miss = 0
reassigned = 0

## Best Candidate

```json
{
  "candidate_id": "H650B300ESCAPE_001_x_pair_J2J1_G90",
  "source_candidate_id": "H500DIMER12D_008_B300_y_pair_swap_G80_O-30",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "0.986137",
  "worst_Tx": "0.928105",
  "worst_matrix_error": "1.007004",
  "max_phase_error_deg": "158.473359",
  "nearest_actual_bins": "120;60",
  "best_pass_level": "fail",
  "near_miss": "false",
  "reassignment_flag": "none",
  "failed_gates": "ratio;matrix;phase",
  "score": "-2.918858"
}
```

## A8 B60 Donor Reference

{
  "ratio": 11.278722,
  "Tx": 0.75218,
  "matrix": 0.297811,
  "phase_error_to_B60": 24.596581
}

## Recommendation

Stop LP-Hnew six-bin attempt and write route-positioning audit; A17 G1 found no H650 true-B300 near-miss.
