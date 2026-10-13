# APCD_COUPLING_DIAG2_V21_ADMISSION_PREPARATION_V1

**Final status: DIAG2_V21_ADMISSION_PREPARATION_HOLD**

## Science Owner decision

The original two scientific identities and their source/setup evidence are carried forward unchanged. The formal 6 ps Coupling contract is unchanged. This is an inert review candidate: no production Science Admission was signed or activated, no V2.1 profile was enabled, and no unsupported request hash was invented.

Admission is blocked by two independent gates:

1. Installed V2.1 diag2.py rejects the frozen Coupling contract status and field layout before entry. No formal admission-shape adapter was found. This requires a GPU Owner-owned versioned adapter and regression; Coupling will not rewrite the science contract or SHA.
2. Global GPU resource exclusivity is not confirmed. WDDM per-process memory is N/A, GameViewer has active 3D/video-encode work, and five Shared V3 canary tasks remain manually launchable. Two EDT GUI processes passed bounded idle sampling, which does not establish global GPU idle.

No production ledger, Scheduler, release, Controller, or Worker state was changed.

## Required counters

| Counter | Result |
|---|---:|
| Solver entries | 0 |
| FDTD runs | 0 |
| New RCWA/FMM runs | 0 |
| New ML fits | 0 |
| Replay | 0 |
| DIAG2 entered | 0/2 |
| DOE56 | 4 entered / 52 unentered; FROZEN_NUMERICAL_ADVANCEMENT_HOLD |
| Sealed/confirmation response access | 0 |

## Candidate identities and provenance

DIAG2_ADMISSION_CANDIDATE_MANIFEST.json contains exactly A1 and A2, each attempt_001 and max one entry. It carries the source anchor FSP, direct 3 ps setup FSP, setup spec, source manifest, load-only proofs, candidate 6 ps setup FSP, and readback audit pins from the existing registration evidence. Both candidate FSPs are fresh-load-only artifacts, not solver truth. Case entry and replay counts remain zero.

The formal 6 ps contract raw/canonical SHA is 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. Parent 3 ps SHA is 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. The frozen ingest._canon rule remains in force. The only physical change is simulation maximum time 3 ps to 6 ps; auto-shutoff stays 1e-6. FDTD simulation time and platform task scheduling time remain separate.

## SHA discrepancy and V2.1 interface

The earlier nested candidate is retired. Its raw SHA is 6d15721bb3d69342c1b24f4fae687efb10bc55c375b44624aec717c7b351524b; it declares afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f, while the prior frozen-rule recomputation excluding the declared self-hash is 5220e0f869bcd718e0e1caf807c7d75519ef424c3a600d3ad2f28d454018928d. The old registration package pins afc06..., not the formal 51212... contract. The old file is a different candidate schema; the evidence cannot distinguish a stale declaration from intervening content change. It is not reused.

Installed diag2.py accepts only SCIENTIFIC_ADMISSION_PASS or FORMAL_GPU_CONTRACT; it requires top-level parent_physical_contract_sha256, temporal_settings.maximum_simulation_time_s and auto_shutoff_min, and difference field FDTD.simulation time. The Coupling contract status is SCIENCE_OWNER_FROZEN_CONTRACT_ADMISSION_NOT_ISSUED; its parent field is parent_contract_file_sha256, its time is nested in temporal_stop/setup readback, and its difference field is fdtd.simulation_time_s. GPU Owner confirmed no formal entry adapter exists. Do not add aliases, change the status, or replace expected SHA.

The installed release is v21_83c4fcd1329252e069760789ef5d0e92b02a781a, Disabled with science_authorized=false, controller_started=false and profiles=[]. The coupling_609d_v1 certificate passes offline, but the installed release has no profile binding. No valid installed request canonicalization is available, so request_sha256 remains unset. New source acceptance, native FSP/H5 destination and production DIAG2 ledger are not bound before an authorized Admission.

## Reused science evidence

### Historical native parity

The prior closeout's HISTORICAL_NATIVE_IMPORTER_PARITY.json is PASS. Original G001/G004 development FSP/H5 identities yielded 609 labels each with exact array parity for C_hat real/imaginary, P_scale, eta and absolute order. The audit was read-only and reconciled in isolation; it did not write an admission or production ledger, replay, or add an entry. This is not DIAG2 6 ps truth.

### B/C offline ledger integration

Existing explicitly marked mock fixtures passed: B_DIAG2_TEST_FIXTURE used an isolated budget of 2 and produced two fixture truth/label receipts; C_COUPLING_TEST_FIXTURE used a separate budget of 1 and produced one fixture receipt. Negative checks rejected attempt_002, Consumer self-authorization, duplicate/old G001 replay, over-budget entry, unknown identity and a B receipt used in C. DOE56 HOLD remained intact, sealed data was not accessed, and production ledgers were not modified. Prior offline regression covers truth-before-next. These fixtures validate interfaces only.

## GPU Owner pre-entry evidence

See GPU_OWNER_PREENTRY_HANDOFF.json. At the fresh snapshot, no V2/V1 Controller or Worker process, no fdtd-engine.exe, no APCD scheduled task running, and an empty V2 slot were observed. Both EDT GUIs passed three one-second-separated zero-engine samples; this is bounded to those GUI identities.

Eight long-lived fdtd-solutions.exe -server -hide API servers were present; their license checkout was not independently established. The RTX 3080 showed 1% utilization and 2226/10240 MiB. WDDM per-process memory was N/A. WDDM reported GameViewerServer.exe PID 10484 with 3D and VideoEncode activity. Five Shared V3 canary tasks are Enabled/Ready with AllowDemandStart=true; no current task process was observed, but manual alternate-entry paths remain.

The read-only global resource gate is therefore HOLD.

## Warnings

The corrected installed regression recorded 237 passed, 0 failed, 0 skipped, 13 warnings. One warning is Pydantic Plan.schema shadowing StrictModel.schema. Twelve are np.trapz deprecations, six in the installed GPU helper and six in the Coupling helper. They were non-fatal offline; the deprecations carry future NumPy compatibility risk. This Coupling task changed no implementation and did not rerun the full suite.

GPU Owner reported log SHA 017569..., while independent certutil on the same named path returned 1a0e.... This reference digest conflict is preserved in WARNING_CLASSIFICATION.json and is not used as an authority pin.

## Certification matrix

| Layer | Decision | Boundary |
|---|---|---|
| SCIENCE_CONTRACT_IDENTITY | PASS | Official contract and original A1/A2 source/setup pins verified by prior independent SHA audit. |
| COUPLING_609D_PROFILE | PARTIAL | Offline certification passes; current installed release has no bound profile. |
| HISTORICAL_NATIVE_IMPORTER_PARITY | PASS | Existing read-only native FSP/H5 parity for G001/G004. |
| NEW_BATCH_OFFLINE_LEDGER_INTEGRATION | PASS | B/C marked fixtures and isolated ledgers; no physical truth claim. |
| DIAG2_SCIENTIFIC_ADMISSION_READINESS | BLOCKED | Contract schema rejected; global resource exclusivity unconfirmed. |
| DIAG2_6PS_TRUTH_VALIDATION | NOT_RUN | No 6 ps solver entry or physical result. |

Science Owner decision: retain DIAG2_V21_ADMISSION_PREPARATION_HOLD; do not issue or activate Admission.

## Conditional two-case serial checklist

Only after separate Chat authorization and GPU Owner closure of both blockers:

1. Revalidate the disabled release, unchanged contract/profile pins, Shared V3 canary state and global GPU ownership immediately before entry. Stop on any unknown or active contender.
2. Submit through the GPU Owner's authorized admission interface; start A1 once and persist its entered receipt before launch.
3. Wait for A1 native FSP/H5, 609D labels and truth_valid. Only then start A2 once. Any uncertain result means stop, no replay, and no next entry.

No start command or active Admission is included.

## Git

Evidence baseline: Coupling worktree D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1, branch work/mdc-np-coupling-ml-v1, HEAD 4bbbc7b2b87d2ef7741ca309a7b6cf56996f32db, ahead/behind 0/0. The worktree already had extensive unrelated dirty/staged/untracked files. Only the seven files in this task directory are eligible for the allowlisted commit/push; foreign work is preserved. Final delivery HEAD and push result are returned in Chat to avoid a self-referential commit hash in this report.
