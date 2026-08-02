# NP_K6_ML_D0_DATABASE_FOUNDATION_V1

状态: NP_K6_ML_D0_DATABASE_FOUNDATION_V1_COMPLETE

本阶段仅构建离线数据库、合同、确定性 split、pilot 清单和未来 HF task ledger；没有调用 solver。

## 数据库

- K6 geometry master: 296010 rows, diameters D100–D230 at 5 nm, strict increasing sextets.
- LF spectral records: 3256110 geometry×wavelength rows; m=-3..+3 DFT proxy arrays in 60 compressed NPZ chunks.
- Wavelength grid: 445–455 nm, 1 nm; polarization: x-only.
- LF labels are explicitly `LOW_FIDELITY_SINGLE_PILLAR_DFT_PROXY`, not coupled K6 truth or production labels.

## Split and pilot

- Split counts: development=236808, validation=29601, sealed_test=29601.
- Pilots: 48 development + 12 sealed-test.
- Future HF tasks: 120 (60 geometries × x/y), all blocked by production mesh.
- Sealed-test geometry hashes are isolated from development selection.

## Contracts

- Native-M1 material IDs remain APCD_TIO2_NATIVE_M1 / APCD_SIO2_NATIVE_M1.
- production_mesh_id=PENDING_NUMERICAL_FIDELITY_FREEZE.
- Existing RUN3A/B/C and material diagnostics remain diagnostic-only; TiO2-only/SiO2-only numerical forensics are deferred.
- No HF labels, DOE execution, or model training was performed.

## Evidence paths

- Database root: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_ml_d0_database_foundation_v1`
- Design master: `k6_design_space_master.csv.gz`
- LF manifest: `k6_lf_arrays_manifest.json`
- Pilot manifest: `k6_hf_pilot_geometry_manifest.csv/.json`
- HF ledger: `k6_hf_task_ledger.csv/.json`
- Dataset contract: `k6_hf_dataset_contract_v1.json`
- Model feature contract: `k6_model_feature_contract_v1.json`
- Checksum manifest: `database_checksum_manifest.json`

Next action: AUTHORIZE_PRODUCTION_MESH_GATE_FOR_K6_HF_PILOT.
