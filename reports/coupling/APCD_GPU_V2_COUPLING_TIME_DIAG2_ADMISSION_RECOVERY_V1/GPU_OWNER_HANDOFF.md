# GPU Owner handoff: V3 time diagnostic setup candidates

Observed host: DESKTOP-NNE313K. This package contains two independent setup candidates for the approved time-convergence diagnostic budget. It does not register cases, release a request, or authorize a solver invocation.

Candidate batch ID: K6V3_TIME_DIAG2_V1_BATCH_001
Dataset: APCD_COUPLING_V3_TIME_DIAG2_V1
Role: TIME_CONVERGENCE_DIAGNOSTIC_ONLY

## Candidate inputs

| Candidate case | attempt / role | ordered geometry (nm) | candidate FSP SHA-256 | fresh LOAD proof SHA-256 |
|---|---|---|---|---|
| K6V3_TIME_DIAG2_A1_5NM_6PS | attempt_001 | 120, 160, 165, 175, 160, 195 | 7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c | 75c17023d2507258fdd1939c9395624da0261ef21d798d93f826e54ccd6eb1e0 |
| K6V3_TIME_DIAG2_A2_5NM_6PS | attempt_001 | 210, 115, 175, 115, 180, 125 | 15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739 | 244631fa4a5adaed9393e3c303b52c9c865b15ca940dbb838020505c33ddd40b |

For each case, source_run_truth is an identity/provenance reference to the existing anchor run. setup_input is the direct saved 3 ps source FSP actually loaded to create the candidate 6 ps setup. These are distinct artifacts and are recorded separately in CASE_REGISTRATION_PACKAGE.json.

The only setup readback difference from each direct 3 ps setup input is FDTD.simulation_time: 3 ps to 6 ps. Auto-shutoff remains 1e-6; saved core mesh override remains 5 nm. This is not evidence about engine-generated mesh, convergence, or scientific truth.

## Required owner-side closure

1. Resolve the installed authority discrepancy captured in GPU_INSTALLATION_STATE.json. The current installed consumer does not support this dataset/role. Root INSTALLATION.json and SCIENCE_RELEASE_DENY.json conflict with CURRENT_INSTALLATION.json and CURRENT_SCIENCE_BINDING.json. The enabled scheduled action still names the DOE56 plan, so it must not be used for this diagnostic batch.
2. Do not use or modify the DOE56 release or scheduled DOE56 action for these candidates. Preserve the DOE56 ledger at 4 entered / 4 truth-valid / 4 labels-valid / 52 unentered and preserve V3 numerical advancement HOLD.
3. Through formal Runner APIs, create a separate diagnostic registration, isolated two-entry budget ledger, request, release/binding, and receipt path for this batch. Keep identities outside DOE56; set one entry maximum per case and replay disabled.
4. Ensure the formal manifest separately binds source_run_truth and setup_input hashes/paths. Bind the candidate batch ID consistently through registration, request, ledger, and release.
5. Run owner-side preflight and provide exact request/release/binding hashes, formal admission result, installed consumer code SHA, and current single-slot/owner evidence.
6. Only after formal admission and valid ownership, execute A1 then A2 through the official Runner path. Preserve-first on any post-entry failure. Do not infer scientific PASS from setup LOAD.

Coupling-side status: setup preparation passed; formal admission and scientific execution remain blocked/not performed.
