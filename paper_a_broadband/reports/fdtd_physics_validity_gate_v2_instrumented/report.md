# Paper A FDTD physics validity gate V2 instrumented

Status: PASS_PRE_ADMISSION_INSTRUMENTATION_READY

This is a zero-solver pre-admission audit. It does not promote any new physics result.

## Decisions

- BF08 attempt-003 x/y immutable p0 logs both classify as INVALID_FOR_PHYSICS_TRUTH_NUMERICAL_DIVERGENCE using the established V1/BF08 Auto Shutoff rule.
- BF07 remains INSUFFICIENT_EVIDENCE_NOT_VALIDATED under V2 because no independent persisted time series exists.
- BF01_x attempt-001 remains unchanged and INSUFFICIENT_EVIDENCE_NOT_VALIDATED.
- BF01_x attempt-002 setup-only instrumentation passed. Physics semantic fingerprint: 7ef054cffe4e3967c43a700fd2498397d3de1f39104d9c6b1977c4bcbfb5085f. Instrumented pre-FSP SHA256: 748999f34803762b38ebf8ed7db131ce95fd4df02c2ca31afa41ce9845704a69. Instrumentation fingerprint: c7b67d8358f4147c401620516d46c8c2ad95314593586aa38129013dd0c65657.
- New cases without a V2 convergence instrumentation fingerprint are blocked before solver entry as BLOCKED_V2_INSTRUMENTATION_NOT_PREPARED.
- The anisotropy runner now calls the V2 gate and passes immutable convergence evidence when available. BF01_x future entry uses a distinct attempt-002 identity.

## Safety counters

NEW_FDTD_BUDGET=0; solver_run_called=false; solver_entered=0; RCWA=0; ML=0; no scheduler admission. No FSP, raw solver data, material, mesh, boundary, or scientific monitor was modified by this audit.

## Artifacts

- paper_a_broadband/authority/paper_a_fdtd_physics_validity_gate_v2_instrumented.json
- paper_a_broadband/reports/fdtd_physics_validity_gate_v2_instrumented/BF01_x_attempt_002_setup_only.json
- paper_a_broadband/reports/fdtd_physics_validity_gate_v2_instrumented/audit.json
- BF08_x_v2_regression.json
- BF08_y_v2_regression.json
- BF07_x_v2_regression.json
- BF01_x_attempt_001_v2_regression.json

## Next authority

No benchmark solver is started by this task. A future BF01_x attempt-002 FDTD run requires explicit scientific authorization and scheduler admission. No automatic replay or BF02-BF04 admission is enabled.
