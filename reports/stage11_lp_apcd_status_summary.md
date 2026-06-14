# Stage11 LP-APCD Status Summary

## Scope

Project branch: Blue-10K6 APCD-ML-RCWA LP-APCD experimental-friendly branch.

Frozen baseline:

- wavelength_nm = 450
- steering_angle_deg = +10
- K_dimers_per_supercell = 6
- dimer_pitch_x_nm = 431.907786
- period_y_nm = 432
- phase_states_deg = [0, 60, 120, 180, 240, 300]

K means dimer count, not nanopillar count.

## Stage11-1E Static Library

Stage11-1E formed a H500-only same-height strong static Jones/phasor library for all six phase bins:

| bin_deg | pair_id | predicted_ratio | phase_error_deg |
|---:|---|---:|---:|
| 0 | LPPAIR1E_H500_014392 | 1986.999406 | 7.699474 |
| 60 | LPPAIR1E_H500_009200 | 8.427811 | 2.521312 |
| 120 | LPPAIR1E_H500_015319 | 7.161645 | 3.639046 |
| 180 | LPPAIR1E_H500_013279 | 1649.258041 | 6.690256 |
| 240 | LPPAIR1E_H500_007210 | 308.460144 | 7.856951 |
| 300 | LPPAIR1E_H500_007734 | 64.608193 | 6.545086 |

This is single-pillar Jones/phasor static pairing only. It is not dimer verified and is not K=6 steering.

## Stage11-2A Dimer Validation

Stage11-2A generated a H500 dimer validation plan with 12 legal cases covering all six bins. Real H500 dimer FDTD was run for x-LP and y-LP normal incidence only.

Result:

- dimer FDTD success = 12
- dimer FDTD failed = 0
- dimer_pass_loose = 0
- dimer_pass_strict = 0

Best dimer status by bin:

| bin_deg | best_case | selectivity | target_x_power | phase_error_vs_static | status |
|---:|---|---:|---:|---:|---|
| 0 | H500DIMER2A_001_B0_y_pair | 548.902141 | 0.324590 | 33.537054 | static_only_failed_dimer |
| 60 | H500DIMER2A_003_B60_y_pair | 258.742386 | 0.930182 | 58.904570 | static_only_failed_dimer |
| 120 | H500DIMER2A_006_B120_y_pair | 1.409862 | 0.992409 | 21.133526 | static_only_failed_dimer |
| 180 | H500DIMER2A_007_B180_y_pair | 0.654288 | 0.656673 | 97.413281 | static_only_failed_dimer |
| 240 | H500DIMER2A_010_B240_y_pair | 1.517707 | 0.098597 | 28.255419 | static_only_failed_dimer |
| 300 | H500DIMER2A_011_B300_y_pair | 0.538864 | 0.434639 | 17.820203 | static_only_failed_dimer |

Diagnosis:

- 0 and 60 preserve high selectivity but coupling shifts the output phase too far from static predictions.
- 120, 180, 240, and 300 show poor dimer selectivity and/or phase transfer.
- The H500 static model does not directly transfer to the tested single-dimer geometries.

## Evidence Boundary

This code sync intentionally excludes FDTD project files, monitor dumps, far-field dumps, logs, and large outputs.

K=6 full FDTD, phase-gradient supercell simulation, and LP steering validation are not complete.
