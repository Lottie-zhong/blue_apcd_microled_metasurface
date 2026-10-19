# Git commit and push record

## Scientific closeout commit

- Branch: `work/mdc-np-coupling-ml-v1`
- Commit: `6f5d9bf2c4541d1cfe7f3c3343d61c432b4c3ca5`
- Message: `Add Coupling-ML cleanup and 272G closeout evidence`
- Parent before commit: `236d94f1b68e2dcdaa45d5b12f2f9d2b45c68592`
- Scope: 22 exact paths under `reports/coupling/APCD_COUPLING_CLEANUP_FAST_CLOSE_AND_FORWARD_RESUME_V1/` (reports, metric tables, fold identity, K6 crosswalk, run metadata, preregistration and offline analysis source).
- Review: pre-existing index was empty; staged name list matched the 22-file allowlist; `git diff --cached --check` passed. No `.fsp`, `.h5`, Science Ledger, Runner source, ignored `OOF_PREDICTIONS.npz`, or unrelated prior changes were staged.

## Push

The configured upstream was verified as `origin/work/mdc-np-coupling-ml-v1` with the expected branch. Before push the branch was ahead/behind `1/0`; normal `git push origin work/mdc-np-coupling-ml-v1` succeeded, and the post-push count was `0/0`. No force push or history rewrite was used.

`FINAL_GIT_STATUS.md` and this record are included in a second exact-path metadata commit and were pushed by the same normal branch workflow. The five preserved tracked edits and remaining unrelated untracked assets stay outside both commits.
