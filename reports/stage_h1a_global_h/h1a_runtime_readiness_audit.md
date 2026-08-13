# H1A runtime and offline-analysis readiness

- Status: `COMPLETE_ANALYSIS_WITH_ENTERED_QUARANTINE`
- Verdict: `H1A_INCONCLUSIVE`
- Unique entered / accepted checkpoints / entered quarantined: `48 / 40 / 8`
- Policy: `APCD_GLOBAL_FDTD_PARALLEL_POLICY_V1`; global capacity `2`; max LP active `1`; resources `4 MPI x 1 thread`.
- Observed legal peak: global active FDTD jobs `2`; LP active FDTD jobs `1`; NP peer remained active while LP used Slot 2.
- H500 was reused and not scheduled. Flags `FLAG_60_SECTOR=False`, `FLAG_120_ML_RESTART=False`.
- Phase-only rows: `26`; full-Jones rows: `26`.
- Hard gate: 8 cases have `solver_entered=true` but no accepted checkpoint (`HARD_GATE_SOLVER_BUDGET_EXCEEDED`). Exact-entry accounting forbids automatic replay; no replay was attempted.
- No automatic ML/cVAE/inverse/K6/atlas/solver continuation is authorized from this audit.

Authoritative final audit: `reports/stage_h1a_global_h/stage_h1a_global_h_final.json`.
