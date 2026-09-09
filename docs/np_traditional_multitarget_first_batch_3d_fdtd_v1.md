# NP traditional multi-target K4/K9 first-batch 3D-FDTD closure

Status: `NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY`

The four authorised attempt_001 cases were run strictly serially with one FDTD slot and 12 cores; two other global slots remained reserved. All four were independently reloaded, labelled valid, and have unchanged post-FSP fingerprints after read-only extraction.

## Cases and evidence

| case | family | diameter vector (nm) | pre-FSP SHA | post-FSP SHA | entered/completed/post | T/R/closure at 450 nm | max |1-T-R| | mean eta(+1) | eta(+1) at 450 nm |
|---|---|---|---|---|---|---:|---:|---:|---:|
| K4_SEED_A_190_155 | K4 | 190,115,140,155 | 98eeeb7c73aa445617255d79dc97151ed6de8e18b968f705af225ebc91d04048 | 762f77937becac506ada73a91922f025178aa75de75eac68706cd84eda45efd7 | True/True/True | 0.820838/0.177479/0.001683 | 0.008691 | 0.678534 | 0.734075 |
| K4_SEED_B_100_175 | K4 | 100,125,145,175 | 9bc471feeea090db91566a9c5a59ae028f49e8bfe38b7c5e7a863adf8f86c919 | 64a9ebdc46039edca33ea511104e44beb8f55ff2c8c46a78d2a6bdd2d7ffa95d | True/True/True | 0.815398/0.169959/0.014643 | 0.014643 | 0.699229 | 0.671672 |
| K9_SEED_A_195_180 | K9 | 195,105,215,125,140,165,150,170,180 | 7713380db4a4af26a7789f644781d3450c98e5e1e4989b9bff1e81604a7d33dd | 34c0506c6c0e1dbfc27e39ea29961220dd034d0d103240566235743550bddd51 | True/True/True | 0.878022/0.120513/0.001465 | 0.009192 | 0.623874 | 0.632256 |
| K9_SEED_B_205_185 | K9 | 205,110,120,130,135,145,155,175,185 | eb16737ef4d4b69936ef90aa087e3ce0783acec3eec457e52d2ac212fe0dbf82 | 1fe9ddd28d4ab2eb9a1d9da5f06c3a12ae8bdb7e53d4d7eefd28e074159807fb | True/True/True | 0.863808/0.134803/0.001389 | 0.014580 | 0.813968 | 0.833319 |

All runs used normal incidence, Forward/+z, x-polarisation, 445–455 nm at 11 points, periodic x/y and PML z. Dynamic propagating transmitted orders were extracted from the order monitor (55 rows for K4 and 121 rows for K9 across 11 wavelengths); order fractions sum to unity within numerical precision.

## Decision

Broadband mean eta(+1) champion: **K9_SEED_B_205_185** (0.813968); no additional seed was needed. K4 and K9 each have two valid first-batch cases. The complete per-wavelength metrics are in each case directory and the lightweight comparison is `first_batch_family_comparison.csv`.

## Scope and handoff

The frozen K6 traditional baseline manifest is identity-only and no K6 solver was run. y-polarisation was not run, angle sweeps/RCWA/ML were not used, and MDC was not handled. The next route is coupling handoff using the recommended K9 seed B candidate. This report is numerical evidence and does not freeze a new cyclic-closure threshold.

## Reproducibility

- Runner: `scripts/run_np_traditional_multitarget_first_batch_3d_fdtd_v1.py` (one `fdtd.run()` call, no retry path).
- Offline finalizer: `scripts/finalize_np_traditional_multitarget_first_batch_3d_fdtd_v1.py`.
- Resource audit: `first_batch_resource_usage.csv`, `global_slot_compliance_audit.json`.
- Budget audit: `first_batch_solver_budget_audit.json` (4/4 entered and completed).
- attempt_002/003: not run.
