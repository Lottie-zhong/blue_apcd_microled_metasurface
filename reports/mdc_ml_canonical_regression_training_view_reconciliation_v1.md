# Canonical regression development-view reconciliation v1

The legacy `training_view_v1.npz` remains untouched and is superseded for
formal regression because its 837-row mask includes 111 sealed-test rows.

The versioned `regression_development_view_v1.npz` is derived by frozen row
identity: original train/validation/calibration are 443/111/72, Round1
eligible rows are 100 in frozen folds 24/22/34/20, and all original test rows
are excluded before regression target materialization.  Its 726 rows produce
fold train counts 519/521/509/523.

The excluded identity registry has 377 original test identities, including the
111 formerly mask-eligible sealed rows, and contains no regression targets.
The old pre-fit rejected formal root remains read-only and non-resumable.

`FORMAL_REGRESSION_CANONICAL_INPUT_READY=true` and composite production
dispatch readiness is true; no fit, prediction, conformal operation, formal
OOF call, sealed-target read, or solver call occurred in this task.
