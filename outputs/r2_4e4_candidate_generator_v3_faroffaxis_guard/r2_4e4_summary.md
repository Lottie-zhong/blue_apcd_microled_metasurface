# R2-4E4 Candidate Generator V3 Far-Offaxis Guard

This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.

Generated candidates: 480
Hard-pass proxy candidates: 0
Decision: **no-pass**

E4 adds E3-derived 45-55 deg and 40-60 deg far-offaxis guards to avoid E1_0236-like false positives.

## Top Candidates
| candidate_id | family_id | hard_pass | score | normal/offaxis | 30-40 | 45-55 | 40-60 | FWHM |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E4_0006 | E0A_lower_Q_angle_stable_cavity | False | 7.711322 | 4.760051 | 0.085073 | 0.129367 | 0.12547 | 6.896265 |
| E4_0008 | E0A_lower_Q_angle_stable_cavity | False | 6.929944 | 4.278921 | 0.139095 | 0.114186 | 0.117239 | 6.821839 |
| E4_0015 | E0A_lower_Q_angle_stable_cavity | False | 6.225336 | 4.100997 | 0.092079 | 0.17763 | 0.15107 | 7.618289 |
| E4_0017 | E0A_lower_Q_angle_stable_cavity | False | 5.837398 | 3.814549 | 0.146101 | 0.157916 | 0.139959 | 7.426103 |
| E4_0009 | E0A_lower_Q_angle_stable_cavity | False | 5.811798 | 3.873527 | 0.079045 | 0.1718 | 0.153643 | 7.993027 |
| E4_0018 | E0A_lower_Q_angle_stable_cavity | False | 4.797322 | 3.453967 | 0.086051 | 0.22097 | 0.179969 | 8.741909 |
| E4_0024 | E0A_lower_Q_angle_stable_cavity | False | 4.751961 | 3.455598 | 0.085073 | 0.195856 | 0.16771 | 8.623412 |
| E4_0014 | E0A_lower_Q_angle_stable_cavity | False | 4.746358 | 3.417134 | 0.101725 | 0.199367 | 0.176404 | 8.488053 |

## No-Pass
No candidate satisfied every v3 hard guard; do not force FDTD from E4.
