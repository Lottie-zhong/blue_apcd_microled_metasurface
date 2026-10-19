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

## Direct answers to the requested scientific questions

1. **Does the K6 cyclic shift satisfy the frozen contract?** Yes for the ideal periodic geometry and saved-label transform: the six-center lattice, x/y periodicity, uniform full-cell stack layers, normal-incidence source, and 5 nm mesh support an exact +290 nm translation. This is algebra/code/H5-coordinate evidence; a rotated-geometry FDTD pair was not present.
2. **What is the complex phase sign?** With the actual extractor kernel `exp(-i G_m x)`, `T^k=roll(D,+k)` corresponds to `C_m(T^kD)=C_m(D) exp(-i 2πmk/6)`; both TE and TM use the same factor. Inference aligns with the conjugate positive phase before averaging.
3. **Are there cyclic duplicates in 272G?** No: 272 ordered geometries form 272 canonical cyclic orbits.
4. **Do the existing folds split cyclic-equivalent cases?** No observed orbit has multiple cases; exact case/family/cyclic train-validation overlaps are zero in all four folds. All wavelengths remain grouped by geometry.
5. **Does six-view augmentation improve 28D complex learning?** On the fixed development folds, B improves complex NRMSE over A in 12/12 fold-seed pairs; D also improves every reported loss metric over C in 12/12 pairs. This is repeat-development evidence, not independent generalization.
6. **Is phase-aligned six-view inference better than direct NN3?** C improves the mean H2/ranking metrics against A but does not beat B on mean complex, TM, routing, or phase errors. D is the best development candidate when combined with augmentation.
7. **Do P(+1), Spearman, and Top20 improve together?** Their fold/seed means all improve from A to D. Spearman improves in 12/12 A→B pairs and 9/12 C→D pairs; Top20 improves in only 4/12 pairs for either comparison. Top20 therefore does not show stable paired improvement.
8. **Which model should be retained?** Keep D as the best development candidate, not as a production-ready or H1-passing model. H1 remains HOLD.
9. **Is P_scale spectral low-rank learning necessary now?** Not established by this experiment. Cyclic augmentation improves overall P_scale MAE (0.06543→0.05066) and high-region MAE (0.1000→0.0658), but high-region signed bias stays negative and underprediction remains frequent. First do a zero-solver, train-fold-only common spectral-trend/residual diagnostic; do not add a low-rank model solely from this result.
10. **Is another 50G needed now, and what should it cover?** This study does not justify automatically starting another 50G. H1 is still HOLD and the 124 cases are reused development data. If a new batch is later authorized after independent confirmation planning, prioritize six-dimensional coverage in geometries associated with high-`P_scale` underprediction and the higher-error `m=0` response while retaining broad coverage; do not spend the batch on synthetic cyclic copies.

H1 remains a development gate, all confirmation data remain sealed, and this study used zero FDTD runs and zero new Solver Entries.
