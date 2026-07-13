# MDC P1 asymmetric Native-M1 TMM spectral v1

Pure-film, normal-incidence Native-M1 TMM only. No external solver, model training, or database write was performed.

## Pipeline

- Materials: APCD_TIO2_NATIVE_M1 / APCD_SIO2_NATIVE_M1, sampled complex epsilon, frequency-axis interpolation, physical principal square root, extrapolation forbidden.
- Evaluator: repository `mdc_tmm_core.emission_tmm`; metric extraction and FWHM use the canonical topology-scan pipeline.
- Grid: 420-480 nm, 0.1 nm; incidence 0 deg; GaN -> compiled stack -> Air.

## Results

|structure|seed|N_GaN/N_Air|peak nm|FWHM nm|T448|T450|T453|edge stability|
|---|---|---|---:|---:|---:|---:|---:|---:|
|P1_EXPLICIT_FAB_G1_A5|explicit_fab|1/5|480.000000|boundary-clipped|0.01639967|0.01647059|0.01653866|0.01639967|
|P1_EXPLICIT_FAB_G2_A4|explicit_fab|2/4|450.000000|19.500000|0.14664330|0.15316225|0.14006076|0.14006076|
|P1_EXPLICIT_FAB_G3_A3|explicit_fab|3/3|450.200000|7.500000|0.61986037|0.82784149|0.53414557|0.53414557|
|P1_EXPLICIT_FAB_G4_A2|explicit_fab|4/2|450.100000|8.700000|0.50072308|0.62523200|0.44170250|0.44170250|
|P1_EXPLICIT_FAB_G5_A1|explicit_fab|5/1|450.100000|26.500000|0.08933560|0.09189142|0.08761322|0.08761322|
|P1_ZL1_NOMINAL_G1_A5|zl1_nominal|1/5|450.000000|22.200000|0.03232973|0.03352327|0.03120739|0.03120739|
|P1_ZL1_NOMINAL_G2_A4|zl1_nominal|2/4|450.200000|6.400000|0.19184985|0.28658421|0.16815907|0.16815907|
|P1_ZL1_NOMINAL_G3_A3|zl1_nominal|3/3|450.300000|3.300000|0.33986899|0.96049795|0.28492814|0.28492814|
|P1_ZL1_NOMINAL_G4_A2|zl1_nominal|4/2|450.200000|5.500000|0.22884542|0.37819661|0.19164879|0.19164879|
|P1_ZL1_NOMINAL_G5_A1|zl1_nominal|5/1|449.900000|17.500000|0.04454080|0.04676501|0.04152467|0.04152467|
|P1_ZL1_ALTERNATIVE_G1_A5|zl1_alternative|1/5|450.100000|22.400000|0.03180283|0.03308254|0.03095252|0.03095252|
|P1_ZL1_ALTERNATIVE_G2_A4|zl1_alternative|2/4|449.700000|6.200000|0.22046786|0.28429975|0.14256694|0.14256694|
|P1_ZL1_ALTERNATIVE_G3_A3|zl1_alternative|3/3|449.700000|3.200000|0.48141664|0.96059330|0.20923241|0.20923241|
|P1_ZL1_ALTERNATIVE_G4_A2|zl1_alternative|4/2|449.700000|5.400000|0.26905724|0.37424219|0.15994089|0.15994089|
|P1_ZL1_ALTERNATIVE_G5_A1|zl1_alternative|5/1|450.000000|17.600000|0.04365146|0.04612730|0.04135632|0.04135632|

## Control replay

Three `(3,3)` controls passed geometry/sequence/hash replay and metric comparison. See `p1_control_replay.csv` for reference, replay, delta and tolerance provenance.

## Core metric availability

- Spectral peak/FWHM/T448/T450/T453/edge stability: available.
- TMM angular FWHM: unavailable; `missing_reason=spectral_only_scan`.
- Maximum transmission angle: unavailable; `missing_reason=spectral_only_normal_incidence_scan`; 0° incidence is not reported as an angular maximum.

## Local comparisons

Local Pareto views use only unweighted pairwise views: FWHM vs T450, edge stability, and ratio. No composite score or final primary baseline is frozen.

## Next lambda-angle candidates

Recommend only structures that pass this spectral gate for a later Native-M1 lambda-angle run: controls plus non-symmetric rows on each seed's local Pareto views. This report does not execute that stage.

## Selection conclusion

- Symmetric G3/A3 is preferred for all three seeds.
- Moderate GaN-heavy G4/A2 consistently outperforms mirrored G2/A4, but remains inferior to the symmetric control.
- Extreme asymmetry is not recommended for further angular/FDTD validation.
