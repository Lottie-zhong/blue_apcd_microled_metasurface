# COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1

**Status:** setup prepared; waiting for Chat scientific review. No HF launch is authorized by this task.

## Authority and execution boundary

- Starting worktree HEAD: `42748512daedfb580f77199c32cc8ff31ab508d1` (formal successor of requested `03f4a5b737a99bb0ec5b6a0d38b64a5d51ad1a3f`; no reset).
- Worktree/branch: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, `work/mdc-np-coupling-ml-v1`.
- Fixed physical contract SHA256: `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`. Geometry-domain authority SHA256: `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f`. 32G dataset authority SHA256: `0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e`. Original H1 numeric-gate authority SHA256: `8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd`.
- ZERO solver: 0 FDTD/GPU Runner/new HF/reserve entries. ZERO training and ZERO P_scale fitting. The builder saved setup FSPs and the paired validator freshly loaded/read them; neither invoked a solver.
- Runner remains frozen/serial and approves only its existing 12 Stage-1 IDs. The 16 new IDs have no per-case Runner authority, no authority-input manifests, and no Runner-canonical FSP paths.

## 32G coverage and interpretation

The 32G source is 32 independent geometry groups and 672 geometry-wavelength rows (21 wavelengths, 440–460 nm). Ordered D1…D6 each span 100–230 nm on a 5 nm grid. This broad coordinate range does not imply dense local coverage: normalized geometry distance is Euclidean distance after scaling each coordinate difference by 130 nm; nearest-neighbor distance has min/median/max `0.789/0.823/0.937`, and no pair is closer than 0.75. At radius 1.0 the neighbor count has median 4, mean 4.125, and range 1–14.

Across 496 non-independent geometry pairs, geometry distance has descriptive Pearson/Spearman correlations of −0.253/−0.245 with symmetric relative C_hat L2 change, −0.0875/−0.102 with routing RMS change, and −0.129/−0.120 with mean absolute log P_scale ratio. The 0.5–1.0 distance bin (66 pairs) has median changes 1.247, 0.1499, and 0.2403; the 1.0–1.5 bin (282 pairs) 1.145, 0.1470, and 0.2184; the >=1.5 bin (148 pairs) 1.082, 0.1399, and 0.2098. All pairs generally change multiple diameters; these figures are descriptive, not single-coordinate derivatives or causal evidence. Existing 32G therefore does not resolve ±5 nm local response smoothness; it also does not establish that the full domain is unlearnable.

Coverage state hashes pass for all 32 geometries. Readback/H2 parity in the coverage audit is max routing absolute difference 0.000342 for the 20G subset and 0.000337 for the 12G expansion; corresponding P_scale relative differences 0.001298 and 0.000887. These are input-validation checks for this planning task, not new H1 scores.

## Anchor and frozen 16-case design

Selection followed the preregistered geometry-only rule: eligible existing truth-valid anchors must fit symmetric ±5 nm axial points and the four confirmation sign patterns without clipping or duplicate geometries. Tie-breaking maximized minimum formal-domain boundary margin, then cyclic neighbor clearance, then minimized normalized distance to the 32G coordinate centroid, then case ID. No model error, routing result, tail label, or prediction was used. The selected existing anchor is `K6V1_S31` with ordered D=`[220, 195, 210, 150, 140, 210]` nm, minimum domain boundary margin 10 nm, and minimum cyclic neighbor gap 75 nm.

The local domain is the 3^6 grid of each coordinate at anchor−5, anchor, or anchor+5 nm. Twelve axial cases are development data; four multi-coordinate geometries are sealed confirmation geometries. The anchor is already one of the 32G geometries; total proposed new logical cases remain 16. The sealed responses are not present in this task’s artifacts.

| Case ID | Role | Ordered D1…D6 (nm) | Minimum periodic neighbor gap (nm) | Setup FSP SHA256 prefix | Fresh LOAD |
|---|---|---|---:|---|---|
| K6LDA1_DEV_D1_M05 | DEVELOPMENT_AXIS | 215,195,210,150,140,210 | 77.5 | 91e4f2710c20… | PASS |
| K6LDA1_DEV_D1_P05 | DEVELOPMENT_AXIS | 225,195,210,150,140,210 | 72.5 | c527de5c0cd9… | PASS |
| K6LDA1_DEV_D2_M05 | DEVELOPMENT_AXIS | 220,190,210,150,140,210 | 75.0 | b304ec9fa166… | PASS |
| K6LDA1_DEV_D2_P05 | DEVELOPMENT_AXIS | 220,200,210,150,140,210 | 75.0 | 4768d7ec82f5… | PASS |
| K6LDA1_DEV_D3_M05 | DEVELOPMENT_AXIS | 220,195,205,150,140,210 | 75.0 | f17c4d0cdf13… | PASS |
| K6LDA1_DEV_D3_P05 | DEVELOPMENT_AXIS | 220,195,215,150,140,210 | 75.0 | 71bc1c76ab1a… | PASS |
| K6LDA1_DEV_D4_M05 | DEVELOPMENT_AXIS | 220,195,210,145,140,210 | 75.0 | c5fea1132a0b… | PASS |
| K6LDA1_DEV_D4_P05 | DEVELOPMENT_AXIS | 220,195,210,155,140,210 | 75.0 | 1205d7d2ad0d… | PASS |
| K6LDA1_DEV_D5_M05 | DEVELOPMENT_AXIS | 220,195,210,150,135,210 | 75.0 | 778f6cf28a00… | PASS |
| K6LDA1_DEV_D5_P05 | DEVELOPMENT_AXIS | 220,195,210,150,145,210 | 75.0 | 61449d51a909… | PASS |
| K6LDA1_DEV_D6_M05 | DEVELOPMENT_AXIS | 220,195,210,150,140,205 | 77.5 | d5d73025e75c… | PASS |
| K6LDA1_DEV_D6_P05 | DEVELOPMENT_AXIS | 220,195,210,150,140,215 | 72.5 | 9eff49b0d1fe… | PASS |
| K6LDA1_SEAL_C1 | SEALED_CONFIRMATION_COMBINATION | 225,200,215,145,135,205 | 75.0 | 0eeec0d47c9e… | PASS |
| K6LDA1_SEAL_C2 | SEALED_CONFIRMATION_COMBINATION | 225,190,205,145,145,215 | 70.0 | ad1aa3de99f9… | PASS |
| K6LDA1_SEAL_C3 | SEALED_CONFIRMATION_COMBINATION | 215,200,205,155,135,215 | 75.0 | 74e664473de8… | PASS |
| K6LDA1_SEAL_C4 | SEALED_CONFIRMATION_COMBINATION | 215,190,215,155,145,205 | 80.0 | d7ca34079bec… | PASS |

All 16 are in-domain, on the 5 nm grid, unique from the 32G set, six reserve identities and 25 protected/exclusion geometries, and each other. Cyclic re-registration/permutation augmentation was not used. Periodic-cylinder edge gap is `290 − (D_i + D_(i+1))/2`, including D6↔D1; candidate gaps range 70.0–150.0 nm, hence no geometric overlap. Builder mesh checks pass for all candidates, with minimum lateral margin 32.5 nm and vertical margin 100 nm. This verifies geometry/domain/non-overlap and existing mesh coverage only; the independent fabrication-authority file remains unresolved, so manufacturing acceptance is not claimed.

## Future local model and validation protocol (not executed)

Use one deterministic first-order local affine baseline, not an architecture search: features `[1, (D1−anchor)/5, …, (D6−anchor)/5]`; output the full ordered 21-wavelength Cartesian C_hat state (all seven transmitted orders × TE/TM complex coordinates, separate real/imaginary parts) and a separately predicted P_scale target using its existing definition. No PCA/rank truncation, phase gauge, NP feature, or new P_scale physics is introduced. This changes the global C0/C1 encoder or rank-2 latent path to a small local input-to-integrated-state map; it is only a learnability probe, not an explicit Maxwell or MDC–NP feedback solver.

After the future 12 development HF truths are lawfully available, perform 12 leave-one-axial-geometry-out development evaluations; each split holds out the whole geometry and all 21 wavelengths. Refit all preprocessing on the corresponding geometry-grouped training split. Freeze the final model and evaluator before opening the four confirmation responses, then evaluate the four groups once. Do not tune on them. Use predicted C_hat and predicted P_scale through the original physical-state reconstruction, frozen H2, and every original H1 conjunctive metric. Report applicable local gate attainment without calling this production admission or full-domain confirmation. Original seed-stability comparability is unavailable for a deterministic one-fit affine model unless separately reviewed; it must not be redefined to claim admission. The four confirmations cannot support global reliability or establish that cross-coordinate interactions vanish.

No fits ran here. If later authorized, the minimal computation is 12 deterministic multi-output least-squares development fits plus one final fit, with no neural optimizer search; four sealed evaluations only after freeze. No additional architecture, seeds, rank, loss, or HF cases are recommended in this plan.

## Setup-only preflight and launch dependencies

The existing frozen generic 5 nm K6 setup builder `scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py` (SHA `fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1`) saved 16 FSPs in the task-private path `outputs/coupling_ml/COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1_SETUP_ONLY/`. The paired fresh LOAD-only validator (SHA `b694ecf692376a33673b785774a8ea734c452f11009aad1cfe553f444817e2a8`) passed for all 16 and verified IDs, ordered D values, contract, materials, monitors, and mesh geometry. Candidate specs, stdout/stderr, FSPs, readbacks, and hashes are retained. Total task-private setup output is 8,731,812 bytes; FSP files alone are 8,322,928 bytes. These FSPs are not under the Runner authority path and must not be submitted to `run-one`.

The current production POSTNP monitor setting is inherited unchanged. The POSTNP monitor-validity audit found no independent second-height POSTNP field; the two-air-plane validation task remained blocked before solver entry. Its separate monitor validation remains a Chat review/launch dependency. This plan does not add the second plane, move monitors, or revise the production contract. Any future FSP rebuild after monitor review would need the reviewed contract and fresh LOAD-only proof.

## Future HF / storage estimate

The estimate uses 11 completed prior Stage-1 `created→DONE` records: median 668.13 s, mean 673.76 s, range 653.24–698.57 s. Sixteen single-slot serial cases project to 10,690 s (2.97 h) at the median, 10,780 s (3.00 h) at the mean, and 2.90–3.10 h across observed min/max. Completed-case storage including run directory, setup FSP, authority manifest and LOAD proof has median 369,628,975 bytes; 16×median is 5,914,063,600 bytes (about 5.51 GiB). This excludes an unapproved two-plane monitor payload and is an extrapolation, not a speed guarantee.

Historical S35 remains `FAILED_POSTENTRY`; its separate LOAD-only truth recovery recorded zero replay and a 242,063,007-byte recovery bundle. One failure among 12 identities is too small to estimate a future failure probability. A future post-entry failure consumes its solver entry; preserve evidence and request review rather than replay.

## Review boundary

No solver, training, P_scale fit, reserve, inverse search, Runner change, truth change, or production-monitor change occurred. The task is ready for Chat review of the DOE and monitor dependency. It grants no future HF entry. Continue only after Chat explicitly chooses the science experiment and resolves monitor/Runner authority prerequisites.
