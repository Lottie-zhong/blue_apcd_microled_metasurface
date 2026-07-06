# R2-4H1K / FMM2A2 Next Stage Recommendation

Recommended next user action: complete the manual GUI audit for the H1J3 runtime FSP.

If the GUI audit passes, the next possible simulation stage is an explicitly approved H1L x-only 453 nm source-isolated FDTD validation using at least three x-axis source positions and incoherent intensity/power averaging.

If the GUI audit fails due to mesh order, monitor position, source settings, or far-field settings, perform a corrected derived FSP fix stage first. Do not run FDTD.

For FMM, do not proceed to FMM2B until an FMM/RCWA solver is installed or otherwise made available. The first FMM2B action should be a tiny API probe, not a sweep.
