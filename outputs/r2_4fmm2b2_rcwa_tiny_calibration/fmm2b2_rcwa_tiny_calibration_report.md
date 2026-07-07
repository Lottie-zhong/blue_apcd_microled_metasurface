# FMM2B2 tiny RCWA calibration

## ????

stage = `FMM2B2`; previous_schema_commit = `1ea5369`.

?? case: air_reference, single_SiO2_proxy, single_TiO2_proxy, H1J4_like_bottom_DBR_QWinteger453_10pair_proxy.
??: 453.0 nm; ??: [0.0]; x-polarized plane-wave proxy????? x ? s/p ??????
??/??: TiO2 45.0 nm (n=2.4), SiO2 79.0 nm (n=1.45), DBR pair count=10.

| case | Rs | Ts | Rp | Tp | R_avg | T_avg | status |
|---|---:|---:|---:|---:|---:|---:|---|
| air_reference | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | ok |
| single_SiO2_proxy | 3.081487911019578e-33 | 1.0000000000000002 | 3.081487911019578e-33 | 1.0000000000000002 | 3.081487911019578e-33 | 1.0000000000000002 | ok |
| single_TiO2_proxy | 3.081487911019578e-33 | 1.0000000000000002 | 3.081487911019578e-33 | 1.0000000000000002 | 3.081487911019578e-33 | 1.0000000000000002 | ok |
| H1J4_like_bottom_DBR_QWinteger453_10pair_proxy | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | ok |

## Sanity notes

- reference should be near transparent: `True`.
- DBR-like stack should show stronger reflection than empty/single-layer proxy: `False`.
- decision: `rcwa_tiny_calibration_partial`.
- ??????? FDTD???????? H1J4 FSP??? sweep??? broadband??? APCD coupling??? push?
