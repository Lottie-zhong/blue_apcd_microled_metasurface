# Stage13-5 Center Order Diagnosis

Read-only post-processing of Stage13-4 center_x/center_y FSP results. No FDTD run was performed.

- Expected order centers: ux = 0, +0.1736481777617225, -0.1736481777617225; uy=0.
- Cones: 3, 5, 10 degrees.
- Complex Ex/Ey/Ez only; Ez enters total vector power but not LP projection.
- Primary classification: `class_C_no_steering`.
- Recommendation: Diagnose finite-patch phase-ramp/source coupling and coordinate mapping; do not run +/-q or add DBR/RCLED.
- Large FSP/log files remain ignored and must not be committed.
