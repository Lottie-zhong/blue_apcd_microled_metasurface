# RCLED/MDC workspace index

This is the RCLED/MDC worktree.

Use this path for future RCLED work:

D:\project\worktrees\blue_apcd_rcled_mdc

Do not use the mixed main repo outputs for current RCLED decisions:

D:\project\blue_apcd_microled_metasurface\outputs

## Current frozen baseline candidate

- candidate_id = R1C2_C2_cav230
- top_pair_count = 6
- bottom_pair_count = 0
- cavity_span_nm = 230
- termination = TiO2_50nm

## Backup

- candidate_id = R1C2_C2_base
- top_pair_count = 6
- bottom_pair_count = 0
- cavity_span_nm = 220
- termination = TiO2_50nm

## Key output folders

- outputs\r1c0_rcled_tmm_stack_redesign_screen
- outputs\r1c1_rcled_top3_tmm_candidates_fdtd_validation
- outputs\r1c2_rcled_c2_focused_refinement

## Rejected old route

- m8 + bottomDBR99 / R1B route
- reason: symmetric off-normal 20-30 degree lobes

## Next planned stage

R1C3_RCLED_C2_baseline_freeze_package

## R1C3 freeze status

- frozen primary baseline: R1C2_C2_cav230
- backup: R1C2_C2_base
- next stage: source-y robustness test around frozen baseline
- APCD integration: not yet run

## R1C5 Source Module Handoff

- Frozen source-module baseline: `R1C2_C2_cav230`
- top_pair_count=6, bottom_pair_count=0, cavity_span_nm=230, termination=TiO2_50nm
- Recommended source_y_offset_nm: 0
- Backup source_y_offset_nm: -20
- Full +/-40 nm source-y robustness did not pass; use center or near-center placement for APCD coupling.
- APCD integration has not yet been run.
- Handoff package: `outputs/r1c5_rcled_source_module_handoff_package`

## R2-0 Closeout and Target Package

- R1 high-Q route status: m8 + bottomDBR99 rejected as main route because dipole FDTD showed symmetric 20-30 degree off-normal lobes.
- R1 fallback: R1C2_C2_cav230, Level C fallback only.
- R2 target: 453 nm high-Q RCLED/DBR source module, spectral_FWHM <= 6 nm, angular_FWHM <= 10 deg ideal / 10-25 deg acceptable, normal/off-axis ratio > 1.
- R2 next stage: R2-1 STACK/TMM redesign before more FDTD.
- Package: outputs/r2_0_rcled_r1_closeout_and_r2_target_package

## R2-1 STACK/TMM High-Q Screen

- Output: outputs/r2_1_rcled_stack_tmm_453_highq_screen
- Method: lightweight STACK/TMM-style proxy, no FDTD.
- Candidates screened: 4800
- Level A count: 1637
- Level B count: 511
- Next: R2-2 2D FDTD dipole validation for top candidates only.

## R2-1A Physical Sanity Audit

- Output: outputs/r2_1a_rcled_stack_tmm_physical_sanity_audit
- No FDTD run.
- Cavity validity counts: true_two_mirror=2880, weak_bottom=960, top_filter_only=960.
- Main warning: bottom_pair_count=0 rows are top-filter controls, not true high-Q RCLED cavities.
- Next: R2-2 FDTD validation only for r2_1a_fdtd_shortlist.csv candidates.

## R2-1B High-Resolution Shortlist Verification

- Output: outputs/r2_1b_rcled_highres_tmm_shortlist_verify
- No FDTD run.
- High-resolution proxy grid: wavelength 448-458 nm step 0.05 nm, theta 0-35 deg step 0.25 deg.
- FDTD shortlist count: 5.
- Main recommendation: validate top balanced true-cavity candidates first, keep top-filter and C2 rows as controls.
