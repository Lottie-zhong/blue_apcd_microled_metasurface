# Stage-A P/S sensitivity reduction audit v1

Read-only audit of the frozen Stage-A integrated MDC+spacer+NP matrix.
The matrix is not an NP-only provider and this report does not define a shared NP P/S operator.

## P/S quantitative difference

- Status: `SYSTEM_LEVEL_PS_DIFFERENCE_SUBSTANTIAL` (`DESCRIPTIVE_ONLY`; `NO_FORMAL_TOLERANCE`).
- Pairs: `55` exact same-angle/same-wavelength P/S pairs.
- Mean / median / max `abs(delta_eta_plus1)`: `0.112704464789` / `0.106306992985` / `0.368746078251`.
- Maximum at `-5 deg`, `453 nm`.
- Mean / max symmetric relative difference: `0.495274203734` / `1.45172080357`.

| angle (deg) | mean eta+1 P | mean eta+1 S | mean abs delta | max abs delta | mean R P/S | mean T P/S | mean directionality P/S | max-difference wavelength (nm) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| -10 | 0.18489464 | 0.28160075 | 0.12731358 | 0.20094459 | 0.14074632 / 0.1125815 | 0.25417383 / 0.3271247 | 0.97782862 / 0.96748245 | 453 |
| -5 | 0.18651402 | 0.29915571 | 0.1290285 | 0.36874608 | 0.14257313 / 0.109914 | 0.2586089 / 0.33876097 | 0.95627318 / 0.9823233 | 453 |
| +0 | 0.27928111 | 0.27459792 | 0.10958132 | 0.1783485 | 0.11605347 / 0.11562449 | 0.32122302 / 0.32846818 | 0.9947855 / 0.9810412 | 454 |
| +5 | 0.22772889 | 0.26530952 | 0.12528616 | 0.28991221 | 0.13437763 / 0.11438301 | 0.27601887 / 0.3293258 | 0.94250627 / 0.98713916 | 453 |
| +10 | 0.16395052 | 0.20386976 | 0.072312763 | 0.16545919 | 0.13291476 / 0.11814934 | 0.26984989 / 0.31569452 | 0.94716989 / 0.94960271 | 450 |

## Where difference comes from

The direct `eta(+1)` difference is decomposed exactly into a throughput contribution and an order-partition contribution. Reflection and residual deltas are accompanying energy-budget channels; they are not treated as an NP-only causal attribution.

- Direct-source counts: `{"ORDER_PARTITION": 8, "THROUGHPUT": 47}`.
- Budget-channel counts: `{"REFLECTION": 2, "RESIDUAL": 3, "THROUGHPUT": 50}`.
- The closure identity is checked per pair as `delta_R + delta_T + delta_residual`; no new numerical tolerance is introduced.

## Scientific interpretation

This is system-level P/S sensitivity evidence in the observed frozen matrix only. It may inform whether testing a shared NP P/S approximation is worth a separately authorized study, but it cannot validate that approximation. No claim of P/S equivalence, NP polarization independence, or formal pass/fail tolerance is made.

## Safety / Git

- Matrix SHA256: `d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6`.
- Matrix path: `D:\project\worktrees\blue_apcd_mdc_np_coupling_v1\reports\coupling\stage_a_frozen_spacer_polarization_angle_broadband_matrix_v1.json`.
- This audit solver entries: FDTD=0, TMM=0, RCWA=0, training=0, ML inference=0.
- Polarization averaging: false; exact P/S branches retained.
- Next action: `USER_REVIEW_PS_REDUCTION_EVIDENCE`.
