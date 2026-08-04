import argparse, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1'); STAGE=ROOT/'outputs'/'np_k6_p0_runtime_launcher_recovery_setup_v1'; MANIFEST=STAGE/'launcher_manifest.json'; PIDFILE=STAGE/'dummy.pid.json'; HEARTBEAT=STAGE/'dummy.heartbeat.json'; STATUS=STAGE/'launcher_status.json'; STDOUT=STAGE/'dummy.stdout.log'; STDERR=STAGE/'dummy.stderr.log'; COMPLETED=STAGE/'dummy.completed.json'; WORKER=ROOT/'scripts'/'np_k6_p0_dummy_worker_v1.py'; RECOVERY_STAGE=ROOT/'outputs'/'np_k6_p0_simtime_2ps_recovery_v2_runtime'; RECOVERY_MANIFEST=RECOVERY_STAGE/'launcher_manifest.json'; RECOVERY_PID=RECOVERY_STAGE/'recovery.pid.json'; RECOVERY_STATUS=RECOVERY_STAGE/'launcher_status.json'; RECOVERY_STDOUT=RECOVERY_STAGE/'recovery.stdout.log'; RECOVERY_STDERR=RECOVERY_STAGE/'recovery.stderr.log'; RECOVERY_HEARTBEAT=RECOVERY_STAGE/'runtime_runs'/'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2'/'attempt_001'/'heartbeat.json'; RECOVERY_RUNNER=ROOT/'scripts'/'np_k6_p0_simtime_recovery_v2_runner.py'; RECOVERY_LEDGER=ROOT/'outputs'/'np_k6_p0_simtime_2ps_recovery_v2_setup'/'attempt_ledger.json'; RECOVERY_SETUP=ROOT/'outputs'/'np_k6_p0_simtime_2ps_recovery_v2_setup'/'runtime_prefsp'/'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2.fsp'
def now():return datetime.now(timezone.utc).isoformat()
def atomic(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(o,indent=2,sort_keys=True,default=str),encoding='utf-8');t.replace(p)
def load(p,default=None):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except Exception:return default
def ensure():
 if not MANIFEST.exists():atomic(MANIFEST,{'schema_version':'np_k6_p0_runtime_launcher_v1','worktree':str(ROOT),'python_executable':r'N:\anaconda_envs\RCP_LCP\python.exe','worker_script':str(WORKER),'case_manifest':str(ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_setup'/'recovery_case_manifest.json'),'stdout_path':str(STDOUT),'stderr_path':str(STDERR),'pid_path':str(PIDFILE),'heartbeat_path':str(HEARTBEAT),'start_timestamp_utc':None,'entered':False,'run_invocation_count':0,'automatic_retry':False,'execution_time_limit':'PT0S','interactive_session_dependency':False,'solver_calls':0})
 return load(MANIFEST)
def write_status(state,**x):
 o={'state':state,'timestamp_utc':now(),'run_invocation_count':0,'entered':False,'automatic_retry':False};o.update(x);atomic(STATUS,o);return o
def pid_alive(pid):
 try:
  os.kill(int(pid),0); return True
 except Exception: return False
def start_recovery():
 RECOVERY_STAGE.mkdir(parents=True,exist_ok=True); m=load(RECOVERY_MANIFEST,{}) or {}; l=load(RECOVERY_LEDGER,{}) or {}
 if m.get('launch_count',0)>0: raise RuntimeError('recovery launcher already consumed; repeat refused')
 if l.get('entered') or l.get('run_invocation_count',0)!=0: raise RuntimeError('recovery ledger already entered')
 if not RECOVERY_SETUP.exists(): raise RuntimeError('recovery setup missing')
 if RECOVERY_PID.exists() and pid_alive((load(RECOVERY_PID,{}) or {}).get('pid')): raise RuntimeError('recovery PID alive; duplicate start refused')
 launch_id='NP_K6_P0_RECOVERY_V2_001'; started=now(); out=RECOVERY_STDOUT.open('ab'); err=RECOVERY_STDERR.open('ab'); flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'CREATE_BREAKAWAY_FROM_JOB',0)
 p=subprocess.Popen([r'N:\anaconda_envs\RCP_LCP\python.exe',str(RECOVERY_RUNNER),'--launch-id',launch_id],cwd=str(ROOT),stdout=out,stderr=err,creationflags=flags,close_fds=True); out.close(); err.close()
 atomic(RECOVERY_PID,{'pid':p.pid,'parent_pid':os.getpid(),'start_timestamp_utc':started,'interactive_session_dependency':False,'case_id':'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2','attempt_id':'attempt_001'})
 m={'schema_version':'np_k6_p0_recovery_launcher_v2','case_id':'RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2','attempt_id':'attempt_001','launch_id':launch_id,'launch_count':1,'pid':p.pid,'python_executable':r'N:\anaconda_envs\RCP_LCP\python.exe','runner':str(RECOVERY_RUNNER),'worktree':str(ROOT),'setup_path':str(RECOVERY_SETUP),'stdout_path':str(RECOVERY_STDOUT),'stderr_path':str(RECOVERY_STDERR),'heartbeat_path':str(RECOVERY_HEARTBEAT),'interactive_session_dependency':False,'automatic_retry':False,'controller_timeout_kill':False,'solver_launch_authorized':True,'solver_call_budget':1,'entered_before_run_required':True,'start_timestamp_utc':started}; atomic(RECOVERY_MANIFEST,m); atomic(RECOVERY_STATUS,{'state':'RECOVERY_STARTED','timestamp_utc':now(),'pid':p.pid,'launch_id':launch_id,'case_id':m['case_id'],'attempt_id':'attempt_001','entered':False,'run_invocation_count':0,'post_save_allowed':False}); print(json.dumps({'state':'RECOVERY_STARTED','pid':p.pid,'launch_id':launch_id,'stdout_path':str(RECOVERY_STDOUT),'stderr_path':str(RECOVERY_STDERR),'heartbeat_path':str(RECOVERY_HEARTBEAT)},indent=2)); return 0
def recovery_status():
 m=load(RECOVERY_MANIFEST); l=load(RECOVERY_LEDGER); pid=load(RECOVERY_PID); hb=load(RECOVERY_HEARTBEAT); st=load(RECOVERY_STATUS); alive=pid_alive((pid or {}).get('pid')) if pid else False; o={'state':'RECOVERY_STATUS_ONLY','timestamp_utc':now(),'process_alive':alive,'pid':pid,'heartbeat':hb,'controller_status':st,'ledger':l,'launch_manifest':m,'post_save_allowed':False}; atomic(RECOVERY_STATUS,o); print(json.dumps(o,indent=2,default=str)); return 0
def start(duration):
 m=ensure()
 if m.get('entered') or m.get('run_invocation_count',0)!=0 or m.get('solver_calls',0)!=0:raise RuntimeError('zero-run launcher invariant failed')
 if PIDFILE.exists():
  old=load(PIDFILE,{}) or {}
  if pid_alive(old.get('pid')): raise RuntimeError('duplicate dummy start refused')
  PIDFILE.replace(STAGE/(f"dummy.stale.{old.get('pid','unknown')}.pid.json"))
 for stale in (HEARTBEAT, COMPLETED):
  if stale.exists(): stale.replace(STAGE/(stale.name+'.stale'))
 if duration<60:raise ValueError('duration must be >=60s')
 STAGE.mkdir(parents=True,exist_ok=True);start_utc=now();out=STDOUT.open('ab');err=STDERR.open('ab');flags=getattr(subprocess,'DETACHED_PROCESS',0)|getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0)|getattr(subprocess,'CREATE_BREAKAWAY_FROM_JOB',0)
 p=subprocess.Popen([m['python_executable'],str(WORKER),str(HEARTBEAT),str(COMPLETED),str(PIDFILE),str(duration)],cwd=str(ROOT),stdout=out,stderr=err,creationflags=flags,close_fds=True);out.close();err.close()
 atomic(PIDFILE,{'pid':p.pid,'parent_pid':os.getpid(),'start_timestamp_utc':start_utc,'duration_s':duration,'interactive_session_dependency':False});m.update({'start_timestamp_utc':start_utc,'last_dummy_pid':p.pid,'last_dummy_duration_s':duration,'dummy_start_count':m.get('dummy_start_count',0)+1,'entered':False,'run_invocation_count':0,'automatic_retry':False,'solver_calls':0});atomic(MANIFEST,m);o=write_status('DUMMY_STARTED',pid=p.pid,duration_s=duration,stdout_path=str(STDOUT),stderr_path=str(STDERR),heartbeat_path=str(HEARTBEAT));print(json.dumps(o,indent=2));return 0
def status():
 m=ensure();o=write_status('STATUS_ONLY',pid=load(PIDFILE),heartbeat=load(HEARTBEAT),completed=load(COMPLETED),manifest=m,post_save_allowed=False);print(json.dumps(o,indent=2));return 0
def recover(mode):
 m=ensure();o=write_status(mode.upper(),manifest=m,pid=load(PIDFILE),completed=load(COMPLETED),post_save_allowed=False);print(json.dumps(o,indent=2));return 0
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['dummy-start','status-only','recover-controller-only','recover-post-save-only','recovery-start','recovery-status'],required=True);ap.add_argument('--duration',type=float,default=65);a=ap.parse_args();return start(a.duration) if a.mode=='dummy-start' else status() if a.mode=='status-only' else start_recovery() if a.mode=='recovery-start' else recovery_status() if a.mode=='recovery-status' else recover(a.mode)
if __name__=='__main__':raise SystemExit(main())
