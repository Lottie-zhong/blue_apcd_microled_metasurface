# APCD LP POST-D8 Local Curvature Diagnostic Physics v1

## Execution
Frozen design A only. Planned/raw/accepted/failed/missing = `8/8/8/0/0`. Complete Jones = `4/4`; central pairs = `4/4`; wavelength = `450 nm`; solver calls = `8`. Two pre-solver compatibility stops occurred before any backend invocation and are not solver calls.

## Central pairs and odd/even
Anchor: `D8_TRV_PLAN_d6f4911593b64495`. All four mirror geometries retain the frozen IDs, paired lineage, geometry hashes and half-nm center gate. Phase, complex Jones, Txx/Tyy, leakage, sigma ratio and projection error odd/even components are in the decomposition JSON. Maximum actual normalized pair residual is `0.011180`.

## Central gradient
Normalized phase gradient: `[0.5385052621544314, -0.1507462566666147, -0.02726644788150117]`. Raw derivatives: W `0.538505` deg/nm, D `-0.301493` deg/nm, Psi `-0.095417` deg/degree. Rank/condition: `3/1.573358`. Leave-one-pair-out phase MAE: `0.217302` deg; Jones MAE: `0.003917`.

## Directional curvature and validation
Directional phase curvature indicators are reported for all four sampled directions; pair-to-pair sign consistency = `True`. Existing-probe back-check MAE = `4.511434` deg; one-sided-to-mirror external MAE = `4.579418` deg; D7/D8 secant residual reference MAE = `1.066678409540886` deg. No full Hessian is claimed.

## Outcome
`CURVATURE_DOMINANT_TRUST_REGION_SHRINK_REQUIRED`. This is a diagnostic result only. No D9, progression candidate, extra geometry, canonical merge, spectrum or tolerance run was created.

## Evidence
Execution package: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\execution_packages\b120_j2lm06_post_d8_local_curvature_diagnostic_execution_package_v1`. Physics staging: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\staging\b120_j2lm06_post_d8_local_curvature_diagnostic_v1`. Analysis outputs are under `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\analysis`. D7/D8/recalibration/canonical inputs were read-only.
