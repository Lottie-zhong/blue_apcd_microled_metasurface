import json
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');O=R/'outputs/lp_ml_dataset_v1';A=O/'analysis';S=O/'staging/lp_ml_dataset_v1_round1_continuation_attempt1_v1'
def j(p): return json.loads(p.read_text(encoding='utf-8'))
acc=j(S/'final_sentinel_v1.json'); man=j(A/'lp_ml_dataset_v1_round1_complete_255_manifest_v1.json'); mlp=j(A/'lp_ml_round1_full_residual_mlp_5seed_v1.json')
proposal={'proposal_version':'LP_ML_DATASET_V1_ROUND2_OFFLINE_PROPOSAL_V1','status':'OFFLINE_ONLY_NOT_AUTHORIZED','solver_authorized':False,'runnable_solver_package':False,'candidate_count':0,'basis':'255 clean geometry / 2295 formal weighted-G0 rows; geometry 054 permanently quarantined','no_active_learning':True,'no_inverse_design':True,'no_d9':True}
(A/'lp_ml_dataset_v1_round2_offline_acquisition_proposal_v1.json').write_text(json.dumps(proposal,indent=2)+'\n',encoding='utf-8')
report=R/'reports/lp_ml_dataset_v1_round1_complete_255_audit_v1.md'
report.write_text(f'''# LP ML Dataset v1 — Round-1 complete 255-geometry audit

## Status
`LP_ML_ROUND1_COMPLETE_DATASET_READY_OFFLINE_ONLY`

## Geometry 054 closeout
`LPML_R1_GLOBAL_SOBOL_054` is permanently quarantined. The prior production `054_y` failure and its single authorized recovery attempt remain retained; no third retry occurred. The orphan `054_x` checkpoint is excluded. No 054 row is present in the 255-geometry assembly.

## Continuation accounting
- Planned: 194 geometries / 388 x-y subruns / 450–454 nm at 0.5 nm.
- Entered: {acc.get('solver_entered')}; accepted: {acc.get('successful_accepted_subruns')}; failed: {acc.get('failed_subruns')}; quarantined: {len(acc.get('quarantined_cases',[]))}.
- Outcome: `{acc.get('outcome')}`; no replacement, retry, or systemic failure.

## Complete dataset
- Smoke 16 + prior clean production 45 + continuation 194 = **255 geometries / 2295 rows**.
- Nine rows per geometry, 450.0–454.0 nm at 0.5 nm step; complete raw complex Jones; no model-filled rows; positive-T gate passes.
- Strata: {man['strata_counts']}.
- Geometry-level deterministic 70/15/15 split; normalization statistics use training geometries only.

## From-scratch models
ExtraTrees, HistGradientBoosting and simple MLP use the seven frozen features and eight raw Jones components. Metrics are in `analysis/lp_ml_round1_full_tree_and_simple_baselines_v1.json`.

Five-seed residual MLP: CUDA `{mlp.get('cuda_name')}`, 7→256 with four residual blocks (SiLU/LayerNorm/dropout 0.03), seeds 11/22/33/44/55, fresh initialization, no warm start. Ensemble test MAE={mlp.get('ensemble_test',{}).get('mae')}, RMSE={mlp.get('ensemble_test',{}).get('rmse')}, Frobenius mean={mlp.get('ensemble_test',{}).get('frobenius_mean')}, phase circular MAE={mlp.get('ensemble_test',{}).get('phase_circular_deg_mae')} deg.

## Round-2 boundary
`lp_ml_dataset_v1_round2_offline_acquisition_proposal_v1.json` is offline-only with zero candidates and `solver_authorized=false`; no active learning, inverse design, D9, K6, Batch B, old Batch2, or solver expansion was launched.
''',encoding='utf-8')
print(report)
