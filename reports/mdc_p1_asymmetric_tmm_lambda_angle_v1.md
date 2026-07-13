# MDC P1 asymmetric Native-M1 wavelength-angle v1

Formal pure-film Native-M1 TMM only. No FDTD, external solver, model training, or database writes.

## Angular pipeline provenance

- Reused `stage_mdc_native_m1_integer_tolerance_audit.py` definitions: signed -60..60 deg grid, 1 deg step, full-width linear half-power crossings, signed-grid argmax, and unpolarized=(TE+TM)/2.
- Spectral peak/FWHM/T448/T450/T453 are read from frozen P1 spectral output; no redefinition.

## Candidate summary

|candidate|topology|peak nm|spectral FWHM nm|angular FWHM 450 deg|max abs angle 450 deg|T0/Tmax 450|
|---|---|---:|---:|---:|---:|---:|
|EX_N3_L79_H45_C156|Explicit|450.000|19.500|42.045|0.0|1.000000|
|EX_N3_L79_H45_C156|Explicit|450.200|7.500|26.509|3.0|0.998453|
|EX_N3_L79_H45_C156|Explicit|450.100|8.700|28.292|2.0|0.999198|
|ZL1_N3_M3_L78_H46|ZL-1 nominal|450.200|6.400|23.312|3.0|0.994380|
|ZL1_N3_M3_L78_H46|ZL-1 nominal|450.300|3.300|17.726|3.0|0.969593|
|ZL1_N3_M3_L78_H46|ZL-1 nominal|450.200|5.500|21.616|3.0|0.993922|
|ZL1_N3_M3_L79_H44_C316|ZL-1 alternative|449.700|6.200|21.423|0.0|1.000000|
|ZL1_N3_M3_L79_H44_C316|ZL-1 alternative|449.700|3.200|14.921|0.0|1.000000|
|ZL1_N3_M3_L79_H44_C316|ZL-1 alternative|449.700|5.400|19.713|0.0|1.000000|

## Control replay

All three G3/A3 controls passed spectral and angular replay against frozen Native-M1 summaries.

## Interpretation

- G3/A3 remains the balanced angular reference for every seed.
- G4/A2 is the GaN-heavy probe; G2/A4 is the Air-heavy mirror probe.
- Angular values are plane-wave TMM transmission selection, not dipole far-field metrics.
- Proposed plane-wave FDTD candidates are Explicit G3/A3, ZL-1 nominal G3/A3, and ZL-1 alternative G3/A3; asymmetric probes require a clear local Pareto or angular advantage.
- This task does not run FDTD or train models.

## Physical conclusion

P1 asymmetric mirror-strength scan is a negative optimization result. Symmetric G3/A3 remains preferred for all three seeds. G4/A2 outperforms mirrored G2/A4 in the observed screening metrics, but not G3/A3; this difference is attributed to GaN/Air boundary or termination asymmetry, not demonstrated directional emission. ZL-1 alternative is the narrow spectral/angular performance anchor, while ZL-1 nominal remains the edge-stability/ratio balanced candidate. The alternative's narrower angular spectrum does not imply lower small-angle dispersion; both ZL-1 candidates show approximately 10 nm blue shift by 20 degrees. The +/-3 degree maxima for Explicit/nominal are symmetric near-normal responses, not one-sided 3 degree steering. Plane-wave TMM angular metrics do not equal dipole-FDTD far-field metrics.
