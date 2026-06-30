# R2-1 RCLED/TMM High-Q Screen

RCLED = Resonant-Cavity LED, 谐振腔发光二极管. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. FDTD = Finite-Difference Time-Domain, 时域有限差分法. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性. MQW = Multiple Quantum Wells, 多量子阱. eta20/eta30 = ±20°/±30° cone collection efficiency, ±20°/±30°锥角收集效率.

No FDTD was run. This is a lightweight STACK/TMM-style screening proxy for a 453 nm near-normal high-Q source module.

## Pass Summary

- Total candidates: 4800
- Level A: 1637
- Level B: 511

## Best 10 Candidates

| candidate | family | top | bottom | cavity_nm | termination | spectral_FWHM_nm | angular_FWHM_deg | peak_abs_deg | normal/offaxis | pass |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|
| R2_1_04530 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 250 | SiO2_25nm | 4.959948 | 8.0 | 2.0 | 3.083387 | Level A |
| R2_1_04526 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 240 | SiO2_25nm | 4.959948 | 8.0 | 2.0 | 3.087504 | Level A |
| R2_1_04534 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 260 | SiO2_25nm | 4.959948 | 8.0 | 2.0 | 3.087504 | Level A |
| R2_1_04590 | R2D_all_dielectric_highR_mediumR_scan | 12 | 2 | 250 | SiO2_25nm | 4.360571 | 7.0 | 2.0 | 2.860718 | Level A |
| R2_1_04594 | R2D_all_dielectric_highR_mediumR_scan | 12 | 2 | 260 | SiO2_25nm | 4.360571 | 7.0 | 2.0 | 2.866678 | Level A |
| R2_1_04549 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 300 | TiO2_25nm | 4.959948 | 7.0 | 1.0 | 2.93826 | Level A |
| R2_1_04556 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 320 | TiO2_50nm | 4.959948 | 7.0 | 1.0 | 2.975249 | Level A |
| R2_1_04522 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 230 | SiO2_25nm | 4.959948 | 8.0 | 2.0 | 3.09025 | Level A |
| R2_1_04586 | R2D_all_dielectric_highR_mediumR_scan | 12 | 2 | 240 | SiO2_25nm | 4.360571 | 7.0 | 2.0 | 2.866678 | Level A |
| R2_1_04539 | R2D_all_dielectric_highR_mediumR_scan | 12 | 0 | 270 | none | 4.959948 | 6.0 | 0.0 | 2.874214 | Level A |

## Interpretation

If Level A/B candidates are present, validate only the top few with 2D FDTD dipole runs next. If later FDTD contradicts this proxy, trust FDTD and return to STACK/TMM model calibration.
