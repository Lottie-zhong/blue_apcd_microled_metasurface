# R2-1A Physical Sanity Audit

RCLED = Resonant-Cavity LED, 谐振腔发光二极管. DBR = Distributed Bragg Reflector, 分布式布拉格反射镜. FDTD = Finite-Difference Time-Domain, 时域有限差分法. TMM = Transfer Matrix Method, 传输矩阵法. STACK = multilayer stack optical solver, 多层膜堆光学求解器. FWHM = Full Width at Half Maximum, 半高全宽. Q = Quality factor, 品质因子. MQW = Multiple Quantum Wells, 多量子阱. APCD = Arbitrary Polarization Conversion Dichroism, 任意偏振转换二色性. eta20/eta30 = ±20°/±30° cone collection efficiency, ±20°/±30°锥角收集效率.

No FDTD was run. This audit reclassifies R2-1 proxy candidates before any FDTD validation.

## Cavity Validity Counts

- true_two_mirror_cavity: 2880
- weak_bottom_reflector: 960
- top_filter_only: 960

Bottom_pair_count=0 candidates are not true high-Q RCLED cavity candidates in this proxy; they are top-filter controls because the effective bottom reflector is absent except for the weak background/proxy baseline.

## Conservative Top 10

| candidate | family | validity | top | bottom | cavity_nm | termination | spectral_FWHM | angular_FWHM | normal/offaxis | extraction_risk |
|---|---|---|---:|---:|---:|---|---:|---:|---:|---|
| R2_1_00227 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 290 | none | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00223 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 280 | none | 4.023958 | 9.0 | 2.423956 | low |
| R2_1_00225 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 290 | TiO2_25nm | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00219 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 270 | none | 4.023958 | 9.0 | 2.419212 | low |
| R2_1_00221 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 280 | TiO2_25nm | 4.023958 | 9.0 | 2.423956 | low |
| R2_1_00224 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 290 | TiO2_50nm | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00195 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 210 | none | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00193 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 210 | TiO2_25nm | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00192 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 210 | TiO2_50nm | 4.023958 | 9.0 | 2.427966 | low |
| R2_1_00220 | R2A_Taguchi2026_scaled_control | true_two_mirror_cavity | 6 | 6 | 280 | TiO2_50nm | 4.023958 | 9.0 | 2.423956 | low |

## Family Behavior

- R2D_all_dielectric_highR_mediumR_scan: Level A=575, Level B=145, top_filter_only=240.
- R2B_Khaidarov_hybrid_scaled_control: Level A=165, Level B=123, top_filter_only=240.
- R2A_Taguchi2026_scaled_control: Level A=897, Level B=243, top_filter_only=240.
- R2C_C2_medium_bottomR_upgrade: Level A=0, Level B=0, top_filter_only=240.

R2A produced many Level A candidates because its proxy parameters favor normal resonance and suppress off-axis strength. R2B produced fewer Level A candidates because the hybrid-style proxy is less aggressive. R2C produced no Level A/B because adding bottom reflectivity to the C2 fallback does not overcome broad/angular constraints in this proxy. R2D produced many top candidates because all-dielectric high top reflectivity plus controlled bottom reflectivity scores well in the proxy.
