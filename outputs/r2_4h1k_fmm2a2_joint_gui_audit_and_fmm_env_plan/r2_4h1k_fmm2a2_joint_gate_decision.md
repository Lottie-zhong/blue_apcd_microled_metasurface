# R2-4H1K / FMM2A2 Joint Gate Decision

`joint_gate_decision = gui_audit_required_and_fmm_env_not_ready`

Immediate FDTD is not allowed because the H1J3 derived FSP still requires manual GUI confirmation of mesh order, source setup, monitor placement, and far-field settings.

Immediate FMM/RCWA is not allowed because FMM2A found no importable FMM/RCWA solver in the current environment.

Immediate heavy FMM sweep, y-dipole validation, broadband FDTD, and APCD coupling are all blocked.

Next user action: manually open the uncommitted H1J3 derived FSP and complete the H1K GUI audit form.

Next Codex action after the user GUI audit: record the H1K audit if it passes, or create a corrected derived FSP fix stage if it fails.
