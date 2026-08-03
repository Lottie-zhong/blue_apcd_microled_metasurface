import csv,json,hashlib
from pathlib import Path
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); P=R/'outputs/lp_ml_dataset_v1/plans'; A=R/'outputs/lp_ml_dataset_v1/analysis'
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
full=rows(P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv'); smoke=rows(P/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv'); smoke_ids={r['candidate_id'] for r in smoke}; remain=[r for r in full if r['candidate_id'] not in smoke_ids]
assert len(full)==256 and len(smoke)==16 and len(remain)==240 and not smoke_ids.intersection({r['candidate_id'] for r in remain})
assert len({r['exact_geometry_hash_sha256'] for r in remain})==240
assert min(float(r['direct_gap_nm']) for r in remain)>=60 and min(float(r['periodic_gap_nm']) for r in remain)>=60 and all(r['manufacturing_pass']=='True' for r in remain)
def write_csv(p,rs):
 fields=[]
 for r in rs:
  for k in r:
   if k not in fields:fields.append(k)
 with p.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)
write_csv(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv',remain)
from collections import defaultdict
def groups(field):
 d=defaultdict(list)
 for r in remain:d[r[field]].append(r['candidate_id'])
 return {k:v for k,v in d.items() if len(v)>1}
canonical_groups=groups('canonical_relative_geometry_hash_sha256'); symmetry_groups=groups('symmetry_equivalence_geometry_hash_sha256')
plan={'plan_version':'LP_ML_ROUND1_REMAINING_240_V1','full_plan_path':str((P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv').relative_to(R)).replace('\\','/'),'full_plan_sha256':h(P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv'),'smoke_plan_path':str((P/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv').relative_to(R)).replace('\\','/'),'smoke_plan_sha256':h(P/'lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv'),'remaining_count':240,'candidate_ids':[r['candidate_id'] for r in remain],'excluded_smoke_ids':sorted(smoke_ids),'exact_hash_unique':True,'canonical_hash_unique_count':len({r['canonical_relative_geometry_hash_sha256'] for r in remain}),'symmetry_hash_unique_count':len({r['symmetry_equivalence_geometry_hash_sha256'] for r in remain}),'canonical_equivalence_groups':canonical_groups,'symmetry_equivalence_groups':symmetry_groups,'alias_policy':'legal sign-reflection aliases retained exactly as frozen; same geometry-level split group required; no alias leakage','manufacturing_pass':True,'min_direct_gap_nm':min(float(r['direct_gap_nm']) for r in remain),'min_periodic_gap_nm':min(float(r['periodic_gap_nm']) for r in remain),'no_subgrid':True,'material':'APCD_TIO2_NATIVE_M1','H_nm':500.0,'period_nm':432.0,'wavelengths_nm':[450.0,450.5,451.0,451.5,452.0,452.5,453.0,453.5,454.0]}
(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.json').write_text(json.dumps(plan,indent=2,sort_keys=True)+'\n',encoding='utf-8')
contract={'execution_contract_version':'LP_ML_ROUND1_PRODUCTION_EXECUTION_V1','attempt_id':'LP_ML_ROUND1_PRODUCTION_ATTEMPT1_V1','source_plan_sha256':h(P/'lp_ml_dataset_v1_round1_remaining_240_plan_v1.json'),'full_plan_sha256':h(P/'lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv'),'smoke_attempt2_sentinel_sha256':h(R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1/final_sentinel_v1.json'),'authorized_geometries':240,'authorized_new_subruns_max':480,'wavelengths_nm':plan['wavelengths_nm'],'sampling_mode':'wavelength_domain_uniform_via_source_limits','monitor_settings':{'global_frequency_points':9,'global_use_wavelength_spacing':True,'global_use_source_limits':True,'local_override_global':True,'local_frequency_points':9,'local_use_wavelength_spacing':True,'local_use_source_limits':True},'lifecycle':'x->checkpoint->reload->acceptance->9-point weighted-G0; y->checkpoint->reload->acceptance->9-point weighted-G0','no_retry_entered_case':True,'old_attempts_excluded':['LP_ML_ROUND1_SMOKE_ATTEMPT1_V1'],'smoke_not_rerun':True,'geometry_alias_policy':{'canonical_equivalence_groups':canonical_groups,'symmetry_equivalence_groups':symmetry_groups,'same_split_required':True,'no_alias_leakage':True},'forbidden':['D9','Batch B','old Batch2','new candidate selection','plan expansion','active-learning solver','inverse design','K6']}
(P/'lp_ml_dataset_v1_round1_production_execution_contract_v1.json').write_text(json.dumps(contract,indent=2,sort_keys=True)+'\n',encoding='utf-8')
ledger={'ledger_version':'LP_ML_ROUND1_PRODUCTION_BUDGET_LEDGER_V1','attempt_id':contract['attempt_id'],'historical_smoke_attempt2':{'geometries':16,'accepted_subruns':32,'spectral_rows':144,'status':'RETAINED_FORMAL'},'production':{'geometries_planned':240,'subruns_max':480,'status':'PLANNED_NOT_RUN'},'round1_target':{'geometries':256,'accepted_subruns':512,'spectral_rows':2304},'smoke_ids_excluded_from_production':sorted(smoke_ids),'no_overlap':True,'old_five_point_attempt_excluded':True}
(A/'lp_ml_dataset_v1_round1_production_budget_ledger_v1.json').write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'remaining':len(remain),'exact_unique':len({r['exact_geometry_hash_sha256'] for r in remain}),'canonical_unique':len({r['canonical_relative_geometry_hash_sha256'] for r in remain}),'symmetry_unique':len({r['symmetry_equivalence_geometry_hash_sha256'] for r in remain})},indent=2))
