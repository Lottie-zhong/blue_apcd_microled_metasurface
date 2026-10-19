from pathlib import Path
import json,csv,sys,hashlib,subprocess,importlib.util,copy,time
import numpy as np
from scipy.spatial.distance import cdist
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');O=R/'reports/coupling/APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1';A=R/'reports/coupling/APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';S=R/'scripts/coupling_ml/diag2_v31_migration_guard_v1.py'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest as I,contracts as C
from k6_v2_pipeline.amended156 import adapter as F
spec=importlib.util.spec_from_file_location('migration_guard',S);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,j):(O/n).write_text(json.dumps(j,indent=2,allow_nan=False,default=lambda z:z.tolist() if isinstance(z,np.ndarray) else z.item())+'\n',encoding='utf-8')
def sha(p):return I.sha256_file(p)
binding=read(R/'reports/coupling/APCD_COUPLING_DIAG2_FINAL_ADMISSION_BINDING_V1/FINAL_ADMISSION_BINDING_CHECK.json');contract=R/'reports/coupling/APCD_COUPLING_V21_SCIENCE_CONTRACT_CLOSEOUT_V1/SCIENCE_CONTRACT_6PS.json';doc=read(contract);assert sha(contract)==M.CONTRACT
source_checks=[]
for c in binding['candidate_binding']['cases']:
 for d in c['source_setup_checks']:
  actual=sha(d['path']);assert actual==d['expected_sha256'];source_checks.append({'case_id':c['case_id'],'role':d['role'],'path':d['path'],'sha256':actual,'match':True})
assert doc['only_allowed_physical_difference']=={'field':'fdtd.simulation_time_s','from_s':3e-12,'to_s':6e-12}
assert doc['shared_6ps_actual_setup_readback']['fdtd']['auto_shutoff_min']==1e-6
put('CONTRACT_SOURCE_AUDIT.json',{'status':'PASS','contract':str(contract),'physics_contract_sha':M.CONTRACT,'source_setup_checks':source_checks,'unchanged_scientific_fields':'Prior CONTRACT_DIFF.json proof retained; current file SHA matches frozen6ps; no rewrite','physical_simulation_time_s':6e-12,'auto_shutoff_min':1e-6,'scheduler_walltime_is_physical_time':False})
record={'schema':'APCD_COUPLING_DIAG2_V31_BUDGET_MIGRATION_REVIEW_RECORD_V1','record_kind':'NON_EXECUTABLE_MIGRATION_REVIEW_NOT_SCIENCE_ADMISSION','authority':'User APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1: principle approval of original2 budget carryover; zero solver now','batch_id':M.BATCH,'dataset_id':'APCD_COUPLING_V3_TIME_DIAG2_V1','new_entry_budget':0,'inherited_entry_ceiling':2,'physics_contract_sha':M.CONTRACT,'current_task_solver_authorization':0,'execution_enabled':False,'ledger_mutation':False,'cases':[]}
for cid,g in zip(M.CASE_IDS,M.GEOMETRIES):record['cases'].append({'case_id':cid,'attempt_id':'attempt_001','ordered_D_nm':g,'max_entries':1,'entered_count':0,'replay_count':0,'simulation_time_s':6e-12,'mesh_nm':5,'auto_shutoff_min':1e-6,'runner_job_id':None,'runner_execution_attempt':None,'platform_tag_policy':'future Runner execution tag maps to this immutable science attempt; never replaces it; no binding created now'})
M.validate_migration_record(record);put('BUDGET_MIGRATION_REVIEW_RECORD.json',record)
# Explicit narrow tests of only the new guard, not a full regression or fake run.
tests=[]
def rejects(label,mutate):
 t=copy.deepcopy(record);mutate(t)
 try:M.validate_migration_record(t)
 except ValueError as ex:tests.append({'test':label,'status':'PASS','rejection':str(ex)});return
 raise AssertionError(label)
tests.append({'test':'same_original_two_budget_semantics','status':'PASS','result':M.validate_migration_record(record)})
rejects('third_science_identity',lambda t:t['cases'].append(copy.deepcopy(t['cases'][0])))
rejects('budget3',lambda t:t.update(inherited_entry_ceiling=3))
rejects('new_budget2',lambda t:t.update(new_entry_budget=2))
rejects('attempt002',lambda t:t['cases'][0].update(attempt_id='attempt_002'))
rejects('entered_attempt',lambda t:t['cases'][0].update(entered_count=1))
rejects('replay',lambda t:t['cases'][0].update(replay_count=1))
rejects('geometry_permutation',lambda t:t['cases'][0].update(ordered_D_nm=list(reversed(t['cases'][0]['ordered_D_nm']))))
rejects('old3psSHA',lambda t:t.update(physics_contract_sha=C.PHYSICAL_CONTRACT_SHA256))
rejects('time3ps',lambda t:t['cases'][0].update(simulation_time_s=3e-12))
rejects('shutoff_relaxed',lambda t:t['cases'][0].update(auto_shutoff_min=1e-5))
rejects('premature_enable',lambda t:t.update(execution_enabled=True))
assert M.validate_completed_is_not_labels('COMPLETED',None)=='POSTPROCESS_PENDING_NOT_LABELS_VALID';tests.append({'test':'completed_not_labels_valid','status':'PASS'})
assert M.final_verdict([{'status':'PASS'}]*5+[{'status':'PARTIAL'}])=='DIAG2_V3_1_MIGRATION_HOLD';tests.append({'test':'six_gate_fail_closed','status':'PASS'})
put('TARGETED_MIGRATION_TESTS.json',{'tests':tests,'pass':len(tests),'fail':0,'solver_calls':0,'model_fits':0,'scope':'new migration identity policy only; existing model comparisons not rerun'})
# Reuse the frozen156 loader; it performs the already approved identity/provenance checks, no fits.
col=F.load_collection(False);cases=col.training_cases();assert len(cases)==156;plan=F.build_plan();heldout=[s for v in plan.outer_validation_ids.values() for s in v];assert len(heldout)==len(set(heldout))==124
old={c.case_id for c in cases if c.role==C.ROLE_OLD32};assert len(old)==32 and not old.intersection(heldout)
put('AL_ASSET_PRESERVATION.json',{'valid156':156,'old32_train_only':True,'new124_geometry_grouped':True,'roles':{r:sum(c.role==r for c in cases) for r in C.DEVELOPMENT_ROLES},'original_fit_counts':{'old_amended':'retained_no_fit','simple_forward':479,'AL_bootstrap':read(A/'TRAINING_COMPLETE.json')['fits']},'new_fits':0,'GPR_optional_previous_evidence':'retained previous simple-forward scalar benchmark; not refit','H1_H2_609D_unchanged':True,'sealed_responses':0})
reg=I.load_frozen_case_registry(R);protected={}
def add(g,why):
 try:
  if len(g)==6 and all(isinstance(v,(int,float,np.number)) and float(v).is_integer() and 0<float(v)<1000 for v in g):protected.setdefault(tuple(map(int,g)),set()).add(why)
 except (TypeError,ValueError):pass
def walk(v,why):
 if isinstance(v,dict):
  for k,a in v.items():
   if k in ['ordered_D_nm','ordered_D1_D6_nm','ordered_D1_D6','D_nm','geometry','diameters_nm']:add(a,why)
   if isinstance(a,(dict,list)):walk(a,why)
 elif isinstance(v,list):
  for a in v:
   if isinstance(a,(dict,list)):walk(a,why)
for name,rows in [('old32',reg.old32),('registered_dev_including_failed',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for row in rows.values():add(row['ordered_D_nm'],name)
for cid,g in zip(M.CASE_IDS,M.GEOMETRIES):add(g,'DIAG2_reserved:'+cid)
ex=read(A/'EXCLUSION_AUDIT.json');sources=[]
for s in ex['sources']:
 p=Path(s)
 if p.is_file():walk(read(p),'retained_metadata:'+s);sources.append(s)
# Extend to current runtime source/queue manifest metadata, never response/confirmation files.
for base in [Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data'),Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 if not base.exists():continue
 for p in base.rglob('*.json'):
  if p.name.lower() not in ['manifest.json','source_manifest.json','queue_manifest.json','batch_manifest.json']:continue
  if any(w in str(p).lower() for w in ['sealed','confirmation','fixture','validation']):continue
  walk(read(p),'runtime_manifest:'+str(p));sources.append(str(p))
with (A/'CANDIDATES_PROPOSED_16.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
geometry=np.array([[int(row[f'D{i}_nm']) for i in range(1,7)] for row in rows]);assert geometry.shape==(16,6) and len(set(map(tuple,geometry)))==16
pool=np.load(A/'PROVISIONAL_CANDIDATE_POOL.npz',allow_pickle=False);assert len(pool['ordered_D_nm'])==8192 and np.array_equal(geometry,pool['ordered_D_nm'][pool['selection_indices']])
conflicts=[{'proposal':rows[i]['proposal_id'],'D':g.tolist(),'reasons':sorted(protected[tuple(g)])} for i,g in enumerate(geometry) if tuple(g) in protected]
assert not conflicts
assert np.all((geometry>=100)&(geometry<=230)&((geometry-100)%5==0))
pair=cdist(geometry/130,geometry/130);pair[np.diag_indices(16)]=np.inf;near=cdist(geometry/130,np.array([c.ordered_D_nm for c in cases])/130).min(1)
domain=read(R/'reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json');domainstatus=domain['fabrication_constraint_authority'];assert 'UNRESOLVED' in domainstatus
fingerprints=[{'path':str(p),'sha256':sha(p),'meaning':'source byte fingerprint only; no new scientific identity or manufacturing approval'} for p in [A/'CANDIDATES_PROPOSED_16.csv',A/'PROVISIONAL_CANDIDATE_POOL.npz',R/'scripts/coupling_ml/gpu_active_learning_select_v1.py']]
put('AL16_HANDOFF_AUDIT.json',{'status':'VALID_RESEARCH_PROPOSALS_NOT_PRODUCTION_ADMISSIBLE','ordered_dimensions_verified':True,'pool_row_parity':True,'pool_size':8192,'proposal_count':16,'unique':16,'protected_unique_count':len(protected),'known_history_DOE56_DIAG2_sealed_geometry_conflicts':conflicts,'source_metadata_count':len(sources),'source_metadata_paths':sources,'full_cartesian_domain_enumerated':False,'global_queue_completeness':'BLOCKED by missing immutable science-job registry; no claim of universal live no-conflict','distance_convention':'Euclidean D/130nm','minimum_pair_distance':float(pair.min()),'nearest156_distances':near,'physical_nonoverlap_pass':bool((290-(geometry+np.roll(geometry,-1,axis=1))/2>0).all()),'manufacturing':'BLOCKED: '+domainstatus,'selection_mix':'8coverage/4disagreement/4stratified-random; not solely highest predicted efficiency','source_fingerprints':fingerprints,'new_legal_science_ids':0,'new_solver_budget':0})
print('MIGRATION_AUDIT_COMPLETE',json.dumps({'source_checks':len(source_checks),'policy_tests':len(tests),'valid156':len(cases),'AL16_conflicts':conflicts,'protected':len(protected)}),flush=True)
