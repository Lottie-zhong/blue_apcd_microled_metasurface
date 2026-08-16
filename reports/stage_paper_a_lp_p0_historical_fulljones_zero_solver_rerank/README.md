# Paper A LP P0 historical full-Jones zero-solver rerank

PASS: offline CSV/JSON audit only; FDTD/RCWA/ML calls 0/0/0. Frozen grid 450-454 nm, 0.5 nm, 9 points. Phase is diagnostic only; K6 and legacy/ML labels excluded. Native-compatible complete geometries: 52; Pareto front: 9; shortlist: 6.

Ranking is Pareto first, then fixed deterministic hierarchy: worst-case physical viability (DoLP, target-x fidelity, leakage), useful output, rank-one contrast, broadband variance, exact hash. No post-hoc composite weights. Absolute power is bound to the reported throughput column; Jones-derived operator metrics remain separate. Fabrication margin is unavailable from existing physics.
