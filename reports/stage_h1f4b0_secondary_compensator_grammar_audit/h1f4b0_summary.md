# H1F-4B0 secondary compensator grammar audit

- Status: `PASS_ZERO_SOLVER_AUDIT`
- Primary route: `GROUPED_D_PLUS_J1_ANISOTROPY_COMPENSATOR_PROBE_READY`
- Backup: `GLOBAL_H_GROUPED_D_MANIFOLD_REVISIT_READY`
- `solver_entered_delta=0`; `ml_admitted=false`.

J2 decoupling is deprioritized because its authoritative full-Jones local probe reports `J2_DECOUPLING_PHASE_LEVER_BREAKS_SELECTIVITY` and `tradeoff_improves=false`. J1 rotation is projector-mixing dominant. Position is weak on full K6. Helper is projector-degraded. Global H is retained only as a medium-value operating-manifold selector.

The proposed next probe is not executed: one full-K6 seed (`K6_L1_C_POS_PLUS10`) with J1 length/width differential ±2 nm, X/Y serial, maximum 4 cases.
