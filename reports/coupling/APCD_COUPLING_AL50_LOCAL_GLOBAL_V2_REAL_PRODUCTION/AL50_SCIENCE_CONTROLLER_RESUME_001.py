from pathlib import Path
import json,sys,subprocess,sqlite3,datetime,os,traceback,time,hashlib
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');CLI=Path(r'C:\Users\DELL\anaconda3\python.exe');SCIPY=Path(r'N:\anaconda_envs\RCP_LCP\python.exe');RUNNER=P/'minimal_batch_runner_v3.1_final.py'
sys.stdout=open(D/'RESUME_001_CONTROLLER_STDOUT.log','a',encoding='utf-8',buffering=1);sys.stderr=open(D/'RESUME_001_CONTROLLER_STDERR.log','a',encoding='utf-8',buffering=1)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(p,v):
 p=Path(p);tmp=p.with_suffix('.atomic.tmp');tmp.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(tmp,p)
def put(n,v):atomic(D/n,v)
package=read(B/'AL50_FAST_PRODUCTION_MANIFEST_V2.json');authority=read(D/'REAL_EXECUTION_AUTHORITY.json');assert authority['max_entries']==50 and len(package['cases'])==50
cases={c['case_id']:c for c in package['cases']};batches={c['case_id']:c for c in package['runner_batches']};ids={c['external_execution_id'] for c in cases.values()}
package['canary_first_two']=authority['first_two']; package['execution_order']=authority['first_two']+[x for x in package['execution_order'] if x not in authority['first_two']]
protected=read(D/'PROTECTED_LEDGER_SNAPSHOTS.json'); old_snapshots={p['path']:Path(p['path']).read_bytes() for p in protected}
sys.path.insert(0,str(P));import shared_resource_gate as resource
policy=read(P/'shared_resource_policy.json')
def canonical():
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row
 jobs=[dict(r) for r in con.execute('select * from jobs') if r['external_execution_id'] in ids];entries=[dict(r) for r in con.execute('select * from solver_entries') if r['external_execution_id'] in ids];con.close()
 assert len(entries)<=50 and len({e['external_execution_id'] for e in entries})==len(entries)
 for e in entries:
  c=next(c for c in cases.values() if c['external_execution_id']==e['external_execution_id'])
  assert e['case_id']==c['case_id'] and e['attempt_id']==c['attempt_id'] and e['pre_fsp_sha256']==c['source_fsp_sha256'] and e['physical_contract_sha256']==c['physical_contract_sha256'] and e['execution_mode']=='REAL'
 return jobs,entries
ledger=read(D/'AL50_SCIENCE_LEDGER.json');assert ledger['maximum_entries']==50 and ledger['entered']==ledger['labels_valid']==2
def sync():
 jobs,entries=canonical();assert all(Path(p).read_bytes()==v for p,v in old_snapshots.items()),'protected scientificledger changed; HOLD'
 for e in entries:ledger['cases'][e['case_id']].update(entry_id=e['id'],runner_job_id=e['job_id'],solver_entered=True,entered_at=e['entered_at'])
 ledger.update(entered=len(entries),remaining=50-len(entries),labels_valid=sum(c['labels_valid'] for c in ledger['cases'].values()),updated_utc=now());put('AL50_SCIENCE_LEDGER.json',ledger);return jobs,entries
def cli(args,outprefix):
 with (D/(outprefix+'_STDOUT.log')).open('w',encoding='utf-8') as out,(D/(outprefix+'_STDERR.log')).open('w',encoding='utf-8') as err:
  child=subprocess.Popen([str(CLI),str(RUNNER),*args],cwd=str(P),stdout=out,stderr=err)
  put(outprefix+'_PROCESS.json',dict(pid=child.pid,started_utc=now(),args=args))
  import psutil
  info=read(D/(outprefix+'_PROCESS.json'));info['create_time']=psutil.Process(child.pid).create_time();put(outprefix+'_PROCESS.json',info)
  while child.poll() is None:
   if outprefix.endswith('_RUN'):sync()
   time.sleep(3)
  return child.returncode
lock=D/'AL50_SCIENCE_CONTROLLER_RESUME_001_EXCLUSIVE.lock';fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,json.dumps({'pid':os.getpid(),'utc':now()}).encode());os.close(fd)
put('CONTROLLER_STATE.json',dict(state='STARTING',pid=os.getpid(),utc=now(),authorized50=True));initial_jobs,initial_entries=canonical();assert len(initial_jobs)==len(initial_entries)==2
assert all(j['status']=='COMPLETED' for j in initial_jobs)
assert {e['case_id'] for e in initial_entries}==set(authority['first_two'])
for e in initial_entries:
 c=cases[e['case_id']];assert ledger['cases'][e['case_id']]['labels_valid'] and ledger['cases'][e['case_id']]['entry_id']==e['id']
 receipt=read(Path(c['science_output_directory'])/'SCIENCE_RECEIPT.json');assert receipt['entry_id']==e['id'] and receipt['labels_valid']==receipt['truth_valid']=='PASS'

assert not any(c['external_execution_id'] in set(authority['V1_superseded_denied']) for c in cases.values())
sync()
try:
 for index,cid in enumerate(package['execution_order']):
  c=cases[cid];batch=batches[cid];state=ledger['cases'][cid]
  if state.get('solver_entered'):
   assert state['labels_valid'] and state['state']=='LABELS_VALID','consumed attempt needs scientific reconciliation; never run again'
   print('SKIP_ACCEPTED_NO_REPLAY',cid,flush=True)
   continue
  if index>=2:assert all(ledger['cases'][k]['labels_valid'] for k in package['canary_first_two'])
  jobs,entries=sync();assert len(entries)<50 and not any(j['external_execution_id']==c['external_execution_id'] for j in jobs)
  assert hashlib.sha256(RUNNER.read_bytes()).hexdigest()=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7'
  req=read(batch['manifest'])['jobs'][0]['resource_requirements'];snapshot=resource.check(req,D,policy);put(cid+'_PREFLIGHT_RESOURCES.json',snapshot)
  assert not snapshot['hold_reasons'],snapshot['hold_reasons']
  state.update(state='REGISTERING',updated_utc=now());sync();rc=cli(['submit',batch['batch_name'],'--manifest',batch['manifest']],cid+'_SUBMIT');assert rc==0,('submit failed',cid,rc)
  jobs,entries=sync();j=next(j for j in jobs if j['external_execution_id']==c['external_execution_id']);assert j['status']=='PENDING' and not any(e['external_execution_id']==c['external_execution_id'] for e in entries)
  state.update(state='RUN_INVOCATION_ONCE',runner_job_id=j['id'],launch_intent_utc=now());sync();put(cid+'_RUN_INVOCATION_ONCE.json',dict(case_id=cid,external_execution_id=c['external_execution_id'],authority=str(D/'REAL_EXECUTION_AUTHORITY.json'),utc=now(),max_invocations=1))
  put('CONTROLLER_STATE.json',dict(state='SOLVING',case_id=cid,index=index+1,total=50,utc=now(),pid=os.getpid()));rc=cli(['run',batch['batch_name']],cid+'_RUN');put(cid+'_RUN_RETURN.json',dict(returncode=rc,utc=now()))
  jobs,entries=sync();je=next(j for j in jobs if j['id']==state['runner_job_id']);ee=[e for e in entries if e['external_execution_id']==c['external_execution_id']]
  assert len(ee)==1 and rc==0 and je['status']=='COMPLETED',('run result HOLD',cid,rc,je['status'],len(ee))
  state.update(state='NATIVE_COMPLETE_PENDING_SCIENCE',native_fsp=je['output_fsp_path'],native_fsp_sha256=je['output_sha256']);sync()
  put('CONTROLLER_STATE.json',dict(state='SCIENTIFIC_ACCEPTANCE',case_id=cid,index=index+1,total=50,utc=now(),pid=os.getpid()))
  with (D/(cid+'_EXTRACTION_STDOUT.log')).open('w',encoding='utf-8') as out,(D/(cid+'_EXTRACTION_STDERR.log')).open('w',encoding='utf-8') as err:
   post=subprocess.run([str(SCIPY),str(B/'al50_v2_extract_native.py'),'--case',cid],cwd=str(R),stdout=out,stderr=err)
  assert post.returncode==0,('offline extraction failure; retain evidence; never replay',cid)
  outdir=Path(c['science_output_directory']);receipt=read(outdir/'SCIENCE_RECEIPT.json');assert receipt['labels_valid']=='PASS' and receipt['truth_valid']=='PASS' and receipt['entry_id']==ee[0]['id']
  # Native extraction preserves contract-defined metrics and frozen numeric validation, no strict convergence reclassification.
  raw_files=list((outdir/'raw').glob('*_raw.json'));assert len(raw_files)==1;raw=read(raw_files[0]);metrics=raw['metrics'];assert all(metrics[n]['status']=='PASS' for n in ['order_sign','reference_plane_deembedding','lossy_gan'])
  for row in metrics['rows']:
   for key in ['R_FDTD','T_FDTD','A_FDTD','output_P_scale_IN_REF','output_incident_cell_power_W','output_transmitted_power_W']:
    value=float(row[key]);assert value==value and abs(value)!=float('inf'),('nonfinite',key)
   assert row['output_incident_cell_power_W']>0 and row['output_transmitted_power_W']>0 and row['R_FDTD']>=0 and row['T_FDTD']>=0,'illegal native power'
  state.update(state='LABELS_VALID',labels_valid=True,truth_valid=True,receipt=str(outdir/'SCIENCE_RECEIPT.json'),labels=str(outdir/'labels_609d.npz'),truth_h5=str(outdir/'truth.h5'),accepted_utc=now());sync()
  put(cid+'_SCIENCE_ACCEPTANCE.json',dict(status='PASS_ML_TRAINING_GRADE',receipt=receipt,energy_metrics={k:metrics.get(k) for k in ['max_energy_closure','order_sign','reference_plane_deembedding','lossy_gan']},energy_limit_note='frozen existing definitions; A=1-R-T algebraic closure not independent absorption; strict convergence not claimed',native_power_finite_and_nonnegative=True,protected_old_ledgers_unchanged=True))
  print('ACCEPTED',cid,ledger['entered'],ledger['labels_valid'],flush=True)
  if ledger['labels_valid'] in [16,32,50]:
   stage=ledger['labels_valid'];put('CONTROLLER_STATE.json',dict(state='ZERO_SOLVER_STAGE_EVALUATION',stage=stage,utc=now(),pid=os.getpid()))
   evaluation=D/'AL50_STAGE_EVALUATION.py'
   assert evaluation.is_file(),'Stage scientific evaluation script missing: no further entry'
   with (D/f'STAGE_{stage}_STDOUT.log').open('w',encoding='utf-8') as so,(D/f'STAGE_{stage}_STDERR.log').open('w',encoding='utf-8') as se:
    er=subprocess.run([str(SCIPY),str(evaluation),'--stage',str(stage)],cwd=str(D),stdout=so,stderr=se)
   assert er.returncode==0,('Zero-solver stage evaluation failure, no further entry',stage)
   ledger.setdefault('completed_evaluation_stages',[]).append(stage);sync()
 put('CONTROLLER_STATE.json',dict(state='PRODUCTION_COMPLETE_PENDING_ML',utc=now(),entered=ledger['entered'],labels_valid=ledger['labels_valid'],pid=os.getpid()))
except Exception:
 err=traceback.format_exc();put('PRODUCTION_HOLD.json',dict(utc=now(),error=err,case_id=locals().get('cid'),no_replay=True));
 try:sync()
 except Exception:pass
 put('CONTROLLER_STATE.json',dict(state='HOLD',case_id=locals().get('cid'),utc=now(),error=err,pid=os.getpid()));print(err,flush=True)
finally:
 put('CONTROLLER_EXIT.json',dict(utc=now(),pid=os.getpid(),lock_retained_for_forensic=True))
