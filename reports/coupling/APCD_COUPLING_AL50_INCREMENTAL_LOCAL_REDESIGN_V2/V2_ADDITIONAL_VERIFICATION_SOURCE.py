from pathlib import Path
import json,csv,hashlib,itertools,sqlite3,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';V=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';D=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
v1=read(V/'AL50_FAST_PRODUCTION_MANIFEST.json');v2=read(D/'AL50_FAST_PRODUCTION_MANIFEST_V2.json');o={c['case_id']:c for c in v1['cases']};n={c['case_id']:c for c in v2['cases']};keep=set(o)&set(n);new=set(n)-set(o);gone=set(o)-set(n);tests=[]
for cid in keep:
 for key in ['case_id','attempt_id','input_fsp','source_fsp_sha256','external_execution_id','external_job_id','physical_contract_sha256']:assert n[cid][key]==o[cid][key]
assert len(keep)==40 and len(new)==len(gone)==10;tests.append({'test':'40retained_identity_FSP_SHA_execution_exact','pass':True})
for cid in gone:assert hashlib.sha256(Path(o[cid]['input_fsp']).read_bytes()).hexdigest()==o[cid]['source_fsp_sha256']
tests.append({'test':'10superseded_inputs_retained_not_overwritten','pass':True})
assert all(c['case_id'] in keep for c in v1['cases'] if c['selection_role']=='coverage' or c['ordered_D_nm'][1] in [130,185]);tests.append({'test':'all30coverage_andD2rare_cases_retained','pass':True})
assert not {n[cid]['external_execution_id'] for cid in new}&{c['external_execution_id'] for c in v1['cases']};assert not {n[cid]['source_fsp_sha256'] for cid in new}&{c['source_fsp_sha256'] for c in v1['cases']};tests.append({'test':'new10independent_execution_and_inputsha','pass':True})
z=np.load(AL/'ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);hist={str(cid):tuple(map(int,g)) for cid,g in zip(z['case_ids'],z['D_nm'])};geom={**hist,**{cid:tuple(c['ordered_D_nm']) for cid,c in n.items()}};idx={str(cid):i for i,cid in enumerate(z['case_ids'])};edges=list(csv.DictReader((D/'AL50_LOCAL_PAIR_GRAPH.csv').open(encoding='utf-8')));groups=list(csv.DictReader((D/'AL50_INTERACTION_GROUPS.csv').open(encoding='utf-8')));nodes=[];oldinv={c['case_id']:c for c in read(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json')['cases']};almeta={c['case_id']:c for c in read(AL/'NATIVE_ARTIFACT_INDEX.json')}
for cid,g in geom.items():
 if cid in hist:
  if cid in almeta:fs=almeta[cid]['native_fsp'];sha=almeta[cid]['native_fsp_sha256']
  else:fs=oldinv[cid]['native_files'][0]['path'];sha=oldinv[cid]['native_files'][0]['sha256']
  nodes.append({'case_id':cid,'ordered_D_nm':g,'truth_status':'LABELS_VALID_EXISTING','target_cache':str(AL/'ML_UPDATE/FAST_DATASET_172G.npz'),'target_cache_case_id':cid,'frozen609D_source_inventory':str(Q/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json') if cid in oldinv else almeta[cid]['labels'],'native_fsp':fs,'native_fsp_sha256':sha})
 else:nodes.append({'case_id':cid,'ordered_D_nm':g,'truth_status':'NOT_RUN','input_fsp':n[cid]['input_fsp'],'input_sha256':n[cid]['source_fsp_sha256'],'future_labels':str(Path(n[cid]['science_output_directory'])/'labels_609d.npz')})
put('LOCAL_GEOMETRY_NODE_INDEX.json',nodes)
existing_changes=[]
for e in edges:
 a=np.array(geom[e['case_low']]);b=np.array(geom[e['case_high']]);d=b-a;assert np.count_nonzero(d)==1 and d[int(e['axis'])-1]==5
 e['ordered_D_low_nm']=json.dumps(a.tolist());e['ordered_D_high_nm']=json.dumps(b.tolist())
 if e['labels_status']=='VALID_EXISTING':
  assert e['case_low'] in idx and e['case_high'] in idx and Path(e['labels_low']).is_file() and Path(e['labels_high']).is_file()
  i,j=idx[e['case_low']],idx[e['case_high']];existing_changes.append({'pair_id':e['pair_id'],'axis':int(e['axis']),'case_low':e['case_low'],'case_high':e['case_high'],'Pplus1_delta_21':z['P_plus1_H2'][j]-z['P_plus1_H2'][i],'eta_delta_21':z['eta'][j]-z['eta'][i],'Pscale_delta_21':z['P_scale'][j]-z['P_scale'][i],'meaning':'Observed fullintegratedHF labeldifferences, not predictivevalidation or isolatedpillaraddition'})
with (D/'AL50_LOCAL_PAIR_GRAPH.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(edges[0]));w.writeheader();w.writerows(edges)
put('EXISTING_VALID_PAIR_DIFFERENCES.json',existing_changes);assert len(existing_changes)==11 and len(edges)==23;tests.append({'test':'all23edges_exact5nm_existing11labels_traced','pass':True})
for g in groups:
 base=np.array(geom[g['D']]);di=np.array(geom[g['D_i']]);dj=np.array(geom[g['D_j']]);ij=np.array(geom[g['D_ij']]);assert np.array_equal(ij-base,(di-base)+(dj-base)) and np.count_nonzero(di-base)==np.count_nonzero(dj-base)==1 and int(g['axis_i'])!=int(g['axis_j']);assert g['truth_complete']=='False'
assert len(groups)==2 and len({g['anchor'] for g in groups})==2;tests.append({'test':'two_exact_fourcorner_designs_twoanchors_no_false_truthcomplete','pass':True})
# Exhaustivepositive5nmrectangle enumeration validates actual design count.
gset=set(geom.values());quad=[]
for g in gset:
 for i,j in itertools.combinations(range(6),2):
  corners=[]
  for a,b in [(0,0),(1,0),(0,1),(1,1)]:
   t=list(g);t[i]+=a*5;t[j]+=b*5;corners.append(tuple(t))
  if all(t in gset for t in corners):quad.append((g,i,j))
assert len(quad)==2;tests.append({'test':'exhaustive_rectangle_count_two','pass':True})
families=read(D/'LOCAL_FAMILY_COMPONENTS.json');fam={cid:set(v) for v in families for cid in v};folds=read(AL/'ML_UPDATE/FOLDS.json');g059family=fam['K6GDP2_DEV_G059'];g059fold=next(f['fold'] for f in folds if 'K6GDP2_DEV_G059' in f['heldout_old_ids']);assert g059fold==3
purge_audit=[]
for f in folds:
 val=set(f['heldout_old_ids']+f['heldout_new_ids']);val.update(g059family if f['fold']==g059fold else set());val.update(cid for k,cid in enumerate(sorted(keep)) if k%4==f['fold']-1)
 assert 'K6V1_S31' not in val
 blocked=set().union(*(fam.get(cid,{cid}) for cid in val));train=set(geom)-val-blocked;assert not any((set(v)&train and set(v)&val) for v in families);assert set(f['heldout_old_ids'])<=val
 purge_audit.append({'fold':f['fold'],'heldout_old124_ids_unchanged':True,'purged_family_training_members':sorted((set(geom)-val)&blocked),'train_validation_family_overlap':0,'old32_anchor_evaluated':False})
put('FAMILY_LEAKAGE_GUARD_ZERO_FIT_TEST.json',{'status':'PASS','folds':purge_audit,'g059_family_fold':3,'note':'Syntheticindexrouting only; no fits/predictions. Futurematched172baseline mustapplysamepurging. S31interactionphysicaleffectnotoutofsamplelocalskill.'});tests.append({'test':'family_purging_no_train_validation_overlap_keep124heldouts','pass':True})
assert v2['budget_proposal']['maximum_requested_entries']==50 and v2['budget_proposal']['authorized_entries']==0;tests.append({'test':'budget50unchanged_zeroauthorized','pass':True})
put('V2_ADDITIONAL_TARGETED_CHECKS.json',{'passed':len(tests),'failed':0,'tests':tests,'new_FDTD':0,'new_fits':0})
print('V2_ADDITIONAL_PASS',len(tests))
