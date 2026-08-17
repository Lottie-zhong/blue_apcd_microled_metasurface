# NP K6 M9A normal-incidence plateau reassessment and Coupling handoff

- Status: `NP_K6_M9A_NORMAL_INCIDENCE_SCREENING_FROZEN_WAIT_COUPLING_ANGULAR_HANDOFF`
- Preregistration: `NP_K6_M9A_PLATEAU_REASSESSMENT_PREREG_V1`
- Preregistration SHA256: `0ee8251bff8ca4b6c3cdb982f1fc9a2387caf6e3cd370ccfe9dc6e551080bf91`
- HF22 authority: 484 rows, 22 geometries, 44 P/S pairs, exact 445–455 nm, `u_x=0`, `k_y=0`.
- Solver policy: FDTD=0, RCWA=0, new HF=0, external HF=0, sealed reads=0, inverse design=0.

## Decision

Normal-incidence development is closed at HF22 for this stage. The screening provider is complementary: LF-only for broadband ranking and LF-ridge residual for coarse full-order screening. It is `NP-1` and ranking/screening only; it is not a FDTD replacement, not an angular provider, and not quantitative full-response authority.

The M7→M8→M9 learning curve shows mixed common-geometry gains and no model passing all frozen numerical, ranking, worst-case, and physics gates. The plateau root cause is mixed (data tail/champion limits, formulation specialization, LF baseline limits, physics constraints, and multi-objective conflict). Additional normal-incidence HF is not justified by the preregistered rule.

The 12-geometry external set remains metadata-only and HOLD; no sealed targets were read. A fresh narrow-screening preregistration would be required before any future external use. Angular generalization is unsupported because all current evidence has `u_x=0`.

## Coupling handoff

The NP→MDC contract freezes order identity (`m=+1` is physical `+x`), +z outward normalization, P/S identity, exact wavelength semantics, and explicit extrapolation/error flags. Concrete nonzero-`u_x` anchors are not selected here. The next trigger is Coupling Stage1 9/9 plus CONTROL_0 versus ALT_1 zero-solver evidence; only then may angular anchor design begin.

This is a physics-guided surrogate / screening / active-learning-assisted HF acquisition / coupling-aware handoff methodology. It never claims that ML replaces FDTD.
