import os,sys,json,subprocess,hashlib,datetime,ast
from pathlib import Path
import psutil
v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1')
r=Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1')
c=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
rt=Path(r'D:\apcd_runtime\gpu_production_runner_v1')
report=c/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1'
out=v/'platform_v2/reports/native_acceptance_v1';out.mkdir(exist_ok=True)
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1');runtime.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,cwd=None):
 x=subprocess.run(args,cwd=cwd,capture_output=True,timeout=40);return {'exit':x.returncode,'stdout':x.stdout.decode('utf-8',errors='replace').strip(),'stderr':x.stderr.decode('utf-8',errors='replace').strip()}
git={str(p):{str(args):run(['git',*args],p) for args in [['status','--short'],['branch','--show-current'],['rev-parse','HEAD'],['rev-list','--left-right','--count','HEAD...@{u}']]} for p in [v,r,c]}
assert git[str(v)][str(['rev-parse','HEAD'])]['stdout']=='a6fef4aa3925dd5989d8b1e7db2f3197f45da016'
(out/'baseline_git.json').write_text(json.dumps(git,indent=2),encoding='utf-8')
print('V2 BASELINE',git[str(v)])
ps=r'''$ErrorActionPreference='Stop'
$rows=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(pythonw?\.exe|fdtd.*\.exe|powershell\.exe|sshd\.exe|taskeng\.exe|taskhostw\.exe)$'} | ForEach-Object {
 $p=$_; $o=Invoke-CimMethod -InputObject $p -MethodName GetOwner -ErrorAction SilentlyContinue
 [pscustomobject]@{PID=$p.ProcessId;ParentPID=$p.ParentProcessId;CreationDate=$p.CreationDate.ToUniversalTime().ToString('o');CommandLine=$p.CommandLine;Name=$p.Name;SessionId=$p.SessionId;ExecutablePath=$p.ExecutablePath;Owner=($o.Domain+'\'+$o.User)} })
$svc=New-Object -ComObject 'Schedule.Service';$svc.Connect()
$running=@($svc.GetRunningTasks(1) | ForEach-Object {[pscustomobject]@{Name=$_.Name;Path=$_.Path;InstanceGuid=$_.InstanceGuid;EnginePID=$_.EnginePID;CurrentAction=$_.CurrentAction;State=$_.State}})
$tasks=@($svc.GetFolder('\').GetTasks(1) | Where-Object {$_.Name -match 'APCD'} | ForEach-Object {[pscustomobject]@{Name=$_.Name;State=$_.State;Enabled=$_.Enabled;LastRunTime=$_.LastRunTime.ToString('o');LastTaskResult=$_.LastTaskResult;Xml=$_.Xml}})
ConvertTo-Json -InputObject ([pscustomobject]@{Processes=$rows;RunningTasks=$running;InstalledTasks=$tasks}) -Depth 8 -Compress
'''
x=run(['powershell','-NoProfile','-Command',ps]);assert x['exit']==0,x
cim=json.loads(x['stdout']);(runtime/'p0_full_private.json').write_text(json.dumps(cim,indent=2),encoding='utf-8')
rows=[]
for p in psutil.process_iter(['pid','ppid','create_time','exe','cmdline','name','username']):
 try:
  if p.info['pid']==os.getpid():continue
  cmd=' '.join(p.info['cmdline'] or [])
  if 'fdtd' in (p.info['name'] or '').lower() or ((p.info['name'] or '').lower().startswith('python') and ('apcd' in cmd.lower() or 'mdc_' in cmd.lower() or cmd.endswith(' -'))):
   row=dict(p.info);row['cim']=next((q for q in cim['Processes'] if q['PID']==p.pid),None)
   try:row['open_files']=[f.path for f in p.open_files()];row['connections']=[{'laddr':list(k.laddr),'raddr':list(k.raddr),'status':k.status} for k in p.net_connections()]
   except psutil.AccessDenied:row['access']='DENIED'
   ancestors=[];pp=p
   for _ in range(4):
    pp=pp.parent()
    if pp is None:break
    ancestors.append({'pid':pp.pid,'creation_time':pp.create_time(),'name':pp.name(),'cmdline':pp.cmdline()})
   row['ancestors']=ancestors
   row['classification']='UNKNOWN'
   if ('task_scheduler_v1.py' in cmd or 'serial_queue.py' in cmd or '-run' in cmd or (p.info['name'] or '').lower().startswith('fdtd-engine')):row['classification']='CONFIRMED_V1_ACTIVE' if 'gpu_runner_v1' in cmd or 'k6_v2_pipeline' in cmd else 'UNKNOWN'
   if 'mdc_complex_prior_fsp_' in cmd:
    source=Path((p.info['cmdline'] or [])[-1])
    if source.is_file():
     body=source.read_text(encoding='utf-8',errors='replace');row['source_path']=str(source);row['source_sha256']=sha(source)
     row['source_code']=body
     row['classification']='CONFIRMED_OTHER_ACTIVITY' if 'fd.run(' not in body and '.run(' not in body and 'run;' not in body else 'UNKNOWN'
   rows.append(row)
 except (psutil.NoSuchProcess,psutil.AccessDenied):pass
ledger=json.loads((report/'QUEUE_EXECUTION_LEDGER_V1.json').read_text())
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audit_pid_excluded':os.getpid(),'rows':rows,'running_tasks':cim['RunningTasks'],'installed_tasks':cim['InstalledTasks'],'markers':{n:(rt/n).exists() for n in ['active_run.json','.runner.lock','scheduler_worker_v1.lock']},'ledger':{k:z for k,z in ledger.items() if 'count' in k or 'current' in k},'controller_status':json.loads((report/'CONTROLLER_STATUS_K6V2SERIAL20261009T112100Z_5F6AEEED.json').read_text())}
(runtime/'p0_process_full.json').write_text(json.dumps(proof,indent=2,default=str),encoding='utf-8')
print('PROCESSES',json.dumps(rows,default=str)[:16000]);print('RUNNING_TASKS',json.dumps(cim['RunningTasks']));print('TASKS',[(t['Name'],t['State'],t['Enabled']) for t in cim['InstalledTasks']])
g25=rt/'runs/K6GDP2_DEV_G025/attempt_001/K6V2_G025_20261008T140327Z_454d6858'
for name in ['manifest.json','hashes.json']:
 print('G025',name,(g25/name).read_text()[:12000])
for p in (rt/'requests/scheduled_run_one_v1').glob('*/request.json'):
 doc=json.loads(p.read_text())
 if doc.get('identity',{}).get('case_id')=='K6GDP2_DEV_G027':print('G027REQUEST',str(p),doc)
print('INGEST_RECORD',(report/'INGEST_RESULT_K6GDP2_DEV_G025_V1.json').read_text())
launcher=Path(r'D:\apcd_runtime\shared_v3_backend\pw_powernorm_v1_aaaa25b53a9a3322\scripts\shared_fdtd\tools\pw_scientific_launcher.py')
calls=sorted({n.attr for n in ast.walk(ast.parse(launcher.read_text())) if isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id=='fd'})
print('LAUNCHER_FD_CALLS',calls)
print('IMPORT ROOTS',[(str(p),p.exists()) for p in [launcher.parents[2],c/'scripts',c/'scripts/coupling_ml']])
