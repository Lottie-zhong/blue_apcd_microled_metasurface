# Continuation V2 — queue21 release snapshot / EXT02 route refresh

Read this file first, then `STATUS_SUPPLEMENT_AFTER_RELEASE_V1.md`, the unchanged `CONSUMER_EXCLUSION_REGISTRY_V1.json`, and the original `FINAL_REPORT.md`.

## Current Coupling state
- Worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch: `work/mdc-np-coupling-ml-v1`; verify current HEAD and preserve unrelated untracked state.
- Consumer registry remains unchanged at SHA-256 `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`.
- Queue21 count remains UNKNOWN and all quarantine rules remain active.
- Runner's current read-only control snapshot: generation 27, no active holds, new-entry hold false; the owner authority records release event 4 and the exact release-authority SHA in the status supplement.

## Route refresh gate
- Runner HEAD at capture: `5532a130439fa18f67986628ca74c4355a132b43`, upstream `0/0`, tracked worktree had uncommitted adapter/authority changes.
- Working-copy controlled authority SHA `cc44603accaa173bf879ce7ae36f5400a4cea378c7aa07564def64336d26ac3f`; adapter SHA `688be69e978b3b9e43e7a09c846aaa6e0448b1250a3e9a18098d4e3bf6df6308`. Do not use these as final route pins until Runner owner commits, pushes, and reports passing tests.
- The prior 4765... authority had an authorization-text contradiction; the working-copy text now aligns, but its successor authority is not yet a committed handoff.
- No fresh FSP LOAD/readback was performed by this update. Read-only file SHA checks confirmed source/staged FSPs remain `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`; physical contract remains `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`.
- Old route-bound manifests/proofs remain historical. Do not edit or delete them. Do not issue successor source manifest/proof/envelope until a committed Runner route is provided.

## Resume sequence
1. Recheck Coupling and Runner HEAD/status/upstream and read the successor Runner handoff.
2. Verify committed authority SHA, adapter pin, route policy SHA, and passing Runner tests; confirm no new contradiction.
3. Recheck unchanged FSP and contract bytes.
4. Perform a genuine LOAD-only readback with the pinned setup validator/Lumerical API; never call `run`.
5. Create a versioned proof and route-bound source manifest/envelope without overwriting historical proof files.
6. Hand the hashes to the Runner owner for formal preflight and FINAL_LAUNCH_REVALIDATION. Do not run either here unless separately requested.

No solver, training, sealed-response, hold-release, or Runner-modification authority is granted by this continuation.
