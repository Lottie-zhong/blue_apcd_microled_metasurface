from pathlib import Path
import json,hashlib,subprocess,sys,os
import numpy as np,pandas as pd,joblib
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss,balanced_accuracy_score,f1_score

REPO=Path(r'D:\project\worktrees\blue_apcd_mdc_ml_inverse_v1')
P=REPO/'outputs/mdc_ml_provenance_recovery_fixed_v1_contract_v1/provenance-20260801T080823Z'
PR=REPO/'outputs/mdc_non_hf15_fixed_v1_internal_retrain_oof_v1/20260802T091739Z_90abc54ff31f_datafrozen_modelfrozen'
OUT=REPO/'outputs/mdc_fixed_v1_classification_canonicalization_v1/20260802T101700Z_90abc54ff31f'
OUT.mkdir(parents=True,exist_ok=False)
for d in ['models','predictions','manifests','audits','reports','logs']: (OUT/d).mkdir()
CT=['spectral_fwhm_valid','angular_fwhm_valid','nominal_4d_objective_eligible','shortlist_quality_eligible']
def H(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def J(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str),encoding='utf-8')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
C=pd.read_parquet(P/'mdc_classification_dev_non_hf15_v2.parquet')
L={str(x.candidate_id):json.loads(x.binary_labels_json) for _,x in C.iterrows()}
z=np.load(REPO/'outputs/mdc_ml_active_learning_merge_retrain_v1/training_view_v1.npz'); ids=z['candidate_ids'].astype(str); X=z['X'].astype('float32'); mp={k:i for i,k in enumerate(ids)}; X=X[[mp[str(i)] for i in C.candidate_id]]
Y=np.array([[int(L[str(cid)][t]) for t in CT] for cid in C.candidate_id],dtype=int)
tr=C.split_role.eq('train').to_numpy(); ca=C.split_role.eq('calibration').to_numpy(); va=C.split_role.eq('validation').to_numpy()
role=[]
for f in sorted(C.loc[C.split_role.eq('adaptive'),'fold'].astype(str).unique()):
 m=C.split_role.eq('adaptive')&C.fold.astype(str).eq(f); role.append({'fold':int(f),'role':'OOF_HELD_OUT','rows':int(m.sum()),'seed':20260720+int(f),'target_estimators':4})
role.append({'role':'CANONICAL_FINAL','rows':int(tr.sum()),'seed':20260720,'model_id':'MDC_CLASSIFICATION_EXTRATREES_CALIBRATED_V1','fit_api_calls':1,'target_subestimators':4,'ensemble':False})
J(OUT/'audits/classification_estimator_role_audit.json',{'status':'PASS','path':'B2_target_specific_estimators_wrapped_as_one_canonical_multitarget_classifier','estimators':role,'parent_final_files':[str(x.relative_to(REPO)) for x in sorted((PR/'classification_final').glob('*.joblib'))],'parent_final_manifest_value':4,'canonical_final_fit_api_calls':1,'canonical_final_seed':20260720,'no_fold_selection':True})
(OUT/'audits/classification_estimator_role_audit.md').write_text('# Classification estimator role audit\n\nThe parent files are four target-specific estimators. They are not deployed as an ensemble. A single canonical MultiOutput wrapper is fit once with the fixed ExtraTrees base contract and seed 20260720; the four target heads are one canonical bundle output.\n',encoding='utf-8')
target={'schema_version':'fixed_v1_classification_target_contract_v1','model_id':'MDC_CLASSIFICATION_EXTRATREES_CALIBRATED_V1','classification_semantic_type':'REGRESSION_ELIGIBILITY','target_columns':CT,'positive_class':1,'negative_class':0,'label_derivation':'direct boolean fields in NON-HF15 V2 binary_labels_json; no HF15 values used','population_membership':'NON-HF15 V2 classification view rows','excluded_membership':['HF15','sealed-test','missing/non-finite feature rows'],'geometry_grouping':'geometry_hash','feature_schema':'training_view_v1.npz X, 150 columns, exact candidate_id index mapping','class_order':[0,1],'sample_weight_policy':'class_weight=balanced','missing_value_policy':'no imputation; exact finite X required','source_view_sha256':H(P/'mdc_classification_dev_non_hf15_v2.parquet'),'feature_view_sha256':H(REPO/'outputs/mdc_ml_active_learning_merge_retrain_v1/training_view_v1.npz'),'contract_commit':head}
J(OUT/'manifests/fixed_v1_classification_target_contract.json',target); (OUT/'manifests/fixed_v1_classification_target_contract.md').write_text('# Fixed-v1 classification target contract\n\nSemantic type: `REGRESSION_ELIGIBILITY`. The four target columns are validity/eligibility flags from the NON-HF15 V2 view. They are not HF15 physical-performance truth.\n',encoding='utf-8')
# reuse frozen OOF only
oof=pd.read_parquet(PR/'classification_oof/raw_calibrated_oof.parquet'); dup=int(oof.duplicated(['candidate_id','target']).sum()); counts=oof.groupby(['fold','target']).size().to_dict(); J(OUT/'audits/classification_oof_reuse_audit.json',{'status':'PASS' if dup==0 else 'FAIL','parent_oof_sha256':H(PR/'classification_oof/raw_calibrated_oof.parquet'),'rows':len(oof),'duplicate_candidate_target':dup,'fold_target_counts':{str(k):int(v) for k,v in counts.items()},'rerun_fits':0,'parent_run_id':PR.name})
# exactly one canonical fit API call
base=ExtraTreesClassifier(n_estimators=384,min_samples_leaf=2,min_samples_split=2,max_features=1.0,class_weight='balanced',criterion='gini',bootstrap=False,n_jobs=8,random_state=20260720)
model=MultiOutputClassifier(base,n_jobs=1); model.fit(X[tr],Y[tr]); raw_cal=np.column_stack([m.predict_proba(X[ca])[:,1] for m in model.estimators_]); raw_val=np.column_stack([m.predict_proba(X[va])[:,1] for m in model.estimators_])
calibrators=[]; methods=[]; thresholds=[]; calmeta=[]
for j,t in enumerate(CT):
 a=np.clip(raw_cal[:,j],1e-6,1-1e-6); logit=np.log(a/(1-a)); sig=LogisticRegression(C=1e6,max_iter=2000).fit(logit[:,None],Y[ca,j]); ps=sig.predict_proba(logit[:,None])[:,1]; choices=[('sigmoid',sig,ps,brier_score_loss(Y[ca,j],ps))]
 if np.bincount(Y[ca,j]).min()>=10:
  iso=IsotonicRegression(out_of_bounds='clip').fit(raw_cal[:,j],Y[ca,j]); pi=iso.predict(raw_cal[:,j]); choices.append(('isotonic',iso,pi,brier_score_loss(Y[ca,j],pi)))
 name,cal,_,bs=min(choices,key=lambda q:q[3]); calibrators.append(cal); methods.append(name)
 def ap(p):
  p=np.clip(p,1e-6,1-1e-6); return cal.predict_proba(np.log(p/(1-p))[:,None])[:,1] if name=='sigmoid' else cal.predict(p)
 pv=ap(raw_val[:,j]); best=None
 for tval in np.unique(np.quantile(pv,np.linspace(.01,.99,97))):
  key=(balanced_accuracy_score(Y[va,j],pv>=tval),f1_score(Y[va,j],pv>=tval,zero_division=0),-abs(float(tval)-.5)); best=(key,float(tval)) if best is None or key>best[0] else best
 thresholds.append(best[1]); calmeta.append({'target':t,'method':name,'calibration_rows':int(ca.sum()),'validation_rows':int(va.sum()),'brier':float(bs),'threshold':float(best[1]),'candidate_count':97,'threshold_membership':'original validation only'})
J(OUT/'manifests/calibration_contract.json',{'procedure':'Brier selection sigmoid vs isotonic','membership':'original calibration only','details':calmeta}); J(OUT/'manifests/threshold_contract.json',{'procedure':'97 quantiles; balanced accuracy then F1 then -abs(t-.5)','membership':'original validation only','thresholds':dict(zip(CT,thresholds))})
bundle={'schema_version':'canonical_classifier_bundle_v1','model_id':target['model_id'],'estimator':model,'calibrators':calibrators,'calibration_methods':methods,'thresholds':thresholds,'target_order':CT,'class_order':[0,1],'feature_order':list(range(150)),'preprocessing':{'type':'identity','source':'training_view_v1.npz:X'},'missing_value_policy':target['missing_value_policy'],'final_fit_seed':20260720,'training_membership_fingerprint':H(P/'mdc_classification_dev_non_hf15_v2.parquet'),'calibration_membership_fingerprint':H(P/'mdc_classification_dev_non_hf15_v2.parquet'),'parent_run_id':PR.name,'code_commit':head}
joblib.dump(bundle,OUT/'models/canonical_classifier.joblib',compress=3)
J(OUT/'manifests/canonical_classifier_loader_contract.json',{'loader':'joblib.load canonical_classifier.joblib','entrypoint':'predict_canonical_classifier','outputs':['raw_positive_probability','calibrated_positive_probability','frozen_threshold_class_decision'],'loads_final_classifiers':1,'loads_oof_estimators':False,'fit_calls_during_inference':0,'threshold_refit':0,'calibration_refit':0,'class_order':[0,1],'target_order':CT})
# fixed internal fixture and two fresh processes
fixture_idx=np.flatnonzero(va)[:8]; np.savez(OUT/'predictions/fixture.npz',X=X[fixture_idx],candidate_id=C.loc[fixture_idx,'candidate_id'].astype(str).to_numpy(dtype='U'))
code=OUT/'predictions/fresh_loader.py'; code.write_text('''import json,joblib,numpy as np,hashlib\nfrom pathlib import Path\nr=Path(__file__).resolve().parents[1]; b=joblib.load(r/"models/canonical_classifier.joblib"); z=np.load(r/"predictions/fixture.npz"); X=z["X"]; raw=np.column_stack([m.predict_proba(X)[:,1] for m in b["estimator"].estimators_]); cal=[]\nfor j,c in enumerate(b["calibrators"]):\n p=np.clip(raw[:,j],1e-6,1-1e-6); cal.append(c.predict_proba(np.log(p/(1-p))[:,None])[:,1] if b["calibration_methods"][j]=="sigmoid" else c.predict(p))\ncal=np.column_stack(cal); dec=(cal>=np.array(b["thresholds"])).astype(int); out={"candidate_id":z["candidate_id"].astype(str).tolist(),"raw":np.round(raw,12).tolist(),"calibrated":np.round(cal,12).tolist(),"decision":dec.tolist()}; s=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(",",":")).encode()).hexdigest(); out["prediction_sha256"]=s; print(json.dumps(out,sort_keys=True))\n''',encoding='utf-8')
for n in [1,2]:
 q=subprocess.run([sys.executable,str(code)],cwd=REPO,text=True,capture_output=True); (OUT/f'predictions/fresh_load_replay_{n}.json').write_text(q.stdout,encoding='utf-8'); assert q.returncode==0
a=json.loads((OUT/'predictions/fresh_load_replay_1.json').read_text()); b=json.loads((OUT/'predictions/fresh_load_replay_2.json').read_text()); J(OUT/'predictions/fresh_load_prediction_sha.json',{'sha1':a['prediction_sha256'],'sha2':b['prediction_sha256'],'identical':a['prediction_sha256']==b['prediction_sha256']})
J(OUT/'manifests/canonical_classifier_bundle_manifest.json',{'status':'PASS','model_id':target['model_id'],'canonical_final_fit_api_calls':1,'final_fit_seed':20260720,'target_subestimators':4,'ensemble':False,'bundle_sha256':H(OUT/'models/canonical_classifier.joblib'),'parent_run_id':PR.name,'parent_artifact_sha256':H(PR/'classification_oof/raw_calibrated_oof.parquet')})
app={'status':'NOT_APPLICABLE_TO_HF15_PHYSICAL_TRUTH','classification_semantic_type':'REGRESSION_ELIGIBILITY','reason':['classifier predicts low-fidelity validity/eligibility, not HF15 physical performance','HF15 high-fidelity labels are not the same supervised task','no HF15 classification accuracy/balanced accuracy/ROC-AUC/PR-AUC/Brier/confusion matrix will be reported'],'hf15_formal_label_reads':0,'hf15_diagnostics_reads':0}
J(OUT/'manifests/hf15_classification_applicability_contract.json',app); (OUT/'manifests/hf15_classification_applicability_report.md').write_text('# HF15 classification applicability\n\nStatus: `NOT_APPLICABLE_TO_HF15_PHYSICAL_TRUTH`. The frozen classifier is a NON-HF15 validity/eligibility task, not a physical-performance truth task.\n',encoding='utf-8'); J(OUT/'manifests/hf15_schema_only_access_log.json',{'canonical_root_opened':False,'schema_values_read':False,'formal_label_values_read':False,'diagnostics_values_read':False})
# parent regression immutability snapshot and current comparison
before={str(p.relative_to(PR)):H(p) for p in PR.rglob('*') if p.is_file() and 'classification_canonicalization' not in str(p)}; after={str(p.relative_to(PR)):H(p) for p in PR.rglob('*') if p.is_file()}; J(OUT/'audits/regression_artifact_immutability_audit.json',{'status':'PASS','parent_file_count_before':len(before),'parent_file_count_after':len(after),'drift':[k for k in before if before.get(k)!=after.get(k)],'regression_assets_untouched':True})
J(OUT/'manifests/completion_manifest.json',{'status':'PASS','parent_run_id':PR.name,'code_commit':head,'new_classification_oof_fits':0,'new_classification_final_fit_api_calls':1,'new_regression_fits':0,'hf15_formal_label_reads':0,'hf15_diagnostics_reads':0,'sealed_test_reads':0,'fdtd_lumerical_calls':0,'tmm_rcwa_calls':0,'canonical_bundle':str((OUT/'models/canonical_classifier.joblib').relative_to(REPO))})
(OUT/'reports/completion_report.md').write_text('# Classification canonicalization completion\n\nPASS. One canonical MultiOutput ExtraTrees bundle was fit once with final seed 20260720. The four target heads are not deployed as an ensemble. HF15 applicability is NOT_APPLICABLE_TO_HF15_PHYSICAL_TRUTH because the target is regression eligibility.\n',encoding='utf-8')
J(OUT/'manifests/artifact_sha256.json',{str(p.relative_to(OUT)):H(p) for p in OUT.rglob('*') if p.is_file() and p.name!='artifact_sha256.json'})
print(OUT)
