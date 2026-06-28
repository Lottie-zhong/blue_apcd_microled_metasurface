# Stage10-CP-BW2 dense-lite spectral validation

- Scope: Stage10 CP 450 nm metasurface-only periodic plane-wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.
- Target: `R_in -> L_out`; leakage: `R_in -> R_out`; negative `DoCP_RminusL` means desired L-output dominance.

- Completed FDTD cases: 150/150
- Failed/missing FDTD cases: 0

## Required answers

- Top candidate by min_ratio_447_454: `BW2_J1J2_D194_T90_PSI99_H525` (60.9054237205).
- Top candidate by weighted_ratio_center453_FWHM3: `BW2_J1J2_D196_T90_PSI98_H525` (179.789319297).
- Top candidate by weighted_ratio_center452p5_FWHM3: `BW2_J1J2_D196_T90_PSI98_H525` (175.299292371).
- Best 448 guard candidate: `BW2_J1J2_D194_T88_PSI97_H525` ratio_448=230.960824959.
- PSI99 remains best simple-shift candidate: dense_strict_pass with weighted453_FWHM3=179.446654249.
- T92 remains best robust candidate: reject with min_ratio_447_454=7.60940228296.
- Hidden notch candidates: ['BW2_J1J2_D194_T92_PSI97_H525'].
- Recommended top candidates for 0.25 nm refined scan: `BW2_J1J2_D196_T90_PSI98_H525`, `BW2_J1J2_D194_T90_PSI99_H525`, `BW2_J1J2_D194_T90_PSI97_H525`.

## Ranking

| candidate_id | rank_reason | min_ratio_447_454 | weighted453_FWHM3 | ratio_448 | hidden_notch | collapse |
|---|---|---:|---:|---:|---|---|
| BW2_J1J2_D196_T90_PSI98_H525 | dense_strict_pass | 24.9800002334 | 179.789319297 | 24.9800002334 | false | false |
| BW2_J1J2_D194_T90_PSI99_H525 | dense_strict_pass | 60.9054237205 | 179.446654249 | 96.0569910059 | false | false |
| BW2_J1J2_D194_T90_PSI97_H525 | borderline | 9.10007786078 | 111.341605157 | 9.10007786078 | false | false |
| BW2_J1J2_D194_T92_PSI97_H525 | reject | 7.60940228296 | 142.90968882 | 130.952134141 | true | true |
| BW2_J1J2_D194_T88_PSI97_H525 | reject | 47.2161392798 | 76.0345719591 | 230.960824959 | false | true |
