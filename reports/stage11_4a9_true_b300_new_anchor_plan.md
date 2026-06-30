# Stage11-4A9 True B300 New-Anchor Plan

Planning only. No FDTD/Lumerical was run.

## Why A9 Exists

A8 showed the best A6 B300-labeled high-selectivity family is actually a stable B60 donor. It should be kept as B60 evidence, not forced as B300.

## Excluded B60 Donor Family

{
  "candidate_ids": [
    "H600B300PULL_001_FROM_H500DIMER12D_002_B300_x_pair_swap_G80_O-30",
    "H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
    "H600B300PULL_003_FROM_H500DIMER12D_005_B300_x_pair_swap_G80_O-20",
    "H600B300PULL_004_FROM_H500DIMER12D_006_B300_x_pair_noswap_G80_O-30",
    "H600B300PULL_005_FROM_H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "H600B300PULL_006_FROM_H500DIMER12D_007_B300_x_pair_noswap_G100_O-24"
  ],
  "source_candidate_ids": [
    "H500DIMER12D_002_B300_x_pair_swap_G80_O-30",
    "H500DIMER12D_003_B300_x_pair_swap_G90_O-30",
    "H500DIMER12D_004_B300_x_pair_swap_G80_O-40",
    "H500DIMER12D_005_B300_x_pair_swap_G80_O-20",
    "H500DIMER12D_006_B300_x_pair_noswap_G80_O-30",
    "H500DIMER12D_007_B300_x_pair_noswap_G100_O-24"
  ],
  "families": [
    "B300_x_pair_noswap_G100_O-24",
    "B300_x_pair_noswap_G80_O-30",
    "B300_x_pair_swap_G80_O-20",
    "B300_x_pair_swap_G80_O-30",
    "B300_x_pair_swap_G80_O-40",
    "B300_x_pair_swap_G90_O-30"
  ]
}

## Future Groups

- S11_4A9_G1_TRUE_B300_DIFFERENT_ANCHOR_FAMILY: 18 cases, find a true B300 phase anchor without rediscovering B60
- S11_4A9_G2_TRUE_B300_PHASE_OPPOSITE_FAMILY: 12 cases, test whether a different resonance branch can land near actual B300
- S11_4A9_G3_TRUE_B300_MINI_ESCAPE: 6 cases, cheap sanity check before broader H600 redesign or stopping LP-Hnew path

Total future cases: 36 / 36.

## Recommended Next Run Group

S11_4A9_G1_TRUE_B300_DIFFERENT_ANCHOR_FAMILY

Do not include B60 donor refinement, coverage, H650, K=6, finite patch, dipole, or DBR/RCLED.
