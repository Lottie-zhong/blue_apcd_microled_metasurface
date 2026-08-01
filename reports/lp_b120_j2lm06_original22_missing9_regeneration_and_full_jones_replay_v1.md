# ORIGINAL22 missing9 matching regeneration and full Jones replay v1

Status: PARTIAL (physics preserved; frozen txx reproduction hard gate failed)

- 9/9 exact matching geometries regenerated; 18/18 450 nm x/y subruns accepted.
- Batch A gate: BATCH_A_REGENERATION_GATE_PASS.
- Original22 complete: 13 historical + 9 prospective = 22.
- Full-Jones design matrix rank 10, condition 6.10534. The 22-point fitted txx coefficients differ from the frozen historical proxy by 8.228297e-03, exceeding 2e-15: HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE.
- No bounded6 data entered fitting, feature selection, or threshold selection.
- bounded6 replay is leakage-controlled retrospective, not historical primary validation. Complex-Jones MAE 0.00456626; Frobenius MAE 0.0111321.
- 22->28 post-hoc classification is retained only as diagnostic evidence; D9 readiness is POSTHOC_MODEL_DRIFT_REQUIRES_MORE_DIAGNOSTIC.
- No D9 geometry generated and no additional solver run.
