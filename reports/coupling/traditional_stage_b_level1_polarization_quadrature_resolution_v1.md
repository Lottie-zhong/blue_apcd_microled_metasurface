# Traditional Stage-B Level-1 polarization, quadrature and factorisation resolution

Status: `USER_DECISION_REQUIRED_LEVEL1_POLARIZATION_SCOPE`

## MDC polarization basis

- The authoritative setup and read-only FSP metadata show `dimension=2D`, solver x-y coordinates, solver z invariant, source position on solver y, and upward propagation toward +y.
- Project coordinates map solver x -> project x, solver y -> project z, solver z -> project y invariant. Therefore project propagation is `k=(kx,0,kz)` while the Lumerical solver sees `(kx,ky,0)`.
- `theta=90 deg, phi=0` is the solver-x source used by the x case: P/TM-like family `(Ex,Ey,Hz)` in solver coordinates.
- `theta=0 deg, phi=0` is the solver-z invariant source used by the z case: S/TE-like family `(Ez,Hx,Hy)` in solver coordinates.
- The six frozen top/centroid/bottom x/z cases therefore contain independent P and S families. The source z position is vertical project-z position; the z source orientation is solver-z/project-y invariant. These are different fields.
- Existing field-component readback is not available in the legacy FSP assets; the classification is resolved by the exact setup plus analytic 2D Maxwell decoupling, not by a guessed label.

## Quadrature / ux

- The fixed-v2 authoritative native profile is raw `farfield2d(upward_monitor, wavelength_index)` intensity with shape `301 x 2000`, axis order `[wavelength_index, angle_index]`.
- Wavelength grid: 420--480 nm, 301 points, 0.2 nm spacing. Native angle grid: -90--90 deg, 2000 nonuniform points, converted to radians before integration.
- Raw aggregation is x/z average at each position, then three-position average; no case normalization occurs before aggregation.
- Normalization is `Z=trapz_lambda(trapz_theta(raw_joint,theta_rad),lambda_nm)` and `W_theta=raw_joint/Z`. The observed normalized integral is `0.9999999999999999`.
- Theta-to-ux is a conservative monotonic remap with `u_x=sin(theta_rad)`, inverse-sine overlap, no extrapolation, no negative weights, and explicit mass/marginal closure tests. Native support is `[-1,1]`; the exact ZL1 relevant support must be derived after the formal ZL1 profile exists.

## Interface / NP factorisation

- MDC ends at project z=975 nm; NP starts at pillar bottom project z=1212 nm.
- The 237 nm homogeneous Native-M1 SiO2 region is an interface propagation operator, not part of the MDC provider and not part of the NP scattering provider.
- Native SiO2 data are lossless over the frozen 445--455 nm material bracket (`k=0` in the native samples), so the Level-1 propagating-channel power factor is 1; the coherent phase operator is retained only for a field-level extension.
- Standalone SiO2 -> RUN3A -> Air is valid as a one-way NP scattering operator at the pillar-bottom reference plane. Current NP coverage remains partial: P/X-like at `u_x=0`, exact 445--455 nm only.
- Stage-A's integrated 110-row matrix remains validation/reference data and is not an NP eta provider.

## Solver implications / Git

- No solver was run. Minimum future MDC input remains six formal real 2D FDTD cases.
- Option A (`TRADITIONAL_LEVEL1_P_TM_ONLY`) and Option B (`TRADITIONAL_LEVEL1_FULL_P_S_SOURCE_SCOPE_EXTENSION`) are both frozen without selecting either. NP state counts remain conditional on the exact remapped ZL1 support; no NP grid was invented.
- Contracts: `MDC_INTERFACE_POLARIZATION_BASIS_V1`, `MDC_LEVEL1_QUADRATURE_SEMANTICS_V1`, `MDC_THETA_TO_UX_CONSERVATIVE_REMAP_V1`, `LEVEL1_INTERFACE_PROPAGATION_V1`, `LEVEL1_NP_SCATTERING_OPERATOR_V1`, `MDC_LEVEL1_POWER_PROFILE_FACTORISATION_V1`.
- This report's source audit is read-only; source worktree writes, FDTD, TMM, RCWA, FEM, training and ML inference entries are all zero.
