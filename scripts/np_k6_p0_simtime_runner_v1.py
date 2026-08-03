import argparse, hashlib, json, os, shutil, time, traceback
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi

ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
STAGE=ROOT/'outputs/np_k6_p0_simulation_time_extension_control_v1'
CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1'
CDIR=STAGE/'cases'/CASE
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def atomic(p,obj):
 p=Path(p); tmp=p.with_name(p.name+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,default=str),encoding='utf-8'); tmp.replace(p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--task-name',default=''); args=ap.parse_args()
 c=json.loads((CDIR/'setup_contract.json').read_text(encoding='utf-8-sig')); lp=CDIR/'attempt_ledger.json'; l=json.loads(lp.read_text(encoding='utf-8-sig'))
 run=STAGE/'runtime_runs'/CASE/'attempt_001'; run.mkdir(parents=True,exist_ok=True); copy=run/f'{CASE}_attempt_001_run.fsp'; post=run/f'{CASE}_attempt_001_post.fsp'; status=run/'controller_status.json'; events=run/'controller_events.jsonl'
 src=Path(c['source_prefsp_path'])
 if l.get('entered') or l.get('run_invocation_count',0)!=0 or post.exists(): raise RuntimeError('refusing repeat attempt')
 if sha(src)!=c['source_prefsp_sha256']: raise RuntimeError('setup SHA mismatch')
 shutil.copy2(src,copy)
 if sha(copy)!=c['source_prefsp_sha256']: raise RuntimeError('run copy SHA mismatch')
 def event(state,**extra):
  v={'case_id':CASE,'attempt_id':'attempt_001','state':state,'timestamp_utc':now(),'pid':os.getpid()}; v.update(extra); atomic(status,v); events.open('a',encoding='utf-8').write(json.dumps(v,sort_keys=True)+'\n'); return v
 event('controller_started',source_prefsp_sha256=sha(src),run_copy_sha256=sha(copy),task_name=args.task_name or None)
 l.update({'entered':True,'run_invocation_count':1,'solver_entered_timestamp_utc':now(),'controller_started':True,'scheduler_task_name':args.task_name or None,'run_copy_path':str(copy),'run_copy_sha256':sha(copy)})
 atomic(lp,l); atomic(run/'entered_ledger.json',l)
 fd=None
 try:
  fd=lumapi.FDTD(str(copy),hide=True); l['prefsp_opened']=True; atomic(lp,l); atomic(run/'entered_ledger.json',l); event('prefsp_opened')
  fd.run(); l['engine_completed']=True; atomic(lp,l); atomic(run/'entered_ledger.json',l); event('engine_completed')
  fd.save(str(post)); last=-1; stable=False
  for _ in range(180):
   if post.exists() and post.stat().st_size>0:
    size=post.stat().st_size
    if size==last: stable=True; break
    last=size
   time.sleep(1)
  if not stable: raise RuntimeError('post FSP did not stabilize')
  ps=sha(post); l.update({'post_saved':True,'post_fsp_path':str(post),'post_fsp_sha256':ps}); atomic(lp,l); atomic(run/'entered_ledger.json',l); event('post_fsp_saved',post_fsp_sha256=ps,post_fsp_size_bytes=post.stat().st_size)
 except Exception as e:
  l.update({'failure':repr(e),'failure_timestamp_utc':now()}); atomic(lp,l); atomic(run/'entered_ledger.json',l); event('controller_failed',error=repr(e)); raise
 finally:
  if fd is not None: fd.close()
 l['controller_returned']=True; atomic(lp,l); atomic(run/'entered_ledger.json',l); event('controller_returned'); print(json.dumps(l,indent=2,sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception: traceback.print_exc(); raise
