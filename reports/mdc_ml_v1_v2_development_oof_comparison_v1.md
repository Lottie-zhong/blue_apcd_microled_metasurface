# v1 prospective vs v2 development OOF comparison v1

Status: PASS. This is read-only comparison evidence; it does not select a champion, make a promotion decision, or create any new prediction.

## Provenance and alignment

- v1 prospective source: `outputs/mdc_ml_active_learning_round1_v1/selected_batch_v1.csv`, SHA256 `3578f8be74bd41bd114315451ba1cfd8203bc4f7643a2bd6699a47cbe7a8d773`.
- The selected batch mtime (`2026-07-22 16:58`) precedes `tmm_labels_v1.csv` materialization (`17:12`), and its SHA matches the Round1 frozen manifest. Its acquisition record marks surrogate outputs as non-physical labels.
- v2 classification manifest/fingerprint: `4f76e6e37a1ce60329531a88bdade4fd6465ac5c13c1854bf6b3b0687c4bc7ad` / `7256061c7fc4366dd451374a32224b800fd1fdc0c09290b90f8435dd1fceaba3`.
- v2 regression manifest: `9d091f9b1548ea391edfda248154d7ec2bf23f25e6228ce1fc0f1cac4657da9e`.
- Exact alignment: classification 128 rows; regression 100 eligible rows × 4 targets = 400 rows. The 28 ineligible identities were excluded from regression metrics. Formal OOF inventories had zero added/removed/modified files.

## Statistical evidence

Paired parent/source-group bootstrap: 2,000 repetitions, seed 20260723, 80% CI. Negative deltas favour v2 because all primary losses are lower-is-better.

| Comparison | v1 | v2 | delta v2−v1 | 80% CI |
| --- | ---: | ---: | ---: | ---: |
| Classification Brier | 0.16438 | 0.17398 | +0.00960 | [-0.00107, +0.02004] |
| Regression aggregate normalized MAE | 0.38346 | 0.35366 | -0.02980 | [-0.04023, -0.01973] |
| spectral FWHM MAE | 2.67136 | 2.22774 | -0.44362 | [-0.61412, -0.28132] |
| angular FWHM MAE | 8.51960 | 7.84195 | -0.67765 | [-1.06762, -0.27966] |
| cone5 integral MAE | 0.02835 | 0.02731 | -0.00104 | [-0.00229, +0.00019] |
| normal-band transmission MAE | 0.16113 | 0.15664 | -0.00449 | [-0.01143, +0.00228] |

The regression aggregate is the frozen arithmetic mean of target-wise MAE normalized by the v1 frozen training IQR. Classification probability quality/threshold metrics were: v1 vs v2 ROC-AUC 0.70732/0.66696, ECE 0.14840/0.14918, and threshold balanced accuracy 0.610/0.605.

## Practical effects, subgroups, and limits

- Regression: the aggregate and two targets (spectral and angular FWHM) have 80% intervals below zero. Cone5 and transmission are inconclusive at the specified interval.
- Classification: the primary Brier interval crosses zero, so the observed +0.00960 change is inconclusive under this contract; threshold and calibration summaries do not establish a practical advantage.
- All eight frozen topology-family subgroups met the required sample floor. Classification Brier intervals were clearly lower only for `off_center_defect` and clearly higher for `grouped_chirped`; other family results were inconclusive. Regression normalized-MAE intervals were lower for `dual_defect`, `grouped_chirped`, `locally_aperiodic`, and `symmetric_periodic`; remaining family results were inconclusive.
- No promotion/route decision was executed or implied by this evidence.

## Safety

New fits/predictions, added formal OOF calls, sealed reads/predictions, solver calls, and final-model calls were all zero. Sealed evaluation count remained 1.
