# Stage10-CP-BW2 robust narrow-band dimer screen plan

- Scope: CP-APCD metasurface-only periodic plane-wave planning/dry-run.
- No FDTD was run.
- No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry/LP/Stage11/Stage12/Stage13 included.
- Baseline candidate: `B4INT_J1J2_D194_T90_PSI97_H525`.
- Target: `R_in -> L_out`; leakage: `R_in -> R_out`. Negative DoCP_RminusL means desired L_out dominance.

## Existing helpers found

- `D:\project\blue_apcd_microled_metasurface\scripts\blue_stage10_cp_zprop_validation\stage10_cp_route_b4_integer_plane_wave_screen.py`
- `D:\project\blue_apcd_microled_metasurface\scripts\blue_stage10_cp_zprop_validation\stage10_cp_bw1_spectral_tolerance.py`
- `D:\project\blue_apcd_microled_metasurface\scripts\blue_stage10_cp_zprop_validation\stage10_cp_bw1r2_dense_448nm_notch_check.py`

B4INT local perturbation is supported at planning level by the existing B4 integer plane-wave geometry pattern. Execution should reuse the B4/BW1 model builder and run exact clearance audit before launch.

## Candidate list

| candidate_id | family | d | theta | psi | J1 | J2 | valid | note |
|---|---|---:|---:|---:|---|---|---|---|
| BW2_J1J2_D194_T90_PSI97_H525 | baseline | 194.0 | 90.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | current frozen fabrication-aware CP candidate |
| BW2_J1J2_D189_T90_PSI97_H525 | BW2-A d micro-perturbation | 189.0 | 90.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | d offset -5 nm |
| BW2_J1J2_D191p5_T90_PSI97_H525 | BW2-A d micro-perturbation | 191.5 | 90.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | d offset -2.5 nm |
| BW2_J1J2_D196p5_T90_PSI97_H525 | BW2-A d micro-perturbation | 196.5 | 90.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | d offset +2.5 nm |
| BW2_J1J2_D199_T90_PSI97_H525 | BW2-A d micro-perturbation | 199.0 | 90.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | d offset +5 nm |
| BW2_J1J2_D194_T88_PSI97_H525 | BW2-A theta micro-perturbation | 194.0 | 88.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | theta offset -2 deg |
| BW2_J1J2_D194_T89_PSI97_H525 | BW2-A theta micro-perturbation | 194.0 | 89.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | theta offset -1 deg |
| BW2_J1J2_D194_T91_PSI97_H525 | BW2-A theta micro-perturbation | 194.0 | 91.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | theta offset +1 deg |
| BW2_J1J2_D194_T92_PSI97_H525 | BW2-A theta micro-perturbation | 194.0 | 92.0 | 97.0 | 230.0x100.0 | 180.0x90.0 | True | theta offset +2 deg |
| BW2_J1J2_D194_T90_PSI95_H525 | BW2-A psi micro-perturbation | 194.0 | 90.0 | 95.0 | 230.0x100.0 | 180.0x90.0 | True | psi offset -2 deg |
| BW2_J1J2_D194_T90_PSI96_H525 | BW2-A psi micro-perturbation | 194.0 | 90.0 | 96.0 | 230.0x100.0 | 180.0x90.0 | True | psi offset -1 deg |
| BW2_J1J2_D194_T90_PSI98_H525 | BW2-A psi micro-perturbation | 194.0 | 90.0 | 98.0 | 230.0x100.0 | 180.0x90.0 | True | psi offset +1 deg |
| BW2_J1J2_D194_T90_PSI99_H525 | BW2-A psi micro-perturbation | 194.0 | 90.0 | 99.0 | 230.0x100.0 | 180.0x90.0 | True | psi offset +2 deg |
| BW2_J1J2_D194_T90_PSI97_H525_J1231x101_J2180x90 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 231x101 | 180.0x90.0 | True | J1 +1 nm |
| BW2_J1J2_D194_T90_PSI97_H525_J1229x99_J2180x90 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 229x99 | 180.0x90.0 | True | J1 -1 nm |
| BW2_J1J2_D194_T90_PSI97_H525_J1230x100_J2181x91 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 230.0x100.0 | 181x91 | True | J2 +1 nm |
| BW2_J1J2_D194_T90_PSI97_H525_J1230x100_J2179x89 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 230.0x100.0 | 179x89 | True | J2 -1 nm |
| BW2_J1J2_D194_T90_PSI97_H525_J1231x101_J2181x91 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 231x101 | 181x91 | True | both +1 nm |
| BW2_J1J2_D194_T90_PSI97_H525_J1229x99_J2179x89 | BW2-B size micro-perturbation | 194.0 | 90.0 | 97.0 | 229x99 | 179x89 | True | both -1 nm |
| BW2_J1J2_D195_T90_PSI98_H525 | BW2-C right-shifted local candidate | 195 | 90.0 | 98 | 230.0x100.0 | 180.0x90.0 | True | D195/PSI98 right-weight candidate |
| BW2_J1J2_D196_T90_PSI98_H525 | BW2-C right-shifted local candidate | 196 | 90.0 | 98 | 230.0x100.0 | 180.0x90.0 | True | D196/PSI98 right-weight candidate |

## Case count and runtime

- Candidates: 21
- Sentinel wavelengths: [448.0, 450.0, 452.0, 453.0, 454.0]
- Linear inputs: ['x', 'y']
- Total planned case count = 21 x 5 x 2 = 210
- Runtime estimate: 43.4 s/case, total about 2.53 h.

## Planned scoring logic

- Prefer strong 453, 452, 450, 454 red-side safety, plus 448 guard.
- Reject or heavily penalize CP flip, L_fraction < 0.5, 448 ratio < 8, 452/453 worse than B4INT, fake high ratio from target-power collapse, or invalid geometry.
- strict_pass: all sentinel ratios >= 20, L_fraction >= 0.95, no CP flip, target power not below 60-70% of B4INT.
- useful_pass: 450-454 ratios >= 20, 448 ratio >= 10-15, L_fraction >= 0.90, no CP flip, no target-power collapse.
