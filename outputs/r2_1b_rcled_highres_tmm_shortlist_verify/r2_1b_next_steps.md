# R2-1B Next Steps

Recommended maximum shortlist for 2D FDTD validation:

- primary_validation: R2_1_00227 (best_true_or_weak_two_mirror, Level A_highres)
- primary_validation: R2_1_00223 (best_Taguchi_style, Level A_highres)
- primary_validation: R2_1_04067 (best_all_dielectric_highR_mediumR, Level A_highres)
- control: R2_1_00359 (top_filter_control, Control)
- control: R2_1_02653 (C2_fallback_control, Fail_highres)

Run only these before any broader sweep. Validate upward power, angular lobe shape, spectral response around 453 nm, and extraction loss for high-top-reflector candidates.
