# CONTINUATION — APCD Coupling V3 5 nm time diagnostic

Last updated: 2026-10-12
Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1
Branch expected: work/mdc-np-coupling-ml-v1
Candidate batch: K6V3_TIME_DIAG2_V1_BATCH_001

## Mandatory recovery order

Read this file, then PRODUCTION_CODEX_WORKFLOW_HANDOFF.md, ADMISSION_PREPARATION_FINAL_REPORT.md, CASE_REGISTRATION_PACKAGE.json, CONTRACT_DIFF.json, SETUP_READBACK_AUDIT.json, GPU_INSTALLATION_STATE.json, SHA_INVENTORY.json, and GPU_OWNER_HANDOFF.md before continuing.

## Current state

- Both 6 ps candidate setup FSPs exist and passed fresh native LOAD-only semantic readback.
- Only readback change is 3 ps to 6 ps. Auto-shutoff and saved setup mesh override remain unchanged.
- The package now distinguishes source_run_truth from setup_input. These are separate paths and hashes.
- Solver entry/invocation=0; replay=0; no training or P_scale fits; no confirmation response access.
- No scientific 6 ps truth exists; time convergence is unresolved.
- Formal GPU registration/admission is absent. Installed consumer does not support this diagnostic role.
- Do not invoke Runner, Scheduler, solver, run-one, start, resume, or replay from this continuation.
- DOE56 remains unchanged at 4 entered / 4 truth-valid / 4 labels-valid / 52 unentered; V3_NUMERICAL_ADVANCEMENT=HOLD.
- Runtime installation, binding, deny, and scheduled-action markers conflict. Only GPU Owner can close this through official release/registration APIs.

## Resume conditions

1. GPU Owner establishes a separate isolated request and two-entry ledger for batch K6V3_TIME_DIAG2_V1_BATCH_001, with one entry per case, replay disabled, and no DOE56 identity/ledger mutation.
2. Request, registration, ledger, release and binding all carry the same batch ID and separately bind source_run_truth and setup_input.
3. GPU Owner provides exact request/release/binding and installed-consumer hashes plus single-slot ownership evidence.
4. Formal preflight passes before any solver entry. Preserve-first on any post-entry failure.
5. Keep the DOE56 HOLD in force; setup LOAD is not numerical validation.
