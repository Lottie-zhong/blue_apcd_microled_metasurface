# NP Traditional Multi-Target Baseline Extension V1

Status: `READY_FOR_NP_TRADITIONAL_K4_K9_FIRST_BATCH_3D_FDTD_AUTHORIZATION`.

## Evidence boundary

The input is the measured/recovered 27-point x-only single-pillar library (`D100..D230`, 5 nm spacing; 297 rows; `445..455 nm`; no interpolation). The library is used for relative phase initialization only; K4/K9 final performance remains full-supercell 3D-FDTD authority. D180 is the recovered valid historical point; no new single-pillar library was built.

The frozen K6 traditional baseline is reused from `outputs/np_k6_p1d4_k6x_candidate_freeze_v1/selected_k6x_candidates.json` and `candidate_freeze_manifest.json`; it is not redesigned and has zero new solver runs. Phase increases along physical +x, target order is `m=+1`, and `gratingn=1`/`u_x>0` is the sign bridge.

## Offline phase initialization

K4 uses `Lambda_x=1160 nm`, ideal 90° bins, centered positions `[-435,-145,145,435] nm`:

- `K4_SEED_A_190_155`: D=`[190,115,140,155]`, phi0=`3°`, 450-nm RMS/max=`1.042/1.742°`, broadband RMS=`19.399°`, min gap/seam=`117.5/117.5 nm`.
- `K4_SEED_B_100_175`: D=`[100,125,145,175]`, phi0=`47°`, 450-nm RMS/max=`1.695/2.303°`, broadband RMS=`5.986°`, min gap/seam=`130.0/152.5 nm`.
- `K4_SEED_C_110_185`: D=`[110,130,150,185]`, phi0=`74°`, 450-nm RMS/max=`3.369/4.683°`, broadband RMS=`6.426°`, min gap/seam=`122.5/142.5 nm`.

K9 uses `Lambda_x=2610 nm`, ideal 40° bins, centered positions `[-1160,-870,-580,-290,0,290,580,870,1160] nm`:

- `K9_SEED_A_195_180`: D=`[195,105,215,125,140,165,150,170,180]`, phi0=`18°`, 450-nm RMS/max=`3.972/8.218°`, broadband RMS=`35.096°`, min gap/seam=`102.5/102.5 nm`.
- `K9_SEED_B_205_185`: D=`[205,110,120,130,135,145,155,175,185]`, phi0=`35°`, 450-nm RMS/max=`5.207/8.856°`, broadband RMS=`12.256°`, min gap/seam=`95.0/95.0 nm`.
- `K9_SEED_C_205_190`: D=`[205,110,120,130,135,145,155,175,190]`, phi0=`36°`, 450-nm RMS/max=`5.367/9.856°`, broadband RMS=`12.422°`, min gap/seam=`92.5/92.5 nm`.

K9 classification is `K9_PHASE_LIBRARY_COVERAGE_USABLE_WITH_FULL_SUPERCELL_FDTD`; this is not a final physical pass.

## Setup-only FDTD package

The generic setup-only builder is `scripts/build_np_traditional_multitarget_prefsp_v1.py`. It saves, closes, independently reloads, reads geometry/material/source/monitor/boundary properties, and records checksums for six pre-FSPs under `runtime_fsp/np_traditional_multitarget_baseline_extension_v1/`. `solver_entered=0`, `fdtd_run_called=false`, `mpi_calls=0`; no FDTD solve, RCWA, ML training, y-pol, angle sweep, or MDC coupling occurred.

## Next authorization

Authorize at most four `attempt_001` full-supercell 3D-FDTD runs: K4 phase+broadband seeds and K9 phase+broadband seeds (one run if the two seeds coincide). Resource contract: one solver slot with 12 cores; the other two slots remain reserved for the concurrent branches. No automatic rerun. Coupling receives only the frozen modules `NP_TRAD_K9_10DEG`, `NP_TRAD_K6_15DEG`, and `NP_TRAD_K4_23DEG` after physical verification.
