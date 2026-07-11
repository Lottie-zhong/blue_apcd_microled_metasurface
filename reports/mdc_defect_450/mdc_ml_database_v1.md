# MDC ML database v1

Absolute path: `D:\project\worktrees\blue_apcd_mdc_defect_450\datasets\mdc_ml_database_v1`
Relative path: `datasets/mdc_ml_database_v1/`
Database/schema version: 1.0.0
Generated from commit: `81371ba1b38368cfff3e4eb680f4be9d30f58ed6`

## Counts

- Source files: 302; raw coarse rows: 2688; unique geometries: 8675.
- Canonical nominal TMM records: 2688; tolerance samples: 8400; FDTD records: 11.
- Unique tolerance physical geometries: 6448; duplicate tolerance rows: 1952; conflicts: 0.
- Missing source directory: `outputs/mdc1d3_broadband_spectrum_normalization_audit/` (recorded as missing; no inference).

## Dedup and labels

- Geometry hashes use ordered material/thickness layers, GaN/Air boundaries, propagation direction, Native-M1 IDs, and material model; candidate names, source files, roles and ranks are excluded.
- Refined nominal metrics supersede coarse metrics for the same physical geometry; coarse records remain provenance.
- TMM spectral/angular labels, FDTD dipole far-field labels, raw monitor power, and normalized power are separate dictionary entries.
- Clipped widths are blank with quality flags; provisional broadband raw spectra are excluded from training.

## Splits

- Strategy: grouped_parent_geometry_v1, seed 20260711, nominal split 70/15/15; FDTD rows use external_high_fidelity_validation.
- Split counts: {'train': 10394, 'test': 338, 'validation': 356, 'external_high_fidelity_validation': 11}; geometry hash overlap 0; parent group overlap 0.

## Limitations

- No solver was run. Existing source result files and frozen materials were read only.
- Runtime probes are retained in inventory but never used as MDC performance training data.
- Broadband FDTD raw upward spectra are provisional and not pure-film spectral labels.
