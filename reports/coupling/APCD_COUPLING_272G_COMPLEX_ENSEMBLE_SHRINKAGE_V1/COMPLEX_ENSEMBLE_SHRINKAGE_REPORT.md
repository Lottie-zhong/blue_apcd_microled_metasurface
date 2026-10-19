# Complex ensemble shrinkage — 272G

## Scientific verdict
Cross-tree cancellation is a demonstrated major cause of norm shrinkage in this saved Leaf1 forest, across all four legal folds and three seeds. It is not proof that phase averaging alone is the cause of all prediction error. Tree modal-distribution disagreement and insufficient conditional information remain.

12 fold/seed checks, 124 primary heldout geometries (32/31/30/31), 128 trees per forest; Cartesian forest/mean-tree norm ratio range 0.457128–0.483671. See TREE_DIAGNOSTIC.json for every fold/seed, Re/Im tree variance and amplitude-weighted circular resultants. These are evaluation-fold findings, not six-dimensional space-wide certification.

## Frozen method and comparison
609D truth remains 588 Cartesian components plus21 natural-log P_scale. Per-lambda29D is28 Cartesian+lnP. Same native phase gauge, POSTNP1722nm, orders -3…+3, TE/TM, same frozen H2. No field/label/reference-plane modification, no independent order rotations, no mechanical state normalization.

A reuses all384 saved Leaf1 trees per fold and exactly reproduces predecessor NRMSE and P+MAE (<1e-12). B uses arithmetic mean modal magnitude and amplitude-weighted circular phase: arg(sum C). Thus B retains A phase and changes amplitude without oracle alignment. Dark exact-zero circular resultant yields magnitude times angle(0)=0 phase convention; it must not be interpreted as phase certainty. Low concentration is reported. C averages frozen-H2 per-tree Routing at fixed A P_scale; no unique complex state, hence complex/phase metrics N/A. C is an application comparator, never a replacement609D model.

No valid cached29D neural-network checkpoint was identified in the inspected predecessor inventories. D is an explicitly new lightweight CPU-only7→64→64→29 tanh model, two fixed seeds17/29, four original family-purged folds,300epochs, no tuning. Train-only X/Y standardization; ordered geometry and wavelength preserved. Eight fits, zero forest refits, zero CVAE fits.

|Model|Complex NRMSE|TM amplitude MAE|TM variance/truth|Routing MAE|Relative phase °|P_scale MAE|eta+ MAE|P+ MAE|450nm rho|Top20 recall|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_ReIm|0.754712|0.223137|0.141785|0.115907|49.219550|0.053121|0.089674|0.028486|0.499227|0.482143|
|B_MagnitudeCircular|0.765881|0.137856|0.058110|0.091368|49.219550|0.053121|0.097059|0.030871|0.190539|0.410714|
|C_PowerOnly|N/A|N/A|N/A|0.091501|N/A|0.053121|0.097713|0.031108|0.190540|0.410714|
|D_NN29|0.574201|0.122936|0.667493|0.068135|42.694430|0.061272|0.067663|0.021560|0.679698|0.660714|

TM variance ratio uses pooled124 geometry variance at fixed wavelength/mode. NRMSE pools SSE/true energy; MAE geometry-weighted; rho and Top20 average four folds. Top20 uses ceil(0.2*n) per fold and predecessor argsort convention. Non-comparable direct42D regressors were not substituted.

## Stability
{
  "B_MagnitudeCircular": {
    "Pplus_MAE_delta_vs_A": 0.0023846101456544066,
    "family_cluster_percentile95": [
      -0.0004444478857997937,
      0.005054601909940695
    ],
    "folds_improved": 1
  },
  "C_PowerOnly": {
    "Pplus_MAE_delta_vs_A": 0.0026223935102141953,
    "family_cluster_percentile95": [
      -0.00023500137320136503,
      0.005412434210120534
    ],
    "folds_improved": 1
  },
  "D_NN29": {
    "Pplus_MAE_delta_vs_A": -0.0069255395472849635,
    "family_cluster_percentile95": [
      -0.010630985271366557,
      -0.00337122704906373
    ],
    "folds_improved": 4
  }
}
Paired bootstrap resamples connected local families/singletons (2000 replicates), conditional on existing OOF fits; no tree/wavelength pseudoreplication. Four folds and two/three seeds remain small. Acquisition was adaptive to predecessor data; this is development OOF, not a pristine external or sealed test. Point gains alone do not establish reliable unknown-K6 generalization.

## H1
{
  "A_ReIm": {
    "gates": {
      "state": false,
      "routing": false,
      "absolute_order": false,
      "thresholded_absolute_order": false,
      "total_power": false,
      "seed_stability": true
    },
    "production_admission": false,
    "seed_stability_status": "PASS"
  },
  "B_MagnitudeCircular": {
    "gates": {
      "state": false,
      "routing": false,
      "absolute_order": true,
      "thresholded_absolute_order": false,
      "total_power": false,
      "seed_stability": true
    },
    "production_admission": false,
    "seed_stability_status": "PASS"
  },
  "D_NN29": {
    "gates": {
      "state": false,
      "routing": false,
      "absolute_order": true,
      "thresholded_absolute_order": false,
      "total_power": false,
      "seed_stability": true
    },
    "production_admission": false,
    "seed_stability_status": "PASS"
  }
}
Frozen H1 is not relaxed. Power-onlyC cannot qualify609D. B's production ensemble pools all trees; H1 seed stability uses each forest's same aggregation separately. No inverse-production readiness is claimed.

## Evidence and boundaries
COMPLEX_AGGREGATION_ABLATION.csv, FOLD_METRICS.csv, TM_ORDER_DIAGNOSTIC.csv, TREE_DIAGNOSTIC.json, PAIRed family stability JSON, saved per-fold predictions and tree caches; source WORKER.py and FIT_LEDGER.json. FAST272, NEW_FDTD0, NEXT_BATCH_AUTHORIZED0, DIAG2=1/2,A2HOLD,DOE56HOLD. Runner/native/sealed untouched; canonical117 solver entries unchanged; original four staged files unchanged. No commit/push.

## Final comparative decision

Magnitude/circular aggregation B reduces TM amplitude MAE by38.2% and all-order Routing MAE by21.2%, but P+MAE worsens8.37%, rho falls0.499→0.191 and TM geometry variance falls14.18%→5.81% of truth. Only1/4folds improves P+. Power-onlyC shows the same limitation. Neither is promoted. Restoring average amplitude does not recover geometry-dependent modal allocation. Re/Im averaging is a main norm-loss mechanism, not a sufficient explanation or cure of target-power error.

New fixed29D NN is the most consistent tested improvement: stateNRMSE0.75471→0.57420 (23.9% lower), TM amplitudeMAE0.22314→0.12294 (44.9% lower), RoutingMAE0.11591→0.06814 (41.2% lower), P+MAE0.028486→0.021560 (24.3% lower), rho0.499→0.680 and Top20recall0.482→0.661. All4folds improve P+; paired family bootstrap P+delta95%[-0.01063,-0.00337], conditional on fixed fits. Relative phase49.22°→42.69°. TM variance recovery14.18%→66.75% is substantial but incomplete. PscaleMAE worsens0.05312→0.06127 (15.3% higher). Therefore this is a multi-metric development improvement with an explicit total-power weakness, not full scientific qualification. Mean baseline predecessor P+MAE0.04338 and KRR0.03897 are exceeded on pooled development metrics; stronger power-outputMean and truly external validation remain separate evidence.

FrozenH1 remains HOLD: NN state, Routing, thresholded absolute-order and total-power gates FAIL; absolute-order and seed-stability gates PASS. No reliable inverse optimization or full unknown-space certification. Capacity/representation matters in addition to geometry coverage; this small controlled probe does not establish the optimal model or guarantee more-data benefit.

MODAL_DISTRIBUTIONS.json records per-order tree/forest/truth amplitude quantiles, Re/Im variances and circular resultant distributions across all folds. SEED_METRICS.csv records individual seed performance; no best-seed selection. Broad low resultants represent phase/distribution ambiguity. No independent phase alignment is applied.
