# APCD GPU Production Runner V1 handoff

**Status:** Existing approved-case Runner route remains available. Full Task Scheduler ownership of the Coupling serial queue is not qualified; the Scheduler currently owns only a single-case worker. Coupling reconciliation/controller integration is pending.

**Runner execution HEAD for the latest owner-approved diagnostic:** 472bf2ae4c5bc8faaea04adec13d0a441777fc3f
**Previous qualified HEAD:** `578bdb714fe1455064a8b750968d3afac92b4a12`
**Branch:** `codex/apcd-gpu-production-runner-v1`

## Production input contract

The V1 production setup validator is manifest-driven. It reads the current case and attempt from the immutable run manifest, then binds the setup check to that case's `PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1` authority manifest and Stage-1 LOAD-only validation artifact. S39 is a regression fixture; it is no longer a production decision constant.

For each case, copy the case ID, attempt, ordered geometry, canonical FSP path/hash, and scientific expectations from its approved Coupling authority artifacts. The CLI envelope keeps the Runner's strict core manifest and adds `physical_contract_path` plus a `setup_authority` object carrying both artifact paths and SHA256 values.

A generic S21 consumer example follows. It documents the input shape only; this maintenance qualification did not run the command or create a run ID.

```json
{
  "case_id": "K6V1_S21",
  "attempt_id": "attempt_001",
  "run_id": "<new-immutable-run-id-for-this-logical-attempt>",
  "geometry": [
    120,
    115,
    230,
    140,
    110,
    115
  ],
  "physical_contract_sha256": "32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5",
  "expansion_manifest_sha256": "4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f",
  "pre_fsp_path": "D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\outputs\\coupling_ml\\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\\K6V1_S21\\attempt_001\\setup\\runtime.fsp",
  "pre_fsp_sha256": "c1ff163da2f2ccac43343be2bc79f50c380144af133dd41694f6533e0fac5e30",
  "physical_contract_path": "D:\\apcd_runtime\\gpu_production_runner_v1\\contracts\\pw_contract_32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5.json",
  "setup_authority": {
    "authority_manifest_path": "D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\outputs\\coupling_ml\\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\\K6V1_S21\\attempt_001\\authority_input_manifest.json",
    "authority_manifest_sha256": "e48ed4488c025adf34d699779726a96bd6831a05fc9bf4f5a43a86144cebf11e",
    "load_only_validation_path": "D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1\\outputs\\coupling_ml\\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\\K6V1_S21\\attempt_001\\load_only_validation.json",
    "load_only_validation_sha256": "c7e39cd41aff41bc643199e92289fcc2a6415cb1781fe4e5db3e4d05004b5358"
  }
}
```

The same schema applies to every approved case; use the matching authority paths and values rather than S21 values. Set the GPU resource name frozen in the case specification, then invoke `adapter.py run-one <immutable-case-manifest.json>`. The Runner remains GPU-only, serial, single-slot, and no-replay.

## Checks retained

Before solver entry, the validator hashes and LOADs the unsolved source/staged FSP and checks exact case/attempt/ordered geometry, the frozen contract, MDC and spacer, materials, source/polarization/wavelengths, boundaries, monitor definitions and sample/reference planes, and the full-period mesh authority against the Coupling case authority and LOAD-only proof. It requires exact source/staged FSP SHA parity. It does not require solved result cards or call the solver.

After solver return, the existing strict truth validator remains unchanged: it validates monitor results, finite complex E/H, C_PW, powers, P_scale, energy closure, durable native H5/FSP/truth H5, and a fresh LOAD. GPU launch, the existing 1369 MiB admission threshold, single-slot locking, no-replay, persistence, and truth processing were not changed.

## Zero-solver Stage-1 input qualification

The frozen code commit passed all 38 focused tests and 3 subtests. The manifest-driven validator passed all 12 approved Stage-1 geometries; per-case setup LOAD, LOAD-only semantic parity, and dependency preflight passed. Source and staged FSP hashes matched for every case. Solver invocations: **0**. Scientific entries: **0**.

The ten additional Stage-1 inputs and the S35/S39 compatibility cases are listed below:

| Case | Ordered D1-D6 (nm) | Setup LOAD | Stage-1 LOAD parity | Dependency preflight | Solver / entry |
|---|---|---|---|---|---|
| `K6V1_S21` | `120, 115, 230, 140, 110, 115` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S42` | `195, 210, 165, 130, 230, 230` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S36` | `115, 210, 220, 100, 150, 100` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S31` | `220, 195, 210, 150, 140, 210` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S45` | `195, 120, 105, 210, 220, 215` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S32` | `105, 190, 105, 115, 105, 225` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S47` | `165, 160, 105, 100, 230, 170` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S33` | `170, 175, 155, 150, 190, 105` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S37` | `215, 170, 110, 180, 105, 130` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S48` | `110, 100, 225, 205, 195, 175` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S35` | `110, 145, 225, 105, 185, 215` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |
| `K6V1_S39` | `175, 100, 125, 120, 100, 230` | PASS | PASS (0 mismatch) | PASS | 0 / 0 |

The ten additional inputs were: `K6V1_S21`, `K6V1_S42`, `K6V1_S36`, `K6V1_S31`, `K6V1_S45`, `K6V1_S32`, `K6V1_S47`, `K6V1_S33`, `K6V1_S37`, `K6V1_S48`. S35 remains `RECOVERED_TRUTH_VALID`; S39 remains `DONE / SCIENTIFIC_VALID` with its existing GPU canary. Neither history was changed or replayed.

## Existing S39 GPU qualification and durable report

- Existing immutable GPU canary: `S39-20261002T075624Z-30a1c44a`.
- Existing canary evidence: `reports/apcd_gpu_production_runner_v1/S39_CANARY_20261002.json` (SHA256 `06338557e28a473e880d5becd057b4c5b24ccf40b49e6758203bb360bf778a3a`).
- New zero-solver qualification: `reports/apcd_gpu_production_runner_v1/GENERIC_SETUP_VALIDATOR_ZERO_SOLVER_20261002.json` (SHA256 `45f22f900ab07157527645815fb5ec14a98631a0ebaac9da25aad1c6e8b36c5f`).
- Handoff JSON: `APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.json` (SHA256 `ca7e4a9fcc15ccb60f4921feb788bf3663e1b8fd3c56f64892894cc8299df599`).
- Authority: `APCD_GPU_PRODUCTION_RUNNER_V1_AUTHORITY.json` (SHA256 `021951707cd94d62ca93076f5f2a6867b400df4c9921932286b32ffc1840972c`).

## Freeze and handoff

This is a narrow V1 maintenance revision. Runner development is frozen again. Resume Coupling-ML work through this V1 Runner using the approved per-case authority manifest; do not change the scientific contract or replay any entered attempt.

## Controlled-admission recovery closeout (2026-10-04)

**Closeout status:** `READY_FOR_ONE_AUTHORIZED_EXT02_ENTRY` applies only to `K6V1_EXT02 / attempt_001` with the declared monitor overlay. It does not authorize a K6 geometry sweep, additional attempts, or any other new case. The existing 12-case route and its real Stage-1 setup evidence remain unchanged.

The final production adapter and Runner core used for the checks below have SHA256 `b7a1d074b3ab776cb1d192868192ad3a300a5192af3c439b35bfa6f0dea6d106` and `c97f459ffb3434d1a9419d8f203de2ca34630748c92626ff3d967edcfbd4f6aa`. Controlled route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`; policy SHA256 `e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f`; authority SHA256 `e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec`.

The Runner invokes a controlled pre-entry callback after setup LOAD and before writing `SOLVER_ENTERED`. That callback rereads the route envelope, per-case authority, contract, source manifest, staged FSP and LOAD proof; rechecks the content fingerprint and current GPU quota; then the Runner checks owner/fencing again before entry. A changed file or authority fails pre-entry. The recorded `control_generation_sha256` is a content-addressed Runner fingerprint, not an externally managed monotonic controller generation. The setup-only preflight reports no GPU snapshot or quota reservation; the one-run start callback must check the live 1369 MiB threshold.

### Final EXT02 setup preflight

The final `preflight-setup` used adapter SHA above and the real Lumerical 2025 R1 API. Result: **PASS**, `solver_invocations=0`, `scientific_entry_count=0`; source/staged semantic mismatches: 0; setup LOAD proof parity mismatches: 0. The fresh structural readback preserved all four existing monitors and added only `EXT02_POSTNP_DIAG_Z2000`.

| Artifact | SHA256 |
|---|---|
| Physical contract | `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68` |
| Source and staged FSP (identical bytes) | `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30` |
| Source manifest | `77107310820f44f19aff32baa8bc2db5170775187025fa95cee76ef2ba6d7ffb` |
| Setup LOAD-only proof | `2e97596b983df1b11d3d0a06309df41cabff6c7076917a30ebf446459f3ce386` |
| Setup contract fingerprint | `95c40a99da6ca199e297496a638f051a4f1d1547c2d25b86455a2c4bf3afbea2` |
| Final preflight report V2 | `916b6e46c26e26346043bad43efc70413c07a7917dd4c3535654f143405f3a7e` |

The diagnostic plane is configured at z=2000 nm, with full 1740×290 nm period coverage, E/H components `Ex,Ey,Ez,Hx,Hy,Hz`, 21 samples from 440–460 nm, nearest-mesh-cell interpolation and unit downsampling. Its frozen common reference plane is z=1722 nm. Lumerical setup LOAD readback of `NP_D1…NP_D6` gives z-min 1212 nm and z-max 1712 nm (500 nm height); the configured diagnostic plane is 288 nm above the NP top and the reference plane is 10 nm above it. These are setup coordinates, not solved field-grid coordinates.

The NP-derived 5 nm mesh region reads back as z=1112…1812 nm (center 1462 nm, span 700 nm); the diagnostic plane lies outside that local region. The other configured mesh region is 10 nm steps over z=1087…1837 nm. FDTD z boundaries read back as −600 and 3000 nm with eight PML layers; the configured plane is 1000 nm below the +z outer boundary. The actual sampled monitor z, generated local mesh coordinates/spacing at z=2000 nm, and PML inner mesh face are unavailable before solving and remain post-run checks. Periodic x/y boundaries and 1740×290 nm spans read back unchanged.

The setup LOAD-only proof means only that this unsolved setup can be loaded and its declared structure read back. It is not a solver-result or durable-truth proof. There is no EXT02 post-entry truth yet.

### Second-plane persistence and extraction

The original EXT02 baseline used launcher SHA256 `e4de8da6a824c02b3d0425c3e3c76f45111e369ad6a20237e464b0e6f7dce908`. The current immutable pinned backend is `pw_powernorm_v1_aaaa25b53a9a3322` with launcher SHA256 `7639b9d07f041d5f8af3121286f6ce5aae4d8b18b66f5368052c627da219307f`; the postprocessing power-fraction mapping was updated and independently audited on one archived V2 case. GPU launch semantics and GPU-observability dependencies remain unchanged. For the exact authorized overlay, the adapter extends the launcher's field-monitor list with `EXT02_POSTNP_DIAG_Z2000`; it does not create another GPU launcher or change the standard raw export. After solver return, the adapter waits for a stable H5 sidecar with at least five monitor groups and all six numeric E/H component datasets in every group, fsyncs it, and records its SHA256. The Runner also inventories the sidecar hash before truth completion.

The new extraction CLI is `scripts/shared_fdtd/gpu_runner_v1/extract_controlled_monitor_load_only_v1.py` and accepts `--run-dir <immutable-completed-run-directory>`. It requires the archived `run.fsp`, `run/run_output.h5`, `truth.h5`, manifest, status, validation, hashes, setup validation, pre-entry revalidation, solver log/stdout, process-exit provenance and runtime timeline. It requires exactly one entered solver, `DONE`, fresh LOAD and `SCIENTIFIC_VALID`, hashes consistent with the inventory, and GPU engine lineage. It then LOADs the archived FSP and reads E/H by the exact new monitor name, checks finite six-component data, coordinate agreement, wavelength grid and H5 group/coordinate mapping, and writes a separate NPZ plus JSON metadata under `monitor_extraction/`. Missing/corrupt/schema-mismatched data is an extraction failure; it never starts or replays the solver.

The generic LOAD/H5 mapping was exercised against an existing S39 archive: `MON_POSTNP` matched H5 `Monitor2`, actual z=1802 nm, 21 wavelengths 440–460 nm, shape `(349,59,1,21,3)`, all six finite E/H components. Probe report SHA256 `3a8ea1742de06b0d100f508bd40cb9084f45a7fe8cc004bc095f3987ca5af92b`. This validates the generic existing-monitor reader only. There is no real EXT02 second-plane result yet; the new monitor persistence path and extraction against that monitor remain pending its single authorized entry.

### Regression and execution boundary

Final remote suite: **68 passed, 38 subtests passed** across the controlled admission, second-monitor extraction, pre-entry/H5, core Runner and adapter test modules. These are offline/synthetic tests. The prior real Stage-1 setup LOAD evidence remains 12/12 as documented above; those FSPs were not reloaded in this closeout. Tests verify the legacy IDs stay on their existing route and the controlled route rejects them, along with unapproved geometry/monitor changes and changed envelope, contract, file hashes or proof.

This closeout performed setup LOADs and read-only extraction of an existing S39 archive only. EXT02 solver entries: **0**; FDTD runs: **0**; post-entry replays: **0**. No K6 new-geometry authority was added. The dual-plane scientific comparison, including actual sampled z/local mesh/PML readback and frozen same-reference-plane de-embedding, has not been performed.

### Next action — do not execute from this handoff alone

Before the one future entry, recheck the exact EXT02 case/attempt authority, current route/policy/contract/setup/proof hashes, zero prior EXT02 solver entry, owner/fencing, current resource threshold and immutable staged setup. Build a new immutable controlled run envelope with a unique run ID; do not pass the setup-only `formal_preflight_envelope.json` to `run-one`. Invoke the existing adapter/backend once for `K6V1_EXT02 / attempt_001`, with no automatic replay. Require GPU process lineage, durable FSP and sibling H5, fresh LOAD, `SCIENTIFIC_VALID`, and `RELEASED` before running the extraction CLI on that completed run directory. Then compare `MON_POSTNP` and `EXT02_POSTNP_DIAG_Z2000` using the frozen reference plane and no global-phase oracle alignment. Stop on any post-entry ambiguity or missing truth; do not replay.


## K6 V2 owner enrollment — setup only (2026-10-04)

- Versioned authority: `APCD_GPU_RUNNER_K6_V2_OWNER_ENROLLMENT_20261004_V1`; SHA256 `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`.
- Frozen package/inventory SHAs: `22560277c3cd7032e48de6ef5b0023986eefe5aba3c3de07b6eff2bf51dc33f9` / `f4497dc646588bf4b83dce5e022d5aa9f2bf48646a298fa78b9fe7adc70bab08`.
- 160 geometries enrolled for setup only; 128 development and 32 confirmation. Every solver-entry flag is false and budget is zero.
- Setup LOAD/PREFLIGHT counts: {'SETUP_LOAD_PASS': 160, 'SETUP_FAILED': 0, 'PENDING': 0} / {'FORMAL_PREFLIGHT_PASS': 160, 'FORMAL_PREFLIGHT_FAILED': 0, 'BLOCKED_SETUP_NOT_READY': 0, 'PENDING_SETUP_PREFLIGHT': 0, 'PENDING_SYSTEMIC_FAILURE': 0}. Solver, FDTD, replay and training counts are zero.
- Confirmation responses were not read; manufacturing authority unresolved. Queue21 hold remains active (`hold-4a6eab94af3b4a6d8510ba2fe32a5b66` ACTIVE, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, new_entry_hold=1, generation=26, control DB SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`).
- EXT02 history and truth are unchanged; diagnostic solver authorization remains false; prior setup proof is stale for the new authority digest and requires current-route preflight before future use.
- Coupling status: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_GPU_RUNNER_K6_V2_OWNER_ENROLLMENT_AND_SETUP_PREFLIGHT_V1`.


## Project-owner recovery and one-entry EXT02 diagnostic (2026-10-04)

This is the current status; it supersedes earlier setup-only EXT02 notes. Queue21 remains quarantined with physical entry count UNKNOWN. The owner-approved release event 4 released hold hold-4a6eab94af3b4a6d8510ba2fe32a5b66 at generation 27. Coupling registry SHA256 01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261; all 12 inventory items verify and the report records 32 focused tests passed. The registry's generation-26 hold is a creation-time snapshot.

K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001 had exactly one run-one call and one solver entry, zero automatic replays. Execution HEAD 472bf2ae4c5bc8faaea04adec13d0a441777fc3f; state DONE; fresh LOAD and SCIENTIFIC_VALID PASS. FSP SHA256 68ae5cd34144bbe908fc57a5628ac041a4bef2be35058fc614133f58233b27df; H5 sidecar SHA256 3ae7828f30ec1edcd6e8493461064325163ecd3fa993bb7baefb7cf212551077; truth H5 SHA256 05495a2d202795fd215474ac63c461558269efed05581e528048ed383627eb25. MON_POSTNP and EXT02_POSTNP_DIAG_Z2000 were extracted from archived FSP in load-only mode and matched to H5 Monitor2 and Monitor4. Actual sample z values are 1801.9999999999932 nm and 2006.6041666666679 nm; both reference z=1722 nm.

Coupling handoff manifest: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1\EXT02_COUPLING_HANDOFF_V1.json (SHA256 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75). Runner did not run the numerical comparison. Actual local mesh spacing at the two planes and PML inner face remain unknown. The diagnostic budget is consumed; no attempt_002 or V2 solver entry is authorized.


## K6 V2 development budget update (2026-10-05)

This update supersedes the 2026-10-04 setup-only budget and generation-26 hold snapshot above. The current project-owner recovery released the queue21 hold through official release event 4 at generation 27; the exception remains quarantined with physical entry count UNKNOWN. This administrative recovery does not certify queue21 truth.

The pinned versioned route authority is `a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35` (`APCD_GPU_RUNNER_EXT02_AND_K6_V2_DEV_BUDGET_20261005_V1`). Its separate budget `e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c` authorizes only the 128 frozen K6 V2 development identities (`attempt_001`, at most one entry each, total at most 128, zero automatic replay). The 32 sealed confirmations remain solver/response denied. The 160 setup-source authority rows remain setup-only with solver budget zero; budget permission is separate. No training fit is authorized.

The first launch is limited to `K6LDA1_DEV_D1_M05 / attempt_001` with ordered D `[215,195,210,150,140,210]`. As of the report, its fresh current-route proof, formal preflight and live FINAL_LAUNCH_REVALIDATION are pending; no K6 V2 solver entry has occurred. After its durable truth, stop and wait for Coupling ingestion/evaluator PASS before any later case. Route tests pass: 106 tests and 50 subtests. Full report and continuation: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1`.

## Power-fraction normalization audit (2026-10-05)

The Runner output-order source fraction now uses `P_scale × grating_eta`, with `P_scale` computed from directly integrated POSTNP E/H Poynting flux divided by the frozen IN_REF incident unit-cell power. The Poynting integrand is `0.5 Re(Ex·conj(Hy) − Ey·conj(Hx))` over actual monitor coordinates. The legacy `T_FDTD` quantity is a zero-order modal proxy and is not used as the total multi-order power scale.

The one-case LOAD-only physical report is `reports/gpu_runner_v1_power_fraction_normalization_v1/INDEPENDENT_PHYSICAL_POWER_AUDIT.json` (SHA256 `8302638ec31cf34f5fce370d5d6d3da47a681092c1e5303c5e5079ce21b19a11`, schema `APCD_GPU_RUNNER_V1_INDEPENDENT_PHYSICAL_POWER_AUDIT_V1`, status `MEASURED`). It covers archived `K6LDA1_DEV_D1_M05/attempt_001` only. The transmission-times-sourcepower versus independent E/H flux maximum relative difference is `1.2892487612961532e-14`; Runner P_scale agrees with a separately integrated raw-field calculation at stored precision. Coupling's frozen representation check (`rtol=1e-3`, `atol=1e-9`) matched 147/147 order rows, and eta sums passed at `atol=1e-6` for all 21 wavelengths.

Physical modal cross-checks remain distinct: surface-integrated POSTNP E/H versus the 9×9 H2 modal sum has maximum relative difference `2.8956697877272297e-4`; the maximum Runner per-order versus H2 modal relative difference is `1.499059534294761e-3`. No frozen direct-closure threshold was found, so these measurements are not labeled as physical pass/fail. Coupling must independently review them before admitting any explicit supplement. The current-backend LOAD-only report and test/dependency-preflight report are adjacent under the same report directory. Existing archived `orders.json`, FSP, H5, truth and Coupling intake were not rewritten or enabled.


## Task Scheduler queue-lifetime boundary (2026-10-07)

The installed `\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER` task is a durable **single-request Runner worker**. Its live settings are recorded in `reports/apcd_gpu_production_runner_v1/PLATFORM_RECOVERY_G023_TSK_V1/TASK_SCHEDULER_SIMULATION_EVIDENCE_V1.json` and a UTF-8-normalized copy of its exported XML is stored beside that evidence. Its empty-queue invocation returned `LastTaskResult=0`; this submitted no case. The task is configured for one worker instance at a time, no scheduler restart, and a 72-hour task limit. It runs as the existing interactive DELL token.

A synthetic Task Scheduler exercise verified that a worker task is separate from a caller/controller task, that a simulated controller exit does not itself perform a solver replay, and that a separately launched worker can persist a synthetic result. The simulation is not Lumerical evidence. Desktop logoff survival was not tested.

**Serial execution rules remain:** one active scientific case globally; the next case may be admitted only after the previous case has reached a terminal Runner state, truth validation/persistence and required Coupling reconciliation have completed, and the single slot is released. A pre-entry failure is not a solver entry, but its old immutable `run_id` remains retired and Coupling must reconcile the terminal attempt before any new dispatch. Any post-entry failure consumes the case's entry budget and is never automatically replayed; it requires zero-solver recovery or quarantine. The queue controller itself must preserve this order across disconnects.

**Queue-lifetime gap:** `serial_queue.py` in Coupling SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966` starts an SSH-side process that loops over `adapter.py run-one` under `--execute`; it does not provide a safe bounded continuation interface, and a full execution would reach all 93 remaining cases. No `\APCD_COUPLING_SERIAL_QUEUE_V1` Scheduled Task is registered. A companion P05 pre-entry recovery returned `RECOVERED_FAILED_PREENTRY` with entry=0/replay=0 and 26 offline tests passing, but Coupling reconciliation still returned `ENTERED_CASE_NEEDS_AUDIT:K6LDA1_DEV_D6_P05`. Therefore the current single-case worker does not satisfy the owner requirement that Task Scheduler own the full Coupling queue controller for its entire lifetime. Coupling must provide a versioned bounded queue-controller entrypoint that performs reconciliation and progression, and Task Scheduler must launch that controller directly. Do not invoke the current unbounded `--execute` as a one-case qualification.

The G023 attempt was formally closed as `FAILED_POSTENTRY_NO_TRUTH`; its one recorded entry remains consumed, truth is unavailable, the run is quarantined from training and handoff, and replay count is zero. The Runner closeout receipt and evidence hashes are in the task report.


## Follow-up queue-controller integration blocker (2026-10-07)

The Runner Scheduler still owns only the single-case worker. A Task Scheduler task for Coupling `serial_queue.py --execute` was not registered: the current Coupling source (SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966`) runs the full remaining queue and its startup reconciliation rejects Runner P05 `FAILED_PREENTRY` as `ENTERED_CASE_NEEDS_AUDIT`, although the Runner reports entry=0. Coupling worktree changes are outside the Runner task scope and remain untouched. The Coupling owner must add versioned pre-entry reconciliation and a bounded/restartable controller interface before Task Scheduler can safely own the queue. Four no-solver Runner synthetic lifecycle tests pass; they do not qualify the Coupling controller. Historical V3 provenance and reuse boundaries are in the platform recovery report.
