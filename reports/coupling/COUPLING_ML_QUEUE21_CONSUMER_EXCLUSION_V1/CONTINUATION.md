# Continuation — queue21 Coupling consumer exclusion

Read this file first when resuming this task, then read `CONSUMER_EXCLUSION_REGISTRY_V1.json` and `FINAL_REPORT.md`.

## Current state

- Coupling worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch at task review: `work/mdc-np-coupling-ml-v1`
- Starting HEAD observed: `fbd5b376a4180f0b814e604dfbd77ea7171c2e30`; check current HEAD/status before any action.
- Target: `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, events 1499/1506, physical entry count **UNKNOWN**.
- Latest Runner HEAD reviewed: `88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35`. Owner V2 disposition and decision hashes are pinned in the registry. Owner V2 still requires Coupling consumer enforcement; hold release was not performed here.
- Registry SHA-256: `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`.
- Final focused suite: 32 passed. No solver entries, scientific model fits, confirmation-response reads, Runner edits, hold-release calls, deletes, or replays.

## Protected boundary

Queue21 and any artifact linked by case identity, event metadata, disposition/quarantine/hold identifiers, or unresolved provenance must remain excluded from training, ranking, candidate evaluation, scientific conclusions, and formal truth handoff. Do not infer or replace the UNKNOWN entry count. Do not alter Runner, control DB, historical rows, truth, EXT02, or confirmation data in this Coupling task.

## Wired entry points

- `scripts/coupling_ml/k6_v2_pipeline/consumer_exclusions.py`: pinned versioned registry and fail-closed linkage/provenance validation.
- `ingest.py`: frozen/Runner development, confirmation, and diagnostic import checks.
- `contracts.py`, `training.py`: role-bound collections and direct training-map provenance checks.
- `validation.py`: candidate OOF evaluation/ranking boundary.
- `confirmation.py`: confirmation evaluation boundary.
- `local_affine.py`: direct local-affine fit and LOO boundary.
- `tests/coupling_ml/k6_v2_pipeline/test_consumer_exclusions.py`: quarantine and valid-provenance fixtures.

## Resume instructions

1. Check current Coupling and Runner branch, HEAD, upstream, and dirty state. Preserve unrelated untracked paths.
2. Re-read the pinned Runner V2 owner disposition and registry. If authority changed, audit the new source before updating pins.
3. Keep the GPU hold active unless the separate Runner-authorized task validates all owner conditions and calls only the official release API. This continuation grants no hold or solver authority.
4. Commit only the explicit task paths after all checks pass; push normally. No force push.
