# APCD global durable monitor policy V2 — NP K6 M8A

This migration installs one server-side, read-only monitor for `NP_K6_M8A_PRIMARY2`.
The production interval is 600 seconds; internal state reads may be more frequent only inside the same monitor process.
Normal samples are appended to the canonical JSONL file without visible chatter. Important transitions, anomalies, and terminal state are reported once.

## Canonical artifacts

- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_progress.jsonl`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor_state.json`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_hourly_summary.json`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/monitor_deployment_audit.json`
- `outputs/np_k6_m8a_primary2_hf_acquisition_v1/monitor/NP_K6_M8A_PRIMARY2_monitor.lock`
- `terminal_success.json` / `terminal_failure.json`

The monitor is independent of the dispatcher, never acquires or releases slots, never calls `run`, never saves or edits an FSP, and never kills, pauses, restarts, or replays a worker. It samples internally every 600 seconds and updates the hourly summary every six samples (about 3600 seconds). The production scheduler wrapper is quiet; no routine 600-second or hourly chat callback is assumed.
Historical anomaly records are retained separately from current execution semantics: `historical_anomalies` preserves prior alerts, while `active_alert`, boolean `active_hard_gate`, and `current_execution_state` describe only the latest authoritative readback. A later healthy state marks an old alert `resolved_by_later_authoritative_state` without deleting or rewriting its historical alert record.
Task Scheduler and dispatcher remain the owners of queue progression, slot release, post-save, and G02-S admission.

## Current M8A authority

G01-P, G01-S, and G02-P are represented as engine-complete, result-recovered, and formally accepted while preserving the fact that their original controller `post_saved` flag was false. G02-S is represented from the latest authoritative readback with `entered=1`, `run_invocation_count=1`, `engine_completed=1`, and `post_saved=1`; its quality acceptance remains separate.

Legacy polling/probe scripts are forensic-only and are not production durable monitors. The query helper reads only the hourly summary first, then the last JSONL record and canonical monitor state; it never scans the repository.

This is a zero-solver control-plane migration: `solver_calls=0`, no new FDTD/RCWA, no slot mutation, and no sealed-HF access.
