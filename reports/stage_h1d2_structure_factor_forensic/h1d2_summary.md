# Stage H1D-2 Primitive-Period and Structure-Factor Forensic

- Status: `PASS`; zero solver stage.
- H1D-1 sorted centers form x0+n*p: `True`; maximum residual `4.547e-13 nm`.
- Complete pillar distribution recovers primitive period p: `True`; phase-bin labels are physically inert: `true`.
- Identical-scatterer structure factor: `|S_-1|=6.474e-16`, `|S_0|=6`, `|S_+1|=6.474e-16`.
- FDTD qualitative comparison: `STRUCTURE_FACTOR_EXPLAINS_ORDER_SELECTION`; m=0 remains dominant across all 9 wavelengths for x/y.
- H1D-1 is a primitive-p identical-dimer array represented with P=6p, not a physical detour-modulated supercell.
- No-detour control is physically redundant; no control FDTD is recommended.
- Required adjacent intrinsic phase step for m=+1: +60 deg per +x primitive site.
- Positional 60-degree scale: P/6=431.907785999999987 nm = p; identical-phase compensation co-locates the six sites.
- Updated route: `EXTEND_DIMER_GRAMMAR_FIRST`; proposed-only smallest extension: J1 independent anisotropy.
- solver_entered_delta=0; no FDTD, RCWA, ML, inverse, or replay.

Artifacts: `h1d2_exact_geometry_audit.json`, `h1d2_primitive_period_audit.json`, `h1d2_structure_factor.csv`, `h1d2_fullwave_structure_factor_comparison.json`, `h1d2_phase_label_physicality_audit.json`, `h1d2_no_detour_control_equivalence.json`, `h1d2_constructive_phase_condition.md`, `h1d2_positional_shift_feasibility.json`, `h1d2_hybrid_reassessment.json`, `h1d2_route_decision.json`, `h1d2_proposed_next_stage.json`.
