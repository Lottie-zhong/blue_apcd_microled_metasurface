# Cleanup fast close and forward continuation

## Result

**PARTIAL.** The K6 read-only case/entry crosswalk and 272G offline analysis are complete. The worktree is intentionally not forced clean because protected and other-line changes remain. V2's snapshot and classification are reused; this pass did not rerun the full-tree inventory or move/delete scientific assets.

## Cleanup evidence reused

V2 recorded its end-of-pass inventory as 871 visible untracked files, 5 tracked modifications, and an empty index. This closeout adds report/data files; immediately before its allowlisted commit, `git ls-files --others --exclude-standard` reports 893 files. V2's source/extension/path-root breakdown remains in `../APCD_COUPLING_ML_WORKTREE_CLEANUP_V2/V2_CLASSIFICATION_SUMMARY.csv`; it is timestamped evidence, not a claim that every current path was reclassified.

At the V2 snapshot, source classes were 430 report/metrics/provenance candidates (4,581,306 B), 3 historical audit items (12,209 B), 171 other subline assets (2,438,545 B), 1 project instruction (4,118 B), 10 runtime/execution-state items (167,064 B), 247 science identity/provenance items (243,928 B), and 9 unresolved/other items (41,166 B). V2 also recorded 1,767 ignored model/array/checkpoint files across exact science-output trees; those counts overlap the output-tree view.

The five dirty tracked paths were preserved, unstaged and uncommitted: the DOE56 execution ledger, K6 power-normalization continuation, K6 preparation status, K6 queue ledger, and G026 continuation. The historical V2 record for the initial 4 staged/10 modified/6,936 untracked state remains in its own final report. No V3/V4 re-sweep was run.

## K6 close

The frozen manifest contains 128 unique authorized scientific IDs, with 3 initial entries plus 125 prepared queue IDs. Read-only cross-checks reconcile all 128 against current entry records and the final case-status file: 128 entered, 124 truth/label valid, 4 invalid, 0 unentered, 0 replay. The four invalid entries remain consumed; no attempt or ledger was rewritten. The old `Remaining127` directory label is not used as a budget count.

## Git and asset disposition

This pass stages only files under this task's exact report directory that are named in the allowlist used for its commit. The 3.59 MB `OOF_PREDICTIONS.npz` remains ignored and in place. FSP/H5/609D and Science Ledgers were not moved or deleted. Current ignored-path enumeration returns 15,749 paths and reports one Windows path-too-long traversal warning, so this figure is a lower bound, not a complete count.

The project branch is `work/mdc-np-coupling-ml-v1`, upstream `origin/work/mdc-np-coupling-ml-v1`; at the pre-commit snapshot the branch was 0/0 against upstream. Final exact status and commit/push evidence are in `FINAL_GIT_STATUS.md` and `GIT_COMMIT_AND_PUSH_RECORD.md`.

## Scientific boundary

`FAST=272G`; `H1=HOLD`; `NEW_FDTD=0`; `NEXT_BATCH_AUTHORIZED=0`; `DIAG2=1/2`; `A2=HOLD`; `DOE56=HOLD`; CVAE paused. No GPU Runner call/change or sealed-data access occurred.
