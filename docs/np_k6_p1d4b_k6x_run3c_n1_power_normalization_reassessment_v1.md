# NP K6-x RUN3C N1 power normalization reassessment v1

- sourcepower_diagnostic_run_authorized=false
- sourcepower_diagnostic_prefsp_preserved=true
- sourcepower_error_not_scaled_to_structure_gain=true
- structure_interval_nonconservation_localized=true
- conformal_diagnostic_setup_only=true
- additional_solver_entered=0
- N2_not_authorized=true
- production_mesh_frozen=false
- K6_training_label=false

The prepared sourcepower diagnostic was not entered: no runtime attempt directory, ledger, scheduler task, controller, or post-FSP exists. The existing boundary post-FSP was independently reloaded read-only. At 449 nm source-slab injection is 0.9997404753, sourcepower error is 0.0002595247 (0.02595%), structure-bearing interval gain is 0.0513418100, and their ratio is 197.83. Raw power has the same positive interval gain (4.8306067e-17 W) as normalized flux, while monitor-T/raw/sourcepower differs by at most 1.11e-16. Sourcepower normalization is therefore effectively ruled out.

The cause layer is `STRUCTURE_INTERVAL_NUMERICAL_NONCONSERVATION_CONFIRMED`, localized to the interval containing pillars and material interfaces; it does not identify a single pillar or interface. v251 readback exposes `FDTD.mesh refinement` as `conformal variant 0`, with officially accepted adjacent values including variants 1 and 2. The sole selected future variable is `FDTD.mesh refinement: conformal variant 0 -> conformal variant 1`; no mesh spacing, geometry, material, source, PML, boundary, existing monitor, simulation-time, or auto-shutoff field changes.

Final status: `READY_FOR_RUN3C_N1_CONFORMAL_SINGLE_VARIABLE_DIAGNOSTIC_AUTHORIZATION`.
