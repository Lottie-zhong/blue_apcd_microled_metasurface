# MDC Native-M1 2D dipole device comparison v1

Stage status: `native_m1_2d_dipole_device_closure_pass`.

- Main candidate device closure: `PASS`.
- Wan proxy unweighted FWHM: `window_truncated` because its left half-maximum is below 420 nm; no extrapolation was used.
- Preferred candidate: `ZL-1 alternative`.
- Decision label: `alternative_best_angle_power_tradeoff`.

## Preferred candidate

|metric|ZL-1 alternative|
|---|---:|
|R12-normalized output spectral FWHM|18.7821 nm|
|450 nm in-plane angular FWHM|23.5924 deg|
|output peak|447.8 nm, near-normal symmetric peak|
|28 nm benchmark weighted FWHM|13.2613 nm|
|450 nm cone10|0.632357|
|integrated R12-normalized power|0.5631879|

ZL-1 nominal remains the stable narrow-angle control, Explicit the traditional defect baseline, Wan the `wan_mdc_engineering_proxy`, and Bare the no-stack emission reference.

## Comparison

Relative to nominal, the alternative reduces angular FWHM by 1.44243 deg and R12-normalized output spectral FWHM by 0.240644 nm while increasing integrated R12 power by about 2.06%. No additional directional-power penalty is observed.

Relative to Wan, the alternative has narrower 450 nm angular and 28 nm benchmark-weighted FWHM, but its integrated R12 power is about 71.1% of Wan. Directional and spectral gains are supported; throughput advantage is not.

Relative to Bare, directionality improves substantially while integrated R12 power decreases. This is not called an absolute extraction-efficiency loss.

## R12 physical definition

- Source-local mesh: 1 nm.
- Box half-size: 12 nm.
- Four-side direct outward Poynting integration.
- Field: `near_source_outward_flux_r12nm`.
- Method: `fixed_physical_r12nm_box`.

It is not exact total emitted power, absolute extraction efficiency, or zero-radius emitted power. The earlier zero-radius/r8 failure evidence remains preserved in the frozen CSV and 440-460 report.

## Strict FWHM separation

|physical aperture|Explicit|ZL-1 nominal|ZL-1 alternative|Wan proxy|
|---|---:|---:|---:|---:|
|Native-M1 plane-wave TMM|7.4 nm|3.3 nm|3.3 nm|n/a|
|Native-M1 dipole-FDTD R12-normalized output|19.9312 nm|19.0227 nm|18.7821 nm|window truncated|
|28 nm Gaussian benchmark weighted output|13.0310 nm|13.2869 nm|13.2613 nm|18.7161 nm|

These three FWHM families are not interchangeable.

## Evidence boundary

The complete 420-480 evidence and ML labels are in the final device manifest. Runtime FSP, NPZ, solver logs, checkpoints, and overnight state are excluded from Git. This freeze performed postprocessing and audit only; no solver was started.
