# MDC1D0 2D FDTD noncoherent-average plan

Generated: 2026-07-08T16:09:39

## Scope

This stage prepares the 2D FDTD validation plan for MDC. It does not open FSP, does not run Lumerical/FDTD, and does not perform runanalysis.

## Physical goal

Validate the MDC source-module using 2D FDTD with lateral source-position averaging:

```text
center source + left source + right source -> incoherent power average
```

This is needed because FMM/TMM treat the MDC as laterally uniform, while 2D FDTD can later include finite window, source placement, and angular-spectrum extraction.

## Planned candidate set

- `BARE_GaN_Air` (bare_reference): bare GaN/Air
- `MDC1B_FAB_0126` (baseline_fab_primary): SiO2:79nm / TiO2:45nm / SiO2:79nm / TiO2:45nm / SiO2:79nm / TiO2:45nm / SiO2:156nm / TiO2:45nm / SiO2:79nm / TiO2:45nm / SiO2:79nm / TiO2:45nm / SiO2:79nm
- `MDC-A0-INT` (rounded_reference): SiO2:79nm / TiO2:44nm / SiO2:79nm / TiO2:44nm / SiO2:79nm / TiO2:44nm / SiO2:158nm / TiO2:44nm / SiO2:79nm / TiO2:44nm / SiO2:79nm / TiO2:44nm / SiO2:79nm
- `MDC1B_PERF_0890` (performance_anchor): SiO2:81nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:157nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:81nm / TiO2:44nm / SiO2:81nm

## Planned source set

- wavelengths: `[450.0]` nm
- source x positions: `[0.0, -500.0, 500.0]` nm
- first dipole set: `['x']`
- planned jobs: `12`

## Metrics to extract in MDC1D1+

- upward power
- angular spectrum
- 20° cone power
- 40–60° large-angle leakage
- normal-to-large-angle ratio
- center/side sensitivity
- noncoherent averaged metrics

## Template audit

- matched local script/report files: `180`
- See `reports/mdc_defect_450/mdc1d0_fdtd_template_audit.csv`.

## Decision

Next safe stage is `MDC1D1`: build a minimal 2D FDTD smoke script for one case first, preferably `BARE_GaN_Air` and then `MDC1B_FAB_0126`, before launching all 12 planned jobs.

## Tracked lightweight outputs

- `reports/mdc_defect_450/mdc1d0_fdtd_2d_plan.md`
- `reports/mdc_defect_450/mdc1d0_fdtd_2d_job_manifest.csv`
- `reports/mdc_defect_450/mdc1d0_fdtd_template_audit.csv`
