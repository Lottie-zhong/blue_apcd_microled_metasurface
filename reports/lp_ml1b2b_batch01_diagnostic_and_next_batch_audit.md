# LP-ML1B2B batch-01 diagnostic and next-batch audit

This is analysis only. No FDTD was run. No GUI, FMM, ML training, K=6, or coverage was run.

## Batch-01 technical result
- candidates: 6
- subruns: 108 / 108
- merged Jones rows: 54 / 54
- failures: 0
- anomalies: 0

## Batch-01 performance interpretation
- Technical PASS: runner/schema/resume/reporting produced complete finite data with no failures or anomaly flags.
- Physical weak: no strong/usable B300 candidate appeared; phase targeting is scattered and selectivity is generally poor.

- nearest_bin_mode counts: {'300': 2, '240': 1, '120': 1, '60': 1, '180': 1}
- preliminary_status counts: {'weak': 1, 'phase_wrong': 5}
- Tx_mean range/median: 0.153109..0.912648 / 0.504485
- ratio_median range/median: 0.153982..1.525693 / 0.953036
- phase_err_at_452nm range/median: 25.473485..178.091363 / 67.998092

## High-Tx but poor-ratio candidates
- LPML1A4_0157_B300_exploration_B300_H500: nearest=240, Tx_mean=0.596152, ratio_median=1.525693, phase_err_452=45.543915
- LPML1A4_0178_B300_exploration_B300_H650: nearest=60, Tx_mean=0.912648, ratio_median=1.006323, phase_err_452=90.452269
- LPML1A4_0093_B300_exploration_B300_H500: nearest=180, Tx_mean=0.779973, ratio_median=0.899749, phase_err_452=111.201295

## Phase-near-target but poor-ratio candidates
- LPML1A4_0196_B300_exploration_B300_H500: nearest=300, Tx_mean=0.153109, ratio_median=0.153982, phase_err_452=25.473485
- LPML1A4_0028_B300_exploration_B300_H600: nearest=300, Tx_mean=0.261044, ratio_median=0.412745, phase_err_452=29.250068

## Drifted candidates
- LPML1A4_0157_B300_exploration_B300_H500: nearest=240, Tx_mean=0.596152, ratio_median=1.525693, phase_err_452=45.543915
- LPML1A4_0049_B300_exploration_B300_H500: nearest=120, Tx_mean=0.412817, ratio_median=1.377731, phase_err_452=178.091363
- LPML1A4_0178_B300_exploration_B300_H650: nearest=60, Tx_mean=0.912648, ratio_median=1.006323, phase_err_452=90.452269
- LPML1A4_0093_B300_exploration_B300_H500: nearest=180, Tx_mean=0.779973, ratio_median=0.899749, phase_err_452=111.201295

## Remaining batch composition
| batch | targets | groups | H | label | note |
|---|---|---|---|---|---|
| LPML1B2A_BATCH_02 | 300:6 | B300_exploration:6 | 500:3;650:3 | mostly_one_exploration_group | B300 continuation / statistical failure mapping |
| LPML1B2A_BATCH_03 | 240:5;300:1 | B240_exploration:5;B300_exploration:1 | 500:1;600:4;700:1 | diverse | remaining planned batch |
| LPML1B2A_BATCH_04 | 120:1;180:2;240:3 | B240_exploration:3;global_escape_lhs:3 | 500:3;600:2;650:1 | diverse | diverse next batch candidate |
| LPML1B2A_BATCH_05 | 120:1;180:3;300:2 | global_escape_lhs:5;sixbin_balance:1 | 500:2;600:3;650:1 | diverse | remaining planned batch |
| LPML1B2A_BATCH_06 | 0:2;120:1;180:1;60:2 | sixbin_balance:6 | 500:4;600:2 | diverse | remaining planned batch |

## Recommendation
Authorize next: **LPML1B2A_BATCH_04**.
Rationale: batch-01 and batch-02 are B300-heavy; this batch adds B240 plus global/sixbin diversity.
Do not declare K=6 readiness.
Do not execute anything from this diagnostic step.
