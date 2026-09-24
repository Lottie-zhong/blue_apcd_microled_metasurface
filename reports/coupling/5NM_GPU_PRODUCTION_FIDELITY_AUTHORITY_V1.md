# 5 nm GPU Production Fidelity Authority V1

Case: `W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1`, `attempt_001`
Authority state: **GPU_BACKEND_PARITY_VALIDATED = YES**; **GPU_NATIVE_TRUTH_PRODUCTION_ADMITTED = NO / BLOCKED**.

The CPU/GPU backend parity gate passes all frozen project-defined thresholds. The completed GPU run is therefore valid evidence of backend reproducibility. Production truth admission remains blocked because the required durable bundle contains no `MON_REFLECTION` data card.

Measured run evidence:

- Actual scientific solver entry count: 1; no replay after entry.
- GPU solver wall: 561.747039 s.
- Child wall: 574.391 s.
- CPU reference solver wall: 29625.919359 s.
- Solver-only speedup: 52.7389x.
- GPU observation: about 90% utilization, about 1789 MiB, about 301.52 W.

Admission boundary:

- GPU backend parity: PASS.
- Native FSP + sibling H5 truth-bundle durability: BLOCKED.
- `PW_K6_SEED_DB_V1`: NOT STARTED.
- New valid geometries / active GPU slots / queued cases: 0 / 0 / 0.
- Autofill scheduler: NOT STARTED.
- FAST and MEDIUM remain NOT ADMITTED.

This report does not authorize a rerun. The next scientific or setup action requires a separately authorized contract decision for the missing reflection monitor; until then the current canary evidence remains quarantined as backend-parity evidence only.

## V2 production-schema attempt

The contract conflict is resolved by `PW_GPU_MONITOR_TRUTH_SCHEMA_V1`: `MON_REFLECTION` is R-only. V2 structural setup validation passed, but the single authorized V2 run attempt is `FAILED_AFTER_ENTRY` under the conservative entry ledger. `run_gpu.xml` records `in run: could not match resource name provided`; no `fdtd-engine-msmpi.exe` was observed, no H5 was created, and the runtime FSP SHA remained equal to the setup FSP SHA. Replay and `attempt_002` are forbidden.
