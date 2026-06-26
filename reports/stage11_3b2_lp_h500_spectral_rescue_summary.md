# Stage11-3B2 LP H500 Spectral Rescue Summary

## Boundary
- H500 LP dimer rescue only over 449/450/451 nm.
- No K=6/metagrating, finite patch, dipole source, DBR, RCLED, H600/H700, or Stage10 CP modification.

## Completion
- Planned spectral cases: `30`.
- Successful cases: `30`.
- Did all planned rescue cases complete? `True`.

## Best Candidates
- Best 120 deg replacement: `H500DIMER2H_003_B120_y_pair_noswap_G22_O-30`; worst_ratio `20.160105`, worst_Tx `0.906126`, max_phase_error `22.959239`, failed_gate ``.
- Best 240 deg replacement: `H500DIMER12A_004_B240_x_pair_swap_G90_O-30`; worst_ratio `4.201513`, worst_Tx `0.433866`, max_phase_error `40.890228`, failed_gate `ratio;Tx;phase`.
- 300 deg check: `H500DIMER2D_006_B240_x_pair_swap_G80_O-30`; keep frozen/check candidate acceptable: `False`; failed_gate `ratio;matrix_error`.

## Decision
- Repaired six-bin library plausible without global phase-offset relabeling: `False`.
- Recommended next step: Stage11-3B3 can try repaired-bin tuple search plus limited global-offset relabeling.

## Candidate Ranking
| target | candidate_id | complete | worst_ratio | worst_Tx | worst_matrix_error | max_phase_error | rescue | failed_gate |
|---:|---|---|---:|---:|---:|---:|---|---|
| 120 | H500DIMER2H_003_B120_y_pair_noswap_G22_O-30 | True | 20.160105 | 0.906126 | 0.222716 | 22.959239 | true |  |
| 120 | H500DIMER2H_007_B120_y_pair_noswap_G24_O-30 | True | 13.994380 | 0.896346 | 0.267314 | 23.791488 | true |  |
| 120 | H500DIMER2H_001_B120_y_pair_noswap_G20_O-30 | True | 34.236290 | 0.920320 | 0.170905 | 25.308988 | false | phase |
| 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | True | 4.500509 | 0.505731 | 0.471386 | 135.013858 | false | ratio;phase |
| 240 | H500DIMER12A_004_B240_x_pair_swap_G90_O-30 | True | 4.201513 | 0.433866 | 0.487862 | 40.890228 | false | ratio;Tx;phase |
| 240 | H500DIMER12A_005_B240_x_pair_swap_G90_O-26 | True | 3.778578 | 0.391807 | 0.514442 | 31.324397 | false | ratio;Tx;matrix_error;phase |
| 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | True | 3.759887 | 0.388795 | 0.515718 | 35.736993 | false | ratio;Tx;matrix_error;phase |
| 240 | H500DIMER12A_001_B240_x_pair_swap_G90_O-28 | True | 3.759887 | 0.388795 | 0.515718 | 35.736993 | false | ratio;Tx;matrix_error;phase |
| 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | True | 3.845420 | 0.972728 | 0.509951 | 12.699260 | false | ratio;matrix_error |
| 300 | H500DIMER12D_001_B300_x_pair_swap_G70_O-30 | True | 3.523155 | 0.956686 | 0.532763 | 16.257979 | false | ratio;matrix_error |
