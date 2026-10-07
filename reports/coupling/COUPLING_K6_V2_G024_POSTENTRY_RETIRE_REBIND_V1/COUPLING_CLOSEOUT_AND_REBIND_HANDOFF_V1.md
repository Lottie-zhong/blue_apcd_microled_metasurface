# Coupling K6 V2 G024 closeout and rebind handoff

Version: `COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1`

## Result

G024 (`K6GDP2_DEV_G024`, `attempt_001`, `K6V2_G024_20261007T123943Z_713590ad`) is reconciled as `FAILED_POSTENTRY_NO_TRUTH`. Its single solver entry remains consumed; Runner receipt verification found one invocation, zero replay, no durable truth, and no label. The former current-case pointers are cleared. The old controller status is `STOPPED_RECONCILED`, and the batch phase is `QUEUE_RECOVERY_RECONCILED_STOPPED`. G023's immutable historical registry digest remains verified through its closeout chain; the current global registry digest is allowed to include the later G024 row while its exact G023 row remains case-scoped and verified.

Current ledger counts: **36 entered; 33 truth-valid; 33 labels-valid; 92 unentered.** Training fits, P_scale fits, confirmation response access, and automatic replay remain zero.

## GPU Codex inputs

Use these three files with Coupling version `COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1`:

1. Successor controller manifest: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1\SUCCESSOR_CONTROLLER_MANIFEST_V1.json`
   SHA-256: `7894166e6cf35311e6f574735773b056c1656bf9e33039c966a1e8b3d569e2ac`
2. Current owner retirement receipt: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1\OWNER_RETIREMENT_RECEIPT_V1.json`
   SHA-256: `f57255515f7f5c2015e58d8c491250de25e62cfed95370ee18be9ee09d10dc0a`
3. Queue state snapshot: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1\QUEUE_STATE_SNAPSHOT_V1.json`
   SHA-256: `fc36c988ea446ae36fe29e541ae01d8de70b4b8131edaf9d2abd881a2d2f38c7`

The successor manifest contains exactly the unentered ordered cases `K6GDP2_DEV_G025` through `K6GDP2_DEV_G116` (92 cases). Only Runner-approved manifest delta fields changed: controller run ID, current Coupling entrypoint hash, status path, case allowlist, and max case count. The frozen queue ID/hash and all scientific and per-case budget fields remain inherited. Its status path stays inside the frozen startup report root as required by `serial_queue.verify_controller_manifest`.

The retirement receipt binds the current old request/task bindings and reconciled status SHA, plus the owner decision and queue snapshot. The receipt validates against Runner commit `8056739d5d2a16092ba139713fe943a63f86fb35`.

## Validation and boundary

Focused tests: `2 passed`. `py_compile`, serial queue `--help`, Coupling successor-manifest validation, Runner old/new manifest checks, exact delta validation, retirement evidence checks, and terminal G024 request validation all passed. Details and hashes are in `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_G024_POSTENTRY_RETIRE_REBIND_V1\RUNNER_API_READONLY_VALIDATION_V1.json` and `SHA256_INVENTORY_V1.json`.

The mutating Runner retirement/rebind API was **not called**. The Task Scheduler task remains enabled/Ready until GPU Codex executes the formal API with these pinned inputs. No solver, training fit, or P_scale fit was run.

## Git context at preparation

Coupling: `work/mdc-np-coupling-ml-v1` at `c00e915c7e9196f1154d496474745e5e2cc6a2e9`. Runner: `codex/apcd-gpu-production-runner-v1` at `8056739d5d2a16092ba139713fe943a63f86fb35`. Coupling workspace contains pre-existing unrelated dirty and untracked files; this task stages only its exact allowlist.
