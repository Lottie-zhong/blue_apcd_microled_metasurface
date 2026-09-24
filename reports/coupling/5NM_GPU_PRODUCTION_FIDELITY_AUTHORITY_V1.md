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
