# R2-4G0 Minimal Validation Dataset Plan

Purpose: calibrate the next proxy with the fewest possible FDTD cases, not run another blind sweep.

Dataset stages:
- G1: Python-only assemble existing negative dataset and feature table. No FDTD.
- G2: minimal calibration FDTD only if explicitly approved, maximum 2 new candidates x 3 tri-point cases, x-dipole only, 453 nm only.
- G3: fit/threshold/update proxy using negatives plus any calibration results.
- G4: candidate generation using calibrated proxy.

G0 does not execute G1/G2. It only defines the boundary.
