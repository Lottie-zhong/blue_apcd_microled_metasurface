# R1C3 RCLED C2 baseline freeze package

Old m8 + bottomDBR99 / R1B route was rejected because it produced symmetric off-normal 20-30 degree lobes.
R1C0 TMM redesign found the top=6 bottom=0 family.
R1C1 validated top3 and selected C2.
R1C2 refined C2 and selected C2_cav230.

Primary baseline = R1C2_C2_cav230: top_pair_count=6, bottom_pair_count=0, cavity_span_nm=230, termination=TiO2_50nm.
Backup = R1C2_C2_base: top_pair_count=6, bottom_pair_count=0, cavity_span_nm=220, termination=TiO2_50nm.

| wl nm | eta10 | eta20 | eta30 | peak_abs deg | dominant zone |
|---:|---:|---:|---:|---:|---|
| 450 | 0.398 | 0.587 | 0.856 | 9.30 | abs_5_10 |
| 453 | 0.461 | 0.682 | 0.856 | 9.01 | abs_5_10 |
| 456 | 0.494 | 0.719 | 0.861 | 6.81 | abs_5_10 |

Source-y sweep is now allowed as a robustness test, not rescue. APCD integration has not yet run.
