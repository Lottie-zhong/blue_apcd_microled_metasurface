# NP K6 frozen forward-surrogate order heatmap Nature figure v1

## Caption

**Order-resolved held-out evidence for rapid K6 screening.** **a,** Geometry-level held-out ranking for 22 K6 geometries. Each marker is one held-out geometry and uses the frozen broadband η(+1) score across explicit P/S and 445–455 nm; the ranking component is `LF_only / ensemble_raw` (Spearman ρ = 0.962). **b,** Programmatically selected Best, Median and Worst geometries ranked by mean absolute η(+1) OOF error across both polarizations and 11 wavelengths. Each cell shows the authority-derived transmitted-order vector `m = −3,…,+3` for P_XLIKE and S_YLIKE without interpolation, smoothing, clipping or renormalization. FDTD and `LF_ridge_residual / ensemble_raw` prediction use one common linear efficiency scale; absolute error uses a separate linear scale. Raw negative model predictions remain visible.

## Frozen data and selection

- HF authority: `outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv` (484 rows; 22 geometries × 2 polarizations × 11 wavelengths).
- OOF authority: `outputs/np_k6_m9_22g_forward_retraining_v1/oof_predictions_22g.csv`.
- Best: `K6X_D110_D190_D210_D215_D220_D225`, rank 1/22, mean η(+1) error 0.023598.
- Median: `K6X_D100_D130_D135_D155_D160_D225`, rank 11/22, mean η(+1) error 0.067126.
- Worst: `K6X_D135_D155_D190_D220_D225_D230`, rank 22/22, mean η(+1) error 0.185083.

## Interpretation boundary

The ranking and spectral panels use distinct frozen provider components, not one universal surrogate. Scope is normal incidence (`u_x = 0`, `k_y = 0`) only. The figure supports screening/ranking before full-wave FDTD verification; it does not support FDTD replacement, angular generalization, Jones-matrix prediction or integrated MDC–NP truth.

## Compute and export audit

New FDTD, RCWA, training, external-HF access, inverse design and data regeneration are all zero. Final exports are 183 × 163.8 mm in PNG/TIFF (600 dpi) and editable PDF/SVG.
