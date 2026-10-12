# Complex-state learnability audit

## Evidence scope

The descriptive statistics below were computed from the frozen 156G labels and saved H2 state without fitting a model. They characterize this dataset and its representation; they do not prove general physical laws or predict performance on a new split.

## State scale and variation

- Norm of C_hat per geometry: median 4.87125; 5th/95th percentiles 4.70350/5.12564.
- P_scale over geometry-wavelength values: median 0.259157; 5th/95th percentiles 0.076965/0.707020.
- Individual coefficient magnitude over 45,864 values: median 0.002721; 5th percentile 1.922e-6; 95th percentile 0.617094.
- Median across-channel amplitude coefficient of variation across geometries: 0.55884; 95th percentile 1.15071.
- Energy-weighted circular phase variance across the 294 wavelength/order/polarization cells: median 0.83449; 95th percentile 0.95596.

These ranges indicate strongly heterogeneous coefficient scales, with many small-magnitude values. A single unweighted phase loss is likely to overemphasize phase where amplitude is negligible; any phase metric needs a frozen amplitude/energy threshold and must report threshold sensitivity.

## Routing and modal distribution

The H2 mean routing shares for m=-3 through +3 are approximately:

| m | -3 | -2 | -1 | 0 | +1 | +2 | +3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mean eta | 0.07592 | 0.11756 | 0.15884 | 0.32630 | 0.13665 | 0.11379 | 0.07094 |

For this +z TM-input dataset, the aggregate TE/TM energy shares were about 9.35e-10 and 0.9999999991. This describes the saved labels under the current decoder; it is not a universal polarization-selection result.

The three role strata differ descriptively and have unequal sample sizes: global n=113, old32 n=32, local-axis n=11. Median P_scale was 0.2620, 0.2693 and 0.1719, respectively. Mean eta at m=-1 was 0.1573, 0.1114 and 0.3126; at m=0 it was 0.3017, 0.4792 and 0.1342. These are not matched comparisons and do not establish a causal role effect.

## Historical H1 evidence

Both historical geometry-only models fail the frozen conjunctive H1 gate. For the 124G evaluation:

| Metric | RBF KRR | Cartesian MLP | H1 limit |
|---|---:|---:|---:|
| State error median / q95 | 0.872970 / 1.086444 | 0.923843 / 1.109628 | <= 0.5 / 0.8 |
| Routing error median / q95 | 0.182086 / 0.297147 | 0.274689 / 0.373825 | <= 0.05 / 0.10 |
| Routing correlation | 0.470601 | 0.416899 | >= 0.95 |
| Absolute-order error median / q95 | 0.064621 / 0.115201 | 0.096554 / 0.142925 | <= 0.05 / 0.10 |
| Thresholded relative error median / q95 | 0.801501 / 0.937560 | 0.911368 / 0.972487 | <= 0.30 / 0.75 |
| Total-power relative error median / q95 | 0.248064 / 0.757838 | 0.245158 / 0.778914 | <= 0.15 / 0.30 |
| Power correlation | 0.904588 | 0.931426 | >= 0.95 |
| Norm ratio median | 0.507299 | 0.448574 | diagnostic |

MLP seed standard deviation was 0.003603 against a <=0.03 seed gate; passing this one stability check does not rescue the conjunctive failures. Existing phase diagnostics report truth-weighted significant absolute/relative phase RMSE medians of 1.220526/1.721010 rad for KRR and 1.535195/1.819352 rad for MLP. Error energy is distributed across orders, with the reported m=0 relative RMSE 2.959/3.088 and larger TM error.

P_scale and decoded total_power are identical by decoder definition. Their paired values are not independent confirmations.

## Learnability conclusion

A direct complex-state target is numerically representable but difficult for the current 156 geometry sample because coefficient scales and phase relevance vary sharply across channels. The strongest defensible next step is to obtain a validated, convention-matched physics baseline and test whether it reduces held-out geometry error. These diagnostics do not establish that the physics-guided model will pass H1.

## Local response and sample sufficiency

The available role summary has only 11 local-axis groups. The role-wise distributions above are descriptive and are not a matched finite-difference sensitivity study around common geometry anchors. Local response sensitivity and whether 156 groups are sufficient for a small shared residual network are UNRESOLVED.

No aggregate historical predictor passes H1, so no output can be called easy at the frozen H1 acceptance level. The TM-dominated energy share and routing distribution describe the labels, not predictive learnability.

## Temporal-convergence boundary

Historical numerical comparisons stopped at 3 ps without reaching the 1e-6 auto-shutoff. A 6 ps setup passed LOAD-only readback but was not run. This leaves a temporal-convergence confound. It does not prove that time truncation caused either model failure. The 5 nm/4 nm diagnostic cases are not training data.
