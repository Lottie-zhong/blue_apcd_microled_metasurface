# Paper A LP balanced initial truth v1

Status: `HARD_GATE_CASE_FAILURE`

Current Native-M1; source/monitor 430-470 nm; formal axis-free full-Jones evaluation 435-465 nm at 1 nm; zero-order J_xy from independent x/y inputs.
Solver entered: 1/8. Conditional BF05-BF08 was not authorized or run.

| geometry | weighted DoLP | weighted P_LP | FWHM psi span | FWHM DoLP worst | pass | promising |
|---|---:|---:|---:|---:|---|---|

## Physics validity hard gate

- Failing case: BF01_x
- Gate status: INSUFFICIENT_EVIDENCE_NOT_VALIDATED
- Gate 1: no Auto Shutoff trajectory in immutable solver log.
- Gate 2: independent late-time electromagnetic-energy/residual time series was not persisted.
- Gate 3 transmission sanity and Gate 4 source normalization passed.
- No replay was performed; BF01_y-BF04_y were not started.
