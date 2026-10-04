# Continuation - project-owner recovery and EXT02 diagnostic

Status: **The authorized EXT02 diagnostic completed once. Durable truth and both E/H planes are ready for the frozen Coupling evaluator. The Runner did not perform the comparison.**

- Queue21 Traditional K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001 events 1499/1506 remain physical-entry UNKNOWN, preserved and quarantined.
- Coupling consumer commit 8019c12c9627dad414bbbfff3579a0bffcda6aa4: registry 01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261; inventory fde78be0e927ba084301cfcbf8b8500206eaea1dc7fdfb4715eb88517231c48b; 12/12 hashes verified; report evidence says 32 tests passed. Registry generation 26 is a historical snapshot, not live Runner hold state.
- Official owner-approved queue21 hold release: hold-4a6eab94af3b4a6d8510ba2fe32a5b66, authority 7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2, event 4, generation 27. Live control hold=0, health PASS, no active hold/lease/reservation.
- Runner V1 remains single-slot. Run ID EXT02_DIAG_20261004T141216Z_1b4ce0df234b; one run-one call, one solver entry, zero replay; state DONE, fresh LOAD and SCIENTIFIC_VALID PASS.
- MON_POSTNP actual sample z=1801.9999999999932 nm, H5 Monitor2. EXT02_POSTNP_DIAG_Z2000 actual sample z=2006.6041666666679 nm, H5 Monitor4. Both have six finite complex components, 349 x 59 x 1 x 21 coordinates and reference to z=1722 nm.
- The raw NPZ includes incident-reference IN E/H and spectrum for Coupling's frozen source normalization. No fitted field scaling or phase-oracle alignment was applied.
- Actual local mesh spacing at both monitor planes and the PML inner mesh face are not recorded in saved results. Keep unknown; configured values are not measurements.
- The independent diagnostic is not a training label and does not replace historical EXT02 truth. All 160 V2 cases remain unauthorized with zero entries.

## Evidence pointers

- Final report: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1\FINAL_REPORT.md
- Coupling handoff manifest: D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1\EXT02_COUPLING_HANDOFF_V1.json
- Immutable run directory: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b
- Frozen protocol: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1\DIAGNOSTIC_PROTOCOL_V1.json (SHA256 fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8)
- Load-only extraction files: D:\apcd_runtime\gpu_production_runner_v1\runs\K6V1_EXT02_TWO_AIR_PLANES_DIAG\attempt_001\EXT02_DIAG_20261004T141216Z_1b4ce0df234b\monitor_extraction\final_v1
- Final checksum inventory: SHA256_INVENTORY_V4.json

## Next - do not execute solver

Send the handoff to the Coupling scientific evaluator for only the frozen one-case comparison. Do not call Runner again, create attempt_002, or launch any V2 case.
