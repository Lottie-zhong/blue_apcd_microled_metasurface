# APCD GPU V2.1 Real DIAG2 Validator Fix

**Final status: V21_REAL_DIAG2_VALIDATOR_OFFLINE_PASS**

## Result

The real frozen A1/A2 6 ps Coupling contract now passes the V2.1 physical-contract compatibility adapter offline, with original identities and bytes unchanged. This is not a Science Admission: the installed release remains disabled/default-deny, and no solver or entry was run.

## Instructions and authority reviewed

No AGENTS.md was found in the remote candidate tree; the user-provided AGENTS.md governs this task. The repo authority pointer and V2.1 disabled-deployment continuation were read. Older V1/V3 authority documents were treated as historical context and do not supersede this task. Their SHA values and timestamps are recorded in SHA_INVENTORY.json.

## Reproduced rejection and fix

At baseline commit a16f30d8cda254722fc77015f0cec9530b2d18c9, the old validate_diag2_contract in platform_v2/apcd_gpu_v2/diag2.py rejected both real identities with DIAG2_PHYSICAL_CONTRACT_NOT_FORMALLY_ACCEPTED. The first rejection occurred at the status allowlist before hash validation. The frozen contract is APCD_COUPLING_PHYSICS_CONTRACT_V2, status SCIENCE_OWNER_FROZEN_CONTRACT_ADMISSION_NOT_ISSUED, raw/canonical SHA 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. The old validator expected an already-admitted status, parent_physical_contract_sha256, temporal_settings.*, and FDTD.simulation time; the official contract carries parent_contract_file_sha256, nested temporal_stop/setup readback, and fdtd.simulation_time_s. The failure was a status/schema mapping mismatch, not a corrupted SHA.

The adapter in platform_v2/apcd_gpu_v2/diag2.py now validates the official schema, parent SHA, exact 3 ps to 6 ps physical difference, 5 nm mesh, 6 ps/1e-6 timing, A1/A2 case bindings, frozen 609D label contract, canonicalization rule, and pinned contract SHA. It does not write aliases into the contract. A1 and A2 both pass this contract-only validation.

Default denial remains intact and separately tested: an empty profile list denies with UNSUPPORTED_SCIENCE_PROFILE, and an unissued production Science Admission denies with SCIENTIFIC_ADMISSION_NOT_GRANTED. The frozen status being recognized as a physical contract is not treated as authorization.

## GPU resource gate

RESOURCE_GATE_OFFLINE_MECHANISM=PASS: the implementation requires three attributable WDDM samples, checks PID/create-time identity, denies Compute/CUDA and non-system WDDM activity even when nvidia-smi reports N/A memory, and records a fresh gate immediately before production launch claim. Synthetic failure injection and the full regression passed.

RESOURCE_GATE_LIVE_PREENTRY_STATUS=HOLD at 2026-10-13T16:03:51.075192+00:00: RTX 3080 reports 8014 MiB free, 2040 MiB used, and 1% aggregate utilization. GameViewerServer.exe PID 10484 engines 3D, VideoEncode utilization 8.0-58.0 percent. The bounded WDDM result is HOLD (WDDM_NON_SYSTEM_GPU_ACTIVITY_PRESENT); the complete formal GPU inventory gate was not run in this evidence refresh, so no live PASS is claimed. A fresh complete pre-entry gate is required before any future science entry.

The process scan found 2 ansysedt.exe GUI process(es) and 0 fdtd-engine.exe process(es). Their per-process NVIDIA memory is N/A; that is not interpreted as idle. PID 18936/40664 process identity and ancestry are recorded in LIVE_RESOURCE_GATE.json. Their business purpose remains unclassified; no command line, stdin, credential payload, or license context was read. V2 ledger slot generation is 95 with token/owner/request absent=True; DIAG2 task rows=0. No process was changed and no license context was read.

## Regression and safety counters

The full platform_v2/tests suite completed with 252 passed, 0 failed, 0 skipped in 372.99 seconds. The focused validator/profile/resource suite had 60 passed. Thirteen warnings were model/deprecation warnings. See TEST_RESULTS.md and FULL_REGRESSION.log.

Counters for this task: scientific solver entry 0; real FDTD 0; FMM/RCWA 0; ML fits 0; replay 0. Coupling DIAG2 remains 0/2 and DOE56 remains 4 entered / 52 unentered under FROZEN_NUMERICAL_ADVANCEMENT_HOLD. The Coupling worktree was not edited. Candidate B/C tests use isolated fixtures and synthetic numeric/importer payloads; they are not scientific truth or new physical validation.

## Installed release and source distinction

Candidate GPU source commit: b9abe87058d65cb2ba52c5ce1a7acb377a2ab048 on codex/apcd-gpu-v2-serial-production-v1; the code commit was pushed by normal fast-forward. It is not installed. The previously controlled, disabled release is 83c4fcd1329252e069760789ef5d0e92b02a781a at D:\apcd_runtime\gpu_platform_v2_serial_production_v1\releases\v21_83c4fcd1329252e069760789ef5d0e92b02a781a. Its installed diag2.py SHA remains 99f6c199fe077d0a2d2d5e420a9ccdda3a4c4ebc8c8eeabe5ef6419eff517a5e in the read-only check, versus the candidate source SHA listed in SHA_INVENTORY.json. This task changed no installation, Scheduler, ACL, production database, or release binding.

## Delivery

- Reproduction evidence: REPRODUCTION_EVIDENCE.json
- Live resource evidence: LIVE_RESOURCE_GATE.json
- Test summary and raw log: TEST_RESULTS.md, FULL_REGRESSION.log
- Next-run handoff: CONTINUATION.md
- SHA inventory: SHA_INVENTORY.json (SHA-256 be3fb7783338476b2c7a956d50687f61bbb252eaaa753c134d80d63f72347640)
- Report directory: D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\platform_v2\reports\APCD_GPU_V21_REAL_DIAG2_VALIDATOR_FIX_V1

The source patch is ready for one controlled deployment authorization. Science entry remains held until WDDM activity is absent and a fresh resource gate passes; DIAG2 also needs a separately issued production Science Admission and finite release. No solver authorization is implied.
