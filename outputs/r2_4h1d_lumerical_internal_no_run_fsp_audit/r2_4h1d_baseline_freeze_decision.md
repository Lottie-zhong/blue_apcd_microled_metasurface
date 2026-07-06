# R2-4H1D Lumerical Internal No-run FSP Audit

Target FSP: `F:\wc_312\MDC_blue_oujizi.fsp`

Load succeeded: `True`
Lumerical version: `8.33.3999`
Object tree extracted: `False`
Source type confirmed: `False`
SiO2/TiO2 confirmed: `False`
450/453 nm confirmed: `False`
100/52 nm confirmed: `False`
m about 8 confirmed: `False`

Baseline status: `still_requires_manual_gui_screenshot_audit`
Immediate FDTD allowed: `false`
Next stage: `manual GUI screenshot audit`

Command attempts:
- Succeeded: 4
- Failed/unsupported: 11

H1D did not run, mesh, analyze, optimize, sweep, save, or copy the original FSP.


## Conservative Freeze Decision

Do not freeze an executable simulation baseline from H1D unless the GUI confirms source type, source wavelength, monitor layout, FDTD boundaries, and SiO2/TiO2 stack details. H1D metadata alone is not optical validation.
