D9_PROSPECTIVE_DUAL_ANCHOR_EVIDENCE_CAVEAT_REVIEW_AND_PLANNING_CONTRACT_FREEZE_V1

STATUS: PASS (offline only; solver/lumapi/FDTD calls=0)

ENVIRONMENT
- Worktree: D:/project/worktrees/blue_apcd_lp_stage11_4
- Branch: work/lp-stage11-4
- Starting/current HEAD: 4866190c027253eff611633b05dd74cb6023213f
- Existing cross-branch evidence: 18 geometries / 36 x-y subruns / 36 accepted

PHASE_GRADIENT_SANITY
- Conclusion: LOCAL_GRADIENTS_SUPPORTED_WITH_HIGH_UNCERTAINTY
- Phase OLS gradient: [0.47904409621065747, -0.24488913316353664, -0.02872140412789878]
- Projector OLS gradient: [0.35789777331239975, -0.024626892133030348, 0.8229290920498139]
- Gradient cosine: 0.318075; principal angle: 71.453444 deg
- Phase LOO std: [0.04856059278859788, 0.01648383468401225, 0.02472365504706712]
- Projector LOO std: [0.11522681142556278, 0.09412799943428078, 0.07847321591317016]
- Max Cook distance: 0.615276 / 0.880201
- Unwrap correction: 7.10543e-15 deg

BRIDGE_THRESHOLD_SENSITIVITY
- Classification: NOT_CONNECTED_UNDER_FORMAL_GUARD
- Connectivity 1.00x/0.75x/0.50x: [False, False, False]
- No formal path exists under the actual-node guard at any multiplier.

EVIDENCE_CAVEATS
- Historical full-Jones validated: NO
- Bounded6 historical primary replay: NO
- Prospective continuity: CONDITIONAL YES, local domain only
- Global W/D/Psi quadratic surrogate: NO
- Jacobians: anchor-local only
- Permanent hard gate: HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE (error 0.008228297174274063 vs tolerance 2e-15)

ANCHOR_ADJUDICATION
- Outcome: RETAIN_EXISTING_DUAL_ANCHORS
- Retained anchors: ['POSTD8_BOUNDED_PHASE_01', 'POSTD8_BOUNDED_DIAG_06']
- Prospective phase minimum: PDCB_PHASE_LOCAL_01
- Strongest projector: PDCB_PROJECTOR_LOCAL_10
- Best trade-off: PDCB_PHASE_LOCAL_04

GLOBAL_PHASE_PLATEAU
- Classification: GLOBAL_PHASE_PLATEAU_NOT_YET_PROVEN
- Historical/bounded/phase/projector/bridge minima: 80.985689 / 80.985689 / 81.254921 / 83.053889 / 82.162029 deg
- Floor refreshed: False (difference is within 1e-6 degree serialization tolerance)

PLANNING_METHOD_AND_REVIEW
- Primary: PIECEWISE_DUAL_ANCHOR_LOCAL_LINEAR
- Fallback: MORE_PROSPECTIVE_DIAGNOSTIC_REQUIRED
- Review outcome: MORE_PROSPECTIVE_DIAGNOSTIC_REQUIRED
- Future budget only: max 8 geometries / 16 x-y subruns / 450 nm
- No D9 geometry, candidate, package or staging created

CONSTRAINT_AUDIT
- Existing cross-branch physics/package/staging untouched
- Historical original22 replay not attempted
- No solver/lumapi/FDTD calls
- Historical hard gate remains permanent
