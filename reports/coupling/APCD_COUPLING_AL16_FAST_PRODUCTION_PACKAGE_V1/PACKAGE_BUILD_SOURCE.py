from pathlib import Path
import json,subprocess,sys,importlib.util,csv,sqlite3,hashlib,time,numpy as np,socket
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';D=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';D.mkdir(exist_ok=False)
P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest as I
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).parent.mkdir(parents=True,exist_ok=True);(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda v:v.tolist() if hasattr(v,'tolist') else str(v)),encoding='utf-8')
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],text=True).strip()
baseline=dict(host=socket.gethostname(),user=subprocess.check_output(['whoami'],text=True).strip(),branch=git('branch','--show-current'),HEAD=git('rev-parse','HEAD'),ahead_behind=git('rev-list','--left-right','--count','HEAD...@{u}'),staged=git('diff','--cached','--name-only'),dirty_count=len(git('status','--short').splitlines()));put('GIT_BASELINE.json',baseline)
ledger=Q/'APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING/DIAG2_SCIENCE_LEDGER.json';lb=ledger.read_bytes();put('SCIENCE_LEDGER_BEFORE_METADATA.json',dict(path=str(ledger),entered=read(ledger)['entered_total'],remaining=read(ledger)['remaining_total'],bytes=len(lb)))
put('USER_IDEAL_GEOMETRY_ADMISSION.json',{'authority':'Direct user reply in current conversation','verbatim':'本轮批准理想几何FAST仿真准入，实际制造资格仍UNRESOLVED','scope':'Ideal-geometry simulation admission only; no actual manufacturing certification; no solver authorization','entries_authorized':0})
rows=list(csv.DictReader((A/'CANDIDATES_PROPOSED_16.csv').open(encoding='utf-8-sig')));geom=np.array([[int(r[f'D{i}_nm']) for i in range(1,7)] for r in rows]);pool=np.load(A/'PROVISIONAL_CANDIDATE_POOL.npz',allow_pickle=False);assert len(geom)==16 and np.array_equal(geom,pool['ordered_D_nm'][pool['selection_indices']]);assert len(set(map(tuple,geom)))==16
protected={};sources=[]
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
reg=I.load_frozen_case_registry(R)
for name,rr in [('old32',reg.old32),('development_including_failed',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for row in rr.values():add(row['ordered_D_nm'],name)
prev=read(Q/'APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1/AL16_HANDOFF_AUDIT.json')
for sn in prev['source_metadata_paths']:
 p=Path(sn)
 if p.is_file():walk(read(p),'metadata:'+sn);sources.append(sn)
for folder in [Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data'),Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 for p in folder.rglob('*.json'):
  if p.name.lower() not in ['manifest.json','source_manifest.json','queue_manifest.json','batch_manifest.json']:continue
  if any(w in str(p).lower() for w in ['sealed','confirmation','fixture','validation']):continue
  walk(read(p),'runtime_metadata:'+str(p));sources.append(str(p))
con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(x) for x in con.execute('select * from jobs')];entries=[dict(x) for x in con.execute('select * from solver_entries')];con.close()
for row in jobs:
 if row.get('manifest_json'):walk(json.loads(row['manifest_json']),'runner_job:'+str(row['id']))
 if row.get('case_id') in ['K6V3_TIME_DIAG2_A1_5NM_6PS','K6V3_TIME_DIAG2_A2_5NM_6PS']:
  add([120,160,165,175,160,195] if '_A1_' in row['case_id'] else [210,115,175,115,180,125],'DIAG2_reserved')
conflicts=[dict(proposal=rows[i]['proposal_id'],ordered_D_nm=g.tolist(),reasons=sorted(protected[tuple(g)])) for i,g in enumerate(geom) if tuple(g) in protected];assert not conflicts,conflicts
put('DEDUPLICATION_AUDIT.json',{'protected_unique':len(protected),'sources':sorted(set(sources)),'sealed_responses_accessed':0,'known_geometry_conflicts':conflicts,'all16_unique':True,'live_v31_jobs':jobs,'live_v31_entries':entries,'scope':'All previously verified protected metadata plus refreshed known runtime manifest metadata and canonical V31 jobs/entries. No claim over unregistered manual files; repeat snapshot before authorized submission.'})
contract=read(Q/'PW_K6_SEED_DB_V1_GEOMETRY_MANIFEST.json')['physical_contract'];assert I._canon(contract['contract'])==contract['contract_sha256'];put('FAST_FROZEN_PHYSICS_CONTRACT.json',contract)
B=Q/'APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1';proof=read(B/'A1_SETUP_LOAD_PROOF.json');template=Path(proof['candidate_fsp_path']);assert I.sha256_file(template)==proof['candidate_fsp_sha256']
# Verified setup-only template. All existing sources/monitors/materials retained; only duration restored to frozen3ps and per-case radii changed.
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python');import lumapi
s=importlib.util.spec_from_file_location('al16_existing_builder',R/'scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
props={'FDTD':['dimension','x span','y span','z min','z max','x min bc','x max bc','y min bc','y max bc','z min bc','z max bc','pml layers','mesh accuracy','mesh refinement','dt stability factor','simulation time','auto shutoff min'],b.CORE_MESH['name']:['x','y','z','x span','y span','z span','dx','dy','dz'],b.BACKGROUND_MESH['name']:['x','y','z','x span','y span','z span','dx','dy','dz'],'SPACER_LAYER':['material','z min','z max','x span','y span']}
for name in b.SOURCE_PROFILE['names']:props[name]=['enabled','plane wave type','injection axis','direction','polarization angle','angle theta','angle phi','x','y','z','x span','y span','wavelength start','wavelength stop','amplitude','phase','frequency dependent profile']
for name in ['MON_IN','MON_PRENP','MON_POSTNP','MON_REFLECTION']:props[name]=['monitor type','x','y','z','x span','y span','override global monitor settings','use source limits','use wavelength spacing','frequency points','output power']
for i in range(1,13):props[f'MDC_LAYER_{i:02d}']=['material','z min','z max','x span','y span']
for i in range(1,7):props[f'NP_D{i}']=['x','y','radius','z min','z max','material']
def val(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 return x
def snap(fd):return {o:{p:val(fd.getnamed(o,p)) for p in ps} for o,ps in props.items()}
cases=[];t0=time.time();fd=lumapi.FDTD(hide=True)
try:
 fd.load(str(template));assert int(fd.layoutmode())==1,'template not setup layout';base=snap(fd);put('TEMPLATE_BASE_READBACK.json',base)
 for rank,(row,g) in enumerate(zip(rows,geom),1):
  cid=f'K6AL_FAST_R01_G{rank:03d}';attempt='attempt_001';eid='coupling:'+cid+'/'+attempt
  assert all(cid!=x.get('case_id') and eid!=x.get('external_execution_id') for x in jobs)
  target=D/'inputs'/cid/attempt/'pre.fsp';assert not target.exists();target.parent.mkdir(parents=True)
  b.validate_geometry(g.tolist());fd.load(str(template));assert int(fd.layoutmode())==1
  fd.setnamed('FDTD','simulation time',3e-12)
  for i,d in enumerate(g,1):fd.setnamed(f'NP_D{i}','radius',float(d)*.5e-9)
  fd.save(str(target));fd.load(str(target));actual=snap(fd);expected=json.loads(json.dumps(base));expected['FDTD']['simulation time']=3e-12
  for i,d in enumerate(g,1):expected[f'NP_D{i}']['radius']=float(d)*.5e-9
  assert actual==expected,('readback mismatch',cid)
  assert actual['FDTD']['auto shutoff min']==1e-6
  assert np.allclose([actual[b.CORE_MESH['name']][k] for k in ['dx','dy','dz']],[5e-9]*3,rtol=0,atol=1e-20)
  source_sha=I.sha256_file(target);gaps=290-(g+np.roll(g,-1))/2;ygap=290-g;half=(290-g)/2;ar=500/g
  checks={'ideal_geometry_simulation_admission':'PASS_USER_APPROVED','actual_manufacturing':'UNRESOLVED','diameter_domain_observed':[100,230],'step_nm':5,'D1_to_D6_not_sorted':True,'centers_x_nm':b.pillar_centers_nm(290,6),'pitch_nm':290,'height_nm':500,'spacer_nm':237,'material':'APCD_TIO2_NATIVE_M1','periodic_x_gaps_nm':gaps.tolist(),'periodic_y_gaps_nm':ygap.tolist(),'half_cell_margins_nm':half.tolist(),'aspect_ratios_H_over_D':ar.tolist(),'physical_nonoverlap':bool((gaps>0).all() and (ygap>0).all()),'manufacturing_minimum_gap_limit':None,'manufacturing_minimum_edge_margin_limit':None,'manufacturing_maximum_aspect_ratio':None,'sidewall_taper_roughness_and_process_limits':'UNRESOLVED; ideal vertical cylinders only'}
  assert checks['physical_nonoverlap']
  rec={'case_id':cid,'attempt_id':attempt,'external_execution_id':eid,'external_job_id':'coupling:'+cid,'proposal_id':row['proposal_id'],'selection_reason':row['reason'],'ordered_D_nm':g.tolist(),'input_fsp':str(target),'source_fsp_sha256':source_sha,'physical_contract_sha256':contract['contract_sha256'],'budget_proposal_id':'AL16_FAST_R01_BUDGET_PROPOSAL_V1','maximum_entries':1,'entries_authorized':0,'solver_entered':False,'science_output_directory':str(D/'science_outputs'/cid/attempt),'manufacturing_checks':checks,'setup_readback_file':str(D/'checks'/f'{cid}_SETUP_READBACK.json'),'profile':'coupling_609d_v1','numerical_grade':'ML_TRAINING_GRADE','strict_convergence':'NOT_CERTIFIED','fidelity_role':'FAST_DATASET'}
  put('checks/'+cid+'_SETUP_READBACK.json',{'case_id':cid,'source_sha256':source_sha,'fresh_load_readback':actual,'expected_delta_from_template':{'simulation_time_s':[6e-12,3e-12],'radii_nm':(g/2).tolist()},'all_other_audited_properties_identical':True,'solver_run_called':False});cases.append(rec);put('CASE_PREPARATION_PROGRESS.json',{'completed':rank,'total':16,'elapsed_s':time.time()-t0,'new_entries':0});print('SAVED',rank,cid,source_sha,flush=True)
finally:fd.close()
put('AL16_CASES.json',cases)
resource=read(Q/'APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING/K6V3_TIME_DIAG2_A1_5NM_6PS_MANIFEST.json')['jobs'][0]['resource_requirements']
jobsout=[{k:c[k] for k in ['input_fsp','source_fsp_sha256','external_execution_id','external_job_id','attempt_id','case_id','physical_contract_sha256']}|{'resource_requirements':resource} for c in cases]
# One-job batches enforce truth-before-next; bulk run_batch would launch all pending jobs before scientific acceptance.
runbatches=[]
for c,item in zip(cases,jobsout):
 bn='K6AL_FAST_R01_BATCH_001__EXEC__'+c['case_id'];man={'batch_name':bn,'description':'AL16 ideal-geometry FAST preparation ONLY; no solver authorization','jobs':[item],'science_entry_authorized':False,'science_batch_id':'K6AL_FAST_R01_BATCH_001','numerical_grade':'ML_TRAINING_GRADE'};mp='runner_manifests/'+c['case_id']+'.json';put(mp,man);runbatches.append({'case_id':c['case_id'],'batch_name':bn,'manifest':str(D/mp)})
put('AL16_FAST_PRODUCTION_MANIFEST.json',{'schema':'COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1','status':'PREPARED_AWAITING_INDEPENDENT_CHECKS_AND_SOLVER_AUTHORIZATION','science_batch_id':'K6AL_FAST_R01_BATCH_001','budget_proposal':{'id':'AL16_FAST_R01_BUDGET_PROPOSAL_V1','requested_max_entries':16,'authorized_entries':0,'source':'separate future AL16 authorization, never DIAG2','per_case_max_entries':1},'user_ideal_geometry_admission':True,'manufacturing_certified':False,'cases':cases,'runner_batches':runbatches,'execution_order':[c['case_id'] for c in cases],'canary_first_two':['K6AL_FAST_R01_G001','K6AL_FAST_R01_G009'],'stage_order':['G001','G009','G002','G003','G004','G005','G006','G007','G008','G010','G011','G012','G013','G014','G015','G016'],'runner_note':'Package manifest is science wrapper; submit only per-case runner_manifests after explicit authorization. Runner ignores science_entry_authorized flag: scientific consumer must enforce authority before submit/run.'})
put('PREPARATION_AUDIT.json',{'native_setup_sessions':1,'setup_saved_and_loaded':16,'native_run_calls':0,'new_entries':0,'replay':0,'fits':0,'sealed_response_access':0,'science_ledger_bytes_unchanged':ledger.read_bytes()==lb,'production_jobs_unchanged':len(jobs)==2,'production_entries_before':len(entries),'staged_unchanged':git('diff','--cached','--name-only')==baseline['staged'],'FSP_generation_elapsed_s':time.time()-t0,'source_template':{'path':str(template),'sha256':proof['candidate_fsp_sha256']},'reuse':'original6ps setup-only input; restore original3ps max; only radii percase; preserve both frozen source objects','no_manufacturing_limits_invented':True})
print('PREP_COMPLETE',D,flush=True)
