from pathlib import Path
import csv, hashlib, json
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
ROOT = HERE.parent.parent if HERE.parent.name == 'scripts' else HERE.parent
EVAL = ROOT / 'outputs/mdc_replacement_hf_external_r12_solver_evaluation_v1/20260802T150000Z_R12_SOLVER'
PRE = ROOT / 'outputs/mdc_replacement_hf_external_r12_cleanroom_geometry_prelabel_freeze_v1/20260802T131000Z_R12_PRELABEL'
PARENT = ROOT / 'outputs/mdc_non_hf15_fixed_v1_internal_retrain_oof_v1/20260802T091739Z_90abc54ff31f_datafrozen_modelfrozen'
CANON = ROOT / 'outputs/mdc_fixed_v1_classification_canonicalization_v1/20260802T101700Z_90abc54ff31f/manifests/canonical_classifier_bundle_manifest.json'
REVIEW = EVAL / 'promotion_review'
REVIEW.mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rd(p): return json.loads(Path(p).read_text())
def out(name, obj): (REVIEW / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n', encoding='utf-8')

full = rd(EVAL/'replacement_full_cohort_metrics.json')
routed = rd(EVAL/'replacement_routed_metrics.json')
metric_sha = rd(EVAL/'replacement_metric_sha.json')
coverage = rd(EVAL/'replacement_routing_coverage.json')
completion = rd(EVAL/'completion_manifest.json')
pred_sha = rd(PRE/'prelabel/replacement_prediction_sha.json')
route_sha = rd(PRE/'prelabel/replacement_routing_sha.json')
lock = rd(PRE/'prelabel/replacement_prelabel_lock.json')
canon = rd(CANON)
reg_hashes = {p.name: sha(p) for p in sorted(PARENT.rglob('regression_final_*.joblib'))}
expected_pred = '80cf649a194aa95f362388a619c095c3e2fb97626cc54ca37df9b84ddc72a061'
expected_route = '2f0bc3223a9228e8c4c9c494942178fe203e3959598bdaeb635bc6e1da5f56a0'

integrity = {'git_head_expected':'4c49cc19ddd7d582ee784178f2aa6df641fdacfc','prelabel_lock_status':lock.get('status'),'prediction_sha_expected':expected_pred,'prediction_sha_observed':pred_sha.get('sha1'),'prediction_replay_identical':pred_sha.get('identical'),'routing_sha_expected':expected_route,'routing_sha_observed':route_sha.get('sha1'),'routing_replay_identical':route_sha.get('identical'),'join_sha':metric_sha['replay_1']['hashes']['join_membership_sha'],'residual_sha':metric_sha['replay_1']['hashes']['replacement_row_level_residuals.parquet'],'summary_full_sha':metric_sha['replay_1']['hashes']['replacement_full_cohort_metrics.json'],'summary_routed_sha':metric_sha['replay_1']['hashes']['replacement_routed_metrics.json'],'conformal_observation_sha':metric_sha['replay_1']['hashes']['replacement_conformal_external_observation.json'],'metric_replay_identical':metric_sha['identical'],'canonical_bundle_sha':canon['bundle_sha256'],'regression_final_hashes':reg_hashes,'solver_calls':completion['total_solver_calls'],'HF15_reads':completion['HF15_formal_reads'],'sealed_test_reads':completion['sealed_test_reads']}
integrity['status'] = 'PASS' if integrity['prelabel_lock_status'] == 'FROZEN_PRELABEL_AWAITING_SOLVER_AUTHORIZATION' and integrity['prediction_sha_observed'] == expected_pred and integrity['routing_sha_observed'] == expected_route and integrity['metric_replay_identical'] and integrity['solver_calls'] == 72 and integrity['HF15_reads'] == 0 and integrity['sealed_test_reads'] == 0 else 'HARD_GATE_PROMOTION_REVIEW_INPUT_DRIFT'
out('promotion_input_integrity_audit.json', integrity)

targets = [('spectral_fwhm_normal_nm','spectral FWHM','nm',4,0),('angular_fwhm_450_deg','angular FWHM@450 nm','deg',4,1),('cone5_integral_proxy','cone5 proxy','unitless',5,2)]
def extremes(m):
    d = m.get('per_geometry_residual', {})
    if not d: return {'worst_geometry_hash':'NOT_PREDEFINED','best_geometry_hash':'NOT_PREDEFINED'}
    w = max(d,key=lambda k:abs(d[k])); b = min(d,key=lambda k:abs(d[k]))
    return {'worst_geometry_hash':w,'worst_absolute_residual':abs(d[w]),'best_geometry_hash':b,'best_absolute_residual':abs(d[b])}
extract = {'source_full':str(EVAL/'replacement_full_cohort_metrics.json'),'source_routed':str(EVAL/'replacement_routed_metrics.json'),'source_full_sha256':sha(EVAL/'replacement_full_cohort_metrics.json'),'source_routed_sha256':sha(EVAL/'replacement_routed_metrics.json'),'targets':{}}
for key,label,unit,digits,ix in targets:
    extract['targets'][key] = {'label':label,'unit':unit,'full_cohort':{**full[key],**extremes(full[key]),'eligible_count':12,'abstain_count':0,'routing_coverage':1.0},'eligibility_routed':{**routed[key],**extremes(routed[key]),'eligible_count':coverage['eligible_count_by_target'][key],'abstain_count':coverage['abstain_count_by_target'][key],'routing_coverage':coverage['eligible_count_by_target'][key]/12}}
out('formal_metric_extraction.json', extract)

expected = {'spectral_fwhm_normal_nm':(26.6601,28.9424,-26.3723,4),'angular_fwhm_450_deg':(38.6215,45.8802,-33.3040,4),'cone5_integral_proxy':(0.06207,0.06771,-0.04391,5)}
checks = {}
for key,(a,b,c,digits) in expected.items():
    checks[key] = {'stored':{'MAE':full[key]['MAE'],'RMSE':full[key]['RMSE'],'bias':full[key]['bias']},'displayed':{m:round(full[key][m],digits) for m in ('MAE','RMSE','bias')},'expected_displayed':{'MAE':a,'RMSE':b,'bias':c},'match':all(round(full[key][m],digits)==v for m,v in (('MAE',a),('RMSE',b),('bias',c)))}
out('formal_metric_summary_check.json', {'status':'PASS' if all(v['match'] for v in checks.values()) else 'HARD_GATE_FORMAL_METRIC_SUMMARY_CONFLICT','checks':checks})

geo = pd.read_parquet(EVAL/'replacement_r12_geometry_labels_v1.parquet')
pred = pd.read_parquet(PRE/'prelabel/replacement_prelabel_regression_predictions.parquet')
route = pd.read_parquet(PRE/'prelabel/replacement_prelabel_eligibility_routing.parquet')
joined = geo.merge(pred,on='geometry_hash',validate='one_to_one').merge(route,on='geometry_hash',validate='one_to_one')
def rank_view(df,key,ix):
    y=df[key].to_numpy(float); p=np.array([json.loads(x)[ix] for x in df.ensemble_mean],float); n=len(y); inv=sum((y[i]-y[j])*(p[i]-p[j])<0 for i in range(n) for j in range(i+1,n)); ry=pd.Series(y).rank().to_numpy(); rp=pd.Series(p).rank().to_numpy(); corr=float(np.corrcoef(ry,rp)[0,1]) if n>1 and np.std(ry)>0 and np.std(rp)>0 else None; status='RANK_EVIDENCE_UNDEFINED' if corr is None else ('RANK_EVIDENCE_POSITIVE' if corr>0 and inv<n*(n-1)/4 else ('RANK_EVIDENCE_WEAK' if corr>0 else 'RANK_EVIDENCE_NEGATIVE')); order=[{'geometry_hash':h,'truth':float(t),'prediction':float(q),'truth_rank':int(r1),'prediction_rank':int(r2)} for h,t,q,r1,r2 in zip(df.geometry_hash,y,p,pd.Series(y).rank(method='min'),pd.Series(p).rank(method='min'))]; return {'n':n,'spearman':corr,'rank_inversions':int(inv),'pair_count':n*(n-1)//2,'evidence_status':status,'ordering':sorted(order,key=lambda z:z['truth_rank'])}
rank = {}
for key,_,_,_,ix in targets:
    mask=np.array([json.loads(x)[ix]>json.loads(t)[ix] for x,t in zip(joined.calibrated_probability,joined.threshold)])
    rank[key]={'full_cohort':rank_view(joined,key,ix),'eligibility_routed':rank_view(joined[mask].reset_index(drop=True),key,ix),'mathematical_validity':{'full':True,'routed':int(mask.sum())>1}}
out('targetwise_rank_evidence.json',rank)

rows=[]
for key,label,unit,_,_ in targets:
    rows.append({'target':label,'internal_source':str(PARENT/'reports/mdc_ml_fixed_v1_internal_training_oof_v1.json'),'internal_metric_status':'NOT_PREDEFINED','internal_metric_definition':'ordinary-TMM label-fit internal NON-HF15 OOF evidence; no frozen summary metric artifact','replacement_full_MAE':full[key]['MAE'],'replacement_full_RMSE':full[key]['RMSE'],'replacement_full_bias':full[key]['bias'],'replacement_routed_n':routed[key]['n'],'physical_same':False,'direct_comparison_allowed':False,'reason':'internal ordinary-TMM fit versus replacement FDTD external transfer'})
with (REVIEW/'internal_vs_external_evidence_matrix.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)

matrix={}
for key,label,unit,_,_ in targets:
    matrix[key]={'quantitative_high_fidelity_support':'REJECTED','rank_order_evidence':rank[key],'routed_operational_evidence':{'eligible_count':coverage['eligible_count_by_target'][key],'abstain_count':coverage['abstain_count_by_target'][key],'coverage':coverage['eligible_count_by_target'][key]/12},'conformal_external_observation':{'full_rate':full[key]['observed_conformal_inclusion_rate'],'routed_rate':routed[key]['observed_conformal_inclusion_rate'],'interpretation':'external observation only'},'systematic_bias_direction':'UNDERPREDICTION' if full[key]['bias']<0 else 'OVERPREDICTION','small_n_limitation':'12 full-cohort geometries; routed n='+str(routed[key]['n']),'allowed_future_use':'descriptive replacement reporting; target-specific rank-only review','prohibited_claim':'quantitative high-fidelity surrogate validity or automatic promotion'}
out('targetwise_promotion_evidence_matrix.json',matrix)
out('classification_scope_statement.json',{'semantic':'REGRESSION_ELIGIBILITY','replacement_physical_classification_truth':False,'allowed':['NON_HF15_INTERNAL_REGRESSION','NON_HF15_REGRESSION_ELIGIBILITY_ROUTING','DESCRIPTIVE_REPLACEMENT_R12_EXTERNAL_REPORTING'],'forbidden':['external classification accuracy','ROC-AUC','Brier','physical-performance validation']})
out('transmission_noncomparability_statement.json',{'fixed_v1_target':'normal_band_transmission_proxy','replacement_field':'eta_up_r12_relative','status':'NOT_NUMERICALLY_COMPARABLE','in_quantitative_promotion_evidence':False,'extraction_efficiency_claim':False})
out('fixed_v1_promotion_review_registry.json',{'model_bundle':'MDC_FIXED_V1','quantitative_high_fidelity_promotion':'REJECTED','sealed_test_authorized':False,'sealed_test_status':'UNTOUCHED','model_state':'FROZEN','allowed_current_uses':['NON_HF15_INTERNAL_REGRESSION','NON_HF15_REGRESSION_ELIGIBILITY_ROUTING','DESCRIPTIVE_REPLACEMENT_R12_EXTERNAL_REPORTING'],'pending_manual_scope_decisions':['SPECTRAL_RANK_ONLY','ANGULAR_RANK_ONLY','CONE5_RANK_ONLY'],'prohibited_actions':['SEALED_TEST_ACCESS','FIXED_V1_REFIT','POSTHOC_CALIBRATION','POSTHOC_THRESHOLD_CHANGE','REPLACEMENT_R12_MODEL_SELECTION','REPLACEMENT_R12_TRAINING','ADDITIONAL_SOLVER','HF15_BLIND_REUSE'],'status':'MDC_FIXED_V1_QUANTITATIVE_HF_PROMOTION_REJECTED_RANK_ONLY_SCOPE_REVIEW_READY'})

report='# Fixed-v1 promotion review evidence\n\nOverall quantitative high-fidelity promotion: **REJECTED**. Spectral and angular FWHM show large external error and systematic underprediction; cone5 is one target-specific result and does not overturn the bundle decision. The normal-band transmission proxy is not comparable with `eta_up_r12_relative`.\n\nInternal NON-HF15 OOF evidence measures ordinary-TMM label fit. Replacement R12 measures cross-fidelity FDTD external transfer; internal OOF performance does not establish external validity. Models remain frozen. Current uses are limited to internal regression, frozen eligibility routing, and descriptive R12 reporting. No sealed-test, HF15 reuse, refit, posthoc calibration, threshold change, additional solver, or fixed-v2 action is permitted.\n'
(REVIEW/'promotion_review_report.md').write_text(report,encoding='utf-8')
review_completion={'status':'MDC_FIXED_V1_QUANTITATIVE_HF_PROMOTION_REJECTED_RANK_ONLY_SCOPE_REVIEW_READY','quantitative_high_fidelity_promotion':'REJECTED','model_state':'FROZEN','new_model_fits':0,'optimizer_backward':0,'solver_calls':0,'TMM_calls':0,'RCWA_calls':0,'HF15_reads':0,'sealed_test_reads':0,'formal_metric_definitions_added':0,'input_integrity_status':integrity['status'],'metric_summary_status':'PASS' if all(v['match'] for v in checks.values()) else 'HARD_GATE_FORMAL_METRIC_SUMMARY_CONFLICT'}
out('completion_manifest.json',review_completion)
files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for p in sorted(REVIEW.rglob('*')) if p.is_file() and p.name!='artifact_sha256.json'}
out('artifact_sha256.json',files)
print(json.dumps(review_completion,sort_keys=True))
