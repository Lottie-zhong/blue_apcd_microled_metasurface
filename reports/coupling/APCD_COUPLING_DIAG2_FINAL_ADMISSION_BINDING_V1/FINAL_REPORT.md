# DIAG2 Final Admission Binding

Status: **DIAG2_FINAL_ADMISSION_READY_AWAITING_AUTHORIZATION**

Zero-solver, read-only scientific binding only. No production Science Admission was issued or activated; no Controller, Worker, or scientific solver was authorized.

## Result

- Exact installed V2.1 patch release is pinned by the current installation. Immutable release inventory: 26/26 files match.
- The real installed V2.1 contract validator accepted both frozen A1/A2 attempt_001 requests through validate_diag2_contract. The Admission validator was not called.
- K6V3_TIME_DIAG2_A1_5NM_6PS / attempt_001: V2.1 contract preflight PASS; eight source/setup file SHA checks PASS; offline identity SHA 7a850ee7eecbdbdb697a02915f70efb4389f17ada01e60624890557768021e81 (not signed or registered).
- K6V3_TIME_DIAG2_A2_5NM_6PS / attempt_001: V2.1 contract preflight PASS; eight source/setup file SHA checks PASS; offline identity SHA 8b067085b1a2af1af48877e1fc9eef85e045301e7b3d741a59b31f8e082f891a (not signed or registered).
- Official 6 ps contract, 609D certification, exact two-entry/no-replay budget, and current bytes of the referenced Coupling ledgers were rechecked.
- No DIAG2 production science ledger exists while Admission is unissued. Offline fixture ledgers remain fixture-only and are not promoted.

## Frozen scientific binding

Batch: K6V3_TIME_DIAG2_V1_BATCH_001; A1/A2 only; attempt_001 each; maximum 2 total entries, 1 per case; automatic replay 0.
Official contract raw and canonical SHA-256: 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. Only allowed physical change from the parent contract is simulation time 3 ps to 6 ps; mesh is 5 nm and auto-shutoff 1e-6.
Candidate manifest SHA-256: 8472518baf1425243b05292ac882a141bd886f91524b1f2bd664e4f4d962e5c7. Retired bad candidate SHA afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f remains rejected and was not restored.
Profile coupling_609d_v1: 609 outputs; 440-460 nm, 21 wavelengths; orders -3..+3; TE/TM; reference plane 1722 nm. Certification SHA-256: 11ddbf2fc13e2dd34a9a4c4b07daf17c6d2c8275a64eb27fa3202e67cad204ca; verdict PASS. Six-ps physical truth remains NOT_RUN.

## Installed release and default deny

Release: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6. Manifest SHA-256: d4f37eeb249747eb07e1227ef9a64eb7a256712661a496d014e777e679a8b30a. Code inventory SHA-256: ea92f62348f6d32c15bb46a992d1ca370a159c7f645808a472ae4013a6a756e1. Inventory 26/26 PASS.
Installed validator module: D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_diag2_validator_b9abe87058d6\platform_v2\apcd_gpu_v2\diag2.py; diag2.py SHA-256: 1c0e6bbe5c4506e58eb6bba9948b79df850057662fbb5652ee5652c08b500b4a.
Installation marker SHA-256: fd6f673db4f5f318421bb1842ae2ceaca3885c4b04b48eeaec5b0bc44fcbbb47. Profiles empty; scheduler Disabled, demand-start false, zero triggers; Admission unissued; science binding unauthorized; Controller not started.
The old preparation candidate embeds the superseded base-release identifier. Its historical bytes are preserved; this report pins the actual installed patch. The Science Owner decision predates deployment and remains unchanged; it still records no production Admission.
The latest GPU Owner report recorded live pre-entry resource HOLD on 2026-10-13. This task did not refresh the live gate; a fresh global resource/exclusivity gate is mandatory before any future entry.

## Ledger identity and isolation

DOE56 execution ledger SHA-256, rehashed from current bytes: 9e277f111f3ba6e7399d74e730f05a1f0a69388be8e40506135b28d8ffc84367.
Coupling queue execution ledger SHA-256, rehashed from current bytes: a25cb5347cb97020c6abbddfdc99f669843b384c4f1932de5892fa249813572a.
These are existing Coupling authority ledgers, not the DIAG2 production Admission ledger. Dedicated production DIAG2 science ledger: NOT_CREATED; SHA-256 null by design while Admission is unissued. B/C offline fixture ledger SHA values are recorded as fixture-only in the JSON check.
No ledger was modified.

## Counters and safety

DIAG2 0/2; DOE56 4 entered / 52 unentered, FROZEN_NUMERICAL_ADVANCEMENT_HOLD. New solver entries 0; new ML fits 0; replay 0; Admission not issued; Controller/Worker not started.
No scientific contract, source/setup artifact, ledger, runtime profile, scheduler task, or release was edited. Only the four requested report artifacts were created.

## GPU Owner / Science Owner handoff

Only after separate Chat authorization:
1. Trusted Science Owner signs the canonical Admission through the supported owner API. Bind exact batch/case/attempt identities, official contract SHA, candidate manifest SHA, profile certification SHA, source/setup/candidate-FSP hashes, profile id, two-entry total budget, one per case, no replay, and DOE56 HOLD boundary. Initialize/append the dedicated production DIAG2 ledger through that authority and record its exact path and resulting SHA-256. Never hand-edit ledgers or reuse fixture hashes.
2. GPU Owner validates the signed Admission and request digests with the installed V2.1 validator; verifies profile binding, exact identity, budget isolation, no-replay and default-deny behavior in a Disabled release. Do not enable tasks or start Controller/Worker during binding.
3. Immediately before any separately authorized entry, GPU Owner runs a fresh global GPU/resource/process/lease gate and stops on unknown ownership or active contention. The prior recorded live gate was HOLD, not PASS.
4. Any later activation or entry requires separate explicit authorization. Preserve serial A1 then A2, one entry each, no replay, truth-before-next.

## Git scope

Worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; branch work/mdc-np-coupling-ml-v1; base HEAD e3a9528c1d5cf3eb4b27ff9a0b4201618d28f512. Final commit and push metadata are reported in the task response.
