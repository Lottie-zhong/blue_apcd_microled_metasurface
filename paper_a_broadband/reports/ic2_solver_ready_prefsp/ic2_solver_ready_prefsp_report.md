# IC2 setup-only pre-FSP audit

Status: PASS_SOLVER_READY_PREFSP
Case: IC2_TOPWELL_Y
No FDTD/RCWA/ML solver was run; run() was not called and solver entry remains zero.

Canonical pre-FSP: D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\runtime\ic2_solver_ready\IC2_TOPWELL_Y_attempt_001_pre.fsp
Canonical SHA256: 66cb2dff751c1baf03f5bcbddf7cfeb368e7901146d258805ed3408a9e5183a3
Physics semantic fingerprint: 43f8469cd278ffa6d56876391447a3c3bf902be03b17b362e8d844dfe43eeb0a
Integrated instrumentation fingerprint: ff0f40c8595b71d7bd1d5d16db898338b9dbfbb1f92fbe5978f6ab1beb163b86
Geometry semantic SHA256: c961c01e1024cc8a4315a2cdea9be7ee2b05b1b2d04bdaa1a7f71ff02c411a52

## IC1-to-IC2 comparison
- Geometry, domain, materials, mesh, boundaries, z layout, and monitors match IC1 semantic authority.
- Only source azimuth changes: theta=90 deg, phi=0 deg (IC1 x) to phi=90 deg (IC2 y).
- Source position remains (0, 0, -171.5) nm; source grid remains 400-500 nm with 101 points.
- The runtime IC1 pre-FSP observed after the completed run was not used as a parent.

## Gate
- Setup-only readback: PASS.
- Native-M1 materials: PASS.
- Solver counters: run_called=false, entered=0, active_fdtd=0, RCWA=0, ML=0.
- New FDTD entry is authorized but remains unused until the separate production runner executes with explicit confirmation.
