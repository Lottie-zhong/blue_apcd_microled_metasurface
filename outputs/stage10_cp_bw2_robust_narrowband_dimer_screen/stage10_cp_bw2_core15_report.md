# Stage10-CP-BW2 core15 first FDTD run

- Scope: metasurface-only periodic plane-wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.
- Target: R_in -> L_out. Negative DoCP_RminusL means desired L_out dominance.

- Completed FDTD cases: 150/150
- Failed/missing FDTD cases: 0

## Top 5 weighted_ratio_center453

- BW2_J1J2_D194_T90_PSI99_H525: 206.240408614 (strict_pass)
- BW2_J1J2_D196_T90_PSI98_H525: 197.910634422 (strict_pass)
- BW2_J1J2_D199_T90_PSI97_H525: 194.481367973 (useful_pass)
- BW2_J1J2_D195_T90_PSI98_H525: 176.93749164 (strict_pass)
- BW2_J1J2_D196p5_T90_PSI97_H525: 169.554831294 (useful_pass)

## Top 5 min_ratio_all_sentinel

- BW2_J1J2_D194_T92_PSI97_H525: 108.408648462 (strict_pass)
- BW2_J1J2_D194_T90_PSI99_H525: 96.0569910059 (strict_pass)
- BW2_J1J2_D194_T88_PSI97_H525: 47.2161392798 (strict_pass)
- BW2_J1J2_D196_T90_PSI98_H525: 24.9800002334 (strict_pass)
- BW2_J1J2_D195_T90_PSI98_H525: 22.3310747006 (strict_pass)

Best 448 nm guard candidate: BW2_J1J2_D194_T88_PSI97_H525 ratio=230.960824959

Candidates beating B4INT at 448 while preserving 452/453: ['BW2_J1J2_D194_T90_PSI99_H525', 'BW2_J1J2_D196_T90_PSI98_H525', 'BW2_J1J2_D199_T90_PSI97_H525', 'BW2_J1J2_D195_T90_PSI98_H525', 'BW2_J1J2_D196p5_T90_PSI97_H525', 'BW2_J1J2_D194_T92_PSI97_H525']
