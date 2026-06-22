# Stage13-7A LP Coordinate/Sign Bridge Validation

## Scope

- No FDTD was run. No FSP was opened, created, saved, or modified.
- Existing Stage12 order CSV/code and Stage13 far-field CSV/code were audited read-only.
- No +/-q, DBR/RCLED, geometry change, or optimization.

## Stage12 order/sign evidence

- `src/metasurface/apcd_diffraction.py::extract_fdtd_grating_orders` reads `gratingn(T)` and `gratingu1(T)` into aligned rows using the same array index.
- The existing Stage12 x-LP order CSV records order_n=+1 with ux=+0.173648177762 and order_n=-1 with ux=-0.173648177762.
- These ux values come directly from Lumerical `gratingu1`, not from a post-processing sign assumption.
- `stage12_k6_fdtd.expected_theta_deg` uses `asin(order * wavelength / period)`, not a leading-minus formula.
- The official Stage12 result calls +1/+ux +10 deg and reports +1 as the dominant x-LP order.

## Stage13 axis/code evidence

- Stage13 obtains `farfieldux` and `farfielduy` numerically and builds `meshgrid(uxa, uya, indexing="ij")`.
- If field shape requires it, xx and yy are transposed together; their signs are unchanged.
- Peak CSV values are read directly as `xx[index]` and `yy[index]`.
- PNGs use `pcolormesh(xx, yy, values)` with no `imshow`, origin override, `invert_xaxis`, negation, or axis reversal.
- The +target marker is plotted at `+TARGET_UX`; CSV integration and PNG plotting therefore share the same sign convention.

## Bridge decision

- Status: **`resolved_plus_order_maps_to_positive_ux`**.
- Stage12 +1/+x/+10 deg maps to Stage13 `ux=+0.173648177762`.
- Stage12 -1/-x/-10 deg maps to Stage13 `ux=-0.173648177762`.
- Sign-convention inconsistency detected: **false**.

## Stage13-5 interpretation update

- The actual designed target center is now resolved as `ux=+0.173648177762, uy=0`.
- center_x Ex global peak remains at ux=-0.33999999999999997, uy=-0.11999999999999995.
- Angular distance to +target: 30.736468 deg; to -target: 12.147832 deg.
- It is not within 3 deg of either expected order. `class_C_no_steering` remains unchanged.
- Existing incoherent LP fractions at the resolved +target center:

| cone half-angle (deg) | LP_fraction_incoherent |
| ---: | ---: |
| 3 | 0.592461399 |
| 5 | 0.579781089 |
| 10 | 0.543895214 |

- With phase ramp and tiling already clean, the leading diagnosis is local-dipole broad-angle/source-coupling mismatch, including the source-center bias toward the phase-180 J2 pillar.

## Single recommended next step

**Stage13-7C: run center_x only with an adjusted source-center or controlled source-coupling diagnostic.**

This recommendation is for a separately authorized future FDTD task. Do not run +/-q and do not add DBR/RCLED yet.

## Jones/APCD evidence boundary

- Stage12 order vectors exist, but this task does not reconstruct a new J_xy matrix or alpha/beta basis conversion.
- `t_{alpha*<-alpha}^order` is not newly evaluated or claimed. This task resolves coordinate sign only.
