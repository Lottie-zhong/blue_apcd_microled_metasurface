# APCD Native-M1 material display colors v1

## Method

- Display colors are visualization metadata only; optical policy remains version 5.
- No source FSP was loaded or saved. No solver was run during this audit.
- The existing blank-session readback evidence was reused; no Lumerical session was started for this freeze.

## Registration path

- The existing `apcd_native_materials.py` loader remains the sole sampled-data path.
- `register_lumerical_sampled_material` loads sampled frequency-epsilon data, registers `Sampled data`, sets the canonical name, then applies optional color.
- SiO2 intentionally receives no color override.

## Display policy

- `APCD_GAN_NATIVE_M1`: high-contrast blue `[0.05, 0.30, 0.95, 1.00]`.
- `APCD_TIO2_NATIVE_M1`: high-contrast yellow `[1.00, 0.82, 0.05, 1.00]`.
- `APCD_SIO2_NATIVE_M1`: unchanged.
- RGBA is normalized to `[0,1]`, alpha is `1.0`.

## Quantization-aware acceptance

- The former `1e-12` readback criterion was inappropriately strict for a quantized display-only property.
- Lumerical color channels are stored on a 16-bit discrete grid: step `1/65535`; maximum nearest-value rounding error `0.5/65535`; acceptance tolerance `0.5/65535 + 1e-12`.
- Requested RGBA policy values are unchanged. Readback is the nearest representable GUI color, not a material-precision loss.
- GaN observed maximum channel error `7.629510948348184e-06`: PASS. TiO2 observed maximum channel error `4.577706569031115e-06`: PASS.
- Overall status: `display_color_policy_pass_with_expected_api_quantization`.

## Optical invariance

- GaN sampled shape is `[500, 2]`; TiO2 and SiO2 are `[101, 2]`. All sampled-data hashes, epsilon, n/k values at 420/448/450/453/480 nm, material type, mesh order, and fitting metadata remain unchanged.
- Colors do not enter geometry hashes, optical hashes, ML features, or solver settings.

## Builder audit

- `build_mdc_p1_plane_wave_fdtd_static_v1.py`: `property_not_used`.
- `run_mdc_p1_plane_wave_fdtd_v1.py`: `property_not_used`.
- `extract_mdc_gan_native_m1_candidate_v1.py`: `inherits_material_database_color`.
- `promote_apcd_gan_native_m1_v1.py`: `property_not_used`.
- This freeze covers the unified display policy and registration helper only. The current plane-wave WIP does not call this helper; a future builder patch must call `register_lumerical_sampled_material(...)` and must not hard-code a separate color policy.

## Scope

- Color quantization affects GUI display only, not sampled optical data or the solver.
- No source FSP was modified.
