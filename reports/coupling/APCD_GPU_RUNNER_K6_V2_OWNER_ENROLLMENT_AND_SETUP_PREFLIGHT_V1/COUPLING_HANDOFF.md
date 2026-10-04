# K6 V2 owner enrollment and setup preflight

Status: **READY_FOR_SETUP_ONLY**. This is setup-only preparation, not solver authorization.

- Runner route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`; authority `APCD_GPU_RUNNER_K6_V2_OWNER_ENROLLMENT_20261004_V1`; authority SHA256 `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`; policy SHA256 `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45`.
- Frozen package/inventory SHA256: `22560277c3cd7032e48de6ef5b0023986eefe5aba3c3de07b6eff2bf51dc33f9` / `f4497dc646588bf4b83dce5e022d5aa9f2bf48646a298fa78b9fe7adc70bab08`.
- Enrollment: 160 exact geometries (128 development, 32 confirmation: 4 local affine, 27 global core, 1 global stress).
- Setup builder/readback: {'SETUP_LOAD_PASS': 160, 'SETUP_FAILED': 0, 'PENDING': 0}. Formal production adapter preflight: {'FORMAL_PREFLIGHT_PASS': 160, 'FORMAL_PREFLIGHT_FAILED': 0, 'BLOCKED_SETUP_NOT_READY': 0, 'PENDING_SETUP_PREFLIGHT': 0, 'PENDING_SYSTEMIC_FAILURE': 0}.
- Solver-authorized cases: 0; per-case entry budget: 0; solver entries, FDTD runs, replay, training: 0.
- Confirmation response data were not read. Manufacturing authority remains unresolved.
- Queue21 hold remains active and unchanged (`hold-4a6eab94af3b4a6d8510ba2fe32a5b66` ACTIVE, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, new_entry_hold=1, generation=26, control DB SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`); this setup-only route requests no GPU slot and does not call `run-one`.
- EXT02 historical entry/truth remains unchanged; its independent diagnostic identity stays solver unauthorized. Its previous setup proof is retained as historical evidence and is stale for the new route digest; current-route preflight is pending. No two-plane solver result exists.

Per-case statuses are in `CASE_SETUP_STATUS_V1.csv`; hashes are in `SHA256_INVENTORY_V1.json`.

Authority path: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\controlled_admission_authority_v1.json`. Do not modify the frozen package or its original status CSV.
