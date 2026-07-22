# MDC-ML SHARED_SURROGATE_V1

## Scope and evidence

This run used the frozen Combined-2512 registry only. It did not generate candidates, call TMM/FDTD/Lumerical, run active learning or inverse optimization, expand to 5,000, or modify frozen data. Formal input signatures remained `fc8c1798...119` (candidate), `daea19d4...4c4c` (Formal-2000), and `d14b0555...591d` (Combined-2512).

## Environment

- Python 3.10.20; numpy 2.2.5; pandas 2.3.3; scikit-learn 1.7.1; joblib 1.5.3; torch 2.5.1+cu121.
- Formal device: CPU, 8 process-local threads, deterministic seeds 20260720/20260721/20260722, DataLoader workers 0.
- CUDA was available on an NVIDIA GeForce RTX 3080 but was not used for formal results.

## Data integrity and physical feature contract

- Population: 2,512 classification records (512 PRE1 + 2,000 Formal); 737 continuous-regression eligible records; one power-balance failure retained for classification/audit and excluded from regression.
- Total family counts: asymmetric_pair_count 257, dual_defect 255, grouped_chirped 255, hybrid_periodic_aperiodic 254, locally_aperiodic 254, off_center_defect 569, symmetric_periodic 414, termination_reversed 254.
- Feature allowlist: 150 physical features. Positions 0--24 each encode material token, thickness, present mask, defect mask and normalized position (125); 17 global physical descriptors; 8 family one-hot values.
- Material mapping: PAD=0, APCD_TIO2_NATIVE_M1=1, APCD_SIO2_NATIVE_M1=2. PAD thickness is paired with present mask. MLP material tokens use an embedding and are not scaled.
- No sample/hash/artifact/origin/source/anchor/generation/target/quality/Pareto field is present in the feature list. Feature signature: `cc49c7b99dcf486f373f1add526c4c23174069dc92bace0dae6b8fabbcc3cd69`.

## Frozen four-way split

Seed `20260720`; signature `8479d9712153b9b2e676231549f48a35e87207dd64cdbcd914eb39513528d42e`.

| Split | Total | 4D eligible | Shortlist | Family counts in configured order |
|---|---:|---:|---:|---|
| train | 1507 | 443 | 80 | 155,154,154,153,153,338,248,152 |
| validation | 377 | 111 | 19 | 38,38,38,38,38,87,62,38 |
| calibration | 251 | 72 | 13 | 26,25,25,25,25,57,42,26 |
| test | 377 | 111 | 19 | 38,38,38,38,38,87,62,38 |

Canonical, physical and derived split-group overlap counts are all zero. Calibration/test each contain regression-eligible examples from all eight families. Test was sealed before training and was used once after validation-only model selection and calibration-only calibration selection.

The nearest-neighbor diagnostic found median normalized test-to-train distance 0.1066, minimum 0.00484 and 68/377 test examples below the fixed 0.05 extreme-neighbor threshold. All three anchor parents cross IID splits, so IID test results can be optimistic for local interpolation; the separate anchor holdouts quantify this risk.

## Model suite and validation selection

Ten classification and ten regression configurations were compared: two dummies, three linear settings, two ExtraTrees settings, two HistGradientBoosting settings, and one shared MLP 3-seed ensemble. The MLP used material embeddings, a shared [256,128] trunk, four weighted BCE heads and four masked SmoothL1 heads.

Classification validation ranking (four principal PR-AUC columns):

| Model | Spectral | Angular | 4D eligible | Shortlist | 4D ROC-AUC |
|---|---:|---:|---:|---:|---:|
| ExtraTrees-1 | .862 | .866 | .701 | .328 | .823 |
| ExtraTrees-0 | .858 | .861 | .698 | .343 | .814 |
| HGB-1 | .856 | .861 | .657 | .188 | .827 |
| HGB-0 | .851 | .860 | .644 | .195 | .826 |
| shared MLP | .827 | .830 | .597 | .184 | .798 |
| Linear best | .728 | .740 | .424 | .097 | .667 |
| Dummy prevalence | .504 | .501 | .294 | .050 | .500 |

Regression validation ranking:

| Model | Mean IQR-NMAE | Mean Spearman | Worst target NMAE |
|---|---:|---:|---:|
| shared MLP 3-seed | .318 | .796 | .339 |
| ExtraTrees-0 | .350 | .779 | .375 |
| ExtraTrees-1 | .350 | .783 | .376 |
| HGB-1 | .354 | .770 | .369 |
| HGB-0 | .355 | .768 | .368 |
| Ridge best | .497 | .503 | .534 |
| Dummy median | .522 | undefined constant predictor | .675 |

The deployable bundle therefore uses ExtraTrees-1 for classification and the 3-seed shared MLP ensemble for regression. The MLP did not win classification and was not selected merely to force a single-network deliverable.

## One-time test results

All classification probabilities were calibrated with isotonic regression on calibration only; thresholds were selected without test labels.

| Head | Prevalence | ROC-AUC | PR-AUC | Balanced accuracy | Precision | Recall | F1 | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| spectral valid | .507 | .859 | .826 | .792 | .763 | .859 | .808 | .157 | .079 |
| angular valid | .501 | .815 | .809 | .732 | .716 | .772 | .743 | .178 | .093 |
| 4D eligible | .294 | .848 | .721 | .746 | .624 | .658 | .640 | .138 | .052 |
| shortlist | .050 | .783 | .241 | .738 | .109 | .842 | .193 | .043 | .015 |

The 4D PR-AUC exceeds prevalence by 0.427. Shortlist precision remains low because only 5.0% of the test population is positive; its fixed-seed test bootstrap 95% PR-AUC interval is [0.100, 0.434], so accuracy and the .241 point estimate are not used alone.

| Regression target | MAE | RMSE | R2 | Spearman | Pearson | IQR-NMAE | Bias | P90 abs error |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| spectral FWHM (nm) | 2.748 | 4.531 | .698 | .801 | .840 | .395 | .509 | 7.610 |
| angular FWHM (deg) | 9.108 | 12.665 | .586 | .682 | .767 | .412 | .454 | 18.511 |
| cone5 proxy | .0262 | .0352 | .472 | .665 | .693 | .354 | .00434 | .0565 |
| normal-band proxy | .1478 | .2014 | .469 | .655 | .691 | .349 | .0215 | .3397 |

Test family mean NMAE is worst for termination_reversed (.555), followed by symmetric_periodic (.478); locally_aperiodic is best (.223). This family spread is a deployment warning.

## Calibration, uncertainty and Pareto retrieval

- Calibration-split conformal test coverage: 80% target = spectral .748, angular .847, cone .910, band .883; 90% target = spectral .919, angular .955, cone .955, band .964. Mean 90% coverage is .948.
- 90% full interval widths: 16.86 nm, 52.95 deg, .156 cone proxy, .934 band proxy. These are calibrated intervals; MLP seed dispersion alone is only an uncertainty score.
- Uncertainty vs absolute-error Spearman: spectral .355, angular .153, cone -.007, band .073. Except for spectral FWHM, ensemble dispersion is a weak error-ranking signal and should not be the sole acquisition function.
- Test eligible count 111; true Pareto 24; predicted Pareto 45; precision .289; recall .542; F1 .377; pairwise domination accuracy .930; true recall@K .292; recall@2K .625.

## Learning curve and OOD diagnostics

| Train fraction | Classification n | Regression n | 4D PR-AUC | Mean NMAE | Mean Spearman |
|---:|---:|---:|---:|---:|---:|
| 25% | 376 | 118 | .603 | .442 | .566 |
| 50% | 753 | 213 | .611 | .388 | .796 |
| 75% | 1130 | 337 | .681 | .335 | .784 |
| 100% | 1507 | 443 | .701 | .318 | .787 |

More data is still useful, but the curve does not by itself justify an immediate 5,000 run. Acquisition should first target sparse/high-error neighborhoods.

LOFO regression is weakest for dual_defect (NMAE 1.899, Spearman .300), termination_reversed (1.196, .239) and off_center_defect (.870, .210). The explicit-fabrication anchor holdout is the most serious local extrapolation failure (NMAE .509, Spearman .006), whereas the two ZL1 anchor holdouts remain strong. Formal-to-PRE1 transfer is materially better than PRE1-to-Formal. These results prohibit treating unseen-family or explicit-fabrication extrapolation as validated.

## Decision

`READY_ACTIVE_LEARNING_V1`

All quantitative IID gates passed: 4D PR-AUC uplift, 4D ROC-AUC, mean/minimum target Spearman, mean IQR-NMAE, Pareto recall@2K and 90% conformal coverage. A 5,000 expansion is not currently justified. The next stage should be a bounded surrogate-guided acquisition proposal with hard family coverage, explicit-fabrication anchor safeguards, uncertainty diversity and mandatory TMM verification before any candidate is accepted. It must not claim general OOD readiness.

## Reproducibility and outputs

- Champion artifacts: classification and regression joblib bundles; prediction hashes are frozen in `manifest_v1.json`.
- Output contains 28 artifacts excluding manifest, 23,635,757 bytes excluding manifest, signature `1cd29db19f5bb9c073a64bfb7f52991781fa7041ee716aaf947d342870e9e24d`.
- No generated output is tracked. Repository source scope is exactly the five SHARED_SURROGATE_V1 files.

## Verification

- Surrogate专项：40 passed，包括相同 seed 的 MLP prediction exact reproducibility。
- Full MDC-ML no-solver suite：166 passed, 1 explicitly deselected cross-fidelity test that would invoke new TMM。
- Repository freeze audit：12/12 PASS，payload drift 0。
- Smoke、PRE1、Formal-2000、Combined-2512、dataset 与 model validation-only：PASS。
- Champion serialization roundtrip、prediction signatures、feature leakage、split determinism、artifact/output immutability、diff/whitespace：PASS。


## SHARED_SURROGATE_V1-A2 contracts
Test-seal, split roles, hybrid champions with artifact hashes, and bounded active-learning/OOD contracts are machine-readable in config and read-only validated; no output was regenerated.
