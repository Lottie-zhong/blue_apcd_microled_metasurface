# GPU Owner read-only science interface handoff

Authority: APCD_COUPLING_ML_SCIENCE_OWNER_V1
Packet: APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1

Frozen files: SCIENCE_CONTRACT_6PS.json; CONTRACT_DIFF.json; SHA_AUDIT.json; COUPLING_609D_PROFILE_CERTIFICATION.json; HISTORICAL_NATIVE_IMPORTER_PARITY.json; B_C_OFFLINE_LEDGER_INTEGRATION.json; SCIENCE_OWNER_DECISION.json.

Formal 6 ps physics contract raw/canonical SHA256: 51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36. Parent 3 ps contract SHA256: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. Only allowed physical setting delta: fdtd.simulation_time_s 3e-12 -> 6e-12. Auto-shutoff remains 1e-6. Scheduler wall-clock deadline is separate and unchanged.

- K6V3_TIME_DIAG2_A1_5NM_6PS anchored to K6GDP2_DEV_G001; FSP SHA256 7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c.
- K6V3_TIME_DIAG2_A2_5NM_6PS anchored to K6GDP2_DEV_G004; FSP SHA256 15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739.

Current GPU serial caller omits these required profile fields: request_sha256, physical_contract_file_sha256, source_acceptance_file_sha256, native_fsp, native_h5. Add them in the GPU Owner workspace, then run complete integration regression. This packet grants no production entry or V2.1 deployment.

Historical native parity and receipts passed read-only. B/C used marked mock labels/H5 fixtures only; they do not validate 6 ps physics. DIAG2_6PS_TRUTH_VALIDATION remains NOT_RUN.
GPU branch codex/apcd-gpu-v2-serial-production-v1, local HEAD 8d5e10260c51c3ad7567ffe5a8fcb9f11c1590e2; origin ref 2294f90270d5452355dd4ca282ef582b23077f49. Candidate is one commit ahead and not published. V2.1 remains not deployed.
