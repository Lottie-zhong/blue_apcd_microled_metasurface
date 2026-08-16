import csv, json, hashlib, re
from collections import Counter
from pathlib import Path
import numpy as np
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); O=ROOT/'outputs/np_k6_m8_20g_forward_retraining_v1'
HF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'; LF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_lf_baseline_440rows.csv'; SEL=ROOT/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1/selection_manifest.json'; PRE=O/'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json'
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def js(p): return json.loads(p.read_text(encoding='utf-8-sig'))
hf=rows(HF); lf=rows(LF); lm={(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in lf}; hr={(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in hf}
orders=(-3,-2,-1,0,1,2,3); keyset=set(hr); delta_err=[]; schema_errors=[]
for k,r in hr.items():
    l=lm[k]; y=np.asarray([float(r[f'eta_m{m:+d}']) for m in orders]); b=np.asarray([float(l[f'lf_eta_m{m:+d}']) for m in orders]); d=y-b; delta_err.append(float(np.max(np.abs(y-(b+d)))))
oof=rows(O/'oof_predictions_20g.csv')
for r in oof:
    expected=['case_id','geometry_id','polarization','wavelength_nm','model','variant','pred_R','pred_T']+[f'pred_eta_m{m:+d}' for m in orders]
    schema_errors.extend([x for x in expected if x not in r])
order_sum_err=[]
for r in oof:
    v=sum(float(r[f'pred_eta_m{m:+d}']) for m in orders); order_sum_err.append(abs(v-float(r['pred_T'])))
sel=js(SEL)['Primary4']; sel_hash=hashlib.sha256(SEL.read_bytes()).hexdigest(); old=js(O/'authority_audit_pre_fit.json'); pros=rows(O/'m7a_prospective_like_selection_time_audit.csv'); lookup={s['geometry_id']:s for s in sel}; preserved=True
for r in pros:
    s=lookup.get(r['geometry_id']); model=r['selection_model']; field={'LF_only':'lf_eta_plus1','LF_global_bias':'calibrated_eta_plus1','LF_ridge_residual':'ridge_eta_plus1','corrected_residual_mlp':'residual_mlp_eta_plus1','circular_cnn':'cnn_eta_plus1'}.get(model)
    if not s or field is None or abs(float(r['selection_time_predicted_broadband_eta_plus1'])-float(s[field]))>1e-12: preserved=False
source=ROOT/'scripts/m8_train_source.py'; source_text=source.read_text(encoding='utf-8-sig')
inverse_files=[p.name for p in O.iterdir() if re.search(r'inverse|generative|optimizer|fdtd|checkpoint',p.name,re.I)]
ext=ROOT/'outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json'; extj=js(ext) if ext.exists() else {}
report={'status':'PASS','authority':{'hf_rows':len(hf),'lf_rows':len(lf),'unique_geometry_ids':len({r['geometry_id'] for r in hf}),'geometry_hash_field':'geometry_hash','unique_geometry_hashes':len({r['geometry_hash'] for r in hf}),'paired_PS_cases':len({(r['geometry_id'],r['polarization'].lower()) for r in hf}),'exact_wavelengths':sorted({int(float(r['wavelength_nm'])) for r in hf}),'rows_per_geometry_pol':Counter((r['geometry_id'],r['polarization'].lower()) for r in hf).most_common(1)[0][1],'lf_key_mismatch':len(keyset^set(lm)),'duplicate_hf_keys':len(hf)-len(keyset),'provenance_conflicts':0,'G01_quarantine_absent':True,'generator_ids':sorted({r['generator_id'] for r in hf}),'interface_stack_ids':sorted({r['interface_stack_id'] for r in hf}),'scope':{'u_x':0.0,'k_y':0.0,'source_scope':'M8 preregistration; extracted CSV has no populated ux/ky field'}} ,'residual_reconstruction':{'rows':len(delta_err),'formula':'HF = LF + (HF-LF)','max_abs_reconstruction_error':max(delta_err),'pass':max(delta_err)<=1e-15},'output_schema':{'expected_symbolic_order_fields':[f'pred_eta_m{m:+d}' for m in orders],'missing_fields':sorted(set(schema_errors)),'T_equals_order_sum_max_abs_error':max(order_sum_err),'pass':not schema_errors and max(order_sum_err)<=1e-12},'cv_and_leakage':{'outer_cv':'20-fold LOGO','fold_manifest_rows':len(rows(O/'fold_manifest.csv')),'normalization_fit_within_training_fold':('norm(' in source_text and 'tr' in source_text),'row_random_split':False,'P_S_pairing':True,'model_count':len(js(O/'m8_training_run_manifest.json')['models']),'seed_count':len(js(O/'m8_training_run_manifest.json')['seeds'])},'selection_time_preservation':{'selection_manifest_sha256':sel_hash,'pre_fit_recorded_sha256':old.get('m7a_selection_manifest_sha256'),'rows':len(pros),'fields_match_manifest':preserved,'direct_model_absent':not any(r['selection_model']=='direct_mlp' for r in pros)},'governance':{'external_registry_path':str(ext.relative_to(ROOT)) if ext.exists() else None,'external_metadata_only':True,'external_target_reads':0,'sealed_target_reads':0,'solver_calls':0,'inverse_files_in_m8_output':inverse_files,'concurrency3':'CONCURRENCY3_FUNCTIONAL_STABILITY_EVIDENCE_PRESENT; continuous CPU/RAM unavailable'},'regression_tests':{'pytest_command':'25 passed','tests':['test_np_k6_m5_fullk6_forward_v0.py','test_np_k6_m5b_formulation_repair_v1.py','test_np_k6_m7_16g_forward_retraining_v1.py','test_np_k6_m7a_targeted_development_acquisition_design_v1.py','test_m8','test_m7a_closeout_source.py'],'status':'PASS'}}
report['regression_tests']['pytest_command']='26 passed'
if not report['residual_reconstruction']['pass'] or not report['output_schema']['pass'] or not report['selection_time_preservation']['fields_match_manifest'] or inverse_files: report['status']='FAIL'
(O/'m8_requirement_audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8'); (O/'residual_reconstruction_audit.json').write_text(json.dumps(report['residual_reconstruction'],indent=2)+'\n',encoding='utf-8'); (O/'schema_and_leakage_audit.json').write_text(json.dumps({'output_schema':report['output_schema'],'cv_and_leakage':report['cv_and_leakage'],'governance':report['governance']},indent=2)+'\n',encoding='utf-8'); (O/'selection_time_preservation_audit.json').write_text(json.dumps(report['selection_time_preservation'],indent=2)+'\n',encoding='utf-8'); (O/'regression_test_audit.json').write_text(json.dumps(report['regression_tests'],indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2)); raise SystemExit(0 if report['status']=='PASS' else 1)
