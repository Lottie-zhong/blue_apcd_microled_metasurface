# R2-2A Reuse Audit

No script was imported or executed for FDTD. This is a prepare-only audit.

Likely reusable pieces for the later R2-2 FDTD runner:
- `stage_r1c2_rcled_c2_focused_refinement.py`
- `stage_r1c4_rcled_c2_cav230_source_y_robustness.py`
- `stage_r2_1_rcled_stack_tmm_453_highq_screen.py`
- `stage_r2_1a_rcled_stack_tmm_physical_sanity_audit.py`
- `stage_r2_1b_rcled_highres_tmm_shortlist_verify.py`

Reuse candidates should be checked later for:
- 2D simulation mapping and physical x/y dipole orientation handling.
- vertical stack construction from top/bottom pair counts and cavity_span_nm.
- angular extraction at 453 nm and x/y incoherent power averaging.

Safety marker: no lumapi import, no FDTD solve, no .fsp/.ldf generation in R2-2A.
