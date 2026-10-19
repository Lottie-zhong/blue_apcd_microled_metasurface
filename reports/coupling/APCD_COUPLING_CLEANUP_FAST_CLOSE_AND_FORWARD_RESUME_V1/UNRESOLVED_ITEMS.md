# Unresolved items after cleanup fast close

## Preserved tracked changes

Five tracked paths remain modified and uncommitted. They were left intact to preserve scientific history and cross-owner boundaries:

1. `reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json` — protected DOE56 record with credential-bearing context; no secret values copied into this report.
2. `reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md` — historical continuation retained.
3. `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/BATCH_PREPARATION_STATUS_V1.json` — current status retained.
4. `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json` — authority history retained; case/entry identity is crosswalked read-only in this closeout, with no rewrite.
5. `reports/coupling/COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1/CONTINUATION.md` — Runner-owner recovery boundary remains outside this closeout.

## Preserved untracked ownership groups

The current pre-allowlist-commit raw untracked count is 893 files. The V2 report's end snapshot was 871; its classification is reused as a historical inventory, not presented as a fresh exact classification of the newer state. Large untracked groups still include K6 execution evidence, M2I runtime, and shared/runtime artifacts. No group was bulk-added, deleted, moved, or globally ignored.

The Git ignored-file enumeration found 15,749 paths but emitted one Windows path-length warning. Its count is therefore a lower bound. Existing ignored scientific outputs remain in place under the exact V2 ignore rules. The 3.59 MB current OOF prediction archive remains ignored.

## Closure boundary

The remaining issue is ownership/authority disposition for the preserved files above, not a mismatch in the read-only K6 128-case crosswalk. A clean worktree cannot be claimed while the five tracked paths and unrelated untracked files remain. No permission is inferred to alter DOE56, Runner recovery state, M2I, or shared runtime assets.
