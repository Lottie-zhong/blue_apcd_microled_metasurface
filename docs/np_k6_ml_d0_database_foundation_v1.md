# NP K6 ML D0 database foundation v1

Status: `NP_K6_ML_D0_DATABASE_FOUNDATION_V1_COMPLETE`

- Design space: 296010 canonical K6 geometries from D100–D230 in 5 nm steps; strict diameter ordering and deterministic geometry hashes.
- LF prior: 3,256,110 geometry-wavelength rows (296010 × 11), x-only, `LOW_FIDELITY_SINGLE_PILLAR_DFT_PROXY`, chunked NPZ arrays with explicit axis/dtype/hash manifest.
- Regression: frozen DFT convention is `exp(-2*pi*i*m*j/K)`, m = -3..+3, target +1; ideal increasing phase maps to +1 and rejects the opposite sign. Eight legacy passing sextets and RUN3A/B/C anchors are linked by canonical geometry hash.
- Pilot: 48 development + 12 sealed-test geometries; 120 potential x/y HF tasks; all task ledgers remain `entered=false`, `run_invocation_count=0`, `solver_authorized=false`.
- Contracts: HF dataset contract and model feature contract are schema-only; Native-M1 remains the production material contract; production mesh is `PENDING_NUMERICAL_FIDELITY_FREEZE`.
- Large CSV/NPZ artifacts remain in the remote outputs directory and are indexed by checksum; they are intentionally not staged in Git.
- The legacy 26-point dataset contract is preserved and explicitly superseded for this database by the 27-point library manifest/verification evidence; the original file is unmodified.

Solver calls: 0. No HF labels or training labels were generated.
