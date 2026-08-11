# NP K6 M4 Batch2 Primary4 HF acquisition v1

Status: `NP_K6_M4_BATCH2_PRIMARY4_HF_ACQUISITION_COMPLETE_M5_RETRAIN_READY`.

The frozen Primary4 set completed exactly 8 logical P/S tasks and 88 exact 445--455 nm rows. The merged development view contains 198 pre-existing rows plus 88 new rows (286 total), with duplicate and sealed reads both zero. Native-M1 sampled materials, the independent pilot stack, fixed 5/5/5 nm mesh, 3 ps generator and policy hash are preserved.

G04-S had one pre-entry controller/file-lock failure; the same `attempt_001` task was safely recovered and consumed exactly one physical solver invocation. No solver was rerun.

P/S similarity remains `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; no polarization merging or schema change is authorized. M4 predictions are audited against truth in `m4_prediction_vs_truth_long.csv` and `m4_prediction_vs_truth_summary.csv`. M5 retraining, first6/first8, sealed evaluation and all new solver work remain prohibited. Selection roles are recorded in `batch2_selection_role_audit.csv`; the combined P0+Batch1+Batch2 empirical engine-time distribution is recorded in `combined_p0_batch1_batch2_runtime_statistics.json`, separate from controller/licensing overhead.

See `batch2_closure_audit.json`, `batch2_standalone_validator_report.json`, `batch2_runtime_statistics.json`, `combined_p0_batch1_batch2_runtime_statistics.json`, and `batch2_p_s_audit_summary.json`.
