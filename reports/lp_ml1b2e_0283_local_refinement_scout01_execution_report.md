# LP-ML1B2E 0283 local refinement scout-01 execution

This run executed only 8 selected local refinement candidates from the frozen B2D 0283 plan.

## Selected candidates

| candidate_id | family | H | rationale |
|---|---|---:|---|
| LPML1B2D_B2D_0283_A01 | reassigned_B120_cleanup | 650.000000 | small theta1 pull for B120 phase cleanup |
| LPML1B2D_B2D_0283_A02 | reassigned_B120_cleanup | 650.000000 | small theta1 push for B120 phase cleanup |
| LPML1B2D_B2D_0283_A03 | reassigned_B120_cleanup | 650.000000 | small theta2 pull for B120 phase cleanup |
| LPML1B2D_B2D_0283_A04 | reassigned_B120_cleanup | 650.000000 | small theta2 push for B120 phase cleanup |
| LPML1B2D_B2D_0283_A05 | reassigned_B120_cleanup | 650.000000 | slightly stronger coupling while preserving projector backbone |
| LPML1B2D_B2D_0283_B01 | phase_tuning_scout | 650.000000 | local L1 phase perturbation |
| LPML1B2D_B2D_0283_C02 | fabrication_friendly_H_check | 600.000000 | height-only H600 check from strong H650 projector seed |
| LPML1B2D_B2D_0283_C05 | fabrication_friendly_H_check | 500.000000 | height-only H500 experimental convenience check |

## Runtime
- expected FDTD subruns: 144
- actual subrun records: 144
- run this invocation: 144
- reused subruns: 0
- expected merged Jones rows: 72
- merged Jones rows: 72
- failures: 0
- anomalies: 0
- total runtime sec: 3212.66
- per candidate runtime sec: 401.58

## Boundary
No batch-05, full 36-case, 600-candidate, GUI, FMM, training, K=6, or coverage run was executed.
