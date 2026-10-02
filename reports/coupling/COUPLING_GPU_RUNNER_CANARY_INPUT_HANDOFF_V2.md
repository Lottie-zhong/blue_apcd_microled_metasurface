# COUPLING_GPU_RUNNER_CANARY_INPUT_HANDOFF_V2

Status: READY_FOR_HANDOFF. S35 and S39 have canonical pre-FSPs and passing fresh LOAD-only validation. This handoff supplies inputs; it does not dispatch or run a GPU canary.

| Case | Canonical pre-FSP | SHA256 | Geometry hash | LOAD validation SHA256 |
|---|---|---|---|---|
| K6V1_S35 | D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\K6V1_S35\attempt_001\setup\runtime.fsp | fc7b3f5dab639b7b8816f42438a6eba7c2090266570253e4da043e0bda25b892 | bd6fb9a41c003910eeda456315bafb1962dd4335d1ec64ec055322e2f4a19276 | 435580f595204c82574e7ff83176f8e09f405ed2816b42e9295cf912e1b029ca |
| K6V1_S39 | D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1\K6V1_S39\attempt_001\setup\runtime.fsp | 23c7d66cf8a73dc838b772c1cae048464451b0cb1584f3305d10938a2ebafe0d | 7c582e2c53da5394d6cdf446a1ee9e16a970264b1fc78312d3f304df52403729 | 5ad9843088ecc3ded9b8ff01d81efe12efd6d78c6ef0bd9837e7330fd2b364b1 |

Physical contract hash: 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5
Mesh implementation authority: PW_K6_5NM_FULL_PERIOD_MESH_AUTHORITY_V1
Builder commit: 7a0edbc3d9a9d28e732f35be166efb1fb50cd9b2
Builder SHA256: fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1
Stage-1 manifest SHA256: 4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f
The remaining ten approved Stage-1 cases also have regenerated, passing pre-FSPs. Solver and GPU entry counts are zero.
NEXT = HANDOFF_COUPLING_GPU_RUNNER_CANARY_INPUT_V2_TO_APCD_GPU_PRODUCTION_RUNNER_V1. This NEXT was not executed.
