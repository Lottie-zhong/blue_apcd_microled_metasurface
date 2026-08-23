# NP K6 capability boundary

## Supported

- Geometry ranking
- Coarse screening
- Normal-incidence spectral estimation at `u_x = 0`, `k_y = 0` with explicit P/S

## Not supported

- FDTD replacement
- Quantitative coupled-device prediction
- Angular generalization
- Jones-matrix prediction
- Full MDC–NP integrated truth

The ranking component (`LF_only`) and spectral component (`LF_ridge_residual`) are distinct frozen provider components. Final quantitative verification remains full-wave FDTD.
