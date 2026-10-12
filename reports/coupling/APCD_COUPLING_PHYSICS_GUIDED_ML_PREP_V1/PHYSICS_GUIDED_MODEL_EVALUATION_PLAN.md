# Physics-guided model evaluation plan

## Compare the same development cases

Future development-stage comparison must include:

1. Original Cartesian KRR.
2. Original Cartesian MLP.
3. Analytic physics baseline.
4. Physics baseline plus residual model.
5. Physics-conditioned shared modal model only if needed.

Use the 156G authorized development pool and keep confirmation responses sealed. Keep all wavelengths, output modes and polarizations from one geometry in the same geometry-group split. Use the same geometry groups, role composition, H1/H2 definitions, phase reference, target decoder and budget accounting for every route. The current 32 old32, 113 global and 11 local-axis roles are all development strata; disclose their counts and do not claim the n=11 local-axis stratum supports a separate model.

Normalization, imputation if ever approved, feature selection and output scaling must be fit on training groups only. No HF truth may be used as an inference feature unless the exact physics calculation is genuinely available at unknown-geometry inference time. No HF oracle, confirmation leakage, oracle phase alignment or oracle power rescaling.

The exact split sizes, seeds, fit count and any budget increase require a separate dispatch. This plan does not authorize training or hyperparameter search.

## Required fair baselines and cost

- Geometry-only KRR and MLP from the frozen historical fit packages.
- Physics-only predictions where a validated provider supplies the exact held-out geometry and axes.
- Physics plus residual and, only if justified, a physics-conditioned shared model.
- A simple constant or nearest-neighbour check.

Report provider coverage and failures without imputation. For every physics route, report provider runtime plus network runtime. If each new geometry requires RCWA, include the RCWA calculation and setup cost in end-to-end inference latency; do not report neural-network latency alone. Track solver entered runs under the project budget semantics, including failed or interrupted entered runs.

## Frozen H1/H2 evaluation

Keep the 609-value packing, H2 decoder, source gauge and H1 thresholds unchanged:

- State error median <=0.5 and q95 <=0.8.
- Routing eta error median <=0.05 and q95 <=0.10; routing correlation >=0.95.
- Absolute-order error median <=0.05 and q95 <=0.10.
- Thresholded relative error median <=0.30 and q95 <=0.75.
- Total-power relative error median <=0.15 and q95 <=0.30; power correlation >=0.95.
- MLP seed standard deviation <=0.03.

Every mandatory gate must pass. Report per-wavelength, per-order and per-polarization slices. Report real/imaginary and amplitude error; phase error only above a preregistered magnitude floor, with the excluded fraction. Preserve the common source phase gauge and never align channels after prediction.

## Independent physics checks

Validate conventions independently of the ML target. Check positive finite P_scale. Where available, compare independent incident, reflected, transmitted and absorbed powers. Decoded total_power=P_scale is an identity of the current decoder and is not an independent closure check. For cascades, report mode truncation sensitivity, condition numbers, convergence, and comparison with an independent trusted calculation.

## Current status

No new fits or hyperparameter searches were run. Both historical H1 models fail the conjunctive gate. The eight adapter tests are synthetic compatibility tests, not physical validation or evaluation of a trained model.
