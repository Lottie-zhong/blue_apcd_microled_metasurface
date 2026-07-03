# R2-4E2 Pass/Fail Verdict

Verdict: **fail**.

Rules applied:
- hard fail if any case status != ok
- hard fail if tri-point average peak_abs_angle > 10 deg
- hard fail if tri-point average normal/offaxis <= 1
- hard fail if any source revives a dominant 30-40 deg lobe

Reasons: tri_point_avg_peak_abs_angle_gt_10deg;tri_point_avg_normal_offaxis_ratio_le_1
