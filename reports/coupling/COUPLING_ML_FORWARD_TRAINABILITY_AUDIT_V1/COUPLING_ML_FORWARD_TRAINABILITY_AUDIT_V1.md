# COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1

## STATUS
COMPLETE; train-only development audit; no held-out generalization or production admission claim.

## AUTHORITY / GIT
Remote DESKTOP-NNE313K / dell; worktree D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; canonical root D:/project/blue_apcd_microled_metasurface.
Branch work/mdc-np-coupling-ml-v1; start HEAD f0f47023af9c306590414232155c0d539c3dfa4d; start ahead/behind 0/0. Expected HEAD verified.
All 332 unrelated pre-existing worktree entries retain the same status hash. Frozen source and authority SHA-256 inputs are in protocol.json. No AGENTS.md was present in the formal worktree or canonical root; the user-provided project instructions governed this run.

## ZERO-SOLVER / EXACT FIT COUNT
ZERO solver, FDTD, GPU Runner, new HF, reserve, inverse search, P_scale fit, platform work, and full LOGO rerun. Exactly two fit IDs were started once: T0 and T1, 1,500 optimizer updates each and 3,000 total. CPU-only RCP_LCP runtime.

## CONSTANT-BASELINE VS SAVED G0
Frozen loss divides by per-coordinate population std and does not subtract the target mean. PCA scores are outer-train centered, so latent-zero and outer-train-mean baselines each score 1.000.
Across 96 saved G0 fold-seed checkpoints: train loss median 0.997874, q95 1.004165, worst 1.014990. Output/target latent variance-ratio median 0.000133, q95 0.00126. Median coordinate correlation 0.132. Median relative parameter L2 change 0.103.
G0 initial train-loss median 1.0374; saved final median 0.9979. It updated weights and reduced loss, yet remains near-constant across outer-train geometries.

## AVAILABLE C0 TRAINING AUDIT
96 saved C0 seed fits and 288 inner best-epoch records are available. C0 artifacts lack model tensors, final train losses, inner executed epochs, validation-loss values, and train curves. Known outer-refit updates sum to 1100. No C0 LOGO fit was repeated.

## EARLY-STOP / REFIT-STEP DISTRIBUTION
C0 outer-refit selected epochs min/median/q95/max: 1.00/12.00/20.25/24.00. G0: 4.00/17.00/40.25/52.00. G0 inner best median 16.0; inner executed median 61.0. Inner plus outer updates reconcile to 20,786.

## GRADIENT / UPDATE / CHECKPOINT AUDIT
Both fit paths pass every parameter to AdamW, backpropagate through the model, clip at 5, and evaluate validation only in eval/no-grad mode. Four-case fits connected all parameters, used all 1,500 optimizer steps per parameter, and triggered no clipping. Final and minimum-loss checkpoint/NPZ reloads passed parity. See reconstruction_and_training_audit.json.

## 4G C0 / G0 TRAINABILITY CURVES
| Fit | Step | Loss | Raw latent MSE | State median | State q95 | Variance ratio median | Corr median | Gradient norm | Update norm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| T0 | 0 | 1.468 | 0.4719 | 0.6186 | 0.7279 | 0.01467 | 0.3169 | 2.07 | - |
| T0 | 10 | 0.8094 | 0.309 | 0.5374 | 0.6558 | 0.03627 | 0.8778 | 1.09 | 0.0707 |
| T0 | 50 | 0.01127 | 0.004433 | 0.3282 | 0.4653 | 1.004 | 0.9989 | 0.207 | 0.0361 |
| T0 | 100 | 6.631e-05 | 2.262e-05 | 0.3241 | 0.4628 | 1.001 | 1 | 0.0159 | 0.00238 |
| T0 | 300 | 5.977e-13 | 2.734e-13 | 0.3241 | 0.4628 | 1 | 1 | 1.87e-06 | 1.29e-06 |
| T0 | 750 | 1.892e-13 | 9.14e-14 | 0.3241 | 0.4628 | 1 | 1 | 1.04e-06 | 1.28e-06 |
| T0 | 1500 | 8.998e-14 | 3.449e-14 | 0.3241 | 0.4628 | 1 | 1 | 8.48e-07 | 1.29e-06 |
| T1 | 0 | 1.431 | 0.4962 | 0.6134 | 0.8092 | 4.003e-05 | 0.1842 | 1.28 | - |
| T1 | 10 | 1.158 | 0.4192 | 0.5833 | 0.7589 | 4.759e-05 | 0.05376 | 0.816 | 0.0487 |
| T1 | 50 | 0.9525 | 0.3498 | 0.5734 | 0.659 | 0.002296 | 0.551 | 0.198 | 0.0289 |
| T1 | 100 | 0.0568 | 0.02367 | 0.3418 | 0.4878 | 1.004 | 0.9926 | 0.293 | 0.0772 |
| T1 | 300 | 3.392e-11 | 1.529e-11 | 0.3241 | 0.4628 | 1 | 1 | 7.31e-06 | 3.71e-06 |
| T1 | 750 | 2.595e-13 | 9.216e-14 | 0.3241 | 0.4628 | 1 | 1 | 2.19e-06 | 1.52e-06 |
| T1 | 1500 | 3.592e-13 | 9.9e-14 | 0.3241 | 0.4628 | 1 | 1 | 4.31e-06 | 1.54e-06 |

T0 has 2,684 parameters; initial/final loss 1.468/9e-14; minimum at step 1434. T1 has 2,444 parameters; initial/final loss 1.431/3.59e-13; minimum at step 1234.

## PCA RECONSTRUCTION FLOOR
Fold 0 held out K6V1_S02; its truth was not used. The four lexicographically selected outer-train cases were K6V1_EXT01, K6V1_EXT02, K6V1_EXT03, K6V1_EXT04. Each case carries the full 21-wavelength spectrum. The reconstructed outer-train rank-2 PCA basis matched saved explained-variance ratios with max delta 0.
Four-case zero/mean constant losses: 1.5675 / 1.0000. Oracle rank-2 floor state median/q95/worst: 0.3241/0.4628/0.4849, complex RMSE 0.1013. T0 and T1 reach near-zero latent error and this nonzero PCA floor by step 300.

## BUGS / AFFECTED HISTORICAL RESULTS
Three diagnostic-harness issues were repaired before their fit ID took any optimizer step; T0 and T1 each started once and completed 1,500 updates. No project training source, labels, frozen authority, or historical result changed. The G0 outer-step reconciliation field was corrected to compare against the persisted total update count.

## CONCLUSION / LIMITATIONS
G0 saved predictions are close to constant under the true loss, output-variance, and correlation checks. Training code is correctly wired, and both architectures fit the four selected samples to the rank-2 floor. The saved G0 protocol selected short refits and did not fit its 31-geometry training sets. Review and preregister the early-stop/refit budget and train/validation trajectories before changing representation or claiming data insufficiency. Whether more training improves held-out performance remains untested. The tiny train-only fits do not establish generalization, physical correctness, H1 admission, or a need for new samples.

## ARTIFACTS / HASHES / COMMIT / PUSH
Protocol, source checks, baseline comparisons, curves, fit/resume/final/minimum checkpoints, PCA floor, implementation fix log, and continuation are in this directory. Hash inventory is artifact_hashes.json. Exact-allowlist commit and normal push are pending.

## NEXT - DO NOT EXECUTE
Chat review: choose whether to preregister a training-protocol validation trajectory before any representation or data-coverage experiment. No follow-on fit or sample expansion was run or authorized.
