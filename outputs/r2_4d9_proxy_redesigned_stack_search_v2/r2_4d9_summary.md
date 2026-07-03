# R2-4D9 Proxy-Redesigned Stack Search V2

This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 outputs.

## Decision
Decision: **no-pass**.

D9 does not declare a physical pass. It only decides whether any existing stack/design-family candidate is justified for a later low-cost tri-point FDTD guard.

## D8 Rule Applied
D8 showed that center-only near-normal emission can be a false positive for the x-line source-position ensemble. The D9 score therefore penalizes source-position risk, edge sensitivity, 30-40 deg lobes, TE/TM off-axis risk, and center-vs-xline mismatch.

## Top Scored Candidates
| candidate_id | hard_pass | score | hard_fail_reasons |
|---|---:|---:|---|
| R2_4D2_OPT_13003 | False | -0.0484 | center_only_false_positive_risk_high |
| R2_4D2_OPT_08802 | False | -0.5512 | center_only_false_positive_risk_high |
| D5_BASE_11399 | False | -0.8800 | 30_40_lobe_penalty_high |
| D5_BASE_14742 | False | -0.8800 | 30_40_lobe_penalty_high |
| D5_BASE_08114 | False | -0.8800 | 30_40_lobe_penalty_high |
| D5_BASE_08535 | False | -0.8800 | 30_40_lobe_penalty_high |

## Shortlist Rule
No candidate may enter the shortlist from center/normal proxy alone. The shortlist also requires low TE/TM off-axis risk, low 30-40 deg lobe penalty, normal/off-axis proxy above 1, and no high center-vs-xline mismatch risk.

## No-Pass Outcome
No candidate satisfied the conservative D8-derived hard guards. The next route should redesign the stack/design family or run limited FDTD-in-loop only after a stronger Python-only proxy is available.
