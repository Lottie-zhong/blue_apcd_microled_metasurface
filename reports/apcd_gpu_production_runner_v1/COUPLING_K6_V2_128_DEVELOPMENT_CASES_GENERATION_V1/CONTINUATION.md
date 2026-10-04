# Continuation — K6 V2 128 development budget

Read this file and `FINAL_REPORT.md` first. Then check current remote Git and live Runner state; saved hashes are pins for comparison, not substitutes for fresh launch validation.

## Current state

- The controlled route uses authority `a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35` and budget `e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c`.
- Budget ID is `APCD_GPU_RUNNER_K6_V2_128_DEVELOPMENT_CASES_MAX1_20261005_V1`; exact 128-case order and hashes live in `scripts/shared_fdtd/gpu_runner_v1/k6_v2_development_solver_budget_v1.json`.
- The 128 budget is 1 entry per exact development case, maximum 128 total, `attempt_001`, zero automatic replay. All 32 sealed confirmations remain zero-entry/zero-response-access; training fits remain zero.
- Route implementation regression: 105 passed, 50 subtests passed. No K6 V2 solver entry had occurred when this continuation was written.
- First case: `K6LDA1_DEV_D1_M05 / attempt_001`, D `[215,195,210,150,140,210]`, geometry SHA `260821eaa933c1b36e67132656e633bde30f2f4cbf994b0b774eed04cca1b6e5`.

## Resume procedure

1. Inspect its existing task-isolated canonical/staged FSP, physical contract, source authority, source manifest and old proof. Preserve old artifacts under a versioned route-refresh directory; do not rewrite science inputs or setup bytes.
2. Bind a current-route setup LOAD-only proof and source manifest to the exact current authority/policy hashes and FSP SHA. Run only official `adapter.py preflight-setup`; it must not call `run-one` or solver.
3. Immediately before entry, verify live global hold/control generation, owner/fence, official registry and active lock, process/engine lineage, GPU quota, exact first-case history count 0, and current proof/FSP/manifest hashes. The adapter repeats setup, authority, budget, registry-count and hold checks under the single-slot guard.
4. Start only `K6LDA1_DEV_D1_M05 / attempt_001` through official `adapter.py run-one`, once. If entry is recorded, never replay; preserve artifacts and use zero-solver recovery only.
5. Require GPU/process lineage, durable FSP and sibling H5, fresh LOAD, `SCIENTIFIC_VALID`, truth-before-DONE and formal release. Hand the full truth/provenance/hash bundle to Coupling. Do not continue with the other 127 until the Coupling ingestion/evaluator explicitly returns PASS.

## Hard boundaries

No confirmation identity, response reads, model fitting, geometry substitution, physical contract changes, extra attempts, automatic replay, parallel slot, or alternate launcher. `attempt_002` for any budgeted case is rejected. EXT02 diagnostic remains a separate completed identity and is not a training label.
