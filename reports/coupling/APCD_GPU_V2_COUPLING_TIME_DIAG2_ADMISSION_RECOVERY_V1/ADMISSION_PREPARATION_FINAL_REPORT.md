# APCD_COUPLING_V3_5NM_TIME_CONVERGENCE_DIAG2_V1 — admission preparation result

Status: PARTIAL / BLOCKED_PREENTRY
Engineering admission: BLOCKED
Scientific data: NOT_GENERATED
Time convergence: UNRESOLVED
5 nm canonical status: RETAIN_PROVISIONALLY
V3 numerical advancement: HOLD

## Result

Two 6 ps setup candidates were generated from the frozen A1/G001 and A2/G004 direct 3 ps setup inputs, then each was closed and freshly loaded through the native Lumerical API. The semantic readback audit passed for both candidates. It found one and only one difference per case: FDTD.simulation_time changed from 3 ps to 6 ps. Auto-shutoff remains 1e-6, and the saved core mesh override remains 5 nm.

This was setup preparation only. No FDTD solver entry or invocation occurred. There is no 6 ps native solution, no stop time or termination reason, no auto-shutoff trajectory, no native result H5/FSP pair, no independently extracted 609D label, and no 3 ps/6 ps output comparison. Therefore no time-stability or time-truncation conclusion can be drawn.

## Case identity and independent budget

Candidate batch ID: K6V3_TIME_DIAG2_V1_BATCH_001
The candidates are K6V3_TIME_DIAG2_A1_5NM_6PS and K6V3_TIME_DIAG2_A2_5NM_6PS, each attempt_001, role TIME_CONVERGENCE_DIAGNOSTIC_ONLY, dataset APCD_COUPLING_V3_TIME_DIAG2_V1. Their ordered geometry and anchor mappings are in CASE_REGISTRATION_PACKAGE.json. They are not DOE56 identities, are not in the 156G development pool, and have not been formally registered by GPU Owner. This work consumed zero of the two scientific solver entries.

## Setup and contract evidence

A1 candidate FSP SHA-256: 7d9f237ca3a57a2240c8a3cd3d753f8fe85f201ca132557b54336622252a3a6c
A1 fresh LOAD proof SHA-256: 75c17023d2507258fdd1939c9395624da0261ef21d798d93f826e54ccd6eb1e0
A2 candidate FSP SHA-256: 15042dc7d58eeab35ce00a900d1bb979de58c19c182b18723924c184a48c9739
A2 fresh LOAD proof SHA-256: 244631fa4a5adaed9393e3c303b52c9c865b15ca940dbb838020505c33ddd40b
Readback audit SHA-256: 83ad5ffed6480cbe732e5e8a07798107d909a83f4467d73fa321ff8f8d6243b7
Candidate contract SHA-256: afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f

The 5 nm statement is limited to the saved setup mesh override; engine-generated spatial mesh has not been measured. See CONTRACT_DIFF.json.

## Formal admission blocker

The installed consumer at release 03c0125c4a6b1e9f239a694d9052cbeb3229242a, source SHA 92e933cf20f08976607c16198cf6e07c3999fb4709f688dc501b6ee4f52cb633, does not support the diagnostic dataset/role. Runtime authority markers conflict: CURRENT_INSTALLATION.json and CURRENT_SCIENCE_BINDING.json name an enabled DOE56 release, while root INSTALLATION.json binds another code release and a deny receipt whose science_authorized value is false. The enabled Task Scheduler action names the old DOE56 plan. A stale binding references a controller PID that was not observed active. These are formal GPU-owner admission issues. No release, Scheduler, Runner, registry, or DOE56 ledger files were changed in this task.

The live DOE56 ledger remains 56 authorized, 4 entered, 4 truth-valid, 4 labels-valid, 52 unentered, replay 0. V3 numerical advancement remains HOLD.

## Required continuation

GPU Owner must resolve the installation/binding discrepancy and formally register both candidates in an isolated request and budget, without enrolling them in DOE56. Then, and only through the official Runner path after admission, the approved two-entry sequence can be run. Preserve the one-entry-per-case and no-replay rules. See GPU_OWNER_HANDOFF.md and CONTINUATION.md.
