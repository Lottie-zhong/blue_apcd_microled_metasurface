# R2-4D3 Cavity-phase Reachability

Exact angle-dependent DeltaPhi(lambda, theta) cannot be reconstructed from the saved R2-4D2 CSV alone because phi_top(lambda, theta) and phi_bottom(lambda, theta) were not stored. I therefore used metric-space evidence plus the stored model_lam0/spectral peak as a simplified phase proxy.

| representative | candidate_id | model_lam0_nm | spectral_peak_nm | peak_abs_angle_deg | phase_proxy_cycles_at_453 |
| --- | --- | --- | --- | --- | --- |
| best_R2_4D2 | R2_4D2_OPT_13003 | 459.527 | 459.5 | 7.0 | -0.014204 |
| top_near_pass | R2_4D2_OPT_04463 | 450.306 | 450.25 | 6.0 | 0.005983 |
| failed_old_proxy | R2_4B_OPT_06361 | 452.217 | 452.25 | 7.0 | 0.001731 |
| failed_old_proxy | R2_4B_OPT_06176 | 453.708 | 453.75 | 7.0 | -0.00156 |

Evidence: the best R2-4D2 candidates still drift away from the 450-456 nm target or retain 30-40 deg resonance risk. The current variable space can place narrow responses near 6-8 deg, but not with the required spectral centering and off-axis suppression simultaneously.
