# R2-4H1B Manual GUI Audit Checklist

Use only if metadata is incomplete or to verify the freeze target before any FDTD planning.

- Open the original FSP read-only or via a disposable copy outside git.
- Confirm top MDC/DBR layer order and material names.
- Confirm SiO2 thickness near 100 nm and TiO2 thickness near 52 nm if present.
- Confirm pair count near m=8 if present.
- Confirm blue / 453 nm source or sweep settings.
- Confirm whether source is dipole/MQW-like or plane-wave-like.
- Confirm source orientation and position.
- Confirm monitor names, positions, and far-field monitor suitability.
- Confirm FDTD region, boundary conditions, and mesh settings.
- Do not run, mesh, runanalysis, sweep, optimize, or save over original files.
