# Fixed-v3 plan freeze

Status: `MDC_HF_SURROGATE_V3_PLAN_FROZEN_READY_FOR_TARGETED_AL64_SOLVER_AUTHORIZATION`.

The V2 Test40 remains `CONSUMED_EXTERNAL_TEST` for fixed-v2 and is reclassified as `V2_TEST40_CONSUMED_DEVELOPMENT_FOR_V3`; fixed-v2 historical conclusions are unchanged. The frozen V3 development base is 136 geometries / 816 cases, with six native 301x2000 cases per geometry.

AL64 is frozen at 64 geometries / 384 future cases with topology quotas ZL1=32, Explicit=16, ZL2=16. The independent `MDC_HF_SURROGATE_V3_TEST40_V1` manifest is frozen at 40 geometries / 240 cases with zero overlap against DOE96, V2 Test40, AL64, Pilot4, and the hash-only historical formal-FDTD registry. Labels are not generated or read.

Three profile-only candidates (V3-A/B/C), the duration/inner-stop/OOF contract, exact profile-only loss weights, selection diagnostics, and RCP_LCP environment provenance are frozen before any training. No solver or neural fit was started.
