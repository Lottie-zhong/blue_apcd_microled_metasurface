# Paper A LP anisotropy-expanded search v1 — planning before benchmark

Verdict: `PAPER_A_BROADBAND_LP_ANISOTROPY_EXPANDED_SEARCH_PLANNED_WAIT_BENCHMARK`

No new solver was authorized or started. Current execution authority is FDTD=0, RCWA=0, ML=0.

## Planned DOE

A01–A04 are the initial planned batch; A05–A08 are conditional planned geometry only. The 6D variables are independent a1, b1, a2, b2, delta_theta, and D with deterministic seed 20260818. All eight planned geometries passed the zero-solver validity audit; any deterministic replacement is recorded in anisotropy_doe.csv.

## Setup-only preparation

A01_x and A01_y have validated Native-M1 pre-FSPs with 430–470 nm source/monitor, 41 native points, 435–465 nm / 31-point extraction contract, and solver_run_called=false. A02–A08 have configuration and future case manifests only.

## Admission freeze

The shared scheduler has active FDTD=0, entered FDTD=0, and READY-for-auto-admission=0 for this stage. No controller or monitor is left with a pending automatic claim. A future explicit benchmark authorization is required before any solver case can enter.

No broadband Jones spectra, MDC-weighted truth metrics, or candidate PASS/FAIL verdict is produced at planning stage.
