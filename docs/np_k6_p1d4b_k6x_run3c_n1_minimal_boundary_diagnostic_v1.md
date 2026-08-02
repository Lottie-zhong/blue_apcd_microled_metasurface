# NP K6-x RUN3C N1 minimal boundary diagnostic v1

- diagnostic_run_only=true
- solver_entered_once=true
- entered/engine/controller/post-save=1/1/1/1
- signed_power_preserved=true
- source_slab_corrected=true
- 449nm_not_removed=true
- closure_threshold_unchanged=true
- N2_not_authorized=true
- production_mesh_frozen=false
- candidate_performance_label=false
- K6_training_label=false

The existing attempt_001 was recovered by read-only audit; no second run was made. The frozen pre-FSP SHA is 982057c2d0112644bcf22c5927a53858328fbf1f3b6c23b5ae251aa9c772b63c and the post-FSP SHA is 92624a63a13b321015274c3ef8ceeaddcaee5bb80afceb65f649444178e58b83. At 449 nm the signed normalized fluxes from z=-500,-110,-90,590,610,1100 nm are -0.3040018042, 0.6957386711, 0.6958621319, 0.7472039419, 0.7471925707, and 0.7469237229. The lower/upper fixed-mesh jumps are +1.23461e-4 and -1.13712e-5; the upper PML jump is -2.68848e-4. The source slab injection is 0.9997404753 and the structure interval increases by +0.05134181, while raw-power/sourcepower agrees with monitor T to 1.11e-16 and order sum closes to T. Therefore the root cause is BOUNDARY_FLUX_BALANCE_CLEAN_FORMAL_CLOSURE_CONFLICT, with the next single-variable setup-only sourcepower-frequency normalization diagnostic at SHA f7cf4561e6b145772b57940b038de9d4483bc3605f13969e1fe09520b6c2c33c. This evidence is diagnostic only and is not a production or training label.
