# APCD MDC-NP Coupling V1 interface freeze

Status: APCD_MDC_NP_COUPLING_V1_INTERFACE_ONLY_AWAITING_SOURCE_SCOPE_FREEZE

The coupling worktree is based on MDC commit 489b54e43bbf2c08ce030a945b9d4b70ee7550f2. MDC is a frozen five-seed M1 2D joint wavelength-angle relative-upward-power surrogate and is not externally validated. The NP source is branch commit 6493fae1f9acc636722ae1705c58b208c5cbdbe6; its authoritative handoff records pilot-only scope, pending interface decisions, zero formal HF labels, and no model training.

The interface is limited to one-way incoherent power records keyed by wavelength_nm and kx_over_k0. The coordinate contract fixes +z from GaN through MDC to K6 and Air, physical +x as positive kx and m=+1. MDC x/z dipole channels are not mapped to NP x/y polarization. Extra spacer baseline is 0 nm; 79/158/237 nm remain future Stage A diagnostic candidates.

No FDTD, TMM, RCWA, FEM, or NP solver was run. No model was trained. No source worktree was modified. No large artifact is committed.
