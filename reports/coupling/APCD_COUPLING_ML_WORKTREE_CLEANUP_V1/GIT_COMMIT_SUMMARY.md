# Git commit summary — APCD Coupling-ML worktree cleanup

## Intended exact allowlist

- `reports/coupling/APCD_COUPLING_ML_WORKTREE_CLEANUP_V1/WORKTREE_CLEANUP_REPORT.md`
- `reports/coupling/APCD_COUPLING_ML_WORKTREE_CLEANUP_V1/FILE_CLASSIFICATION_MANIFEST.csv`
- `reports/coupling/APCD_COUPLING_ML_WORKTREE_CLEANUP_V1/BACKUP_AND_SHA256_MANIFEST.csv`
- `reports/coupling/APCD_COUPLING_ML_WORKTREE_CLEANUP_V1/GIT_COMMIT_SUMMARY.md`

These are documentation and inventory artifacts only. No code, ledger, `.fsp`, `.h5`, `.npz`, `.joblib`, other scientific data, or pre-existing staged path is part of the allowlist.

The four pre-existing staged paths remain staged and unchanged. The code changes and large untracked historical science assets remain in place. This cleanup commit is local only; no push is performed while the worktree has unresolved task ownership and ledger state.

Tests: not run. The commit contains no implementation code; no relevant offline test is associated with the documentation-only change.
