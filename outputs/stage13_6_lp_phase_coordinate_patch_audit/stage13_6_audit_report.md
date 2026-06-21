# Stage13-6 LP Phase-Ramp / Coordinate / Finite-Patch Consistency Audit

## Scope

- Read-only audit of existing Stage12 and Stage13 artifacts. No FDTD, +/-q, DBR/RCLED, geometry change, optimization, or FSP write.
- K=6 means six dimers, not six nanopillars.

## 1. Stage12 plane-wave evidence

- Official target: x-order +1 in the x-z plane, +10.000000 deg, ux=+0.173648177762.
- Stage12 periodic FDTD measured x-LP +1 power 0.357823825858; +1 was dominant. Zero and -1 powers were 0.080872261874 and 0.017669974856.
- Propagation/monitor convention: plane wave below the z=0 pillar base, forward +z; top z-normal monitor above the 500 nm pillars.
- Evidence is periodic/metagrating order resolved (`gratingvector`/order CSV), not only cone integration. The official package contains `figure_3_xgrad_order_power.png/.svg`.
- Stage12 explicitly maps order_n=+1 to ux=+0.173648 and calls it +x/+10 deg.

## 2. Frozen K=6 phase ramp

- Lambda_x=2591.446716 nm; phase-bin pitch=431.907786 nm; y pitch=432.0 nm.
- Dimer centers: d0=-1079.769465 nm/0 deg, d1=-647.861679 nm/60 deg, d2=-215.953893 nm/120 deg, d3=215.953893 nm/180 deg, d4=647.861679 nm/240 deg, d5=1079.769465 nm/300 deg.
- Nominal bins are 0,60,120,180,240,300 deg and increase monotonically along +x. Unwrapped actual common phases are also monotonic.
- Under the repository's empirical Stage12 convention, positive dphi/dx produces order +1 / +x. The periodic FDTD confirms this sign.
- Result: phase sequence is internally consistent; `phase_ramp_error_suspected=false`.

## 3. A_small finite patch

- 3 x 19 whole tiles; 342 dimers / 684 nanopillars. Extent: x=[-3831.216181, 3816.216181] nm, y=[-4000.5, 3965.5] nm.
- Whole six-dimer supercells are repeated at integer x-tile offsets without phase reset errors. Edge asymmetry remains 15 nm in x and 35 nm in y, matching Stage13-2.
- No true center dimer. The source lies midway between phase-120 and phase-180 dimer centers at x=+/-215.953893 nm; it is not on a supercell boundary or the 300->0 phase wrap.
- Six nearest pillars: 180deg J2 (115.954 nm), 120deg J2 (218.386 nm), 120deg J1 (227.799 nm), 180deg J1 (295.954 nm), 120deg J1 (419.376 nm), 180deg J2 (447.291 nm).
- The closest pillar is phase-180 J2 at 115.954 nm, so local source coupling is geometrically biased even though the two nearest dimer centers are tied.
- Result: tiling is consistent; `finite_patch_tiling_error_suspected=false`, `source_center_local_bias=true`.

## 4. Far-field coordinate consistency

- Stage13 uses `farfieldux/farfielduy`; saved extraction shape is 101x101 and the PNG axes cover approximately [-1,+1]. Positive ux is plotted to the right and CSV values preserve the API sign.
- Both Stage12 and Stage13 use a +z/top monitor, but Stage12 order signs come from grating-order extraction while Stage13 signs come from continuous far-field direction cosines.
- No common saved dataset directly proves that `gratingvector order_n=+1` and Stage13 `farfieldux>0` have identical sign under all monitor conventions.
- Expected ux=+/-0.173648177762; Stage13-5 peaks are center_x Ex (-0.34,-0.12) and center_y Ey (-0.58,0), both far from expected +/-10 deg centers.
- Result: `coordinate_status=unresolved`, not failed.

## 5. Angular-spectrum and excitation mechanism

- center_x Ex retains finite power near both expected orders, but its global peak is near theta_x=-19.88 deg with nonzero uy, indicating a broad/multilobed finite-aperture field rather than clean periodic +1 steering.
- center_y Ey peaks near theta_x=-35.45 deg, not at zero or +/-10 deg.
- The default homogeneous background, absent substrate/device stack, no DBR and no RCLED allow broad off-normal dipole components; this is not representative of a final MicroLED stack.
- Periodic plane-wave illumination excites every supercell coherently. A single local dipole below a finite patch excites phase bins with unequal amplitude and phase, especially with the center-pillar bias above.
- DBR/RCLED is not recommended yet because coordinate/API sign consistency is still unresolved.

## 6. Classification

- phase_ramp_error_suspected: false
- finite_patch_tiling_error_suspected: false
- coordinate_mapping_unresolved: true
- local_dipole_broad_angle_dominance: true
- plane_wave_to_dipole_mismatch: true
- source_center_local_bias: true
- insufficient_evidence: false for layout/tiling; true for direct API-to-API sign equivalence

## 7. Recommended next action

**Stage13-7A: no-new-FDTD coordinate/sign validation against Stage12 plane-wave artifacts.**

This is the single next step. Do not run +/-q or add DBR/RCLED until the Stage12 grating-order sign and Stage13 continuous far-field sign are tied by a direct artifact-level check.

## Jones/APCD evidence boundary

- This audit uses existing periodic order power and finite-patch dipole angular power. It does not construct a new incident-wave J_xy matrix.
- No alpha/beta basis conversion or t_{alpha*<-alpha}^order claim is made here.
