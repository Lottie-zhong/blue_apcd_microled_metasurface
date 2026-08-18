# Paper A new-scope axis-free broadband LP geometry search

## Verdict

PAPER_A_BROADBAND_LP_NEW_GEOMETRY_SEARCH_STOPPED_NO_STABLE_BASIN

The deterministic initial DOE completed with 6 geometries and 12 entered/accepted real x/y FDTD cases. No candidate met the final-pass or promising gate; no local refinement was started.

- Formal window: 435-465 nm, 1 nm, 31 points; source/monitor: 430-470 nm.
- Native-M1 FDTD only; phase/K6/old rescue ranking were not used.
- MDC weighting: ZL-1 alternative r12_normalized_output, relative spectral shape only.
- Geometry waves were sequential; x/y were the only concurrent cases.

## Candidate comparison

| rank | geometry | weighted DoLP | weighted useful LP | FWHM worst DoLP | FWHM psi span | final | promising |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | LPBROAD_G006 | 0.1244 | 0.0414 | 0.0528 | 145.80 deg | False | False |
| 2 | LPBROAD_G005 | 0.0548 | 0.0205 | 0.0184 | 132.52 deg | False | False |
| 3 | LPBROAD_G002 | 0.0645 | 0.0218 | 0.0127 | 270.00 deg | False | False |
| 4 | LPBROAD_G003 | 0.0623 | 0.0233 | 0.0079 | 145.80 deg | False | False |
| 5 | LPBROAD_G004 | 0.1720 | 0.0613 | 0.0022 | 167.72 deg | False | False |
| 6 | LPBROAD_G001 | 0.0318 | 0.0126 | 0.0014 | 195.03 deg | False | False |

No primary or runner-up is frozen because no geometry passed the pre-registered promising gate.

Artifacts: candidate_comparison.csv, full_formal_spectra.csv, final_decision.json, audit.json.
