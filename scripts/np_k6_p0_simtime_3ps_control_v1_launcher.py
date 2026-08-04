import hashlib, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
EV=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1'
RUNTIME=ROOT/'outputs/np_k6_p0_simtime_3ps_control_v1_runtime'
CASE='RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1'; ATTEMPT='attempt_001'
RUN=RUNTIME/'runtime_runs'/CASE/ATTEMPT
LEDGER=EV/'attempt_ledger.json'; RUNNER=ROOT/'scripts/np_k6_p0_simtime_3ps_control_v1_runner.py'
PID=RUNTIME/'controller.pid.json'; MANIFEST=RUNTIME/'launcher_manifest.json'; STDOUT=RUNTIME/'controller.stdout.log'; STDERR=RUNTIME/'controller.stderr.log'
def now(): return datetime.now(timezone.utc).isoformat()
def atomic(p,o):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8'); t.replace(p)
def load(p):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except:return {}
def alive(pid):
 try: os.kill(int(pid),0); return True
 except:return False
if load(LEDGER).get('entered') or load(LEDGER).get('run_invocation_count',0)!=0: raise RuntimeError('3 ps ledger already entered')
if load(MANIFEST).get('launch_count',0)>0: raise RuntimeError('3 ps launcher already consumed')
if PID.exists() and alive(load(PID).get('pid')): raise RuntimeError('3 ps controller already alive')
RUNTIME.mkdir(parents=True,exist_ok=True); RUN.mkdir(parents=True,exist_ok=True)
out=STDOUT.open('ab'); err=STDERR.open('ab')
flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'CREATE_BREAKAWAY_FROM_JOB',0)
started=now(); p=subprocess.Popen([r'N:\anaconda_envs\RCP_LCP\python.exe',str(RUNNER)],cwd=str(ROOT),stdout=out,stderr=err,creationflags=flags,close_fds=True); out.close(); err.close()
atomic(PID,{'pid':p.pid,'parent_pid':os.getpid(),'start_timestamp_utc':started,'case_id':CASE,'attempt_id':ATTEMPT,'interactive_session_dependency':False})
atomic(MANIFEST,{'schema_version':'np_k6_p0_simtime_3ps_breakaway_launcher_v1','case_id':CASE,'attempt_id':ATTEMPT,'launch_count':1,'pid':p.pid,'python_executable':r'N:\anaconda_envs\RCP_LCP\python.exe','runner':str(RUNNER),'worktree':str(ROOT),'runtime_root':str(RUNTIME),'stdout_path':str(STDOUT),'stderr_path':str(STDERR),'interactive_session_dependency':False,'automatic_retry':False,'controller_timeout_kill':False,'solver_call_budget':1,'start_timestamp_utc':started})
print(json.dumps({'state':'3PS_STARTED','pid':p.pid,'case_id':CASE,'attempt_id':ATTEMPT,'stdout':str(STDOUT),'stderr':str(STDERR)},indent=2))
