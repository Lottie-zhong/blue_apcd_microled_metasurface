# NP K6 frozen forward-surrogate Nature figure layout v2

## Caption

**Held-out K6 ranking and order-resolved spectral evidence from distinct frozen provider components.** Figure 1 shows a 22-geometry held-out ranking comparison using `LF_only / ensemble_raw` (Spearman rho = 0.962). Figure 2 compares FDTD truth, `LF_ridge_residual / ensemble_raw` raw prediction and absolute error for programmatically retained Best, Median and Worst geometries. The selection metric is geometry-level mean absolute eta(+1) OOF error over explicit P/S and 445-455 nm. Each P_XLIKE and S_YLIKE heatmap uses the authority-derived transmitted-order vector `m = [-3, -2, -1, 0, 1, 2, 3]`; `m = +1` corresponds to physical +x. Truth and raw prediction share a global zero-centred scale. Negative predicted values are retained to expose physics-consistency violations and are not clipped. Absolute error uses a separate, global scale shared by all cases.

The provider components are distinct and do not form a single universal surrogate. Scope is normal incidence only (`u_x = 0`, `k_y = 0`), with 22 held-out geometries, 484 HF rows, explicit P/S, and 445-455 nm support. These figures support screening/ranking before FDTD; they do not support FDTD replacement, angular generalization, Jones-matrix prediction or integrated MDC-NP truth.

## Compute audit

No new FDTD, RCWA, training, external-HF access, inverse design or data regeneration was performed. PNG/TIFF are 600 dpi; PDF/SVG retain editable text.
