# APCD Coupling ML — Codex Branch Takeover

**Audit date:** 2026-10-12 (Asia/Shanghai)  
**Mode:** READ_ONLY_SCIENTIFIC_TAKEOVER  
**Role:** This Codex instance is responsible only for the Coupling ML branch. Chat dispatches each task; this branch executes within the assigned scope and reports evidence and outcome back in Chat.

## 1. Scope and execution boundary

This takeover reconciles the current Coupling ML worktree, dataset/model evidence, DOE56 and DIAG2 records, and static GPU V2.1 admission evidence. This handoff document is the only new artifact authorized by the takeover.

No FDTD/solver, model training, DOE56 continuation, DIAG2 submission, sealed-response access, GPU runtime/platform/release/scheduler edits, or live database/scheduler/process polling was performed. Historical training and solver counts below are taken from recorded reports and ledgers, not from new runs.

For any future solver attempt, retain the project entry protocol: atomically record case_id, attempt_id, solver_entered=true, entered timestamp, pre-FSP hash, and physical-contract hash before run; never replay an uncertain entered attempt. No solver authority is granted by this handoff.

## 2. Workspace identity and Git state

- Verified SSH identity on the contacted host: DESKTOP-NNE313K / desktop-nne313k\dell. The authenticated LAN address used was 192.168.1.106. The supplied project instructions list 192.168.1.107; that address was not positively verified in this takeover, so the address discrepancy remains an environment note.
- Canonical remote project: D:\project\blue_apcd_microled_metasurface.
- Coupling ML worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1.
- Coupling branch: work/mdc-np-coupling-ml-v1; HEAD 2996b6fc6589384f80d359aafdf4e72dfff6346a; upstream divergence 0/0.
- Before this document, git status --short --untracked-files=all showed 3,057 entries: 5 staged, 9 unstaged, and 3,047 untracked entries (staged/unstaged counts overlap for partially staged files). These pre-existing changes were preserved. This file was absent and not ignored before creation; it is created exclusively, not staged or committed.
- Main worktree was not modified: main HEAD 732d887340eccd0a86d30c485bdd964facb4f93c, 37 behind upstream, with pre-existing untracked files.
- GPU serial worktree was not modified: branch codex/apcd-gpu-v2-serial-production-v1, HEAD 03c0125c4a6b1e9f239a694d9052cbeb3229242a, with 18 pre-existing dirty entries. The GPU production-runner worktree also had 4 pre-existing dirty entries. GPU cleanroom was clean and one commit ahead.

## 3. Dataset and model evidence

### Frozen 156G dataset

Source: reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FROZEN_156G_DATA_MANIFEST.json  
SHA-256: cbd3aaa4b6ac966a2bc3fdb980e2ae3d16056d36ab80fefefe514e92328c67ea

- 156 cases, 156 unique case IDs/geometries; all are marked SCIENCE_VALID_UNDER_FROZEN_CONTRACT.
- Role counts: 113 DEVELOPMENT_GLOBAL, 32 DEVELOPMENT_OLD32, 11 DEVELOPMENT_LOCAL_AXIS.
- 21 wavelengths × 7 diffraction orders × 2 polarizations. State has 294 complex coordinates (588 Cartesian real values); the recorded P_scale targets add 21 values, for 609 scalar outputs.
- Inventory source: reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json, SHA-256 9e2687d61496850bca4f79b5fb24d20f446f47b56944c7a69edb127757a38403. Its recorded result is valid_count=156, DATASET_READY, no errors; confirmation, queue21, and independent diagnostic roles are excluded, with EXT02 separately distinguished.
- SHA-256 recheck covered only the canonical NPZ groups: old32 state 32 files / 11,322,354 bytes; new124 complex state 124 / 43,885,189 bytes; new124 ingested labels 124 / 1,199,042 bytes. Each group had zero missing files and zero hash mismatches. This was not a rehash of every FSP, H5, or raw-field artifact.

### H1 training result

Source: reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1/FINAL_SCIENTIFIC_REPORT.md  
SHA-256: 0ac4cce0f9df0fee83a3989c4f7b37dc87f620b7b355124879eaffbbbb653055

- Recorded CPU fits: 268/268 complete. No new fit was run during takeover. Recorded solver/FDTD/replay count is 0; confirmation-response reads and standalone P_scale fits are 0.
- H1 does not pass its conjunctive acceptance gate. RBF KRR held-out 124G state median/q95 = 0.872970/1.086444, routing = 0.182086/0.297147, total-power relative error = 0.248064/0.757838. MLP: state = 0.923843/1.109628, routing = 0.274689/0.373825, total power = 0.245158/0.778914. MLP seed-stability passes, but that alone does not pass H1.
- Frozen key limits include state median/q95 ≤0.5/0.8; routing median/q95 ≤0.05/0.10 and Pearson ≥0.95; total-power relative error median/q95 ≤0.15/0.30 and Pearson ≥0.95. Both model families fail the joint gate. Do not describe either as H1 PASS, a production surrogate, or an accepted replacement for the forward solver.

## 4. DOE56, numerical gate, and DIAG2

### DOE56 ledger

Source: reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json  
SHA-256: 9e277f111f3ba6e7399d74e730f05a1f0a69388be8e40506135b28d8ffc84367

- Authorized budget is 56 cases: 44 development, 4 diagnostic, 8 sealed.
- Latest ledger records 4 entered, 4 truth-valid, 4 labels-valid, and 52 unentered; auto-replay=0, confirmation access=0, training/P_scale fits=0.
- V3 numerical status remains HOLD. No DOE56 continuation was initiated.

### Numerical gate

Source: reports/coupling/APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1/V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1.md  
SHA-256: 82055e7186315beea86b82bc48e14fa5bd15ca4cc29a8c6f456ed26b28e12f17

The recorded four 5 nm / 4 nm comparisons all reached the 3 ps maximum and none reached 1e-6 auto-shutoff, leaving a temporal confound. Recorded A1 differences (state/routing/total power) are 0.1303/0.0450/0.1605; A2 differences are 0.1925/0.1166/0.3221, against limits 0.02/0.005/0.01. Repeated 5 nm runs were stable, but do not establish temporal or spatial convergence. Numerical advancement remains HOLD; 5 nm is only a provisional setting.

### DIAG2 admission state

Latest static continuation: reports/coupling/APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1/CONTINUATION.md  
SHA-256: f95d6a2e6d30791dd272244a23e34aad519c7aa77dcaa632180599c8f6adf10f

- Batch K6V3_TIME_DIAG2_V1_BATCH_001 has A1/A2 candidate attempt_001 setup FSPs. Contract SHA-256: afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f.
- The 6 ps candidates passed fresh native LOAD-only semantic readback. The only setup change recorded was simulation_time 3→6 ps; 5 nm mesh override and 1e-6 auto-shutoff were unchanged. A1 FSP SHA prefix 7d9f237c, LOAD proof prefix 75c17023; A2 FSP prefix 15042dc7, LOAD proof prefix 244631fa.
- Solver entry/invocation=0, replay=0, and no new 6 ps truth exists. Formal GPU registration/admission is absent; the installed consumer is recorded as supports_diag2=false. There were no training fits, P_scale fits, or confirmation reads.
- Earlier report reports/coupling/APCD_COUPLING_5NM_TIME_CONVERGENCE_DIAG2_V1/APCD_COUPLING_5NM_TIME_CONVERGENCE_DIAG2_V1.md has SHA-256 b3faeb92b426e1a72cc7b1c2931c6a1e80309d4e8b14f6504e376b3444d993c3 and records BLOCKED_PREENTRY. The newer continuation governs candidate setup status but does not authorize entry.
- The exact 2026-10-09 artifact APCD_Coupling_ML_Handoff_20261009_V1.md was not found in the searched Coupling reports or tracked Git paths. The current continuation and available production handoff were used instead.

## 5. Protection and GPU runtime findings

### Sealed and confirmation protection

- Protection record: reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/ORIGINAL_TRUTH_MODELS_CONFIRMATION_PROTECTION.json, SHA-256 09af90c988c2758466433505e2b46d657161105d73d378bbd5d3d785b8c80069. It records all_current_sha_match=true across 1,735 protected entries, with zero confirmation-response reads and zero fits.
- The 28 global plus 4 local confirmations remain sealed/not accessed; four local confirmations have no model/prediction and local13 is suspended. Geometry-only prediction files are not response truth.
- Role-access fixture: reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/science_admission_setup_review_v1/V3_SEALED_ROLE_ACCESS_TEST.json, SHA-256 4b012e34b185bfe34a1d3c8ef2899549390c5ef9744573006cd10ce04559c6c6. It is fixture_only=true and verdict BLOCKED_SAME_PRIVILEGED_SID_NO_RESPONSE_CUSTODY_BOUNDARY; ordinary_same_identity_os_read_denied=false and a synthetic read was allowed. Production-equivalent OS ACL isolation is therefore not demonstrated. This is not evidence that any real sealed response was read; this takeover accessed no sealed response and changed no ACL.

### Installed GPU V2.1 static markers

Runtime path: D:\apcd_runtime\gpu_platform_v2_serial_production_v1. No live runtime, DB, scheduler, or process status was queried.

- CURRENT_INSTALLATION.json (SHA prefix cea9b984) says enabled=true, FINITE_AUTHORIZED, and science_admission PASS.
- CURRENT_SCIENCE_BINDING.json (SHA prefix 27f1f64b) says science_authorized=true, max 56.
- Older INSTALLATION.json (SHA prefix a7773c83) references code head e662a92, reports deny reason FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND, and solver calls 0.
- SCIENCE_RELEASE_DENY.json (SHA prefix 8301556c) says science_authorized=false and requests empty.
- These durable markers conflict. Static compatibility evidence identifies installed consumer 03c0125c4a6b1e9f239a694d9052cbeb3229242a / source SHA prefix 92e933 and supports_diag2=false. GPU Owner must reconcile the authoritative binding/release state and DIAG2 role compatibility before any submission.
- The V2.1 candidate remains offline in the dirty GPU serial worktree; it is not committed/deployed. Its latest FULL_REGRESSION.log had no final result (about 65% at the recorded snapshot; SHA prefix e42f73af), so regression PASS is not established.

## 6. Readiness and next authorized gate

**Readiness: PARTIAL.** The 156G data and recorded training audit are available, but H1 fails; DOE56 numerical advancement is HOLD; DIAG2 has setup evidence only and no solver entry; GPU admission markers conflict; and production-equivalent sealed-response custody isolation is unproven. No physical or production action is authorized by this takeover.

Highest-priority dependency before any DIAG2 submission: obtain a static, owner-authoritative reconciliation of installed GPU release/binding markers and confirm a consumer that explicitly supports the DIAG2 role. Keep solver entry, sealed access, and runtime modifications closed until a separately dispatched task provides the required authority and scope.

Next tasks must be dispatched by Chat to this Coupling ML branch. Execute only the dispatched scope, preserve unrelated dirt, and return concise status, evidence paths/hashes, limitations, and Git state to Chat.
