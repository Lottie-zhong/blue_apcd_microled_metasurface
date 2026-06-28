# R1C2 RCLED C2 focused refinement

2D FDTD focused refinement around R1C1 C2 only. No APCD/B4INT/CP/LP/finite patch/3D/source-y sweep/bottom DBR.

Best robust candidate: `C2_cav230` cavity `230.0` nm termination `TiO2_50nm`.
C2_base remains best: `False`.
450/453/456 robust by peak<=15 and zone abs_0_20: `True`.
Source-y sweep allowed: `True`.
Freeze as RCLED source-module baseline: `True`.

| candidate | wl | eta10 | eta20 | eta30 | peak_abs | zone | near | P_total |
|---|---:|---:|---:|---:|---:|---|---|---:|
| C2_base | 450 | 0.4233 | 0.6340 | 0.8885 | 9.18 | abs_5_10 | True | 0.00254832 |
| C2_base | 453 | 0.4655 | 0.6901 | 0.8341 | 6.92 | abs_5_10 | True | 0.00166573 |
| C2_base | 456 | 0.4686 | 0.6553 | 0.7889 | 7.27 | abs_5_10 | True | 0.00126629 |
| C2_cav210 | 450 | 0.4132 | 0.6075 | 0.8187 | 7.33 | abs_5_10 | True | 0.00183274 |
| C2_cav210 | 453 | 0.4197 | 0.6013 | 0.7523 | 7.39 | abs_5_10 | True | 0.00197507 |
| C2_cav210 | 456 | 0.4326 | 0.6852 | 0.8074 | 16.12 | abs_10_20 | False | 0.00165397 |
| C2_cav230 | 450 | 0.3985 | 0.5866 | 0.8564 | 9.30 | abs_5_10 | True | 0.00342026 |
| C2_cav230 | 453 | 0.4607 | 0.6817 | 0.8557 | 9.01 | abs_5_10 | True | 0.00242099 |
| C2_cav230 | 456 | 0.4942 | 0.7190 | 0.8612 | 6.81 | abs_5_10 | True | 0.00155919 |
| C2_TiO2_40 | 450 | 0.3350 | 0.4490 | 0.6633 | 8.08 | abs_5_10 | True | 0.00202103 |
| C2_TiO2_40 | 453 | 0.4136 | 0.5961 | 0.7320 | 7.04 | abs_5_10 | True | 0.00217059 |
| C2_TiO2_40 | 456 | 0.4444 | 0.7213 | 0.8123 | 16.00 | abs_10_20 | False | 0.0015012 |
| C2_TiO2_60 | 450 | 0.3562 | 0.5720 | 0.8112 | 9.36 | abs_20_30 | True | 0.00408804 |
| C2_TiO2_60 | 453 | 0.3882 | 0.5564 | 0.7769 | 9.24 | abs_5_10 | True | 0.00490651 |
| C2_TiO2_60 | 456 | 0.4576 | 0.6606 | 0.8211 | 7.44 | abs_5_10 | True | 0.00166974 |
