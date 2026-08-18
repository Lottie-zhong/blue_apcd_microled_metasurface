# A02 pre-admission geometry audit

Status: `PRE_ADMISSION_GEOMETRY_RISK`

The reported 0.032 nm is not the pillar-1/pillar-2 edge gap. It is the distance from pillar_2 vertex 2 to the lower periodic cell boundary y=-216 nm: `0.031995530124988964860678346652 nm`. The implied same-object periodic seam gap is `0.063991060249977929721356693304 nm`.

Same-cell pillar_1/pillar_2 minimum edge gap: `44.5319955301249939648606783467 nm`, between pillar_2 vertex 2 and the bottom edge of pillar_1 at x approximately `9.0747172360105242120507084472 nm`.
Minimum direct distinct periodic-image pair gap: `52.5319955301249939648606783467 nm`; the limiting physical periodic seam is the pillar_2 copy across the y boundary.

A02 consists of two distinct non-intersecting rectangles in the builder model, but its periodic seam clearance is sub-resolution/physically ambiguous. No A02 child FSP exists, so FSP topology was not claimed from an uninstantiated file.

No current Paper A hard minimum-gap or mesh-separability threshold was found. Historical LP-ML-specific 20 nm rules exist upstream but were not imported into this Paper A contract.

DOE unchanged. No FDTD/RCWA/ML was run. Benchmark admission remains blocked pending scientific decision.
