# Forward-model scientific decision

## Decision

The K6 cyclic transform is supported by the frozen periodic geometry, production Fourier convention, and H2 invariance tests. On the fixed 124-geometry development folds, six-cycle training augmentation improved the 29D NN3 baseline, and six-view inference further improved the augmented model. The best development candidate is **D: train-only cyclic augmentation plus six-view inference ensemble**.

| Measure (four-fold × three-seed mean) | A original | D augmented + ensemble | Change |
|---|---:|---:|---:|
| 609D complex NRMSE | 0.5998 | 0.4439 | lower is better |
| TM magnitude MAE | 0.1255 | 0.0928 | lower is better |
| routing MAE | 0.0724 | 0.0533 | lower is better |
| P_scale MAE | 0.0654 | 0.0507 | lower is better |
| η(+1) MAE | 0.0736 | 0.0547 | lower is better |
| P(+1) MAE | 0.0234 | 0.0184 | lower is better |
| 450 nm Spearman | 0.6628 | 0.8102 | higher is better |
| Top20 recall | 0.6270 | 0.7619 | higher is better |

## Limits and recommendation

- H1 remains **HOLD**. All four variants fail at least routing, thresholded order, and total-power frozen gates; no candidate has production admission.
- The 124 validation geometries are repeatedly used development cases. This experiment cannot certify unknown-K6 final generalization or authorize production inverse design.
- Fixed 300-epoch fits reached the iteration ceiling and emitted convergence warnings; improvements are conditional on this budget and are not evidence of an optimized NN architecture.
- The 272G dataset remains unchanged; symmetry views are synthetic training examples, not new physical truth. No independent FDTD label pair exists for rotated twins.
- Six-view inference uses six model passes; whether that runtime is acceptable for future acquisition needs a separate deployment measurement.

Recommended next development step: keep D as a candidate under the same grouped folds, preserve the four-way ablation, and seek an independent confirmation set through the existing authorization process. Do not change H1 thresholds, access sealed data, launch a new batch, or declare final model readiness from this development result.

Boundary: `NEW_FDTD=0`, `NEXT_BATCH_AUTHORIZED=0`, `DIAG2=1/2`, `A2=HOLD`, `DOE56=HOLD`, `CVAE=PAUSED`.
