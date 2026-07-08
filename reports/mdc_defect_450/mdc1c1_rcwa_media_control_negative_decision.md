# MDC1C1 RCWA media-control negative probe

Generated: 2026-07-08T16:02:00

## Scope

Blank-project Lumerical RCWA property probe. No RCWA run, no FDTD, no FSP open/save.

## Result

- decision: `do_not_run_GaN_Air_RCWA_until_media_control_is_known`
- rcwa_object_created: `True`
- can_set_gaN_air_media: `False`
- set_ok_properties: `['background material', 'index', 'propagation axis']`

## Decision

Do not use the current Lumerical RCWA template for GaN -> MDC -> Air physical parity. The old axis-z RCWA route remains trusted for air/stack/air 1D stacks, but this probe did not identify reliable upper/lower GaN/Air medium controls.

## Next

Use FMMAX only as a minimal single-dipole sanity/closure check, then use 2D FDTD for center/side incoherent averaging.
