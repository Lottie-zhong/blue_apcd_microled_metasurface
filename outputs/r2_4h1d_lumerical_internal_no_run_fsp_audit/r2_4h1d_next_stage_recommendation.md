# R2-4H1D Next Stage Recommendation

Recommended next stage: `manual GUI screenshot audit`

If H1D status is `still_requires_manual_gui_screenshot_audit`, do manual GUI screenshot review first. If all metadata checks pass later, prepare H1E as a no-run simulation plan. Do not proceed directly to FDTD from H1D.


Because H1D still cannot confirm object/source/material metadata, the human GUI audit must capture:
- full object tree
- source object property panel
- source type and orientation
- source wavelength/frequency settings
- monitor list and far-field settings
- FDTD span/boundaries/mesh
- all material/layer names
- z-stack order and thickness estimates
- SiO2/TiO2 and m/pair-count evidence
