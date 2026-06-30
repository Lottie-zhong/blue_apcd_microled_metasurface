# Stage11-4A6 H600 B300 Phase Pull

Scope: only H600 B300 phase pull, 18 cases over 451/452/453 nm. No coverage, H650, K=6, H500 rescue, DBR/RCLED, dipole, or finite patch.

planned = 18
reused = 0
run = 18
failed = 0
missing = 0
strict_candidates = 0
loose_candidates = 0
near_miss_candidates = 5

## Best Candidate

```json
{
  "candidate_id": "H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
  "source_candidate_id": "H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "11.278722",
  "worst_Tx": "0.752180",
  "worst_matrix_error": "0.297811",
  "max_phase_error_deg": "144.596581",
  "best_pass_level": "fail",
  "near_miss": "true",
  "failed_gates": "phase",
  "selectivity_vs_a1_b300": "1.232889",
  "matrix_delta_vs_a1_b300": "0.032823",
  "score": "8.147374"
}
```

## A1 H600 B300 Baseline

{
  "worst_ratio": 9.148207,
  "worst_Tx": 0.956956,
  "worst_matrix_error": 0.330634,
  "failure_mode": "phase_only"
}

## Best By Wavelength

```json
[
  {
    "wavelength_nm": 451,
    "candidate_id": "H600B300PULL_005_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "ratio": "9.148207",
    "phase_error_deg": "99.860401",
    "matrix_error": "0.330634"
  },
  {
    "wavelength_nm": 452,
    "candidate_id": "H600B300PULL_005_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "ratio": "24.277230",
    "phase_error_deg": "94.623998",
    "matrix_error": "0.202969"
  },
  {
    "wavelength_nm": 453,
    "candidate_id": "H600B300PULL_005_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "ratio": "265880.348910",
    "phase_error_deg": "82.239089",
    "matrix_error": "0.002621"
  }
]
```

## Recommendation

Run focused B300 refinement; B300 is a phase-only near-miss.
