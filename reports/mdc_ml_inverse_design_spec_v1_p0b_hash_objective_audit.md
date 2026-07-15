# MDC-ML P0-B hash identity and staged-objective audit

## Result

The static contracts close the two P0-B issues: identity layers are non-overlapping, and robust Pareto cannot activate before real tolerance labels exist. No optical solver, model, or pilot dataset is involved.

## Hash behavior

- Wavelength-grid-only and angle-grid-only changes affect only simulation provenance.
- A GaN raw-table/source change affects physical configuration and downstream simulation provenance, but not canonical geometry or split group.
- A single-layer +3 nm child has a new canonical geometry and physical configuration, while its record inherits the nominal parent's split group.
- Mirror reversal has a different canonical geometry identity.
- Repeated baseline encode/canonicalize/decode preserves all corresponding hashes and layer equality.

## Baseline lineage

The baseline is `P1_ZL1_ALTERNATIVE_G3_A3` with thicknesses `[44,79,44,79,44,316,44,79,44,79,44,79] nm`, alternating TiO2/SiO2, from `APCD_GAN_NATIVE_M1` to Air. The static audit records the historical `c386...`, P0-A `878c...`, new canonical geometry, physical configuration, simulation example, and split-group identities.

## Objective activation

Nominal Pareto resolves to exactly four fields. Robust shortlist Pareto resolves to exactly five only when `robustness_label_available=true`, `robustness_evaluation_status=complete`, and `tolerance_robustness_penalty_pm3` is non-null. Missing robustness is rejected rather than replaced with zero. The first nominal surrogate remains a four-target contract.
