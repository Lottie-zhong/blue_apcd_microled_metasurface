# R2-4E0 FDTD Entry Rules

These rules apply after Python-only E1 candidate generation. E0 itself runs no FDTD.

1. No center-only FDTD verdict is allowed.
2. First FDTD must be tri-point x-dipole at 453 nm only.
3. Tri-point positions are x = [-0.7, 0.0, +0.7] um.
4. Pass tri-point before any 5-point x-line.
5. Pass 5-point before any 9-point x-line.
6. Fail at any stage stops that candidate immediately.
7. No y-dipole, z-out-of-plane, or broadband validation before tri-point pass.
8. The tri-point guard must check normal/off-axis lower bound, 30-40 deg lobe revival, angular FWHM, and source-position consistency.
