from __future__ import annotations
import csv,json,hashlib,re,sys
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); OUT=ROOT/r'outputs\np_k6_m5_fullk6_forward_v0'; ORDERS=[-3,-2,-1,0,1,2,3]; WLS=list(range(445,456))
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def csvr(p):
 with open(p,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def main():
 checks={}
 pre=OUT/'NP_K6_FULLK6_FORWARD_V0_PREREG_V1.json'; preh=OUT/'preregistration_sha256.json'; run=OUT/'training_run_manifest.json'; auth=load(OUT/'authority_audit.json'); schema=load(OUT/'order_schema_audit.json'); ext=load(OUT/'external_set_registry.json'); zero=load(OUT/'solver_zero_audit.json')
 checks['prereg_hash']=sha(pre)==load(preh)['sha256']; checks['prereg_precedes_fit']=load(run)['fit_started_utc']>load(pre)['created_utc']; checks['exact_286_rows']=auth['normalized_authority_rows']==286; checks['13_geometries']=auth['geometry_count']==13; checks['26_cases']=auth['case_count']==26; checks['exact_wavelengths']=auth['wavelengths']==WLS; checks['labels_true']=auth['all_m5_training_label_true'] and auth['quality_gate_pass_all'] and auth['diagnostic_only_all_false']; checks['duplicate_conflicting_provenance']=auth['duplicate_conflicting_provenance']==0; checks['order_contract']=schema['all_complete'] and schema['orders']==ORDERS and schema['rows_per_case']==77 and schema['order_sum_mismatch_max']<1e-12; checks['external_metadata_only']=ext['geometry_count']==12 and ext['sealed_hf_target_read']==0 and not ext['training_geometry_intersection']; checks['solver_zero']=all(zero[k]==0 for k in ['fdtd_run_calls','lumapi_solver_run_calls','new_hf_acquisition','sealed_hf_target_reads','inverse_design_artifacts']); checks['incident_ux_zero']=load(pre)['input_contract']['u_x_values']==[0.0]; checks['output_contract']=load(pre)['output_contract']['tracked_orders']==ORDERS
 folds=csvr(OUT/'fold_manifest.csv'); checks['13_geometry_folds']=len(folds)==13 and len(set(x['held_out_geometry'] for x in folds))==13 and all(int(x['test_rows'])==22 for x in folds)
 oof=csvr(OUT/'oof_predictions.csv'); checks['oof_rows']=len(oof)==286*5+286*4*3; checks['oof_no_nan_truth']=all(all(x[k] not in ('','nan','NaN') for k in ['true_R','true_T']+[f'true_eta_m{m:+d}' for m in ORDERS]) for x in oof); checks['oof_model_identity']=set(x['model'] for x in oof)=={'lf_only','direct_mlp','resmlp','residual_mlp','circular_cnn'}
 checks['lf_provenance_solver_zero']=load(OUT/'lf_baseline_provenance.json')['solver_calls']==0; checks['complex_status']=load(OUT/'complex_feasibility_audit.json')['status']=='COMPLEX_ORDER_CONTRACT_NOT_YET_READY'; checks['decision_status']=load(OUT/'m5_decision.json')['status']=='NP_K6_M5_FULLK6_FORWARD_V0_COMPLETE_EXTERNAL_HF_AUTHORIZATION_READY' and load(OUT/'m5_decision.json')['surrogate_frozen'] is False; _src=(ROOT/r'scripts\np_k6_m5_fullk6_forward_v0.py').read_text(encoding='utf-8').lower(); checks['no_lumapi_import']='import lumapi' not in _src and 'from lumapi' not in _src; checks['no_inverse_artifacts']=not any('inverse' in p.name.lower() for p in OUT.iterdir());
 result={'validator':'np_k6_m5_fullk6_forward_v0','checks':checks,'all_pass':all(checks.values()),'solver_calls':0,'sealed_target_reads':0}
 (OUT/'validator_report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(result,indent=2)); return 0 if result['all_pass'] else 1
if __name__=='__main__': raise SystemExit(main())
