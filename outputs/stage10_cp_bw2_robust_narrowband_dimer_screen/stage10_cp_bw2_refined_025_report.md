# Stage10-CP-BW2 refined 0.25 nm spectral validation

- Scope: Stage10 CP 450 nm metasurface-only periodic plane-wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.
- Target: `R_in -> L_out`; leakage: `R_in -> R_out`; negative `DoCP_RminusL` means desired L-output dominance.

- Completed/reused FDTD cases: 174/174
- Reused dense-lite cases: 90
- Newly run or locally reused refined cases: 0
- Failed/missing cases: 0
- Extracted wavelength rows: 87/87

## Required answers

- Top candidate by min_ratio_447_454: `BW2_J1J2_D194_T90_PSI99_H525` (60.6765595279).
- Top candidate by weighted_ratio_center453_FWHM3: `BW2_J1J2_D194_T90_PSI99_H525` (177.107393531).
- Top candidate by weighted_ratio_center452p5_FWHM3: `BW2_J1J2_D194_T90_PSI99_H525` (173.664254146).
- PSI99 remains best all-band/simple-shift candidate: refined_strict_pass min_ratio=60.6765595279.
- D196_PSI98 remains best red/RCLED-weighted candidate: refined_strict_pass weighted453_FWHM3=176.766553232.
- Baseline notch reproduction: ratio_447p75=8.06014716812, ratio_448=9.10007786078.
- Hidden notch in PSI99/D196_PSI98: none.
- Recommended candidate(s) for RCLED spectral convolution: `BW2_J1J2_D194_T90_PSI99_H525`, `BW2_J1J2_D196_T90_PSI98_H525`.

## Ranking

| candidate_id | class | min_ratio_447_454 | weighted453_FWHM3 | weighted452p5_FWHM3 | hidden_notch | collapse |
|---|---|---:|---:|---:|---|---|
| BW2_J1J2_D194_T90_PSI99_H525 | refined_strict_pass | 60.6765595279 | 177.107393531 | 173.664254146 | false | false |
| BW2_J1J2_D196_T90_PSI98_H525 | refined_strict_pass | 23.6417153219 | 176.766553232 | 173.58437795 | false | false |
| BW2_J1J2_D194_T90_PSI97_H525 | reject | 8.06014716812 | 109.001911914 | 113.921110989 | true | false |
