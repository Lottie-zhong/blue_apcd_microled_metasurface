# APCD native material handoff for MDC

- High-index layer: APCD_TIO2_NATIVE_M1 / tio22
- Low-index layer and SiO2 defect: APCD_SIO2_NATIVE_M1 / sio222
- Authority: `configs/material_reference_apcd_blue.yaml`; native data: `outputs/material_reference/mdc_blue_oujizi_m/material_ref_native_sampled.csv`.
- At 450 nm, quarter-wave estimates are TiO2 44.34 nm and SiO2 78.88 nm; SiO2 half-wave defect 157.76 nm. TMM/FDTD must use wavelength-dependent n+ik, not fixed indices.
