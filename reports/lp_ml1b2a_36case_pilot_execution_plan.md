# LP-ML1B2A 36-case pilot execution plan

Purpose: plan the frozen LP-ML1B 36-case pilot execution without running FDTD.

## Inputs
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b0_runner_planning\lp_ml1b0_pilot_queue.csv
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1a_smoke_result_sanity_audit\lp_ml1b1a_summary.json
- D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml1b1a_smoke_result_sanity_audit\lp_ml1b1a_candidate_summary.csv

## Frozen queue audit
- frozen candidate count: 36
- geometry complete: 36
- missing geometry: 0
- target_bin distribution: {'0': 2, '60': 2, '120': 3, '180': 6, '240': 8, '300': 15}
- sampling_group distribution: {'B240_exploration': 8, 'B300_exploration': 13, 'global_escape_lhs': 8, 'sixbin_balance': 7}
- H_nm distribution: {'500': 17, '600': 12, '650': 6, '700': 1}

## Runtime estimate
- LPML1A4_0028_B300_exploration_B300_H600: 340.82 s
- LPML1A4_0234_B240_exploration_B240_H600: 296.46 s
- estimated per candidate: 318.64 s
- estimated 36-candidate pilot: 11471.04 s = 3.19 h plus overhead

## Batching
- recommended batch size: 6 candidates
- batch count: 6
- reason: small enough to inspect failures between batches while avoiding one-candidate overhead.

## Resume logic
- Before each candidate/wavelength/polarization subrun, check whether a successful row already exists in the result CSV.
- Resume key: candidate_id + wavelength_nm + input_polarization.
- Skip successful rows; retry missing or failed rows only when explicitly requested.

## Failure logging
- Write a failure row with candidate_id, wavelength_nm, polarization, status, exception type, message, traceback head, fsp path, and runtime seconds.
- Continue to the next subrun unless Lumerical startup itself fails repeatedly.

## LP-ML1B2B output schema
- candidate_id, target_bin_deg, wavelength_nm, txx_re, txx_im, txy_re, txy_im, tyx_re, tyx_im, tyy_re, tyy_im, selected_Tx, leakage_xin_to_yout, leakage_yin_to_xout, y_direct_leakage, conversion_to_leakage_ratio, selected_phase_deg, nearest_bin_deg, phase_error_deg, matrix_error, spectral_pass, result_status, error_message, result_csv, fsp_path_untracked

## LP-ML1B2C sanity/ranking criteria
- Verify finite complex Jones entries and recomputed metrics as in LP-ML1B1A.
- Rank seeds by spectral median ratio, Tx floor, matrix_error ceiling, bin consistency, and phase error stability.
- Treat the pilot as seed filtering only; do not claim K=6 readiness.

## Performance caution from LP-ML1B1A
- LPML1A4_0028_B300_exploration_B300_H600: Tx_mean=0.261044, phase_err_452=29.250068, nearest_bin_mode=300, ratio_median=0.412745
- LPML1A4_0234_B240_exploration_B240_H600: Tx_mean=0.476181, phase_err_452=126.415068, nearest_bin_mode=120, ratio_median=2.127896
- B300 smoke: low Tx and ratio < 1.
- B240 smoke: nearest bin shifted toward 120 and phase-wrong.
- LP-ML1B2 is for statistical exploration and seed filtering, not immediate K=6 use.

No FDTD was run.
No Lumerical GUI was opened.
No FMM solve was executed.
No model training was run.
No K=6 was started.
