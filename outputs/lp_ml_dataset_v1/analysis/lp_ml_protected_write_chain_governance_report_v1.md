# LP protected-report write-chain governance and Round-2 evidence review
 
 ## Status
 
 LP_PROTECTED_WRITE_CHAIN_HARD_GATE
 
 ## Incident freeze
 
 Incident ID: LP_PROTECTED_REPORT_POST_EXCEPTION_WRITE_INCIDENT_V1. The earlier accepted byte-identity exception (171033e0d2c73865d0f8610e81d5a33de56d7deb79d8d38aa2f925f7e17e8321) is distinct from the later unauthorized writes. The first protected report has current SHA 9e46a7bd1927d65adc3a9cf9192040e7d239b839ed516adcd96870bf64bfcd02 and the second ae3b13341547e13ca85ca763ed8265591c100ac1a78c555de1c8378816a33708; four first-report USN writes and three second-report USN writes are retained in the incident ledger. No protected report was restored or modified by this task.
 
 ## Writer root cause and remediation
 
 The two identified writers were audited and patched. They had explicit write_text report writes; no import side effect, scheduler, hook, or second writer was found. Defaults now point to derived output trees and protected targets hard-fail before writing. Guard tests: 6/6. LP governance shard: 78 passed, 334 deselected, 0 failed, 0 solver calls.
 
 ## Round-2 artifact integrity
 
 64 planned geometries, 576 prospective rows, 319 merged geometries and 2871 merged rows were independently counted. Staging entered/accepted is 128/128. Model-filled physics rows: 0; split-leakage candidates: 0; geometry-054 absent: False. Existing accepted ledger, prediction-freeze, checkpoint and dataset artifacts were read-only audited. The protected-report drift remains a contamination gate.
 
 ## Independent metric recomputation
 
 Round-1 frozen test (342 rows), Round-2 model on the same test, Round-2 external test (72 rows), and the full 576-row prospective cohort were recomputed from saved checkpoints. On the same frozen test, Round-1 Frobenius MAE/RMSE/max = 0.045942/0.054744/0.238274; Round-2 = 0.056207/0.064816/0.232395. Round-2 external Frobenius = 0.104096, relative mean/P90/P95 = 0.077207/0.111837/0.116589, phase MAE = 2.6088 degrees. Cohort Frobenius MAE = 0.078121, phase MAE = 0.7524 degrees. Txx/Tyy/leakage/sigma-ratio residuals, actual projection-error distribution, and uncertainty-error correlations are in the JSON audit. Predicted projection error is explicitly marked unavailable from the checkpoint-only recomputation; no guessed fill was used.
 
 The same-test recomputation does not show a universal <=10% improvement gate; results remain stratum-dependent. This is evidence review, not promotion.
 
 ## Outputs
 
 - outputs/lp_ml_dataset_v1/analysis/lp_protected_report_post_exception_write_incident_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_protected_report_writer_chain_audit_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_protected_artifact_writer_remediation_report_v1.md
 - outputs/lp_ml_dataset_v1/analysis/lp_protected_artifact_static_scan_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_artifact_integrity_audit_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_metric_recomputation_audit_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_sharded_pytest_manifest_v1.json
 - outputs/lp_ml_dataset_v1/analysis/lp_ml_protected_write_chain_governance_outcome_v1.json
 
 ## Hard gates
 
 Offline-only; solver calls = 0. No Round-3, inverse design, six-bin FDTD, K6, D9, model retraining, canonical merge, or protected-report rewrite was performed. Existing Round-2 outcome remains LP_ML_ROUND2_HARD_GATE because the post-start protected-evidence incident is unresolved.
 