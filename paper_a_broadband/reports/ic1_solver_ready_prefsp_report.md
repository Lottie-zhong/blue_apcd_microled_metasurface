# IC1 setup-only pre-FSP and deterministic rebuild audit

Status: PASS_SOLVER_READY_PREFSP
Case: IC1_MDC_I03_TOPWELL_X
No FDTD/RCWA/ML solver was run; run() was not called and solver entry remains zero.

Canonical pre-FSP: D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\runtime\ic1_solver_ready\IC1_MDC_I03_TOPWELL_X_attempt_001_pre.fsp
Canonical SHA256: 72439a053e8d2c2d8f09df544096ff31922e10bc99c6bc7baa439762a64536a0
Physics semantic fingerprint: 5f3a5cf319a270572d9acf33b7c1cba6495728bcb55caf350efe1d4aee12eb6b
Integrated instrumentation fingerprint: ff0f40c8595b71d7bd1d5d16db898338b9dbfbb1f92fbe5978f6ab1beb163b86

## Rebuild result
- Binary identical: False.
- Physics semantic identical: True.
- Integrated instrumentation identical: True.
- Diagnosis: LUMERICAL_FSP_BINARY_SERIALIZATION_DRIFT_WITH_IDENTICAL_PHYSICS_AND_INSTRUMENTATION_READBACK.
- Canonical output is the validated rebuild-A byte copy; serialization drift is explicit and not silently ignored.

## Contract
- Fresh model constructed from frozen JSON authorities, not an old FSP geometry template.
- CP setup FSP was used only as a native-material seed; all seed model objects were deleted in memory and the seed was not saved.
- Native aliases: APCD_GAN_NATIVE_M1, APCD_TIO2_NATIVE_M1, APCD_SIO2_NATIVE_M1.
- Finite 3 um mesa, 5x5 I03, direct MDC/I03 contact at z=975 nm, finite xyz PML, no periodic xy.
- Top-well x dipole at (0, 0, -171.5) nm, 400-500 nm / 101 points.
- V2 probe at (0, 0, -100) nm; V2 thresholds unchanged.
- Dedicated runner: one case, 12 MPI x 1 thread, maximum one new entry, explicit execute confirmation.
