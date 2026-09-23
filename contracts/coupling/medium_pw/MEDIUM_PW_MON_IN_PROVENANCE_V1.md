# MEDIUM_PW_MON_IN_PROVENANCE_V1

`MON_IN` completes the production truth payload required by the frozen
`PW_COMPLEX_FLOQUET_STATE_COMPARATOR_V1`. The production state remains measured
FDTD six-component total fields; an analytic plane-wave source is not substituted
for the input-plane truth.

## Frozen monitor

- Name: `MON_IN`
- Type: 2D Z-normal frequency-domain field monitor
- Sample plane: `z=-100 nm`
- De-embedded reference: `z=-50 nm`
- Coverage: `1740 x 290 nm`, the complete periodic supercell
- Grid: 440¨C460 nm, exactly 21 points
- Fields: complex `Ex,Ey,Ez,Hx,Hy,Hz`
- Local medium: `APCD_GAN_NATIVE_M1`

The existing `MON_PRENP`, `MON_POSTNP`, and `MON_REFLECTION` positions and
semantics are unchanged. Geometry, MDC, spacer, source, polarization, boundary
conditions, materials, mesh, wavelength grid, normalization, order convention,
and validation thresholds are unchanged.

## Placement audit

The mesh/geometry authority places homogeneous GaN at `-600 <= z <= 0 nm`.
Therefore `z=-100 nm` is inside the intended local medium. The source is at
`-276 nm`, the GaN/MDC interface is at `0 nm`, and PML begins at `-600 nm`; no
source coincidence, material interface, or PML overlap exists.

## Extraction

The existing PW extraction path consumes `MON_IN`, `MON_PRENP`, and `MON_POSTNP`
through the same canonical comparator. It produces the unchanged state schema
`PW_COMPLEX_FLOQUET_STATE_V1` with shape `[3,21,81,2,2]`; no MEDIUM-specific
comparator or analytic incident-field definition is introduced.

The generated setup-only and LOAD-only readback artifacts are kept under the

The generated setup-only artifact SHA256 is
`1907d677c0a35e658ae3595c665e5899d093f97480bc1e79cbecf110f110489b`; the
LOAD-only monitor-inventory readback SHA256 is
`0c57bf56511c45c3cfd9d56d7e3bff1996c5bfdaa2508b695755364b28fef033`.
No solver invocation or scientific solver entry occurred.
existing output namespace and are not Git-tracked. The focused zero-solver test
also reruns the existing MEDIUM pre-entry and comparator A¨CJ suites.
