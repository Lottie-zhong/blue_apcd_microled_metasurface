# TM Routing and circular phase

Single X/P_XLIKE incidence only; full Jones/polarization selectivity is not evaluated. Seven orders TE/TM retained. Circular absolute angular errors and training-fold-only dominant-channel relative references are used. Primary relative-phase weights |C_true|² preserve predecessor convention; true amplitude <0.001 of per-case/lambda maximum is excluded, plus reference/near-zero predicted safeguards. Weak TE phase is not assigned meaningful large weight. This weighting is not cos(theta) modal flux; Routing itself uses exact frozen H2 flux weights.

B keeps A circular phase, so identical phase errors cannot demonstrate phase learning improvement. Tree resultant |mean C|/mean|C| describes cancellation/concentration, not phase accuracy. TM_ORDER_DIAGNOSTIC.csv exposes order-dependent attenuation and magnitude/Routing error for all folds; tree Re/Im variances are descriptive across trees, not confidence intervals.

H2 power depends on modal squared magnitudes and P_scale, with no cross-order phase interference in this decoder. Improved complex magnitude may improve Routing, but phase fidelity cannot be inferred from target power. Power ensemble C averages H2 outputs and has no validated609D phase state. Nonadditivity/cancellation does not uniquely prove a near-field mechanism.

|Model|Complex NRMSE|TM amplitude MAE|TM variance/truth|Routing MAE|Relative phase °|P_scale MAE|eta+ MAE|P+ MAE|450nm rho|Top20 recall|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_ReIm|0.754712|0.223137|0.141785|0.115907|49.219550|0.053121|0.089674|0.028486|0.499227|0.482143|
|B_MagnitudeCircular|0.765881|0.137856|0.058110|0.091368|49.219550|0.053121|0.097059|0.030871|0.190539|0.410714|
|C_PowerOnly|N/A|N/A|N/A|0.091501|N/A|0.053121|0.097713|0.031108|0.190540|0.410714|
|D_NN29|0.574201|0.122936|0.667493|0.068135|42.694430|0.061272|0.067663|0.021560|0.679698|0.660714|

## Final comparative decision

Magnitude/circular aggregation B reduces TM amplitude MAE by38.2% and all-order Routing MAE by21.2%, but P+MAE worsens8.37%, rho falls0.499→0.191 and TM geometry variance falls14.18%→5.81% of truth. Only1/4folds improves P+. Power-onlyC shows the same limitation. Neither is promoted. Restoring average amplitude does not recover geometry-dependent modal allocation. Re/Im averaging is a main norm-loss mechanism, not a sufficient explanation or cure of target-power error.

New fixed29D NN is the most consistent tested improvement: stateNRMSE0.75471→0.57420 (23.9% lower), TM amplitudeMAE0.22314→0.12294 (44.9% lower), RoutingMAE0.11591→0.06814 (41.2% lower), P+MAE0.028486→0.021560 (24.3% lower), rho0.499→0.680 and Top20recall0.482→0.661. All4folds improve P+; paired family bootstrap P+delta95%[-0.01063,-0.00337], conditional on fixed fits. Relative phase49.22°→42.69°. TM variance recovery14.18%→66.75% is substantial but incomplete. PscaleMAE worsens0.05312→0.06127 (15.3% higher). Therefore this is a multi-metric development improvement with an explicit total-power weakness, not full scientific qualification. Mean baseline predecessor P+MAE0.04338 and KRR0.03897 are exceeded on pooled development metrics; stronger power-outputMean and truly external validation remain separate evidence.

FrozenH1 remains HOLD: NN state, Routing, thresholded absolute-order and total-power gates FAIL; absolute-order and seed-stability gates PASS. No reliable inverse optimization or full unknown-space certification. Capacity/representation matters in addition to geometry coverage; this small controlled probe does not establish the optimal model or guarantee more-data benefit.

MODAL_DISTRIBUTIONS.json records per-order tree/forest/truth amplitude quantiles, Re/Im variances and circular resultant distributions across all folds. SEED_METRICS.csv records individual seed performance; no best-seed selection. Broad low resultants represent phase/distribution ambiguity. No independent phase alignment is applied.
