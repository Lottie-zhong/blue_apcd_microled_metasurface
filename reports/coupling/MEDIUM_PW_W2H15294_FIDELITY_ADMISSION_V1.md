# MEDIUM PW W2H15294 fidelity admission report

STATUS: BLOCKED_FIDELITY_GATE

## Reference

- recovered 5 nm FSP SHA256: `aea4c8f642fb02fd1ba1717cc9e0d4612c316baf8d232f732c12121a4795472f`
- runtime: 8.22942 h (29625.919 s)

## MEDIUM

- case/attempt: `W2H_15294_MEDIUM_PW / attempt_001`
- native FSP SHA256: `f6579034bd86edbb740596ff02ee5cb26119b5bfc9f31e582535d0fabebab0e3`
- solver entry count: 1; replay: False
- scientific truth: `SCIENTIFIC_VALID`; native/load-only/archive PASS

## Canonical complex state

| Plane | max E_C | wavelength nm | max amplitude RMS | max phase RMS rad |
|---|---:|---:|---:|---:|
| IN | 0.289176031229 | 446 | 0.0758701622547 | 0.360046277179 |
| PRENP | 0.537559729041 | 446 | 0.291377240458 | 1.01317519029 |
| POSTNP | 290230425421 | 460 | 290230425421 | 0.136582063429 |

Aggregate max E_C: **290230425421**, worst `{'plane': 'POSTNP', 'wavelength_nm': 459.99999999999994, 'channel': {'order_m': -2, 'order_n': 4, 'direction': '+z', 'polarization': 'TE'}}`.
All 21 per-wavelength state rows and channel details are in the JSON report.

## Power / routing

- R max absolute error: 0.0893804187075 at 446 nm
- T max absolute error: 0.0186691772733 at 446 nm
- worst order error: {'absolute_error': 0.004302264528297288, 'wavelength_nm': 452.0, 'order': [2, 0], 'medium': 0.047073572972667836, 'reference': 0.051375837500965124}
- +1 routing correlation: 0.984911428635
- topology changes: post=0, input=0
- energy closure max: Medium=1.11022302463e-16; reference=0
The order/routing values are scalar order-resolved power comparisons; no alpha*/beta* Jones transfer claim is made here.

## Runtime

- Medium: 5.05003 h; 5 nm: 8.22942 h; speedup: **1.629580x**
- FAST authoritative runtime: 1.16101 h

## Final gate

| Metric | Threshold | Measured | Result |
|---|---:|---:|---|
| complex_state_E_C_max | 0.05 | 290230425421 | FAIL |
| R_absolute_error_max | 0.05 | 0.0893804187075 | FAIL |
| T_absolute_error_max | 0.05 | 0.0186691772733 | PASS |
| populated_order_absolute_error_max | 0.05 | 0.0043022645283 | PASS |
| routing_spectral_trajectory_correlation_min | 0.98 | 0.984911428635 | PASS |
| missing_required_wavelengths | 0 | 0 | PASS |

Decision: **MEDIUM_PW_PRODUCTION_FIDELITY_ADMITTED = NO**.
Failed criteria: `complex_state_E_C_max` and `R_absolute_error_max`.
Medium is not materially better overall than FAST for admission: scalar power/routing improves, but canonical state fidelity is substantially worse and R still fails.

## Production boundary

- `PW_K6_SEED_DB_V1_STARTED = NO`.
- `NO_FURTHER_SOLVER_ACTION = YES`.
- Comparison-phase scientific solver entries: `0`.
- Queue/slot/reservation released; historical `terminal_failure.json` is non-authoritative pre-entry evidence.

## Evidence

- queue: `RELEASED`; slot: `GLOBAL_SLOT_2=FREE`; reservation: `RELEASED`
- foreign mutation count: 0; duplicate scientific entry count: 0
- report JSON: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\MEDIUM_PW_W2H15294_FIDELITY_ADMISSION_V1.json`
