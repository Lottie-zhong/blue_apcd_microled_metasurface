# Stage10-CP-BW1R fresh 448 nm anomaly check

- Candidate: `B4INT_J1J2_D194_T90_PSI97_H525`
- Target: `R_in_to_L_out`; same-spin leakage: `R_in_to_R_out`.
- Fresh simulations ran in a new folder; old BW1 FSPs were not used for metrics.
- Scope: metasurface-only periodic plane wave. No DBR/RCLED/MQW/dipole/finite-patch/+/-q/tolerance geometry.

## Fresh metrics

| nm | target | same-spin leakage | ratio | L fraction | DoCP R-L | status |
|---:|---:|---:|---:|---:|---:|---|
| 447.0 | 0.742510027913 | 0.032496678205 | 22.8487977519 | 0.958069165146 | -0.916138330292 | PASS |
| 447.5 | 0.372847793907 | 0.0357187083584 | 10.4384455946 | 0.912575533823 | -0.825151067646 | BORDERLINE |
| 448.0 | 0.267805154613 | 0.0294288860722 | 9.10007786078 | 0.90099086227 | -0.80198172454 | BORDERLINE |
| 448.5 | 0.536026961188 | 0.0173618791421 | 30.8737871518 | 0.968626257205 | -0.93725251441 | PASS |
| 449.0 | 0.930748584293 | 0.00632747527474 | 147.096360536 | 0.993247639602 | -0.986495279204 | PASS |

## Old vs fresh comparison

| nm | old ratio | fresh ratio | old L frac | fresh L frac | verdict |
|---:|---:|---:|---:|---:|---|
| 447.0 | 22.8487977519 | 22.8487977519 | 0.958069165146 | 0.958069165146 | context_point |
| 448.0 | 9.10007786078 | 9.10007786078 | 0.90099086227 | 0.90099086227 | unresolved_recommend_0p25nm_check |
| 449.0 | 147.096360536 | 147.096360536 | 0.993247639602 | 0.993247639602 | context_point |

## Verdict

`unresolved_recommend_0p25nm_check`

If unresolved, the next minimal check is a 0.25 nm fresh grid around 448 nm.

## Run log

- 447.0 nm x: ok, runtime_s=43.95, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_447NM_XIN.fsp
- 447.0 nm y: ok, runtime_s=43.908, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_447NM_YIN.fsp
- 447.5 nm x: ok, runtime_s=47.911, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_447p5NM_XIN.fsp
- 447.5 nm y: ok, runtime_s=45.772, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_447p5NM_YIN.fsp
- 448.0 nm x: ok, runtime_s=41.831, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_448NM_XIN.fsp
- 448.0 nm y: ok, runtime_s=43.777, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_448NM_YIN.fsp
- 448.5 nm x: ok, runtime_s=43.817, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_448p5NM_XIN.fsp
- 448.5 nm y: ok, runtime_s=43.88, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_448p5NM_YIN.fsp
- 449.0 nm x: ok, runtime_s=43.825, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_449NM_XIN.fsp
- 449.0 nm y: ok, runtime_s=43.802, fsp=D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\_saved_fsp\BW1R_B4INT_J1J2_D194_T90_PSI97_H525_449NM_YIN.fsp

## Figures

- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\figures\bw1r_fresh_target_leakage.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\figures\bw1r_fresh_ratio.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\figures\bw1r_fresh_lfraction_docp.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_bw1r_fresh_448nm_check\figures\bw1r_old_vs_fresh_ratio.png`
