# MDC1C2 FMMAX minimal single-dipole closure

Generated: 2026-07-08T16:01:57

## Scope

This stage is a minimal FMMAX single x-dipole-like gaussian source closure probe for MDC. Uniform layer permittivity is represented as a 1x1 spatial grid, as required by FMMAX. Layer thickness arrays include one entry per layer, with semi-infinite bounding layers represented by zero thickness. The minimal source uses matching jx/jy/jz shapes, with only jx nonzero. It does not use Lumerical, does not open/save FSP, and does not run FDTD.

It is intentionally not the final noncoherent position average. Center/side incoherent averaging is deferred to 2D FDTD.

## Settings

- wavelength: 450.0 nm
- approximate_num_terms: 50
- pitch: 1200.0 nm
- source: gaussian x-dipole-like source, FWHM 80.0 nm

## Candidate set

- `BARE_GaN_Air`: bare reference
- `MDC-A0-INT`: rounded quarter-wave reference
- `MDC1B_FAB_0126`: fabrication-friendly baseline
- `MDC1B_PERF_0890`: performance anchor

## Result summary

- status: `minimal_closure_ok`
- ok_rows: `4`
- api_failed_rows: `0`
- failed_rows: `0`

| candidate | status | diagnostic amplitude abs sum | runtime s |
|---|---|---:|---:|
| BARE_GaN_Air | ok | 122.57863140106201 | 11.333868265151978 |
| MDC-A0-INT | ok | 227.28271865844727 | 1.9330132007598877 |
| MDC1B_FAB_0126 | ok | 280.1814489364624 | 1.1809625625610352 |
| MDC1B_PERF_0890 | ok | 206.7767276763916 | 2.0781774520874023 |

## Interpretation

FMMAX import, basis generation, stack construction, gaussian source creation, and source-amplitude call completed for at least one candidate. This closes the minimal single-dipole FMM loop.

## Next

Do not use this as final device evidence. Next physical validation should be 2D FDTD with center/side source positions and noncoherent averaging.

## Local raw outputs

- `outputs/mdc1c2_fmmax_minimal_dipole/mdc1c2_fmmax_minimal_dipole_results.csv`
- `outputs/mdc1c2_fmmax_minimal_dipole/mdc1c2_fmmax_api_info.json`

## Tracked lightweight outputs

- `reports/mdc_defect_450/mdc1c2_fmmax_minimal_dipole_report.md`
- `reports/mdc_defect_450/mdc1c2_fmmax_minimal_dipole_compact_results.csv`
