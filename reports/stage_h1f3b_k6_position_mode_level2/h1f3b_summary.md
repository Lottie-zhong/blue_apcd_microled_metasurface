# H1F-3B K6 position-mode Level-2

- Status: FULLWAVE_COMPLETE; 8/8 formal x/y cases accepted, 0 quarantine, 0 replay.
- Mode: `delta_x_n=A*cos(2*pi*n/6)`, phi=0, A=+/-10 nm, zero mean, fixed P=6p, no y motion.
- Seeds: H1F1-A (`K6_L0_A`) and H1F2-C (`K6_L1_C`); no fallback.
- Order-resolved rows: 792; target-order Jones rows: 36; alpha/beta transform uses authoritative H1D1 transform.
- Principal classification: `POSITION_MODE_RESPONSE_WEAK`. Seed transferability: `WEAK_FOR_BOTH`.
- Central differences are local empirical full-wave sensitivities; phase uses circular-safe complex differences.
- K6 registry row semantics: one target-order Jones row per layout x polarization x wavelength; 648 -> 720 (+72); local registry remains 578; ML admitted: false.
- No automatic continuation to another amplitude, mode, or seed.
