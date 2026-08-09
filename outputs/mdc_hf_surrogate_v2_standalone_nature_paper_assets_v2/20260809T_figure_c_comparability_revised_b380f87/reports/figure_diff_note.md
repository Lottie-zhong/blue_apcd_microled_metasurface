# Figure revision diff note

## Global invariants

- All scientific values, frozen Test40 metrics, representative geometry hashes/ranks, model scope, and selection CSV rows are unchanged.
- No solver, training, optimizer, PCA/scaler refit, or Test40 metric recomputation was run.
- Revised exports use Python/matplotlib with editable SVG/PDF text and 600-dpi PNG previews.

## Figure A

Pure layout and semantic repair: the canvas is widened within a double-column-compatible width; the raw and unit-peak heatmaps have explicit separate colorbars; spectral and angular marginals are moved to vertically stacked panels with native wavelength/angle axes. No underlying values were changed, smoothed, or recomputed.

## Figure B

Pure layout repair: title/panel spacing, margins, horizontal category labels, numeric value labels, and the explicit PCA32 selection annotation were improved. Bar heights and all candidate values are unchanged.

## Figure C

The comparability audit identified a v1 `NORMALIZATION_MISMATCH` and `COLOR_LIMIT_MISMATCH` at the display layer: prediction was unit-peak normalized while truth remained on its stored `normalized_joint` amplitude scale, and error limits were coupled to truth/prediction limits. Source, aggregation, and grid levels match, so the audit decision is `COMPARABLE_AFTER_DISPLAY_FIX`.

The revised C preserves the frozen best/median/worst rows and geometry hashes, applies the same unit-peak display normalization to truth and prediction on the same 301×2000 wavelength-angle grid, uses one shared truth/prediction scale, and uses an independent absolute-error scale. The stored arrays and frozen metrics are untouched.

## Figure D

Pure layout/annotation repair: additional bottom margin prevents note/x-label collisions; the geometry-ranking panel now reports frozen Spearman `0.128330`; the error-distribution panel reports frozen case joint-JS mean `0.267155`; the power panel explicitly states that the two power definitions are not on a common quantitative scale. Data values are unchanged.
