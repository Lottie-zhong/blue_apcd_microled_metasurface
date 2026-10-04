# K6 V2 first development truth handoff

Status: PILOT_DONE_PENDING_COUPLING_INGESTION_PASS. This handoff covers one development case only.

## Identity and execution

- Case: K6LDA1_DEV_D1_M05; attempt: attempt_001; role: DEVELOPMENT_LOCAL_AXIS.
- Ordered geometry D1..D6 (nm): [215, 195, 210, 150, 140, 210]; geometry SHA-256: 260821eaa933c1b36e67132656e633bde30f2f4cbf994b0b774eed04cca1b6e5.
- Run ID: K6V2_D1M05_20261004T175055Z_449c4f94; entry UTC: 2026-10-04T17:52:33.959392Z; DONE UTC: 2026-10-04T18:04:03.192260Z.
- Solver entries: 1; FDTD runs: 1; replay: 0. Budget remains 127 of 128.
- Route: APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1; authority SHA-256: a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35; policy SHA-256: b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45; adapter SHA-256: a9cfb11db584bf2ab96049b9066e198415bfba0863f29d0ed278230ffddc8579.
- Budget SHA-256: e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c; global entry-control generation recorded by Runner: 27.

## GPU execution and truth

The saved LSF calls run FDTD with the GPU resource. The solver log records fdtd-engine-msmpi.exe -gpu, detects NVIDIA GeForce RTX 3080 (GPU UUID 15ded1d4-3837-27b9-d22a-fa67c55420f4), and completes. No license credential is copied into this handoff. A live process snapshot associated Runner child PID 15596, MPI PID 41380, and GPU engine PID 27856 with the same run; the engine exit code was not separately captured, while the Runner child returned 0.

Runner terminal state is DONE. Fresh LOAD, monitors, state, and scientific validation all passed; max energy closure is 1.1102230246251565e-16. The raw orders artifact contains 21 wavelengths from 440 to 460 nm and seven orders per wavelength. The saved solver H5 contains four monitor groups, six E/H components each; raw extracted fields preserve IN/PRENP/POSTNP with actual plane sample coordinates. The canonical complex Floquet metadata has 3 planes x 21 wavelengths x 81 orders x 2 directions x 2 polarizations; Coupling's frozen importer will independently validate its seven-order subset and normalization.

The machine-readable record is D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1\FIRST_CASE_TRUTH_RECORD_V1.json and has SHA-256 db7b56ebcedcee2f2244c72fb06400244b57942c8e29f01e69ac0f86a50b91fc. It supplies exactly the record/artifact descriptors consumed by the existing load_verified_runner_case API. Its source manifest SHA-256 is b80a2cee0e546826ad8271c1be5287274c52d457ce65ccff6ed817dd6e7ae047; physical contract SHA-256 is 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5. Full truth artifact digests are in FIRST_CASE_SHA256_INVENTORY_V1.json.

## Gate and boundaries

Coupling ML has not yet acknowledged or accepted this record. The other 127 development cases remain unentered until its explicit first-case ingestion PASS. The 32 sealed confirmation identities remain at zero entries and zero response access; training fits remain zero. This is a solver/truth delivery status, not a learning/H1/model or manufacturing qualification.

Runtime root: D:\apcd_runtime\gpu_production_runner_v1\runs\K6LDA1_DEV_D1_M05\attempt_001\K6V2_D1M05_20261004T175055Z_449c4f94. Runner report root: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1.
