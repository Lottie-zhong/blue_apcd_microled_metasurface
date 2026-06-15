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

- Focused only on final H500 gaps: 240 and 300 deg.
- Selected 24 source pairs and generated 48 legal H500 final-gap dimer cases.
- Ran 48 H500 dimer x/y normal-incidence FDTD cases successfully.
- Merged 2A + 2B + 2C + 2D: 118 total real H500 dimer cases.
- actual_dimer_usable_loose_or_strict = 43.
- actual_dimer_usable_strict = 20.

## Current Best Actual Dimer Bins

- 0 deg: strict usable, H500DIMER2C_029_B240_x_pair_noswap_G60_O-20.
- 60 deg: strict usable, H500DIMER2B_006_B180_x_pair_swap_G60_O-20.
- 120 deg: loose usable, H500DIMER2C_004_B120_x_pair_swap_G60_O-20.
- 180 deg: strict usable, H500DIMER2C_026_B240_x_pair_swap_G60_O-20.
- 240 deg: gap remains, common_phase_missed; best H500DIMER2D_018_B240_x_pair_swap_G80_O-30, phase error 15.788334 deg.
- 300 deg: strict usable, H500DIMER2D_006_B240_x_pair_swap_G80_O-30.

## Boundaries

- No K=6 full FDTD was run.
- No phase-gradient supercell was generated.
- No H600/H700 FDTD was run.
- Simulation outputs, .fsp files, logs, monitor dumps, and far-field dumps are not intended for git submission.
- LP steering is not claimed complete.
