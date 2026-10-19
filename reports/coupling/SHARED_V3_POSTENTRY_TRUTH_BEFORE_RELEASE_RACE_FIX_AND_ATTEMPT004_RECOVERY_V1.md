# SHARED_V3_POSTENTRY_TRUTH_BEFORE_RELEASE_RACE_FIX_AND_ATTEMPT004_RECOVERY_V1

## STATUS

`CONTROL_RECOVERY_BLOCKED_TRUTH_VALID`

Zero-solver only for this task. No solver, replay, attempt_005, queue enqueue, direct runtime SQLite mutation, or recovery mutation was executed.

## ATTEMPT_004 CAUSAL TIMELINE

- `2026-09-25T02:26:53Z`: host started and `GLOBAL_SLOT_2` acquired at fencing generation 47.
- `2026-09-25T02:27:15Z`: GPU engine entry and `SCIENTIFIC_SOLVER_ENTERED`; ledger records exactly one invocation and no replay.
- `2026-09-25T02:28:08Z`: the old reconciler observed a no-truth/process-gap condition and wrote `POSTENTRY_NO_TRUTH`, quarantined the terminal record, and released the slot while the solver lineage was still running.
- `2026-09-25T02:36:26Z to 02:38:34Z`: the solver naturally produced durable native truth, LOAD-only evidence, solver return, post FSP, raw/projection/state/orders, scientific validation, and HF archive.
- `2026-09-25T02:38:34Z`: final persistence attempted to release the old owner and failed with `OwnershipMismatch('GLOBAL_SLOT_2')`; the saved scientific truth remained on disk.

## RECONCILER ROOT CAUSE

`closeout_owned_postentry_no_truth()` treated process disappearance/no-truth as releasable before requiring `SOLVER_RETURNED`, completion of native/post/HF truth finalization, or explicit post-entry failure adjudication. This created a release-before-truth-finalization race. The resulting queue state is `AMBIGUOUS_QUARANTINED`, while the saved truth is later valid.

## LIFECYCLE FIX

- Reconciler now preserves the owner and returns a pending/review state when solver return or truth finalization is not proven.
- Pending markers (`NATIVE_TRUTH_PERSISTING`, `POSTPROCESSING`, `PERSISTENCE_PENDING`, `FRESH_LOAD_PENDING`, `RELEASE_PENDING`, `PENDING_RECONCILE`) cannot trigger release.
- Release is allowed only after explicit post-entry failure adjudication or the normal durable-truth finisher path.
- `v3_g2_host.py` emits `NATIVE_TRUTH_PERSISTING` before native persistence, closing the pre-durable gap.

## ZERO-SOLVER RACE TESTS

- New post-entry race matrix: **17/17 PASS**, solver invocations 0, scientific entries 0, replays 0.
- Durable post-solver finisher regression: **20/20 PASS**, solver runs 0, replay 0.
- Full individual zero-solver set: **23/23 PASS**.
- Full suite: global **20/20**, branch **20/20**, chaos **12/12**.
- Foreign mutation count: **0**; direct SQLite mutations in tests: **0**.

## FULL REGRESSION

All applicable shared V3, admission, exact-permit, backend mutex, dispatcher detach, GPU observability/bundle/schema/resource, persistence, pre-entry recovery, post-entry supervision, PW launcher/manifest/complex-state, SHA canonicalization, and the new race tests passed. No scientific solver was invoked by regression.

## EXISTING TRUTH REVALIDATION

Saved-files-only validation passed:

- Native and post FSP fresh `LOAD_ONLY`: **PASS**.
- Native/post FSP SHA256: `20bbf75e8be30bcbd06d6389f02e0294e09a7d204b9df7af194b26cef54244ee` (identical).
- Native/post H5 SHA256: `ea20f121640054d3e2ecbfc43b3e95ebc97cef95b837162e6e041b7c127b8a36` (identical).
- Raw JSON SHA256: `3e6a1ce481f01bcd7c8f67ca8368a5f94d089622b753a48145de07e14793e8ed`.
- Wavelength grid: 440-460 nm inclusive, 21 points; raw/projection/orders/state grids agree.
- State payload: 3 planes x 21 wavelengths x 81 orders x 2 directions x 2 polarizations; six complex E/H fields; finite NPZ data; relative phase preserved; zero denominator count 0; evanescent coefficients retained as complex.
- H5: native and post each have 36 non-empty datasets and four monitor field groups.
- Energy closure maximum: `0.0`; reference-plane de-embedding round-trip maximum: `3.572017459575819e-16`; lossy-GaN complex-kz validation: PASS; order-sign contract: PASS.
- HF archive manifest and post-FSP verification: PASS/DURABLE.

Therefore the scientific result is **truth-valid on disk**. This does not change the control-plane verdict or production admission.

## ATTEMPT_004 RECOVERY

The sealed host configuration retains the original lease token, and its SHA256 matches the quarantined queue row (`09f239d01f47058dc8f9b8deaa0caa66a4e9fc38c33d567763db272bc113a56b`) at generation 47. However, the authoritative DB slot is now `FREE` with null owner and null lease token; the queue row is `AMBIGUOUS_QUARANTINED`. The existing recovery/finisher APIs require current owned-slot fencing and provide no safe adoption operation for a released slot. Re-acquiring the slot would mint a new owner and could mutate unrelated future ownership. Recovery was therefore intentionally not attempted.

## CONTROL SAFETY

- `PW_K6_PRODUCTION_NEW_ENTRY_HOLD=TRUE`, control generation 15, temporary runtime cap 1.
- All three authoritative DB slots are currently `FREE`; `K6V1_S15` and `K6V1_S16` remain `WAIT_RESOURCE_CAPACITY`.
- `K6V1_S14/attempt_004` has one scientific entry, one invocation, no replay; attempt_005 count is 0; S12/S13 replay count is 0.
- No active `fdtd-engine-msmpi.exe` or `mpiexec.exe` lineage remains. Unrelated `fdtd-solutions.exe` service processes are not solver lineage.
- The controller status JSON is an older stale snapshot and conflicts with the current DB; it was not used to mutate or release anything.

## GIT / CHANGED FILES

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD unchanged: `7d844158e2318a56b7d34eb01c26d3da45b98822`
- Worktree remains dirty from the pre-existing shared V3 work plus this race fix, tests, evidence manifest, and report. No unrelated dirty artifacts were deleted or staged.
- No commit and no push. No temporary recovery branch was modified.

## NEXT

Chart review of the control-plane recovery design: add a strictly fenced, explicit adoption/quarantine-resolution API before any attempt to reuse this valid truth. Do not run a solver, create attempt_005, or release the hold in this task.

Evidence manifest: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\SHARED_V3_ATTEMPT004_RECOVERY_EVIDENCE_MANIFEST_V1.json`
