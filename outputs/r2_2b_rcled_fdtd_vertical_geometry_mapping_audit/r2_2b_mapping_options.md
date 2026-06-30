# R2-2B Mapping Options

## Option A: literal spacer mapping

Use `cavity_span_nm` directly as the physical GaN cavity / effective spacer thickness in the first 2D FDTD smoke model. Place the MQW dipole plane at the cavity center unless a later device-specific MQW depth is supplied.

This option does not claim that TMM `cavity_span_nm` is the final physical cavity thickness. It is the safest first smoke mapping because it is reproducible, auditable, and changes only one intended geometry variable.

## Option B: optical phase mapping

Treat `cavity_span_nm` as an effective optical cavity length proxy. The physical GaN thickness may need adjustment because DBR penetration phase and termination phase are not explicit in the simple TMM candidate label.

This is more physically flexible but unsafe for the first smoke run because it adds an extra fitting degree of freedom before any FDTD evidence exists.

## Recommendation

Use Option A for the first R2-2 FDTD smoke validation. If FDTD peak wavelength or angular response is shifted, use the mismatch to calibrate an Option B optical-phase correction later.
