# COUPLING_GPU_RUNNER_CANARY_INPUT_HANDOFF_V1

## STATUS

PARTIAL. CANARY_INPUT_HANDOFF_READY is not asserted. Both cases are classification C.

Both files fresh LOAD successfully; scientific contract validation does not pass. Existing files were not modified. No run(), solver engine, dispatch or Shared V3 DB write occurred.

## SCIENTIFIC CONTRACT

`32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`

Expansion manifest SHA256: `4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f`. Ordered geometry and geometry hashes match the approved Stage-1 manifest. MDC identity: P1_ZL1_ALTERNATIVE_G3_A3; twelve native TiO2/SiO2 layers totaling 975 nm; spacer 237 nm; K6 period 1740 x 290 nm; pillars 500 nm; X polarization; 440-460 nm; x/y periodic and z PML.

## CASES

### K6V1_S35

Classification: C. Existing candidate path: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1\K6V1_S35\attempt_001\setup\runtime.fsp`.

SHA256: `dc1abfd755d443ed16fe0a6c0771f8aa3ce2700a3c999bb0cd77a7caa799378a`; bytes: 522322.

Ordered D1-D6 (nm): [110, 145, 225, 105, 185, 215]. Geometry SHA256: `bd6fb9a41c003910eeda456315bafb1962dd4335d1ec64ec055322e2f4a19276`.

Fresh LOAD: PASS. Frozen scientific mesh validation: FAIL. FSP hash and mtime unchanged.

Generating commit: unknown. Report-associated commit f0cd93d1407d080bf93259fd1153cb664235e8c8 is not claimed as the FSP generation commit.

Readback checks: `{"ordered_geometry": true, "pillar_height_and_material": true, "mdc_stack": true, "spacer_237nm": true, "sample_planes_and_monitors": true, "complex_field_output_configuration": true}`.

Pillar local 5 nm mesh coverage: `[{"pillar": 1, "diameter_nm": 110, "override_x_span_nm": 175.00000000000003, "override_y_span_nm": 175.00000000000003, "full_xy_pillar_coverage": true}, {"pillar": 2, "diameter_nm": 145, "override_x_span_nm": 125.00000000000001, "override_y_span_nm": 125.00000000000001, "full_xy_pillar_coverage": false}, {"pillar": 3, "diameter_nm": 225, "override_x_span_nm": 215.0, "override_y_span_nm": 215.0, "full_xy_pillar_coverage": false}, {"pillar": 4, "diameter_nm": 105, "override_x_span_nm": 170.0, "override_y_span_nm": 170.0, "full_xy_pillar_coverage": true}, {"pillar": 5, "diameter_nm": 185, "override_x_span_nm": 200.00000000000003, "override_y_span_nm": 200.00000000000003, "full_xy_pillar_coverage": true}, {"pillar": 6, "diameter_nm": 215, "override_x_span_nm": 165.0, "override_y_span_nm": 165.0, "full_xy_pillar_coverage": false}]`.

### K6V1_S39

Classification: C. Existing candidate path: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1\K6V1_S39\attempt_001\setup\runtime.fsp`.

SHA256: `5e7beeeaa5d87b11f687efd279b10cdcf5eb054bea6c8ace9863f660f9c476c2`; bytes: 522322.

Ordered D1-D6 (nm): [175, 100, 125, 120, 100, 230]. Geometry SHA256: `7c582e2c53da5394d6cdf446a1ee9e16a970264b1fc78312d3f304df52403729`.

Fresh LOAD: PASS. Frozen scientific mesh validation: FAIL. FSP hash and mtime unchanged.

Generating commit: unknown. Report-associated commit f0cd93d1407d080bf93259fd1153cb664235e8c8 is not claimed as the FSP generation commit.

Readback checks: `{"ordered_geometry": true, "pillar_height_and_material": true, "mdc_stack": true, "spacer_237nm": true, "sample_planes_and_monitors": true, "complex_field_output_configuration": true}`.

Pillar local 5 nm mesh coverage: `[{"pillar": 1, "diameter_nm": 175, "override_x_span_nm": 175.00000000000003, "override_y_span_nm": 175.00000000000003, "full_xy_pillar_coverage": true}, {"pillar": 2, "diameter_nm": 100, "override_x_span_nm": 125.00000000000001, "override_y_span_nm": 125.00000000000001, "full_xy_pillar_coverage": true}, {"pillar": 3, "diameter_nm": 125, "override_x_span_nm": 215.0, "override_y_span_nm": 215.0, "full_xy_pillar_coverage": true}, {"pillar": 4, "diameter_nm": 120, "override_x_span_nm": 170.0, "override_y_span_nm": 170.0, "full_xy_pillar_coverage": true}, {"pillar": 5, "diameter_nm": 100, "override_x_span_nm": 200.00000000000003, "override_y_span_nm": 200.00000000000003, "full_xy_pillar_coverage": true}, {"pillar": 6, "diameter_nm": 230, "override_x_span_nm": 165.0, "override_y_span_nm": 165.0, "full_xy_pillar_coverage": false}]`.

## OPEN ISSUES

Actual objects use mixed 5/10/15/20 nm overrides. The local pillar mesh widths retain the old W2H geometry dimensions and do not cover all approved enlarged pillars. See complete fresh LOAD audit and approved 5 nm baseline comparison. Global dx/dy/dz properties in auto non-uniform mode are configuration values, not a solved mesh cell-spacing measurement. No solved mesh was generated.

The exact existing FSP-generating code/commit has not been recovered. A current frozen S35/S39 regeneration builder was not established. No replacement FSP was generated and no scientific contract was changed. Material object assignments match Native-M1 names; material sampled-data provenance was not independently closed.

## EXPECTED TRUTH

PW_GPU_MONITOR_TRUTH_SCHEMA_V1: MON_IN, MON_PRENP, MON_POSTNP require Ex/Ey/Ez/Hx/Hy/Hz; MON_REFLECTION requires signed reflected power. Sample planes -100/1150/1800/-400 nm; normalization reference planes -50/1202/1722 nm, carried by the external frozen contract. No solver truth is included.

## EVIDENCE

`D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_GPU_RUNNER_CANARY_INPUT_HANDOFF_V1_LOAD_ONLY_AUDIT.json` (SHA256 `32da8bee19316f7c37a3bb23e5d53beac9261840f992f0b66328fbcad4e6fcfc`). Includes all loaded object properties, supplementary source/monitor/global settings and baseline comparison. Historical case.json, setup_readback, STAGE1_PREENTRY_AUDIT and terminal evidence declare zero scientific entries; these are provenance only.

## GIT

Source branch work/mdc-np-coupling-ml-v1, HEAD defae390edf4335595897ece5b1cbaba850f429a, ahead/behind 0	0. Existing tracked tree unchanged. Only new handoff evidence files were written; unrelated untracked files preserved. No commit/push.

## NEXT

HANDOFF_TO_APCD_GPU_PRODUCTION_RUNNER_V1 — not executed; current candidates are not approved Runner inputs.
