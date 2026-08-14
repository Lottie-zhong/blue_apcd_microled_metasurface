# Stage H1C-1B H550 Broadband Adaptive Global Full-Dimer

- Status: H1C1B_PARTIAL_DATA_PRESERVED; outcome: H1C1B_INCONCLUSIVE.
- Exact geometries: 24 (12 selectivity frontier + 12 phase-gap/global exploration).
- Frozen grid: [450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0] nm; one broadband solve per polarization returns all 9 points.
- Formal subruns planned/entered/accepted/quarantined: 48/48/45/3.
- Strict before / H1C-1B batch / cumulative after: 2 / 5 / 7; near-miss is never promoted.
- Category counts: {'BROADBAND_PROJECTOR_COMPATIBLE_STRICT': 5, 'CENTER_ONLY_COMPATIBLE': 8, 'PARTIALLY_COMPATIBLE': 3, 'INCOMPATIBLE': 8}.
- FDTD concurrency: global 2, LP branch 1; resources 4 MPI x 1 thread; RCWA excluded from FDTD count.
- ML registry: 209 + 189 = 398; ml_admitted=false for all.
- No automatic H1C-1C, ML training, inverse design, K6, constituent solver, or domain expansion.

Artifacts are listed in the H1C1B report directory.
