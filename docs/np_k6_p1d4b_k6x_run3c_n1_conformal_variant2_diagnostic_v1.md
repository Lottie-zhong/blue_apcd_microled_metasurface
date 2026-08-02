# NP K6-x RUN3C N1 conformal variant 2 diagnostic v1

- single_variable_conformal_test=true; diagnostic_variant=2
- source SHA256: `88060c4f7b7b6d2aa75b94aee43e9e82159edeb2b496e065fe8d1c2960b7238d`; post SHA256: `2b9e1bd1a17efba40a1239cbd5711790e1c97b900f06a4970687b3dfa4a88e65`
- solver entered exactly once; engine/controller/post-save completed.
- Only `FDTD.mesh refinement` changed from conformal variant 0 to 2.
- All 11-point v0/v1/v2 observables are identical; 449 nm residual remains `-0.05078316231892488`; sourcepower is ruled out.
- Classification: `CONFORMAL_VARIANT2_NO_EFFECT`.
- Next setup-only action: Native-M1 material-representation control; its pre-FSP SHA is in `material_control_prefsp_checksum.json` and it was not run.
- fixed_grid_unchanged=true; production_mesh_frozen=false; N2_not_run=true; candidate_performance_label=false; K6_training_label=false.
