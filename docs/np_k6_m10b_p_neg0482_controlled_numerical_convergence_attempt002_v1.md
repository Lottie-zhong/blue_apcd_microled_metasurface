# NP K6 M10B P −0.482758 controlled numerical convergence attempt 002

Status: `PARTIAL`

Classification: `TEMPORAL_UNDERCONVERGENCE_NOT_PRIMARY_CAUSE`. The single authorized attempt completed and was independently reloaded; the frozen closure gate remains failed, so S and any later attempt remain unauthorized.

## Identity and safety

- Case: `NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE`; attempt: `attempt_002`; polarization: `P_XLIKE`; ux: `-0.48275862068965514`.
- Setup/pre-FSP SHA256: `920c4257debd6e2adbc7a7893752552f71d8500bf04437f7332bf54304af38d2`. Run-copy SHA256: `6ee4ddefd8822acc5e5122aeea26da4306aa0ea4906d2989caec88b347a39f5a`.
- Post-FSP: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_m10b_serial_execution_v1\runtime_runs\NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE\attempt_002\NP_K6_M10B_ALT1_UX_M0d482758620690_P_XLIKE_attempt_002_post.fsp`
- Post-FSP SHA256: `8f5da182c892c3602b9e29c6ea221324d15bc853a7a0e2f59da5a7ff16497e46`.
- Ledger: entered=1, run_invocation_count=1, engine_completed=1, post_saved=1, controller_returned=1.
- Independent post-FSP reload: PASS; reload used no `run()` and no `save()`; resources read back as 12 MPI × 1 thread.
- Global slot: acquired for the solver attempt and released after post-FSP persistence; current active FDTD=0.
- Attempt 001 remains immutable/rejected; attempt 003, S, external MDC, and all other cases were not started.

## 11-point result

- T range: 0.664408603–0.717356450.
- R range (formal positive magnitude): 0.266850462–0.321771384.
- Max |1−T−R|: 0.0217521700181 (gate ≤0.01: FAIL; worst at 445 nm).
- Max transmitted-order sum−T mismatch: 1.11022302463e-16 (gate ≤1e−8: PASS).
- Max source-normalization mismatch: 1.11022302463e-16 (gate ≤1e−8: PASS).
- Exact wavelengths: 445–455 nm, 11/11, finite: PASS.
- At 450 nm: T=0.6945426528202804, R=0.2962506721904919, η(+1)=0.12032614874663729, η(0)=0.07047835680416716, η(−1)=0.12140996334314873.
- Reflection monitor raw sign is negative for −z flux; formal R is `abs(raw reflection T)`, matching the frozen extraction convention.

## Convergence comparison

Attempt 001 max closure residual was 0.0214212198722; attempt 002 is 0.0217521700181, a change of -0.000330950145963. Max |ΔT|=0.0388078048899; max |Δη(+1)|=0.009224539755. The closure did not improve, so this is `TEMPORAL_UNDERCONVERGENCE_NOT_PRIMARY_CAUSE`, not a convergence-repair pass.

## Evidence

- `attempt002_post_fsp_manifest.json`
- `attempt002_post_reload_readonly_audit.json`
- `attempt002_solver_call_reconciliation.json`
- `attempt002_provenance_reconciliation.json`
- `attempt002_evidence_consistency_audit.json`
- `attempt002_authoritative_summary.json`
- `attempt002_quality_gate.json`
- `attempt002_spectral_metrics.csv`
- `attempt002_transmitted_orders.csv`
- `attempt001_attempt002_deltas.csv`

No candidate or S promotion follows from this result.
