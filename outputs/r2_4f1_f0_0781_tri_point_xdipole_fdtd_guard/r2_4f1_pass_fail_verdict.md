# R2-4F1 Pass/Fail Verdict

Verdict: **fail**.

Rules applied:
- hard fail if any case status != ok
- hard fail if tri-point average peak_abs_angle > 8 deg
- hard fail if tri-point average normal/offaxis <= 1
- hard fail if any source revives a dominant 30-40, 45-55, or broad 40-60 deg lobe

Reasons: tri_point_avg_peak_abs_angle_gt_8deg;tri_point_avg_fwhm_gt_20deg;tri_point_avg_normal_offaxis_ratio_le_1;F0_0781_xm0p7_xdipole_453_40_60_lobe_dominant;F0_0781_x0p0_xdipole_453_40_60_lobe_dominant;F0_0781_xp0p7_xdipole_453_40_60_lobe_dominant
