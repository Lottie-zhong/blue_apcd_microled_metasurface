# NP traditional multi-target final freeze: K4 / K6 / K9

Status: `NP_TRADITIONAL_MULTI_TARGET_BASELINES_FROZEN_COUPLING_HANDOFF_READY`

No new solver, RCWA, ML training, single-pillar data, or third seed was run in this freeze. Family selection is scoped within each family; the global result is descriptive only because target periods differ.

## Frozen providers

| provider | K | Lambda_x (nm) | diameter vector (nm) | eta(+1) mean | eta(+1) @450 | band min/max | T@450 | max closure residual | pre/post FSP SHA |
|---|---:|---:|---|---:|---:|---|---:|---:|---|
| NP_TRAD_K4_23DEG | 4 | 1160 | 100,125,145,175 | 0.699229 | 0.671672 | 0.671672/0.736243 | 0.815398 | 0.014643 | 9bc471feeea090db91566a9c5a59ae028f49e8bfe38b7c5e7a863adf8f86c919 / 64a9ebdc46039edca33ea511104e44beb8f55ff2c8c46a78d2a6bdd2d7ffa95d |
| NP_TRAD_K6_15DEG | 6 | 1740 | 125,135,150,175,190,210 | 0.747717 | 0.745971 | 0.697473/0.829384 | 0.813246 | 0.016578 | fdcfd72198ab00ed2cf7df52f0bfc087a90cc8c18f869b045e15a45eba8310e3 / 33bfd0bba229b782f2c45dfd26b8100527940d760ee2410e6076bfeebc5537c4 |
| NP_TRAD_K9_10DEG | 9 | 2610 | 205,110,120,130,135,145,155,175,185 | 0.813968 | 0.833319 | 0.607367/0.887866 | 0.863808 | 0.014580 | eb16737ef4d4b69936ef90aa087e3ce0783acec3eec457e52d2ac212fe0dbf82 / 1fe9ddd28d4ab2eb9a1d9da5f06c3a12ae8bdb7e53d4d7eefd28e074159807fb |

Family champions: K4 = `K4_SEED_B_100_175`; K9 = `K9_SEED_B_205_185`; K6 = `NP_K6_15DEG` from the existing frozen authority. Descriptive global standalone winner by broadband mean target-order power: `K9_SEED_B_205_185`.

The three providers are traditional modular control arms, not an integrated winner, joint optimum, or angular-response model. Coupling must use the same frozen `MDC_best^trad` for the 10°, 15°, and 23° comparisons; integrated FDTD and angular physics remain in Coupling scope.

Scope exclusions: no incident-angle or ux sweep, MDC angular weighting, dipole, spacer, integrated FDTD, final device angular FWHM, NP-ML restart, surrogate training, or new K4/K9 standalone FDTD. The K6 authority is identity-preserved and RUN3C diagnostics are not used as champion evidence.

Evidence: first-batch report `docs/np_traditional_multitarget_first_batch_3d_fdtd_v1.md`; final comparison `traditional_multitarget_final_comparison.csv`; handoff `np_traditional_multi_target_coupling_handoff_v1.json`.
