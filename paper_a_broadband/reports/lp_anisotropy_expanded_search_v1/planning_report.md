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


## Exclusive-idle resource authority

Paper A future FDTD admission requires Chart authorization, benchmark release, and zero active FDTD in every other branch; cross-branch active FDTD must equal 0. The current stage remains solver-free and has no hidden pending admission. Canonical authority: `D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\authority\paper_a_exclusive_idle_fdtd_resource_authority_v1.json` (SHA256 `a74dd9378a8ee23d6f5c3be5369ab9f45691e74b053405ca5927603b4d2eb955`).


## A02 pre-admission geometry risk

The reported `0.03199553012498768 nm` is the aggregate validity field's minimum cell-boundary clearance: pillar_2 vertex 2 is `0.03199553012498768 nm` above the lower periodic boundary. The same-cell pillar_1/pillar_2 gap is `44.5319955301249939648606783467 nm`; the implied pillar_2 periodic seam gap is `0.063991060249977929721356693304 nm`. A02 is mathematically non-overlapping but not benchmark-safe because of periodic seam near-contact. DOE unchanged; no replacement applied; solver authority remains zero. See `D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\reports\lp_anisotropy_expanded_search_v1\a02_pre_admission_geometry_audit.json`.


## A02 pre-admission geometry risk

The reported `0.03199553012498768 nm` is the aggregate validity field's minimum cell-boundary clearance: pillar_2 vertex 2 is `0.03199553012498768 nm` above the lower periodic boundary. The same-cell pillar_1/pillar_2 gap is `44.5319955301249939648606783467 nm`; the implied pillar_2 periodic seam gap is `0.063991060249977929721356693304 nm`. A02 is mathematically non-overlapping but not benchmark-safe because of periodic seam near-contact. DOE unchanged; no replacement applied; solver authority remains zero. See `D:\project\worktrees\blue_apcd_paper_a_lp_cp_broadband_v1\paper_a_broadband\reports\lp_anisotropy_expanded_search_v1\a02_pre_admission_geometry_audit.json`.
