# COUPLING_ML_QUEUE21_CONSUMER_EXCLUSION_V1

**STATUS: PASS — Coupling consumer-side exclusion implemented and tested.** This establishes data-consumer isolation only; it does not release the GPU hold, resolve the historical entry count, or authorize a solver run.

## Authority and decision

The excluded identity is `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, traditional branch, event IDs 1499 and 1506. Physical solver-entry count remains **UNKNOWN**. The latest GPU Runner worktree reviewed for this task is `88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35`. Its owner V2 disposition still marks the case `QUARANTINED_PENDING_COUPLING_CONSUMER_ENFORCEMENT`; the applicable global hold is recorded as ACTIVE, generation 26. No hold-release API was called. The task did not edit the Runner worktree, alter the database, delete artifacts, replay an attempt, read sealed confirmation responses, or launch a solver.

The registry preserves both historical V1 evidence and the current V2 owner decision. Pinned source hashes include V1 disposition `5e2ba9d6de8c94e2f4fe0af89ba9fc7b5a523763d35b863e083888f3f06c5065`, V2 disposition `468331313528c2a1d68e079617d84c8cac7baceff329e1384a65a38d1ec7de97`, owner decision `da6176fe98a1e7f38e149db417e419455720922527d6d9699772456f308a752a`, and scoped delegation `14ee2b2e84fb291775b9e2c4dbfb501b253c3d10b5ab88ecda9abea2575d55f1`.

## Consumer protections

The fail-closed registry is SHA-pinned at `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`. Its checks reject the exact case across all attempts, linked event/disposition/quarantine/hold metadata, unresolved associated artifacts, and truth without the import contract's independently verifiable provenance.

The guard is wired into Runner-truth import, development/confirmation/diagnostic imports, role-bound training collections, direct development fitting, candidate OOF evaluation/ranking, confirmation evaluation, and direct local-affine fit/LOO entry points. A distinct hash-pinned old32 case (`K6V1_S02`) remains accepted as the positive provenance fixture. Confirmation response values were not opened.

## Verification

Command: `N:\anaconda_envs\RCP_LCP\python.exe -m pytest -q tests/coupling_ml/k6_v2_pipeline/test_consumer_exclusions.py tests/coupling_ml/k6_v2_pipeline/test_ingest.py tests/coupling_ml/k6_v2_pipeline/test_confirmation.py tests/coupling_ml/k6_v2_pipeline/test_models_training.py`

Result: **32 passed in 13.01s**. Tests cover attempt_001/attempt_002 rejection before artifact access, linked event/provenance rejection, missing-provenance rejection, training/ranking/confirmation/diagnostic/local-affine isolation, and acceptance of the separate valid old32 fixture. Test fixtures do not count as scientific fits.

A newly added direct-local-affine test first exposed that the short-input size check preceded provenance validation. The fit API was corrected to run the same quarantine/provenance checks before any training-data processing; the final targeted suite then passed.

## Git and execution counts

Coupling worktree at review: `work/mdc-np-coupling-ml-v1`, starting HEAD `fbd5b376a4180f0b814e604dfbd77ea7171c2e30`, upstream count `0/0`. Exact task files are listed in `SHA256_INVENTORY_V1.json`. Pre-existing unrelated dirty/untracked paths remain untouched and unstaged.

- Coupling solver entries: 0
- Coupling model fits: 0
- Confirmation response accesses: 0
- Runner/GPU authority modifications: 0
- Hold-release calls: 0
- Delete/replay actions: 0

## Recovery boundary

Read `CONTINUATION.md` and the registry before resuming. Revalidate and version any newer Runner authority before changing these pins or consumers. Keep the queue21 identity and linked artifacts excluded, and keep the global hold active until the Runner owner's separate current-state/release conditions are satisfied by its authorized agent. This task does not authorize the EXT02 entry or any of the 160 K6 V2 cases.
