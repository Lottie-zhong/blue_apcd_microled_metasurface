# Stage11-4A8 Phase-Bin Reassignment Audit

Planning/audit only. No FDTD/Lumerical was run.

## Result

Rows audited: 18.
Stable promoted candidates: 3.
Promoted bins: [60].
B300 is not solved unless selected phase is near 300; no A6 high-selectivity donor solved B300.

## Best Reassigned Candidate

```json
{
  "candidate_id": "H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
  "bins": [
    60
  ],
  "worst_ratio": 11.278722,
  "worst_Tx": 0.75218,
  "worst_matrix_error": 0.297811,
  "max_phase_error_to_actual_bin_deg": 24.596581,
  "levels": [
    "strict"
  ],
  "promoted_bin": 60
}
```

## Remaining Missing/Weak Bins

0;120;180;300

## Recommended Next

Use the A6 high-selectivity family as B0/B60 donor evidence only if stable; do not force it as B300. Future B300 should use a different anchor family.
