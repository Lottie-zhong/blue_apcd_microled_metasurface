# COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1

STATUS: COMPLETE_ZERO_SOLVER_DIAGNOSTIC; scientific review boundary.

## AUTHORITY / GIT
Initial HEAD 9dce0048ff6577f7290a9aa8d9b936ba7b38a63d; branch work/mdc-np-coupling-ml-v1. Original authority/prediction manifests and state NPZ hashes checked. Source paths and hashes: protocol.json / audit.json. No foreign untracked files changed. Remote AGENTS.md absent at checked canonical/worktree locations; user-provided execution instructions applied.

## DATASET / SPLIT
32 ordered geometries; full 440-460 nm: 672 rows / 4704 order rows; NP paired 445-455 nm: 352 / 2464. POSTNP +z TE/TM complex coordinates, m=-3..3,y=0, P/XLIKE. Geometry LOGO, original seeds 0,1,2 and grouped inner splits. Full-band and paired-band model results are separate.

## ZERO-SOLVER ASSERTION
FDTD, GPU Runner, new HF, reserves, inverse search: 0. Existing archived predictions reused. No predictor training. Only CPU error decomposition, train-fold PCA oracle projections and tests. No production admission. S35 FAILED_POSTENTRY and independent LOAD-only recovery preserved. Historical 20G provenance limitation remains; no FSP forensic reopened.

## REPRESENTATION DEFINITIONS
Original C_PW preserved in incident gauge. C_hat = C_PW/sqrt(sum modal_weight*abs(C_PW)^2); model separately predicts P_scale. Physical prediction uses frozen TE/TM _mode power coefficients to normalize reconstructed C_hat to predicted P_scale. Raw physical error reported separately from original normalized H1 metric.
Diagnostic reversible polar: amplitude + phase for each of 14 complex coordinates. Diagnostic gauge: amplitude + common anchor phase + 14 relative phases + reference index, per wavelength. Anchor uses largest own amplitude, deterministic first tie; all-zero phase 0. Carry index when reference switches. exp(i phase) handles wrapping; no coordinate dropped. Largest-amplitude reference uses the represented object itself for reversible encoding only; no held-out truth reference used by a predictor. No candidate gauge predictor constructed. TE/TM remain separate; this single incident state is not a Jones matrix.

## AMPLITUDE VS PHASE
Full normalized complex SSE: amplitude 63.244%, phase 36.756%. Aggregate relative RMSE 0.836900; amplitude RMSE 0.665555; amplitude-squared-weighted circular phase RMSE 1.454251 rad. This aggregate differs from geometry median.
Exact identity: |pred-truth|^2 = (|pred|-|truth|)^2 + 2|pred||truth|(1-cos(delta phase)). Phase contribution depends on predicted amplitude; no unique causal partition implied.
Weak coordinates: 50.0106%; truth energy 7.37e-08; complex SSE 3.36e-06. Threshold frozen at 1% row maximum amplitude. No masking in complex/H1 metrics. TE truth energy fraction 8.14e-10; retain TE despite small contribution. Zero predicted-coordinate count is recorded per arm; phase at zero has no physical information.

## COMMON VS RELATIVE PHASE
ORACLE DIAGNOSTIC: best common phase per wavelength reduces full aggregate RMSE 0.836900 -> 0.782016, explaining 12.686% SSE. Separate per-order alignment over TE/TM reaches 0.665555; additional 24.070% SSE is removable by independent order phases. Common phase alone is insufficient. Neither alignment is H1/model performance.

## ORDER-LOCAL VS CROSS-ORDER
Outer-train fitted bases; held-out truth projection is ORACLE DIAGNOSTIC. Equal 14-real-latent budget: local rank2 x7 median/q95 0.363291/0.500738; joint rank14 0.451377/0.645050. This favors retaining order-local spectral bases at this budget; it does not compare learned local versus cross-order predictors. Archived M5 already has cross-order fusion. Per-order errors are in order_local_diagnostics.csv.

## TAIL ATTRIBUTION
K6V1_EXT08: state 1.032973; amplitude 0.840648; common-aligned ORACLE 0.964410; routing 0.328472; absolute 0.135187; P_scale 0.309830; worst state wavelength/order 450/-2. Ordered geometry, truth descriptors and wavelength/order decomposition: tail_attribution.json and geometry_wavelength_order.csv.
K6V1_S31: state 1.201533; amplitude 0.851480; common-aligned ORACLE 0.986643; routing 0.343753; absolute 0.129335; P_scale 0.718727; worst state wavelength/order 452/-1. Ordered geometry, truth descriptors and wavelength/order decomposition: tail_attribution.json and geometry_wavelength_order.csv.
K6V1_S33: state 1.268978; amplitude 0.716705; common-aligned ORACLE 0.847996; routing 0.263197; absolute 0.095540; P_scale 0.234901; worst state wavelength/order 459/0. Ordered geometry, truth descriptors and wavelength/order decomposition: tail_attribution.json and geometry_wavelength_order.csv.

## NP FEATURE ATTRIBUTION
Paired 445-455 nm only: amplitude wins 26/32, median paired delta -0.036330; weighted-phase wins 15/32, delta 0.023663 rad. Routing wins 20/32; P_scale 19/32; absolute-order 15/32. Benefit is strongest in amplitude, with modest routing/scale effects and no consistent phase improvement.
A1 aggregate state RMSE is slightly worse despite improved geometry median; retained to expose tails. A1 aggregate amplitude RMSE improves while its phase SSE share rises. Paired effects are descriptive attribution, not causality. Full-band NP predictions do not exist, so no full-band NP claim. Support distance remains diagnostic; correlations are in support_diagnostic.json. Provider remains auxiliary LF features, never truth/scattering/Jones/cascade.

## RECONSTRUCTION PARITY
Raw C_PW gauge max absolute error 4.88e-15; C_hat 3.51e-16; 56 reference switches. Original absolute 1e-12 label-parity check passed; wrapping/zero/switch tests passed.

## H2 PRESERVATION
Routing/order/total max differences 2.22e-16/1.39e-16/3.33e-16. Frozen mode-power physical reconstruction parity passed. Existing modal/grating routing difference 0.000341991 retained; reparameterization preserves original H2 output, not silently corrected truth.

## H1 COMPARISON UNDER ORIGINAL GATES
All archived original H1 metrics recomputed within 1e-12; original gates unchanged. FULL/A0/A1: FAIL/FAIL/FAIL. Seed gate passes; state, routing, absolute, thresholded absolute and P_scale gates fail. No oracle alignment/scale/latent projection included. No candidate representation predictor evaluated; no production admission. Full detailed gates and seed metrics: results.json.

## LEAKAGE AUDIT
Protocol saved before new diagnostic computation. Existing prediction provenance reused; fold partitions checked. New PCA bases fit on 31 outer train geometries only, then held-out truth projected solely for ORACLE DIAGNOSTIC. No full-data fitted basis entered predictions. Geometry physical ordering preserved. Support/OOD never input. audit.json / test_results.json.

## NEXT PROPOSAL — DO NOT EXECUTE
First review a finite amplitude-and-circular-phase target experiment retaining order-local spectra and explicit common/relative phase, with a train-only or predicted reference rule, predicted common phase and independent predicted P_scale. Existing evidence establishes reversible parity and diagnoses amplitude/relative-phase error; it does not prove a polar/gauge predictor will learn better, nor that reference switching will generalize. Compare under original folds/seeds/H2/H1 before considering HF.
No current evidence justifies broad sample expansion. Targeted supplementation is a hypothesis only: after representation review, consider small ordered-geometry neighborhoods around S31/S33/EXT08 that probe the observed worst-order amplitude/relative-phase and P_scale spectral regimes, with prediction-before-truth and a separate budget approval. No specific cases or solver runs are authorized here.

## ARTIFACT PATHS / HASHES
This directory: results.json, audit.json, protocol.json, checkpoint.json, continuation, per-geometry and geometry/wavelength/order CSVs, train-fold PCA oracle CSV, tail/support diagnostics, tests, software recovery. SHA256 mapping: artifact_hashes.json. Exact allowlist only; historical outputs/FSP/runtime excluded.

Original physical C_PW versus physically reconstructed predicted state (predicted P_scale): aggregate RMSE 0.916560; amplitude/phase SSE 52.653%/47.347%; amplitude-weighted phase RMSE 1.412173 rad. Common-phase ORACLE explains 16.783% and reaches RMSE 0.836116. Thus physical amplitude and phase are both substantial; normalized H1-state amplitude dominance must not be confused with the physical-state partition. The archived raw/modal versus monitor-power discrepancy remains explicit.

ORACLE DIAGNOSTIC orthogonal accounting of full state SSE: local-PCA truncation 20.003%; in-basis prediction error 79.997%; max orthogonality cross term 5.73e-14. The largest share is prediction of the retained coordinates rather than loss from rank2 local compression. This is error accounting, not proof that architecture or sampling alone caused it.

Raw C_PW order/total H2 preservation max abs: 2.22e-16/2.22e-16.
Recovery finalization script: scripts/coupling_ml/coupling_ml_32g_complex_state_representation_diagnostic_v1_finalize.py; run only after successful core results.
