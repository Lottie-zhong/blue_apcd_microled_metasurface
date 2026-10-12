# Production Codex workflow handoff — V3 5 nm time diagnostic

Updated: 2026-10-12  
Scope: execute the two already prepared 6 ps diagnostic candidates through the official GPU V2 controlled route, but only after current formal registration, admission, release, and preflight are independently verified.

This document is an operational handoff, not solver authorization. It does not authorize a Runner call, create a release, change a budget, or lift the V3 numerical hold.

## Verified starting point

At the handoff snapshot, the Coupling worktree is `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, branch `work/mdc-np-coupling-ml-v1`, HEAD `d1f0dca550fb92582d09063bd0ee009dc47d7e3b`. Verify the live host, identity, branch, HEAD, worktree status, and current Runner release before acting; preserve unrelated staged and untracked files.

The isolated candidate batch is `K6V3_TIME_DIAG2_V1_BATCH_001` (`APCD_COUPLING_V3_TIME_DIAG2_V1`). Both candidate setups passed fresh native LOAD-only readback. No scientific entry, solver invocation, truth, or label exists for either 6 ps candidate. The case package still records formal GPU admission as absent. DOE56 remains separate and unchanged at 4 entered / 4 truth-valid / 4 labels-valid / 52 unentered; `V3_NUMERICAL_ADVANCEMENT=HOLD`.

| Candidate | Attempt | Ordered D1…D6 (nm) | Candidate FSP SHA-256 | Fresh LOAD proof SHA-256 | Matching 3 ps repeat identity |
|---|---|---|---|---|---|
| `K6V3_TIME_DIAG2_A1_5NM_6PS` | `attempt_001` | 120, 160, 165, 175, 160, 195 | `7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c` | `75c17023d2507258fdd1939c9395624da0261ef21d798d93f826e54ccd6eb1e0` | `K6V3_NUM_REPEAT_A1` |
| `K6V3_TIME_DIAG2_A2_5NM_6PS` | `attempt_001` | 210, 115, 175, 115, 180, 125 | `15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739` | `244631fa4a5adaed9393e3c303b52c9c865b15ca940dbb838020505c33ddd40b` | `K6V3_NUM_REPEAT_A2` |

The existing `K6GDP2_DEV_G001/G004` records are parent-anchor identities; the package separately identifies the direct 3 ps setup inputs and matching repeat cases. Preserve and verify both provenance links. Do not substitute the parent-anchor truth for the matching 3 ps repeat result.

## Frozen execution boundaries

- These are two independent time-convergence diagnostic identities outside DOE56 and outside the 156G development and sealed-confirmation pools.
- Maximum budget: two new scientific entries total, one for each `attempt_001`; automatic replay is zero. No new attempt IDs, DOE56 ledger edits, model training, P_scale fitting, or confirmation access.
- Candidate physical-contract SHA-256: `afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f`. The sole declared change from the source 3 ps contract is `FDTD.simulation_time` from 3 ps to 6 ps. Keep the 5 nm saved core mesh override, `auto_shutoff_min=1e-6`, geometry, materials, MDC/spacer, source, boundaries, monitors, wavelength grid, reference plane, normalization, and modal definitions unchanged.
- Setup LOAD proves setup readability only. It is not solver admission, scientific truth, time convergence, or spatial mesh convergence.
- The 32-case confirmation set remains sealed. The DOE56 numerical-advancement HOLD remains in force even if both time-diagnostic cases pass their comparison.

## Production workflow

### 1. Recover and verify authority

Read the latest `CONTINUATION.md`, this handoff, `ADMISSION_PREPARATION_FINAL_REPORT.md`, `CASE_REGISTRATION_PACKAGE.json`, `TIME_DIAG2_PHYSICAL_CONTRACT_CANDIDATE.json`, `CONTRACT_DIFF.json`, `SETUP_READBACK_AUDIT.json`, both fresh LOAD proofs, `SHA_INVENTORY.json`, the latest official GPU Runner handoff, and the current installed release/binding authority.

Verify the remote host and user; Coupling and Runner worktree identities; live Git branches/HEADs; file hashes; case/attempt identities; both distinct source/setup provenance chains; current single-slot ownership; and whether the installed consumer formally supports this diagnostic dataset/role. Re-read the DOE56 ledger and numerical gate receipt without modifying either. A prior report, setup proof, or this document cannot substitute for live authority checks.

### 2. Establish isolated formal admission

The GPU authority owner must use the current official Runner APIs to create and validate a separate registration, request, two-entry ledger, release/binding, and provenance chain for `K6V3_TIME_DIAG2_V1_BATCH_001`. Bind both case IDs, their `attempt_001` identities, the candidate contract SHA, candidate FSP SHA, fresh LOAD proof, source setup/manifest, and source-run reference. Preserve the distinction between `source_run_truth` and `setup_input` in the formal manifest.

The registration must cap each case at one entry and the batch at two, with replay disabled. It must remain outside DOE56 and outside confirmation roles. Confirm installed-consumer support, current release and code hashes, single-slot owner/fencing, and complete formal preflight through the supported APIs. Do not reuse the DOE56 request or scheduled action; do not bypass a validator or construct a parallel launcher. If any formal authority or binding is absent or inconsistent, stop before entry and return the exact missing official artifact to its owner.

### 3. Run serially through the official controller

After the isolated request is formally admitted and all fresh pre-entry checks pass, let the official server-owned controller execute A1, then A2, with scientific concurrency fixed at one. Do not dispatch cases manually or overlap them.

Before each entry, the controller must revalidate the exact case/attempt, candidate FSP and contract hashes, source manifest and LOAD proof, entry budget, current owner, and empty slot. Record the formal entry receipt and timestamp. Preserve the complete solver lineage and logs, actual stop time/reason, auto-shutoff history, and wall times. Retain the solved FSP and its native H5 result as a paired artifact; the H5 must contain the full six-component E/H data, not coordinates-only output.

### 4. Close and ingest each case before advancing

For each entered case, require all of the following before the controller can advance:

1. Official Runner terminal state and one-entry/replay accounting agree with the case receipt and request ledger.
2. Solved FSP and sibling native H5 are durable and their hashes are recorded; a fresh native LOAD and official truth validation pass.
3. The frozen importer accepts the full truth with the existing 21 wavelengths, seven propagating orders, TE/TM coordinates, complete complex `C_hat`, and independent positive `P_scale` under the unchanged reference-plane and source-normalization convention.
4. The generated label, provenance, source-manifest identity, input truth hash, validation result, and label hash are durably recorded and pass Coupling ingestion.
5. Runner registry/ledger and Coupling case/label records reconcile; the GPU slot is released before the next case starts.

A case is not complete merely because the API returned, the solver exited, a setup LOAD passed, or an H5 file exists. Do not start A2 until A1 has reached the required terminal state, native truth validation, label-ingestion acceptance, reconciliation, and slot release.

### 5. Handle failures without replay

If a pre-entry check fails, preserve the evidence and use the official reconciliation path to prove entry remained zero; any further action must follow the formal request/controller state. If failure or ambiguity occurs after entry, preserve the original attempt, logs, FSP/H5 if present, receipts, and hashes; count the entry as consumed and never automatically replay it. Use only an authorized zero-solver recovery path where applicable. Do not infer entry=0 from a missing log or missing status. Stop advancement if the owner, entry state, truth lineage, or contract cannot be resolved safely.

### 6. Evaluate the time diagnostic without changing the science gate

Compare each 6 ps result only with its matching existing 3 ps repeat result (`K6V3_NUM_REPEAT_A1` or `K6V3_NUM_REPEAT_A2`) after verifying geometry, contract, extraction, and artifact identity. Keep parent-anchor identity as provenance context, not as a substitute comparison row.

Use the frozen DIAG2 comparison/evaluation protocol and unchanged physical reference, modal basis, normalization, H2, and H1 implementations. Report actual termination and auto-shutoff behavior as well as complex-state, per-order TE/TM amplitude/phase, routing, absolute-order power, `P_scale`, and total-power differences. Do not perform global-phase oracle alignment, fit a correction from the two results, change thresholds, or replace earlier truth. If the frozen protocol does not define a decision threshold for a reported quantity, report the measured value without inventing a PASS rule.

Interpret the result narrowly: it informs time-limit sensitivity for these two tested geometries and settings. It does not establish spatial convergence, validate all 156G labels globally, or clear the independent 4 nm numerical failure. Only the scientific owner may review the evidence and change the DOE56 HOLD through a separately versioned decision.

### 7. Produce durable closeout

Save the formal request/release/binding identifiers and hashes, both entry and terminal receipts, controller/worker logs, per-case timings, solved FSP/native H5/validation/label hashes, reconciliation results, the paired 3 ps/6 ps report, and exact execution counts. Update the DIAG2 continuation and SHA inventory using an exact Git allowlist; leave unrelated staged, dirty, and untracked files untouched. State explicitly whether each case entered, whether truth and labels passed, and whether either attempt failed. Do not read sealed responses or start training.

## Required handoff order

1. Current scientific and Runner authority, including live admission and ownership.
2. Formal isolated admission and fresh preflight evidence.
3. Official serialized A1 → truth/label acceptance → A2 progression.
4. Dual-ledger closeout and 3 ps/6 ps scientific comparison.
5. Updated continuation and SHA inventory for the next Codex.

This document records the workflow only. It contains no production start command and grants no new solver entry.
