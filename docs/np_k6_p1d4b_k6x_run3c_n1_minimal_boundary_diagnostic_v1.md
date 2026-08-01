# NP K6-x RUN3C N1 minimal boundary diagnostic v1

- diagnostic_run_only=true
- solver_entered_once=true
- signed_power_preserved=true
- source_slab_corrected=true
- 449nm_not_removed=true
- closure_threshold_unchanged=true
- N2_not_authorized=true
- production_mesh_frozen=false
- candidate_performance_label=false
- K6_training_label=false

The sole authorized attempt completed and produced a stable post-FSP. At 449 nm the signed normalized fluxes at z = -500, -110, -90, 590, 610 and 1100 nm are -0.3040018042, 0.6957386711, 0.6958621319, 0.7472039419, 0.7471925707 and 0.7469237229. The lower and upper fixed-mesh transition jumps are +1.2346076e-4 and -1.1371154e-5; the upper PML propagation jump is -2.6884786e-4. The source-slab jump is 0.9997404753, consistent with source injection. Raw-power/sourcepower and signed monitor-T agree to 1.11e-16. The structure interval increases by +0.05134181, while formal T+R remains 1.05078316; therefore no boundary transition or PML defect is confirmed.

Classification: `BOUNDARY_FLUX_BALANCE_CLEAN_FORMAL_CLOSURE_CONFLICT`. The unique next setup-only contract adds one sourcepower audit monitor at z=-200 nm and changes no mesh, PML, source, geometry, materials or existing monitors. No next solver has been run.
