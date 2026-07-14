# MDC GaN Native-M1 TMM spectral rebaseline v1

## Closed spectral, angular, and ratio metrics

- Deterministic postprocess only: this closure reads frozen normal spectra and frozen signed-angle spectra. It does not invoke TMM, FDTD, Lumerical, lumapi, RCWA, or FMMAX.
- Strict ratio join: `structure_id + geometry_hash + canonical_sequence_hash + gan_material_id + gan_representation + angle_convention_id`.

|candidate|spectral FWHM nm|angular FWHM deg|max-angle set|T448/T450/T453|edge stability|T0/Tmax|ratio|layers/thickness nm|
|---|---:|---:|---|---|---:|---:|---:|---|
|P1_EXPLICIT_FAB_G3_A3|7.4|26.619014|[-3.0,3.0]|0.614061/0.827220/0.539372|0.539372|0.997378|40.115520|13/900|
|P1_ZL1_NOMINAL_G3_A3|3.3|17.826891|[-4.0,4.0]|0.334481/0.955739/0.288988|0.288988|0.963524|63.088795|12/978|
|P1_ZL1_ALTERNATIVE_G3_A3|3.3|14.996580|[0.0]|0.473289/0.966597/0.211693|0.211693|1.000000|45.666605|12/975|

## Candidate roles

- Explicit: broad-band engineering/FAB baseline.
- ZL-1 nominal: ratio-leading narrow-spectrum balanced candidate.
- ZL-1 alternative: narrower angular FWHM and unique 0 degree maximum; not assigned a composite score.

## Angle semantics

- Symmetric signed-grid maxima are reported as sets, not unilateral negative-angle deflection. The angular FWHM and normal-incidence spectral metrics are unchanged.

## Boundary

- No finite GaN propagation distance is included. Ratio is a plane-wave TMM angular-transmission metric, not a dipole far-field extraction efficiency.
