# MDC HF Surrogate V3 final-epoch policy

This contract is frozen before any V3 OOF outcome is visible. It is outcome-blind and has no solver or training entry point.

- Eligible checkpoint range: epochs 50–400 inclusive.
- Monitor: inner-stop validation, geometry-level frozen profile-only composite.
- Outer held-out folds, power, auxiliary targets, final-development loss and V3-Test40 are forbidden for checkpoint selection.
- Machine-equal minimums select the earliest eligible epoch.
- For a selected V3-A/B/C architecture, exactly 15 valid leakage-free OOF fits (5 folds × 3 seeds) provide `eligible_best_epoch_i`.
- `E_final = round_half_up(median(eligible_best_epoch_i))`, constrained to 50–400.
- Full-development training uses 200 geometries / 1200 cases, no validation split, no early stopping and no checkpoint hunting.
- If the median equals 400, emit `MAX_EPOCH_SATURATION_WARNING`; do not expand the budget or alter `E_final` automatically.
- Final seed/ensemble membership is not frozen by the existing contract and remains a pre-final-training item; it must not be invented here.
- V3-Test40 remains sealed until model/checkpoint hashes are frozen and separate Chart authorization is granted.

Formal status: `MDC_HF_SURROGATE_V3_FINAL_EPOCH_POLICY_FROZEN_200G1200C_READY_FOR_OOF_AUTHORIZATION`.
