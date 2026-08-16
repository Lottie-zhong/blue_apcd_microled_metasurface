import csv, json, hashlib
from pathlib import Path

R = Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O = R / 'outputs/np_k6_m8_20g_forward_retraining_v1'
errors = []
def j(name):
    p = O / name
    if not p.exists(): errors.append('missing:'+name); return {}
    return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(name):
    p = O / name
    if not p.exists(): errors.append('missing:'+name); return []
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
prereg_path = O / 'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json'
prereg = j(prereg_path.name)
sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest() if prereg_path.exists() else ''
sha_record = j('preregistration_sha256.json')
if sha_record.get('sha256') != sha: errors.append('preregistration_hash_mismatch')
if sha != 'fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9': errors.append('unexpected_prereg_sha')
auth = j('authority_audit_pre_fit.json')
if auth.get('hf_rows', auth.get('rows')) not in (440, '440'): errors.append('hf_rows')
if auth.get('unique_geometries', auth.get('geometries')) not in (20, '20'): errors.append('geometries')
solver = j('solver_zero_audit.json')
for k in ('solver_calls','fdtd_run_calls','lumapi_run_calls','external_hf_solver_calls','sealed_target_reads'):
    if solver.get(k, 0) not in (0, '0'): errors.append(k)
pred = rows('oof_predictions_20g.csv')
if len(pred) != 440*9: errors.append('oof_row_count:'+str(len(pred)))
keys = {(r.get('geometry_id'), r.get('polarization'), r.get('wavelength_nm'), r.get('model')) for r in pred}
if len(keys) != len(pred): errors.append('oof_duplicate_keys')
models = sorted({r.get('model') for r in pred})
if len(models) != 9: errors.append('model_count:'+str(models))
folds = rows('fold_manifest.csv')
fold_geo = {r.get('heldout_geometry') or r.get('held_out_geometry') or r.get('test_geometry') or r.get('geometry_id') for r in folds}
if len(folds) != 20 or len(fold_geo) != 20: errors.append('fold_manifest')
raw = rows('model_metrics_raw.csv')
if len(raw) != 9: errors.append('raw_metric_models')
by_seed = rows('model_metrics_by_seed.csv')
if len(by_seed) != 27: errors.append('seed_metric_rows')
if 'G01' in json.dumps(j('m8_external_promotion_decision.json')) and 'quarantine' in json.dumps(j('m8_external_promotion_decision.json')).lower(): errors.append('g01_quarantine')
manifest = j('m8_training_run_manifest.json')
if manifest.get('status') != 'COMPLETE' or manifest.get('outer_cv') != '20-fold LOGO' or manifest.get('geometries') not in (20, '20') or manifest.get('seeds') not in ([17,29,43], ['17','29','43']): errors.append('training_manifest')
decision = j('m8_external_promotion_decision.json')
allowed = {'EXTERNAL_HF_PROMOTION_READY','MORE_TARGETED_DEVELOPMENT_HF_REQUIRED','FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED','MODEL_FORMULATION_REQUIRES_REVISION'}
if decision.get('final_state') not in allowed: errors.append('decision_state')
if decision.get('external_hf_authorized', False) is True: errors.append('external_hf_authorized')
review = j('m8_promotion_review.json')
if review.get('solver_calls', 0) not in (0,'0'): errors.append('review_solver_calls')
for audit_name in ('authority_full_audit.json','m8_requirement_audit.json','residual_reconstruction_audit.json','schema_and_leakage_audit.json','selection_time_preservation_audit.json','regression_test_audit.json'):
    audit = j(audit_name)
    if audit_name == 'm8_requirement_audit.json' and audit.get('status') != 'PASS': errors.append('requirement_audit')
    if audit_name == 'authority_full_audit.json' and audit.get('status') != 'PASS': errors.append('authority_full_audit')
    if audit_name == 'residual_reconstruction_audit.json' and not audit.get('pass', False): errors.append('residual_reconstruction')
    if audit_name == 'selection_time_preservation_audit.json' and not audit.get('fields_match_manifest', False): errors.append('selection_time_preservation')
    if audit_name == 'regression_test_audit.json' and audit.get('status') != 'PASS': errors.append('regression_audit')
for name,expected in (('common_HF16_full_metric_delta.csv',144),('common_HF16_full_learning_value.csv',9),('new4_heldout_full_difficulty.csv',36),('hf20_ps_truth_distribution_summary.csv',24),('residual_structure_oof_by_geometry.csv',1120)):
    if len(rows(name)) != expected: errors.append(name+'_row_count')
if (O/'m7a_prospective_like_selection_time_audit.csv').exists():
    sel = rows('m7a_prospective_like_selection_time_audit.csv')
    if any(r.get('model') == 'direct_mlp' for r in sel): errors.append('selection_manifest_schema_not_frozen')
result = {'status':'PASS' if not errors else 'FAIL','errors':errors,'preregistration_sha256':sha,'hf_rows':len({(r.get('geometry_id'),r.get('polarization'),r.get('wavelength_nm')) for r in pred}) if pred else 0,'oof_rows':len(pred),'models':models,'folds':len(folds),'seed_rows':len(by_seed),'solver_calls':0,'final_state':decision.get('final_state')}
(O/'m8_final_validator_report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(0 if not errors else 1)
