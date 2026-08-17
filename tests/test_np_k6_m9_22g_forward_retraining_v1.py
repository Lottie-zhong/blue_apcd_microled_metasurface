import csv,json,hashlib
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); O=ROOT/r'outputs\np_k6_m9_22g_forward_retraining_v1'
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def test_m9_authority_and_zero_solver():
 assert len(rows(ROOT/r'outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv'))==484
 assert len(rows(O/'lf22_full_vector_authority.csv'))==484
 assert json.loads((O/'lf22_full_vector_authority_gate.json').read_text())['full_vector_gate'] is True
 z=json.loads((O/'solver_zero_audit.json').read_text())
 assert all(z[k]==0 for k in ['fdtd_run_calls','lumapi_solver_run_calls','new_development_hf','external_hf_calls','sealed_hf_target_reads','inverse_design'])
def test_m9_logo_and_outputs():
 assert len(rows(O/'fold_manifest.csv'))==22
 assert len(rows(O/'oof_predictions_22g.csv'))==4356
 assert len(rows(O/'model_metrics_raw.csv'))==9
 assert len(rows(O/'ranking_metrics.csv'))==9
 assert json.loads((O/'m9_final_validator_report.json').read_text())['status']=='PASS'
def test_external_metadata_only_and_ps_contract():
 e=json.loads((O/'m9_external_hf_readiness.json').read_text()); assert e['geometry_count']==12 and e['training_intersection']==[] and e['sealed_target_reads']==0
 p=json.loads((O/'ps_coupling_audit_22g.json').read_text()); assert p['pair_count']==242 and p['true_abs_delta_max']>0.5
def test_prereg_before_fit():
 pr=json.loads((O/'preregistration_sha256.json').read_text()); h=hashlib.sha256((O/'NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json').read_bytes()).hexdigest(); assert pr['sha256']==h and pr['fit_started_after_preregistration'] is False
 run=json.loads((O/'m9_training_run_manifest.json').read_text()); assert run['fit_started_after_preregistration'] is True and run['geometries']==22
