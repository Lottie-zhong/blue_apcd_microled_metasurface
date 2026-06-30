# Stage11-4A10 True B300 Different-Anchor Scout

Scope: only A9 G1, 18 H600 true-B300 different-anchor cases. No G2/G3, coverage, H650, K=6, H500 rescue.

planned = 18
run = 18
failed = 0
missing = 0
strict = 0
loose = 0
near_miss = 0
reassigned = 0

## Best Candidate

```json
{
  "candidate_id": "H600TRUEB300G1_004_diag_pair_J1J2_G80",
  "source_candidate_id": "H500DIMER12D_011_B300_diag_pair_noswap_G80_O-30",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "4.458043",
  "worst_Tx": "0.957913",
  "worst_matrix_error": "0.475631",
  "max_phase_error_deg": "89.940554",
  "nearest_actual_bins": "0",
  "best_pass_level": "fail",
  "near_miss": "false",
  "reassignment_flag": "none",
  "failed_gates": "ratio;phase",
  "score": "3.200021"
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

Run A9 G2 phase-opposite family; G1 found no useful true B300.
