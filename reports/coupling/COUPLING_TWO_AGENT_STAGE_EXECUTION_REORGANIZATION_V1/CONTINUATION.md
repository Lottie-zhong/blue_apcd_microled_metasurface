# COUPLING_TWO_AGENT_STAGE_EXECUTION_REORGANIZATION_V1 — continuation

Last updated 2026-10-05T07:07:18Z.

## Ownership

Coupling ML accepted sole ownership of the frozen K6 V2 queue, Coupling case-status ledger, truth intake and labels. Its one-time audit reported 14 Runner registry rows (13 DONE, 1 FAILED_POSTENTRY); the only K6 V2 row is `K6LDA1_DEV_D1_M05 / attempt_001`, DONE, one entry, zero replay. The manager verified the registry SHA `23ed5548…bea07f31`. At that snapshot no Runner lock/active.json or FDTD engine/mpiexec process was active; global control was generation 27, health PASS, no new-entry hold, and no active global hold. No live lock transfer was needed.

ML is the sole queue scheduler and may initiate a Runner entry only after the existing recovery gates pass. Runner V1 exclusively creates/releases its lock and writes its registry, attempt state and durable truth. GPU remains an on-demand platform maintainer and continues the already-authorized zero-solver normalization repair. GPU acknowledged that it is the on-demand Runner/platform maintainer and that Coupling ML owns the K6 V2 queue. GPU continues the existing zero-solver power repair unchanged; this handoff did not restart or expand that task. This reorganization started no solver or training.

## Frozen scope and current gate

The 128-case allowlist remains frozen: 12 local-axis plus 116 global geometries. Budget is 128 total, max one entry per case, zero post-entry replay; first case consumed one, at most 127 remain. Confirmation32, real training fits and extra diagnostic entries stay zero. Keep the accepted near plane at z≈1802 nm, about 90 nm above NP top. EXT02 remains outside training and supports one case only.

Coupling's field/modal checks are close, but its earlier sourcepower/IN_REF factor was inferred and no applicable frozen threshold was identified for the converted per-order residual. GPU has since reported direct archive LOAD-only access to sourcepower(f), transmission(POSTNP) and seven x-orders, with source hashes unchanged. This is interim evidence, not acceptance. The first case remains quarantined and 127 later entries remain paused pending physical comparison, opt-in label acceptance, Runner mapping repair/regression, and fresh authority/owner/fence/startup checks.

The observed Runner HEAD is recorded in the manifest but is not selected for later cases. Every new entry must pin an explicitly validated commit. Endpoint closure, actual mesh spacing/transition and PML inner-boundary readbacks remain limitations; they do not authorize monitor optimization or extra diagnostics.

## Dirty files

See `dirty_triage` in `STAGE_VERSION_MANIFEST_V1.json`. Unknown untracked files remain untouched; no broad cleanup or staging was used.
