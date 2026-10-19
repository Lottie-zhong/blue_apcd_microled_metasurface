"""Read-only production reconciliation and zero-solver AL50 report generation."""
from pathlib import Path
import json,sqlite3,csv,datetime,subprocess,sys,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def main():
 l=read(D/'AL50_SCIENCE_LEDGER.json');assert l['entered']==l['labels_valid']==50 and l['replay_count']==0
 assert read(D/'STAGE_50/STAGE_COMPLETE.json')['stage_new_valid']==50
 package=read(B/'AL50_FAST_PRODUCTION_MANIFEST_V2.json');ids={c['external_execution_id'] for c in package['cases']};assert len(ids)==50
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 jobs=[dict(r) for r in con.execute('select * from jobs') if r['external_execution_id'] in ids];entries=[dict(r) for r in con.execute('select * from solver_entries') if r['external_execution_id'] in ids];con.close()
 assert len(jobs)==len(entries)==len({e['external_execution_id'] for e in entries})==50
 assert [e['case_id'] for e in sorted(entries,key=lambda e:e['entered_at'])]==l['execution_order']
 for p in read(D/'PROTECTED_LEDGER_SNAPSHOTS.json'):assert read(p['path'])==p['content']
 rows=[]
 for c in package['cases']:
  cid=c['case_id'];j=next(x for x in jobs if x['case_id']==cid);e=next(x for x in entries if x['case_id']==cid);o=Path(c['science_output_directory']);r=read(o/'SCIENCE_RECEIPT.json');z=np.load(o/'labels_609d.npz',allow_pickle=False)
  assert j['status']=='COMPLETED' and e['execution_mode']=='REAL' and r['truth_valid']==r['labels_valid']=='PASS'
  assert e['id']==r['entry_id']==l['cases'][cid]['entry_id'] and e['pre_fsp_sha256']==c['source_fsp_sha256'] and e['physical_contract_sha256']==c['physical_contract_sha256']
  assert j['output_sha256']==r['native_fsp']['sha256'] and j['output_fsp_path']==r['native_fsp']['path']
  assert Path(j['output_fsp_path']).is_file() and (o/'truth.h5').is_file() and all(Path(h['path']).is_file() for h in r['native_h5'])
  assert z['model_target'].shape==(1,609) and np.isfinite(z['model_target']).all() and (z['P_scale']>0).all()
  assert not read(D/(cid+'_PREFLIGHT_RESOURCES.json'))['hold_reasons']
  start=datetime.datetime.fromisoformat(j['started_at']);end=datetime.datetime.fromisoformat(j['completed_at']);accepted=datetime.datetime.fromisoformat(l['cases'][cid]['accepted_utc'])
  rows.append(dict(case_id=cid,job_id=j['id'],entry_id=e['id'],external_execution_id=c['external_execution_id'],selection_role=c['selection_role'],ordered_D_nm=c['ordered_D_nm'],source_fsp_sha256=c['source_fsp_sha256'],physics_contract_sha256=c['physical_contract_sha256'],native_fsp=j['output_fsp_path'],native_fsp_sha256=j['output_sha256'],native_h5=[h['path'] for h in r['native_h5']],science_truth_h5=str(o/'truth.h5'),labels=str(o/'labels_609d.npz'),labels_sha256=r['labels_sha256'],receipt=str(o/'SCIENCE_RECEIPT.json'),started_utc=j['started_at'],completed_utc=j['completed_at'],accepted_utc=l['cases'][cid]['accepted_utc'],solver_call_seconds=(end-start).total_seconds(),entry_to_science_seconds=(accepted-start).total_seconds(),labels_valid=True,grade='ML_TRAINING_GRADE'))
 # Canary scientific acceptance must precede every later entry.
 for a,b in zip(l['execution_order'][:2],l['execution_order'][1:3]):
  ra=next(v for v in rows if v['case_id']==a);rb=next(v for v in rows if v['case_id']==b);assert datetime.datetime.fromisoformat(ra['accepted_utc'])<datetime.datetime.fromisoformat(rb['started_utc'])
 stages={str(n):read(D/f'STAGE_{n:02d}/STAGE_COMPLETE.json') for n in [16,32,50]};metrics=read(D/'STAGE_50/MODEL_METRICS_SAME124.json');local=read(D/'STAGE_50/LOCAL_DIFFERENCE_ACCURACY.json')
 first=min(datetime.datetime.fromisoformat(x['started_utc']) for x in rows);last=max(datetime.datetime.fromisoformat(x['accepted_utc']) for x in rows)
 old=np.load(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False)['D_nm'];new=np.array([c['ordered_D_nm'] for c in package['cases']]);allx=np.r_[old,new]
 assert len(set(map(tuple,allx)))==222
 coverage={f'D{i+1}':{'old_counts':{str(v):int((old[:,i]==v).sum()) for v in range(100,231,5)},'new_counts':{str(v):int((allx[:,i]==v).sum()) for v in range(100,231,5)}} for i in range(6)}
 nearest=np.linalg.norm((new[:,None,:]-old[None,:,:])/130,axis=2).min(axis=1);coverage['new_to_old_nearest_6D_normalized']={'mean':float(nearest.mean()),'min':float(nearest.min()),'max':float(nearest.max()),'definition':'Euclidean distance after dividing each diameter by 130 nm'};put('GEOMETRY_COVERAGE_CHANGE.json',coverage)
 verdict={}
 for k in ['KRR','ExtraTrees','MLP']:
  g=metrics['GLOBAL_ONLY_ABLATION'][k];m=metrics['MATCHED_40_ACQUISITIONS_MIXED'][k];a=metrics['ALL_V2_AVAILABLE'][k]
  verdict[k]={'mixed40_minus_global40_Pplus_MAE':m['P_plus1_H2']['MAE']-g['P_plus1_H2']['MAE'],'all50_minus_global40_Pplus_MAE':a['P_plus1_H2']['MAE']-g['P_plus1_H2']['MAE'],'negative_means_lower_error':True,'independent_local_test_families':1,'not_causal_against_unrun_V1':True}
 put('LOCAL_SAMPLING_VALUE_LIMITED_ABLATION.json',verdict)
 summary=dict(AL50_SOLVER_ENTRIES=50,AL50_LABELS_VALID=50,AL50_LABELS_INVALID=0,AL50_REPLAY_COUNT=0,AL50_GPU_TIME_hours=sum(x['solver_call_seconds'] for x in rows)/3600,AL50_GPU_TIME_definition='Canonical started_at to completed_at, including native load/run/save; not GPU kernel profiling',AL50_TOTAL_SERVICE_TIME_hours=sum(x['entry_to_science_seconds'] for x in rows)/3600,AL50_WALL_hours=(last-first).total_seconds()/3600,FAST_DATASET_TOTAL=222,LOCAL_PAIR_TRUTH_COUNT=stages['50']['local_pair_truth_count'],COMPLETE_INTERACTION_GROUP_COUNT=stages['50']['complete_interaction_group_count'],MODEL_MAE_BEFORE_AFTER=metrics,LOCAL_DIFFERENCE_ACCURACY=local,local_sampling_ablation=verdict,stages=stages,protected_ledgers_unchanged=True,DIAG2='1/2',A2='HOLD',DOE56='HOLD',manufacturing='UNRESOLVED',strict_convergence='NOT_CERTIFIED',next_batch_authorized_entries=0,sealed_response_access=0)
 put('INDEPENDENT_PRODUCTION_RECONCILIATION.json',summary);put('NATIVE_ARTIFACT_INDEX.json',rows)
 with (D/'CASE_RESULTS.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 table=['|Model|P(+1) MAE before|After|450nm rho before|After|','|---|---:|---:|---:|---:|']
 for k in ['Mean','KRR','ExtraTrees','MLP']:
  a=metrics['MATCHED_172_BASELINE'][k];b=metrics['ALL_V2_AVAILABLE'][k];table.append(f"|{k}|{a['P_plus1_H2']['MAE']:.7f}|{b['P_plus1_H2']['MAE']:.7f}|{a['450nm_Pplus_mean_fold_Spearman']}|{b['450nm_Pplus_mean_fold_Spearman']}|")
 report=f'''# AL50 Local + Global V2 real production

## Production
50/50 real entries; 50 valid labels; 0 invalid; 0 replay. FAST dataset 172 → 222 independent geometries. Solver-call time {summary['AL50_GPU_TIME_hours']:.3f} h; summed entry-to-science time {summary['AL50_TOTAL_SERVICE_TIME_hours']:.3f} h; first-entry to last-acceptance wall {summary['AL50_WALL_hours']:.3f} h. Timing definitions differ; solver-call time is not kernel-only GPU time.

All original V2 identities retained; V1 superseded cases excluded. G001 then L001 were accepted before the remaining entries. Source/physics identities agree across frozen Manifest, canonical entries and science receipts. No historical raw files or protected ledgers changed.

## Matched evaluation
Same 124 validation geometries; family members purged from training; matched 172 baseline refit once. Published legacy unpurged metrics are a separate reference, not this before/after comparator. Fold-specific counts and purged identities are saved alongside predictions.

{chr(10).join(table)}

## Local sampling ablation
Negative MAE deltas favor the mixed local/global allocation at equal nominal 40 acquisitions. Per-fold training counts differ under family purging. These comparisons are exploratory with one eligible local validation family.

```json
{json.dumps(verdict,indent=2)}
```

## Local information and limits
{summary['LOCAL_PAIR_TRUTH_COUNT']} complete local edges and {summary['COMPLETE_INTERACTION_GROUP_COUNT']} full four-corner truth experiments. Truth interaction is Yij−Yi−Yj+Y0. Per-wavelength truth and model errors are in STAGE_50. Nonadditivity does not uniquely identify a near-field mechanism. S31 is truth-only for local generalization because its original anchor is train-only. Only G059 is an eligible held-out local family; wavelengths are not independent experimental replicates.

Whether local sampling adds predictive value must use the saved GLOBAL_ONLY_ABLATION and equal nominal 40-acquisition mixed view, local delta/direction errors and held-out interaction error together. These are limited ablations, not causal proof against the unrun V1 removed cases. Local response amplitude is compared with observed A1 time sensitivity only; different geometry and unresolved grid error prevent interpreting that comparison as an uncertainty bound.

Recommend retaining global coverage as the default and using a small bounded local fraction until independent held-out local families establish repeatable gains. Do not raise local share solely because physical interactions are measurable. Next batch requires separate entry authorization. No automatic budget increase follows model stagnation.

## Data and artifacts
CASE_RESULTS.csv and NATIVE_ARTIFACT_INDEX.json enumerate every FSP/H5/609D and receipt. STAGE_16/32/50 contain fixed-124 metrics, Mean baseline, target MAE/RMSE, ranking, top recall, local errors, ablations, fit timing/warnings and family partitions. Figures show saved truth, interactions and learning curves. ML_TRAINING_GRADE; strict numerical convergence is not certified; fabrication UNRESOLVED.

## Frozen boundaries
DIAG2 1/2; A2 HOLD; DOE56 HOLD; sealed confirmation not accessed; Runner unchanged; no further production entries authorized.
'''
 (D/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
 (D/'CONTINUATION.md').write_text('# Continuation\n\nAL50 production and staged ML complete; see FINAL_REPORT and independent reconciliation. No more Solver Entry authorized. Visual figure QA and final interpretation require independent inspection before user delivery. DIAG2 1/2; A2 HOLD; DOE56 HOLD. Preserve all existing Git changes.\n',encoding='utf-8')
 git={}
 for key,args in [('branch',['branch','--show-current']),('HEAD',['rev-parse','HEAD']),('ahead_behind',['rev-list','--left-right','--count','HEAD...@{u}']),('status',['status','--short']),('staged',['diff','--cached','--name-only'])]:
  result=subprocess.run(['git','-C',str(R),*args],capture_output=True,text=True,encoding='utf-8');git[key]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
 put('GIT_CLOSEOUT_STATUS.json',git)
 print('AL50_PRODUCTION_RECONCILED',50,222,summary['LOCAL_PAIR_TRUTH_COUNT'],summary['COMPLETE_INTERACTION_GROUP_COUNT'])
if __name__=='__main__':main()
