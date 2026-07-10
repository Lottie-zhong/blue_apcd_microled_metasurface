# MDC blue native material reference library

Actual FSP read: `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`

Extraction was hidden-mode and read-only. No FDTD, GUI, FSP save, or FSP copy was performed.

## Materials
- SiO222 actual name: sio222
- tio22 actual name: tio22

## Native sampled data
The Lumerical `sampled data` property is a two-column complex-permittivity table `[frequency_hz, epsilon]`. `n + i k` is derived as the principal physical square root of complex epsilon.
- SiO222 (sio222): lambda_min=199.9745 nm; lambda_max=1033.2015 nm; sample_count=101
- tio22 (tio22): lambda_min=199.9745 nm; lambda_max=1033.2015 nm; sample_count=101

## 450 nm reference
- SiO222 (sio222): n=1.42617929; k=0
- tio22 (tio22): n=2.53729551; k=0

## Derived tables
- 300-1000 nm in 1 nm increments: exported only where the requested wavelength lies within the native range.
- 400-500 nm and 448-453 nm in 0.5 nm increments: same bounded interpolation rule.
- Interpolation is linear in real/imaginary epsilon on the native frequency axis. No native-range extrapolation is performed.

## Comparison and branch use
- Literature reference only: TiO2 n=2.25 @450 nm; SiO2 n=1.47 @450 nm. Use this FSP-derived material set as the APCD branch reference.
- LP smoke may remain object-defined dielectric plus `n_material`; center it at TiO2_reference.n_450 and retain a local index sweep.
- LP, MDC/TMM, and RCLED-MDC should reuse the unified config and native/derived CSVs emitted here.

No FDTD was run. No FSP or runtime configuration was modified.
