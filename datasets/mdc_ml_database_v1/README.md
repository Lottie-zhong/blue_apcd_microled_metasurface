# MDC ML database v1

Absolute: `D:\project\worktrees\blue_apcd_mdc_defect_450\datasets\mdc_ml_database_v1`
Relative: `datasets/mdc_ml_database_v1/`
Database/schema version: 1.0.0
Generated from commit: `81371ba1b38368cfff3e4eb680f4be9d30f58ed6`

Nominal TMM rows are training candidates; tolerance rows are grouped validation/robustness labels; FDTD rows are external validation only. TMM plane-wave labels and FDTD dipole far-field labels must never be mixed. All split assignments are grouped by parent geometry.

Excluded: heavy artifacts, runtime probes as training rows, clipped labels without quality flags, and provisional raw broadband spectra. Source files are immutable and checksummed.

To append data, add committed lightweight source files, rerun `python scripts/build_mdc_ml_database_v1.py`, inspect `conflict_report.csv`, then run `--audit-only`.
