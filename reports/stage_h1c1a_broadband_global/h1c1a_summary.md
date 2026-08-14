# Stage H1C-1A — H550 Broadband Global Full-Dimer Phase-Island Discovery

- Status: `H1C1A_PARTIAL_DATA_PRESERVED`
- Planned/entered/accepted formal subruns: `48/48/45`.
- Exact geometries: `24` (`20` global + `4` seed controls).
- Frozen grid: `[450.0, 450.5, 451.0, 451.5, 452.0, 452.5, 453.0, 453.5, 454.0]` nm; one broadband solve per polarization returns all 9 points.
- FDTD concurrency: global `2`, LP branch `1`; resources `4 MPI × 1 thread`.
- Strict / center-only / partial / incompatible: `2/8/5/9`.
- C broadband status: `CENTER_ONLY_COMPATIBLE`.
- Circular coverage: `18.8150092574661` deg; largest gap: `341.1849907425339` deg.
- ML labels: `189` new broadband rows + `20` historical 450-only rows; `ml_admitted=false` for all.
- No throughput threshold was invented; no absolute phase-flatness gate was applied; six-bin phase-bin threshold remains unfrozen.
- No automatic second batch, ML training, constituent solver, inverse design, or K6 was started.

Artifacts: `h1c1a_candidate_manifest.json`, `h1c1a_solver_accounting.json`, `h1c1a_broadband_full_jones.csv`, `h1c1a_geometry_broadband_summary.csv`, `h1c1a_global_candidate_bank.json`, `h1c1a_phase_islands.json`, `h1c1a_six_bin_screening.json`, `lp_hf_authoritative_label_registry_v1.json/.csv`, `h1c1a_final.json`.
