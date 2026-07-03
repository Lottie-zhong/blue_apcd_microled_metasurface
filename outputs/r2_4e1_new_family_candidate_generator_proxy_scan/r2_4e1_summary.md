# R2-4E1 New-Family Candidate Generator / Proxy Scan

This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.

Generated candidates: 396
Hard-pass proxy candidates: 15
Decision: **shortlist**

The proxy is an analytic/TMM-style screen for design-family triage. It is not a substitute for tri-point source-position FDTD.

## Top Candidates
| candidate_id | family_id | hard_pass | score | normal/offaxis | 30-40 penalty | TE/TM guard | spectral FWHM | angular FWHM |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E1_0236 | E0C_MQW_lateral_extent_robust_cavity | True | 3.301443 | 2.583981 | 0.277206 | 0.2426 | 7.81581 | 9.078843 |
| E1_0240 | E0C_MQW_lateral_extent_robust_cavity | True | 2.708222 | 2.303671 | 0.277206 | 0.2426 | 7.81581 | 9.616846 |
| E1_0272 | E0C_MQW_lateral_extent_robust_cavity | True | 2.621031 | 2.324177 | 0.291066 | 0.271754 | 7.6616 | 10.074163 |
| E1_0232 | E0C_MQW_lateral_extent_robust_cavity | True | 2.558222 | 2.303671 | 0.277206 | 0.2426 | 7.81581 | 9.616846 |
| E1_0260 | E0C_MQW_lateral_extent_robust_cavity | True | 2.500119 | 2.297924 | 0.263346 | 0.305113 | 7.97002 | 10.475523 |
| E1_0284 | E0C_MQW_lateral_extent_robust_cavity | True | 2.080604 | 2.117263 | 0.318786 | 0.284228 | 7.35318 | 10.868803 |
| E1_0276 | E0C_MQW_lateral_extent_robust_cavity | True | 2.071139 | 2.065531 | 0.291066 | 0.271754 | 7.6616 | 10.612166 |
| E1_0264 | E0C_MQW_lateral_extent_robust_cavity | True | 2.054314 | 2.072239 | 0.252054 | 0.300032 | 7.953081 | 11.013526 |

## Shortlist
- primary: E1_0236 / E0C_MQW_lateral_extent_robust_cavity -> tri-point x-dipole 453 nm only.
