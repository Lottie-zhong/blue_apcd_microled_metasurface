
import pathlib,json,hashlib,sys,datetime
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
P=pathlib.Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
A=P/'reports/coupling/APCD_GPU_V2_G027_FIRST_SCIENTIFIC_ENTRY_AND_INTEGRATED_TRUTH_VALIDATION_V1'
R=pathlib.Path(r'D:\apcd_runtime\gpu_v2_g027_postsolver_audit_20261010_v1')
O=P/'reports/coupling/G027_COUPLING_SCIENTIFIC_OWNER_READ_ONLY_ACK_V1';O.mkdir(exist_ok=True)
def read(f):return json.loads(pathlib.Path(f).read_text(encoding='utf-8-sig'))
def sha(f):
 h=hashlib.sha256()
 with pathlib.Path(f).open('rb') as r:
  for b in iter(lambda:r.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
evidence=[]
context_discrepancies=[]
def bind(f,expected=None):
 f=pathlib.Path(f);actual=sha(f)
 if expected:assert actual==expected,str(f)
 evidence.append({'path':str(f),'sha256':actual,'expected':expected,'pass':True})
 return f
old=read(A/'SHA256_INVENTORY.json');bind(A/'SHA256_INVENTORY.json')
for n,v in old['task_files'].items():bind(A/n,v['sha256'])
for n,v in old['external_artifacts'].items():bind(v['path'],v['sha256'])
inv=read(R/'SHA256_INVENTORY.json');bind(R/'SHA256_INVENTORY.json')
for n in ['REPORT.md','CONTINUATION.md','G027_SCIENTIFIC_REVIEW.json','installed_native_validation.json','installed_scheduler_acceptance.json','final_boundary_audit.json']:
 v=inv['files'][n]
 if n=='final_boundary_audit.json' and sha(v['path'])!=v['sha256']:
  context_discrepancies.append({'path':v['path'],'expected_sha256':v['sha256'],'actual_sha256':sha(v['path']),'classification':'GPU delivery inventory inconsistent; not used as scientific-data authority'})
 else:bind(v['path'],v['sha256'])
nv=read(R/'installed_native_validation.json');sr=read(R/'G027_SCIENTIFIC_REVIEW.json');acc=read(R/'installed_scheduler_acceptance.json');boundary=read(R/'final_boundary_audit.json')
assert nv['verdict']==sr['data_contract']==acc['verdict']=='PASS'
assert nv['record']['case_id']=='K6GDP2_DEV_G027' and nv['record']['attempt_id']=='attempt_001'
for k in ['source_manifest','state_npz','state_metadata','raw_npz','raw_metadata','orders_json','truth_h5']:
 v=nv['record'][k];bind(v['path'],v['sha256'])
v=nv['labels_artifact'];new=bind(v['path'],v['sha256']);pub=old['external_artifacts']['published_labels'];orig=bind(pub['path'],pub['sha256'])
delta={}
with np.load(new,allow_pickle=False) as x,np.load(orig,allow_pickle=False) as y:
 assert set(x.files)==set(y.files)
 for k in x.files:
  assert np.array_equal(x[k],y[k]),k
  delta[k]=0 if x[k].dtype.kind not in 'US' else 'equal'
 c=x['C_hat_real']+1j*x['C_hat_imag'];ps=x['P_scale'];eta=x['eta'];ab=x['absolute_order']
 assert c.shape==(21,7,2) and ps.shape==(21,) and np.isfinite(c).all() and np.isfinite(ps).all() and np.all(ps>0)
 assert np.array_equal(x['wavelengths_nm'],np.arange(440,461)) and np.array_equal(x['order_m'],np.arange(-3,4)) and list(x['polarization'])==['TE','TM']
sys.path.insert(0,str(P/'scripts'))
from coupling_ml.k6_v2_pipeline import h1
decoder=h1.load_h2_decoder();decoded=h1.reconstruct_h2(c,ps,decoder)
h2diff={k:float(np.max(np.abs(decoded[k][0]-t))) for k,t in [('eta',eta),('absolute_order',ab),('total_power',ps)]}
assert h2diff['total_power']==0.0
assert np.max(np.abs(decoded['eta'].sum(axis=-1)-1.0))<1e-12
assert np.max(np.abs(ab.sum(axis=-1)-ps))<1e-12
# H2 modal vs native-grating differences are retained diagnostics, not a new gate.
bind(P/'scripts/coupling_ml/k6_v2_pipeline/h1.py')
bind(P/'scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py','b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15')
ledger=read(old['external_artifacts']['coupling_ledger']['path'])
assert sha(old['external_artifacts']['coupling_ledger']['path'])==boundary['coupling_budget_sha256']
result={'schema':'G027_COUPLING_SCIENTIFIC_OWNER_ACK_V1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'data_contract':'PASS','case_id':'K6GDP2_DEV_G027','attempt_id':'attempt_001',
 'ack_status':'PARTIAL' if context_discrepancies else 'PASS','delivery_inventory_discrepancies':context_discrepancies,'installed_revalidation_code_head':inv['installed_binding']['code_head'],'original_consumed_code_head':old['executed_code_head'],
 'new_labels_vs_original':delta,'h2_vs_native_grating_max_abs_delta_diagnostic':h2diff,'source_sha_evidence':evidence,
 'normalization_and_phase':{'reference_POSTNP_nm':1722,'phase':'one global phase per wavelength from IN_REF +z (0,0) TM; shared across planes/components; relative phase preserved','P_scale':'POSTNP full-period E/H flux / IN_REF incident cell power','same_saved_run_reextraction':'PASS','oracle_phase_alignment':False},
 'budget_snapshot':{'entered_count':ledger['entered_count'],'truth_valid_count':ledger['truth_valid_count'],'labels_valid_count':ledger['labels_valid_count'],'remaining_unentered_count':128-ledger['entered_count']},'original_G027_entry':1,'original_G027_replay':0,
 'execution_counts':{'solver':0,'training':0,'replay':0,'confirmation_response_access':0,'native_LOAD':0},
 'limitations':['algebraic A=1-R-T closure is not independent absorption validation','planar TMM vs patterned integrated differences are diagnostics, not a new frozen gate','deembedding roundtrip is algebraic, not independent two-plane verification','monitor flux checks do not prove mesh convergence or cross-run scientific repeatability','one incident state is not a full Jones or multiport operator','no batch launch authority or continuous-production qualification issued']}
(O/'RECEIPT.json').write_bytes((json.dumps(result,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
print('PASS',len(evidence),'sources; H2',h2diff,'all label arrays byte/element equal')
