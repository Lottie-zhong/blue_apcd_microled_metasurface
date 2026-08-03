import csv,json,hashlib
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');P=R/'outputs/lp_ml_dataset_v1/plans';A=R/'outputs/lp_ml_dataset_v1/analysis'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
full=read(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv'); smoke={r['candidate_id'] for r in read(P/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv')}
prod=read(R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1/candidate_wavelength_jones_v1.csv'); accepted={r['candidate_id'] for r in prod}
failed='LPML_R1_GLOBAL_SOBOL_054'; assert failed not in accepted
untouched=[r for r in full if r['candidate_id'] not in accepted and r['candidate_id']!=failed]; assert len(untouched)==194
frow=[r for r in full if r['candidate_id']==failed][0]; rows=[]
rows.append({**frow,'run_polarizations':'y','recovery_scope':'MISSING_Y_ONLY','supersedes_subrun_id':failed+'_y','supersedes_attempt_id':'LP_ML_ROUND1_PRODUCTION_ATTEMPT1_V1','old_status':'ENTERED_TRUE_ACCEPTED_FALSE_NO_CHECKPOINT','recovery_status':'AUTHORIZED_RECOVERY_PLANNED'})
for r in untouched: rows.append({**r,'run_polarizations':'x,y','recovery_scope':'UNTOUCHED_PRODUCTION','supersedes_subrun_id':'','supersedes_attempt_id':'','old_status':'UNTOUCHED','recovery_status':'AUTHORIZED_RECOVERY_PLANNED'})
assert len(rows)==195 and len({r['exact_geometry_hash_sha256'] for r in rows})==195 and not smoke.intersection({r['candidate_id'] for r in rows})
fields=[]
for r in rows:
 for k in r:
  if k not in fields:fields.append(k)
out=P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv'
with out.open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
auth='DB0808DD31935CDE7A995CA694D2F22212A1F375E8D29B47BB447C523FF10697'
manifest={'plan_version':'LP_ML_ROUND1_RECOVERY_389_V1','authorization_source':'goal-objective:a92dfe02-9bd5-4b77-bcb3-d1882d8adf94','authorization_sha256':auth,'recovery_attempt_id':'LP_ML_ROUND1_RECOVERY_ATTEMPT1_V1','source_remaining_plan_sha256':sha(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv'),'recovery_plan_sha256':sha(out),'old_production_attempt_id':'LP_ML_ROUND1_PRODUCTION_ATTEMPT1_V1','old_failed_subrun':failed+'_y','old_failed_checkpoint_present':False,'candidate_count':195,'first_candidate':failed,'first_run_polarizations':'y','untouched_candidate_count':194,'untouched_run_polarizations':'x,y','new_entered_ceiling':389,'new_subrun_budget':{'recovery_054_y':1,'untouched_full_xy':388,'total':389},'old_entered_evidence_retained':True,'no_overwrite_old_attempt':True,'no_geometry_replacement':True,'no_plan_expansion':True,'wavelengths_nm':[450.0+i*.5 for i in range(9)],'solver_calls_this_freeze':0}
jsonp=P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.json';jsonp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
contract={'execution_contract_version':'LP_ML_ROUND1_RECOVERY_EXECUTION_V1','recovery_attempt_id':manifest['recovery_attempt_id'],'authorization_source':manifest['authorization_source'],'authorization_sha256':auth,'plan_csv_path':str(out.relative_to(R)).replace('\\','/'),'plan_csv_sha256':sha(out),'exact_entered_ceiling':389,'first_gate':{'candidate_id':failed,'polarization':'y','must_accept_before_continue':True,'on_failure':'STOP_NO_RETRY_NO_CONTINUATION'},'untouched_continuation':{'geometries':194,'polarizations_per_geometry':['x','y'],'subruns':388},'physics_contract':'reuse frozen broadband weighted-G0 Native-M1 contract','old_attempt_preservation':{'old_staging_read_only':True,'old_failed_record_retained':True,'old_accepted_x_not_rerun':True},'forbidden':['abs(T)','clipping','interpolation','model_fill','candidate_replacement','plan_expansion','D9','K6','Batch B','active learning'],'sampling':{'source_start_nm':450.0,'source_stop_nm':454.0,'frequency_points':9,'step_nm':0.5},'solver_calls_at_freeze':0}
contractp=P/'lp_ml_dataset_v1_round1_recovery_execution_contract_v1.json';contractp.write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(A/'lp_ml_round1_recovery_supersession_ledger_v1.json').write_text(json.dumps({'old_attempt':'LP_ML_ROUND1_PRODUCTION_ATTEMPT1_V1','new_attempt':manifest['recovery_attempt_id'],'old_failed_subrun':failed+'_y','old_record_retained':True,'new_plan_sha256':sha(out),'new_contract_sha256':sha(contractp),'candidate_replacement':False,'old_054_x_rerun':False,'solver_calls':0},indent=2,sort_keys=True)+'\n',encoding='utf-8')
(A/'lp_ml_round1_untouched_production_accounting_v1.json').write_text(json.dumps({'source_plan_count':240,'previously_complete_production':45,'failed_geometry':failed,'untouched_count':194,'untouched_full_xy_subruns':388,'recovery_missing_y':1,'total_new_budget':389,'candidate_ids':[r['candidate_id'] for r in untouched]},indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'candidate_count':len(rows),'failed_y':1,'untouched':len(untouched),'budget':389},indent=2))
