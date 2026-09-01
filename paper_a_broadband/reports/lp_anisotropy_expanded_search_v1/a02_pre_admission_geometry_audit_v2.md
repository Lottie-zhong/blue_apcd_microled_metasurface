# A02 independent pre-admission geometry audit v2

Status: `PASS_WITH_A02_ADMISSION_HARD_GATE`

The reported `0.03199553012498768 nm` is not a pillar-pair gap, not a translated-polygon gap, not a bounding-box approximation, and not floating-point noise. It is the 100-digit-recomputed distance from `pillar_2` vertex 0 to the bottom cell boundary `y=-216 nm`, included by the legacy aggregate `min_edge_gap_nm` field.

Exact instantiated geometry: L1/W1/L2/W2 = `195.5/114.99999999999999/206.99999999999997/76.5 nm`; rotations = `0.0/65.0 deg`; centers = `(0,106.0)/(0,-106.0) nm`; D/Px/Py = `212.0/432.0/432.0 nm`.
Independent same-cell pillar gap: `44.531995530124993964860678346651961425291898838349 nm`, pair `pillar_1 ↔ pillar_2`; nearest translated periodic-image gap under the canonical shift convention: `52.531995530124993964860678346651961425291898838349 nm`, pair `pillar_1 ↔ pillar_2`, shift `[0, 1]`. Nearest same-object translated image gap is `212.8392310549349088473764687980523851716175496867 nm`; therefore the prior `0.064 nm` boundary-doubling interpretation is not a physical translated-image distance.

Containment: `True`. Same-cell intersection/touch: `False`. Periodic intersection/touch count: `0`. The builder has two distinct rectangle objects and no A02 child FSP was instantiated.

The inherited current Paper A geometry gates are direct polygon clearance >=60 nm, translated periodic-image clearance >=60 nm, no overlap/touch, containment, integer lateral dimensions, and half-grid-compatible centers. A02 has direct `44.531995530... nm`, periodic `52.531995530... nm`, and non-integer lateral dimensions `195.5/76.5 nm`; it is therefore not safe for benchmark admission even though it is mathematically non-overlapping and the `0.032 nm` report is only a boundary-margin definition artifact.

A01-A08 were re-audited with the corrected zero-solver method; the DOE was not edited or replaced. No solver, mesh, physics, or scheduler state was changed.
