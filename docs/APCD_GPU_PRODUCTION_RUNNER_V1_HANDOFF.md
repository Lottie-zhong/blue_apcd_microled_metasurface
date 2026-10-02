# APCD GPU Production Runner V1 handoff

**Status:** `APCD_GPU_PRODUCTION_RUNNER_V1_READY`

**Frozen maintenance code HEAD:** `783bd5741eb5e6853a3be5532624f4282f9488b7`
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
