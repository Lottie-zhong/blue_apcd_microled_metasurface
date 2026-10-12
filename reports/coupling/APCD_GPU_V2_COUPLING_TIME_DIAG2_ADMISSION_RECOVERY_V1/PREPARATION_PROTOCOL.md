# DIAG2 setup preparation protocol (frozen before LOAD)

Scope: create two Coupling-side 6 ps setup candidates and fresh native LOAD-only proofs. This package does not call the Runner, controller, Scheduler, or any solver entry API. The two candidate identities and role remain unregistered until GPU Owner installs a matching isolated consumer/release.

Cases: A1 `K6V3_TIME_DIAG2_A1_5NM_6PS`, parent repeat anchor `K6GDP2_DEV_G001`, D1…D6 `[120,160,165,175,160,195]` nm; A2 `K6V3_TIME_DIAG2_A2_5NM_6PS`, parent repeat anchor `K6GDP2_DEV_G004`, D1…D6 `[210,115,175,115,180,125]` nm. Each proposes only `attempt_001`, one entry maximum, no replay, no training, no confirmation role. IDs are candidate IDs, not formal Runner enrollment.

Input is the verified 3 ps source setup FSP for the corresponding frozen `K6V3_NUM_REPEAT_A1/A2` row. The operation is load source → read back 3 ps/1e-6 → set only FDTD `simulation time` to 6e-12 s → save to a new task-isolated path → close → open that exact saved file in a separate fresh native Lumerical session → record complete setup readback. No solver run, meshing solve, result extraction, or truth generation occurs. Existing source FSPs are never overwritten. Existing source LOAD proofs and SHA are checked before use.

Acceptance is exact: semantic readback of the candidate matches the source in all recorded geometry, stack, material sample, boundary/PML, mesh override, source, monitor, wavelength, reference-plane and normalization fields; the sole expected mismatch against the frozen 3 ps validator is `FDTD simulation_time_s`; candidate readback is 6e-12 s and auto-shutoff remains 1e-6. Core mesh override must read 5 nm. This does not establish the solver-generated mesh lattice or numerical convergence.

The 6 ps contract is a Coupling candidate contract with a canonical SHA, explicitly not a formal GPU Runner contract. The installed GPU consumer/release discrepancy remains a hard launch blocker. The original V3 numerical advancement state remains HOLD.
