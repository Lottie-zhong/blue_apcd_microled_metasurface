# R2-4H1C Baseline Decision After Path Resolution

Primary GUI-audit target: `F:\wc_312\MDC_blue_oujizi.fsp`

Reason:
- H1A found MDC blue qujizi/oujizi naming evidence.
- H1B loaded `F:\wc_312\MDC_blue_oujizi.fsp` successfully but could not introspect object/source/material metadata through the attempted API path.
- H1C confirms the exact oujizi FSP path remains available for manual GUI audit.
- Exact `F:\wc_312\MDC_blue_qujizi.fsp` found: `False`.

Text-supported Wan MDC baseline hints:
- SiO2/TiO2: `False`
- blue 453/450 text: `True`
- 100/52 nm text: `True`
- m about 8: `False`

Decision: keep `F:\wc_312\MDC_blue_oujizi.fsp` as the primary manual GUI-audit target. Do not freeze it for simulation until GUI evidence confirms object tree, source type, source settings, monitor settings, layer stack, and 453 nm target.

Immediate FDTD allowed: `false`
Next recommended stage: manual GUI screenshot review, then H1D no-run simulation plan only if the audit passes.
