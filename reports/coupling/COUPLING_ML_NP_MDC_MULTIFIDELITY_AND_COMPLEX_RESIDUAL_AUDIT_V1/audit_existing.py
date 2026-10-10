import pathlib,sys,json,hashlib,subprocess,datetime,ast
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
W=pathlib.Path(r'D:\project\worktrees'); P=W/'blue_apcd_mdc_np_coupling_ml_v1'
O=P/'reports/coupling/COUPLING_ML_NP_MDC_MULTIFIDELITY_AND_COMPLEX_RESIDUAL_AUDIT_V1'
O.mkdir(exist_ok=True)
def sha(f):return hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()
def read(f):return json.loads(pathlib.Path(f).read_text(encoding='utf-8-sig'))
def write(n,v):(O/n).write_bytes((json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
def git(*args):return subprocess.run(['git','-C',str(P),*args],capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
D=P/'reports/coupling/COUPLING_ML_PARTIAL_DEVELOPMENT_DIAG_33G_2FITS_V1'
M=read(D/'DATASET_SHA256_MANIFEST_V1.json');R=read(D/'RESULT_V1.json')
sources=[]
def bind(f,expected=None):
 f=pathlib.Path(f);h=sha(f)
 if expected:assert h.lower()==expected.lower(),str(f)
 sources.append({'path':str(f),'sha256':h,'expected_sha256':expected,'verified':True})
 return f
bind(D/'DATASET_SHA256_MANIFEST_V1.json',R['dataset_manifest_sha256'])
for n in ['RESULT_V1.json','PREFIT_PROTOCOL_V1.json','PARTIAL_DIAGNOSTIC_CONFIG_V1.json','FIT_LEDGER_V1.json','CONTINUATION.md']:bind(D/n)
old=bind(P/M['old32']['dataset_path'],M['old32']['dataset_sha256'])
truth={}
with np.load(old,allow_pickle=False) as z:
 for i,c in enumerate(z['case_ids']):truth[str(c)]=(z['C_hat'][i],z['P_scale'][i])
for row in M['new33']['cases']:
 f=bind(row['label_npz_path'],row['label_npz_sha256'])
 with np.load(f,allow_pickle=False) as z:
  assert np.array_equal(z['wavelengths_nm'],np.arange(440,461))
  assert np.array_equal(z['order_m'],np.arange(-3,4))
  assert list(z['polarization'])==['TE','TM']
  c=str(z['case_id'].item());assert c==row['case_id'];assert row['role'] in ['DEVELOPMENT_LOCAL_AXIS','DEVELOPMENT_GLOBAL']
  if 'role' in z: assert str(z['role'].item())==row['role']
  truth[c]=(z['C_hat_real']+1j*z['C_hat_imag'],z['P_scale']) if 'C_hat_real' in z else ((z['C_hat'],z['P_scale']) if 'C_hat' in z else (z['c_hat'],z['p_scale']))
assert set(truth)==set(M['combined_ordered_case_ids']) and len(truth)==65
ct=np.stack([truth[c][0] for c in R['validation_case_ids']])
cn=np.linalg.norm(ct.reshape(13,-1),axis=1)
assert np.all(cn>0)
diag={'dataset':{'total':65,'train':52,'validation':13,'validation_old':8,'validation_local':1,'validation_global':4},
 'zero_state_relative_rmse': [1.0]*13,'state_definition':'sqrt(sum(abs(pred-truth)^2)/sum(abs(truth)^2)) over all wavelength/order/TE-TM per geometry',
 'models':{},'no_oracle_alignment':True,'no_prediction_changes':True}
for name in ['RBF_KRR','CARTESIAN_MLP']:
 f=bind(D/'fit_artifacts'/name/'predictions.npz')
 with np.load(f,allow_pickle=False) as z:
  assert list(z['case_ids'])==R['validation_case_ids'];cp=z['c_hat'];pp=z['p_scale']
 assert cp.shape==ct.shape and np.isfinite(cp).all() and np.all(pp>0)
 rn=np.linalg.norm(cp.reshape(13,-1),axis=1)/cn
 err=np.linalg.norm((cp-ct).reshape(13,-1),axis=1)/cn
 saved=R['models'][name]['original_h1_diagnostic']
 assert np.allclose(err,[v['state_relative_rmse'] for v in saved['aggregate']['per_geometry']],atol=1e-12,rtol=0)
 cosine=np.real(np.sum(cp.conj()*ct,axis=(1,2,3)))/(np.linalg.norm(cp.reshape(13,-1),axis=1)*cn)
 assert np.allclose(err**2,1+rn**2-2*rn*cosine,atol=1e-12)
 rows=[]
 for i,c in enumerate(R['validation_case_ids']):
  role='OLD32' if c.startswith('K6V1_') else ('LOCAL_AXIS' if c.startswith('K6LDA1_') else 'GLOBAL')
  rows.append({'case_id':c,'cohort':role,'norm_ratio':float(rn[i]),'complex_cosine_real_inner_product':float(cosine[i]),**saved['aggregate']['per_geometry'][i]})
 groups={}
 for cohort in ['OLD32','LOCAL_AXIS','GLOBAL']:
  v=[r for r in rows if r['cohort']==cohort]
  groups[cohort]={'count':len(v),'state_median':float(np.median([r['state_relative_rmse'] for r in v])),'norm_ratio_median':float(np.median([r['norm_ratio'] for r in v]))}
 sse=np.abs(cp-ct)**2
 diag['models'][name]={'per_geometry':rows,'cohorts':groups,'norm_ratio_median':float(np.median(rn)),
  'state_sse_by_wavelength':sse.sum(axis=(0,2,3)).tolist(),'state_sse_by_order':sse.sum(axis=(0,1,3)).tolist(),
  'state_sse_by_TE_TM':sse.sum(axis=(0,1,2)).tolist(),'truth_energy_by_TE_TM':(np.abs(ct)**2).sum(axis=(0,1,2)).tolist(),
  'original_h1':{k:v for k,v in saved.items() if k in ['gates','all_applicable_numeric_gates_attained','seed_stability_status']},
  'aggregate_metrics':saved['aggregate']['metrics'],'training_loss':R['models'][name]['training_loss'],
  'validation_loss':R['models'][name]['validation_loss'],'updates':R['models'][name]['actual_updates'],'best_update':R['models'][name]['best_update']}
# Bind official MDC prior exact handoff values, and NP later contract child hashes.
handoff=read(P/'reports/coupling/MDC_TMM_COMPLEX_2PORT_PRIOR_V1_HANDOFF.json')
bind(P/'reports/coupling/MDC_TMM_COMPLEX_2PORT_PRIOR_V1_HANDOFF.json')
for key,pathkey in [('artifact_sha256','artifact_path'),('source_code_sha256','source_code'),('report_sha256','report_path')]:
 bind(W/'blue_apcd_mdc_hf_surrogate_v2'/handoff['source_authority'][pathkey],handoff['source_authority'][key])
N=W/'blue_apcd_np_k6_mdc_v1';nc=read(N/'outputs/np_k6_complex_two_port_reference_plane_contract_v1/contract_manifest.json')
bind(N/'outputs/np_k6_complex_two_port_reference_plane_contract_v1/contract_manifest.json')
for n,v in nc['artifacts'].items():
 f=N/v['path'] if n=='report' else N/'outputs/np_k6_complex_two_port_reference_plane_contract_v1'/n
 bind(f,v['sha256'])
feat=read(P/'reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2/feature_manifest_v2.json')
bind(feat['runtime_adapter_path'],feat['runtime_adapter_sha256'])
for branch,rels in {
 'blue_apcd_np_k6_mdc_v1':['reports/NP_K6_COMPLEX_FORWARD_SURROGATE_BENCHMARK_V1.md','reports/NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1.md','reports/NP_K6_COMPLEX_PROVIDER_AND_COUPLING_RESIDUAL_POC_V1.md','reports/NP_K6_COUPLING_FORWARD_RUNTIME_COVERAGE_V2.md','scripts/np_k6_hf22_complex_scattering_state_extractor_v1.py','docs/np_k6_m9a_normal_incidence_plateau_reassessment_and_coupling_handoff_v1.md','docs/np_k6_m11_alt1_sparse_angular_provider_calibration_and_handoff_v1.md'],
 'blue_apcd_mdc_hf_surrogate_v2':['reports/MDC_COMPLEX_PRIOR_ZERO_SOLVER_CAPABILITY_AUDIT_V1.md'],
 'blue_apcd_mdc_rg_traditional_v1':['reports/mdc_rg_traditional_v1_blue_authority_provenance.json'],
 'blue_apcd_mdc_np_coupling_ml_v1':['reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json','scripts/coupling_ml/k6_v2_pipeline/h1.py','scripts/coupling_ml/k6_v2_pipeline/contracts.py','scripts/coupling_ml/k6_v2_pipeline/models.py','scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py','reports/coupling/COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1/COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1.md','reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2.md','reports/coupling/COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1/COUPLING_ML_TRAIN_VALIDATION_TRAJECTORY_AUDIT_V1.md','reports/coupling/APCD_GPU_V2_G027_FIRST_SCIENTIFIC_ENTRY_AND_INTEGRATED_TRUTH_VALIDATION_V1/CONTINUATION.md']
 }.items():
 for rel in rels:bind(W/branch/rel)
F=next((W/'blue_apcd_mdc_hf_surrogate_v2'/'outputs/mdc_hf_surrogate_v3_mdc_np_handoff_v1').iterdir())
for n in ['mdc_v3_model_identity.json','mdc_v3_capability_scope.json','level0_mdc_provider_contract.json']:bind(F/n)
write('READ_ONLY_METRICS.json',diag)
write('EVIDENCE_INDEX.json',{'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':sources,
 'heads':{n:subprocess.run(['git','-C',str(W/n),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip() for n in ['blue_apcd_mdc_np_coupling_ml_v1','blue_apcd_np_k6_mdc_v1','blue_apcd_mdc_hf_surrogate_v2']},
 'counts':{'solver':0,'training':0,'P_scale_fits':0,'replay':0,'confirmation_response_access':0,'FSP_LOAD':0},
 'checks':{'65_label_identity':True,'all_expected_source_hashes':True,'saved_state_metric_reproduction':True,'complex_norm_identity':True},
 'dirty_status':git('status','--short')})
print(json.dumps({name:{k:v for k,v in q.items() if k in ['cohorts','norm_ratio_median']} for name,q in diag['models'].items()},indent=2))
