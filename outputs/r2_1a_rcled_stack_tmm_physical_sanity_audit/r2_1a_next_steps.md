# R2-1A Next Steps

Do not run a broad FDTD sweep. Validate only the shortlist:

- best_true_or_weak_two_mirror: R2_1_00227 (R2A_Taguchi2026_scaled_control, bottom=6, top=6)
- best_all_dielectric_highR_mediumR: R2_1_04067 (R2D_all_dielectric_highR_mediumR_scan, bottom=4, top=8)
- best_Taguchi_style: R2_1_00223 (R2A_Taguchi2026_scaled_control, bottom=6, top=6)
- best_Khaidarov_style: R2_1_02264 (R2B_Khaidarov_hybrid_scaled_control, bottom=4, top=12)
- top_filter_control: R2_1_00359 (R2A_Taguchi2026_scaled_control, bottom=0, top=8)
- C2_fallback_control: R2_1_02653 (R2C_C2_medium_bottomR_upgrade, bottom=8, top=6)

For R2-2, run 2D FDTD dipole validation and check transmitted/upward output, angular lobe shape, spectral response around 453 nm, and whether top_pair_count >= 10 causes extraction loss.
