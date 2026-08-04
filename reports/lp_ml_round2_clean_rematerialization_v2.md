# LP-ML Round-2 Clean Rematerialization v2

## Decision

`LPML_R1_GLOBAL_SOBOL_054` is quarantined as `QUARANTINED_INCOMPLETE_NO_COMPLETE_JONES_V1`. Its orphan x checkpoint and failed y attempts remain read-only evidence; admitted physics rows are zero.

The Round-2 candidate `LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054` has a distinct exact geometry hash and is not the quarantined R1 geometry. It remains an admitted Round-2 candidate after accepted x/y checkpoint and hash gates.

## Clean materialization

- Round-1: 255 geometries / 2295 rows; quarantined R1 054 rows: 0.
- Round-2: 64 geometries / 576 rows.
- Merged clean v2: 319 geometries / 2871 rows; exactly 9 rows per geometry; duplicates: 0; model-filled rows: 0.
- Split: Round-1 179/38/38 train/validation/test; Round-2 48/8/8 train/validation/permanent external; canonical and symmetry leakage: 0.
- Solver calls in this task: 0.

The old Round-2 postprocess provenance/status conflict is preserved in the supersession ledger; no source physics checkpoint or old staging file was changed.

See `outputs/lp_ml_dataset_v1/clean_v2/clean_dataset_manifest_v2.json`, `quarantine_manifest_v2.json`, `decision_ledger_v2.json`, and `clean_dataset_checksums_v2.json`.
