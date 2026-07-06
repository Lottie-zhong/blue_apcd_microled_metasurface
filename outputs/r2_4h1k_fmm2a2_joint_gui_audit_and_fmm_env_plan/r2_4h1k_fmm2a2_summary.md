# R2-4H1K FMM2A2 Summary

H1K/FMM2A2 is a no-run joint gate. It prepares the manual GUI audit package for the H1J3 derived RCLED-MDC FSP and records FMM/RCWA environment options after FMM2A found no available solver.

Key decisions:

- `joint_gate_decision = gui_audit_required_and_fmm_env_not_ready`
- `immediate_fdtd_allowed = false`
- `immediate_fmm_allowed = false`
- `immediate_heavy_fmm_sweep_allowed = false`
- `fmm_ready_for_minimal_probe = false`
- `y_dipole_allowed = false`
- `broadband_allowed = false`
- `apcd_coupling_allowed = false`

The H1J3 runtime FSP must be manually inspected before any H1L simulation is planned. FMM2B must wait until a solver environment exists and the user explicitly approves a minimal probe.
