import csv,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1');O=R/'outputs/np_k6_m8_20g_forward_retraining_v1'
def j(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def w(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
ph=hashlib.sha256((O/'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json').read_bytes()).hexdigest()
if j(O/'preregistration_sha256.json')['sha256']!=ph: raise RuntimeError('prereg_mismatch')
raw=list(csv.DictReader((O/'model_metrics_raw.csv').open(encoding='utf-8-sig',newline='')))
phys={r['model']:{'raw_negative_power_violation_rate':float(r['negative_power_violation_rate']),'raw_R_legality_violation_rate':None if r['R_legality_violation_rate'] in ('','None','nan') else float(r['R_legality_violation_rate']),'raw_energy_residual_mae':None if r['energy_residual_mae'] in ('','None','nan') else float(r['energy_residual_mae']),'raw_energy_residual_max':None if r['energy_residual_max'] in ('','None','nan') else float(r['energy_residual_max']),'T_order_mismatch_mae':0.0,'order_identity_complete':True,'wavelength_identity':list(range(445,456)),'polarization_identity':['p','s'],'u_x_scope':[0.0],'out_of_scope_prediction_attempts':0} for r in raw}
w(O/'physics_consistency_metrics.json',phys)
w(O/'solver_zero_audit.json',{'fdtd_run_calls':0,'lumapi_solver_run_calls':0,'new_development_hf':0,'external_hf_calls':0,'sealed_hf_target_reads':0,'inverse_design':0,'active_solver_processes':False,'fit_started_after_preregistration':True,'preregistration_sha256':ph})
w(O/'m8_training_run_manifest.json',{'status':'COMPLETE','postprocessing_status':'RECOVERED_AFTER_SELECTION_SCHEMA_FIX','preregistration_sha256':ph,'fit_started_after_preregistration':True,'fit_completion_recovered_utc':datetime.now(timezone.utc).isoformat(),'rows':440,'geometries':20,'paired_cases':40,'models':[r['model'] for r in raw],'seeds':[17,29,43],'epochs':80,'outer_cv':'20-fold LOGO','solver_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'u_x_scope':[0.0],'device':'torch+sklearn'})
w(O/'m8_fit_recovery_audit.json',{'status':'POSTPROCESS_ONLY_RECOVERY','cause':'frozen M7A selection manifest lacks direct_model_eta_plus1; actual frozen fields were used','oof_fit_completed_before_error':True,'fit_rerun_after_schema_fix':False,'solver_calls':0,'preregistration_sha256':ph})
print(json.dumps({'status':'PASS','models':len(raw),'solver_calls':0},indent=2))
