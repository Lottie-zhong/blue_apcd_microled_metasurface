# GPU Owner read-only science interface handoff

Authority: APCD_COUPLING_ML_SCIENCE_OWNER_V1
Packet: APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1

Frozen files: SCIENCE_CONTRACT_6PS.json; CONTRACT_DIFF.json; SHA_AUDIT.json; COUPLING_609D_PROFILE_CERTIFICATION.json; POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1.json; POSTPROCESS_CONTRACT_RESOLVER_INTERFACE_V1.md; GPU_OWNER_OFFLINE_INTEGRATION_REVIEW_V1.json; HISTORICAL_NATIVE_IMPORTER_PARITY.json; B_C_OFFLINE_LEDGER_INTEGRATION.json; SCIENCE_OWNER_DECISION.json.

Formal 6 ps physics contract raw/canonical SHA256: 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. Parent 3 ps contract SHA256: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. Only allowed physical setting delta: fdtd.simulation_time_s 3e-12 -> 6e-12. Auto-shutoff remains 1e-6. Scheduler wall-clock deadline is separate and unchanged.

- K6V3_TIME_DIAG2_A1_5NM_6PS anchored to K6GDP2_DEV_G001; FSP SHA256 7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c.
- K6V3_TIME_DIAG2_A2_5NM_6PS anchored to K6GDP2_DEV_G004; FSP SHA256 15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739.

At initial inspection of the candidate HEAD, the GPU serial caller omitted request_sha256, physical_contract_file_sha256, source_acceptance_file_sha256, native_fsp, and native_h5. GPU Owner subsequently added these fields and resolver wiring in the uncommitted candidate. Science Owner's targeted wrapper review is 6/6 PASS, formal-certificate wrapper cases are 3/3 PASS, and the current 237-test full regression inventory matches all three dirty source/test hashes. This packet grants no production entry or V2.1 deployment.

Historical native parity and receipts passed read-only. B/C used marked mock labels/H5 fixtures only; they do not validate 6 ps physics. DIAG2_6PS_TRUTH_VALIDATION remains NOT_RUN.
GPU branch codex/apcd-gpu-v2-serial-production-v1, local HEAD 8d5e10260c51c3ad7567ffe5a8fcb9f11c1590e2; origin ref 2294f90270d5452355dd4ca282ef582b23077f49. Candidate is one commit ahead and not published. V2.1 remains not deployed.


## Versioned resolver interface

- Module: scripts/coupling_ml/k6_v2_pipeline/postprocess_contract_resolver.py
- Module SHA256: 01462d5850bbcb18fd64408e42e1fbddf8e43deb7dfbe7dfd474d6d365996536
- Entrypoint: k6_v2_pipeline.postprocess_contract_resolver.resolve_postprocess_contract(authority, case_id, attempt_id)
- Resolver schema: APCD_COUPLING_POSTPROCESS_CONTRACT_RESOLVER_V1
- Resolved mapping schema: APCD_COUPLING_RESOLVED_POSTPROCESS_CONTRACT_V1
- Certification file: POSTPROCESS_CONTRACT_RESOLVER_CERTIFICATION_V1.json
- Certification raw SHA256: f8a7729e786a2c4d636e6195e9d85d87ac2c848de031b9c052de84ac4a89fb59

Pin both resolver module and certification in GPU-owned configuration. Authority adds decoded resolver_certification and raw resolver_certification_file_sha. The returned resolved_contract has exactly materials, monitors, references_nm, samples_nm, stack_layers, wavelengths_nm; resolved_contract_sha256 uses ingest._canon over the versioned projection envelope. Fixed vector: c13356f4b4f51aabce9a82db23fdb503e6b6e159388ce7055da8c09e9cf1b75b.

Use the resolver values consistently through preflight, launch monitor selection, and postprocess. The current GPU integration re-evaluates the pinned resolver at these boundaries; its source hashes and contract SHA are checked on each call. Keep the projection digest in the serial record/receipt. Reject test-fixture-only and audit-only authorities in production; the GPU wrapper's generated TEST_FIXTURE_ONLY certificate is test evidence only, never formal Owner authority.

Science Owner independently ran six targeted offline tests and three additional B/C GPU-wrapper cases using the formal resolver certificate; all passed. GPU Owner's 237-test full regression has zero failures/skips, and its source inventory matches the current dirty GPU sources. Offline DIAG2 admission readiness is READY; actual production Science Admission remains NOT_ISSUED, DIAG2 remains 0/2, V2.1 is not deployed, and DOE56 HOLD remains active.
