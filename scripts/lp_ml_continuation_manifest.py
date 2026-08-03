import csv,json,hashlib
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');P=R/'outputs/lp_ml_dataset_v1/plans';A=R/'outputs/lp_ml_dataset_v1/analysis'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
src=read(P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv'); rows=[r for r in src if r['candidate_id']!='LPML_R1_GLOBAL_SOBOL_054']; assert len(rows)==194 and all(r['run_polarizations']=='x,y' for r in rows)
assert len({r['exact_geometry_hash_sha256'] for r in rows})==194 and 'LPML_R1_GLOBAL_SOBOL_054' not in {r['candidate_id'] for r in rows}
fields=[]
for r in rows:
 for k in r:
  if k not in fields:fields.append(k)
out=P/'lp_ml_dataset_v1_round1_continuation_388_plan_v1.csv'
with out.open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
auth='DB0C5DAA90A009BDD0041D4D16BE0F88B8CCB1EECF57F26464D508475182F0F1'
manifest={'plan_version':'LP_ML_ROUND1_CONTINUATION_388_V1','authorization_source':'goal-objective:0bf27951-dd1b-46c8-bbbb-16595be6dfd8','authorization_sha256':auth,'continuation_attempt_id':'LP_ML_ROUND1_CONTINUATION_ATTEMPT1_V1','source_recovery_plan_sha256':sha(P/'lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv'),'continuation_plan_sha256':sha(out),'candidate_count':194,'subrun_budget':388,'polarizations':['x','y'],'quarantined_candidate':'LPML_R1_GLOBAL_SOBOL_054','no_replacement':True,'no_accepted_rerun':True,'isolated_failure_policy':'entered_false_setup_may_repair; entered_true accepted_false quarantined and continue untouched set; systemic shared-contract failure hard stop','wavelengths_nm':[450.0+i*.5 for i in range(9)],'solver_calls_at_freeze':0}
jsonp=P/'lp_ml_dataset_v1_round1_continuation_388_plan_v1.json';jsonp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
contract={'execution_contract_version':'LP_ML_ROUND1_CONTINUATION_EXECUTION_V1','continuation_attempt_id':manifest['continuation_attempt_id'],'authorization_source':manifest['authorization_source'],'authorization_sha256':auth,'plan_csv_path':str(out.relative_to(R)).replace('\\','/'),'plan_csv_sha256':sha(out),'exact_entered_ceiling':388,'candidate_count':194,'quarantine_054_permanent':True,'old_attempts_read_only':True,'accepted_cases_not_rerun':True,'failure_policy':manifest['isolated_failure_policy'],'physics_contract':'frozen broadband Native-M1 weighted-G0, z=1000 nm, sqrt(T)/norm(weighted Ex,Ey)','forbidden':['abs(T)','clipping','interpolation','model_fill','candidate_replacement','plan_expansion','D9','K6','Batch B','active learning'],'sampling':{'start_nm':450.0,'stop_nm':454.0,'step_nm':0.5,'points':9},'solver_calls_at_freeze':0}
contractp=P/'lp_ml_dataset_v1_round1_continuation_execution_contract_v1.json';contractp.write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n',encoding='utf-8')
(A/'lp_ml_round1_continuation_accounting_freeze_v1.json').write_text(json.dumps({'quarantined_054':True,'continuation_geometries':194,'continuation_subruns_max':388,'previous_clean_geometries':61,'previous_accepted_subruns':123,'solver_calls':0,'new_attempt_id':manifest['continuation_attempt_id']},indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'candidates':len(rows),'subrun_budget':388},indent=2))
