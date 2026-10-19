from pathlib import Path
import json,csv,sys,sqlite3,subprocess,time,importlib.util,hashlib,numpy as np
from scipy.spatial.distance import cdist
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest as I
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')

selection=read(D/'AL50_SELECTION.json');geom=np.array([r['D_nm'] for r in selection]);rows=selection;roles=[r['role'] for r in rows];reasons=[r['reason'] for r in rows]
meta=read(D/'DEDUPLICATION_AUDIT.json');jobs=meta['canonical_jobs'];entries=meta['canonical_entries'];assert len(geom)==50
# Reuse validated AL16 setup/readback implementation unchanged; new taskowned inputs only.
contract=read(B/'FAST_FROZEN_PHYSICS_CONTRACT.json');assert I._canon(contract['contract'])==contract['contract_sha256'];put('FAST_FROZEN_PHYSICS_CONTRACT.json',contract)
proof=read(Q/'APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1/A1_SETUP_LOAD_PROOF.json');template=Path(proof['candidate_fsp_path']);assert I.sha256_file(template)==proof['candidate_fsp_sha256']
oldledger=Q/'APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING/DIAG2_SCIENCE_LEDGER.json';oldbytes=oldledger.read_bytes();albytes=(AL/'AL16_SCIENCE_LEDGER.json').read_bytes()
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python');import lumapi
spec=importlib.util.spec_from_file_location('existing_builder_al50',R/'scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
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

cases=[];fd=lumapi.FDTD(hide=True);start=time.time()
try:
 fd.load(str(template));assert int(fd.layoutmode())==1;base=snap(fd);put('TEMPLATE_BASE_READBACK.json',base)
 for rank,(row,g) in enumerate(zip(rows,geom),1):
  cid=row['case_id'];eid='coupling:'+cid+'/attempt_001';assert not any(j['case_id']==cid or j['external_execution_id']==eid for j in jobs)
  target=D/'inputs'/cid/'attempt_001/pre.fsp';assert not target.exists();target.parent.mkdir(parents=True)
  b.validate_geometry(g.tolist());fd.load(str(template));assert int(fd.layoutmode())==1;fd.setnamed('FDTD','simulation time',3e-12)
  for k,d in enumerate(g,1):fd.setnamed(f'NP_D{k}','radius',float(d)*.5e-9)
  fd.save(str(target));fd.load(str(target));actual=snap(fd);expected=json.loads(json.dumps(base));expected['FDTD']['simulation time']=3e-12
  for k,d in enumerate(g,1):expected[f'NP_D{k}']['radius']=float(d)*.5e-9
  assert actual==expected and actual['FDTD']['auto shutoff min']==1e-6
  sha=I.sha256_file(target);gaps=290-(g+np.roll(g,-1))/2;ygap=290-g;assert (gaps>0).all() and (ygap>0).all()
  checks={'ideal_geometry_admission':'PASS_CURRENT_USER_TASK','actual_manufacturing':'UNRESOLVED','ordered_D_nm':g.tolist(),'centers_x_nm':b.pillar_centers_nm(290,6),'periodic_x_gaps_nm':gaps.tolist(),'periodic_y_gaps_nm':ygap.tolist(),'half_cell_margin_nm':(ygap/2).tolist(),'height_nm':500,'aspect_ratio_H_D':(500/g).tolist(),'no_manufacturing_limits_invented':True,'diameter_range_step_pass':True,'all_other_audited_properties_same_as_template':True}
  put('checks/'+cid+'.json',dict(case_id=cid,fresh_saved_load_readback=actual,geometry=checks,source_fsp_sha256=sha,solver_run_called=False))
  case={'case_id':cid,'attempt_id':'attempt_001','external_execution_id':eid,'external_job_id':'coupling:'+cid,'ordered_D_nm':g.tolist(),'selection_role':row['role'],'selection_reason':row['reason'],'original_pool_index':row['original_pool_index'],'input_fsp':str(target),'source_fsp_sha256':sha,'physical_contract_sha256':contract['contract_sha256'],'budget_proposal_id':'AL50_COMPLEX_R03_BUDGET_PROPOSAL_V1','maximum_entries':1,'entries_authorized':1,'solver_entered':False,'numerical_grade':'ML_TRAINING_GRADE','fidelity_role':'FAST_DATASET','strict_convergence':'NOT_CERTIFIED','science_output_directory':str(D/'science_outputs'/cid/'attempt_001'),'geometry_checks':checks,'readback':str(D/'checks'/f'{cid}.json')};cases.append(case)
  print('SETUP_SAVED',rank,cid,flush=True)
finally:fd.close()
put('AL50_CASES.json',cases);resource=read(read(B/'AL16_FAST_PRODUCTION_MANIFEST.json')['runner_batches'][0]['manifest'])['jobs'][0]['resource_requirements'];batches=[]
for c in cases:
 bn='K6AL_COMPLEX_R03_BATCH_001__EXEC__'+c['case_id'];p='runner_manifests/'+c['case_id']+'.json';item={k:c[k] for k in ['input_fsp','source_fsp_sha256','external_execution_id','external_job_id','attempt_id','case_id','physical_contract_sha256']};item['resource_requirements']=resource;put(p,{'batch_name':bn,'description':'AL50 complex-aware authorized subject to all hard gates','jobs':[item],'science_entry_authorized':True,'science_batch_id':'K6AL_COMPLEX_R03_BATCH_001','numerical_grade':'ML_TRAINING_GRADE'});batches.append({'case_id':c['case_id'],'batch_name':bn,'manifest':str(D/p)})
put('AL50_COMPLEX_PRODUCTION_MANIFEST.json',{'schema':'COUPLING_AL50_FAST_PRODUCTION_PACKAGE_V1','status':'PREPARED_PENDING_OFFLINE_ACCEPTANCE','science_batch_id':'K6AL_COMPLEX_R03_BATCH_001','budget_proposal':{'id':'AL50_COMPLEX_R03_BUDGET_PROPOSAL_V1','maximum_requested_entries':50,'authorized_entries':50,'per_case_max':1,'DIAG2_budget_allocated':0,'replay':False},'cases':cases,'runner_batches':batches,'execution_order':[c['case_id'] for c in cases],'interface_note':'Sciencewrapper; only percase Runner manifests after separatehumanapproval. False scienceflag not enforced byRunner; consumer mustenforceauthority.','preferred_window':'Asia/Shanghai21:00–next10:00 preferredonly, no forcedstop','checkpoint_new_valid_geometry_targets':[16,32,50],'invalid_policy':'enteredfailuresconsume; no automaticreplacement to reach50valid','actual_manufacturing':'UNRESOLVED'})
extract=(B/'al16_extract_native_v1.py').read_text(encoding='utf-8').replace('APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1','APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1').replace('AL16_FAST_PRODUCTION_MANIFEST.json','AL50_COMPLEX_PRODUCTION_MANIFEST.json').replace('AL16_FAST_R01','AL50_COMPLEX_R03').replace('AL16_FAST_DEVELOPMENT','AL50_FAST_DEVELOPMENT');(D/'al50_extract_native_v1.py').write_text(extract,encoding='utf-8')
put('PREPARATION_AUDIT.json',{'FSP_saved_reloaded':50,'cases_unique':50,'selection_mix':{'coverage':30,'disagreement':10,'stratified_random':10},'new_FDTD':0,'new_entries':0,'new_ML_fits':0,'old_DIAG2_ledger_bytes_unchanged':oldledger.read_bytes()==oldbytes,'AL16_ledger_bytes_unchanged':(AL/'AL16_SCIENCE_LEDGER.json').read_bytes()==albytes,'setup_elapsed_s':time.time()-start,'physics_sha_canonical_rule':'originalI._canon unchanged','template_sha':proof['candidate_fsp_sha256'],'no_runner_changes':True})
print('AL50_PREP_COMPLETE',D)
