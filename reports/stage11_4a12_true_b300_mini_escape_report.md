# Stage11-4A12 True B300 Mini-Escape Scout

Scope: only A9 G3, 6 H600 true-B300 mini-escape cases. No G1/G2 rerun, coverage, H650, K=6, H500 rescue.

planned = 6
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
  "candidate_id": "H600TRUEB300G3_002_diag_pair_J1J2_G100",
  "source_candidate_id": "H500DIMER12D_011_B300_diag_pair_noswap_G80_O-30",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "2.357350",
  "worst_Tx": "0.947046",
  "worst_matrix_error": "0.651573",
  "max_phase_error_deg": "88.009657",
  "nearest_actual_bins": "0",
  "best_pass_level": "fail",
  "near_miss": "false",
  "reassignment_flag": "none",
  "failed_gates": "ratio;matrix;phase",
  "score": "0.959579"
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

Stop H600 true-B300 search and write Stage11-4A13 decision audit; G1/G2/G3 found no useful true B300.
