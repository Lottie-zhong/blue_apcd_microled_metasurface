# R1C4 RCLED C2 cav230 source-y robustness

2D FDTD source-y robustness for frozen R1C2_C2_cav230. No forbidden integration, no bottom DBR, no cavity/termination sweep.

Center source remains best: `True`.
Source-y robustness passes all offsets: `False`.
Worst source_y_offset_nm: `-40.0`.
Best robust source_y_offset_nm: `0.0`.
Ready for later coupling: `False`.
Integration with downstream metasurfaces has not been run.

| source_y_offset_nm | wl | eta10 | eta20 | eta30 | peak_abs | zone | near | P_total |
|---:|---:|---:|---:|---:|---:|---|---|---:|
| -40 | 450 | 0.2685 | 0.5026 | 0.6937 | 25.51 | abs_10_20 | False | 0.0011917 |
| -40 | 453 | 0.4255 | 0.6248 | 0.7987 | 9.41 | abs_5_10 | True | 0.000890261 |
| -40 | 456 | 0.4244 | 0.6911 | 0.7906 | 16.30 | abs_10_20 | False | 0.000694006 |
| -20 | 450 | 0.4438 | 0.6069 | 0.9061 | 9.01 | abs_5_10 | True | 0.000982768 |
| -20 | 453 | 0.4818 | 0.7084 | 0.8660 | 7.27 | abs_5_10 | True | 0.000928446 |
| -20 | 456 | 0.4386 | 0.6696 | 0.7937 | 6.75 | abs_5_10 | True | 0.000837415 |
| 0 | 450 | 0.3985 | 0.5866 | 0.8564 | 9.30 | abs_5_10 | True | 0.00342026 |
| 0 | 453 | 0.4607 | 0.6817 | 0.8557 | 9.01 | abs_5_10 | True | 0.00242099 |
| 0 | 456 | 0.4942 | 0.7190 | 0.8612 | 6.81 | abs_5_10 | True | 0.00155919 |
| 20 | 450 | 0.3515 | 0.5562 | 0.7941 | 9.36 | abs_20_30 | True | 0.00509383 |
| 20 | 453 | 0.4407 | 0.6505 | 0.8374 | 9.30 | abs_5_10 | True | 0.00294808 |
| 20 | 456 | 0.5064 | 0.7319 | 0.8801 | 8.78 | abs_5_10 | True | 0.00157719 |
| 40 | 450 | 0.2953 | 0.5241 | 0.7139 | 9.36 | abs_10_20 | True | 0.00350704 |
| 40 | 453 | 0.4136 | 0.6125 | 0.8095 | 9.41 | abs_5_10 | True | 0.00148517 |
| 40 | 456 | 0.4668 | 0.7005 | 0.8364 | 9.30 | abs_5_10 | True | 0.000729727 |
