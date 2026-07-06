# LP-ML1B0 runner planning

Purpose: plan the normal-incidence periodic full-wave FDTD runner for the LP-ML1A4 explicit 36-case pilot queue.

Legacy route No-Go: A2/A3/A3B/A19/A20 recovered no high-confidence run-ready legacy geometry; A20 indexed 2735 FSP files and attempted 20 candidate-matched FSP opens, all failed.
FMM not used yet: LP-FMM0A found no importable FMM/RCWA backend among grcwa, rcwa, s4, S4, meent, reticolo.
LP-ML1A4 pilot is used because it contains explicit numeric geometry and prepared_not_run rows.

## Inputs used
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_pilot_recommendation.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_explicit_seed_manifest.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_explicit_seed_summary.json
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_fmm0a_backend_and_schema_audit\lp_fmm0a_candidate_queue.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_fmm0a_backend_and_schema_audit\lp_fmm0a_convergence_plan.csv

Pilot queue count: 36

## Counts by target bin
- 0: 2
- 60: 2
- 120: 3
- 180: 6
- 240: 8
- 300: 15

## Counts by H_nm
- H500: 17
- H600: 12
- H650: 6
- H700: 1

## Counts by sampling group
- B240_exploration: 8
- B300_exploration: 13
- global_escape_lhs: 8
- sixbin_balance: 7

Expected output schema: see outputs/lp_ml1b0_runner_planning/lp_ml1b0_expected_result_schema.csv.
Runner boundaries: LP-ML1B0 is planning only; LP-ML1B1 should run a 2-candidate template smoke test before the full 36-case pilot.
Next step: LP-ML1B1 template smoke test, not full 36-case execution.

No FDTD was run.
No FMM solver was executed.
No Lumerical GUI was opened.
No model was trained.
No K=6 was attempted.
