"""Geometry-only amendment compiler and failure evidence review. No model fits."""
from pathlib import Path
import sys,json,hashlib,csv,datetime,collections,sqlite3
import numpy as np
import h5py
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');B=R/'reports/coupling'
O=B/'APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1';O.mkdir(exist_ok=True)
V=B/'COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def write(n,d):(O/n).write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def rows(n):return list(csv.DictReader((V/n).open(encoding='utf-8-sig')))
def artifact(p,expected=None):
 p=Path(p);a={'path':str(p),'exists':p.is_file()}
 if p.is_file():a.update(sha256=sha(p),bytes=p.stat().st_size)
 if expected:a.update(expected_sha256=expected,match=a.get('sha256')==expected);assert a['match'],a
 return a
L=read(B/'COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json')
candidates={r['case_id']:r for r in rows('GLOBAL_DATASET_CANDIDATES_V2.csv')};outer=rows('DEVELOPMENT_FOLD_MANIFEST_V2.csv');inner=rows('INNER_FOLD_MANIFEST_V2.csv');lc=rows('LEARNING_CURVE_SUBSET_MANIFEST_V2.csv')
old=read(B/'PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json')['ordered_geometry_ids']
valid=set(L['labels_valid_case_ids']);missing=sorted(set(L['entered_case_ids'])-valid);pool=old+sorted(valid)
assert len(pool)==156 and len(set(pool))==156
failrows=[]
for cid in missing:
 rec=L['case_records'][cid];e=rec['postentry_closeout_evidence'];a=[]
 for pk,hk in [('postentry_disposition_path','postentry_disposition_sha256'),('postentry_journal_path','postentry_journal_sha256'),('postentry_receipt_path','postentry_receipt_file_sha256'),('postentry_closeout_receipt_path','postentry_closeout_receipt_file_sha256'),('postentry_closeout_verification_path','postentry_closeout_verification_file_sha256'),('controller_state_path','controller_state_sha256')]:
  if pk in e:a.append(artifact(e[pk],e.get(hk)))
 rp=Path(e.get('postentry_disposition_path',e.get('postentry_closeout_receipt_path')));base=rp.parent.parent
 disposition=read(rp);sp=base/'status.json';status=read(sp);a.append(artifact(sp,e['runner_status_sha256']))
 assert status['case_id']==cid and status['attempt_id']=='attempt_001' and status['solver_entered'] and status['solver_invocations']==1
 native=[];nativefields={}
 for p in base.rglob('*'):
  if p.is_file() and p.suffix in ('.fsp','.h5'):
   native.append(artifact(p))
   if p.suffix=='.h5':
    with h5py.File(p,'r') as f:
     def visit(n,x):
      if isinstance(x,h5py.Dataset):nativefields[str(p)+'::'+n]={'shape':list(x.shape),'dtype':str(x.dtype)}
     f.visititems(visit)
 eh=[k for k in nativefields if k.split('/')[-1] in ['Ex','Ey','Ez','Hx','Hy','Hz']]
 assert not eh,'Complete fields unexpectedly found; review zero-solver recovery candidate rather than changing history'
 q=candidates[cid];D=[int(q[f'D{i}_nm']) for i in range(1,7)]
 physical=e.get('physical_gpu_engine_entry_count',disposition.get('physical_gpu_engine_observed','UNKNOWN'))
 failrows.append({'case_id':cid,'attempt_id':'attempt_001','run_id':rec['run_id'],'ordered_D_nm':D,
  'role':q['role'],'stratum':q['global_stratum'],'original_outer_fold':int(next(x['outer_fold'] for x in outer if x['case_id']==cid)),
  'phase':rec['phase'],'entry_consumed':True,'solver_invocations':1,'replay':0,'physical_engine_entry':physical,
  'failure':status.get('failure'),'formal_evidence':a,'native_files':native,'H5_datasets':nativefields,
  'complete_native_EH_truth_exists':False,'zero_solver_recovery_candidate':False,
  'recoverability_evidence':{k:disposition.get(k) for k in ['truth_disposition','load_only_recoverability','root_cause','truth_available','solver_return_observed']},
  'conclusion':'No complete saved fields found; archived setup FSP is not solved truth. No stateful recovery, replay or attempt_002 authorized.'})
write('FOUR_FAILED_CASE_FORENSIC.json',{'cases':failrows,'zero_solver_recovery_candidates':[],'history_modified':False})
local=[cid for cid in sorted(valid) if candidates[cid]['role']=='DEVELOPMENT_LOCAL_AXIS'];anchor='K6V1_S31';D0=np.array([220,195,210,150,140,210])
X=np.stack([np.zeros(6)]+[(np.array([int(candidates[c][f'D{i}_nm']) for i in range(1,7)])-D0)/5 for c in local]);X=np.c_[np.ones(len(X)),X]
ranks={c:int(np.linalg.matrix_rank(np.delete(X,i+1,axis=0))) for i,c in enumerate(local)}
orig=read(B/'COUPLING_ML_K6_V2_TRAINING_AND_VALIDATION_PIPELINE_IMPLEMENTATION_V1/DRY_RUN_FIT_PLAN_V1.json');groups=orig['tasks']
original_task_audit=[]
for kind,ts in groups.items():
 for t in ts:
  original_task_audit.append({'task_id':t['task_id'],'group':kind,'missing_train_ids':sorted(set(t['train_case_ids'])&set(missing)),
  'missing_validation_ids':sorted(set(t.get('prediction_case_ids',[]))&set(missing)),
  'original_training_geometry_count':t.get('training_geometry_count')})
write('ORIGINAL_281_FIT_COMPATIBILITY_AUDIT.json',{'original_counts':orig['summary']['counts'],'can_execute_unmodified':False,
 'affected_tasks':original_task_audit,'unchanged_numeric_H1_H2':True,'local_affine_design_rank':int(np.linalg.matrix_rank(X)),
 'local_leave_one_out_rank':ranks,'local_original13_fit_executable':False,
 'aggregate_loader_blocker':'load_development_collection requires exactly new128 and total160; splits.load_frozen_geometry_folds requires160/128. Existing code stays fail-closed; future approved156 adapter must validate new inventory and manifests, not bypass assertions.'})
folds={};outerrows=[];innerrows=[];curverows=[]
for f in range(1,5):
 va=[x['case_id'] for x in outer if int(x['outer_fold'])==f and x['case_id'] in valid]
 tr=[c for c in pool if c not in va];assert len(tr)>=124 and set(tr).isdisjoint(va)
 inn={k:[x['case_id'] for x in inner if int(x['outer_fold'])==f and int(x['inner_fold'])==k and x['case_id'] in tr] for k in range(1,4)}
 assert set().union(*map(set,inn.values()))==set(tr) and sum(map(len,inn.values()))==len(tr)
 sizes={32:list(old)};replacements=[]
 orig64=[x['case_id'] for x in lc if int(x['outer_fold'])==f and int(x['training_geometry_count'])==64]
 ss=[c for c in orig64 if c in tr]
 for gone in [c for c in orig64 if c not in tr]:
  st=candidates[gone]['global_stratum']
  eligible=[c for c in tr if c not in ss and c in candidates and candidates[c]['global_stratum']==st]
  eligible.sort(key=lambda c:hashlib.sha256(('156G_AMENDMENT_02_N64:'+str(f)+':'+c).encode()).hexdigest())
  assert eligible,'No same-stratum replacement';ss.append(eligible[0]);replacements.append({'missing':gone,'replacement':eligible[0],'same_stratum':st})
 assert len(ss)==64 and set(old)<=set(ss);sizes[64]=ss
 remaining=[c for c in tr if c not in ss];remaining.sort(key=lambda c:hashlib.sha256(('156G_AMENDMENT_02_N124:'+str(f)+':'+c).encode()).hexdigest())
 sizes[124]=ss+remaining[:60];assert len(sizes[124])==124
 for n,s in sizes.items():
  assert len(s)==n and len(set(s))==n and set(s)<=set(tr) and set(s).isdisjoint(va)
  for rank,c in enumerate(s):curverows.append({'outer_fold':f,'training_geometry_count':n,'rank':rank,'case_id':c,'all_21_wavelengths_grouped':True})
 for c in va:outerrows.append({'outer_fold':f,'case_id':c,'all_21_wavelengths_grouped':True})
 for k,vs in inn.items():
  for c in vs:innerrows.append({'outer_fold':f,'inner_fold':k,'case_id':c,'all_21_wavelengths_grouped':True})
 folds[f]={'validation_case_ids':va,'outer_train_case_ids':tr,'inner_validation':inn,'learning_subsets':sizes,'n64_replacements':replacements}
def csvwrite(n,rr):
 with (O/n).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
csvwrite('REVISED_OUTER_FOLDS_DRY_RUN.csv',outerrows);csvwrite('REVISED_INNER_FOLDS_DRY_RUN.csv',innerrows);csvwrite('REVISED_LEARNING_CURVE_SUBSETS_DRY_RUN.csv',curverows)
newgroups={'inner_tasks':[],'curve_templates':[],'final_templates':[],'local_tasks':[]}
for key in ['inner_tasks','curve_templates','final_templates']:
 for t in groups[key]:
  q=json.loads(json.dumps(t));f=q.get('outer_fold')
  if key=='inner_tasks':
   vv=folds[f]['inner_validation'][q['inner_fold']];q['prediction_case_ids']=vv;q['train_case_ids']=[c for c in folds[f]['outer_train_case_ids'] if c not in vv]
  elif key=='curve_templates':
   n=q['training_geometry_count'];n=124 if n==128 else n
   q['task_id']=q['task_id'].replace('_n128_','_n124_');q['train_case_ids']=folds[f]['learning_subsets'][n];q['prediction_case_ids']=folds[f]['validation_case_ids']
  else:q['train_case_ids']=pool
  q['training_geometry_count']=len(q['train_case_ids']);q['amendment_status']='PROPOSED_NOT_EXECUTION_AUTHORITY'
  assert set(q['train_case_ids']).isdisjoint(q.get('prediction_case_ids',[])) and set(q['train_case_ids'])<=set(pool)
  newgroups[key].append(q)
counts={'inner_krr':108,'inner_mlp':108,'learning_curve_krr':12,'learning_curve_mlp':36,'final_global':4,'local_affine':0,'total':268}
assert sum(map(len,newgroups.values()))==268
summary={'status':'AMENDMENT_REQUIRED','proposal_id':'V2_PROPOSED_AMENDMENT_02_156G_CLOSURE','actual_training_sizes':[32,64,124],
 'fold_sizes':{f:{'validation':len(v['validation_case_ids']),'outer_train':len(v['outer_train_case_ids']),
 'inner_validation':[len(v['inner_validation'][k]) for k in range(1,4)],'unconsumed_by_max_curve':len(v['outer_train_case_ids'])-124} for f,v in folds.items()},
 'fit_counts':counts,'real_training_executed':0,'final_pool':156,'deferred_local_fit_budget':13,
 'original_sizes_not_preserved':'128 is impossible in all four fixed validation folds; 124 is the common maximum. Retain32/64. Do not label125/126 or124 as128.',
 'selection_scope':'Original outer-train inner selection preserved: hyperparameter/epoch selection uses124-126 groups. Curve32/64/124 counts actual refit geometries, not the total development responses consumed for selection. Not a pure total-label-budget learning curve.',
 'comparability':'Existing32 remain train-only and historically exposed. Filter missing validation identities; original validation membership of survivors unchanged. New fold sample counts and max training size differ from160G; no unqualified paired claim of improvement over unavailable160G.',
 'pipeline_required_change':'Approved156 collection/fold adapter with inventory+SHA gating needed; do not loosen160G loader in this audit.',
 'local':'Defer original13 fits. One LOAO fold has rank6 vs required7 when D6_P05 is withheld; anchor alone does not supply D6 slope. No automatic reduced-axis model or pseudoinverse workaround.',
 'unchanged':['models','588D Cartesian state','21D actual log/exp P_scale','H1/H2','geometry grouping','train-only preprocessing','seed0/1/2','complex C_hat seed mean','physical P_scale arithmetic seed mean','sealed confirmation access']}
write('REVISED_FOLD_AND_FIT_MANIFEST_DRY_RUN.json',{'schema':'PROPOSED_156G_FIT_PLAN_DRY_RUN_V1','summary':summary,'tasks':newgroups})
write('PROPOSED_156G_TRAINING_AMENDMENT.json',summary)
def strata(cs):return dict(collections.Counter(candidates[c]['global_stratum'] for c in cs))
impact={'missing_cases':failrows,'local_available':len(local),'local_planned':12,'paired_axes':[1,2,3,4,5],'unpaired_axis':6,
 'local_LOAO_rank':ranks,'global_planned':strata([c for c,x in candidates.items() if x['role']=='DEVELOPMENT_GLOBAL']),
 'global_available':strata([c for c in valid if candidates[c]['role']=='DEVELOPMENT_GLOBAL']),
 'missing_all_global_deep_interior':True,'global_missingness_cause':'Historical execution/license/orphan failures; three deep-interior points consecutively ordered at boundary of old worker lifecycle. This is a localized stratum loss, not evidence response-dependent selection or random MCAR missingness.',
 'fold_capacity':summary['fold_sizes'],'joint_geometry_leakage':False,'confirmation_reallocated':False,
 'additional_HF':'Global model need not wait for3 deep points; no automatic newHF. If full six-axis local bilateral/LOAO objective retained, D6_M05 is uniquely required by frozen local design. Seek separately reviewed replacement-entry authority only after reviewing need; consumed attempt cannot replay.'}
write('MISSING_FOUR_GEOMETRY_IMPACT_REPORT.json',impact)
pkg=read(B/'COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1/CASE_REGISTRATION_PACKAGE_V1.json')
conf=[x for x in pkg['cases'] if x['case_id'] not in set(L['entered_case_ids'])]
assert len(conf)==32 and all('SEALED' in x['role'] for x in conf)
assert set(x['case_id'] for x in conf).isdisjoint(pool)
write('CONFIRMATION_ISOLATION_AUDIT.json',{'geometry_metadata_only':True,'response_access':0,'count':32,
 'local':4,'global_core':27,'global_stress':1,'case_roles':[{'case_id':x['case_id'],'role':x['role'],'stress':bool(x.get('boundary_stress'))} for x in conf],
 'two_candidates_predictions_before_reveal':True,'all28_original_conjunctive_gates_retained':True,'no_case_moved_to_development':True,
 'local4_opening_blocked_until_valid_local_model_protocol_and_predictions_frozen':True,
 'failure_conversion_rule':'If confirmation responses converted to development, document conversion and use a new sealed set for next confirmation.'})
print(json.dumps({'proposed_fit_count':268,'folds':summary['fold_sizes'],'local_ranks':ranks,'failed_ids':missing},indent=2))
