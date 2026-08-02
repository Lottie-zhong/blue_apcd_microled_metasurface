import argparse,json,hashlib,shutil,os,sys,time,traceback
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,r'N:\Program Files\ANSYS Inc\v251\Lumerical\api\python')
import lumapi
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,d):
 p=Path(p); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(d,indent=2,sort_keys=True,default=str),encoding='utf-8'); t.replace(p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True); a=ap.parse_args(); m=json.loads(Path(a.manifest).read_text(encoding='utf-8'))
 run=Path(m['run_dir']); run.mkdir(parents=True,exist_ok=True); ledger=run/'entered_ledger.json'; status=run/'controller_status.json'; events=run/'controller_events.jsonl'; source=Path(m['source_prefsp_path']); copy=Path(m['run_copy_path']); post=Path(m['post_fsp_path'])
 def event(state,**kw):
  d={'state':state,'timestamp_utc':now(),'pid':os.getpid()};d.update(kw); atomic(status,d); events.open('a',encoding='utf-8').write(json.dumps(d,sort_keys=True)+'\n'); return d
 l=json.loads(ledger.read_text(encoding='utf-8'))
 if l.get('entered') or l.get('run_invocation_count',0)!=0 or post.exists(): raise RuntimeError('refusing repeat attempt')
 if sha(source)!=m['source_prefsp_sha256']: raise RuntimeError('source SHA mismatch')
 shutil.copy2(source,copy)
 if sha(copy)!=m['source_prefsp_sha256']: raise RuntimeError('run copy SHA mismatch')
 event('controller_started',source_prefsp_sha256=sha(source),run_copy_sha256=sha(copy))
 l.update({'entered':True,'run_invocation_count':1,'solver_authorized':True,'solver_entered_timestamp_utc':now(),'controller_started':True}); atomic(ledger,l)
 f=None
 try:
  f=lumapi.FDTD(str(copy),hide=True); event('prefsp_opened'); l['prefsp_opened']=True; atomic(ledger,l)
  f.run(); event('engine_completed'); l['engine_completed']=True; atomic(ledger,l)
  f.save(str(post));
  for _ in range(120):
   if post.exists() and post.stat().st_size>0: break
   time.sleep(1)
  ph=sha(post); event('post_fsp_saved',post_fsp_sha256=ph); l.update({'post_saved':True,'post_fsp_sha256':ph}); atomic(ledger,l)
 finally:
  if f is not None: f.close()
 l['controller_returned']=True; atomic(ledger,l); event('controller_returned'); print(json.dumps(l))
if __name__=='__main__':
 try: main()
 except Exception as e:
  print('RUNNER_FAILED',repr(e),file=sys.stderr); traceback.print_exc(); raise
