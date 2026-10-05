# EXT02 two-air-plane evaluation V2

- Scope: one authorized diagnostic run; saved-field post-processing only.
- Run: EXT02_DIAG_20261004T141216Z_1b4ce0df234b; case K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001.
- Cross-height result: CONSISTENCY_THRESHOLDS_MET; readiness: READY.
- Frozen limits are one-case consistency criteria, not H1 or production-admission gates.

## Execution and authority

- Runner handoff: DONE / SCIENTIFIC_VALID; solver entries=1, run-one calls=1, automatic replays=0.
- This evaluation added zero solver entries, training fits, or P_scale fits; no confirmation response was accessed.
- Handoff SHA256: 2f41bfd493f4105b013ee4269033f789b0d86d007169a57557bee3262f325d75; protocol SHA256: fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8.
- No global phase alignment or fitted power rescaling was used.

## Actual planes and geometry

- MON_POSTNP actual z=1801.999999999993 nm (nominal 1800); diagnostic actual z=2006.604166666668 nm (nominal 2000).
- Actual separation=204.604166667 nm; shared reference=1722 nm.
- NP z=1212-1712 nm per pinned monitor audit; plane clearances above NP top=90.000000 and 294.604167 nm.
- Each monitor stores six complex E/H fields, 349 x 59 x 1 x 21, across the full 1740 x 290 nm period.
- Monitor-coordinate interval medians dx=5 nm and dy=5 nm; these are not the underlying solver mesh.
- Configured NP-derived mesh region ends at 1812 nm; far sample is 194.604167 nm above that configured boundary. Actual mesh transition is unknown.
- Configured z max=3000 nm, 993.395833 nm above far plane. Actual PML inner face is unknown; 2806.1667 nm is a prior layout estimate only.

## Normalization and same-run parity

- Official input E/H reprojection to the frozen -50 nm reference reproduced truth normalization: max relative incident-power delta=0; max wrapped gauge delta=0 rad.
- Near-plane state after deembedding matches the same-run saved POSTNP state with max relative L2=1.28021e-14; implementation parity, not independent validation.

## Frozen cross-height thresholds

| Metric | Observed | Maximum | Result |
|---|---:|---:|---|
| propagating_state_relative_l2 | 0.0077824166 | 0.02 | True |
| routing_max_abs_difference | 2.0107275e-05 | 0.005 | True |
| source_normalized_absolute_order_max_abs_difference | 1.2679032e-05 | 0.005 | True |
| propagating_total_power_relative_difference | 7.9374471e-05 | 0.01 | True |
| significant_coordinate_amplitude_weighted_phase_rmse_rad | 0.0064994422 | 0.05 | True |

- State relative L2 median/q95/max=0.0068760958 / 0.0076681069 / 0.0077824166.
- JSON includes all wavelength/order/TE/TM sample and deembedded complex values, amplitude/phase differences, per-order power/routing, and directionality.
- Significant mask and near-amplitude phase weights follow the frozen protocol; no oracle phase alignment.

## Fit, power, and evanescent diagnostics

- JSON includes periodic endpoint closure, official LS residual/rank/condition, trapezoid half-weights, Poynting vs modal power, downward state, and evanescent fits.
- Evanescent channels are diagnostic only and receive no far-field power or propagating threshold.
- Continuous-medium kz deembedding approximates FDTD numerical dispersion; actual local mesh and PML inner-face readbacks are missing.

## Historical EXT02 cross-run comparison

- New near-plane state was compared directly, without phase alignment, with historical EXT02 stored POSTNP at 1722 nm.
- Common base contract fields match after removing the added diagnostic monitor.
- Descriptive single pair only, no pass threshold. Setup FSP hashes differ and the historical mesh-contract hash is absent; this is not controlled repeatability and does not replace historical truth.

## Limits

This result addresses single-case cross-height extraction consistency only. It does not establish absolute convergence, controlled cross-run repeatability, global label validity, H1, or production admission. No training or additional solver entry occurred.
