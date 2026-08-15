# H1F-3C K6 First-Harmonic Local-Response Lever Audit

Status: PASS; zero solver.

- Formal decision: **GROUPED_D_FIRST_HARMONIC_READY**.
- H1F3B closure is scoped to the tested cosine position grammar only: POSITION_MODE_RESPONSE_WEAK.
- Independent full-wave K6 candidate count from H1F1/H1F2/H1F3B: 10; H1D1 geometry recorded separately: 1.
- Primary: `K6_L1_C_POS_PLUS10`; transfer: `K6_L1_B`.
- D semantics: `J1=(cx-D*cos(Psi)/2,cy-D*sin(Psi)/2); J2=(cx+D*cos(Psi)/2,cy+D*sin(Psi)/2)`; dimer and site centers invariant.
- First-harmonic basis sums: c=-1.1102230246251565e-16, s=3.3306690738754696e-16; inner products c·c=3.0000000000000004, s·s=2.9999999999999996, c·s=3.3306690738754696e-16.
- s_n definition: `t_xx,n(lambda)`; diagnostic only, not a full-K6 decomposition.
- Matched local-D Jacobian available: `False` from 0 exact pairs; no unrelated derivative inference.
- Canonical K6 registry: `D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1\reports\stage_h1f3c_k6_complex_lever_audit\K6_FULLWAVE_EVIDENCE_REGISTRY.csv`, rows=720, exact logical count match=True; local registry remains 578.
- H1F4A is proposed-only: Phase 1 8 cases; conditional Phase 2 4 cases; maximum 12; solver authorized=false.
- ML remains blocked: `ml_admitted=false`; solver_entered_delta=0.
