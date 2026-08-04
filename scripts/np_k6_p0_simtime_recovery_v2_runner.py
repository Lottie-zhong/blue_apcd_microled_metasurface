import argparse, hashlib, json, os, shutil, sys, threading, time, traceback
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, r'N:/Program Files/ANSYS Inc/v251/Lumerical/api/python')
import lumapi
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
SETUP=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_setup'
CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2'; ATTEMPT='attempt_001'
RUN=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_runtime'/'runtime_runs'/CASE/ATTEMPT
LEDGER=SETUP/'attempt_ledger.json'; SOURCE=SETUP/'runtime_prefsp'/f'{CASE}.fsp'
HEARTBEAT=RUN/'heartbeat.json'; STATUS=RUN/'controller_status.json'; EVENTS=RUN/'controller_events.jsonl'; RUNLEDGER=RUN/'entered_ledger.json'
RUN_COPY=RUN/f'{CASE}_{ATTEMPT}_run.fsp'; POST=RUN/f'{CASE}_{ATTEMPT}_post.fsp'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def atomic(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,default=str),encoding='utf-8'); t.replace(p)
def save_ledger(l): atomic(LEDGER,l); atomic(RUNLEDGER,l)
def event(state,**extra):
 v={'case_id':CASE,'attempt_id':ATTEMPT,'state':state,'timestamp_utc':now(),'controller_pid':os.getpid()}; v.update(extra); atomic(STATUS,v); EVENTS.parent.mkdir(parents=True,exist_ok=True); EVENTS.open('a',encoding='utf-8').write(json.dumps(v,sort_keys=True)+'\n'); return v
class Heartbeat:
 def __init__(self): self.stop_flag=threading.Event(); self.thread=None; self.started=time.time()
 def write(self,**extra):
  o={'case_id':CASE,'attempt_id':ATTEMPT,'controller_pid':os.getpid(),'heartbeat_utc':now(),'elapsed_s':time.time()-self.started}; o.update(extra); atomic(HEARTBEAT,o)
 def loop(self):
  while not self.stop_flag.is_set(): self.write(); self.stop_flag.wait(5)
 def start(self): self.write(state='controller_started'); self.thread=threading.Thread(target=self.loop,daemon=True); self.thread.start()
 def stop(self,**extra): self.stop_flag.set(); self.write(**extra); self.thread.join(timeout=2) if self.thread else None
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--launch-id',default=''); args=ap.parse_args()
 RUN.mkdir(parents=True,exist_ok=True); l=load(LEDGER)
 if l.get('entered') or l.get('run_invocation_count',0)!=0 or POST.exists(): raise RuntimeError('recovery-v2 repeat refused')
 if sha(SOURCE)!='76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f': raise RuntimeError('recovery setup SHA mismatch')
 if sha(SOURCE)!=l.get('source_prefsp_sha256'): raise RuntimeError('ledger/source SHA mismatch')
 shutil.copy2(SOURCE,RUN_COPY)
 if sha(RUN_COPY)!=sha(SOURCE): raise RuntimeError('run copy SHA mismatch')
 event('controller_started',launch_id=args.launch_id,source_prefsp_path=str(SOURCE),source_prefsp_sha256=sha(SOURCE),run_copy_path=str(RUN_COPY),run_copy_sha256=sha(RUN_COPY),interactive_session_dependency=False)
 fd=None; hb=Heartbeat(); started=time.time()
 try:
  fd=lumapi.FDTD(str(RUN_COPY),hide=True)
  l.update({'controller_started':True,'prefsp_opened':True,'prefsp_opened_timestamp_utc':now(),'run_copy_path':str(RUN_COPY),'run_copy_sha256':sha(RUN_COPY),'launcher_id':args.launch_id,'controller_pid':os.getpid()}); save_ledger(l); event('prefsp_opened')
  # This is the single atomic budget transition immediately before fd.run().
  l.update({'entered':True,'run_invocation_count':1,'solver_authorized':True,'solver_entered_timestamp_utc':now(),'entered_timestamp_utc':now(),'solver_call_count':1}); save_ledger(l); event('solver_entered',run_invocation_count=1); hb.start()
  fd.run()
  elapsed=time.time()-started; l.update({'engine_completed':True,'engine_completed_timestamp_utc':now(),'runtime_seconds':elapsed,'engine_exit_code':0}); save_ledger(l); event('engine_completed',runtime_seconds=elapsed); hb.stop(state='engine_completed',engine_completed=True)
  fd.save(str(POST)); stable=False; last=-1
  for _ in range(180):
   if POST.exists() and POST.stat().st_size>0:
    sz=POST.stat().st_size
    if sz==last: stable=True; break
    last=sz
   time.sleep(1)
  if not stable: raise RuntimeError('post-FSP did not stabilize')
  post_sha=sha(POST); l.update({'post_saved':True,'post_save_completed':True,'post_fsp_path':str(POST),'post_fsp_sha256':post_sha,'post_fsp_size_bytes':POST.stat().st_size,'post_saved_timestamp_utc':now()}); save_ledger(l); event('post_fsp_saved',post_fsp_sha256=post_sha,post_fsp_size_bytes=POST.stat().st_size)
 except Exception as exc:
  l.update({'failure':repr(exc),'failure_timestamp_utc':now(),'engine_exit_code':None}); save_ledger(l); event('controller_failed',error=repr(exc)); hb.stop(state='controller_failed',error=repr(exc)); raise
 finally:
  if fd is not None: fd.close()
 if l.get('post_saved'):
  l.update({'controller_completed':True,'controller_returned':True,'controller_returned_timestamp_utc':now()}); save_ledger(l); event('controller_returned',post_saved=True); atomic(RUN/'completion.json',{'case_id':CASE,'attempt_id':ATTEMPT,'exit_code':0,'completed_utc':now(),'post_fsp_sha256':l['post_fsp_sha256']}); print(json.dumps(l,indent=2,sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception: traceback.print_exc(); raise
