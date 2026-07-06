# R2-4H1J stop / allow rules

Stop:
- no FDTD
- no run, runanalysis, mesh/run mesh, optimize, or sweep
- no y-dipole
- no broadband
- no APCD coupling
- no center-only validation
- no committing `.fsp`, `.fspx`, `.ldf`, `.mat`, `.h5`, screenshots, images, or videos

Allow:
- derived runtime FSP creation only in the DO_NOT_COMMIT runtime directory
- lightweight CSV/JSON/MD audit outputs
- manual GUI inspection next
