# LP-ML1B seed-objective audit: selectivity first

## Direct answer
Current LP-ML1A4 / LP-ML1B candidates are mainly target-bin geometry exploration seeds, not a true selectivity-first LP-APCD seed set.
The code computes and preserves the correct Jones/projection metrics later, but the A4 seed labels are assigned from geometry-intent sampling groups rather than simulated Jones phase or a projector/selectivity gate.

## What A4 target_bin means
A4 defines GROUP_TARGETS as `{'B300_exploration': 220, 'B240_exploration': 160, 'sixbin_balance': 120, 'global_escape_lhs': 100}` and generates target_bin_deg from sampling groups such as B300_exploration, B240_exploration, global_escape_lhs, and sixbin_balance.
This means target_bin is an intended exploration label. It is not proof that the selected channel phase landed in that bin, and it is not proof that the candidate behaves like `t exp(i phi)|x><x|`.

## Selectivity-first gates found
- A4 selectivity-first gate before inclusion: `False`.
- B0 queue planning documents the desired LP Jones schema, but queue selection is mainly sampling balance / priority-score exploration, not measured selectivity-first selection.
- B2B strong/usable labels use Tx, ratio, phase, and matrix_error thresholds, then ranking sorts by status, ratio, and phase. This is a mixed gate, not a clean hierarchy of projector first then phase.

## Batch-01 selectivity-first reclassification
| candidate_id | target_bin | nearest_bin_mode | Tx_mean | ratio_median | matrix_error_median | phase_err_at_452nm | projector_gate | phase_gate | selectivity_first_class |
|---|---|---|---|---|---|---|---|---|---|
| LPML1A4_0196_B300_exploration_B300_H500 | 300 | 300 | 0.153109 | 0.153982 | 3.296620 | 25.473485 | fail | near | phase_near_but_nonselective |
| LPML1A4_0157_B300_exploration_B300_H500 | 300 | 240 | 0.596152 | 1.525693 | 0.968701 | 45.543915 | fail | fail | high_Tx_but_nonselective |
| LPML1A4_0049_B300_exploration_B300_H500 | 300 | 120 | 0.412817 | 1.377731 | 0.905772 | 178.091363 | fail | fail | phase_drifted_and_nonselective |
| LPML1A4_0178_B300_exploration_B300_H650 | 300 | 60 | 0.912648 | 1.006323 | 0.997636 | 90.452269 | fail | fail | high_Tx_but_nonselective |
| LPML1A4_0093_B300_exploration_B300_H500 | 300 | 180 | 0.779973 | 0.899749 | 1.056853 | 111.201295 | fail | fail | high_Tx_but_nonselective |
| LPML1A4_0028_B300_exploration_B300_H600 | 300 | 300 | 0.261044 | 0.412745 | 1.626343 | 29.250068 | fail | near | phase_near_but_nonselective |

## Batch-01 failure in selectivity-first language
- nearest_bin_mode counts: `{'300': 2, '240': 1, '120': 1, '60': 1, '180': 1}`.
- old preliminary_status counts: `{'weak': 1, 'phase_wrong': 5}`.
- selectivity-first class counts: `{'phase_near_but_nonselective': 2, 'high_Tx_but_nonselective': 3, 'phase_drifted_and_nonselective': 1}`.
- high-Tx but nonselective candidates: `['LPML1A4_0157_B300_exploration_B300_H500', 'LPML1A4_0178_B300_exploration_B300_H650', 'LPML1A4_0093_B300_exploration_B300_H500']`.
- phase-near but nonselective candidates: `['LPML1A4_0196_B300_exploration_B300_H500', 'LPML1A4_0028_B300_exploration_B300_H600']`.
- phase-drifted and nonselective candidates: `['LPML1A4_0049_B300_exploration_B300_H500']`.
Batch-01 is technically healthy as a data extraction run, but physically weak for LP APCD because projector/selectivity behavior is not established before phase targeting.

## Corrected LP-ML1B2C ranking hierarchy
1. Hard gate 1: extraction/schema pass, finite complex Jones values, correct wavelength/polarization coverage, no anomaly flags.
2. Hard gate 2: projector/selectivity pass: selected_Tx floor, leakage ceilings, selected-to-leakage ratio, and matrix_error against `t exp(i phi)|x><x|`.
3. Hard gate 3: phase-bin pass: nearest_bin_mode equals target and phase_err_at_452nm or spectral max phase error meets threshold.
4. Hard gate 4: wavelength stability pass: nearest bin is stable and phase/ratio remain acceptable across the sampled wavelengths.
5. Soft ranking: higher Tx, better ratio, lower matrix_error, bandwidth stability, then geometry/fabrication margin.

## Provisional pilot-stage thresholds
- minimum selected_Tx: 0.45
- minimum ratio_median: 6.0
- maximum y_direct_leakage relative to selected_Tx: y_direct_leakage <= selected_Tx / 6 as a first budget
- maximum phase_err_at_452nm: 15 deg for pass, 30 deg for near-miss diagnostics
- maximum bin instability: one nearest-bin mode across wavelengths for a pass
- matrix_error warning threshold: 0.60

## Next batch recommendation
LPML1B2A_BATCH_04 remains the best next FDTD batch if another batch is authorized because it adds B240 plus global/sixbin diversity.
However, this audit recommends adjusting LP-ML1B2C ranking/seed logic before continuing to batch-02. Batch-02 is mostly B300 continuation and should be treated as statistical failure mapping, not the default next physical rescue batch.

No FDTD was run. No GUI, FMM, model training, K=6, coverage, or heavy output generation was performed.
