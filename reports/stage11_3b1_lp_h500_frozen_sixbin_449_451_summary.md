# Stage11-3B1 LP H500 Frozen Six-bin 449/451 nm Extraction Summary

## Boundary
- H500 frozen LP dimer candidates only.
- Wavelengths run: 449 and 451 nm only; existing 450 nm was not rerun.
- No K=6/metagrating, finite patch, dipole source, DBR, RCLED, or Stage10 CP files touched.

## Completion
- Did all 12 cases complete? `True` (12 success, 0 failed).
- Are 449/451 nm data now available for all six bins? `True`.

## Weakest Cases
- Worst LP selectivity over 450±1 nm new points: bin `240` at `451` nm, ratio `3.759887`.
- Worst selected-channel phase drift: bin `120` at `449` nm, phase error `135.013858` deg.

## Decision
- Frozen six-bin set remains plausible over 449/450/451 nm: `False`.
- If false, Stage11-3B2 should switch to spectral rescue before any K=6 validation.

## Per-case Results
| wavelength_nm | bin | candidate_id | status | Tx | leakage | ratio | phase | phase_error | matrix_error |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 449 | 0 | H500DIMER2C_029_B240_x_pair_noswap_G60_O-20 | ok | 1.000742 | 0.004371 | 228.941257 | 2.188354 | 2.188354 | 0.066112 |
| 451 | 0 | H500DIMER2C_029_B240_x_pair_noswap_G60_O-20 | ok | 0.982771 | 0.000313 | 3143.358004 | 346.272761 | 13.727239 | 0.018045 |
| 449 | 60 | H500DIMER2B_006_B180_x_pair_swap_G60_O-20 | ok | 0.991275 | 0.009072 | 109.266450 | 74.334458 | 14.334458 | 0.095665 |
| 451 | 60 | H500DIMER2B_006_B180_x_pair_swap_G60_O-20 | ok | 0.983085 | 0.033413 | 29.422172 | 56.990416 | 3.009584 | 0.184358 |
| 449 | 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | ok | 0.949048 | 0.077345 | 12.270319 | 344.986142 | 135.013858 | 0.285481 |
| 451 | 120 | H500DIMER2C_004_B120_x_pair_swap_G60_O-20 | ok | 0.870425 | 0.161975 | 5.373816 | 18.075289 | 101.924711 | 0.431382 |
| 449 | 180 | H500DIMER2C_026_B240_x_pair_swap_G60_O-20 | ok | 0.960432 | 0.074032 | 12.973181 | 174.374026 | 5.625974 | 0.277732 |
| 451 | 180 | H500DIMER2C_026_B240_x_pair_swap_G60_O-20 | ok | 0.782728 | 0.089577 | 8.738091 | 212.564402 | 32.564402 | 0.338617 |
| 449 | 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | ok | 0.909409 | 0.080680 | 11.271773 | 204.263007 | 35.736993 | 0.297861 |
| 451 | 240 | H500DIMER2F_026_B240_x_pair_swap_G90_O-28 | ok | 0.388795 | 0.103406 | 3.759887 | 221.701937 | 18.298063 | 0.515718 |
| 449 | 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | ok | 0.972728 | 0.013843 | 70.267809 | 312.699260 | 12.699260 | 0.119294 |
| 451 | 300 | H500DIMER2D_006_B240_x_pair_swap_G80_O-30 | ok | 1.002055 | 0.260584 | 3.845420 | 311.175703 | 11.175703 | 0.509951 |
