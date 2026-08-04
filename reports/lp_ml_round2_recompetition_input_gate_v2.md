# LP ML Round-2 Recompetition Input Gate v2

- Status: `LP_ML_ROUND2_RECOMPETITION_HARD_GATE`
- Failure class: `DATA_BOUNDARY_CONFLICT_AND_STATUS_MISMATCH`
- New solver calls: `0`

## Corrected evidence

The first audit understated the 054 state. The frozen plan marks `LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054` as excluded and `PLANNED_NOT_RUN`, but its staging package contains an `ACCEPTED` candidate checkpoint, accepted x/y subruns, two historical `solver_entered=True` entries, and nine complete Jones rows. The merged CSV also contains those nine rows, while its status fields are inconsistent with the plan.

The postprocess writer reads all staging rows and unconditionally writes Round-2 rows with `geometry_054_excluded=False`, which explains the mismatch. The current merged dataset therefore cannot simultaneously satisfy the stated `quarantined / 0 rows` boundary. No rows were deleted or rewritten in this audit, and no new solver was called.

Training remains paused until the authoritative 054 quarantine, physics lineage, merged hash, and split manifest are reconciled. See the v2 JSON for hashes and field-level evidence.
