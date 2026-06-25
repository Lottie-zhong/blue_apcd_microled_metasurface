# Stage10-CP-BW1R2 dense 448 nm notch-width check

- Candidate: `B4INT_J1J2_D194_T90_PSI97_H525`
- Scope: Stage10 CP-APCD metasurface-only periodic plane-wave spectral stability. No DBR/RCLED/MQW/dipole/finite patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13.
- Target: `R_in -> L_out`; negative DoCP_RminusL is desired L_out dominance, not failure.

## Fresh BW1R2 points

| nm | target | leakage | ratio | L fraction | DoCP | status |
|---:|---:|---:|---:|---:|---:|---|
| 447.25 | 0.544799159655 | 0.0352813334376 | 15.4415694242 | 0.939178555635 | -0.878357111271 | BORDERLINE |
| 447.75 | 0.271333202 | 0.0336635543174 | 8.06014716812 | 0.889626516938 | -0.779253033876 | BORDERLINE |
| 448.25 | 0.364124386428 | 0.0236983824431 | 15.3649468398 | 0.938893782559 | -0.877787565118 | BORDERLINE |
| 448.75 | 0.740859324425 | 0.0113230240238 | 65.429457967 | 0.98494643746 | -0.96989287492 | PASS |

## Dense merged 447-449 nm table

| nm | source | ratio | L fraction | DoCP | status |
|---:|---|---:|---:|---:|---|
| 447.0 | BW1R_context_reused_csv | 22.8487977519 | 0.958069165146 | -0.916138330292 | PASS |
| 447.25 | BW1R2_fresh_fdtd | 15.4415694242 | 0.939178555635 | -0.878357111271 | BORDERLINE |
| 447.5 | BW1R_context_reused_csv | 10.4384455946 | 0.912575533823 | -0.825151067646 | BORDERLINE |
| 447.75 | BW1R2_fresh_fdtd | 8.06014716812 | 0.889626516938 | -0.779253033876 | BORDERLINE |
| 448.0 | BW1R_context_reused_csv | 9.10007786078 | 0.90099086227 | -0.80198172454 | BORDERLINE |
| 448.25 | BW1R2_fresh_fdtd | 15.3649468398 | 0.938893782559 | -0.877787565118 | BORDERLINE |
| 448.5 | BW1R_context_reused_csv | 30.8737871518 | 0.968626257205 | -0.93725251441 | PASS |
| 448.75 | BW1R2_fresh_fdtd | 65.429457967 | 0.98494643746 | -0.96989287492 | PASS |
| 449.0 | BW1R_context_reused_csv | 147.096360536 | 0.993247639602 | -0.986495279204 | PASS |

## Answers

- Notch center/width: broader across 447.5-448.25 nm.
- Borderline region where ratio < 20: [447.25, 447.5, 447.75, 448.0, 448.25]; sampled width at least 1.0 nm.
- All dense points still L_out dominant under R_in: True.
- CP flip wavelengths: [].
- Weakness driver: leakage increase dominates.
- Recommendation: multi-wavelength B4INT re-screen should be considered; RCLED spectral avoidance alone may need tight centering away from 447.5-448.25 nm.

## Warnings

- Some wavelengths are BORDERLINE under the existing B4 ratio threshold of 20.

## Figures

- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r2_dense_448nm_notch_check\figures\bw1r2_dense_ratio.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r2_dense_448nm_notch_check\figures\bw1r2_dense_target_leakage.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r2_dense_448nm_notch_check\figures\bw1r2_dense_lfraction_docp.png`
