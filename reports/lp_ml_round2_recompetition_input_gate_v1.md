# LP ML Round-2 Recompetition Input Gate v1

- Status: `LP_ML_ROUND2_RECOMPETITION_HARD_GATE`
- Failure class: `DATA_BOUNDARY_CONFLICT`
- Solver calls: `0`

## Conflict

The task baseline requires candidate `LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054` to be quarantined with zero rows. The frozen plan marks it excluded, but the current staging and merged CSV each contain nine rows (450.0–454.0 nm). All nine rows are `PLANNED_NOT_RUN`, `ABSENT_NOT_SIMULATED`, and `model_fill=NONE`; they are not physics observations and were not treated as model training data.

This audit does not modify or delete physics/dataset rows and does not rewrite the historical artifact audit. Training is paused until the authoritative dataset boundary and hash are reconciled.

See `outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_recompetition_input_conflict_audit_v1.json` for complete hashes and field-level evidence.
