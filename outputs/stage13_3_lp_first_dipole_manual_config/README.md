# Stage13-3 First No-DBR Dipole Configuration

This package records the manual approvals for A_small, LP-derived q, and a diagnostic source z. It prepares six cases but runs nothing.

- `run_fdtd=false`
- DBR/RCLED: off
- First next-stage runs: `center_x`, then `center_y`
- Four ±q cases remain prepared for later
- source z = -200 nm is a diagnostic placeholder relative to the Stage12 pillar-base z=0 plane, not a final MQW/device-stack position
- Later LP projection requires complex vector Ex/Ey/Ez
- Unpolarized response uses `I_unpol = I_xdip + I_ydip`
