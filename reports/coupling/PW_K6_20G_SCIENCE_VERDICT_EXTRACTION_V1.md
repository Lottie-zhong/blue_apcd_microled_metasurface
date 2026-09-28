# PW_K6_20G_SCIENCE_VERDICT_EXTRACTION_V1

Status: ZERO_SOLVER_COMPLETE; existing artifacts only.
Authority branch: work/mdc-np-coupling-ml-v1
Authority HEAD at extraction: 06c3c89ffb161b081d162ae3b465664ec862648a

## DATASET AUTHORITY

- Fixed-MDC K6 snapshots: 8G, 12G, 20G with 8, 12, 20 valid geometries.
- Existing authority: 20/20 fresh LOAD-only PASS; 20 scientific-valid geometries; replay=0; foreign mutation=0; duplicate entry=0.
- Split: geometry-grouped leave-one-geometry-out; no random wavelength split. Each sample has 21 wavelengths, planes IN/PRENP/POSTNP, and 324 real/imag C_PW components.
- No solver, queue mutation, scientific attempt, replay, AL production, variable MDC, K4/K9, or dipole certification was executed.

## METRIC TABLE

| METRIC | 8G | 12G | 20G |
|---|---:|---:|---:|
| valid geometries | 8 | 12 | 20 |
| scalar MLP RMSE / corr | 0.110462 / 0.809682 | 0.0961759 / 0.8576 | 0.106757 / 0.848511 |
| routing MLP RMSE / corr | 0.0391505 / 0.617461 | 0.0459599 / 0.590168 | 0.0404628 / 0.638734 |
| POSTNP Ridge geometry-only median relative / phase MAE deg | 1.13315 / 85.6028 | 1.04483 / 84.6085 | 1.01204 / 83.0268 |

The 20G RMSE=0.0404628 and corr=0.6387342 are the routing MLP row: INPUT=geometry D1..D6 plus lambda; TARGET=seven post-order power_fraction_of_source; MODEL=shallow MLP; SPLIT=geometry-grouped leave-one-geometry-out; NORMALIZATION=existing CPU analysis pipeline (routing normalization constant is not recorded); N_HELD_OUT_GEOMETRIES=20. It is not a C_PW reconstruction metric.

## 8G SANITY

Verdict: SCIENTIFIC_REVIEW_REQUIRED_8G.
- Geometry uniqueness: snapshot has 8 IDs; freeze-manifest search found 8 matching records and 8 unique geometry hashes.
- C_PW amplitude spread: NOT_AVAILABLE.
- Phase continuity: NOT_AVAILABLE.
- Spectral smoothness: NOT_AVAILABLE.
- Geometry-to-geometry separation: NOT_AVAILABLE.
- R/T/accounting: learnability rows exist, but no 8G sanity closure artifact exists.
- Order topology: NOT_AVAILABLE as a formal sanity result.
- Decoder consistency: NOT_AVAILABLE for direct C_PW-to-routing.
- Collapse/non-collapse: no formal 8G collapse test recorded.
- Existing prior report explicitly says 8G sanity NOT_STARTED/NOT_RUN; the 8G learnability snapshot is not promoted to 8G_SANITY_PASS.

## 8G A/B/C

- A geometry+lambda -> scalar/R/T/orders: Ridge and shallow MLP exist; scalar MLP RMSE/corr=0.110462/0.809682; routing MLP RMSE/corr=0.0391505/0.617461. Exact GP R/T also exists.
- B geometry+lambda -> C_PW: Ridge geometry-only rows exist at IN, PRENP, POSTNP; complex error is decomposed into relative error, magnitude RMSE, and circular phase MAE.
- C geometry+lambda+NP prior -> C_PW: Ridge frozen-upstream-prior rows exist at PRENP and POSTNP; IN prior is unavailable.
- Per-geometry worst identities are retained in the analysis JSON; scalar worst is S15 and routing worst is EXT01. Geometry-only phase errors are approximately 85-88 degrees across 8G planes.

## 12G A/B/C

- A: Ridge, shallow MLP, and exact GP R/T rows; held-out geometries=12 (252 samples / 21 wavelengths).
- B: Ridge geometry-only C_PW rows for IN/PRENP/POSTNP, with per-geometry decomposed errors; MLP C_PW rows only where recorded.
- C: matched Ridge frozen-upstream-prior rows for PRENP/POSTNP; IN prior unavailable.
- ridge geometry plane=1 median_rel=1.03071, p95=2.27797, mag_RMSE=1.77059, phase_MAE_deg=86.8894, worst=K6V1_S03, heldout=12
- ridge prior plane=1 median_rel=0.574322, p95=3.82862, mag_RMSE=0.646954, phase_MAE_deg=39.9143, worst=K6V1_S03, heldout=12
- ridge geometry plane=2 median_rel=1.04483, p95=2.63507, mag_RMSE=2.23707, phase_MAE_deg=84.6085, worst=K6V1_EXT04, heldout=12
- ridge prior plane=2 median_rel=1.39574, p95=6.04854, mag_RMSE=2.3284, phase_MAE_deg=77.0219, worst=K6V1_EXT04, heldout=12

## 20G A/B/C

- A: Ridge and shallow MLP for scalar and seven-order routing; exact GP skipped at 20G because of cubic cost; held-out geometries=20 (420 samples / 21 wavelengths).
- B: Ridge and shallow MLP geometry-only C_PW rows for IN/PRENP/POSTNP.
- C: Ridge frozen-upstream-prior rows for PRENP/POSTNP; IN prior unavailable.
- ridge geometry plane=0 median_rel=1.0016, p95=1.54939, mag_RMSE=0.237071, phase_MAE_deg=84.8202, worst=K6V1_EXT03, heldout=20
- ridge geometry plane=1 median_rel=1.00822, p95=1.74647, mag_RMSE=1.85938, phase_MAE_deg=85.6798, worst=K6V1_EXT02, heldout=20
- ridge prior plane=1 median_rel=0.401754, p95=2.77164, mag_RMSE=0.519805, phase_MAE_deg=33.2581, worst=K6V1_EXT08, heldout=20
- ridge geometry plane=2 median_rel=1.01204, p95=2.02278, mag_RMSE=2.31376, phase_MAE_deg=83.0268, worst=K6V1_EXT13, heldout=20
- ridge prior plane=2 median_rel=1.18215, p95=5.11028, mag_RMSE=1.96212, phase_MAE_deg=68.3881, worst=K6V1_EXT04, heldout=20
- mlp geometry plane=2 median_rel=1.09523, p95=3.44255, mag_RMSE=2.03434, phase_MAE_deg=80.2876, worst=K6V1_EXT04, heldout=20

## 12G->20G LEARNING CURVE

- Routing MLP improves: RMSE 0.0459599 -> 0.0404628, corr 0.590168 -> 0.638734.
- Scalar MLP changes (RMSE worsens here): RMSE 0.0961759 -> 0.106757, corr 0.8576 -> 0.848511.
- Common-geometry Ridge C_PW median-relative improvement (positive means 20G lower):
  - plane 0: {'n': 12, 'mean': 0.011038934604197248, 'median': 0.008389002852020655, 'improved': 11, 'worsened': 1}
  - plane 1: {'n': 12, 'mean': 0.027940150114630274, 'median': 0.01661788951670129, 'improved': 10, 'worsened': 2}
  - plane 2: {'n': 12, 'mean': 0.04150973266765911, 'median': 0.011400957583059368, 'improved': 10, 'worsened': 2}
  - plane 0 magnitude: {'n': 12, 'mean': -0.0014178685904254126, 'median': -0.0007603743032569693, 'improved': 4, 'worsened': 8}; phase: {'n': 12, 'mean': 1.7169033667508724, 'median': 1.4185454215642963, 'improved': 9, 'worsened': 3}
  - plane 1 magnitude: {'n': 12, 'mean': -0.04479989580650521, 'median': -0.04518541476078064, 'improved': 0, 'worsened': 12}; phase: {'n': 12, 'mean': 2.0814823272250655, 'median': 2.1201140807972934, 'improved': 8, 'worsened': 4}
  - plane 2 magnitude: {'n': 12, 'mean': -0.059980984083667165, 'median': -0.04862448796440377, 'improved': 4, 'worsened': 8}; phase: {'n': 12, 'mean': 0.6477940334960728, 'median': 0.544098430838126, 'improved': 7, 'worsened': 5}
- Conclusion: useful but weak/uneven learning curve. Routing improves clearly; C_PW state improvement is plane/metric dependent and remains around unit relative error with large phase error. It is not a monotonic production-learning certification.

## NP PRIOR EFFECT

### 8G
- plane 1: B-C median_rel mean=0.235732, median=0.254358, improved/worsened=8/0; magnitude mean=0.93008, improved/worsened=8/0; phase_deg mean=36.3525, improved/worsened=8/0
- plane 2: B-C median_rel mean=-0.196449, median=-0.196478, improved/worsened=1/7; magnitude mean=-0.304653, improved/worsened=3/5; phase_deg mean=13.2183, improved/worsened=8/0
### 12G
- plane 1: B-C median_rel mean=0.453673, median=0.45792, improved/worsened=12/0; magnitude mean=1.13198, improved/worsened=12/0; phase_deg mean=46.9751, improved/worsened=12/0
- plane 2: B-C median_rel mean=-0.369043, median=-0.332195, improved/worsened=1/11; magnitude mean=-0.00551377, improved/worsened=7/5; phase_deg mean=7.58658, improved/worsened=10/2
### 20G
- plane 1: B-C median_rel mean=0.607466, median=0.608546, improved/worsened=20/0; magnitude mean=1.34793, improved/worsened=20/0; phase_deg mean=52.4217, improved/worsened=20/0
- plane 2: B-C median_rel mean=-0.187081, median=-0.173781, improved/worsened=5/15; magnitude mean=0.414391, improved/worsened=15/5; phase_deg mean=14.6387, improved/worsened=19/1

- Positive B-C means the prior reduces the error. Counts are matched held-out geometries.
- Wavelength dependence is not stored: rows aggregate 21 wavelengths over 440-460 nm, so persistence at every wavelength inside the supported interval cannot be claimed.
- Overall result: prior helps some PRENP relative/phase metrics but is not consistently helpful for POSTNP or all geometries.

## H1 VERDICT

H1: [D1...D6, lambda] -> C_PW.
Verdict: H1_NOT_SUPPORTED_CURRENT_REPRESENTATION.
- 20G geometry-only C_PW remains approximately unit relative error with phase MAE about 80-86 degrees on the modal planes; the 12G->20G change is modest and uneven.
- Dominant bottleneck: phase, with plane-dependent magnitude/conditioning difficulty, especially PRENP/POSTNP. A deeper network is not assumed to be the default explanation.

## H2 VERDICT

H2: C_PW -> routing.
Verdict: H2_NOT_SUPPORTED.
- No direct state-input -> routing regression or deterministic decoder audit is present. Existing routing rows use geometry+lambda directly.
- Reconstruction error, direct state-to-routing correlation, order-power fidelity, and centroid/directional fidelity are NOT_AVAILABLE. The 0.0404628/0.6387342 routing row cannot answer H2.

## REPRESENTATION BOTTLENECK

- C_PW is physically capable of deriving order power in principle as a modal complex-state representation, but direct decoder evidence is absent.
- C_PW is not currently learnable enough from geometry for production use.
- Phase is harder than magnitude in the observed state metrics; errors are global across planes/geometries, with worst cases but no stored order/wavelength localization.
- 12G->20G is useful for scalar/routing outputs but weak/uneven for C_PW. Current bottleneck is representation/conditioning plus coverage; model capacity is not established as primary.

## ACTIVE LEARNING READINESS

Verdict: ACTIVE_LEARNING_NOT_READY.
H1 is not supported and H2 lacks direct evidence. Do not start Active Learning; representation and decoder evidence must precede production AL.

## CONTROL GATE VERDICT

- EXT03-EXT14 crossed the intended pause because new_entry_hold was false at control generation 20 and queue payloads lacked an explicit validation-only/autofill veto.
- Minimal dispatcher fix implemented: validation-only/manual-only or autofill_enabled=false rows remain WAIT_RESOURCE_CAPACITY during refill; exact permit remains subject to final admission.
- Admission 34 checks PASS; global 20/20 PASS; chaos 12/12 PASS; persistence 20/20 PASS; solver invocations for the fix/tests=0.
- Future explicit validation gates are enforceable; historical EXT03-EXT14 remain valid data labeled NORMAL_AUTOFILL_AFTER_RELEASE.

## GIT

- Branch: work/mdc-np-coupling-ml-v1
- HEAD at extraction: 06c3c89ffb161b081d162ae3b465664ec862648a
- No push. Existing dirty/untracked files preserved; no FSP/H5/raw payload selected for this report.

## NEXT

Chart review this verdict and the missing 8G sanity/direct C_PW-to-routing evidence. Do not execute NEXT.
