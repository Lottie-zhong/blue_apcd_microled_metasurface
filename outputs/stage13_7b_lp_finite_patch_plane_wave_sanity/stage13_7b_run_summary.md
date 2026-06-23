# Stage13-7B LP A_small finite-patch plane-wave sanity FDTD

## Scope and setup

- One case only: `a_small_xlp_plane_wave_plusz`; normal-incidence x-LP plane wave from z=-250.0 nm below the pillar-base plane, injection axis z, direction Forward, propagating toward +z.
- A_small: 3 x 19 tiles, 342 dimers / 684 nanopillars; frozen Stage12 geometry unchanged.
- DBR/RCLED off; default Stage13 background; wavelength 450 nm; simulation time 100.0 fs; grid 101.
- Plane source spans the Stage13 FDTD x/y region; all dipole objects were deleted before setup save.
- Runtime: 5.391 minutes. Heartbeat interval: 30.0 seconds.
- Preflight history: the first setup-only attempt stopped before `run()` because Lumerical returned the canonical injection-axis label `Z-AXIS`; the validator was corrected to accept `Z`/`Z-AXIS`, tests passed, and the successful run had no preflight errors.

## Extraction

- Complex farfieldvector3d Ex/Ey/Ez with numeric farfieldux/farfielduy.
- Ez excluded from LP projection and included only in total vector power. No raw complex arrays saved.

## Result

- Ex global peak: ux=0.18000000000000005, uy=0.0; distance to +target=0.36975979996266434 deg; distance to -target=20.36975981099239 deg.
- finite_patch_plane_wave_steering_pass: `True`.
- sign_or_gradient_mismatch_suspected: `False`.
- finite_patch_plane_wave_no_steering: `False`.
- dipole_specific_mismatch: `True`.

## Single recommended next step

**Plane-wave sanity passes: continue with dipole-specific illumination/source-coupling diagnosis; do not add DBR/RCLED yet**

## Jones/APCD evidence boundary

- This finite-patch angular-power sanity check is not a periodic order-resolved J_xy/APCD reconstruction.
- No alpha/beta conversion or t_{alpha*<-alpha}^order claim is made.
