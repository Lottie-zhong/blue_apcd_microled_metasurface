# Stage11-4A5 H600 B240 Mechanism Expansion

Scope: only A4 Group 1, H600 B240 mechanism expansion, 36 cases over 451/452/453 nm. No B300, coverage, H650, K=6, H500 rescue, DBR/RCLED, dipole, or finite patch.

planned = 36
reused = 0
run = 36
failed = 0
missing = 0
strict_candidates = 0
loose_candidates = 2
near_miss_candidates = 0

## Best Candidate

```json
{
  "candidate_id": "H600B240MECH_009_diag_pair_J1J2_G40",
  "case_count": "3",
  "complete_451_452_453": "true",
  "worst_ratio": "5.157216",
  "worst_Tx": "0.835876",
  "worst_matrix_error": "0.481903",
  "max_phase_error_deg": "25.892659",
  "best_pass_level": "loose",
  "near_miss": "false",
  "failed_gates": "ratio;phase",
  "selectivity_improvement_vs_a3": "5.076045",
  "matrix_improvement_vs_a3": "0.510196",
  "score": "5.570285"
}
```

## Baseline

{
  "worst_ratio": 1.015991,
  "worst_Tx": 0.988208,
  "worst_matrix_error": 0.992099,
  "max_phase_error_deg": 39.50157
}

## Best By Wavelength

```json
[
  {
    "wavelength_nm": 451,
    "candidate_id": "H600B240MECH_010_diag_pair_J2J1_G40",
    "ratio": "10.304292",
    "phase_error_deg": "27.666785"
  },
  {
    "wavelength_nm": 452,
    "candidate_id": "H600B240MECH_010_diag_pair_J2J1_G40",
    "ratio": "13.996790",
    "phase_error_deg": "16.668068"
  },
  {
    "wavelength_nm": 453,
    "candidate_id": "H600B240MECH_010_diag_pair_J2J1_G40",
    "ratio": "5.161239",
    "phase_error_deg": "20.440220"
  }
]
```

## Recommendation

B240 has loose/strict evidence; B300 phase pull can resume
