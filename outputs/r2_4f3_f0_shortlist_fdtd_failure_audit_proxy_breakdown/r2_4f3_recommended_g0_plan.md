# R2-4F3 Recommended G0 Plan

Recommended task name:
`R2-4G0_dipole_aware_proxy_spec_and_minimal_validation_dataset_plan`

G0 should be Python-only. It should define a dipole-aware or reciprocity-aware reduced proxy before any new FDTD shortlist.

Minimum G0 content:
- identify the missing physics in the current stack-only proxy: dipole LDOS, source-position coupling, and dipole-to-farfield angular transfer;
- define the smallest validation dataset from existing D7/E2/F1/F2 negative samples;
- specify what proxy terms must predict before another candidate can enter FDTD;
- keep tri-point x-dipole 453 nm as the first FDTD gate after proxy redesign.

Immediate FDTD is not allowed from F0/F1/F2 failed routes.
