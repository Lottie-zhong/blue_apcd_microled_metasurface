# Stage H1C-1B0 — Broadband Compatibility Attribution and Adaptive Search Design

- Status: `READ_ONLY_COMPLETE`
- Zero new FDTD/RCWA/physics solver; solver_entered delta: `0`; solver replay: `False`.
- Quarantine cases: `3`; postprocess recovered: `0`; all history preserved.
- Complete broadband geometries: `21`; strict / center-only / partial / incompatible: `2/8/5/6`.
- Strict identities: `GLOBAL_006, GLOBAL_015`; strict 450-nm phase separation: `18.8150092574661` deg.
- Near-miss identities: `GLOBAL_018, GLOBAL_002`; formal strict bank unchanged.
- C attribution: `RED_EDGE_LIMITED`; failed wavelengths: `[451.5, 452.0, 452.5, 453.0, 453.5, 454.0]`; min throughput: `0.48733160278771903`.
- Six-bin common-offset occupancy, strict only: `[1, 2]`; strict + near-miss diagnostic: `[1, 2]`; unoccupied diagnostic bins: `[0, 3, 4, 5]`.
- Proposed H1C-1B batch: `24` candidates; frontier `12`, gap/global exploration `12`; proposed-only.
- ML_DATASET_READINESS: `NOT_READY_FOR_FORMAL_ML_RESTART`; canonical registry unchanged with `209` rows.
- No H1B local-edge route restart, ML training, inverse design, or K6 was started.
- COSMETIC_COMMIT_MESSAGE_ANOMALY_NO_HISTORY_REWRITE: previous commit was not amended or force-pushed.

Artifacts: `h1c1b0_quarantine_recovery_audit.json`, `h1c1b0_broadband_failure_matrix.csv`, `h1c1b0_near_miss_bank.json`, `h1c1b0_c_failure_attribution.json`, `h1c1b0_phase_status_map.json`, `h1c1b0_geometry_attribution.json`, `h1c1b0_six_bin_coverage_map.json`, `h1c1b0_adaptive_batch_proposal.json`, `h1c1b0_ml_registry_audit.json`, `h1c1b0_authoritative_snapshot.json`.
