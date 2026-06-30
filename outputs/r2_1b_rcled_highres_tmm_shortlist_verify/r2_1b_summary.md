# R2-1B High-Resolution TMM/STACK Shortlist Verification

RCLED = Resonant-Cavity LED, 谐振腔发光二极管. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FDTD = Finite-Difference Time-Domain, 时域有限差分法. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. MQW = Multiple Quantum Wells, 多量子阱. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性.

No FDTD was run. Spectral and angular FWHM values were recomputed from high-resolution proxy curves: wavelength 448-458 nm step 0.05 nm, theta 0-35 deg step 0.25 deg.

| candidate | role | validity | spectral_FWHM | angular_FWHM | peak_abs | normal/offaxis | extraction_risk | pass |
|---|---|---|---:|---:|---:|---:|---|---|
| R2_1_00227 | best_true_or_weak_two_mirror | true_two_mirror_cavity | 3.35 | 9.75 | 1.25 | 2.378815 | low | Level A_highres |
| R2_1_04067 | best_all_dielectric_highR_mediumR | true_two_mirror_cavity | 4.1233 | 8.75 | 0.5 | 2.33607 | medium | Level A_highres |
| R2_1_00223 | best_Taguchi_style | true_two_mirror_cavity | 3.05 | 9.5 | 1.25 | 2.374585 | low | Level A_highres |
| R2_1_02264 | best_Khaidarov_style | true_two_mirror_cavity | 4.0761 | 7.25 | 0.5 | 2.312432 | high | Level A_highres |
| R2_1_00359 | top_filter_control | top_filter_only | 5.0301 | 10.75 | 1.5 | 2.88609 | medium | Control |
| R2_1_02653 | C2_fallback_control | true_two_mirror_cavity | 4.1725 | 29.25 | 0.5 | 1.322987 | low | Fail_highres |

Top-filter-only candidates remain controls even when metrics look good. Top=12 candidates have high extraction risk until transmitted/upward output is checked by FDTD.
