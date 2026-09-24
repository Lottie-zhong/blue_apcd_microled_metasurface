# PW_GPU_MONITOR_TRUTH_SCHEMA_V1

This is the frozen role-aware production truth schema for the PW GPU path. It preserves `MEDIUM_PW_MONITOR_CONTRACT_V1` exactly.

- `MON_IN`, `MON_PRENP`, and `MON_POSTNP` require the 21-point 440–460 nm grid and complex `Ex`, `Ey`, `Ez`, `Hx`, `Hy`, `Hz` payloads.
- `MON_REFLECTION` is a 2D Z-normal monitor at z = -400 nm with 1740 × 290 nm span and 21 points. It is R-only: signed Poynting/power payload and normalized `R` are required; complex E/H are not required and `complex_fields=[]` is valid.
- The validator checks monitor role, geometry, wavelength grid, required payload, and bundle/archive completeness. It never applies the E/H requirement uniformly to all monitors.

The authoritative source remains:
`contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json`.
