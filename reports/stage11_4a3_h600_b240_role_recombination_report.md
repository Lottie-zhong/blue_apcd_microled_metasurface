# Stage11-4A3 H600 B240 Role Recombination Scout

Scope: only H600 B240 role recombination, 24 cases over 451/452/453 nm. No K=6, H650, B300, coverage bins, H500 rescue, DBR/RCLED, dipole, or finite patch.

planned = 24
reused = 24
run = 0
failed = 0
strict_candidates = 0
loose_candidates = 0
near_miss_candidates = 0

## Best Candidate

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

## Baseline Comparison

A1 H600 B240 baseline: worst_ratio 1.003135, phase_error 40.346637 deg, failed ratio/matrix/phase.

## Best By Wavelength

[
  {
    "wavelength_nm": 451,
    "candidate_id": "H600B240REC_008_FROM_H500DIMER12A_007_B240_x_pair_swap_G100_O-28",
    "ratio": "1.049898",
    "phase_error_deg": "42.164018"
  },
  {
    "wavelength_nm": 452,
    "candidate_id": "H600B240REC_001_FROM_H500DIMER12A_006_B240_x_pair_swap_G80_O-28",
    "ratio": "1.039634",
    "phase_error_deg": "36.344412"
  },
  {
    "wavelength_nm": 453,
    "candidate_id": "H600B240REC_003_FROM_H500DIMER12A_012_B240_x_pair_swap_G85_O-32",
    "ratio": "1.025878",
    "phase_error_deg": "32.838420"
  }
]

## Recommendation

redesign B240 search space before B300
