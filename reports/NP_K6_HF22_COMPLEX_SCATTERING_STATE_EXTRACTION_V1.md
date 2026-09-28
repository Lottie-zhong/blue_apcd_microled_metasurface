# NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1

Status: **PASS**
Load-only solver calls: **0**; save calls: **0**; cases: **44/44**; spectral rows: **484/484**.

## Availability

All scoped raw fields were requested from `transmission_monitor` and `reflection_monitor`. The archive exposes complex `Ex,Ey,Ez,Hx,Hy,Hz` and 11 frequencies per monitor when the corresponding case loads. Availability is in `complex_availability_matrix.json`.

## Modal and normalization contract

Lumerical `gratingvector()` is used as the complex order-state API. `m=-3...+3` is retained and `m=+1` means physical +x. P is explicitly TM-projected; S is TE (`y`) and no P/S averaging is performed. Absolute coefficient is `sqrt(formal total power) * gratingvector component`; no per-case rescaling is applied. Raw E/H is independently integrated through Poynting flux and `sourcepower(f)`.

## Closure

Median/q95/max modal absolute error: `1.1102230246251565e-16`, `5.949861818510537e-09`, `2.4543043597446967e-08`. Transmission raw E/H Poynting absolute error: `1.3322676295501878e-15`, `4.218847493575595e-15`, `0.030299750930748437`. Reflection raw E/H Poynting is intentionally marked non-isolated because the reflection plane contains the incident field; reflected-order closure uses `gratingvector` including open m=±4,±5 in SiO₂. Detailed rows are in `complex_power_closure_long.csv` and summary JSON. No closure failure is hidden by renormalization.

## Phase and Jones limitations

Phase is preserved at the physical monitor plane; no arbitrary global phase alignment or source-plane de-embedding was applied. A full 2x2 Jones matrix is unavailable because each geometry has one P and one S input column only; this dataset must not be used to claim polarization selectivity without the missing cross-input columns.

## Artifacts

The machine-readable extraction directory is `outputs/np_k6_hf22_complex_scattering_state_extraction_v1/`. The report and all artifact checksums are generated from LOAD-only reads. No solver result was created or modified.
