from pathlib import Path
import json,csv,sqlite3,sys,copy,importlib.util,time,numpy as np
from scipy.spatial.distance import cdist
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';V=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';D=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import ingest as I
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
v1=read(V/'AL50_FAST_PRODUCTION_MANIFEST.json');oldcases=v1['cases'];oldmap={c['case_id']:c for c in oldcases};z=np.load(AL/'ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);x=z['D_nm'];hist={str(cid):tuple(map(int,g)) for cid,g in zip(z['case_ids'],x)};geomids={g:cid for cid,g in hist.items()};anchor1='K6GDP2_DEV_G059';anchor2='K6V1_S31';assert hist[anchor1][2]==170
new=[]
for k,(axis,sgn) in enumerate([(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(1,-1),(2,-1)],1):
 g=list(hist[anchor1]);g[axis]+=sgn*5;new.append({'case_id':f'K6AL_FAST_R02V2_L{k:03d}','ordered_D_nm':g,'selection_role':'single_pillar_local','selection_reason':f'{anchor1} D{axis+1} {sgn*5:+d}nm; D3sparseanchor','local_anchor':anchor1,'delta_nm':[sgn*5 if j==axis else 0 for j in range(6)]})
for k,(aid,axes) in enumerate([(anchor1,(1,2)),(anchor2,(5,0))],1):
 g=list(hist[aid]);delta=[0]*6
 for a in axes:g[a]+=5;delta[a]=5
 new.append({'case_id':f'K6AL_FAST_R02V2_I{k:03d}','ordered_D_nm':g,'selection_role':'two_pillar_interaction','selection_reason':f'{aid} interactionD{axes[0]+1}-D{axes[1]+1} +5nm/+5nm','local_anchor':aid,'delta_nm':delta})
protected={};sourcepaths=[]
def add(g,why):
 try:
  if len(g)==6 and all(isinstance(a,(int,float,np.number)) and float(a).is_integer() and 0<float(a)<1000 for a in g):protected.setdefault(tuple(map(int,g)),set()).add(why)
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
for role,rr in [('old32',reg.old32),('dev_including_failed',reg.development),('sealed_geometry_metadata_only',reg.confirmation)]:
 for r in rr.values():add(r['ordered_D_nm'],role)
for cid,g in hist.items():add(g,'FAST172:'+cid)
for sn in read(V/'DEDUPLICATION_AUDIT.json')['source_paths']:
 p=Path(sn)
 if p.is_file():walk(read(p),'prior_verified_metadata:'+sn);sourcepaths.append(sn)
for root in [Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\v3_data'),Path(r'D:\apcd_runtime\gpu_production_runner_v1'),Path(r'D:\apcd_runtime\coupling_v3_time_diag2_v1')]:
 for p in root.rglob('*.json'):
  if p.name.lower() not in ['manifest.json','source_manifest.json','queue_manifest.json','batch_manifest.json'] or any(w in str(p).lower() for w in ['sealed','confirmation','fixture','validation']):continue
  walk(read(p),'current_runtime_metadata:'+str(p));sourcepaths.append(str(p))
# ExistingV1candidateIDs are reserved but not consumed; newgeometries cannot collide with even superseded candidates.
for c in oldcases:add(c['ordered_D_nm'],'V1_reserved:'+c['case_id'])
c=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;jobs=[dict(r) for r in c.execute('select * from jobs')];entries=[dict(r) for r in c.execute('select * from solver_entries')];c.close()
for j in jobs:
 if j.get('manifest_json'):walk(json.loads(j['manifest_json']),'canonical_job:'+str(j['id']))
for c in new:assert tuple(c['ordered_D_nm']) not in protected,(c,protected.get(tuple(c['ordered_D_nm'])));assert all(100<=d<=230 and d%5==0 for d in c['ordered_D_nm'])
assert len({tuple(c['ordered_D_nm']) for c in new})==10
# Keep all30coverage, first8disagreement inclD2=130, andD2=185 randomG050. Optimize the second retainedrandom against jointcoverage loss.
cover=[c for c in oldcases if c['selection_role']=='coverage'];disagree=[c for c in oldcases if c['selection_role']=='disagreement'][:8];randoms=[c for c in oldcases if c['selection_role']=='stratified_random'];mandatory=oldmap['K6AL_FAST_R02_G050'];assert mandatory['ordered_D_nm'][1]==185
pool=np.load(Q/'APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1/PROVISIONAL_CANDIDATE_POOL.npz',allow_pickle=False)['ordered_D_nm'];basegeoms=np.array([*x,*[c['ordered_D_nm'] for c in cover+disagree+[mandatory]+new]],float);base_dist=cdist(pool/130,basegeoms/130).min(1);scores=[]
for c in randoms:
 if c['case_id']==mandatory['case_id']:continue
 score=float(np.minimum(base_dist,np.linalg.norm((pool-np.array(c['ordered_D_nm']))/130,axis=1)).mean());scores.append((score,c['case_id']))
best=min(scores)[1];retained=cover+disagree+[oldmap[best],mandatory];retained=sorted(retained,key=lambda c:c['case_id']);removed=[c for c in oldcases if c['case_id'] not in {r['case_id'] for r in retained}];assert len(retained)==40 and len(removed)==10
assert all(c in retained for c in oldcases if c['ordered_D_nm'][1] in [130,185])
put('INCREMENTAL_SELECTION_DECISION.json',{'retained':40,'replaced':10,'mix':{'global_coverage':30,'disagreement':8,'stratified_random':2,'single_pillar_local':8,'two_pillar_interaction':2},'random_keep':best,'random_coverage_scores':scores,'D2_missing_bin_cases_all_retained':True,'historical_local_pair_reuse':11,'interaction_anchors':[anchor1,anchor2],'no_fit':True})
put('SUPERSEDED_ZERO_ENTRY.json',[{'case_id':c['case_id'],'external_execution_id':c['external_execution_id'],'input_fsp':c['input_fsp'],'source_fsp_sha256':c['source_fsp_sha256'],'status':'SUPERSEDED_ZERO_ENTRY','reason':'V2localexperimentallocation; V1archiveimmutable','entered_count':0,'new_execution_id_bound_to_old_FSP':False} for c in removed]);put('V1_ARCHIVE_REFERENCE.json',{'path':str(V),'status':'IMMUTABLE_V1_ARCHIVE_RETAINED_IN_PLACE','manifest_bytes':(V/'AL50_FAST_PRODUCTION_MANIFEST.json').stat().st_size,'all_50_original_inputs_retained':all(Path(c['input_fsp']).is_file() for c in oldcases)})
# Reuse existingprops/snapshot definitions andonlygenerate10newFSP. Never alterretainedorremovedinputs.
proof=read(Q/'APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1/A1_SETUP_LOAD_PROOF.json');template=Path(proof['candidate_fsp_path']);assert I.sha256_file(template)==proof['candidate_fsp_sha256'];sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python');import lumapi
sp=importlib.util.spec_from_file_location('existing_builder_v2',R/'scripts/coupling_ml/build_pw_k6_5nm_full_period_prefsp_v1.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
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

fd=lumapi.FDTD(hide=True)
try:
 fd.load(str(template));assert int(fd.layoutmode())==1;baseline=snap(fd)
 for c in new:
  cid=c['case_id'];g=c['ordered_D_nm'];p=D/'inputs'/cid/'attempt_001/pre.fsp';assert not p.exists();p.parent.mkdir(parents=True);b.validate_geometry(g);fd.load(str(template));fd.setnamed('FDTD','simulation time',3e-12)
  for k,d in enumerate(g,1):fd.setnamed(f'NP_D{k}','radius',d*.5e-9)
  fd.save(str(p));fd.load(str(p));actual=snap(fd);expect=copy.deepcopy(baseline);expect['FDTD']['simulation time']=3e-12
  for k,d in enumerate(g,1):expect[f'NP_D{k}']['radius']=d*.5e-9
  assert actual==expect
  sha=I.sha256_file(p);c.update(attempt_id='attempt_001',external_execution_id='coupling:'+cid+'/attempt_001',external_job_id='coupling:'+cid,input_fsp=str(p),source_fsp_sha256=sha,physical_contract_sha256=oldcases[0]['physical_contract_sha256'],budget_proposal_id='AL50_FAST_R02_BUDGET_PROPOSAL_V1',maximum_entries=1,entries_authorized=0,solver_entered=False,numerical_grade='ML_TRAINING_GRADE',fidelity_role='FAST_DATASET',strict_convergence='NOT_CERTIFIED',science_output_directory=str(D/'science_outputs'/cid/'attempt_001'),readback=str(D/'checks'/f'{cid}.json'))
  put('checks/'+cid+'.json',{'case_id':cid,'fresh_saved_load_readback':actual,'only_changes_from_template':'3psmaximumandorderedradii','sha256':sha,'run_called':False});print('NEW_SETUP',cid,flush=True)
finally:fd.close()
# Reuse retainedmanifests verbatim; onlynew10getnewgenericRunnerbatches.
oldbatches={c['case_id']:c for c in v1['runner_batches']};batches=[oldbatches[c['case_id']] for c in retained];resource=read(batches[0]['manifest'])['jobs'][0]['resource_requirements']
for c in new:
 bn='K6AL_FAST_R02V2_BATCH_001__EXEC__'+c['case_id'];path='runner_manifests/'+c['case_id']+'.json';job={k:c[k] for k in ['input_fsp','source_fsp_sha256','external_execution_id','external_job_id','attempt_id','case_id','physical_contract_sha256']};job['resource_requirements']=resource;put(path,{'batch_name':bn,'description':'AL50V2incremental localglobal preparationONLY','jobs':[job],'science_entry_authorized':False,'science_batch_id':'K6AL_FAST_R02_BATCH_001','numerical_grade':'ML_TRAINING_GRADE'});batches.append({'case_id':c['case_id'],'batch_name':bn,'manifest':str(D/path)})
cases=retained+new;assert len(cases)==50 and len({tuple(c['ordered_D_nm']) for c in cases})==50
for c in cases:assert not any(j['external_execution_id']==c['external_execution_id'] or j['case_id']==c['case_id'] for j in jobs)
v2=copy.deepcopy(v1);v2.update(schema='COUPLING_AL50_LOCAL_GLOBAL_V2',status='PREPARED_PENDING_OFFLINE_CHECKS',cases=cases,runner_batches=batches,execution_order=[c['case_id'] for c in cases],version='V2',previous_manifest=str(V/'AL50_FAST_PRODUCTION_MANIFEST.json'),superseded_zero_entry=[c['case_id'] for c in removed],retained40=True,new10=True,extractor=str(D/'al50_v2_extract_native.py'),acceptance_contract=str(D/'LABEL_EXTRACTION_AND_ACCEPTANCE.json'),staged_model_plan=str(D/'LOCAL_FAMILY_EVALUATION_PLAN.json'));v2['budget_proposal']['authorized_entries']=0;put('AL50_FAST_PRODUCTION_MANIFEST_V2.json',v2)
# Tinyconsumerpath adaptation only; retainedcase outputs continueoriginalpaths viaV2case records.
s=(V/'al50_extract_native_v1.py').read_text(encoding='utf-8').replace('APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1','APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2').replace('AL50_FAST_PRODUCTION_MANIFEST.json','AL50_FAST_PRODUCTION_MANIFEST_V2.json');(D/'al50_v2_extract_native.py').write_text(s,encoding='utf-8')
for n in ['FAST_FROZEN_PHYSICS_CONTRACT.json','FAST_NUMERICAL_CONTRACT_V1.json','SCHEDULING_POLICY_REFERENCE.json']:(D/n).write_bytes((V/n).read_bytes())
acc=read(V/'LABEL_EXTRACTION_AND_ACCEPTANCE.json');acc['extractor']=str(D/'al50_v2_extract_native.py');acc['command_after_completed_job']=['N:\\anaconda_envs\\RCP_LCP\\python.exe',str(D/'al50_v2_extract_native.py'),'--case','<exact V2 activecase_id>'];put('LABEL_EXTRACTION_AND_ACCEPTANCE.json',acc)
# Completepairgraph includeshistoricalvalidandprospectivecases, traceeachendpointtolabel/input.
inv=read(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json');histmeta={c['case_id']:c for c in inv['cases']};almeta={c['case_id']:c for c in read(AL/'NATIVE_ARTIFACT_INDEX.json')};nodes={};active={c['case_id']:c for c in cases}
for cid,g in hist.items():
 label=almeta[cid]['labels'] if cid in almeta else (histmeta[cid]['artifacts'].get('label',{}).get('path') or histmeta[cid]['artifacts'].get('legacy_dataset',{}).get('path'))
 nodes[g]={'case_id':cid,'labels_valid':True,'labels_path':label or 'see156inventoryoriginalstate/H1authority','input_fsp':(histmeta[cid]['native_files'][0]['path'] if cid in histmeta else almeta[cid]['native_fsp'])}
for c in cases:nodes[tuple(c['ordered_D_nm'])]={'case_id':c['case_id'],'labels_valid':False,'labels_path':str(Path(c['science_output_directory'])/'labels_609d.npz'),'input_fsp':c['input_fsp']}
edges=[]
for g,n in nodes.items():
 for k in range(6):
  t=list(g);t[k]+=5;t=tuple(t)
  if t in nodes:
   n2=nodes[t];edges.append({'pair_id':f'PAIR_{len(edges)+1:03d}','case_low':n['case_id'],'case_high':n2['case_id'],'axis':k+1,'delta_nm':5,'labels_status':'VALID_EXISTING' if n['labels_valid'] and n2['labels_valid'] else 'PLANNED_PENDING_SOLVER','labels_low':n['labels_path'],'labels_high':n2['labels_path'],'fsp_low':n['input_fsp'],'fsp_high':n2['input_fsp']})
with (D/'AL50_LOCAL_PAIR_GRAPH.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(edges[0]));w.writeheader();w.writerows(edges)
groups=[]
for aid,(i,j) in [(anchor1,(1,2)),(anchor2,(5,0))]:
 coords=[]
 for a,bb in [(0,0),(1,0),(0,1),(1,1)]:
  g=list(hist[aid]);g[i]+=a*5;g[j]+=bb*5;coords.append(tuple(g))
 assert all(g in nodes for g in coords)
 ns=[nodes[g] for g in coords];groups.append({'group_id':f'INTERACTION_{len(groups)+1:02d}','anchor':aid,'axis_i':i+1,'axis_j':j+1,'delta_i_nm':5,'delta_j_nm':5,**{k:n['case_id'] for k,n in zip(['D','D_i','D_j','D_ij'],ns)},'design_complete':True,'truth_complete':all(n['labels_valid'] for n in ns),'existing_valid_corners':sum(n['labels_valid'] for n in ns),'status':'DESIGN_COMPLETE_TRUTH_PENDING','interaction_formula':'Y_ij-Y_i-Y_j+Y_D'})
with (D/'AL50_INTERACTION_GROUPS.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(groups[0]));w.writeheader();w.writerows(groups)
# 5nmconnectedcomponentfamilies for leakageguards.
parent={n['case_id']:n['case_id'] for n in nodes.values()}
def find(a):
 while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
 return a
for e in edges:
 a,b=find(e['case_low']),find(e['case_high']);parent[b]=a
families={}
for cid in parent:families.setdefault(find(cid),[]).append(cid)
families=[v for v in families.values() if len(v)>1];put('LOCAL_FAMILY_COMPONENTS.json',families)
oldfolds=read(AL/'ML_UPDATE/FOLDS.json');s31touch=[f['fold'] for f in oldfolds if any(cid in next(v for v in families if anchor2 in v) for cid in f['heldout_old_ids'])];anchor1fold=next(f['fold'] for f in oldfolds if anchor1 in f['heldout_old_ids'])
put('LOCAL_FAMILY_EVALUATION_PLAN.json',{'new_fits_now':0,'original124heldout_IDs_preserved':True,'original_metric_definitions_preserved':True,'tracks':{'legacy':'Reportunchanged124heldoutprotocol forcontinuity; not claimlocalfamilyindependence ofhistoricS31family','strict_family_guard':'Keep124heldoutIDs, purge ALLtrainingmembers ofanyconnectedfamily touchingvalidation(includingS31old32anchor); purgedold32never movedintoevaluation. Futurematched172baseline mustuseSAMEpurgingbeforeV2comparison, so oldpublishedbeforeisnotmixedwithguardedafter.','new_local_family':f'{anchor1} andall9newfamilymembers assignfold{anchor1fold}; entirefamilyheldouttogether','old32_boundary_family':'S31family old32anchor remainsnot-test; physicalinteractioncanbecomputedoncealllabelsvalid; doNOTclaimheldoutlocalmodelskillforthisfamily. UseG059familyforstrictpairedpredictionmetrics; familyguardedglobaloldarmmetricsseparate.'},'existingS31legacy_family_touches_folds':s31touch,'metrics':['localdifferenceMAE:meanabs((Yhat_neighbor-Yhat_anchor)-(Y_neighbor-Y_anchor))','signaccuracy:sign(delta_prediction)==sign(delta_truth),exacttiesseparate; do notinventnoise-floor','localrankingagreement pairwiseSpearman/wins onheldoutfamily, tied/constantundefined','nonadditivityI=Yij-Yi-Yj+YD forP+,eta,Pscale all21lambda; absolutevaluesandreferencepowers; relativeinteractionundefinednearzero','modelinteractionerror abs(Ihat-I) only ifentireexperimentalgroupeligibleheldout'],'leakage_unit':'connectedgeometryfamily, notcaseIDonly; no crossfidelity/geometricduplicate splits','sample_limit':'2designgroups/2anchors, onlyoneeligibleanchorforstrictlocalpredictivegeneralization; noclaimlocalguaranteedimprovement','stage_checkpoints_new_valid':[16,32,50],'contract_immutable_if_model_no_gain':True})
v1g=np.array([c['ordered_D_nm'] for c in oldcases]);v2g=np.array([c['ordered_D_nm'] for c in cases]);d1=cdist(pool/130,np.r_[x,v1g]/130).min(1);d2=cdist(pool/130,np.r_[x,v2g]/130).min(1);remaining=[k for k,g in enumerate(pool) if tuple(g) not in set(map(tuple,np.r_[x,v1g,v2g]))];levels=list(range(100,231,5));put('COVERAGE_V1_V2_COMPARISON.json',{'172G_unchanged':True,'same_remaining_pool_mean_V1':float(d1[remaining].mean()),'same_remaining_pool_mean_V2':float(d2[remaining].mean()),'relative_coverage_distance_increase':float(d2[remaining].mean()/d1[remaining].mean()-1),'fullpool_max_V1':float(d1.max()),'fullpool_max_V2':float(d2.max()),'D2_130_185_count_172_plus_V1':[int((np.r_[x,v1g][:,1]==v).sum()) for v in [130,185]],'D2_130_185_count_172_plus_V2':[int((np.r_[x,v2g][:,1]==v).sum()) for v in [130,185]],'D3_170_count_172_plus_V1':int((np.r_[x,v1g][:,2]==170).sum()),'D3_170_count_172_plus_V2':int((np.r_[x,v2g][:,2]==170).sum()),'axis_unique_V1':[len(np.unique(np.r_[x,v1g][:,k])) for k in range(6)],'axis_unique_V2':[len(np.unique(np.r_[x,v2g][:,k])) for k in range(6)],'new_local_points_outside_original8192_allowed':'Derived5nmperturbationwithinexplicituserlegalrange, sourceidentified aslocalderived ratherthanoriginalpoolmember','new_valid_pairs_now':sum(e['labels_status']=='VALID_EXISTING' for e in edges),'planned_or_mixed_pairs':sum(e['labels_status']!='VALID_EXISTING' for e in edges),'design_complete_groups':len(groups),'truth_complete_groups_now':sum(g['truth_complete'] for g in groups),'newanchors_strictmodeltesting':1})
put('DEDUPLICATION_AUDIT.json',{'protected_unique_count_including_allV1reserved':len(protected),'source_paths':sorted(set(sourcepaths)),'canonical_jobs':jobs,'canonical_entries':entries,'retained40_exactoriginalidentity':True,'replaced10_noREALentry':True,'new10_vs_allprotected_conflicts':0,'active50_unique':True,'active50_vs_hist172_conflicts':0,'sealed_response_access':0,'source_notes':'allpreviouslyverifiedhistoryrefreshed,canonicalV31+knownruntimequeue; freshcheckneededbeforefutureadmission','new_entries':0})
put('LOCAL_DESIGN_SUMMARY.json',{'retained':40,'replaced':10,'existing_valid_pairs':sum(e['labels_status']=='VALID_EXISTING' for e in edges),'new_pending_pairs':sum(e['labels_status']!='VALID_EXISTING' for e in edges),'total_pair_graph_edges':len(edges),'design_complete_groups':len(groups),'truth_complete_groups':sum(g['truth_complete'] for g in groups),'group_existing_corners':[g['existing_valid_corners'] for g in groups],'new_FDTD':0,'AL50_authorized':0})
print('V2_DONE',json.dumps(read(D/'LOCAL_DESIGN_SUMMARY.json')));print('COVERAGE',json.dumps(read(D/'COVERAGE_V1_V2_COMPARISON.json')))
