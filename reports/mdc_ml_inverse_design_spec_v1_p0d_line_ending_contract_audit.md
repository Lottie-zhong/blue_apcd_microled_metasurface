# MDC_ML_P0D_LINE_ENDING_CONTRACT_V1_RESULT

## ENVIRONMENT

- Host: `DESKTOP-NNE313K`
- Worktree: `D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1`
- Branch: `work/mdc-ml-inverse-v1`
- HEAD: `ea293ddf2c66a339a60a5e7ff7b0e529eee17054`
- `core.autocrlf`: `true`
- Initial status: tracked diff and staging were empty; only the four pre-existing F0 smoke files were untracked; ahead/behind was `0/0`.

## ROOT_CAUSE

- Freeze-anchor and index content use LF.
- A prior ordinary Windows clean checkout with `core.autocrlf=true` produced CRLF worktree bytes because no path-specific checkout contract existed.
- The former audit hashed raw worktree bytes, so an LF-to-CRLF checkout-only transformation changed SHA-256 and caused a false payload-drift result.
- Git still considered those files semantically clean because its text clean filter normalized checkout bytes back to the indexed canonical content.

## GITATTRIBUTES_CONTRACT

- `.gitattributes` was absent and is newly added.
- Exact `text eol=lf` rules cover `.gitattributes`, the six immutable payloads, and `configs/mdc_ml_spec_freeze_manifest_v1.json`.
- `git check-attr text eol` returned `text: set` and `eol: lf` for all eight paths.
- `git ls-files --eol` returned `i/lf w/lf attr/text eol=lf` for all seven tracked contract paths in both the primary worktree and the real validation clone.
- No repository-wide rule, extension wildcard, or `* text=auto` rule was introduced.
- Git diff for all six immutable payloads remained empty.

## IMMUTABLE_AUDIT_SEMANTICS

- Anchor content: SHA-256 is computed from `git show <freeze-anchor>:<path>`.
- HEAD content: SHA-256 is computed independently from `git show HEAD:<path>`.
- Index content: the stage-0 index entry, regular-file mode, Git object identity, and SHA-256 are checked.
- Worktree content: `git hash-object --path=<path> --stdin` applies path attributes and clean-filter semantics. The resulting blob bytes are read to calculate SHA-256; a previously unseen drift blob is materialized only in an automatically removed temporary object directory, never in the repository object database.
- Raw worktree SHA-256, checkout EOL, raw/anchor equality, and normalization status remain diagnostic only.
- PASS additionally requires no unstaged semantic diff, no staged payload diff, a present non-symlink regular file, and a regular-file index mode.

## CLEAN_CLONE_VALIDATION

- Temporary clone: `D:\project\mdc_ml_p0d_autocrlf_clone_20260715`, outside the worktree.
- Clone command used `git -c core.autocrlf=true clone --no-checkout`; because `.gitattributes` is not committed, it was copied before the first checkout. Only `.gitattributes`, the audit script, and the test file were copied.
- Clone branch/HEAD: `work/mdc-ml-inverse-v1` / `ea293ddf2c66a339a60a5e7ff7b0e529eee17054`.
- Checkout EOL: every immutable payload reported `i/lf w/lf`.
- Formal audit: `PASS`; repository contract `PASS`; payload drift count `0`; all anchor, HEAD, index, and canonical-worktree SHA-256 values agreed.
- Cleanup: the resolved absolute path was verified, the temporary clone was removed, and a subsequent existence check returned false.

## NEGATIVE_TESTS

- Ordinary character mutation: FAIL as required.
- Staged payload mutation: FAIL as required.
- Descendant commit changing a payload: FAIL as required.
- Missing payload: FAIL as required.
- Directory/type replacement: FAIL as required.
- Manifest expected-SHA mutation: FAIL as required.
- CRLF-only raw-byte change with identical Git-canonical content: PASS as required, with raw mismatch retained as a diagnostic.
- Missing anchor, unrelated history, and immutable-inventory drift remain rejected by the existing tests.

## FILES_CHANGED

- Modified: `scripts/audit_mdc_ml_inverse_design_spec_v1.py`
- Modified: `tests/test_mdc_ml_inverse_design_spec_v1.py`
- Added: `.gitattributes`
- Added: `reports/mdc_ml_inverse_design_spec_v1_p0d_line_ending_contract_audit.md`
- All six immutable payloads are unchanged by Git diff and by anchor/HEAD/index/canonical SHA-256 comparison.
- The four F0 smoke files were not edited; their final SHA-256 values are checked against the startup values in the final gate.

## TESTS

- Targeted inverse-spec suite: `19 passed`.
- Full relevant suite (inverse spec, structure grammar, label views, F0 smoke regression): `45 passed`.
- Primary formal audit without bypass: `PASS`, payload drift count `0`.
- Real `core.autocrlf=true` clone formal audit without bypass: `PASS`, payload drift count `0`.
- Manifest deterministic reconstruction, anchor/descendant behavior, CRLF canonicalization, and mutation cases are included in the passing suite.
- Final `py_compile`, `git diff --check`, and trailing-whitespace checks are recorded by the closing gate.

## GIT

- HEAD remained `ea293ddf2c66a339a60a5e7ff7b0e529eee17054`.
- No files were staged.
- No commit or push was performed.
- Startup ahead/behind was `0/0`; the closing gate rechecks this value.

## DECLARATION

- CRLF-only checkout bytes no longer produce a false immutable-payload drift result when Git-canonical content is unchanged.
- Real content drift is still detected in HEAD, index, and worktree, including staged, deleted, and type-replacement cases.
- Exact `eol=lf` constraints were added only for the eight contract paths.
- No frozen payload, freeze-manifest expected SHA, or F0 smoke file was modified.
- No TMM, FDTD, Lumerical, model training, pilot generation, smoke runner, or output generation was run.
- The standalone P0-D freeze condition is satisfied by the recorded tests and audits.
- Remaining blocker: none within P0-D scope; committing or resuming F0 freeze remains a separate authorized task.
