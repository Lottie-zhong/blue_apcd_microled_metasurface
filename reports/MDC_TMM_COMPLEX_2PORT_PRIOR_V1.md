# MDC_TMM_COMPLEX_2PORT_PRIOR_V1

## STATUS

`PASS` — deterministic two-port, plane-wave TMM prior built and frozen with TMM evaluation only. No FDTD solver, DOE96 rewrite, V3-C retraining, 3D dataset generation, or dipole-profile acceptance test was used.

## SOURCE AUTHORITY

- Worktree: `D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2`
- Branch at generation: `work/mdc-hf-surrogate-v2`
- Audited base: `8d1380355ae2c5548d7f0c66a783b413982c8a7c`
- Code commit containing the provider and tests: `4d15546ce2cdbbd42055e6cd5b87c96678494d15`
- Fixed MDC: `P1_ZL1_ALTERNATIVE_G3_A3` / ZL-1 alternative.
- Coupling authority: `contracts/coupling/interface_stack_v1.json`, contract `APCD_MDC_NP_ONE_WAY_POWER_INTERFACE_V1`.
- Coupling stack: GaN → fixed MDC → 237 nm extra `APCD_SIO2_NATIVE_M1` spacer → K6 NP → Air.
- Right spacer-side medium: `APCD_SIO2_NATIVE_M1`, not air. Total SiO₂ separation is 316 nm (79 nm MDC termination + 237 nm extra spacer).

The authoritative coupling worktree was read only at its frozen contract; it was not modified.

## PORT MEDIA

| port | medium | role |
|---|---|---|
| Left | `APCD_GAN_NATIVE_M1` | incident side |
| Right | `APCD_SIO2_NATIVE_M1` | actual coupling spacer side |

The MDC layer sequence is the frozen 975 nm stack from the GaN/MDC interface upward:

`TiO2:44 / SiO2:79 / TiO2:44 / SiO2:79 / TiO2:44 / SiO2:316 / TiO2:44 / SiO2:79 / TiO2:44 / SiO2:79 / TiO2:44 / SiO2:79 nm`.

## TMM CONVENTIONS

- Native-M1 material dispersion: linear complex-ε interpolation on the frequency axis; extrapolation forbidden.
- Wavelength: vacuum wavelength in nm.
- V1 angle: normal incidence, θ = 0°, conserved `kx/k0 = 0`.
- Polarization: E-field TE/TM basis; the current P_XLIKE normal-incidence state is represented by the exactly degenerate TE/TM response.
- Field amplitudes: electric-field basis, not power-normalized amplitudes.
- Power: `R = |r|²`; `T = |t|² Re(n_out)/Re(n_in)`.
- Time/propagation convention: `exp(-iωt)` with forward `exp(+ikz)` and passive `Im(n) ≥ 0`; the existing physical TMM matrix sign is retained.
- The JSON stores real/imaginary parts, magnitude, phase, R/T and direction-specific diagnostics for both directions.

The normal-incidence TE/TM check is exact in the frozen E/H implementation (`max_abs_difference = 0`). It is recorded explicitly rather than inferred from a label.

## TWO-PORT COMPLEX RESPONSE

The machine-readable artifact is:

`reports/MDC_TMM_COMPLEX_2PORT_PRIOR_V1.json`

It contains 21 rows at 440–460 nm in 1 nm steps. Each row contains:

`r_L`, `t_LR`, `r_R`, `t_RL` as Re/Im plus magnitude/phase, and `R_L`, `T_LR`, `R_R`, `T_RL`.

At 450 nm, as an audit sample:

| quantity | value |
|---|---:|
| `r_L` | `0.2460938464 - 0.0893222077i` |
| `t_LR` | `-0.1075997792 - 1.2470679306i` |
| `r_R` | `0.2662065620 + 0.0709316237i` |
| `t_RL` | `-0.0891238252 - 0.7333305947i` |
| `R_L` / `T_LR` | `0.0685406380` / `0.9252273653` |
| `R_R` / `T_RL` | `0.0758972289` / `0.9241027711` |

The displayed complex values are the 450 nm audit sample; real and imaginary components are stored separately in JSON. The two reflection amplitudes are not equated. Reciprocity is used only as the verified E-field relation `n_R t_LR = n_L t_RL`, with maximum residual `7.45e-16` on the evaluated grid.

## POWER CONSISTENCY

The MDC layers are lossless within numerical tolerance (`A_stack` across both directions is within approximately `8e-16` of zero). The GaN incident port is Native-M1 and has nonzero loss; therefore `R+T` is a diagnostic, not a closure identity for left incidence. Across the grid:

- left `R+T`: 0.9600955590–1.0443740579;
- right `R+T`: 0.999999999999999–1.000000000000000;
- physical `power_entering - T - A_stack` maximum absolute residual: 0;
- no `|t|²`-only transmitted-power shortcut is used.

## REFERENCE PLANES

- Left reference plane: GaN/MDC first-layer interface, z = 0 nm.
- Right reference plane: MDC top / entrance to the extra SiO₂ spacer, z = 975 nm.
- Included thickness: MDC only, 975 nm.
- Excluded thickness: extra SiO₂ spacer, 237 nm.
- Phase origin: left reference plane.
- Compositor rule: append `exp(+ikz_spacer d)` exactly once for the 237 nm spacer; no hidden double-counting is present in this prior.

## 440–460 NM PRIOR

The grid is fixed at λ = 440, 441, …, 460 nm, θ = 0°, P_XLIKE-compatible normal incidence. The full row table, provenance, material metadata, convention fields and hashes are in the JSON artifact; no broader angular grid was introduced.

## TMM VS DIPOLAR DOE96 SEMANTICS

`TMM_vs_DOE96_DIPOLAR_PROFILE = NOT_DIRECTLY_COMPARABLE`.

The TMM artifact is a plane-wave layered-stack transfer prior. DOE96 is dipole-emission data with source position/orientation and angular profile semantics. Dipole-profile FWHM, angular widths or V3-C normalized profiles were not used as TMM acceptance criteria. Historical resonance-position comparisons may be informative only and are not a hard complex-prior gate.

## CURRENT COUPLING ROLE

For the current fixed-MDC 20G/32G coupling dataset, this prior is identical across K6 geometries at a given wavelength/source condition. It therefore does not provide K6 geometry discrimination. Its allowed role is:

- spectral amplitude conditioning;
- phase conditioning;
- cavity/reference response;
- composition with the frozen spacer and NP;
- future residual-model baseline.

It is not an absolute-power, LEE, Level-1 truth or full-device surrogate.

## V3-C ROLE

`MDC_V3_C_DIPOLE_PROFILE_ROLE` is frozen separately as a dipole spectral-angular profile prior and emitter-conditioning diagnostic. It is `DIPOLE_PROFILE_AUXILIARY_ONLY`: not plane-wave complex t/r and not a current plane-wave `C_component` input.

## FUTURE COMPONENT-COMPOSITOR INTERFACE

Define the future interface as:

`MDC two-port S(λ,kx,pol) + spacer propagation exp(+ikz d) + NP complex scattering state → C_component`.

The compositor must support full two-port multiple-reflection composition. A single-pass product is not assumed sufficient. This task only freezes the MDC prior; it does not train a residual model or execute coupling evaluation.

## ARTIFACT HASHES

Before the final artifact commit, the generated file hashes are:

- `MDC_TMM_COMPLEX_2PORT_PRIOR_V1.json`: `B8E856FED0C7859B6CE3D1AA7D40549F40720B0C317B6F3DBF362E62C7E37A38`.
- `scripts/mdc_tmm_complex_2port_prior_v1.py`: `A7D618B697A71ED59BF8B56D9D5239B570F0CB03F9F650497FA49CE37A5A6A00`.
- `tests/test_mdc_tmm_complex_2port_prior_v1.py`: `A0258799C11AF85BD639919DC7C83F7C4EB1B2B90D47CA194F277F34DC41D67C`.

The report hash is finalized after this text is written. The JSON itself records the coupling interface/coordinate contract hashes, Native-M1 metadata, source code path and generation commit.

## GIT

- Provider/tests commit: `4d15546ce2cdbbd42055e6cd5b87c96678494d15`.
- Artifact/report commit: added after JSON generation with explicit path allowlist only.
- No FSP, checkpoint, raw array, cache, credential or solver log is staged.

## NEXT

`HANDOFF_MDC_TMM_COMPLEX_PRIOR_TO_COUPLING`.

Do not execute the handoff’s residual training or any new solver from this task.
