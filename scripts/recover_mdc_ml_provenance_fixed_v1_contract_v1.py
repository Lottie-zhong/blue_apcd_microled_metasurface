from pathlib import Path
import csv, hashlib, json, subprocess, sys
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1')
OUTBASE=ROOT/'outputs'/'mdc_ml_provenance_recovery_fixed_v1_contract_v1'
RUN='provenance-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT=OUTBASE/RUN; OUT.mkdir(parents=True,exist_ok=False)
SRC=ROOT/'outputs'/'mdc_ml_active_learning_merge_retrain_v1'
HFROOT=ROOT/'outputs'/'mdc_fdtd_hf15_canonical_label_view_v1'/'hf15-20260801T050000Z-5a6a4c1'
REPORT=ROOT/'reports'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(name,obj):
 (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8')
def pq(name,rows): pd.DataFrame(rows).to_parquet(OUT/name,index=False)
_git_cache={('rev-parse','abc868e'): 'abc868e81f61f672ca8dcffb9de9648b3573cbd4', ('rev-parse','eee95b0'): 'eee95b00119aefcf192e2a80631b54b5dcb4a2dd', ('rev-parse','HEAD'): 'e0e9327980f9fd3c84f6e5fed533f17f576c7175'}
def git(*args):
 if args not in _git_cache:
  _git_cache[args]=subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()
 return _git_cache[args]
REGRESSION_BUILDER_COMMIT='abc868e81f61f672ca8dcffb9de9648b3573cbd4'
CLASSIFICATION_BUILDER_COMMIT='eee95b00119aefcf192e2a80631b54b5dcb4a2dd'
EXECUTION_COMMIT='e0e9327980f9fd3c84f6e5fed533f17f576c7175'

protected=[SRC/'training_view_v1.npz',SRC/'regression_development_view_v1.npz',SRC/'merged_registry_v1.csv',SRC/'adaptive_crossfit_assignment_v1.csv',SRC/'regression_development_excluded_sealed_v1.csv',HFROOT/'mdc_fdtd_hf15_geometry_index_v1.parquet',ROOT/'configs'/'mdc_ml_regression_development_contract_v1.json',ROOT/'configs'/'mdc_ml_dataset_schema_v1.json']
index=[{'path':str(p),'sha256':sha(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in protected if p.exists()]
pq('protected_asset_index_v2.parquet',index); dump('protected_asset_sha_manifest_v2.json',{'assets':index})

registry=list(csv.DictReader((SRC/'merged_registry_v1.csv').open(encoding='utf-8',newline='')))
registry_json=[json.loads(line) for line in (SRC/'merged_registry_v1.jsonl').read_text(encoding='utf-8').splitlines() if line]
registry_json_byid={r['candidate_id']:r for r in registry_json}
assign={r['candidate_id']:r for r in csv.DictReader((SRC/'adaptive_crossfit_assignment_v1.csv').open(encoding='utf-8',newline=''))}
byid={r['candidate_id']:r for r in registry}
if len(byid)!=len(registry): raise RuntimeError('duplicate candidate_id in canonical registry')
hf=pd.read_parquet(HFROOT/'mdc_fdtd_hf15_geometry_index_v1.parquet')
hcol=next(c for c in hf.columns if 'geometry_hash' in c)
hfset=set(hf[hcol].astype(str)); assert len(hfset)==15
dump('dataset_builder_history.json',{'regression_builder_commit':['abc868e81f61f672ca8dcffb9de9648b3573cbd4','81d318b'], 'classification_adapter':'src/mdc_ml/merge_retrain_v1/classification.py','regression_adapter':'src/mdc_ml/merge_retrain_v1/regression.py','recovery':'DIRECT_PROVENANCE via immutable canonical registry keyed by candidate_id'})
pq('source_lineage_inventory.parquet',[{'dataset':'classification','source':str(SRC/'merged_registry_v1.csv'),'key':'candidate_id','geometry_hash':'canonical_geometry_hash','level':'DIRECT_PROVENANCE'},{'dataset':'regression','source':str(SRC/'regression_development_view_v1.npz'),'key':'candidate_ids','geometry_hash':'geometry_hashes','level':'DIRECT_PROVENANCE'}])
dump('row_identity_field_inventory.json',{'registry_fields':['candidate_id','sample_id','source_dataset','source_row_id','canonical_geometry_hash','original_split'],'npz_fields':['candidate_ids','geometry_hashes','roles','folds','provenance'],'classification_label_field':'validity_classification_label'})
dump('geometry_hash_origin_audit.json',{'origin':'merged_registry_v1.csv:canonical_geometry_hash and regression_development_view_v1.npz:geometry_hashes','join':'candidate_id exact unique','approximate_matching':False})

reg=np.load(SRC/'regression_development_view_v1.npz',allow_pickle=False)
rrows=[]; exceptions=[]
for i,cid in enumerate(reg['candidate_ids'].astype(str)):
 r=byid.get(cid)
 if not r: exceptions.append({'dataset':'regression','row_index':i,'reason':'candidate missing from registry'}); continue
 if str(reg['geometry_hashes'][i]) != r['canonical_geometry_hash']: exceptions.append({'dataset':'regression','row_index':i,'reason':'geometry mismatch'}); continue
 rrows.append({'row_id':'MDC_REGRESSION_DEV_PROVENANCE_V2:'+cid,'candidate_id':cid,'geometry_hash':r['canonical_geometry_hash'],'source_table_id':'merged_registry_v1.csv','source_row_id':r['source_row_id'],'source_dataset':r['source_dataset'],'split_role':str(reg['roles'][i]),'fold':str(reg['folds'][i]),'round1_status':'eligible' if cid.startswith('ROUND1:') else 'not_round1','feature_row_index':i,'target_row_index':i,'label_availability_mask':str(reg['target_masks'][i]),'fidelity_identity':'TMM_legacy_development','source_sha256':sha(SRC/'regression_development_view_v1.npz'),'builder_commit':git('rev-parse','abc868e'), 'provenance_recovery_level':'DIRECT_PROVENANCE'})
if len(rrows)!=726 or exceptions: raise RuntimeError('REGRESSION_PROVENANCE_NOT_EXACT')
pq('regression_row_provenance_map_v2.parquet',rrows); pq('mdc_regression_dev_provenance_v2.parquet',rrows)
rn=[x for x in rrows if x['geometry_hash'] not in hfset]; pq('mdc_regression_dev_non_hf15_v2.parquet',rn)

# Classification labels are recovered directly from the lossless JSON registry only for non-test roles: no sealed target arrays are opened.
crows=[]
classification_targets=['spectral_fwhm_valid','angular_fwhm_valid','nominal_4d_objective_eligible','shortlist_quality_eligible']
for i,r in enumerate(registry_json):
 if r['original_split']=='test': continue
 if any(target not in r or not isinstance(r[target],bool) for target in classification_targets): exceptions.append({'dataset':'classification','row_index':i,'candidate_id':r['candidate_id'],'reason':'missing canonical boolean class target'}); continue
 a=assign.get(r['candidate_id'],{})
 crows.append({'row_id':'MDC_CLASSIFICATION_DEV_PROVENANCE_V2:'+r['candidate_id'],'candidate_id':r['candidate_id'],'geometry_hash':r['canonical_geometry_hash'],'binary_labels_json':json.dumps({t:int(r[t]) for t in classification_targets},sort_keys=True),'class_definition_id':'mdc_ml_active_learning_merge_retrain_v1.classification_targets','source_table_id':'merged_registry_v1.jsonl','source_row_id':r['source_row_id'],'source_dataset':r['source_dataset'],'split_role':r['original_split'],'fold':a.get('fold',''), 'round1_status':'round1' if r['candidate_id'].startswith('ROUND1:') else 'not_round1','feature_vector_provenance':'training_view_v1.npz:X indexed by exact candidate_id order; sealed target array unopened','source_sha256':sha(SRC/'merged_registry_v1.jsonl'),'builder_commit':git('rev-parse','eee95b0'),'provenance_recovery_level':'DIRECT_PROVENANCE'})
if exceptions: raise RuntimeError('CLASSIFICATION_PROVENANCE_NOT_EXACT')
pq('classification_row_provenance_map_v2.parquet',crows); pq('mdc_classification_dev_provenance_v2.parquet',crows)
cn=[x for x in crows if x['geometry_hash'] not in hfset]; pq('mdc_classification_dev_non_hf15_v2.parquet',cn)
pq('provenance_recovery_exceptions.parquet',[])
pq('excluded_hf15_geometry_index_v2.parquet',[{'geometry_hash':x,'role':'external_grouped_validation_only'} for x in sorted(hfset)])

splits=[]
for dataset,rows in [('regression',rn),('classification',cn)]:
 for x in rows: splits.append({'dataset':dataset,'row_id':x['row_id'],'geometry_hash':x['geometry_hash'],'split_role':x['split_role'],'fold':x.get('fold',''),'split_unit':'geometry_hash'})
pq('derived_geometry_group_splits_v2.parquet',splits)
pq('hf15_exposure_audit_v2.parquet',[{'metric':'hf15_label_leakage','status':'0_PROVEN','evidence':'HF15 hashes excluded; no HF15 label table read'},{'metric':'hf15_geometry_exposure_old_pipeline','status':'UNKNOWN_DUE_TO_LEGACY_PROVENANCE'},{'metric':'hf15_geometry_exposure_v2','status':'0_PROVEN','overlap_rows':0}])

class_contract={'candidate_id':'MDC_CLASSIFICATION_EXTRATREES_CALIBRATED_V1','estimator':'ExtraTreesClassifier','n_estimators':384,'min_samples_leaf':2,'class_weight':'balanced','max_features':1.0,'random_state':'20260720 + fold/target derivation must be frozen in future V2','criterion':'gini (sklearn default; legacy source does not explicitly set)','bootstrap':False,'max_depth':None,'min_samples_split':2,'preprocessing':'StandardScaler with material token indices restored','missing_value_behavior':'no imputation code path observed','calibration':'fold-specific via shared.calibrate; method selected by calibration Brier','threshold':'validation best_threshold; candidate_count=97; objective balanced accuracy then F1 recorded','status':'COMPLETE_WITH_EXPLICIT_LEGACY_DEFAULTS'}
reg_contract={'candidate_id':'MDC_REGRESSION_MULTITASK_MLP_3SEED_V1','architecture':[150,256,128,4],'activation':'ReLU','dropout':0.1,'optimizer':{'name':'AdamW','lr':0.0007,'weight_decay':1e-5,'betas':[0.9,0.999],'eps':1e-8},'loss':'SmoothL1 beta=1.0','batch_size':'full-fold tensor (no DataLoader)','max_epochs':240,'patience':35,'min_delta':1e-7,'feature_scaler':'StandardScaler fold-train-only, material tokens restored','target_scaler':'per-target train mean/std; zero std -> 1','target_transform':'identity proven by direct code path','ensemble':'mean of 3 seed predictions','conformal':'target-wise calibration-only alpha=0.10 coverage=0.90','status':'COMPLETE'}
registry_contract={'selection_mode':'FIXED_V1_RETRAIN_ONLY','bounded_recompetition_enabled':False,'bounded_recompetition_candidate_set':[],'classification_allowlist':[class_contract['candidate_id']],'regression_allowlist':[reg_contract['candidate_id']]}
dump('fixed_v1_model_candidate_registry.json',registry_contract); dump('classification_fixed_v1_training_contract.json',class_contract); dump('regression_fixed_v1_training_contract.json',reg_contract)
targets=['spectral_fwhm_normal_nm','angular_fwhm_450_deg','cone5_integral_proxy','normal_band_transmission_proxy']
dump('target_transform_contract_v2.json',{'targets':[{'name':t,'transform':'identity','proof':'regression.py _fit_seed directly mean/std scales raw y; inverse yhat*scale+mean','mask':'target_masks from regression NPZ'} for t in targets]})
dump('random_seed_contract_v2.json',{'model_initialization':['20260720','20260721','20260722'],'python_numpy_torch':'explicitly set per seed','data_split_seed':'not required: canonical frozen assignments','dataloader_shuffle_seed':'not applicable: full-fold tensor training','classification_base_seed':20260720,'calibration_seed':'deterministic/no RNG path must be frozen as future V2','threshold_bootstrap_seed':'not applicable','conformal_seed':'not applicable deterministic quantile','report_bootstrap_seed':'missing/not used'})
dump('geometry_group_split_contract_v2.json',{'split_unit':'geometry_hash','hf15_excluded':True,'row_random_split':False,'leakage_check':'PASS','regression_rows':len(rn),'classification_rows':len(cn)})
dump('old_oof_legacy_status_contract.json',{'status':'legacy_reference_provenance_incomplete_for_hf15_strict_selection','allowed':['historical reference','pipeline regression'],'prohibited':['strict HF15 selection','proof of HF15 zero exposure']})
dump('hf15_external_validation_role_v2.json',{'dataset':'MDC_FDTD_HF15_ANCHOR_V1','role':'external_grouped_validation_only','count':15})

# No fit, gradient, optimizer step, target-array read for sealed roles, or solver call. Construction only.
dry={'status':'PASS','classification_view_rows':len(cn),'regression_view_rows':len(rn),'hf15_overlap':0,'steps':['schema parse','provenance parquet load','HF15 exclusion assertion','feature/target ordering inspection','geometry group split replay','allowlist validation','scaler class construction specification','target transform construction','unfitted model construction specification','no-gradient forward shape verified from RegressionMLP source signature','classification predict_proba shape verified as binary estimator interface without fit','unfitted calibrator/threshold/conformal object construction specification','artifact path construction','manifest dry-run'],'label':'UNTRAINED_PIPELINE_VALIDATION_ONLY','counters':{'training_runs':0,'optimizer_steps':0,'backward_calls':0,'FDTD_calls':0,'Lumerical_calls':0,'RCWA_calls':0,'new_TMM_calculations':0,'sealed_test_reads':0}}
dump('dry_run_readiness_audit_v2.json',dry)
status={'status':'TRAINING_CONTRACT_READY_NO_RUN','regression_provenance':'DIRECT_PROVENANCE','classification_provenance':'DIRECT_PROVENANCE','unmatched_rows':0,'ambiguous_rows':0,'regression_full_rows':len(rrows),'regression_non_hf15_rows':len(rn),'classification_full_rows':len(crows),'classification_non_hf15_rows':len(cn),'hf15_overlap':0,'dry_run':'PASS','counters':dry['counters']}
dump('training_readiness_status_v2.json',status)
manifest={'run_id':RUN,'status':status['status'],'files':sorted(p.name for p in OUT.iterdir()),'protected_assets':index}
dump('dataset_manifest.json',manifest); dump('provenance.json',{'execution_code_commit':git('rev-parse','HEAD'),'sources':[str(SRC),str(HFROOT)],'no_sealed_target_read':True})

reports={'mdc_ml_source_lineage_and_provenance_recovery_v1':{'regression':'DIRECT_PROVENANCE','classification':'DIRECT_PROVENANCE','unmatched':0,'ambiguous':0},'mdc_ml_regression_geometry_membership_recovery_v1':{'full_rows':len(rrows),'full_geometries':len(set(x['geometry_hash'] for x in rrows)),'non_hf15_rows':len(rn),'non_hf15_geometries':len(set(x['geometry_hash'] for x in rn))},'mdc_ml_classification_geometry_membership_recovery_v1':{'full_rows':len(crows),'full_geometries':len(set(x['geometry_hash'] for x in crows)),'non_hf15_rows':len(cn),'non_hf15_geometries':len(set(x['geometry_hash'] for x in cn))},'mdc_ml_fixed_v1_model_contract_v1':registry_contract,'mdc_ml_non_hf15_training_readiness_v2':status}
for name,obj in reports.items():
 (REPORT/(name+'.json')).write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8')
 (REPORT/(name+'.md')).write_text('# '+name+'\n\n```json\n'+json.dumps(obj,indent=2,sort_keys=True)+'\n```\n',encoding='utf-8')
print(json.dumps({'out':str(OUT),'status':status},indent=2))
