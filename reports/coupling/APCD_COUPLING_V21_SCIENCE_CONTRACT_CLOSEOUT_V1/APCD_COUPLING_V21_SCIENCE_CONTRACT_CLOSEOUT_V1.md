# APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1

**Status: PARTIAL.** Science contract, 609D profile, historical parity and isolated batch-ledger interfaces pass. DIAG2 admission readiness remains blocked on GPU caller integration. No 6 ps truth was run.

## 1. Candidate and source evidence

- Coupling source branch: work/mdc-np-coupling-ml-v1; source HEAD before this packet commit: b742750418d1b99dc4b5a5c1c40d51fab3eb54bc; ahead/behind upstream: 1	0.
- GPU candidate branch: codex/apcd-gpu-v2-serial-production-v1; HEAD: 8d5e10260c51c3ad7567ffe5a8fcb9f11c1590e2; origin ref: 2294f90270d5452355dd4ca282ef582b23077f49. Candidate is one commit ahead and not published.
- GPU Owner report SHA256: 243ba3ce730567d2033bb7e3d82665a2904f5c4b0104f6d84d72db73c3f9dd92. Its SHA inventory has 32/32 entries verified, zero byte/SHA mismatches.
- The report states V2.1 is partial (231 PASS / 0 SKIP); its 5/5 directed Science Owner tests pass, while the science interface remains partial. Production NOT DEPLOYED.

The current serial record construction in platform_v2/apcd_gpu_v2/serial.py omits five profile fields: request_sha256, physical_contract_file_sha256, source_acceptance_file_sha256, native_fsp, native_h5. This is the engineering integration blocker.

## 2. Formal DIAG2 science contract

SCIENCE_CONTRACT_6PS.json binds two cases to official frozen development-registry anchors:

| New case | Historical anchor | D1–D6 (nm) | Geometry SHA256 | 3 ps source FSP SHA256 | 6 ps setup FSP SHA256 |
|---|---|---|---|---|---|
| K6V3_TIME_DIAG2_A1_5NM_6PS | K6GDP2_DEV_G001 | 120, 160, 165, 175, 160, 195 | af948f30747ec9bfb5fc0bf2235a10cdb885b069f081fab306726784a787a2b3 | 0e6e522141ddbd0f9a4323cdc470293fd485af9493257a4ccd166383f6a62bb2 | 7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c |
| K6V3_TIME_DIAG2_A2_5NM_6PS | K6GDP2_DEV_G004 | 210, 115, 175, 115, 180, 125 | cb67af29fad4b5596ec7412b3ddd7ebcea0a5cb585c7919cb04f02e880f0a61b | 540ec80315bcec60619afb85f60dc894d46e40bffd87d5f8c6fb38b48a2651d1 | 15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739 |

CONTRACT_DIFF.json (SHA256 7803be2a2a1e4661519a89a425f7e39f2c66053695fe8da2fcf3dacf99c59228) proves the only scientific setting change is fdtd.simulation_time_s 3e-12 -> 6e-12. Auto-shutoff remains 1e-6. Native-M1 materials, structures, sources, meshes, monitors/reference planes, 21 wavelengths, TE/TM, seven Floquet orders, 609D labels and stop threshold remain bound to the parent contract. FDTD maximum time is a physical setting; external scheduler/task wall-clock cutoff is separate and unchanged.

Both 6 ps FSPs were setup-loaded only. Proofs record solver_api_run_called=false, scientific entries 0, replay 0. DIAG2 consumption remains 0/2.

## 3. SHA and canonical identity audit

- Parent 3 ps physics contract: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.
- Earlier nested Coupling candidate: raw SHA 6d15721bb3d69342c1b24f4fae687efb10bc55c375b44624aec717c7b351524b; declared semantic SHA afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f; recomputed under the frozen rule 5220e0f869bcd718e0e1caf807c7d75519ef424c3a600d3ad2f28d454018928d. These differ.
- GPU flat candidate: raw SHA f774f7bda8bde878b4c69f47d6ce8d68cb76926a978bd18256fdd9fe0d55aac1; declared semantic SHA d2a41f483c92577106d92f38a9e3d749b94a8cc46d767436e386968e71be4c82. It recomputes only when both embedded hash fields are excluded. It remains a candidate and was not adopted.
- Formal 6 ps contract raw and frozen canonical SHA: 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36; this is a new identity, not the copied 3 ps SHA.
- A1/A2 FSP hashes are separate artifact identities, not physics-contract identities.
- Case request v1 uses frozen ingest._canon. The request self-hash and source_acceptance.sha256 are excluded to avoid circularity; source_acceptance.path stays included. Independent serializer and _canon calculations both give 94ed521d572ce8676c3d5aea99ac91ce2dcf907bdbe08ab4a7cfcd2799fe51a3.
- Production Science Admission is NOT_ISSUED. B/C and historical audit hashes identify test/audit-only authorities.

Full hashes and recomputation rules are in SHA_AUDIT.json.

## 4. Profile certification and positive validations

coupling_609d_v1 is certified for offline identity/source checks, native FSP/H5 SHA binding, 609D labels, receipts and isolated-ledger protocol. C_hat, P_scale, TE/TM, Floquet decomposition, 1722 nm reference plane/de-embedding, H1/H2 and existing 156G labels were not changed.

- Targeted unit tests: 9 passed / 0 failed.
- Historical native parity: 2/2 completed development cases. Native FSP/H5 and existing extracted state/raw/order artifacts passed the frozen importer. All five arrays (C_hat real/imaginary, P_scale, eta, absolute-order power) match frozen labels exactly. The profile emitted receipts and an isolated in-memory dry-run ledger reconciled both. No production ledger was changed or case re-entered. Evidence: HISTORICAL_NATIVE_IMPORTER_PARITY.json, SHA256 4b9fbc436c7a3aad9ec486319c21040df00f4dd66b79a1ecc01c0d6a67648077.
- B/C positive offline interface: B has two DIAG2 test identities; C is a separate new Coupling test batch. All three profile calls returned 609 outputs and reconciled only into their isolated ledgers. Mock labels and H5 placeholders are marked TEST_FIXTURE_ONLY; they are not 6 ps truth. Evidence hashes: B_C_OFFLINE_LEDGER_INTEGRATION.json 71808d8d760c44c98d1ead403ea493c6489d7d078cb25fbf024abc5b009c9bac; B_C_PROFILE_CALL_VERIFICATION.json 8e50fe7981c67fdcd5f9752e7777f6c43d10f1bacd384e97b8276fb441b002f6.
- Negative checks reject unknown/previously entered identities, attempt/duplicate replay, over-budget admission, Consumer-supplied Science Owner, bad request SHA and cross-batch receipt. B/C budgets remain independent (2 and 1).
- No sealed/confirmation response was accessed. No FDTD, RCWA/FMM solve, replay, or ML fit occurred.

## 5. Science Owner decision

| Certification layer | Decision |
|---|---|
| SCIENCE_CONTRACT_IDENTITY | PASS |
| COUPLING_609D_PROFILE | PASS |
| HISTORICAL_NATIVE_IMPORTER_PARITY | PASS |
| NEW_BATCH_OFFLINE_LEDGER_INTEGRATION | PASS |
| DIAG2_SCIENTIFIC_ADMISSION_READINESS | BLOCKED |
| DIAG2_6PS_TRUTH_VALIDATION | NOT_RUN |

**BLOCKED reason:** the GPU serial caller omits the five fields listed in section 1. GPU Owner integration and complete regression are required before DIAG2 admission. This closeout grants no production entry authorization.

## 6. Guardrails and deliverables

DOE56 remains 4 entered / 52 unentered under FROZEN_NUMERICAL_ADVANCEMENT_HOLD; DIAG2 remains 0 entered. Production Science Admission, production ledger, Scheduler, Controller, Worker, GPU release and runtime state were not modified. The 156G dataset remains read-only.

Deliverables: SCIENCE_CONTRACT_6PS.json, CONTRACT_DIFF.json, SHA_AUDIT.json, COUPLING_609D_PROFILE_CERTIFICATION.json, HISTORICAL_NATIVE_IMPORTER_PARITY.json, B_C_OFFLINE_LEDGER_INTEGRATION.json, B_C_PROFILE_CALL_VERIFICATION.json, SCIENCE_OWNER_DECISION.json, GPU_OWNER_READONLY_HANDOFF.md, CONTINUATION.md, SHA_INVENTORY.json.
