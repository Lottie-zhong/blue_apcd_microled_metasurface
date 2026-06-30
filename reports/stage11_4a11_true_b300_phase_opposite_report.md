# Stage11-4A11 True B300 Different-Anchor Scout

Scope: only A9 G2, 12 H600 true-B300 phase-opposite cases. No G2/G3, coverage, H650, K=6, H500 rescue.

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
  "candidate_id": "H600TRUEB300G2_003_x_pair_J2J1_G95",
  "source_candidate_id": "H500DIMER12A_003_B240_x_pair_swap_G95_O-28",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "1.010146",
  "worst_Tx": "0.988775",
  "worst_matrix_error": "0.994965",
  "max_phase_error_deg": "26.072770",
  "nearest_actual_bins": "300",
  "best_pass_level": "fail",
  "near_miss": "false",
  "reassignment_flag": "none",
  "failed_gates": "ratio;matrix;phase",
  "score": "1.210548"
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

Run A9 G3 mini escape; G2 found no useful true B300.
