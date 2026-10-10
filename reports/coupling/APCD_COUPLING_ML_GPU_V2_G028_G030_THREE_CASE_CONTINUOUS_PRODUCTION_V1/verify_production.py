"""Read-only final evidence audit. Never dispatch, LOAD, fit, replay or alter ledgers."""
from pathlib import Path
import json,hashlib,sqlite3,datetime,sys
import numpy as np
import h5py
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
RUNTIME=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1')
OUT=Path(__file__).parent
CASES=['K6GDP2_DEV_G028','K6GDP2_DEV_G029','K6GDP2_DEV_G030']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def public(x):
 if isinstance(x,dict):
  y={k:public(v) for k,v in x.items() if k not in ['command','payload']}
  if 'payload' in x:y['original_payload_sha256']=hashlib.sha256(str(x['payload']).encode()).hexdigest()
  if 'command' in x:y['command_sha256']=hashlib.sha256(json.dumps(x['command']).encode()).hexdigest()
  return y
 if isinstance(x,list):return [public(v) for v in x]
 return x
def audit():
 lp=ROOT/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json'
 coupling=read(lp)
 db=sqlite3.connect('file:'+str(RUNTIME/'ledger.sqlite3').replace('\\','/')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 tasks=[dict(x) for x in db.execute('select * from tasks')];slot=[dict(x) for x in db.execute('select * from slot')]
 events=[dict(x) for x in db.execute('select * from events')]
 db.close()
 errors=[];results=[];bindings={}
 def check(condition,message):
  if not condition:errors.append(message)
 def verify(desc):
  p=Path(desc['path']);actual=sha(p) if p.is_file() else None
  check(actual==desc['sha256'],'PIN:'+str(p))
  bindings[str(p)]=actual
 for case in CASES:
  a=read(OUT/(case+'_ADMISSION.json'))
  verify(a['source_manifest']);verify(a['physical_contract'])
  check(sha(a['pre_fsp'])==a['pre_fsp_sha256'],case+':SOURCE_CHANGED')
  record=coupling.get('case_records',{}).get(case,{})
  rows=[x for x in tasks if x['case_id']==case]
  check(len(rows)==1,case+':SINGLE_SQLITE_TASK')
  if not rows:results.append(dict(case_id=case,status='UNENTERED'));continue
  row=rows[0];request=json.loads(row['payload']);rs=row['request_sha'];ev=[x for x in events if x['request_sha']==rs]
  for x in ev:x['decoded_payload']=json.loads(x['payload'])
  beats=[x for x in ev if x['kind']=='HEARTBEAT']
  heartbeat=dict(count=len(beats),first=beats[0] if beats else None,last=beats[-1] if beats else None)
  engines=[x for x in ev if x['kind']=='ENGINE_PROCESS']
  engine_summary=dict(count=len(engines),first=engines[0] if engines else None,last=engines[-1] if engines else None,unique_pids=sorted(set(x['decoded_payload']['pid'] for x in engines)))
  check(len(engine_summary['unique_pids'])==1,case+':ONE_GPU_ENGINE')
  ev=[x for x in ev if x['kind'] not in ['HEARTBEAT','ENGINE_PROCESS']]
  check(row['entered']==1 and row['state']=='TRUTH_VALID',case+':SQLITE_TRUTH_VALID')
  check(record.get('request_sha256')==rs and record.get('phase')=='V2_TRUTH_VALID',case+':CROSS_LEDGER')
  check(record.get('labels_valid') is True and record.get('truth_valid') is True,case+':COUPLING_VALID')
  check(request['ordered_D_nm']==a['ordered_D_nm'] and request['attempt_id']=='attempt_001',case+':INPUT_IDENTITY')
  proofpath=record.get('v2_entry_receipt')
  if proofpath:verify(dict(path=proofpath,sha256=record['v2_entry_receipt_sha256']))
  for kind in ['PROCESS_RETURNED']:
   check(len([x for x in ev if x['kind']==kind])==1,case+':UNIQUE_'+kind)
  evidence=record.get('evidence',{})
  if 'validation' not in evidence:
   results.append(dict(case_id=case,state=row['state'],entered=row['entered'],events=ev));continue
  val=evidence['validation'];bundle=evidence['bundle']
  check(val['verdict']=='PASS' and val['outputs']==609 and val['fresh_load_verified'] is True and val['actual_importer']=='load_verified_runner_case',case+':IMPORTER')
  check(val['record']['solver_invocations']==1 and val['record']['replay_count']==0,case+':ENTRY_REPLAY')
  for desc in val['record'].values():
   if isinstance(desc,dict) and 'path' in desc and 'sha256' in desc:verify(desc)
  verify(val['labels_artifact'])
  published=ROOT/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1'/('INGESTED_TRUTH_'+case+'_V1.npz')
  receiptp=published.with_name('INGEST_RESULT_'+case+'_V1.json')
  verify(dict(path=str(published),sha256=val['labels_artifact']['sha256']))
  check(receiptp.exists(),case+':PUBLISHED_INGEST_RECEIPT')
  ingest=read(receiptp)
  check(ingest['case_id']==case and ingest['attempt_id']=='attempt_001' and ingest['status']=='PASS',case+':INGEST_IDENTITY')
  check(ingest['input_artifacts']==val['record'],case+':INGEST_TRUTH_PROVENANCE')
  check(ingest['access_counts']['training_fit_count']==0 and ingest['access_counts']['p_scale_fit_count']==0 and ingest['access_counts']['confirmation_response_opened'] is False and ingest['access_counts']['automatic_replay']==0,case+':INGEST_ACCESS_COUNTS')
  bindings[str(receiptp)]=sha(receiptp)
  artifacts={}
  for relative,desc in bundle['files'].items():
   p=Path(bundle['path'])/relative;verify(dict(path=str(p),sha256=desc['sha256']))
   artifacts[relative]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
  with np.load(val['labels_artifact']['path'],allow_pickle=False) as labels:
   check(str(labels['case_id'])==case and str(labels['attempt_id'])=='attempt_001',case+':LABEL_ID')
   check(labels['ordered_D_nm'].tolist()==a['ordered_D_nm'],case+':LABEL_ORDERED_GEOMETRY')
   check(np.array_equal(labels['wavelengths_nm'],np.arange(440,461)),case+':WAVELENGTH')
   check(np.array_equal(labels['order_m'],np.arange(-3,4)),case+':ORDER')
   check(labels['polarization'].tolist()==['TE','TM'],case+':POL')
   for key in ['C_hat_real','C_hat_imag']:
    check(labels[key].shape==(21,7,2) and np.isfinite(labels[key]).all(),case+':'+key)
   check(labels['P_scale'].shape==(21,) and np.isfinite(labels['P_scale']).all() and (labels['P_scale']>0).all(),case+':POSITIVE_SCALE')
   pscale_range=[float(labels['P_scale'].min()),float(labels['P_scale'].max())]
   sys.path.insert(0,str(ROOT/'scripts/coupling_ml'))
   from k6_v2_pipeline import h1
   decoded=h1.reconstruct_h2(labels['C_hat_real']+1j*labels['C_hat_imag'],labels['P_scale'],h1.load_h2_decoder())
   h2_diagnostics={k:float(np.max(np.abs(decoded[k][0]-labels[t]))) for k,t in [('eta','eta'),('absolute_order','absolute_order'),('total_power','P_scale')]}
   h2_diagnostics['interpretation']='Modal H2 vs native-grating labels on the same saved run; descriptive comparison, not independent physical validation or a new gate.'
  h5datasets={}
  h5path=Path(bundle['path'])/'run/run_output.h5'
  with h5py.File(h5path,'r') as f:
   def visit(name,obj):
    if isinstance(obj,h5py.Dataset) and name.rsplit('/',1)[-1] in ['Ex','Ey','Ez','Hx','Hy','Hz']:
     h5datasets[name]=dict(shape=list(obj.shape),dtype=str(obj.dtype))
   f.visititems(visit)
  groups={n.rsplit('/',1)[0] for n in h5datasets}
  check(len(groups)>=3 and all(all(group+'/'+k in h5datasets for k in ['Ex','Ey','Ez','Hx','Hy','Hz']) for group in groups),case+':SIX_NATIVE_FIELDS')
  check(all(x['shape'][-1]==42 for x in h5datasets.values()),case+':21_COMPLEX_WAVELENGTHS_NATIVE_PACKING')
  returned=[x for x in ev if x['kind']=='PROCESS_RETURNED']
  check(bool(returned) and returned[0]['decoded_payload']['returncode']==0,case+':SOLVER_RETURN0')
  first_engine=engines[0]['utc_unix'] if engines else None
  return_time=returned[0]['utc_unix'] if returned else None
  native_session=val.get('native_session',{})
  timing=dict(conservative_entry_at=row['entry_at'],first_observed_engine_at=first_engine,process_return_at=return_time,engine_observed_to_return_seconds=return_time-first_engine if first_engine and return_time else None,fresh_load_started=native_session.get('started_unix'),fresh_load_finished=native_session.get('finished_unix'),truth_terminal_at=next((x['utc_unix'] for x in ev if x['kind']=='TRUTH_VALID'),None),controller_pid=returned[0]['decoded_payload']['launcher'].get('ppid') if returned else None,note='Engine-observation to launcher-return includes lifecycle/save tail; not pure kernel solve time.')
  check(val['record']['case_id']==case and val['record']['attempt_id']=='attempt_001',case+':VALIDATION_CASE_ID')
  results.append(dict(case_id=case,attempt_id='attempt_001',state=row['state'],entry=1,replay=0,request_sha256=rs,artifacts=artifacts,labels=val['labels_artifact'],pscale_range=pscale_range,h2_diagnostics=h2_diagnostics,timing=timing,native_fields=h5datasets,heartbeat=public(heartbeat),engine_evidence=public(engine_summary),events=public(ev)))
 check(len({x.get('labels',{}).get('sha256') for x in results})==3,'THREE_DISTINCT_LABEL_HASHES')
 controllers={x.get('timing',{}).get('controller_pid') for x in results}
 check(len(controllers)==1 and None not in controllers,'ONE_CONTROLLER_FOR_THREE_CASES')
 for left,right in zip(results,results[1:]):
  check(bool(left.get('timing',{}).get('truth_terminal_at')) and left['timing']['truth_terminal_at']<right['timing']['conservative_entry_at'],'TRUTH_BEFORE_NEXT:'+left['case_id'])
 for key,idkey in [('entered_count','entered_case_ids'),('truth_valid_count','truth_valid_case_ids'),('labels_valid_count','labels_valid_case_ids'),('remaining_unentered_count','remaining_unentered_case_ids')]:
  check(coupling[key]==len(set(coupling[idkey])),key+':COUNT_SET')
 check([coupling[k] for k in ['entered_count','truth_valid_count','labels_valid_count','remaining_unentered_count']]==[42,38,38,86],'EXPECTED_FINAL_COUNTS')
 check('K6GDP2_DEV_G031' in coupling['remaining_unentered_case_ids'] and 'K6GDP2_DEV_G031' not in coupling['entered_case_ids'],'G031_UNENTERED')
 check(not any(x['case_id']=='K6GDP2_DEV_G031' and x['entered'] for x in tasks),'G031_SQLITE')
 check(slot[0]['token'] is None,'SLOT_CLEAR')
 check(coupling.get('automatic_replay_count')==0 and coupling.get('confirmation_response_access_count')==0,'REPLAY_CONFIRMATION_ZERO')
 check(not errors,'FINAL_CHECKS')
 return dict(schema='COUPLING_G028_G030_FINAL_READ_ONLY_AUDIT_V1',status='PASS' if not errors else 'PARTIAL',observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),errors=errors,cases=results,counts={k:coupling.get(k) for k in ['entered_count','truth_valid_count','labels_valid_count','remaining_unentered_count','automatic_replay_count','confirmation_response_access_count']},slot=slot,source_bindings=bindings,coupling_ledger_sha256=sha(lp),fit_count=0)
if __name__=='__main__':
 result=audit()
 (OUT/'FINAL_SCIENTIFIC_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:result[k] for k in ['status','observed_at_utc','errors','counts']}))
