# Reference-plane de-embedding contract

Use time convention exp(-i omega t), kx0=ky0=0, `kx_m = kx0 + 2*pi*m/Lambda_x`, and `ky_n = ky0 + 2*pi*n/Lambda_y`. In each local homogeneous medium, compute `kz_mn = sqrt((n(omega) k0)^2 - kx_m^2 - ky_n^2)` with the passive branch chosen so Re(kz)>=0 and Im(kz)>=0.

For upward (+z) amplitudes use `E+(z)=A+ exp(+i kz (z-z0))`, therefore `A+_ref=A+_sample exp(+i kz (z_ref-z_sample))`. For downward (-z) amplitudes use `E-(z)=A- exp(-i kz (z-z0))`, therefore `A-_ref=A-_sample exp(-i kz (z_ref-z_sample))`. For evanescent modes this gives decay in the direction of propagation; no evanescent amplitude is assigned propagating power.

Canonical physical planes and actual sampled monitor planes are separate records in `REFERENCE_PLANE_CONTRACT_V2.json`. No field extraction or modal de-embedding was executed in this task.
