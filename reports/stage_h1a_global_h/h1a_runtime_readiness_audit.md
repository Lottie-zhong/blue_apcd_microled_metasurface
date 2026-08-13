# H1A runtime and offline-analysis readiness

- Status: `COMPLETE_ANALYSIS`
- Verdict: `H1A_GEOMETRY_DEPENDENT_H_RESPONSE_OBSERVED`
- Unique planned / entered / accepted checkpoints / quarantined: `48 / 48 / 48 / 0`
- Policy: `APCD_GLOBAL_FDTD_PARALLEL_POLICY_V1`; global capacity `2`; max LP active `1`; resources `4 MPI x 1 thread`.
- Observed legal peak: global active FDTD jobs `2`; LP active FDTD jobs `1`; NP peer remained active while LP used Slot 2.
- H500 was reused and not scheduled. Flags `FLAG_60_SECTOR=False`, `FLAG_120_ML_RESTART=False`.
- Phase-only rows: `30`; full-Jones rows: `30`.
- Pre-entry reconciliation: 8 raw budget-guard records matched the exact error `HARD_GATE_SOLVER_BUDGET_EXCEEDED`, had no solver-completion/checkpoint/run artifacts, and remain preserved in raw provenance. They were reconciled as pre-entry; each then had one formal run and an accepted checkpoint. No truly entered case was replayed.
- No automatic ML/cVAE/inverse/K6/atlas/solver continuation is authorized from this audit.

Authoritative final audit: `reports/stage_h1a_global_h/stage_h1a_global_h_final.json`.
