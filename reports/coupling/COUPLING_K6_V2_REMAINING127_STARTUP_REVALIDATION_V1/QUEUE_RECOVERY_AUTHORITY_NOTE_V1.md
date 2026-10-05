# Queue recovery authority note

Snapshot captured: 2026-10-05T17:44:13.495624+00:00

`QUEUE_LIVE_CHECKPOINT_V2.json` is a historical snapshot captured at `2026-10-05T17:29:18.381254+00:00`. Its 6/5/5 counts and D3_P05-in-progress state were accurate at that time; they are not the live queue state. Do not use it as a restart cursor.

For recovery, the authoritative live state is `QUEUE_EXECUTION_LEDGER_V1.json` reconciled against the official Runner `registry.json`, the matching per-run `status.json`, and durable truth/validation/hash artifacts. The queue ledger and Runner record must agree on case, attempt, run_id, entry count and replay count. Never replay an entered case.

Read-only reconciliation at this snapshot found ledger timestamp `2026-10-05T17:43:57.355977+00:00`, counts entered/truth/labels `7/6/6`, remaining unentered `121`, failed/isolated `0`, and zero replay/training/P_scale-fit/confirmation access. Current case was `K6LDA1_DEV_D4_M05` / `attempt_001`, run_id `K6V2_D4M05_20261005T173925Z_abe99c6d`, `RUN_ONE_IN_PROGRESS`; Runner status was `SOLVER_ENTERED`, one invocation, zero replay. The active-run marker and Runner lock were present. This documentation correction did not read or modify the solver process, GPU slot, current run artifacts, or runtime ledger.
