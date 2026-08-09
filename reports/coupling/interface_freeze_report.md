# APCD MDC-NP Coupling V1 interface freeze

Status: FINAL_SPACER_FREEZE_FOR_STAGE_A_XPOL_NORMAL

The one-way power interface is frozen for the Stage-A x-polarization, normal-incidence, kx/k0=0 scope. The interface provider is SUPPORT_NONE with no additional support layers and Air as the reference medium.

The fixed MDC is the ZL-1 alternative with a 79 nm top SiO2 termination. The final broadband spacer comparison evaluated t_extra = 0, 79, and 237 nm on the exact 445-455 nm, 1 nm grid. T237 is frozen: extra SiO2 = 237 nm and total SiO2 separation = 316 nm. Evidence is recorded in reports/coupling/stage_a_broadband_spacer_selection_v1.json and its accompanying Markdown report.

All three broadband solver cases entered and completed exactly once. Post-FSP identity, native-material provenance, exact-grid extraction, order closure, power closure, and m=+1 physical +x sign audits passed. The 450 nm monochromatic comparisons remain diagnostic-only because no formal cross-acquisition numerical tolerance exists.

This freeze does not authorize y-polarization, oblique incidence, nonzero kx, interpolation, unrun spacers, production transfer, or Micro-LED dipole integration. Any new solver run requires explicit authorization.
