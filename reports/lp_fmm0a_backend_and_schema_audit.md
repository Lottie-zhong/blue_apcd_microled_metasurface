# LP-FMM0A backend and schema audit

Purpose: plan FMM/RCWA screening for periodic LP dimer Jones matrices before any solver run.

## Inputs used
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_pilot_recommendation.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_explicit_seed_manifest.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1a4_explicit_geometry_seed_generator\lp_ml1a4_explicit_seed_summary.json

## Backend import audit
- grcwa: missing No module named 'grcwa'
- rcwa: missing No module named 'rcwa'
- s4: missing No module named 's4'
- S4: missing No module named 'S4'
- meent: missing No module named 'meent'
- reticolo: missing No module named 'reticolo'

36 pilot queue count: 36
12-candidate convergence subset count: 12

## Convergence subset
- LPML1A4_0381_sixbin_balance_B0_H500: B0, H500, sixbin_balance
- LPML1A4_0406_sixbin_balance_B60_H600: B60, H600, sixbin_balance
- LPML1A4_0511_global_escape_lhs_B120_H500: B120, H500, global_escape_lhs
- LPML1A4_0524_global_escape_lhs_B180_H600: B180, H600, global_escape_lhs
- LPML1A4_0234_B240_exploration_B240_H600: B240, H600, B240_exploration
- LPML1A4_0028_B300_exploration_B300_H600: B300, H600, B300_exploration
- LPML1A4_0049_B300_exploration_B300_H500: B300, H500, B300_exploration
- LPML1A4_0093_B300_exploration_B300_H500: B300, H500, B300_exploration
- LPML1A4_0157_B300_exploration_B300_H500: B300, H500, B300_exploration
- LPML1A4_0239_B240_exploration_B240_H600: B240, H600, B240_exploration
- LPML1A4_0245_B240_exploration_B240_H600: B240, H600, B240_exploration
- LPML1A4_0178_B300_exploration_B300_H650: B300, H650, B300_exploration

## Expected result schema
candidate_id, backend_name, fourier_order_x, fourier_order_y, lambda_nm, polarization_in, txx_re, txx_im, txy_re, txy_im, tyx_re, tyx_im, tyy_re, tyy_im, Tx, leakage, conversion_to_leakage_ratio, selected_phase_deg, nearest_bin_deg, phase_error_deg, matrix_error, energy_balance_error, result_status, error_message, runtime_seconds

No FMM solver was executed.
No FDTD was run.
No Lumerical GUI was opened.
No model was trained.
No K=6 was attempted.
