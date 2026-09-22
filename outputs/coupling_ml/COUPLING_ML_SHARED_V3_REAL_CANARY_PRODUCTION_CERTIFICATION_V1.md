# Coupling-ML Shared V3 Real Canary Production Certification V1

## STATUS

PASS

## FINAL AUTHORITY

- COUPLING_ML_SHARED_V3_MULTISLOT_AUTOFILL_PRODUCTION_READY = YES
- FAST_PW_ADMISSION_READY = YES
- K6_DATABASE_PRODUCTION_READY = NO; FAST fidelity admission is still required.

## CANARY IDENTITY

- case: PW_PLANAR_STACK_REAL_CANARY
- attempt: attempt_002
- task: PW_PERIODIC_PLANAR_STACK_REAL_CANARY_CURRENT_V3_V1
- branch id: coupling_ml
- dimension: 3D
- wavelength coverage: 440-460 nm, 21 points
- slot: GLOBAL_SLOT_2
- physical contract hash: e3b98fbe8d8f39ebe244780bd23d4f3547524b555b8e9f2329ad0f783c9a1ef
- confirmed scientific entry: 2026-09-21T13:56:53.617818+00:00
- solver returned: 2026-09-21T14:20:52.583579+00:00
- solver duration between entry and return: approximately 1438.97 s

## SOURCE PROVENANCE

- closeout branch: work/mdc-np-coupling-ml-v1
- closeout HEAD: 8e87816d89f06134399666811880b2ba45af3963
- runtime metadata path: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\runtime\attempt_002\host_config.json
- recorded PW launcher provenance commit: fcf861bb0617fe32fcc6c263650dc03120758dfa
- committed launcher path: scripts/shared_fdtd/tools/pw_scientific_launcher.py
- relevant committed runtime fixes present in closeout HEAD: e13c7a2 and 8e87816
- runtime patch version recorded by the attempt ledger: 3.0.3-durable-postsolver-finisher
- static dependency audit found no runtime-critical import of the dirty file scripts/shared_fdtd/engine/host_lifecycle.py by the PW launcher path; it remains preserved and excluded.
- all unrelated dirty and untracked items remain untouched. The run recorded commit-level provenance; no separate per-file runtime SHA manifest was emitted.

## SOLVER ACCOUNTING

- confirmed scientific entries: 1
- solver invocations: 1
- solver retries: 0
- replay: 0
- duplicate scientific entries: 0
- attempt_003 queue rows: 0
- earlier pre-entry failures were recovered without scientific invocation and do not count as solver replay.

## TRUTH

- native FSP:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\native\PW_PLANAR_STACK_REAL_CANARY__attempt_002_native_d344c59a8500.fsp
- native SHA256: 333359706ca47dd80dab8e51f44323467f08ba4005b66f41a0ff7e7e4e927a50
- fresh LOAD-only validation: PASS
- validation record:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\post_fsp_verification.json
- native truth was persisted after solver return and before release.
- truth loss after solver return: 0.

## POSTPROCESS

- terminal record:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\terminal.json
- terminal status: SCIENTIFIC_VALID
- post FSP:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\post\PW_PLANAR_STACK_REAL_CANARY__attempt_002_post_d344c59a8500.fsp
- post FSP SHA256: 333359706ca47dd80dab8e51f44323467f08ba4005b66f41a0ff7e7e4e927a50
- raw output:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\raw\PW_PLANAR_STACK_REAL_CANARY__attempt_002_raw.json
- raw SHA256: b054294fa8b75954092015944afffd22287feba6c0ccc5970933852985046ec6
- 21-wavelength projection with A/R/T:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\projection\PW_PLANAR_STACK_REAL_CANARY__attempt_002_projection.json
- diffraction orders:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\orders\PW_PLANAR_STACK_REAL_CANARY__attempt_002_orders.json
- reference-plane de-embedding, modal normalization, energy accounting, order sign, and lossy-GaN physical-state fields are embedded in the raw result metrics/contract; no separate physical-state file was generated.
- standardized database payload schema: APCD_PW_STANDARDIZED_DB_PAYLOAD_V1, recorded in terminal/scientific validation; no separate DB payload file was generated.

## ARCHIVE / MANIFEST

- HF archive manifest:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\HF_ARCHIVE_MANIFEST.json
- archive staging manifest:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\archive_staging\HF_ARCHIVE_MANIFEST_d344c59a8500.json
- attempt ledger:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\attempt_ledger.json
- lifecycle events:
  D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\events.jsonl

## LIFECYCLE

- native truth durable: PASS
- fresh LOAD-only validation: PASS
- postprocessing: PASS
- HF archive: PASS
- final queue state: RELEASED
- final resource reservation: RELEASED
- final successful lease generation 24: one RELEASE_PENDING followed by one LEASE_RELEASED
- earlier generations were pre-entry-only recoveries and were released without solver entry
- GLOBAL_SLOT_1, GLOBAL_SLOT_2, and GLOBAL_SLOT_3: FREE
- no stale owner or active reservation remains
- current canary solver process: none
- scheduler/global capacity violation count: 0
- branch capacity violation count: 0
- pending reconcile count: 0

## FOREIGN STATE

- FOREIGN_MUTATION_COUNT: 0
- Traditional was not modified by this closeout.

## HISTORICAL FAILURE NOTE

The file
D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_COUPLING_PW_PERIODIC_PLANAR_STACK_REAL_CANARY_V1\case\attempt_002\terminal_failure.json
records an earlier pre-entry failure only. It has solver_entered=false and does not supersede the authoritative attempt ledger, event log, native truth, terminal.json, and database state for the later successful scientific entry.

## FINAL VERDICT

The completed real canary validates the shared V3 multi-slot/autofill lifecycle, durable post-solver truth, native-first persistence, fresh LOAD-only validation, no-replay semantics, PW launcher integration, postprocessing, archive, truth-before-release, and end-to-end scientific lifecycle.

COUPLING_ML_SHARED_V3_MULTISLOT_AUTOFILL_PRODUCTION_READY = YES

FAST_PW_ADMISSION_READY = YES

K6_DATABASE_PRODUCTION_READY = NO

## NEXT

FAST PW fidelity admission may be considered next. This closeout did not run FAST_PW and did not start any solver.
