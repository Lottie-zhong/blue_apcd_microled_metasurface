# NP K6 M2 Batch1 HF acquisition v1

Status: `NP_K6_M2_BATCH1_HF_ACQUISITION_COMPLETE_RETRAIN_READY`.

The six selected development geometries were acquired for both p and s polarization at the exact 445–455 nm wavelengths. The logical batch contains 12 accepted executions and 132 formal observations. G04-P uses the explicitly authorized infrastructure-loss replacement execution `G04_P_BATCH1_INFRA_RECOVERY_RECOMPUTE_V1`; the original consumed execution remains preserved and excluded from labels.

Physical solver accounting: 13 invocations = 12 accepted numerical executions + 1 lost infrastructure execution. No attempt_002, automatic rerun, sealed access, or training was used.

All 12 cases have independent read-only reload, stable post-FSP, exact 11-point finite spectra, and V2 gates passed. The 132-row dataset and 198-row merged development dataset are under `outputs/np_k6_m2_batch1_hf_dataset_v1/` and `outputs/np_k6_m2_batch1_merged_development_dataset_v1/`. The p/s audit is descriptive and remains `P_S_SIMILARITY_CANDIDATE_PENDING_MORE_HF_DATA`; it does not authorize bulk MDC-compatible training.

`pilot_training_authorized=true`, `bulk_mdc_compatible_training_authorized=false`, `real_training_started=false`, and `checkpoint_count=0`.
