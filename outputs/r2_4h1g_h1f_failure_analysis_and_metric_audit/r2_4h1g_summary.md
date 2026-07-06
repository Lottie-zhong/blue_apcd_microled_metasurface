# R2-4H1G summary

Decision: `metric_definition_needs_correction_before_physics_decision`.

H1F is valid as a three-position, source-isolated x-dipole run, but it remains a fail/high-risk result for near-normal APCD source preconditioning. The original incoherent average peak is 12.350 deg and FWHM is 44.392 deg. The average lobe class is `moderate_offaxis`.

Metric audit status: `warning`. Python-side recalculation was `available`. Because the audit found normalization/window-definition warnings, the leakage-window metrics should be treated as audit flags until the angle-integration convention is locked down.

Immediate further FDTD allowed: `false`.

Next allowed stage: planning/metric-definition cleanup only, followed by RCLED/DBR or MDC+RCLED source-conditioning design planning if the project still needs stronger near-normal narrowing.
