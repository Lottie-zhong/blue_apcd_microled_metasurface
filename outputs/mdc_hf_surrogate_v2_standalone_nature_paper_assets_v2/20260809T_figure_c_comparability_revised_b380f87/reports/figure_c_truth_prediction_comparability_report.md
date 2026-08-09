# Figure C truth/prediction comparability audit

## Decision

- Status: **PASS**
- Classification: `NORMALIZATION_MISMATCH`, `COLOR_LIMIT_MISMATCH`, `DISPLAY_ONLY_ISSUE`
- Replot strategy: `COMPARABLE_AFTER_DISPLAY_FIX`
- Frozen selection changed: **no**
- Frozen Test40 metrics recomputed or changed: **no**

## C1 — representative geometries

The revised figure must reuse the three rows in the frozen selection CSV exactly: best rank 1, median rank 21, and worst rank 40 (the CSV is authoritative). Geometry hashes and joint-JS values are preserved byte-for-byte.

## C2/C3 — source and aggregation

Truth uses each selected geometry's frozen `normalized_joint` profile. Prediction uses the frozen Test40 profile array and the six case rows for each selected geometry, averaged at geometry level. Source paths, source SHA values, case-index SHA, and selected profile rows are recorded in the JSON audit. This was a read-only comparability audit; no Test40 metric was recomputed.

## C4 — physical and grid comparability

All selected truth and prediction arrays are 301×2000 on the same 420–480 nm wavelength axis and −90–90° angle axis. Aggregation level is geometry-level for both. Their stored amplitudes are not on the same normalization convention: the frozen truth `normalized_joint` and prediction profile have different sums/peak scales. Therefore the stored arrays are not directly pointwise-comparable in amplitude.

For the revised display only, both arrays will be transformed to unit peak on the same grid; the error panel will be `abs(truth_display - prediction_display)` in that shared display space. This does not alter source arrays, frozen metrics, or scientific scope.

## C5/C6 — v1 issue

The v1 plotting code normalized prediction by its maximum but did not apply the same transform to truth, used per-panel limits that coupled error to truth/prediction limits, and created one colorbar per panel. The resulting truth panels appeared nearly black. This is a normalization/color-limit/display issue, not a source, aggregation, or grid mismatch.

## C7 — permission to replot

`COMPARABLE_AFTER_DISPLAY_FIX` permits revised Figure C. The revised figure must preserve best/median/worst selection, use a common truth/prediction color scale per row, use an independent error scale, and leave all frozen numerical results unchanged.
