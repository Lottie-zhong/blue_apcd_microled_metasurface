# POST_D8 frozen full-Jones reconstruction and primary replay v1

Status: BLOCKED_BY_FROZEN_TXX_GATE

- Repository/worktree provenance: PASS; current HEAD e2c6c226d8efd1a5535562f1e79c40cca5fb67da; cb57069 and bounded HEAD reachable; upstream 0/0.
- Original22 training rows: 22 (13 historical recovered + 9 prospective matching regeneration); bounded6 excluded from fit.
- All eight real outputs reconstructed with 10-column quadratic OLS; design rank 10, condition 6.10534.
- Historical txx reproduction max coefficient error: 8.228297e-03 (tolerance 2e-15): HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE.
- Therefore bounded6 primary replay is explicitly NOT EXECUTED; no solver/lumapi/FDTD calls.
- Readiness remains POSTHOC_MODEL_DRIFT_REQUIRES_MORE_DIAGNOSTIC; next diagnostic PHASE_PROJECTOR_CROSS_BRANCH_DIAGNOSTIC. No D9 geometry or candidate plan.
