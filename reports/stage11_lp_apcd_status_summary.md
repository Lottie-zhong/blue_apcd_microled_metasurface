# Stage11 LP-APCD Status Summary

## Scope

Stage11 is the Blue-10K6 LP-APCD branch for H500 linearly polarized dimer projection-phase validation. The target matrix remains:

J_m ~= t_m * exp(i*phi_m) * |x><x|

The current evidence is real H500 dimer Jones/FDTD only. This is not K=6 steering and not a phase-gradient supercell validation.

## Stage11-2B Revised

- Reframed dimer evaluation around selected-channel actual common phase, angle(t_xx), and projection matrix proximity to t*exp(i*phi)*|x><x|.
- Original 2A plus 2B patch established real-dimer usable bins at 0 and 60 deg.

## Stage11-2C

- Selected 23 H500 alternative static source pairs for real-dimer expansion.
- Ran 48 H500 dimer x/y normal-incidence FDTD cases successfully.
- Expanded real-dimer usable bins to 0, 60, 120, and 180 deg.

## Stage11-2D

- Focused only on H500 gaps: 240 and 300 deg.
- Ran 48 H500 dimer x/y normal-incidence FDTD cases successfully.
- Merged 2A + 2B + 2C + 2D: 118 total real H500 dimer cases.
- 300 deg became strict usable.
- 240 deg remained a common-phase near miss: H500DIMER2D_018_B240_x_pair_swap_G80_O-30, ratio 8.253555, Tx 0.778501, phase error 15.788334 deg, matrix error 0.348093.

## Stage11-2E

- Focused only on H500 240 deg selected-channel common-phase fine pull.
- Generated 36 legal fine-pull dimer cases around H500DIMER2D_018_B240_x_pair_swap_G80_O-30.
- Ran 33 H500 dimer x/y normal-incidence FDTD cases successfully; 3 diag-pair backups remained uncompleted after runner abort, with no successful result rows written.
- Merged 2A + 2B + 2C + 2D + 2E: 151 total real H500 dimer cases.
- actual_dimer_usable_loose_or_strict = 65.
- actual_dimer_usable_strict = 20.
- 240 deg is now loose usable through H500DIMER2E_025_B240_x_pair_swap_G90_O-25: ratio 7.561148, Tx 0.732110, phase error 8.016489 deg, matrix error 0.363672.

## Stage11-2F

- Continued H500 real-dimer APCD projection-phase quality improvement only; K=6 and metagrating work is deferred to a separate Stage12.
- Selected 24 H500 source pairs for 120/240 refinement: 12 for 120 deg projection-selectivity rescue and 12 for 240 deg strict common-phase fine pull.
- Generated 35 legal H500 dimer patch cases: 24 for 120 deg and 11 for 240 deg.
- Ran 35 H500 dimer x/y normal-incidence FDTD cases successfully; failed = 0, skipped = 0.
- Merged 2A + 2B + 2C + 2D + 2E + 2F: 186 total real H500 dimer cases.
- actual_dimer_usable_loose_or_strict = 72.
- actual_dimer_usable_strict = 21.
- 240 deg improved from loose to strict through H500DIMER2F_026_B240_x_pair_swap_G90_O-28: ratio 7.675482, Tx 0.737551, phase error 7.365287 deg, matrix error 0.360953.
- 120 deg remains loose: the best remains H500DIMER2C_004_B120_x_pair_swap_G60_O-20, ratio 4.500506, Tx 0.505730, phase error 3.736197 deg, matrix error 0.471387.

## Current Best Actual Dimer Bins

- 0 deg: strict usable, H500DIMER2C_029_B240_x_pair_noswap_G60_O-20.
- 60 deg: strict usable, H500DIMER2B_006_B180_x_pair_swap_G60_O-20.
- 120 deg: loose usable, H500DIMER2C_004_B120_x_pair_swap_G60_O-20.
- 180 deg: strict usable, H500DIMER2C_026_B240_x_pair_swap_G60_O-20.
- 240 deg: strict usable, H500DIMER2F_026_B240_x_pair_swap_G90_O-28.
- 300 deg: strict usable, H500DIMER2D_006_B240_x_pair_swap_G80_O-30.

## Current Conclusion

H500 real-dimer projection-phase 6-bin library candidate is formed at the real-dimer selected-channel common-phase level. After Stage11-2F, five bins are strict and 120 deg remains loose due to projection-selectivity limits. This is still not K=6 steering, not a phase-gradient supercell result, and not LP steering completion.

## Boundaries

- No K=6 full FDTD was run.
- No phase-gradient supercell was generated.
- No H600/H700 FDTD was run.
- Simulation outputs, .fsp files, logs, monitor dumps, and far-field dumps are not intended for git submission.
- LP steering is not claimed complete.
