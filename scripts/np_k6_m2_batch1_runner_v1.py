import argparse, hashlib, json, os, shutil, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs/np_k6_m2_batch1_hf_acquisition_v1'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def atomic(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); t.replace(p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--case',required=True); ap.add_argument('--task-name',default=''); args=ap.parse_args(); case=args.case; cdir=STAGE/'cases'/case; contract=json.loads((cdir/'setup_contract.json').read_text(encoding='utf-8-sig')); lp=cdir/'attempt_ledger.json'; ledger=json.loads(lp.read_text(encoding='utf-8-sig')); run=STAGE/'runtime_runs'/case/'attempt_001'; run.mkdir(parents=True,exist_ok=True); runcopy=run/f'{case}_attempt_001_run.fsp'; post=run/f'{case}_attempt_001_post.fsp'; status=run/'controller_status.json'; events=run/'controller_events.jsonl'; hb=run/'heartbeat.json'; src=Path(contract['source_prefsp_path'])
 if ledger.get('entered') or ledger.get('run_invocation_count',0)!=0 or post.exists() or ledger.get('case_id') != case: raise RuntimeError('official case repeat or identity refused')
 if sha(src)!=contract['source_prefsp_sha256']: raise RuntimeError('V2 source SHA mismatch')
 def event(state,**extra):
  x={'case_id':case,'attempt_id':'attempt_001','state':state,'timestamp_utc':now(),'controller_pid':os.getpid()}; x.update(extra); atomic(status,x); events.open('a',encoding='utf-8').write(json.dumps(x,sort_keys=True)+'\n')
 shutil.copy2(src,runcopy)
 if sha(runcopy)!=contract['source_prefsp_sha256']: raise RuntimeError('V2 run-copy SHA mismatch')
 event('controller_started',source_prefsp_path=str(src),source_prefsp_sha256=sha(src),run_copy_path=str(runcopy),run_copy_sha256=sha(runcopy),task_name=args.task_name)
 ledger.update({'controller_started':True,'controller_pid':os.getpid(),'run_copy_path':str(runcopy),'run_copy_sha256':sha(runcopy),'scheduler_task_name':args.task_name,'controller_started_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger)
 fd=None
 try:
  fd=lumapi.FDTD(str(runcopy),hide=True); ledger.update({'prefsp_opened':True,'prefsp_opened_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('prefsp_opened')
  ledger.update({'entered':True,'run_invocation_count':1,'solver_entered':True,'solver_authorized':True,'setup_only':False,'provisional_hf_label':True, 'active_learning_batch':1, 'batch_id':'NP_K6_M2_BATCH1','training_label':False,'candidate_performance_label':False,'solver_entered_timestamp_utc':now(),'entered_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('solver_entered'); atomic(hb,{'case_id':case,'attempt_id':'attempt_001','controller_pid':os.getpid(),'heartbeat_utc':now(),'state':'solver_entered'})
  fd.run()
  ledger.update({'engine_completed':True,'engine_completed_timestamp_utc':now(),'engine_exit_code':0}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('engine_completed'); atomic(hb,{'case_id':case,'attempt_id':'attempt_001','controller_pid':os.getpid(),'heartbeat_utc':now(),'state':'engine_completed'})
  fd.save(str(post)); last=-1; stable=False
  for _ in range(900):
   if post.exists() and post.stat().st_size>0:
    sz=post.stat().st_size
    if sz==last: stable=True; break
    last=sz
   time.sleep(1)
  if not stable: raise RuntimeError('V2 post did not stabilize')
  ph=sha(post); ledger.update({'post_saved':True,'post_save_completed':True,'post_fsp_path':str(post),'post_fsp_sha256':ph,'post_fsp_size_bytes':post.stat().st_size,'post_saved_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('post_fsp_saved',post_fsp_sha256=ph,post_fsp_size_bytes=post.stat().st_size)
 except Exception as exc:
  ledger.update({'failure':repr(exc),'failure_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('controller_failed',error=repr(exc)); raise
 finally:
  if fd is not None: fd.close()
 if ledger.get('post_saved'):
  ledger.update({'controller_returned':True,'controller_returned_timestamp_utc':now()}); atomic(lp,ledger); atomic(run/'entered_ledger.json',ledger); event('controller_returned'); atomic(run/'completion.json',{'case_id':case,'attempt_id':'attempt_001','post_fsp_sha256':ledger['post_fsp_sha256'],'completed_utc':now()})
 print(json.dumps(ledger,indent=2,sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception: traceback.print_exc(); raise
