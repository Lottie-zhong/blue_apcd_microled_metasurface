# Stage11 LP-APCD Status Summary

## Scope

Stage11 is the Blue-10K6 LP-APCD branch for H500 linearly polarized dimer projection-phase validation. The target matrix remains:

J_m ~= t_m * exp(i*phi_m) * |x><x|

The current evidence is real H500 dimer Jones/FDTD only. This is not K=6 steering and not a phase-gradient supercell validation.

## Stage11-2B Revised

- Reframed dimer evaluation around selected-channel actual common phase, angle(t_xx), and projection matrix proximity to t*exp(i*phi)*|x><x|.
- Original 2A plus 2B patch established real-dimer usable bins at 0 and 60 deg.
- Remaining 2B gaps were 120/180/240 projection leakage and 300 common phase missed.

## Stage11-2C

- Selected 23 H500 alternative static source pairs for real-dimer expansion.
- Generated 48 legal H500 dimer placement cases.
- Ran 48 H500 dimer x/y normal-incidence FDTD cases successfully.
- Merged 2A + 2B + 2C: 70 total real H500 dimer cases.
- actual_dimer_usable_loose_or_strict = 26.
- actual_dimer_usable_strict = 12.

## Current Best Actual Dimer Bins

- 0 deg: strict usable, H500DIMER2C_029_B240_x_pair_noswap_G60_O-20.
- 60 deg: strict usable, H500DIMER2B_006_B180_x_pair_swap_G60_O-20.
- 120 deg: loose usable, H500DIMER2C_004_B120_x_pair_swap_G60_O-20.
- 180 deg: strict usable, H500DIMER2C_026_B240_x_pair_swap_G60_O-20.
- 240 deg: gap remains, projection_matrix_broken_y_leakage.
- 300 deg: gap remains, common_phase_missed.

## Boundaries

- No K=6 full FDTD was run.
- No phase-gradient supercell was generated.
- No H600/H700 FDTD was run.
- Simulation outputs, .fsp files, logs, monitor dumps, and far-field dumps are not intended for git submission.
- LP steering is not claimed complete.
