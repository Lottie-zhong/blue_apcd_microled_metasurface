# MDC_ML_F0_PRE1_PILOT_CALIBRATION_V1_RESULT

## ENVIRONMENT

- Host: `DESKTOP-NNE313K` (SSH alias `lumerical-win`).
- Worktree: `D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1`.
- Branch: `work/mdc-ml-inverse-v1`.
- Python: `N:\anaconda_envs\RCP_LCP\python.exe`.
- Execution date: 2026-07-16/17 (Asia/Shanghai).
- Initial state: correct branch/HEAD/subject, ahead/behind `0/0`, tracked diff empty, staging empty, and nonignored untracked set empty.
- Scope: 512 deterministic nominal Level-A candidates, Native-M1 process-parallel calibration, and a later formal-pilot budget decision only.
- Explicitly not run: formal 2,000/5,000 pilot, FDTD/Lumerical, tolerance children, Level-B generation, or ML training.

### F0-PRE1-A audit/freeze scope

The 2026-07-18 PRE1-A pass is a read-only audit of the existing 512-response evidence plus a contract freeze of these same five PRE1 files. It does not regenerate candidates, rerun the 512 TMM calibration, rerun the 64-structure benchmark or 17-structure smoke set, or alter any ignored output. The validation-only entry point verifies all frozen identities, all 512 artifact hashes, the quality-mask semantics, storage accounting, and the output-tree fingerprint before and after inspection.

## FROZEN_CONTRACT_GATE

- Required and observed HEAD: `8cc545785a1c73f99f31f8dc2ba21d72fc8684b8`.
- Required and observed subject: `Freeze MDC-ML F0 smoke pipeline v1`.
- Upstream divergence at entry: ahead/behind `0/0`.
- Formal repository audit: `PASS`; anchor exists and is an ancestor; immutable payload count `6`; drift count `0`.
- Frozen F0 existing-output validation gate: `PASS` (`1 passed`). The 17-structure smoke set was not recomputed.
- Frozen files and tracked TMM/material backends were read only.

## AUTHORITATIVE_BACKEND

- Material source: `apcd_native_materials.get_complex_index`.
- Normal incidence: `mdc_tmm_complex_incident_power_v1.normal_stack_power`.
- Oblique incidence: `oblique_stack_rt` with `select_forward_kz` and `kx/k0 = sin(theta_air)`.
- TE admittance: `kz/k0`; TM admittance: `n^2/(kz/k0)`.
- Power semantics remain `R`, `T`, `power_entering`, `A_stack = power_entering - T`, and `far_field_balance_offset`; `1-R-T` is not relabeled as absorption.
- Spectral/angular FWHM, peak-set semantics, APCD-ready proxy integrals, deterministic NPZ writing, schema records, and response hashes are imported from the frozen F0 smoke implementation. No solver formula was copied or replaced.

## FILES_CREATED

Exactly five nonignored repository files were created; no existing repository file was modified:

1. `configs/mdc_ml_f0_pilot_calibration_v1.yaml`
2. `scripts/build_mdc_ml_f0_pilot_candidates_v1.py`
3. `scripts/run_mdc_ml_f0_pilot_calibration_v1.py`
4. `tests/test_mdc_ml_f0_pilot_calibration_v1.py`
5. `reports/mdc_ml_f0_pilot_calibration_v1.md`

Generated evidence is under ignored `outputs/mdc_ml_f0_pilot_calibration_v1/` and is not eligible for Git staging.

## ANCHOR_AUTHORITY

All anchors were read from tracked `outputs/mdc_p1_asymmetric_scan_static_v1/p1_asymmetric_structures.csv`; no layer sequence was reconstructed from prose.

| CSV line | Anchor | Frozen family | Canonical geometry hash | Allocation |
|---:|---|---|---|---:|
| 4 | `P1_EXPLICIT_FAB_G3_A3` | `symmetric_periodic` | `ebddda773461126fdcc8d72d0bf1b47e30b8a9ac31fc6333c75b47acd209c03c` | 32 |
| 9 | `P1_ZL1_NOMINAL_G3_A3` | `off_center_defect` | `359110db21157c31e5a8dda91f7ca71193d773468894c669338ccb7d1bbe659f` | 32 |
| 14 | `P1_ZL1_ALTERNATIVE_G3_A3` | `off_center_defect` | `b30dff7f757c1401a595ee448869f65b5e4535e28995afc3976585dcbf688ed0` | 32 |

All three preferred anchors were found; missing-anchor count is zero. Their complete authoritative geometry payloads are:

- `P1_EXPLICIT_FAB_G3_A3`: source/exit `APCD_GAN_NATIVE_M1/AIR`; materials `[APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1]`; thickness `[79,45,79,45,79,45,156,45,79,45,79,45,79]`; physical hash `1d88d2a3e349ee8b95ea86286f8553dff6209a254d9de054d64afd1e5b362e99`.
- `P1_ZL1_NOMINAL_G3_A3`: source/exit `APCD_GAN_NATIVE_M1/AIR`; materials `[APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1]`; thickness `[46,78,46,78,46,312,46,78,46,78,46,78]`; physical hash `50bfca1a476034e3ac26c0a8c30fd8e0c30b36a7998c9ea61bedb6dc5785403f`.
- `P1_ZL1_ALTERNATIVE_G3_A3`: source/exit `APCD_GAN_NATIVE_M1/AIR`; materials `[APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1,APCD_TIO2_NATIVE_M1,APCD_SIO2_NATIVE_M1]`; thickness `[44,79,44,79,44,316,44,79,44,79,44,79]`; physical hash `8a2672e4ce591031e4c092b90b4256a6477bc382f5dd3f8a9c4f8664f6a80d37`.

## CANDIDATE_GENERATION

- Seed: `20260716`.
- Raw proposals: `533`; valid accepted: `512`; legality rejects: `21`; duplicate rejects: `0`; deterministic refills: `21`.
- Acceptance rate: `96.0600%` (`512/533`).
- Unique canonical hashes: `512`; unique physical hashes: `512`; canonical collisions: `0`.
- Candidate content signature: `bcb97eef254334aa382be21ce3fd78f0704e5492275a50a8028b20b6c4bdb5f4`.
- An independent second build produced the exact same ordered records and signature.
- Source-category acceptance: global `320/336 = 95.24%`, anchor `96/96 = 100%`, challenge `64/66 = 96.97%`, rare `32/35 = 91.43%`.
- Family acceptance: symmetric `84/84 = 100%`, asymmetric `52/52 = 100%`, off-center `116/116 = 100%`, grouped/chirped `52/60 = 86.67%`, dual `52/52 = 100%`, termination-reversed `52/52 = 100%`, locally aperiodic `52/61 = 85.25%`, hybrid `52/56 = 92.86%`.

Two generator defects were exposed before any TMM calibration: a fixed cross-family collision in a challenge refill path and one over-thickness dual-defect challenge proposal. Both were corrected within the frozen grammar and bounds; no bound was relaxed.

## SOURCE_CATEGORY_COUNTS

| Source category | Count | Fraction |
|---|---:|---:|
| `FAMILY_STRATIFIED_GLOBAL` | 320 | 62.50% |
| `ANCHOR_NEIGHBORHOOD` | 96 | 18.75% |
| `FAMILY_CHALLENGE` | 64 | 12.50% |
| `RARE_CROSS_FAMILY` | 32 | 6.25% |
| **Total** | **512** | **100%** |

## TOPOLOGY_COUNTS

| Frozen topology family | Global | Anchor | Challenge | Rare | Total |
|---|---:|---:|---:|---:|---:|
| `symmetric_periodic` | 40 | 32 | 8 | 4 | 84 |
| `asymmetric_pair_count` | 40 | 0 | 8 | 4 | 52 |
| `off_center_defect` | 40 | 64 | 8 | 4 | 116 |
| `grouped_chirped` | 40 | 0 | 8 | 4 | 52 |
| `dual_defect` | 40 | 0 | 8 | 4 | 52 |
| `termination_reversed` | 40 | 0 | 8 | 4 | 52 |
| `locally_aperiodic` | 40 | 0 | 8 | 4 | 52 |
| `hybrid_periodic_aperiodic` | 40 | 0 | 8 | 4 | 52 |

## DESIGN_SPACE_COVERAGE

- Layer count `[min, p10, p25, p50, p75, p90, max]`: `[9, 9, 12, 13, 19, 23, 25]`.
- Total thickness (nm): `[500, 867, 964, 1133.5, 1360.5, 1578.6, 2017]`.
- Defect thickness (nm): `[120, 139, 172.75, 250.5, 318, 372, 500]`.
- Defect count distribution: one defect `460`; two defects `52`.
- Terminations: `H->H 364`, `H->L 64`, `L->L 84`.
- Defect-position distribution: `4:88`, `4,6:12`, `5:64`, `6:122`, `6,8:13`, `8:79`, `8,10:9`, `10:58`, `10,12:18`, `12:49`.
- Anchor-parent distribution: 32 children per authoritative anchor.

## STATIC_GATE

- Status: `PASS`.
- Grammar/bounds legality: `512/512`.
- Schema validity: `512/512`.
- Integer-nanometre geometry: `512/512`.
- Deterministic rebuild: `PASS`.
- Canonical and physical uniqueness: `PASS`.
- Source/exit media completeness: `512/512`.
- Level-B count: `0`; tolerance-child count: `0`.
- Frozen-repository audit and immutable-payload drift gate: `PASS`, drift `0`.

## PARALLEL_BENCHMARK

- Fixed subset: 64 structures, exactly 8 per topology family; source mix global `22`, challenge `22`, rare `16`, anchor `4`.
- Subset signature: `55ec72ac0e2c43836208895004ceabb6cb668706915e27836bece7ba793ad031`.
- Warm-up: 2 structures per worker configuration; timed repeats: 2 x 64 structures for workers 1/2/4/8.
- Every worker/repeat produced identical metrics, arrays, and deterministic ordering; failures and worker exceptions were zero.
- Common metrics signature: `c68a1701b639ee9f7ed2cc009ae14a08a9c7635cb6f86590aba0135c5fadc91e`.
- Common array signature: `e7885a388cff3e14bac27308b6e0728148115d6987936ca7b45d1c635be4c767`.
- Common ordering signature: `f0e37bbb1ffbe1aaa1f3b4573ff66b0c6a8023dbed9b2fbb7454d2edffd65dd7`.

| Workers | Median wall time (s) | Structures/s | Speedup | Efficiency | Failures | Metrics hash | Array hash |
|---:|---:|---:|---:|---:|---:|---|---|
| 1 | 148.7051 | 0.430382 | 1.0000 | 1.0000 | 0 | M | A |
| 2 | 80.9285 | 0.790821 | 1.8375 | 0.9187 | 0 | M | A |
| 4 | 44.3464 | 1.443182 | 3.3533 | 0.8383 | 0 | M | A |
| 8 | 26.4470 | 2.419930 | 5.6228 | 0.7028 | 0 | M | A |

`M = c68a1701b639ee9f7ed2cc009ae14a08a9c7635cb6f86590aba0135c5fadc91e`; `A = e7885a388cff3e14bac27308b6e0728148115d6987936ca7b45d1c635be4c767`.

Selected workers: **8**. Relative to 4 workers, the median wall time improved by 40.36% and throughput by 67.68%, well above the 10% stop threshold. Peak RSS was unavailable on this runtime, so no unsupported memory claim is made. Workers wrote no shared artifacts; the main process serialized outputs. Scratch data and unselected reference artifacts were removed.

## F0_CROSS_FIDELITY

- Status: `PASS` against frozen F0 baseline semantics.
- Spectral FWHM `3.300000 nm`; angular FWHM `14.996580 deg`; ratio `45.666605`.
- Peak-angle set `[0.0]`; cone5 fraction `0.4535610924`; cone10 fraction `0.7857629455`.
- Normal-band transmission proxy `0.6313084409`; `T450_unpolarized = 0.9665966453`.
- Maximum scalar deviation was `7.958e-13` (spectral FWHM); all other listed scalar deviations were zero.
- Array-content hash: `d1809afbec9fa2dc28e2f83fd90099b4ecb2f193d570319e15d8fc61094070f7`.
- NPZ SHA-256: `2d1b903ae1431462afe57290701c33e73966c42e10b07b1173d0ae33a166d33a`; all required shapes and dtypes matched.

## CALIBRATION_DATASET

- Structures: `512`; successes: `512`; solver failures: `0`; worker exceptions: `0`.
- Unique geometry hashes: `512`; schema pass: `512`; artifact pass: `512`.
- Selected workers: `8`; wall time: `174.1536 s`; observed end-to-end throughput: `2.939933 structures/s`.
- Per-structure solver runtime: mean `1.840369 s`, P50 `1.669359 s`, P95 `2.768977 s`.
- Artifact bytes: `113,769,924`.
- Dataset content signature: `6b11358568fe27f9cde322e3fb214e0c9f053a2acd5d4bb2e88f51bb8e495c29`.
- Array content signature: `58ad5306b560bfca6160620420444adc54aa2f73a339938446334e3628cebb00`.
- Top-level manifest status: `PASS`; manifest-enumerated bytes excluding the manifest itself: `137,695,175`; actual evidence-directory bytes including the manifest: `137,797,751` (131.41 MiB), below the 250 MiB PRE1 cap.

## QUALITY_AUDIT

- Status: `PASS`; NaN/Inf `0`; duplicate geometry `0`; schema failures `0`; artifact failures `0`; grid failures `0`; power naming `PASS`.
- Spectral boundary-clipped: `238`; spectral invalid FWHM: `247`.
- Angular boundary-clipped and invalid FWHM: `256` each.
- Offset global peak: `453`; secondary peak: `297`; strong secondary peak: `171`; low `T450`: `263`.
- Frozen quality-mask contract: `post_TMM_objective_eligibility_mask_v1`. It is applied only after every legal structure has completed the full TMM response grid; pre-solver performance filtering is explicitly forbidden.
- Independent audit fields: solver/schema/artifact validity; spectral/angular FWHM validity and boundary clipping; center-is-global-maximum; zero-angle peak compatibility; low `T450`; low band proxy; strong secondary peak; transmission power-balance diagnostic; per-target continuous-regression masks; nominal four-objective eligibility; and shortlist eligibility.
- Solver/schema/artifact valid: `512/512`; zero-angle-compatible peak: `59/512`; low-band proxy: `257/512`; nominal four-objective eligible: `157/512`; strict shortlist eligible: `28/512`.
- A raw frozen spectral FWHM equal to zero occurs in `9` rows. Each keeps `spectral_fwhm_raw_nm = 0`, serializes the objective as null in CSV/JSON/JSONL, has `spectral_fwhm_valid = false`, and is excluded from Pareto analysis.
- These are calibration quality flags, not solver or contract failures. They control objective eligibility, future per-target training-loss masks, and shortlist eligibility; no response is deleted or discarded.

## NUMERICAL_TRANSMISSION_DIAGNOSTIC

- Raw `T450_unpolarized` is never clipped. The observed maximum is `1.0000791296228742` for `F0_PRE1_GLOBAL_DUAL_DEFECT_011`, an excess of `7.912962287415226e-05` above unity.
- Fixed PRE1 diagnostic tolerance: `0.001`, contract source `PRE1_fixed_numerical_diagnostic_v1`.
- Above-unity rows: `1`; tolerance failures: `0`; transmission clipping applied: `false`.
- This is a numerical power-balance diagnostic under the frozen complex-incident power convention, not a change to solver semantics and not an authorization to silently clamp data.

## METRIC_DISTRIBUTION

Quantiles are `[min, p10, p25, p50, p75, p90, max]`.

| Metric | Valid | Quantiles |
|---|---:|---|
| `T450_unpolarized` | 512 | `[1.9402e-6, 2.14096e-4, 0.004902, 0.039058, 0.499488, 0.852296, 1.000079]` |
| spectral FWHM (nm) | 265 | `[0.1, 0.4, 1.1, 3.5, 7.4, 20.7, 37.8]` |
| angular FWHM (deg) | 256 | `[1.119873, 2.991762, 5.584670, 16.062701, 38.483972, 84.345696, 116.434378]` |
| cone5 integral proxy | 512 | `[3.39062e-7, 3.86990e-5, 9.00540e-4, 0.008277, 0.086288, 0.147281, 0.172340]` |
| cone5 fraction proxy | 512 | `[5.82274e-6, 8.79086e-4, 0.006888, 0.045641, 0.099503, 0.197615, 0.660525]` |
| cone10 fraction proxy | 512 | `[1.19016e-5, 0.001720, 0.014461, 0.091532, 0.198425, 0.385292, 0.847761]` |
| normal-band transmission proxy | 512 | `[1.94626e-6, 2.19380e-4, 0.005152, 0.046156, 0.499722, 0.842759, 0.986612]` |

`center_is_global_max` rate is `11.5234%`. Peak sets include `[0.0]` for 59 structures and the boundary pair `[-60.0, 60.0]` for 145; remaining symmetric pairs span +/-3 through +/-59 degrees.

## NOMINAL_PARETO

- Frozen objectives: minimize spectral FWHM, minimize angular FWHM, maximize cone5 integral proxy, and maximize normal-band transmission proxy, using only rows valid for all four objectives and neither FWHM boundary-clipped.
- Valid population: `157`; non-dominated set: `32`.
- Source composition: global `23`, anchor-neighborhood `7`, challenge `2`, rare `0`.
- Family composition: symmetric `5`, asymmetric `4`, off-center `11`, grouped/chirped `2`, dual `4`, termination-reversed `3`, locally aperiodic `1`, hybrid `2`.
- Non-dominated-front objective ranges `[min, p10, p25, p50, p75, p90, max]`:
  - spectral FWHM (nm): `[0.1, 0.41, 1.075, 3.35, 6.35, 25.73, 32.5]`;
  - angular FWHM (deg): `[1.168680, 1.502122, 6.168406, 16.844479, 28.830968, 50.402332, 64.151100]`;
  - cone5 integral: `[8.89797e-6, 1.02401e-4, 0.034500, 0.073106, 0.142624, 0.159915, 0.169534]`;
  - normal-band proxy: `[5.00700e-5, 5.79848e-4, 0.189611, 0.389538, 0.822656, 0.919715, 0.971247]`.
- Pearson correlations over the 157-row valid population: angular/spectral width `+0.8199`; angular/cone5 `+0.7698`; angular/band `+0.7721`; spectral/cone5 `+0.7197`; spectral/band `+0.7208`; cone5/band `+0.9996`.
- Trade-off observation: the two transmission proxies are nearly collinear, while narrower angular/spectral widths tend to coincide with lower proxy transmission because all raw-value correlations are positive. The 32-row front therefore spans genuine width-versus-throughput compromises; no single metric ranking is used.
- Redundancy diagnostic threshold: absolute Pearson correlation `0.995`. The cone5/band pair triggers an effective-redundancy warning (`0.9995533503`), but the frozen nominal four-dimensional objective contract is retained. Correlations must be recomputed for every formal pilot; leave-one-highly-correlated-objective-out analysis is diagnostic only and never replaces the frozen 4D result.

This is a nominal TMM Pareto set only, not a final-design, FDTD, or robustness ranking.

## INTERESTING_CALIBRATION_CANDIDATES

The ten audit exemplars below are calibration-only. `H = APCD_TIO2_NATIVE_M1` and `L = APCD_SIO2_NATIVE_M1`; H/L sequences are written in full token order, and thickness arrays are in nanometres.

| # | Source | Family | Anchor | Layers | Canonical geometry hash | Center max | Secondary count/ratio | Boundary flags | Pareto |
|---:|---|---|---|---:|---|---|---|---|---|
| 1 | global | asymmetric | none | 23 | `68e67a24bebfc527b11f22c7aa92849a2f3ed26b6ffb1ba5df433a7547dd0946` | true | `0/0` | `false/false` | non-dominated |
| 2 | global | locally aperiodic | none | 17 | `4082566b0c31b74c5595b219ebb43cea554956a214b5a71b91d96d899935bc83` | true | `0/0` | `false/false` | non-dominated |
| 3 | global | symmetric | none | 25 | `3c679524ca9b934c3a2695deefa67d0055559ace4622ad23e2e9565d630c1fed` | true | `0/0` | `false/false` | non-dominated |
| 4 | anchor | off-center | `P1_ZL1_NOMINAL_G3_A3` | 12 | `51d5938f8adf842474eb40058b6ea51c109ce9c94331391a9d8891d1ea094335` | true | `0/0` | `false/false` | non-dominated |
| 5 | global | hybrid | none | 21 | `1ad2bef937240ddb97d5db7a227dc2d424ccbe98b18346b2310db5e4ec0f883d` | true | `0/0` | `false/false` | non-dominated |
| 6 | global | off-center | none | 19 | `cddbcd7ee75799eb73c8065a1cbb6bdceae8b0415dc57e82a0ecdd481eb55ea7` | true | `0/0` | `false/false` | non-dominated |
| 7 | global | hybrid | none | 13 | `d0d124c56a06cd7cddc90570c79a09f371f85e8b9e013edffb0bc1fc51c58d67` | true | `0/0` | `false/false` | non-dominated |
| 8 | global | dual defect | none | 19 | `754cec71ed6029ca698109c0287060fe76410297f8970d41b058b87cce21bebe` | true | `4/0.476544` | `false/false` | non-dominated |
| 9 | challenge | termination-reversed | none | 13 | `6b9821fd4110290b49695c69d8c9618dbd90d6efdcbb7f93692c1d650d91228a` | false | `0/0` | `false/false` | non-dominated |
| 10 | anchor | off-center | `P1_ZL1_ALTERNATIVE_G3_A3` | 12 | `dd25a9ffd79d7d66d032887569f7774b58e5d30eb22bb7de9e978443da378224` | false | `0/0` | `false/false` | non-dominated |

Here `global/anchor/challenge` expand to `FAMILY_STRATIFIED_GLOBAL/ANCHOR_NEIGHBORHOOD/FAMILY_CHALLENGE`; boundary flags are spectral/angular.

1. `F0_PRE1_GLOBAL_ASYMMETRIC_PAIR_COUNT_038` — family `asymmetric_pair_count`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[40,42,40,42,40,42,40,42,40,42,289,42,40,42,40,42,40,42,40,42,40,42,40]`; total `1191`; defects `[10]`; hash `68e67...`; `T450=0.966889`, spectral/angle FWHM `32.5/50.8639`, peaks `[0]`, secondary ratio `0`, cone5 `0.160206` (fraction `0.127914`), cone10 fraction `0.251467`, band `0.922904`; neither boundary clipped; Pareto.
2. `F0_PRE1_GLOBAL_LOCALLY_APERIODIC_017` — family `locally_aperiodic`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[54,106,54,100,54,106,54,100,372,103,57,103,51,103,57,103,51]`; total `1628`; defects `[8]`; hash `408256...`; `T450=0.942416`, FWHM `26.0/30.0261`, peaks `[0]`, secondary ratio `0`, cone5 `0.150228` (fraction `0.307268`), cone10 fraction `0.587495`, band `0.871395`; unclipped; Pareto.
3. `F0_PRE1_GLOBAL_SYMMETRIC_PERIODIC_023` — family `symmetric_periodic`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[34,60,34,60,34,60,34,60,34,60,34,60,183,60,34,60,34,60,34,60,34,60,34,60,34]`; total `1311`; defects `[12]`; hash `3c679...`; `T450=0.933390`, FWHM `19.3/64.1511`, peaks `[0]`, secondary ratio `0`, cone5 `0.157302` (fraction `0.124277`), cone10 fraction `0.246468`, band `0.903369`; unclipped; Pareto.
4. `F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_003` — family `off_center_defect`; parent `P1_ZL1_NOMINAL_G3_A3`; materials `[H,L,H,L,H,L,H,L,H,L,H,L]`; thickness `[51,66,51,66,51,307,51,66,51,66,51,66]`; total `943`; defects `[5]`; hash `51d593...`; `T450=0.905765`, FWHM `3.5/15.2194`, peaks `[0]`, secondary ratio `0`, cone5 `0.107549` (fraction `0.446252`), cone10 fraction `0.766056`, band `0.638140`; unclipped; Pareto.
5. `F0_PRE1_GLOBAL_HYBRID_PERIODIC_APERIODIC_023` — family `hybrid_periodic_aperiodic`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[30,60,36,54,30,60,36,54,30,60,165,60,30,60,30,60,30,60,30,60,30]`; total `1065`; defects `[10]`; hash `1ad2be...`; `T450=0.891638`, FWHM `23.3/46.2479`, peaks `[0]`, secondary ratio `0`, cone5 `0.149080` (fraction `0.139716`), cone10 fraction `0.272878`, band `0.860635`; unclipped; Pareto.
6. `F0_PRE1_GLOBAL_OFF_CENTER_DEFECT_037` — family `off_center_defect`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[36,98,36,98,36,98,36,98,167,98,36,98,36,98,36,98,36,98,36]`; total `1373`; defects `[8]`; hash `cddbcd...`; `T450=0.791864`, FWHM `0.6/8.08717`, peaks `[0]`, secondary ratio `0`, cone5 `0.0326833` (fraction `0.425654`), cone10 fraction `0.823601`, band `0.190816`; unclipped; Pareto.
7. `F0_PRE1_GLOBAL_HYBRID_PERIODIC_APERIODIC_018` — family `hybrid_periodic_aperiodic`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[37,98,44,91,37,98,342,98,37,98,37,98,37]`; total `1152`; defects `[6]`; hash `d0d124...`; `T450=0.347621`, FWHM `2.1/16.8838`, peaks `[0]`, secondary ratio `0`, cone5 `0.0581666` (fraction `0.406694`), cone10 fraction `0.708120`, band `0.348155`; unclipped; Pareto.
8. `F0_PRE1_GLOBAL_DUAL_DEFECT_011` — family `dual_defect`; anchor `none`; materials `[H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H,L,H]`; thickness `[59,90,59,90,59,90,59,90,258,90,256,90,59,90,59,90,59,90,59]`; total `1796`; defects `[8,10]`; hash `754cec...`; `T450=1.000079`, FWHM `6.1/25.4518`, peaks `[0]`, four secondary peaks, secondary ratio `0.476544`, cone5 `0.136524` (fraction `0.273170`), cone10 fraction `0.517851`, band `0.794024`; unclipped; Pareto. The slight value above one is retained under the frozen complex-incident power convention and is not silently clipped.
9. `F0_PRE1_CHALLENGE_TERMINATION_REVERSED_007` — family `termination_reversed`; anchor `none`; materials `[L,H,L,H,L,H,L,H,L,H,L,H,L]`; thickness `[57,43,57,43,57,43,340,43,57,43,57,43,57]`; total `940`; defects `[6]`; hash `6b9821...`; `T450=0.976217`, FWHM `7.1/25.6648`, peaks `[-3,3]`, secondary ratio `0`, cone5 `0.148345` (fraction `0.263625`), cone10 fraction `0.502211`, band `0.855768`; unclipped; Pareto.
10. `F0_PRE1_ANCHOR_OFF_CENTER_DEFECT_032` — family `off_center_defect`; parent `P1_ZL1_ALTERNATIVE_G3_A3`; materials `[H,L,H,L,H,L,H,L,H,L,H,L]`; thickness `[49,67,49,67,49,313,49,67,49,67,49,67]`; total `942`; defects `[5]`; hash `dd25a9...`; `T450=0.950960`, FWHM `3.4/18.6814`, peaks `[-4,4]`, secondary ratio `0`, cone5 `0.116230` (fraction `0.402247`), cone10 fraction `0.744946`, band `0.671907`; unclipped; Pareto.

Complete hashes, records, arrays, and metrics remain in the ignored evidence bundle; abbreviated hashes here are labels, not identity inputs.

## RUNTIME_AND_STORAGE_BUDGET

- Selected benchmark throughput: `2.419930 structures/s`; mean single-structure solver runtime: `1.840369 s`.
- Benchmark overhead incurred by PRE1: `600.8543 s`.
- Retry allowance for formal planning: `2%`.

The formal storage basis is the complete calibration production payload: root calibration metadata plus response NPZ artifacts. It is `121,155,787 B / 512 = 236,632.396484375 B` per successful structure. PRE1-only candidate, benchmark, cross-fidelity, and control evidence is excluded from the production per-structure basis.

| Formal size | Naive linear | Benchmark-throughput | Runtime +10% | Runtime +20% | Formal storage | Storage +10% | Storage +20% |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,000 | 3,680.74 s (61.35 min) | 826.47 s (13.77 min) | 909.12 s (15.15 min) | 991.76 s (16.53 min) | 473,264,793 B (451.34 MiB) | 520,591,272 B (496.47 MiB) | 567,917,752 B (541.61 MiB) |
| 5,000 | 9,201.85 s (153.36 min) | 2,066.18 s (34.44 min) | 2,272.79 s (37.88 min) | 2,479.41 s (41.32 min) | 1,183,161,982 B (1.102 GiB) | 1,301,478,181 B (1.212 GiB) | 1,419,794,379 B (1.322 GiB) |

Exact PRE1 storage audit:

| Category | Files | Bytes |
|---|---:|---:|
| Candidate manifests/records | 5 | 2,034,906 |
| Benchmark metadata | 3 | 22,905 |
| Benchmark warm-up outputs | 0 | 0 |
| Benchmark workers 1/2/4 | 0 | 0 |
| Benchmark workers 8 retained artifacts | 64 | 14,233,833 |
| F0 cross-fidelity | 2 | 229,822 |
| PRE1 control metadata | 4 | 120,498 |
| Calibration metadata | 7 | 7,385,863 |
| Calibration NPZ artifacts | 512 | 113,769,924 |
| Complete calibration production payload | 519 | 121,155,787 |
| Whole PRE1 evidence tree | 597 | 137,797,751 |

All 64 retained workers-8 benchmark NPZ files are byte-identical duplicates of calibration artifacts and are therefore not charged to the formal production basis. The previously reported `444,413,766 B` for 2,000 and `1,111,034,414 B` for 5,000 exactly reconcile to artifact-only extrapolation; they omitted calibration metadata and are retained only as legacy evidence. Naively scaling the whole PRE1 tree would instead give `538,272,465 B` and `1,345,681,162 B`, but that improperly treats fixed PRE1 audit overhead as production data.

Recommended disk reserve: `1,774,742,974 B` (1.653 GiB), equal to `1.5x` the corrected 5,000-structure formal estimate.

## FORMAL_2000_EXPECTATION

- Observed nominal four-objective eligibility: `157/512 = 30.6640625%`.
- At the observed mix, the 2,000 pilot expectation is `613.28125` eligible structures; the simple Wilson 95% projected-count interval is `[536.53, 695.80]`. This is a sampling projection, not a guarantee.
- Expected eligible counts by observed family mix: asymmetric `50.78`, dual defect `74.22`, grouped/chirped `54.69`, hybrid `70.31`, locally aperiodic `46.88`, off-center defect `183.59`, symmetric periodic `74.22`, termination-reversed `58.59`.
- Decision: conditionally sufficient for a first shared global feasibility surrogate with family embedding or one-hot representation. It is not sufficient evidence for eight independent first-round family models because projected valid counts are small and uneven.

## FORMAL_PILOT_RECOMMENDATION

- Recommendation: run a controlled **2,000-structure** formal pilot next; do **not** jump directly to 5,000.
- Preserve source proportions: global `62.5%`, anchor-neighborhood `18.75%`, challenge `12.5%`, rare `6.25%`.
- Require at least `100` samples per topology family.
- Sampler revision required: `false` (96.06% candidate acceptance and zero identity collisions).
- Post-TMM quality masking required: `true`; the planning invalid-FWHM rate is `50%`, only `157/512 = 30.66%` passed all four objective and boundary gates, and `51.37%` had low `T450`. This is not a pre-solver filter and never suppresses a legal TMM run.
- The 2,000 gate should verify coverage, valid-objective yield, throughput, and storage before authorizing a 5,000 expansion.

## TESTS

- The PRE1-A descendant regression must include `py_compile`, the validation-only output audit, the PRE1 test module, the combined inverse-spec/grammar/F0/PRE1 suite, the formal repository audit, frozen smoke validation-only, whitespace checks, and unchanged output fingerprint. Exact final counts and timings are recorded in the freeze handoff because they are generated after this report enters the commit payload.
- PRE1 tests cover fixed seed/quotas, two-build determinism, canonical/physical uniqueness, invalid rejection, deterministic refill, mirror identity, anchor authority/shortage, Level-B/tolerance exclusion, integer nm, frozen grids, worker `1/2/4/8` synthetic hash identity, Windows spawn safety, worker-exception propagation, artifact SHA/array hash, schema validation, F0 cross-fidelity, invalid/zero-FWHM Pareto exclusion, frozen objective directions/correlations, output-size gate, frozen files, and power names.
- Formal repository audit: `PASS`; all 12 checks passed, immutable payload `6`, drift `0`, solver calls `0`.
- Frozen smoke existing-output validation-only: `1 passed in 0.31 s`; no 17-structure recomputation.
- `git diff --check`: `PASS` with no output.
- The `7,476` warnings are exclusively the frozen backend's `numpy.trapz` deprecation warning; the backend was not modified.

## GIT

- PRE1-A freezes exactly the five files listed in `FILES_CREATED` with commit subject `Freeze MDC-ML F0 PRE1 pilot calibration v1`.
- The freeze must retain `8cc545785a1c73f99f31f8dc2ba21d72fc8684b8` as its sole parent, pass descendant regression, and use a normal non-force push. The resulting commit identity and remote synchronization evidence are recorded in the task handoff rather than self-referenced inside the commit payload.
- Output ignore proof: `.gitignore:6:outputs/`; status reports only `!! outputs/mdc_ml_f0_pilot_calibration_v1/`.
- Old worktree `D:\project\worktrees\blue_apcd_mdc_defect_450` was only inspected read-only at the end. Its existing dirty state (one modified file and many untracked files) was not changed, cleaned, staged, or reset by this task.

## DECLARATION

- Completed: deterministic 512-candidate construction, static gate, fixed-subset parallel calibration, F0 cross-fidelity check, full 512 Native-M1 calibration, artifact/schema audit, nominal Pareto analysis, and formal-pilot budget decision.
- Key progress: worker count 8 is evidence-selected; all 512 solver jobs and artifacts passed; the next budget gate is 2,000 structures.
- Problems encountered: two deterministic generator edge cases and zero-width spectral peak handling were found and fixed without relaxing contracts or rerunning the completed TMM calibration.
- Next priorities: P0 run the 2,000 pilot only after review/authorization; P1 apply the declared quality prefilter and monitor valid-objective yield; P2 consider 5,000 only after the 2,000 gate passes.
- Progress judgment: **F0-PRE1 complete; all final regression, frozen-contract, artifact, and Git gates pass. Formal pilot not started.**
- Declaration checklist: 512 legal unique candidates generated `YES`; 512 Native-M1 TMM calibration completed `YES`; workers 1/2/4/8 benchmark completed `YES`; frozen file modified `NO`; formal 2,000/5,000 pilot run `NO`; FDTD/Lumerical run `NO`; ML model trained `NO`; tolerance or Level-B run/generated `NO`.
- Formal-pilot readiness: technical PRE1 conditions support a separately authorized 2,000-structure pilot with the stated quality prefilter. Remaining blockers are human review/freeze of these five files, explicit run authorization, and provision of the recommended disk/runtime allowance; there is no evidence to authorize a direct 5,000 run.
- These results are nominal Native-M1 calibration evidence. They are not FDTD verification, tolerance robustness, manufacturability certification, ML validation, or a final design claim.
