# R2-4A proxy-to-FDTD validation hierarchy

Do not jump directly to full FDTD adjoint.

1. R2-4A: formulation only, no solver.
2. R2-4B: TMM/STACK variable-thickness DBR optimization / screening.
3. R2-4C: choose 3 to 5 candidates and generate setup-only FSPs for GUI inspection.
4. R2-4D: run 453 nm FDTD smoke for center_x + center_z_outofplane only.
5. R2-4E: only if angular smoke passes, run broadband angle-resolved spectral FWHM validation.
6. R2-4F: optional local adjoint or gradient refinement only after a near-pass candidate exists.

Why not direct adjoint first: the DBR/cavity is mostly 1D layered, so TMM/STACK is faster and more stable for initial exploration. Full FDTD adjoint for dipole angular/spectral objectives is more expensive and should be refinement, not first brute force. The R2_1_00223 failure proves plane-wave proxy is insufficient, so every optimized design still requires dipole-FDTD validation.
