# APCD Coupling-ML GPU V2 science handoff

Observed on DESKTOP-NNE313K as dell at 2026-10-10 08:01 UTC. This package hands off the Coupling-owned science review and zero-solver integration for K6 V2. It does not authorize a real solve.

## Decision

G027_SCIENCE_ADMISSION_BLOCKED. The frozen case and Coupling budget are valid, but the installed V2 release is an explicit DENY: science_authorized=false, owner_clear=false, expires_unix=0, and requests=[]. The live V2 validator refuses at FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND. The Controller task is disabled. Do not start or enable it under this handoff.

Current Coupling ledger: 128 authorized development cases; 38 entered; 34 truth-valid; 34 labels-valid; 90 unentered; automatic replay 0; confirmation-response access 0. G027 attempt_001 remains FAILED_PREENTRY_NO_ENTRY, entry_consumed=false, truth unavailable. G026 remains formally FAILED_POSTENTRY_NO_TRUTH with its consumed entry; it is not eligible for replay. The 32 confirmation cases remain sealed.

## Frozen science interface

The candidate is K6 development-global geometry K6GDP2_DEV_G027, attempt_001, ordered D1..D6 = [105, 105, 220, 105, 180, 135] nm. It uses the frozen 3D periodic plane-wave contract, fixed MDC and 237 nm spacer, Native-M1 material setup, 440–460 nm inclusive at 1 nm (21 wavelengths), seven transmitted orders (x=-3..3, y=0), both TE/TM coordinates, complete complex C_hat plus the independent positive P_scale branch (588 + 21 = 609 real-valued output coordinates). H2 and all original H1 gates remain frozen. No manufacturing approval is claimed.

The exact G027 source setup, source manifest, case specification, and physical contract are hash-pinned by the installed request. The G027 exact-case systemcheck report is PASS for setup/systemcheck only. It records that run was not called. GPU engine license availability and a scientific solve have not been demonstrated by that report.

## Platform authority and current state

GPU V2 is the only production backend. Legacy GPU V1 and Shared V3 are not used. Installed release code head: e662a92a4485a768ffbebe56c2d759c1e416722a. Installation state is V2_INSTALLED_AWAITING_FIRST_GPU_ENTRY_AUTHORIZATION.

The official scheduled task APCD_GPU_V2_SERIAL_CONTROLLER is currently Enabled=false, MultipleInstancesPolicy=IgnoreNew, ExecutionTimeLimit=PT0S, InteractiveToken, with no trigger. Its action is the installed V2 serial_controller.py invoked by N:\anaconda_envs\RCP_LCP\python.exe with the installed config and request list. The direct read-only task XML SHA is 5cbd79e739ce897c31d4966ca368c410e2211adfb6104db583c7dec3f5d35282. PT0S removes the task time limit; it does not prove survival through logoff, reboot, or interactive-session loss. The V2 runtime ledger was read with SQLite mode=ro: tasks=0, events=0, one empty slot row (generation=0; token, owner, and request_sha null). No Python serial_controller process matched the targeted process query at the observation time.

The installation report dated 2026-10-10 records 128/128 installation tests passing. A focused suite against the installed immutable V2 code also passed 13 tests. The older 2026-10-09 native acceptance report is historical and is not substituted for the newer installation evidence. The exact G027 systemcheck is not a real solver run.

## Scope and persistence

This task added a read-only Coupling adapter, a zero-solver fixture integration test, and this evidence package. It did not modify the V2 worktree, installed V2 runtime, science release, controller task, Coupling ledger, queue manifest, truth, confirmation access, or scientific budget. Real solver entry=0; replay=0; production training fits=0; confirmation-response access=0.

The Coupling worktree root did not contain a current root CONTINUATION.md or AGENTS.md at inspection. This task-local continuation is the recovery entry point; read it before resuming.
