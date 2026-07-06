# LP-ML1B1 FDTD smoke test

Purpose: first controlled LP-ML1B periodic dimer FDTD smoke test for exactly two LP-ML1A4 explicit candidates.

## Candidate list
- LPML1A4_0028_B300_exploration_B300_H600
- LPML1A4_0234_B240_exploration_B240_H600

## Geometry source
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_explicit_seed_manifest.csv
- Explicit LP-ML1A4 numeric geometry was used; no unrecovered legacy FSP was used.
- Material/template convention: object-defined dielectric index 2.6, matching the existing Stage11 H500 dimer template convention.

## Simulation scope
- Periodic single dimer unit cell, normal-incidence plane wave, x and y linear inputs.
- Wavelengths: 450, 450.5, 451, 451.5, 452, 452.5, 453, 453.5, 454 nm.
- Source propagates +z from below the dimer; top transmission monitor is above the pillars.
- No K=6, no coverage, no FMM solve, no model training.

## Runtime summary
- expected result rows: 18
- result rows written: 18
- successful result rows: 18
- failed result rows: 0
- failed polarization runs: 0
- runtime LPML1A4_0028_B300_exploration_B300_H600: 340.82 sec
- runtime LPML1A4_0234_B240_exploration_B240_H600: 296.46 sec

## Output paths
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_smoke_results.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_smoke_summary.json
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_failure_log.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\lp_ml1b1_runtime_manifest.csv

## Heavy files
- temporary .fsp files created: 36
- temporary .fsp folder: D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1_fdtd_smoke_test\fdtd_tmp
- heavy files were not committed

## Recommendation
- Proceed to LP-ML1B2 36-case pilot only if the Jones values and failure log look physically sane; otherwise fix the template first.
