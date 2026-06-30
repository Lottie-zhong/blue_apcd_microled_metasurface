# Stage11-4A15 H600 B300 Selectivity-Phase Hybrid Scout

Scope: only A14 G1, 12 H600 B300 selectivity-phase hybrid cases. No G2/G3, coverage, H650, K=6, H500 rescue.

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
  "candidate_id": "H600B300HYBRID_001_x_pair_J2J1_G90",
  "source_candidate_id": "H500DIMER12D_008_B300_y_pair_swap_G80_O-30",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "11.589234",
  "worst_Tx": "0.979696",
  "worst_matrix_error": "0.293775",
  "max_phase_error_deg": "105.037257",
  "nearest_actual_bins": "0;60",
  "best_pass_level": "fail",
  "near_miss": "false",
  "reassignment_flag": "none",
  "failed_gates": "phase",
  "score": "10.103733"
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

Stop H600 B300 and plan H650 B300 escape hatch; A15 G1 improved selectivity but did not place phase near true B300.
