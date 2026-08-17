import csv,json,hashlib
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); O=ROOT/r'outputs\np_k6_m9_22g_forward_retraining_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
errors=[]; pr=O/'NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json'; rec=json.loads((O/'preregistration_sha256.json').read_text())
if rec['sha256']!=sha(pr):errors.append('prereg_hash')
hf=rows(ROOT/r'outputs\np_k6_m8a_primary2_closeout_v1\hf22_formal_development_484rows.csv'); lf=rows(O/'lf22_full_vector_authority.csv')
hk={(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in hf}; lk={(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in lf}
geos=sorted({r['geometry_id'] for r in hf})
if len(hf)!=484 or len(lf)!=484 or len(geos)!=22 or hk!=lk:errors.append('authority')
if len(rows(O/'fold_manifest.csv'))!=22 or len(rows(O/'oof_predictions_22g.csv'))!=4356 or len(rows(O/'model_metrics_raw.csv'))!=9:errors.append('oof')
z=json.loads((O/'solver_zero_audit.json').read_text())
if any(z.get(k,0)!=0 for k in ['fdtd_run_calls','lumapi_solver_run_calls','new_development_hf','external_hf_calls','sealed_hf_target_reads','inverse_design']):errors.append('solver')
e=json.loads((O/'m9_external_hf_readiness.json').read_text())
if e.get('training_intersection') or e.get('sealed_target_reads')!=0 or e.get('external_target_reads')!=0:errors.append('external')
report={'status':'PASS' if not errors else 'FAIL','errors':errors,'preregistration_sha256':sha(pr),'hf_rows':len(hf),'lf_rows':len(lf),'geometries':len(geos),'oof_rows':len(rows(O/'oof_predictions_22g.csv')),'folds':len(rows(O/'fold_manifest.csv')),'models':len(rows(O/'model_metrics_raw.csv')),'solver_calls':0,'sealed_target_reads':0,'external_target_reads':0}
(O/'m9_final_validator_report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
if errors: raise SystemExit(1)
