# COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1

Status: COMPLETE one-fold, seed-0 development audit. No held-out truth state, prediction, or metric was opened; this is not full LOGO validation or H1 admission.

## Execution and authority

- Start HEAD: bdc540baa0b0455b4c13b4a3f3471b2af86e8b7e; branch: work/mdc-np-coupling-ml-v1; base protocol SHA-256: 0ba6590ec408b3188f59e329dcb08ebeebb428736f3a022844c1ea97c360c1bb; amendment SHA-256: 72f1eeeebcf9a2965983a1879450781aa4ee8951536adcc4052ff07a0fce6e15; runner SHA-256: fcaeb39f9b8d4a769c40c2af237cdbfa9fedab11a2d2975666252f6edb2d907a.
- Exact budget: 8 fits x 1,000 AdamW updates = 8000; each fit ran once and saved optimizer step 1,000.
- ZERO solver, HF, reserve, inverse search, GPU Runner, or P_scale fitting. Routing/H2 is unavailable because no lawful nested P_scale prediction exists for inner validation.
- First official outer fold, seed 0: 31 outer-train geometries; inner validation groups 11/10/10 with all 21 wavelengths together. Each scaler and seven rank-2 order-local PCA bases were fit inside the corresponding train split only.
- Training-label provenance: 19 Frozen_20G states came from the formal worktree and 12 STAGE1_12G state files from authority-listed runtime paths. All 31 state hashes matched the formal dataset authority; sidecar-embedded hashes matched the state files. The authority omits sidecar-file SHA-256 for those 12 external cases; observed sidecar hashes are frozen in input_manifest.json. S35 used the separately documented LOAD-only post-entry recovery state; recovery evidence records no solver invocation or replay during recovery.
- Leakage disclosure: before preregistration, authority metadata inspection printed held-out S02 ordered-diameter metadata. No S02 truth state, prediction, or metric was opened; S02 geometry values were not used by training, preprocessing, checkpointing, or comparisons. This is a protocol-boundary deviation and limits blind interpretation.

## Models and optimization

- C0 is frozen M5 Cartesian ordered geometry, 2,684 trainable parameters; G0 is frozen width-4, three-round directed periodic ring, 2,444 parameters. Both use the same 14-D Cartesian order-local rank-2 PCA target/inverse, loss, full-batch AdamW (lr 0.002, weight decay 0.0001), gradient clip 5, seed 0, and 1,000-step fixed trajectory.
- Replayed original rule on inner validation: strict minimum standardized latent loss, maximum 320, patience 45. Continue to 1,000 only for this audit. Each outer refit epoch is that model own median of three inner-selected epochs; both medians equal 18.

## 31-geometry train fit vs constant baselines

| Model | zero baseline loss | train-mean loss | loss at step 18 | loss at step 1,000 | train state median at 1,000 | PCA train-floor state median |
|---|---:|---:|---:|---:|---:|---:|
| C0 | 1 | 1 | 0.920301 | 1.20397e-06 | 0.3199 | 0.3199 |
| G0 | 1 | 1 | 0.999789 | 9.09824e-05 | 0.3201 | 0.3199 |

Both models fit the 31G latent targets far below the approximately 1.0 constant baselines. At 1,000 steps, C0 and G0 losses are near zero; the remaining approximately 0.32 train state relative-L2 median is close to the rank-2 PCA train projection floor. At step 18 the train losses are 0.9203 and 0.9998, so the inner-median refit epoch is not a full train fit.

## Inner trajectories and early-stop replay

Best is the original validation-loss checkpoint. Post-stop minima are diagnostic only.

| Fold | Model | best step / val loss | replay stop | post-stop min step / loss | best state / amplitude / phase | val loss at 1,000 | state / amplitude / phase at 1,000 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | C0 | 18 / 0.8187 | 63 (patience_45) | 64 / 1.2506 | 0.7339/0.5544/1.0483 | 2.1002 | 1.2148/0.7157/1.2521 |
| 1 | G0 | 15 / 0.8085 | 60 (patience_45) | 61 / 0.8445 | 0.7055/0.5706/1.0157 | 2.0473 | 1.1240/0.5776/1.1604 |
| 2 | C0 | 18 / 1.5061 | 63 (patience_45) | 64 / 1.9007 | 0.8497/0.7206/1.4508 | 2.1549 | 1.0370/0.5932/1.5420 |
| 2 | G0 | 18 / 1.4689 | 63 (patience_45) | 64 / 1.6730 | 0.8343/0.7251/1.3773 | 3.0640 | 1.3451/0.5719/1.9375 |
| 3 | C0 | 22 / 1.2052 | 67 (patience_45) | 68 / 1.7100 | 0.8568/0.6328/1.4355 | 1.9220 | 1.1223/0.4985/1.4253 |
| 3 | G0 | 29 / 1.1788 | 74 (patience_45) | 75 / 1.2504 | 0.8474/0.6732/1.4128 | 2.3763 | 1.1527/0.5730/1.4632 |

All six inner fits reached their validation-loss minimum at steps 15-29 and replayed stop at steps 60-74. No post-stop minimum through step 1,000 beat its selected checkpoint. Training loss continued toward zero while validation loss rose and did not recover; this supports overfitting/generalization limitation, not useful late recovery missed by early stopping.

## PCA floors and C0 vs G0

| Fold | validation geometries | PCA state median / q95 / worst | amplitude median | truth-weighted phase RMSE median (rad) | G0-C0 state delta at 1,000 |
|---:|---:|---:|---:|---:|---:|
| 1 | 11 | 0.3744 / 0.4737 / 0.5098 | 0.2445 | 0.3023 | -0.0908 |
| 2 | 10 | 0.3757 / 0.4925 / 0.4961 | 0.2518 | 0.3160 | +0.3081 |
| 3 | 10 | 0.3682 / 0.5285 / 0.5608 | 0.2437 | 0.3035 | +0.0304 |

- G0 wins the step-1,000 inner-validation state median on 1/3 folds; deltas (G0-C0): -0.0908, +0.3081, +0.0304. The direction is mixed.
- Amplitude and fixed truth-amplitude-weighted phase changes also vary across folds. Every fixed milestone has per-geometry amplitude/phase/state metrics in fit_summary.json; every update, gradient norm and parameter update norm is in trajectory.csv.
- PCA validation state floors have median about 0.37, while step-1,000 validation state medians are 1.04-1.35. Compression contributes but does not explain most validation error.

## Leakage, checks and limits

- Split audit passed: each inner train/validation pair is disjoint and partitions the 31 outer-training IDs; the three validation groups cover those 31 IDs exactly once. Every trajectory has 1,001 rows for steps 0-1,000 and all preregistered milestones. All eight AdamW states end at step 1,000, all fits ran once, and all parameter tensors received gradients.
- Preflight passed: output [3,14], finite outputs, full gradient paths, 31 permitted train-state files and four split-local preprocessing objects. Frozen C_hat extraction was POSTNP +z m=-3..3 TE/TM with authority normalization.
- No lawful nested P_scale was available, so routing/H2 and P_scale gates were not evaluated. No held-out prediction is made; no H1 conclusion can be drawn.

## Conclusion and next review

The original early stop is not shown to truncate later validation recovery in this one outer fold. Both models fit training latent targets well by 1,000 steps, but validation shows a strong train-validation gap. G0 has mixed validation behavior versus C0 and no consistent graph benefit is established. Next review should examine train/validation geometry coverage and representation/generalization under current labels before proposing one preregistered protocol rerun. Do not run full LOGO or add HF from this result.

Recovery: read CONTINUATION.md first, then protocol_amendment_01.json, protocol.json, fit_registry.json, current_progress.json and this report.
