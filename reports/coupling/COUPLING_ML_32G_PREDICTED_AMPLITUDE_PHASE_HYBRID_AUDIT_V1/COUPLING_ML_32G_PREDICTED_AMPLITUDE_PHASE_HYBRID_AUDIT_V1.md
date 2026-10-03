# COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1

## STATUS
COMPLETE_POST_HOC_DEVELOPMENT_AUDIT. Gate attainment is reported only; no production admission is inferred.

## AUTHORITY / GIT
Starting HEAD `456cf707880e25283b325dad4b3fc5904aae58d1` on `work/mdc-np-coupling-ml-v1`. The frozen C0/C1 continuation and POC, 32G truth/H1 package, existing LOGO folds, H1 authority and H2 source are hash-pinned in `protocol.json` and `audit.json`. Scope: 32 geometries × 21 wavelengths (672 rows), seven ordered diffraction orders and TE/TM coordinates, seeds 0/1/2.

## ZERO-SOLVER / ZERO-TRAINING ASSERTION
No model fit, FDTD, GPU Runner, new HF, reserve, inverse search or platform development was run. Only saved OOF predictions were read and combined.

## HYBRID DEFINITION / FALLBACK
For each matching seed, geometry, wavelength, order and TE/TM coordinate: `A1=abs(C1)` and `u0=C0/abs(C0)`; `C_hybrid=A1*u0`. If `abs(C0)<1e-8`, use the saved C1 complex phase when its coordinate is nonzero; if both saved complex phases are undefined, use fixed `+1+0i`. The threshold is inherited from the frozen C0/C1 phase rule. No truth enters this construction. See `fallback_by_geometry.csv` for frequency and amplitude/H2-power share.

## FACTORIZATION VALIDITY
The frozen physical reconstruction uses the H2 per-coordinate power coefficient times `abs(C_hat)^2` and applies its existing single scale `sqrt(P_scale_pred / unscaled_modal_power)`. Hybrid coordinate magnitudes and per-seed normalization denominators match C1; no extra normalization or P_scale change was made. The official H1 state gate is evaluated on the arithmetic seed-mean raw C_hat, matching the frozen POC evaluation path. Mean H2 results are separately checked because squaring a phase-varying seed mean can change powers.

## C0 / C1 / HYBRID ORIGINAL H1
The table reports median / q95 / worst across the 32 geometries. H1 is conjunctive.

| Arm | H1 | State | Routing | Absolute order | Thresholded relative | P_scale/total | Routing r | P_scale r | Seed std |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FULL | FAIL | 0.819 / 1.124 / 1.269 | 0.2028 / 0.3194 / 0.3438 | 0.07937 / 0.1255 / 0.1352 | 0.9213 / 0.9777 / 0.9855 | 0.2041 / 0.5749 / 0.7187 | 0.7713 | 0.9432 | 0.0146 |
| C0 | FAIL | 0.819 / 1.124 / 1.269 | 0.2028 / 0.3194 / 0.3438 | 0.07937 / 0.1255 / 0.1352 | 0.9213 / 0.9777 / 0.9855 | 0.2041 / 0.5749 / 0.7187 | 0.7713 | 0.9432 | 0.0146 |
| C1 | FAIL | 0.9342 / 1.273 / 1.384 | 0.1108 / 0.21 / 0.2401 | 0.04757 / 0.08764 / 0.09163 | 0.5832 / 0.85 / 0.9542 | 0.2041 / 0.5749 / 0.7187 | 0.7740 | 0.9432 | 0.0228 |
| HYBRID | FAIL | 0.9239 / 1.293 / 1.48 | 0.1152 / 0.2184 / 0.2211 | 0.04819 / 0.08305 / 0.09606 | 0.6051 / 0.8689 / 0.9694 | 0.2041 / 0.5749 / 0.7187 | 0.7709 | 0.9432 | 0.0104 |

Frozen gate limits are state median/q95 ≤0.50/0.80; routing ≤0.05/0.10 with Pearson ≥0.95; absolute order ≤0.05/0.10; thresholded-relative ≤0.30/0.75; P_scale/total ≤0.15/0.30 with Pearson ≥0.95; seed state-median standard deviation ≤0.03. The table shows only absolute-order and seed-stability attainment for HYBRID. C0 reproduces historical FULL to displayed precision; exact baseline parity is in `results.json`.

C0 / historical FULL H1 metric differences are below 6e-10 in the maximum paired geometry gate metrics; the baseline parity checks are hash-pinned in `results.json`. Per-seed gate metrics are in `seed_metrics.csv`. The fixed OOF P_scale branch is shared by all arms. Paired deltas use the same 32 geometries; lower error is better, a negative candidate-minus-reference delta is an improvement, and win/tie/loss uses the frozen absolute tolerance. These paired geometries and their wavelength/seed records are dependent; no independent-sample significance claim is made.

### Paired geometry deltas
| Comparison | Metric | Median / q95 / worst Δ | Win / tie / loss |
|---|---|---:|---:|
| C1 − C0 | State | 0.117 / 0.2259 / 0.2964 | 1/0/31 |
| C1 − C0 | Routing | -0.09776 / -0.01511 / 0.008406 | 30/0/2 |
| C1 − C0 | Absolute order | -0.03485 / 0.01678 / 0.02976 | 27/0/5 |
| C1 − C0 | Thresholded relative | -0.3006 / -0.04971 / 0.1291 | 30/0/2 |
| C1 − C0 | Amplitude | -0.2338 / -0.1287 / -0.08856 | 32/0/0 |
| C1 − C0 | Truth-amplitude-weighted phase (rad) | -0.0334 / 0.3087 / 0.379 | 18/0/14 |
| C1 − C0 | Cross-order relative phase (rad) | 0.379 / 0.5977 / 0.6161 | 0/0/32 |
| HYBRID − C0 | State | 0.1281 / 0.2023 / 0.2782 | 1/0/31 |
| HYBRID − C0 | Routing | -0.09772 / -0.01237 / 0.009514 | 30/0/2 |
| HYBRID − C0 | Absolute order | -0.03306 / 0.01487 / 0.03412 | 27/0/5 |
| HYBRID − C0 | Thresholded relative | -0.3121 / -0.03044 / 0.1888 | 31/0/1 |
| HYBRID − C0 | Amplitude | -0.2354 / -0.1176 / -0.06004 | 32/0/0 |
| HYBRID − C0 | Truth-amplitude-weighted phase (rad) | -0.0148 / 0.04715 / 0.06586 | 18/0/14 |
| HYBRID − C0 | Cross-order relative phase (rad) | 0.3581 / 0.4925 / 0.5418 | 0/0/32 |
| HYBRID − C1 | State | -0.006918 / 0.112 / 0.1299 | 18/0/14 |
| HYBRID − C1 | Routing | 0.001573 / 0.02328 / 0.02865 | 12/0/20 |
| HYBRID − C1 | Absolute order | 0.0008556 / 0.008852 / 0.01267 | 13/0/19 |
| HYBRID − C1 | Thresholded relative | 0.02094 / 0.1861 / 0.3354 | 14/0/18 |
| HYBRID − C1 | Amplitude | 0.00258 / 0.07047 / 0.1088 | 14/0/18 |
| HYBRID − C1 | Truth-amplitude-weighted phase (rad) | 0.03096 / 0.3869 / 0.533 | 14/0/18 |
| HYBRID − C1 | Cross-order relative phase (rad) | -0.03021 / 0.1757 / 0.3523 | 20/0/12 |

### Per-seed medians
| Arm | Seed | State | Routing | Thresholded relative | Amplitude | Truth-weighted phase (rad) | Cross-order relative phase (rad) |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 0 | 0.8212 | 0.1968 | 0.9093 | 0.6207 | 1.3459 | 0.7216 |
| C0 | 1 | 0.8078 | 0.1974 | 0.8952 | 0.6460 | 1.2889 | 0.7144 |
| C0 | 2 | 0.8432 | 0.1986 | 0.9267 | 0.6462 | 1.3604 | 0.7255 |
| C1 | 0 | 0.9553 | 0.1089 | 0.5424 | 0.3726 | 1.3516 | 1.1716 |
| C1 | 1 | 0.9622 | 0.1103 | 0.5601 | 0.3728 | 1.3120 | 1.2037 |
| C1 | 2 | 1.0067 | 0.1013 | 0.5516 | 0.3722 | 1.4427 | 1.1939 |
| HYBRID | 0 | 0.9748 | 0.1089 | 0.5424 | 0.3726 | 1.3459 | 1.1651 |
| HYBRID | 1 | 0.9496 | 0.1103 | 0.5601 | 0.3728 | 1.2889 | 1.1403 |
| HYBRID | 2 | 0.9658 | 0.1013 | 0.5516 | 0.3722 | 1.3604 | 1.1199 |

## AMPLITUDE / PHASE / RELATIVE-PHASE
Amplitude error is `sqrt(sum((|C_hat|-|C_PW|)^2)/sum(|C_PW|^2))`. `phase_weighted_rmse_rad` uses fixed truth-amplitude-squared weights; `predicted_amplitude_weighted_phase_rmse_rad` changes with predicted amplitude and is not a phase-only comparison. Cross-order `relative_phase_rmse_rad` uses the frozen POC `|C_truth|*|C_prediction|` weights; the separate truth-weighted column fixes those weights. Common-phase removal uses held-out truth and is ORACLE DIAGNOSTIC only.

| Arm | Amplitude med/q95/worst | Truth-weighted phase med/q95/worst (rad) | Predicted-amplitude-weighted phase med/q95/worst (rad) | Cross-order phase med/q95/worst (rad) | Truth-weighted relative phase med/q95/worst (rad) | Oracle common-phase SSE explained med/q95/worst |
|---|---:|---:|---:|---:|---:|---:|
| FULL | 0.6446 / 0.8229 / 0.8515 | 1.33 / 2.054 / 2.406 | 0.5144 / 1.316 / 1.854 | 0.6826 / 1.107 / 1.335 | 1.089 / 1.462 / 1.547 | 4.94% / 33.15% / 55.34% |
| C0 | 0.6446 / 0.8229 / 0.8515 | 1.33 / 2.054 / 2.406 | 0.5144 / 1.316 / 1.854 | 0.6826 / 1.107 / 1.335 | 1.089 / 1.462 / 1.547 | 4.94% / 33.15% / 55.34% |
| C1 | 0.411 / 0.5763 / 0.6236 | 1.409 / 1.976 / 2.037 | 1.153 / 1.608 / 1.798 | 1.197 / 1.52 / 1.555 | 1.203 / 1.491 / 1.505 | 6.68% / 34.21% / 41.33% |
| HYBRID | 0.4195 / 0.5719 / 0.5918 | 1.324 / 2.048 / 2.388 | 1.12 / 1.651 / 1.978 | 1.092 / 1.408 / 1.614 | 1.104 / 1.485 / 1.543 | 7.44% / 38.73% / 55.70% |

The summary phase-metric weight changes can reflect seed-mean phase reweighting by the amplitude branch: they do not mean the per-seed C0 phase predictor changed. HYBRID uses C0 per-seed phases except the recorded fallback. Oracle alignment is excluded from all H1 gates.

## H2 POWER CONSISTENCY
H2's frozen post-projection modal-power path sums the stored TE/TM coordinate powers and has no TE/TM or inter-order cross term after projection. The existing projection coefficient solve was not rerun. Physical reconstruction applies only its original global `sqrt(P_scale_pred / unscaled_modal_power)` factor.

| Aggregation | Max order-power Δ vs C1 | Max routing Δ vs C1 | Max scale-factor Δ vs C1 | Max total-power Δ vs C1 |
|---|---:|---:|---:|---:|
| 0 | 3.89e-16 | 4.44e-16 | 7.11e-15 | 4.44e-16 |
| 1 | 3.33e-16 | 3.33e-16 | 7.11e-15 | 4.44e-16 |
| 2 | 2.78e-16 | 3.33e-16 | 7.11e-15 | 4.44e-16 |
| MEAN | 0.0645 | 0.153 | 2.39 | 6.66e-16 |

Each paired seed's hybrid magnitudes match C1 within 2.22e-16; each seed's reconstructed order powers/routing match within floating-point roundoff. The required arithmetic seed-mean prediction is different: mean H2 order/routing changes are shown above, while total power still closes to the same shared predicted P_scale (max closure 7.77e-16 absolute, 1.17e-15 relative).

## TAIL ATTRIBUTION
H1 aggregate values above cover all 32 geometries × 21 wavelengths. The following rows are the preselected geometry tails; FULL is omitted because its historical parity with C0 is separately retained in `results.json`.

| Geometry | Arm | State | Routing | Absolute order | Thresholded relative | Amplitude | Truth-weighted phase (rad) | Cross-order relative phase (rad) | P_scale rel. RMSE |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| K6V1_S31 | C0 | 1.2015 | 0.3438 | 0.1293 | 0.9222 | 0.8515 | 2.4055 | 1.0635 | 0.7187 |
| K6V1_S31 | C1 | 1.3498 | 0.2401 | 0.0916 | 0.7102 | 0.6236 | 2.0318 | 1.2586 | 0.7187 |
| K6V1_S31 | HYBRID | 1.4797 | 0.2193 | 0.0813 | 0.6302 | 0.5695 | 2.3884 | 1.1262 | 0.7187 |
| K6V1_S33 | C0 | 1.2690 | 0.2632 | 0.0955 | 0.9855 | 0.7167 | 1.9317 | 0.8798 | 0.2349 |
| K6V1_S33 | C1 | 1.3843 | 0.1458 | 0.0549 | 0.8012 | 0.4578 | 1.8591 | 1.4960 | 0.2349 |
| K6V1_S33 | HYBRID | 1.3948 | 0.1545 | 0.0588 | 0.8578 | 0.4997 | 1.9082 | 1.4216 | 0.2349 |
| K6V1_EXT08 | C0 | 1.0330 | 0.3285 | 0.1352 | 0.9560 | 0.8406 | 1.9926 | 1.0495 | 0.3098 |
| K6V1_EXT08 | C1 | 1.0997 | 0.2044 | 0.0898 | 0.5842 | 0.5570 | 1.5339 | 1.3093 | 0.3098 |
| K6V1_EXT08 | HYBRID | 1.2081 | 0.2211 | 0.0961 | 0.7307 | 0.5918 | 1.9578 | 1.3209 | 0.3098 |

HYBRID worst state-by-order location: K6V1_EXT04 order -1 (relative state RMSE 2.733); worst routing wavelength: K6V1_EXT08 at 452 nm (RMSE 0.304); worst absolute-order wavelength: K6V1_EXT08 at 451 nm (RMSE 0.183); worst relative-phase wavelength: K6V1_S33 at 440 nm (RMSE 1.954). Full top-five locations for every arm are in `results.json` and `per_order.csv` / `per_wavelength.csv`. These are error associations, not causal attribution.

## P_SCALE DIAGNOSTIC
The saved RBF KRR OOF prediction matches the POC frozen branch exactly, and its truth is consistent with the sum of absolute-order power to 2.22e-16 maximum absolute difference. No refit, rescaling, clipping or oracle P_scale entered H1.

| Geometry | Relative RMSE | Mean predicted/truth scale | Mean signed relative error | Unit-sum spectral shape RMSE | Within-geometry spectral Pearson |
|---|---:|---:|---:|---:|---:|
| K6V1_S31 | 0.7187 | 1.4093 | 0.5728 | 0.0091 | 0.9649 |
| K6V1_S37 | 0.6390 | 1.3211 | 0.4500 | 0.0124 | 0.9239 |
| K6V1_S42 | 0.5224 | 1.4268 | 0.4718 | 0.0062 | 0.9793 |
| K6V1_EXT06 | 0.4038 | 1.2666 | 0.3612 | 0.0064 | 0.9923 |
| K6V1_EXT01 | 0.3264 | 1.1739 | 0.1365 | 0.0104 | 0.9359 |

Across geometries P_scale relative-RMSE median/q95/worst is 0.2041 / 0.5749 / 0.7187; errors overlap with routing/state errors at Pearson/Spearman r = 0.487/0.538 for routing and 0.452/0.317 for state (HYBRID). These are attribution clues only. The worst scale error is S31; its spectral shape remains correlated but its absolute scale is substantially high.

## LEAKAGE AUDIT
One predeclared hybrid was formed only from same-fold/same-seed OOF predictions. Held-out truth was used for H1 and labeled diagnostics only; it did not choose C0/C1 by geometry/wavelength/order, set fallback, set a mixing weight or select among candidates. No scaler/PCA, retraining, candidate search or oracle P_scale entered the prediction path. Exact fold/seed alignment, one-candidate status and truth-use flags are in `audit.json`.

## POST-HOC DEVELOPMENT LIMITATION
This combination was constructed from held-out OOF predictions after the C0/C1 POC. It is development evidence only, not independent confirmatory validation and does not grant production admission.

## ARTIFACTS / HASHES / COMMIT / PUSH
The result, alignment, fallback masks, per-geometry/per-wavelength/per-order tables, H2 reconstruction, P_scale diagnostics, audit and continuation are hash-indexed by `artifact_hashes.json`. Commit and push state are recorded in the continuation after the exact allowlist commit.

## NEXT — DO NOT EXECUTE
The saved predictions support the power-side value of the C1 amplitude branch, but the HYBRID does not improve full state versus C0/FULL and still misses independent state and P_scale gates. A next proposal for review is a frozen objective that targets full complex-state performance while tracking amplitude and circular-phase losses separately, with seed-mean reconstruction included in the objective; retain the same independent P_scale branch. Any candidate would need prospective held-out geometry confirmation with predictions frozen before truth is revealed. This OOF hybrid is not confirmatory; no next experiment was run.
