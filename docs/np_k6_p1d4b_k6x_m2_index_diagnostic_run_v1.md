# NP K6-x M2 actual mesh/index comparison v1

- diagnostic_run_only=true
- candidate_performance_label=false
- production_mesh_not_frozen=true
- K6_training_label=false
- solver_entered_once=true

M2 diagnostic attempt_001 independently reloaded without run/save. The M2 diagnostic and formal M2 post-FSP agree exactly at all 11 wavelengths for T/R, order efficiency, and directionality. M1/M2 actual grids are NON_NESTED (M1 134x25x52; M2 166x31x66). The supported classification is M1_M2_DISCRETIZATION_SENSITIVITY_CONFIRMED_ROOT_CAUSE_NOT_UNIQUE; this does not claim unique causality from two mesh levels. Fixed-origin N1/N2 pre-FSP files are setup-only; N1 is the only proposed next solver case.

Runtime log audit confirms NORMAL_AUTO_SHUTOFF_CONFIRMED (final auto shutoff 0.000281096; 55,106 iterations).
