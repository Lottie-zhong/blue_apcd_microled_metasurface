# APCD GPU EXT02 diagnostic identity and hold resolution

Date: 2026-10-04 (UTC evidence timestamp is in `IDENTITY_AND_HOLD_EVIDENCE.json`)

## Status

`PARTIAL — DIAGNOSTIC IDENTITY ENROLLED FOR SETUP PREFLIGHT ONLY; GLOBAL HOLD RETAINED.`

This task did not start a solver, run FDTD, or replay a case. The new diagnostic has no solver-entry authorization. Its proposed future budget (one entry, zero automatic replays) remains a proposal and is not a run permit.

## Historical case and new diagnostic identity

The production record remains `K6V1_EXT02 / attempt_001`, queue `52` (`RELEASED`). It has one `SCIENTIFIC_SOLVER_ENTERED` event, event `1680`, `2026-09-25T07:08:37.882954+00:00` UTC, `GLOBAL_SLOT_3`, fencing generation `7`. Its production pre-FSP SHA256 is `99248d02495d8a3124f712bdaf2291c5a058cfd4a6a85ace129b096381b98143`, base physical-contract SHA256 is `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`, and historical `terminal.json` SHA256 is `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded`. Those files and that entry were preserved; this historical truth is single-plane and is not a two-plane result.

The setup previously staged under the old controlled-overlay identity is not the historical production setup/truth. Its overlay FSP bytes were reused exactly for the new identity because the FSP contains no case identity and the requested science delta is unchanged. The new identity has independently bound `identity_link_manifest.json`, provenance, source manifest, proof, preflight envelope and case identity. Its monitor-overlay contract SHA256 is `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`; the old production base contract is `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`. The contract hash equality with the earlier prepared overlay reflects identical scientific contract content, not reuse of the old production contract to disguise a change.

The Runner's pinned versioned authority now enrolls `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` for the sole purpose of cross-height E/H label extraction consistency, excludes it from training, links the historical EXT02 truth and revokes future start authorization under the old overlay identity. The old production history remains in its original registry/events. A regression test verifies the old ID is rejected under the successor authority. There are zero branch-queue rows and zero lease events for the new diagnostic. The new authority explicitly sets `solver_entry_authorized=false` and `max_solver_entries_after_handoff=0`; `proposed_future_solver_entries=1` and replay budget 0 are not authorization.

## Live hold cause and release authority

Read-only snapshot: `D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3`, SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`, `1478656` bytes. `new_entry_hold=1`, generation `26`, health `PASS`. Active hold `hold-4a6eab94af3b4a6d8510ba2fe32a5b66` is GLOBAL, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, created `2026-09-30T14:40:13.441098+00:00` by `Shared V3 production containment / call v3-containment-c1481e55-20260930`.

Its cause is the unresolved Traditional queue21 duplicate-entry incident (`queue21-lineage-not-recoverable`, event IDs 1499 and 1506). S35's dispatch was denied pre-entry because the duplicate metric was 1; the hold metadata says no solver entry occurred in that failed dispatch. The active requirements prohibit dispatch while held, prohibit clearing/waiving the historical duplicate metric, and require no solver entry during the failed dispatch; the active hold's reason says entries remain held pending an explicitly authorized durable disposition or rebuild. The active row has `released_by=null` and `release_authority_hash=null`; it names no current release authority. The older generation-25 release applies only to S35/S39 serial authorization and does not release this generation-26 containment hold. This task made no control database write and did not call a hold-release API. GPU idleness was not treated as release evidence.

Current decision: **keep the global hold active**. Required missing condition: an explicit, applicable release authority and an authorized durable disposition/rebuild of the queue21 duplicate lineage, recorded through the official release process. Until then no new solver entry is allowed.

## Formal setup preflight

The final production adapter's `preflight-setup` passed for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` on route `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`. The current hold allowed this no-entry setup check; no slot or solver was entered. Result counters: `solver_invocations=0`, `scientific_entry_count=0`, `solver_run_called=false`, `post_entry_truth_proved=false`. The proof is a fresh setup LOAD/readback proof only, not solver truth.

The staged and source FSP are byte-identical, SHA256 `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`. Actual overlay added only `EXT02_POSTNP_DIAG_Z2000` while preserving `MON_POSTNP`, and configured six complex E/H components over the declared wavelength samples. The actual sampled z, solved local field mesh and PML inner face remain unavailable until a future solve. The frozen comparison reference plane, signs and thresholds are unchanged. No numerical dual-plane comparison exists.

The Coupling output SHA inventory verified **13 files with zero mismatches**. Review copies of identity, contract, manifest, LOAD proof and preflight JSON are in this report's `evidence/` directory; the large/source `.fsp` files are intentionally not committed and remain at the recorded Coupling path with their SHA.

## Verification and execution counts

Remote Runner checks: AST parse passed; `git diff --check` passed; `test_controlled_admission_v1.py`: **21 passed, 35 subtests passed**. These are software regression tests. The formal preflight is the real Lumerical setup LOAD check; it is not a solver validation. No other case or K6 geometry was admitted.

Task execution counts: solver entry **0**, FDTD run **0**, replay **0**.

## Key SHA256 values

| Item | SHA256 |
|---|---|
| `Historical production truth` | `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded` |
| `Historical production pre-FSP` | `99248d02495d8a3124f712bdaf2291c5a058cfd4a6a85ace129b096381b98143` |
| `Historical production contract` | `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` |
| `Diagnostic physical contract` | `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68` |
| `Diagnostic source/staged FSP` | `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30` |
| `Identity link manifest` | `de864bc6e85a8bb455766a5aaa06a4212370f87fe93f525a3aebd1e1a51a5d65` |
| `Source manifest` | `5aa33b546145ee92dc24d39bf47030661f03afb8b5da7817850c32f97e4fb9aa` |
| `Setup LOAD-only proof` | `245d4cfc34ad7c0069c7b831d3fc4df862694d4fee4687268ea6310b522aee37` |
| `Formal preflight result` | `697ceebdeb82ebdddfe026f72e7f558ad7f28c7ed3185222240b2f208727530f` |
| `SHA256 inventory` | `23390e9f5daef55208edd2c49d098324d36cd9e1377fd23b1f525435be7cb731` |
| `Runner policy` | `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45` |
| `Runner authority` | `15377a9fb5957c211026fadfcab833213bab99dc20129e8d17efd790af88b02e` |
| `Runner adapter` | `a9098bf77cc4ff4e62e3a87ef3029ec4bf4e16b4f94d64d008b062c2ac894e00` |
| `Runner validator` | `f23de4a1ab5ac204980e7c4c21febdd7127e5e06ed1d2a3d7c07c85ff38c5ac6` |
| `Control DB snapshot` | `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202` |

The full artifact list is `evidence/SHA256_INVENTORY.json`; the machine-readable hold and identity snapshot is `IDENTITY_AND_HOLD_EVIDENCE.json`.

## Next — do not execute

Do not start this diagnostic or create another attempt. First obtain the missing explicit authority and durable disposition/rebuild for the queue21 hold through its official owner-controlled process. Separately, a future task must grant exactly one solver entry for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` and perform a fresh `FINAL_LAUNCH_REVALIDATION` against the current control generation, owner/fence, quota, route authority and current FSP/proof hashes. Only then may the one-entry budget be consumed. Any post-entry failure stops; no automatic replay. The historical `K6V1_EXT02 / attempt_001` remains non-replayable.
