# R2-4H1E Manual GUI Audit Record and No-run Plan

Primary baseline target: `F:\wc_312\MDC_blue_oujizi.fsp`

Baseline status: `manual_metadata_supported_primary_baseline_for_no_run_plan`

Manual GUI audit confirms:
- TiO2/SiO2 MDC interpretation through custom materials `tio22` and `sio222`.
- TiO2-like layer thickness: 52 nm.
- SiO2-like layer thickness: 100 nm.
- Blue source settings are present: plane source 438-468 nm and dipole source fixed at 450 nm.
- Dipole source `source_1` is present and set as electric dipole with theta=90 deg, phi=0 deg.
- m about 8 is strongly inferred from stack geometry, but exact object count remains to be recorded if needed.

Critical risks:
- File is in ANALYSIS mode and has existing results; those results must not be used as validation.
- Both PlaneSource `source` and DipoleSource `source_1` exist. Future dipole FDTD must disable `source` and isolate `source_1` in memory.
- Do not save changes back to the original FSP.

This is not optical validation.
Immediate FDTD allowed in H1E: `false`.
