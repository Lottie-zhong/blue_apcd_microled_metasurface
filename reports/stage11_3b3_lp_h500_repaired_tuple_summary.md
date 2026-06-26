# Stage11-3B3 H500 LP Repaired Tuple Search

## Boundary
- Analysis only. No FDTD, no Lumerical, no K=6/metagrating, no finite patch, no dipole, no DBR/RCLED.
- Data sources restricted to Stage11-3B1 and Stage11-3B2 CSV reports under reports/; outputs/ was not read.

## Answers
1. Repaired six-bin tuple using the 120 deg rescue: `False`. Best tuple `offset_060` uses 120 rescue in top candidates: `True`.
2. Can 0/60/180 frozen bins remain from this report-only evidence? `False`. Per-bin pass evidence: `{0: False, 60: False, 180: False}`.
3. Limiting bins/gates after relabeling: `Tx;candidate_gate;matrix_error;ratio;relative_phase;rms_phase`. 240/300 remain suspect because 3B2 showed low long-wavelength ratio/matrix margins.
4. Does global phase offset solve the issue? `False`. Best max relative phase error `75.013858`, RMS `37.963695`.
5. Recommended Stage11-3B4: expand 240/300 candidate search; current report-only pool cannot prove a robust six-bin tuple.

## Best Tuple
| mode | offset | min_ratio | min_Tx | max_matrix | max_rel_phase_err | rms_rel_phase_err | pass | failed_gates |
|---|---:|---:|---:|---:|---:|---:|---|---|
| global_offset_relabel | 60.000000 | 3.523155 | 0.391807 | 0.532763 | 75.013858 | 37.963695 | false | ratio;Tx;matrix_error;relative_phase;rms_phase;candidate_gate |

## Fixed-label Tuple
- tuple_pass_flag: ``; failed_gates: ``.
