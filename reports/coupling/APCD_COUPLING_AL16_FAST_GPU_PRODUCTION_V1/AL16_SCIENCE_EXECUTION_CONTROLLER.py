from pathlib import Path
import json,sys,subprocess,sqlite3,datetime,os,traceback,time,hashlib
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';D=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');CLI=Path(r'C:\Users\DELL\anaconda3\python.exe');SCIPY=Path(r'N:\anaconda_envs\RCP_LCP\python.exe');RUNNER=P/'minimal_batch_runner_v3.1_final.py'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(p,v):
 p=Path(p);tmp=p.with_suffix('.atomic.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(tmp,p)
def put(n,v):atomic(D/n,v)
package=read(B/'AL16_FAST_PRODUCTION_MANIFEST.json');authority=read(D/'REAL_EXECUTION_AUTHORITY.json');assert authority['max_real_entries']==16 and len(package['cases'])==16
cases={c['case_id']:c for c in package['cases']};batches={c['case_id']:c for c in package['runner_batches']};ids={c['external_execution_id'] for c in cases.values()}
assert package['execution_order'][:2]==['K6AL_FAST_R01_G001','K6AL_FAST_R01_G009']
old_path=Q/'APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING/DIAG2_SCIENCE_LEDGER.json';old_bytes=old_path.read_bytes()
sys.path.insert(0,str(P));import shared_resource_gate as resource
policy=read(P/'shared_resource_policy.json')
def canonical():
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 jobs=[dict(r) for r in con.execute('select * from jobs') if r['external_execution_id'] in ids];entries=[dict(r) for r in con.execute('select * from solver_entries') if r['external_execution_id'] in ids];con.close()
 assert len(entries)<=16 and len({e['external_execution_id'] for e in entries})==len(entries)
 for e in entries:
  c=next(c for c in cases.values() if c['external_execution_id']==e['external_execution_id'])
  assert e['case_id']==c['case_id'] and e['attempt_id']==c['attempt_id'] and e['pre_fsp_sha256']==c['source_fsp_sha256'] and e['physical_contract_sha256']==c['physical_contract_sha256'] and e['execution_mode']=='REAL'
 return jobs,entries
ledger={'task':authority['task'],'authority_record':str(D/'REAL_EXECUTION_AUTHORITY.json'),'budget_id':'AL16_FAST_R01_BUDGET_PROPOSAL_V1','maximum_entries':16,'authorized_entries':16,'entered':0,'labels_valid':0,'labels_invalid':0,'replay_count':0,'execution_order':package['execution_order'],'cases':{k:dict(case_id=k,external_execution_id=c['external_execution_id'],attempt_id=c['attempt_id'],source_fsp_sha256=c['source_fsp_sha256'],physical_contract_sha256=c['physical_contract_sha256'],state='AUTHORIZED_NOT_ENTERED',entry_id=None,labels_valid=False) for k,c in cases.items()}}
def sync():
 jobs,entries=canonical();assert old_path.read_bytes()==old_bytes,'protected DIAG2 ledger changed; HOLD'
 for e in entries:ledger['cases'][e['case_id']].update(entry_id=e['id'],runner_job_id=e['job_id'],solver_entered=True,entered_at=e['entered_at'])
 ledger.update(entered=len(entries),remaining=16-len(entries),labels_valid=sum(c['labels_valid'] for c in ledger['cases'].values()),updated_utc=now());put('AL16_SCIENCE_LEDGER.json',ledger);return jobs,entries
def cli(args,outprefix):
 with (D/(outprefix+'_STDOUT.log')).open('w',encoding='utf-8') as out,(D/(outprefix+'_STDERR.log')).open('w',encoding='utf-8') as err:
  child=subprocess.Popen([str(CLI),str(RUNNER),*args],cwd=str(P),stdout=out,stderr=err)
  put(outprefix+'_PROCESS.json',dict(pid=child.pid,started_utc=now(),args=args))
  return child.wait()
lock=D/'AL16_SCIENCE_CONTROLLER_EXCLUSIVE.lock';fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,json.dumps({'pid':os.getpid(),'utc':now()}).encode());os.close(fd)
put('CONTROLLER_STATE.json',dict(state='STARTING',pid=os.getpid(),utc=now(),authorized16=True));assert not canonical()[0] and not canonical()[1],'AL already registered: stop and reconcile; no replay'
sync()
try:
 for index,cid in enumerate(package['execution_order']):
  c=cases[cid];batch=batches[cid];state=ledger['cases'][cid]
  if index>=2:assert all(ledger['cases'][k]['labels_valid'] for k in package['canary_first_two'])
  jobs,entries=sync();assert len(entries)<16 and not any(j['external_execution_id']==c['external_execution_id'] for j in jobs)
  assert hashlib.sha256(RUNNER.read_bytes()).hexdigest()=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7'
  req=read(batch['manifest'])['jobs'][0]['resource_requirements'];snapshot=resource.check(req,D,policy);put(cid+'_PREFLIGHT_RESOURCES.json',snapshot)
  assert not snapshot['hold_reasons'],snapshot['hold_reasons']
  state.update(state='REGISTERING',updated_utc=now());sync();rc=cli(['submit',batch['batch_name'],'--manifest',batch['manifest']],cid+'_SUBMIT');assert rc==0,('submit failed',cid,rc)
  jobs,entries=sync();j=next(j for j in jobs if j['external_execution_id']==c['external_execution_id']);assert j['status']=='PENDING' and not any(e['external_execution_id']==c['external_execution_id'] for e in entries)
  state.update(state='RUN_INVOCATION_ONCE',runner_job_id=j['id'],launch_intent_utc=now());sync();put(cid+'_RUN_INVOCATION_ONCE.json',dict(case_id=cid,external_execution_id=c['external_execution_id'],authority=str(D/'REAL_EXECUTION_AUTHORITY.json'),utc=now(),max_invocations=1))
  put('CONTROLLER_STATE.json',dict(state='SOLVING',case_id=cid,index=index+1,total=16,utc=now(),pid=os.getpid()));rc=cli(['run',batch['batch_name']],cid+'_RUN');put(cid+'_RUN_RETURN.json',dict(returncode=rc,utc=now()))
  jobs,entries=sync();je=next(j for j in jobs if j['id']==state['runner_job_id']);ee=[e for e in entries if e['external_execution_id']==c['external_execution_id']]
  assert len(ee)==1 and rc==0 and je['status']=='COMPLETED',('run result HOLD',cid,rc,je['status'],len(ee))
  state.update(state='NATIVE_COMPLETE_PENDING_SCIENCE',native_fsp=je['output_fsp_path'],native_fsp_sha256=je['output_sha256']);sync()
  put('CONTROLLER_STATE.json',dict(state='SCIENTIFIC_ACCEPTANCE',case_id=cid,index=index+1,total=16,utc=now(),pid=os.getpid()))
  with (D/(cid+'_EXTRACTION_STDOUT.log')).open('w',encoding='utf-8') as out,(D/(cid+'_EXTRACTION_STDERR.log')).open('w',encoding='utf-8') as err:
   post=subprocess.run([str(SCIPY),str(B/'al16_extract_native_v1.py'),'--case',cid],cwd=str(R),stdout=out,stderr=err)
  assert post.returncode==0,('offline extraction failure; retain evidence; never replay',cid)
  outdir=Path(c['science_output_directory']);receipt=read(outdir/'SCIENCE_RECEIPT.json');assert receipt['labels_valid']=='PASS' and receipt['truth_valid']=='PASS' and receipt['entry_id']==ee[0]['id']
  # Native extraction preserves contract-defined metrics and frozen numeric validation, no strict convergence reclassification.
  raw_files=list((outdir/'raw').glob('*_raw.json'));assert len(raw_files)==1;raw=read(raw_files[0]);metrics=raw['metrics'];assert all(metrics[n]['status']=='PASS' for n in ['order_sign','reference_plane_deembedding','lossy_gan'])
  for row in metrics['rows']:
   for key in ['R_FDTD','T_FDTD','A_FDTD','output_P_scale_IN_REF','output_incident_cell_power_W','output_transmitted_power_W']:
    value=float(row[key]);assert value==value and abs(value)!=float('inf'),('nonfinite',key)
   assert row['output_incident_cell_power_W']>0 and row['output_transmitted_power_W']>0 and row['R_FDTD']>=0 and row['T_FDTD']>=0,'illegal native power'
  state.update(state='LABELS_VALID',labels_valid=True,truth_valid=True,receipt=str(outdir/'SCIENCE_RECEIPT.json'),labels=str(outdir/'labels_609d.npz'),truth_h5=str(outdir/'truth.h5'),accepted_utc=now());sync()
  put(cid+'_SCIENCE_ACCEPTANCE.json',dict(status='PASS_ML_TRAINING_GRADE',receipt=receipt,energy_metrics={k:metrics.get(k) for k in ['max_energy_closure','order_sign','reference_plane_deembedding','lossy_gan']},energy_limit_note='frozen existing definitions; A=1-R-T algebraic closure not independent absorption; strict convergence not claimed',native_power_finite_and_nonnegative=True,old_DIAG2_ledger_unchanged=True))
  print('ACCEPTED',cid,ledger['entered'],ledger['labels_valid'],flush=True)
 put('CONTROLLER_STATE.json',dict(state='PRODUCTION_COMPLETE_PENDING_ML',utc=now(),entered=ledger['entered'],labels_valid=ledger['labels_valid'],pid=os.getpid()))
except Exception:
 err=traceback.format_exc();put('PRODUCTION_HOLD.json',dict(utc=now(),error=err,case_id=locals().get('cid'),no_replay=True));
 try:sync()
 except Exception:pass
 put('CONTROLLER_STATE.json',dict(state='HOLD',case_id=locals().get('cid'),utc=now(),error=err,pid=os.getpid()));print(err,flush=True)
finally:
 put('CONTROLLER_EXIT.json',dict(utc=now(),pid=os.getpid(),lock_retained_for_forensic=True))
