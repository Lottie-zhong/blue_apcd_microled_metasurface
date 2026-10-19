from pathlib import Path
import json,csv,sys,sqlite3,subprocess,time,importlib.util,hashlib,numpy as np
from scipy.spatial.distance import cdist
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';A=Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import ingest as I
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
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
for name,rr in [('old32',reg.old32),('dev_registered_including_failures',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for r in rr.values():add(r['ordered_D_nm'],name)
prev=read(B/'DEDUPLICATION_AUDIT.json')
for sn in prev['sources']:
 p=Path(sn)
 if p.is_file():walk(read(p),'prior_verified_metadata:'+sn);sources.append(sn)
for folder in [Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data'),Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 for p in folder.rglob('*.json'):
  if p.name.lower() not in ['manifest.json','source_manifest.json','queue_manifest.json','batch_manifest.json']:continue
  if any(w in str(p).lower() for w in ['sealed','confirmation','fixture','validation']):continue
  walk(read(p),'runtime_metadata:'+str(p));sources.append(str(p))
z=np.load(AL/'ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);x=z['D_nm'];assert len(x)==172
for g in x:add(g,'FAST172_computed')
walk(read(B/'AL16_FAST_PRODUCTION_MANIFEST.json'),'AL16_fixed_science_manifest');sources.append(str(B/'AL16_FAST_PRODUCTION_MANIFEST.json'))
con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(r) for r in con.execute('select * from jobs')];entries=[dict(r) for r in con.execute('select * from solver_entries')];con.close()
for j in jobs:
 if j.get('manifest_json'):walk(json.loads(j['manifest_json']),'canonical_job:'+str(j['id']))
add([120,160,165,175,160,195],'DIAG2_A1');add([210,115,175,115,180,125],'DIAG2_A2_reserved')
priority=np.load(AL/'ML_UPDATE/POOL_PRIORITY_UPDATE.npz',allow_pickle=False);pool=priority['ordered_D_nm'];unc=priority['uncalibrated_disagreement'];assert len(pool)==8192 and np.array_equal(pool,np.load(A/'PROVISIONAL_CANDIDATE_POOL.npz',allow_pickle=False)['ordered_D_nm'])
mask=np.array([tuple(g) not in protected for g in pool]);eligible=np.flatnonzero(mask);assert mask.sum()>=50
levels=np.arange(100,231,5);counts=np.array([[(x[:,k]==d).sum() for d in levels] for k in range(6)]);didx=((pool-100)//5).astype(int);occ=counts.copy();near=cdist(pool/130,x/130).min(1);base_near=near.copy();selected=[];reasons=[];roles=[];decision=[]
put('SELECTION_PREREGISTRATION.json',{'source_pool':str(A/'PROVISIONAL_CANDIDATE_POOL.npz'),'mix':{'coverage':30,'raw_disagreement':10,'stratified_random':10},'no_fits_or_predictions_recomputed':True,'uncertainty':'Reuse final172-model rawdisagreement, not calibrated uncertainty or predictedefficiency','coverage':'First two address D2zero-count130/185, choose jointmaximin within each; other28 globaljointdistance with mild six-axis occupancybalance bonus','balance_formula':'joint_nearest_distance*(1+0.1*mean(1/sqrt(1+axis_value_count))) ; counts include selected prospectivepoints','distance':'Euclidean orderedD/130nm, no sorting','diversity_sampling_target':.4,'diversity_is_not_manufacturing_threshold':True,'random':'seed20261018, ten deciles of meanD among eligible pool; maxdiverse fallback if needed','authorization':0})
def pick(i,role,why):
 i=int(i);assert mask[i] and i not in selected
 decision.append({'pool_index':i,'distance_to_172':float(base_near[i]),'distance_to_172_and_already_selected':float(near[i]),'raw_disagreement':float(unc[i])});selected.append(i);roles.append(role);reasons.append(why)
 for k in range(6):occ[k,didx[i,k]]+=1
 near[:]=np.minimum(near,np.linalg.norm((pool-pool[i])/130,axis=1));near[~mask]=-np.inf;near[selected]=-np.inf
for d in [130,185]:
 available=np.array([i for i in eligible if pool[i,1]==d]);assert len(available);pick(available[np.argmax(near[available])],'coverage',f'D2={d}nm zero-observation gap plus six-dimensional maximin')
for _ in range(28):
 sparsity=np.mean(np.stack([1/np.sqrt(1+occ[k,didx[:,k]]) for k in range(6)],axis=1),axis=1);score=near*(1+.1*sparsity);pick(np.argmax(score),'coverage','six-dimensional maximin with balanced six-axis sparse-value bonus')
for _ in range(10):
 available=np.array([i for i in eligible if i not in selected and near[i]>=.4]);assert len(available);pick(available[np.argmax(unc[available])],'disagreement','reused uncalibrated model disagreement, diversity constrained; not high-predicted-power')
meanD=pool.mean(1);bins=np.quantile(meanD[eligible],np.linspace(0,1,11));rng=np.random.default_rng(20261018)
for b in range(10):
 available=np.array([i for i in eligible if i not in selected and near[i]>=.4 and bins[b]<=meanD[i] and (meanD[i]<bins[b+1] or (b==9 and meanD[i]<=bins[b+1]))]);fallback=False
 if not len(available):available=np.array([i for i in eligible if i not in selected and near[i]>=.4]);fallback=True
 assert len(available);pick(rng.choice(available),'stratified_random',f'mean-diameter decile{b+1}/10 seeded exploration'+('; diverse-global fallback' if fallback else ''))
geom=pool[selected];assert len(set(map(tuple,geom)))==50 and not any(tuple(g) in protected for g in geom);assert np.all((geom>=100)&(geom<=230)&((geom-100)%5==0))
prospective=np.r_[x,geom];aftercounts=np.array([[(prospective[:,k]==d).sum() for d in levels] for k in range(6)]);pair=cdist(geom/130,geom/130);np.fill_diagonal(pair,np.inf);afterdist=cdist(pool/130,prospective/130).min(1);rem=np.array([i for i in eligible if i not in selected]);cov={'computed_now':172,'prospective_if50valid':222,'axis_levels_nm':levels,'axis_counts_172':counts,'axis_counts_prospective222':aftercounts,'axis_missing_172':[[int(d) for d,c in zip(levels,counts[k]) if not c] for k in range(6)],'axis_missing_prospective222':[[int(d) for d,c in zip(levels,aftercounts[k]) if not c] for k in range(6)],'selected_axis_counts':aftercounts-counts,'minimum_selected_pair_distance':float(pair.min()),'same_remaining_pool_mean_distance_172':float(base_near[rem].mean()),'same_remaining_pool_mean_distance_prospective222':float(afterdist[rem].mean()),'fullpool_quantiles_172':np.quantile(base_near,[0,.25,.5,.75,1]),'fullpool_quantiles_prospective222':np.quantile(afterdist,[0,.25,.5,.75,1]),'meaning':'Prospectivecoverageonly, no newtruth. MissingD2fill limited2forcedcases outof50; other28coverage balances6D.'};put('COVERAGE_AND_SPARSE_DIMENSIONS.json',cov)
put('DEDUPLICATION_AUDIT.json',{'all_prior_verified_metadata_refreshed':True,'protected_unique_geometries':len(protected),'source_paths':sorted(set(sources)),'canonical_jobs':jobs,'canonical_entries':entries,'pool8192_eligible_after_protection':int(mask.sum()),'selected50_unique':True,'selected_vs_protected_intersection':0,'sealed_response_access':0,'scope':'all verified history/protected/reserved geometry metadata plus refreshedknownruntimequeue/source manifests and canonicalV31DB; unregisteredexternalmanualwork cannot be exhaustively certified; refresh beforefutureauthorization','new_entries':0})
rows=[]
for rank,(i,g) in enumerate(zip(selected,geom),1):rows.append({'rank':rank,'case_id':f'K6AL_FAST_R02_G{rank:03d}','original_pool_index':int(i),**{f'D{k}_nm':int(v) for k,v in enumerate(g,1)},'role':roles[rank-1],'reason':reasons[rank-1],**{k:v for k,v in decision[rank-1].items() if k!='pool_index'}})
with (D/'AL50_SELECTED_GEOMETRIES.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
put('AL50_SELECTION.json',rows)
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
  case={'case_id':cid,'attempt_id':'attempt_001','external_execution_id':eid,'external_job_id':'coupling:'+cid,'ordered_D_nm':g.tolist(),'selection_role':row['role'],'selection_reason':row['reason'],'original_pool_index':row['original_pool_index'],'input_fsp':str(target),'source_fsp_sha256':sha,'physical_contract_sha256':contract['contract_sha256'],'budget_proposal_id':'AL50_FAST_R02_BUDGET_PROPOSAL_V1','maximum_entries':1,'entries_authorized':0,'solver_entered':False,'numerical_grade':'ML_TRAINING_GRADE','fidelity_role':'FAST_DATASET','strict_convergence':'NOT_CERTIFIED','science_output_directory':str(D/'science_outputs'/cid/'attempt_001'),'geometry_checks':checks,'readback':str(D/'checks'/f'{cid}.json')};cases.append(case)
  print('SETUP_SAVED',rank,cid,flush=True)
finally:fd.close()
put('AL50_CASES.json',cases);resource=read(read(B/'AL16_FAST_PRODUCTION_MANIFEST.json')['runner_batches'][0]['manifest'])['jobs'][0]['resource_requirements'];batches=[]
for c in cases:
 bn='K6AL_FAST_R02_BATCH_001__EXEC__'+c['case_id'];p='runner_manifests/'+c['case_id']+'.json';item={k:c[k] for k in ['input_fsp','source_fsp_sha256','external_execution_id','external_job_id','attempt_id','case_id','physical_contract_sha256']};item['resource_requirements']=resource;put(p,{'batch_name':bn,'description':'AL50 idealgeometry FAST preparation only, NOT_AUTHORIZED','jobs':[item],'science_entry_authorized':False,'science_batch_id':'K6AL_FAST_R02_BATCH_001','numerical_grade':'ML_TRAINING_GRADE'});batches.append({'case_id':c['case_id'],'batch_name':bn,'manifest':str(D/p)})
put('AL50_FAST_PRODUCTION_MANIFEST.json',{'schema':'COUPLING_AL50_FAST_PRODUCTION_PACKAGE_V1','status':'PREPARED_PENDING_OFFLINE_ACCEPTANCE','science_batch_id':'K6AL_FAST_R02_BATCH_001','budget_proposal':{'id':'AL50_FAST_R02_BUDGET_PROPOSAL_V1','maximum_requested_entries':50,'authorized_entries':0,'per_case_max':1,'DIAG2_budget_allocated':0,'replay':False},'cases':cases,'runner_batches':batches,'execution_order':[c['case_id'] for c in cases],'interface_note':'Sciencewrapper; only percase Runner manifests after separatehumanapproval. False scienceflag not enforced byRunner; consumer mustenforceauthority.','preferred_window':'Asia/Shanghai21:00–next10:00 preferredonly, no forcedstop','checkpoint_new_valid_geometry_targets':[16,32,50],'invalid_policy':'enteredfailuresconsume; no automaticreplacement to reach50valid','actual_manufacturing':'UNRESOLVED'})
extract=(B/'al16_extract_native_v1.py').read_text(encoding='utf-8').replace('APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1','APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1').replace('AL16_FAST_PRODUCTION_MANIFEST.json','AL50_FAST_PRODUCTION_MANIFEST.json').replace('AL16_FAST_R01','AL50_FAST_R02').replace('AL16_FAST_DEVELOPMENT','AL50_FAST_DEVELOPMENT');(D/'al50_extract_native_v1.py').write_text(extract,encoding='utf-8')
put('PREPARATION_AUDIT.json',{'FSP_saved_reloaded':50,'cases_unique':50,'selection_mix':{'coverage':30,'disagreement':10,'stratified_random':10},'new_FDTD':0,'new_entries':0,'new_ML_fits':0,'old_DIAG2_ledger_bytes_unchanged':oldledger.read_bytes()==oldbytes,'AL16_ledger_bytes_unchanged':(AL/'AL16_SCIENCE_LEDGER.json').read_bytes()==albytes,'setup_elapsed_s':time.time()-start,'physics_sha_canonical_rule':'originalI._canon unchanged','template_sha':proof['candidate_fsp_sha256'],'no_runner_changes':True})
print('AL50_PREP_COMPLETE',D)
