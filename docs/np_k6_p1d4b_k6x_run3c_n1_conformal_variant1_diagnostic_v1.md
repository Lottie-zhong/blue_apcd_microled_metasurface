# NP K6-x RUN3C N1 conformal variant 1 diagnostic v1

- single_variable_conformal_test=true
- baseline_variant=0
- diagnostic_variant=1
- fixed_grid_unchanged=true
- sourcepower_ruled_out=true
- signed_power_preserved=true
- exact_fill_fraction_not_claimed=true
- production_mesh_frozen=false
- N2_not_run=true
- candidate_performance_label=false
- K6_training_label=false
- solver_entered_once=true

Variant 1 changed only FDTD.mesh refinement from conformal variant 0. The authoritative setup SHA is the 64-character value in conformal_diagnostic_prefsp_checksum.json. The single run completed and independently reloaded. Variant 1 exactly reproduces variant 0: at 449 nm T=0.7470129923, R=0.3037701700, residual=-0.0507831623, structure gain=0.0513418100; at 450 nm T=0.7354313229, R=0.2662242107, residual=-0.0016555336. Full-band maximum closure change and all order/T changes are zero. Classification: CONFORMAL_VARIANT1_NO_EFFECT. A conformal variant 2 setup-only contract was prepared, but no variant 2 solver was run.
