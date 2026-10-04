# K6 V2 128-case development solver budget and route report

Date: 2026-10-05
Status: `BUDGET_AUTHORIZED_AND_TESTED; FIRST_CASE_PREFLIGHT_PENDING`

## Scope and authority

This versioned budget applies only to the 128 frozen development identities in `COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1`: 12 `DEVELOPMENT_LOCAL_AXIS` and 116 `DEVELOPMENT_GLOBAL`. Each identity is fixed to `attempt_001`, receives at most one scientific entry, and the set has a total ceiling of 128 entries. Post-entry automatic replay is zero. This records the direct user instruction for `COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1`; no digital signature is claimed.

The first case is `K6LDA1_DEV_D1_M05 / attempt_001`, ordered D `[215,195,210,150,140,210]`, geometry SHA256 `260821eaa933c1b36e67132656e633bde30f2f4cbf994b0b774eed04cca1b6e5`. Remaining case entries wait until the first durable truth is handed to Coupling and its ingestion/evaluator returns PASS. This report grants no confirmation response access, confirmation solver entry, training fit, or manufacturing claim.

The 32 sealed confirmations (4 `SEALED_LOCAL_COMBINATION`, 28 `SEALED_CONFIRMATION_GLOBAL`) remain at solver budget 0. The 160 geometry source authority rows remain unchanged at `solver_entry_authorized=false`, `max_solver_entries=0`, and `training_dataset_eligible=false`. The separately pinned budget is the only new solver-entry grant.

## Pinned route artifacts

- Route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`
- Authority version: `APCD_GPU_RUNNER_EXT02_AND_K6_V2_DEV_BUDGET_20261005_V1`
- Authority SHA256: `a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35`
- Budget file: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\k6_v2_development_solver_budget_v1.json`
- Budget SHA256: `e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c`
- Adapter SHA256: `a9cfb11db584bf2ab96049b9066e198415bfba0863f29d0ed278230ffddc8579`
- Policy SHA256 (unchanged): `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45`
- Frozen registration package SHA256: `22560277c3cd7032e48de6ef5b0023986eefe5aba3c3de07b6eff2bf51dc33f9`
- Frozen package inventory SHA256: `f4497dc646588bf4b83dce5e022d5aa9f2bf48646a298fa78b9fe7adc70bab08`
- Development allowlist SHA256: `7b9b103a742877dbe9b980ad530a68d667f54c91caeddbed60b906ed3a70830`
- Candidate table SHA256: `596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4`
- Amendment 01 SHA256: `124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a`

The complete budget case order, attempt IDs, roles, ordered D vectors, geometry hashes, source-authority paths and hashes are stored in the JSON budget. All 10 package inventory artifacts matched their frozen size/SHA entries. The 160 package rows reconciled one-to-one with Runner authority: 128 development and 32 sealed; every source authority SHA and geometry matched.

## Runtime enforcement

- Setup admission remains distinct from solver permission; setup-only source rows retain zero-entry values.
- Run admission verifies the pinned budget file hash, exact 128-ID development allowlist, all 32 sealed exclusions, per-case authority hashes and ordered geometry.
- Immediately before solver entry, under Runner V1's serial lock, the adapter rereads the active registry and fails closed for a consumed case entry, total count at 128, malformed registry state, or any alternate attempt identity for any budgeted ID.
- The existing single-slot lock, owner/fence, live global-hold check, fresh setup revalidation, GPU quota, completion barrier, durable FSP/H5, fresh LOAD, truth-before-DONE, and no-replay behavior remain in force.
- The original 12-case execution path remains opt-in through its existing route; those IDs are rejected by the new controlled route.

## Validation and execution count

Synthetic offline tests: `scripts/shared_fdtd/gpu_runner_v1` — 106 passed, 50 subtests passed. This covers controlled-route compatibility, exact budget identity/hash checks, sealed-case refusal, per-case and total caps, alternate attempt rejection, and existing Runner/diagnostic behavior.

At report creation, K6 V2 solver entries: 0; FDTD runs: 0; automatic replays: 0; training fits: 0. The first case still needs a current-route fresh LOAD proof and formal preflight, plus live FINAL_LAUNCH_REVALIDATION. No solver has been started by this authority report.

## Next

Refresh only the first case's route-bound proof/manifest, run the official setup preflight, then recheck live control generation, holds, active Runner lock/registry, process lineage, owner/fence and GPU quota. Start `K6LDA1_DEV_D1_M05 / attempt_001` through `adapter.py run-one` once only if every check passes. After truth is durable, hand it to Coupling and wait for its PASS before authorizing any later case. Confirmation cases and the other 127 development cases are not to be launched in this step.
