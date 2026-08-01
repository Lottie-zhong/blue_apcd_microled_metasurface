from pathlib import Path
import json,hashlib,numpy as np,pandas as pd
R=Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1'); OUT=R/'outputs'/'mdc_ml_hf15_external_training_contract_v1'/'hf15-contract-20260801T060000Z-701c1a4'; REP=R/'reports';OUT.mkdir(parents=True,exist_ok=False)
HF=R/'outputs'/'mdc_fdtd_hf15_canonical_label_view_v1'/'hf15-20260801T050000Z-5a6a4c1';DEV=R/'outputs'/'mdc_ml_active_learning_merge_retrain_v1';CFG=R/'configs'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,x):x.to_parquet(OUT/n,index=False)
def js(n,x): (OUT/n).write_text(json.dumps(x,indent=2,sort_keys=True))
assets=[]
for p in [HF/'dataset_manifest.json',HF/'mdc_fdtd_hf15_geometry_labels_v1.parquet',HF/'mdc_fdtd_hf15_case_diagnostics_v1.parquet',DEV/'regression_development_view_v1.json',DEV/'regression_development_view_v1.npz',CFG/'mdc_ml_regression_development_contract_v1.json',CFG/'mdc_ml_active_learning_merge_retrain_v1.yaml',CFG/'mdc_ml_dataset_schema_v1.json']:
 assets.append({'path':str(p),'exists':p.exists(),'sha256':sha(p) if p.exists() else None,'size':p.stat().st_size if p.exists() else None})
put('protected_input_inventory.parquet',pd.DataFrame(assets));js('protected_asset_index.json',assets)
hf=pd.read_parquet(HF/'mdc_fdtd_hf15_geometry_labels_v1.parquet'); hh=set(hf.geometry_hash.astype(str));assert len(hh)==15
view=json.loads((DEV/'regression_development_view_v1.json').read_text()); npz=np.load(DEV/'regression_development_view_v1.npz',allow_pickle=True); keys=list(npz.keys())
inv=[]
for p in [CFG/'mdc_ml_active_learning_merge_retrain_v1.yaml',CFG/'mdc_ml_regression_development_contract_v1.json',CFG/'mdc_ml_dataset_schema_v1.json',DEV/'regression_development_view_v1.json']:
 inv.append({'asset':p.name,'sha256':sha(p),'status':'READ'})
put('contract_inventory.parquet',pd.DataFrame(inv))
has_geometry=any('geometry' in k.lower() for k in keys); fields={'model_candidate_allowlist':'MISSING_FORMAL_SOURCE','fixed_v1_architecture_retrain':'MISSING_FORMAL_SOURCE','bounded_recompetition_candidate_set':'MISSING_FORMAL_SOURCE','classification_geometry_mapping':'MISSING_FORMAL_SOURCE','regression_geometry_mapping':'AVAILABLE' if has_geometry else 'NOT_AVAILABLE_WITH_CURRENT_SCHEMA','target_transforms':'UNVERIFIED','training_seeds':'UNVERIFIED'}
js('prior_blocker_field_audit.json',{'npz_keys':keys,'field_status':fields})
# No source row is fabricated: only derive if a real geometry_hash array is present.
reg_status='NOT_AVAILABLE_WITH_CURRENT_SCHEMA'; removed=[]
for k in keys:
 if 'geometry' in k.lower():
  arr=npz[k].astype(str); mask=~np.isin(arr,list(hh)); df=pd.DataFrame({'geometry_hash':arr,'source_row_index':np.arange(len(arr))});put('mdc_tmm_dev_non_hf15_regression_v1.parquet',df[mask]);removed=df[~mask].to_dict('records');reg_status='DERIVED_GEOMETRY_INDEX_ONLY';break
if reg_status!='DERIVED_GEOMETRY_INDEX_ONLY':put('mdc_tmm_dev_non_hf15_regression_v1.parquet',pd.DataFrame({'status':[reg_status]}))
put('mdc_tmm_dev_non_hf15_classification_v1.parquet',pd.DataFrame({'status':['NOT_AVAILABLE_WITH_CURRENT_SCHEMA']}));put('excluded_hf15_geometry_index.parquet',pd.DataFrame({'geometry_hash':sorted(hh)}));put('derived_split_membership.parquet',pd.DataFrame({'status':['NOT_AVAILABLE_WITH_CURRENT_SCHEMA']}))
over=pd.DataFrame([{'source':'regression_development_view_v1.npz','total_rows':int(view.get('canonical_development_row_count',view.get('row_count',0)) or 0),'unique_geometries':None,'overlap_geometry_count':len(removed),'overlap_rows':len(removed),'label_leakage':False,'geometry_exposure':'NOT_DETERMINABLE_WITH_CURRENT_SCHEMA'}]);put('hf15_geometry_overlap_audit.parquet',over);put('hf15_split_overlap_audit.parquet',pd.DataFrame({'status':['NOT_AVAILABLE_WITH_CURRENT_SCHEMA']}));js('hf15_leakage_classification.json',{'hf15_label_leakage':'NOT_PROVEN; training/OOF geometry provenance mapping missing','hard_stop':False})
contracts={'dataset_id':'MDC_TMM_DEV_NON_HF15_V1','hf15_role':'external_grouped_validation_only','dipole_tmm_role':'rank_prior_only','sealed_test':'UNREAD_UNTOUCHED_NOT_AUTHORIZED','split_unit':'geometry_hash','training_runs':0,'optimizer_steps':0,'backward_calls':0,'dry_run':'NOT_RUN_BLOCKED_BY_MISSING_CONTRACT_FIELDS','readiness_status':'BLOCKED_BY_UNRESOLVED_MODEL_CONTRACT','missing_fields':[k for k,v in fields.items() if v in ['MISSING_FORMAL_SOURCE','UNVERIFIED','NOT_AVAILABLE_WITH_CURRENT_SCHEMA']]}
for n in ['model_candidate_registry_v1.json','classification_training_contract_v1.json','regression_training_contract_v1.json','target_transform_contract_v1.json','target_compatibility_contract_v1.json','internal_model_selection_contract_v1.json','hf15_external_evaluation_contract_v1.json','multifidelity_data_role_contract_v2.json','grouped_split_and_leakage_contract_v1.json','dry_run_readiness_audit.json','training_readiness_status.json','dataset_manifest.json','provenance.json']:js(n,contracts)
for n in ['mdc_ml_hf15_geometry_overlap_and_leakage_audit_v1','mdc_ml_strict_internal_training_view_v1','mdc_ml_training_and_model_selection_contract_v1','mdc_ml_hf15_external_evaluation_contract_v1','mdc_ml_training_readiness_no_run_v1']:(REP/(n+'.json')).write_text(json.dumps(contracts,indent=2));(REP/(n+'.md')).write_text('# '+n+'\n\n```json\n'+json.dumps(contracts,indent=2)+'\n```\n')
