# NP K6-x M1 index diagnostic setup v1

- setup_only=true; solver_entered=0; diagnostic_level=M1.
- M1_selected_because_observable_outlier=true; added_monitors_only=true.
- production_mesh_not_frozen=true; candidate_performance_claim=false; K6_training_label_claim=false.
- Source is the SHA-matched M1 run input, not an M1 post-FSP.
- Two index monitors use spatial interpolation `none`, conformal mesh recording, and downsample 1; post-run extraction must read index/index_detail and component offsets.
