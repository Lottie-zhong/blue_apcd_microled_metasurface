# LP-ML1A4 Explicit Geometry Seed Plan

Purpose: create a new explicit numeric geometry seed generator for LP-APCD dimer ML.

LP-ML1B was blocked after A2/A3 because old LP-Hnew source rows had no recoverable numeric dimer geometry and LP-ML1A was default-range-only scaffold data.
A4 creates new explicit geometry instead of more history archaeology because the historical search found zero run-ready rows.

Total generated final candidates: 600
Total rejected geometry attempts: 3690

## Counts by sampling_group
```json
{
  "B240_exploration": 160,
  "B300_exploration": 220,
  "global_escape_lhs": 100,
  "sixbin_balance": 120
}
```
## Counts by target_bin_deg
```json
{
  "0": 32,
  "120": 32,
  "180": 32,
  "240": 206,
  "300": 266,
  "60": 32
}
```
## Counts by H_nm
```json
{
  "500": 253,
  "600": 228,
  "650": 99,
  "700": 20
}
```
## Counts by sampling_family
```json
{
  "B240_dx_sweep": 34,
  "B240_global_mixed": 44,
  "B240_moderate_asymmetry": 37,
  "B240_theta_sweep": 45,
  "B300_asymmetric_length": 67,
  "B300_dx_sweep": 48,
  "B300_global_mixed": 55,
  "B300_theta_contrast": 50,
  "global_lhs_mixed": 100,
  "sixbin_moderate_mixed": 120
}
```
## Geometry range summary
L: 100-250 nm; W: 60-150 nm; theta: 0-180 deg modulo; center_dx: 120-230 nm; period: 431.907786 nm.

## Top 20 priority candidates
| candidate_id | target_bin_deg | sampling_group | sampling_family | H_nm | L1_nm | W1_nm | L2_nm | W2_nm | center_dx_nm | priority_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | B300_exploration | B300_theta_contrast | 600 | 170.0 | 80.0 | 140.0 | 100.0 | 190.0 | 415.0 |
| LPML1A4_0049_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 150.0 | 110.0 | 110.0 | 70.0 | 200.0 | 415.0 |
| LPML1A4_0093_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 230.0 | 70.0 | 160.0 | 80.0 | 220.0 | 415.0 |
| LPML1A4_0157_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 140.0 | 80.0 | 100.0 | 70.0 | 220.0 | 415.0 |
| LPML1A4_0178_B300_exploration_B300_H650 | 300 | B300_exploration | B300_dx_sweep | 650 | 170.0 | 130.0 | 110.0 | 90.0 | 200.0 | 415.0 |
| LPML1A4_0196_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 130.0 | 70.0 | 100.0 | 70.0 | 180.0 | 415.0 |
| LPML1A4_0217_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 150.0 | 130.0 | 130.0 | 90.0 | 210.0 | 415.0 |
| LPML1A4_0098_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 130.0 | 80.0 | 180.0 | 80.0 | 220.0 | 414.625 |
| LPML1A4_0163_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 210.0 | 60.0 | 160.0 | 90.0 | 180.0 | 414.0 |
| LPML1A4_0188_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 210.0 | 130.0 | 170.0 | 60.0 | 210.0 | 414.0 |
| LPML1A4_0009_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 190.0 | 90.0 | 240.0 | 90.0 | 200.0 | 413.333 |
| LPML1A4_0025_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 170.0 | 80.0 | 110.0 | 90.0 | 200.0 | 413.333 |
| LPML1A4_0031_B300_exploration_B300_H600 | 300 | B300_exploration | B300_asymmetric_length | 600 | 200.0 | 110.0 | 150.0 | 80.0 | 180.0 | 413.333 |
| LPML1A4_0032_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 180.0 | 70.0 | 110.0 | 90.0 | 200.0 | 413.333 |
| LPML1A4_0040_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 140.0 | 70.0 | 160.0 | 90.0 | 210.0 | 413.333 |
| LPML1A4_0050_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 120.0 | 80.0 | 210.0 | 120.0 | 180.0 | 413.333 |
| LPML1A4_0053_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 140.0 | 70.0 | 100.0 | 80.0 | 220.0 | 413.333 |
| LPML1A4_0063_B300_exploration_B300_H650 | 300 | B300_exploration | B300_dx_sweep | 650 | 160.0 | 100.0 | 150.0 | 100.0 | 220.0 | 413.333 |
| LPML1A4_0070_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 130.0 | 90.0 | 130.0 | 90.0 | 170.0 | 413.333 |
| LPML1A4_0074_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 110.0 | 90.0 | 190.0 | 90.0 | 190.0 | 413.333 |

## 36-row pilot recommendation summary
| pilot_rank | candidate_id | target_bin_deg | sampling_group | sampling_family | H_nm | L1_nm | W1_nm | L2_nm | W2_nm | center_dx_nm | priority_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | LPML1A4_0028_B300_exploration_B300_H600 | 300 | B300_exploration | B300_theta_contrast | 600 | 170.0 | 80.0 | 140.0 | 100.0 | 190.0 | 415.0 |
| 2 | LPML1A4_0049_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 150.0 | 110.0 | 110.0 | 70.0 | 200.0 | 415.0 |
| 3 | LPML1A4_0093_B300_exploration_B300_H500 | 300 | B300_exploration | B300_dx_sweep | 500 | 230.0 | 70.0 | 160.0 | 80.0 | 220.0 | 415.0 |
| 4 | LPML1A4_0157_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 140.0 | 80.0 | 100.0 | 70.0 | 220.0 | 415.0 |
| 5 | LPML1A4_0178_B300_exploration_B300_H650 | 300 | B300_exploration | B300_dx_sweep | 650 | 170.0 | 130.0 | 110.0 | 90.0 | 200.0 | 415.0 |
| 6 | LPML1A4_0196_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 130.0 | 70.0 | 100.0 | 70.0 | 180.0 | 415.0 |
| 7 | LPML1A4_0217_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 150.0 | 130.0 | 130.0 | 90.0 | 210.0 | 415.0 |
| 8 | LPML1A4_0098_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 130.0 | 80.0 | 180.0 | 80.0 | 220.0 | 414.625 |
| 9 | LPML1A4_0163_B300_exploration_B300_H500 | 300 | B300_exploration | B300_asymmetric_length | 500 | 210.0 | 60.0 | 160.0 | 90.0 | 180.0 | 414.0 |
| 10 | LPML1A4_0188_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 210.0 | 130.0 | 170.0 | 60.0 | 210.0 | 414.0 |
| 11 | LPML1A4_0009_B300_exploration_B300_H650 | 300 | B300_exploration | B300_global_mixed | 650 | 190.0 | 90.0 | 240.0 | 90.0 | 200.0 | 413.333 |
| 12 | LPML1A4_0025_B300_exploration_B300_H500 | 300 | B300_exploration | B300_global_mixed | 500 | 170.0 | 80.0 | 110.0 | 90.0 | 200.0 | 413.333 |
| 13 | LPML1A4_0060_B300_exploration_B300_H700 | 300 | B300_exploration | B300_theta_contrast | 700 | 190.0 | 120.0 | 170.0 | 90.0 | 200.0 | 410.0 |
| 14 | LPML1A4_0234_B240_exploration_B240_H600 | 240 | B240_exploration | B240_global_mixed | 600 | 120.0 | 80.0 | 120.0 | 80.0 | 150.0 | 313.889 |
| 15 | LPML1A4_0239_B240_exploration_B240_H600 | 240 | B240_exploration | B240_global_mixed | 600 | 140.0 | 120.0 | 120.0 | 80.0 | 180.0 | 313.889 |
| 16 | LPML1A4_0245_B240_exploration_B240_H600 | 240 | B240_exploration | B240_moderate_asymmetry | 600 | 110.0 | 80.0 | 190.0 | 130.0 | 210.0 | 313.889 |
| 17 | LPML1A4_0254_B240_exploration_B240_H500 | 240 | B240_exploration | B240_moderate_asymmetry | 500 | 130.0 | 90.0 | 130.0 | 90.0 | 180.0 | 313.889 |
| 18 | LPML1A4_0262_B240_exploration_B240_H600 | 240 | B240_exploration | B240_moderate_asymmetry | 600 | 230.0 | 110.0 | 130.0 | 90.0 | 210.0 | 313.889 |
| 19 | LPML1A4_0270_B240_exploration_B240_H600 | 240 | B240_exploration | B240_global_mixed | 600 | 140.0 | 80.0 | 180.0 | 100.0 | 220.0 | 313.889 |
| 20 | LPML1A4_0279_B240_exploration_B240_H500 | 240 | B240_exploration | B240_dx_sweep | 500 | 120.0 | 80.0 | 140.0 | 110.0 | 220.0 | 313.889 |
| 21 | LPML1A4_0283_B240_exploration_B240_H650 | 240 | B240_exploration | B240_dx_sweep | 650 | 210.0 | 150.0 | 120.0 | 100.0 | 210.0 | 313.889 |
| 22 | LPML1A4_0511_global_escape_lhs_B120_H500 | 120 | global_escape_lhs | global_lhs_mixed | 500 | 120.0 | 90.0 | 200.0 | 120.0 | 170.0 | 263.667 |
| 23 | LPML1A4_0524_global_escape_lhs_B180_H600 | 180 | global_escape_lhs | global_lhs_mixed | 600 | 200.0 | 130.0 | 190.0 | 80.0 | 180.0 | 263.667 |
| 24 | LPML1A4_0536_global_escape_lhs_B180_H500 | 180 | global_escape_lhs | global_lhs_mixed | 500 | 140.0 | 70.0 | 180.0 | 140.0 | 200.0 | 263.667 |
| 25 | LPML1A4_0548_global_escape_lhs_B180_H600 | 180 | global_escape_lhs | global_lhs_mixed | 600 | 160.0 | 120.0 | 240.0 | 90.0 | 190.0 | 263.667 |
| 26 | LPML1A4_0588_global_escape_lhs_B300_H650 | 300 | global_escape_lhs | global_lhs_mixed | 650 | 170.0 | 100.0 | 150.0 | 110.0 | 160.0 | 263.667 |
| 27 | LPML1A4_0590_global_escape_lhs_B300_H500 | 300 | global_escape_lhs | global_lhs_mixed | 500 | 200.0 | 130.0 | 190.0 | 80.0 | 180.0 | 263.667 |
| 28 | LPML1A4_0508_global_escape_lhs_B180_H500 | 180 | global_escape_lhs | global_lhs_mixed | 500 | 160.0 | 90.0 | 180.0 | 120.0 | 190.0 | 262.333 |
| 29 | LPML1A4_0520_global_escape_lhs_B180_H600 | 180 | global_escape_lhs | global_lhs_mixed | 600 | 110.0 | 80.0 | 230.0 | 130.0 | 200.0 | 262.333 |
| 30 | LPML1A4_0434_sixbin_balance_B120_H600 | 120 | sixbin_balance | sixbin_moderate_mixed | 600 | 130.0 | 100.0 | 250.0 | 150.0 | 190.0 | 215.0 |
| 31 | LPML1A4_0381_sixbin_balance_B0_H500 | 0 | sixbin_balance | sixbin_moderate_mixed | 500 | 130.0 | 60.0 | 110.0 | 70.0 | 180.0 | 214.0 |
| 32 | LPML1A4_0394_sixbin_balance_B0_H500 | 0 | sixbin_balance | sixbin_moderate_mixed | 500 | 160.0 | 100.0 | 150.0 | 130.0 | 200.0 | 213.889 |
| 33 | LPML1A4_0406_sixbin_balance_B60_H600 | 60 | sixbin_balance | sixbin_moderate_mixed | 600 | 120.0 | 100.0 | 120.0 | 100.0 | 180.0 | 213.889 |
| 34 | LPML1A4_0420_sixbin_balance_B60_H500 | 60 | sixbin_balance | sixbin_moderate_mixed | 500 | 110.0 | 70.0 | 150.0 | 90.0 | 200.0 | 213.889 |
| 35 | LPML1A4_0424_sixbin_balance_B120_H500 | 120 | sixbin_balance | sixbin_moderate_mixed | 500 | 190.0 | 130.0 | 180.0 | 80.0 | 210.0 | 213.889 |
| 36 | LPML1A4_0450_sixbin_balance_B180_H600 | 180 | sixbin_balance | sixbin_moderate_mixed | 600 | 120.0 | 100.0 | 200.0 | 120.0 | 190.0 | 213.889 |

No FDTD was run.
No Lumerical GUI was opened.
No model was trained.
No K=6 was attempted.

Next recommended step: LP-ML1B runner planning + 36-case pilot, not 600-case full run.
