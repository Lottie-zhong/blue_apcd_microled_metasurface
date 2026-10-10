import os,sys,json,subprocess,hashlib,datetime,sqlite3,psutil
from pathlib import Path
rt=Path(r'D:\apcd_runtime\gpu_v2_unknown_closure_20261010_v1');rt.mkdir(exist_ok=True)
v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1');r=Path(r'D:\apcd_runtime\gpu_production_runner_v1');c=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');report=c/'reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1'
old=json.loads((v/'platform_v2/reports/native_acceptance_v1/p0_owner_isolation.json').read_text(encoding='utf-8'));targets=[x for x in old['current_processes'] if x['classification']=='UNKNOWN'];assert len(targets)==16
label='snapshot_2'
def run(args,cwd=None,timeout=75):
 try:
  p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=timeout);return {'returncode':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace').strip(),'stderr':p.stderr.decode('utf-8',errors='replace').strip()}
 except subprocess.TimeoutExpired as e:return {'error':'TIMEOUT','stdout':str(e.stdout)[:500]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def attempt(fn):
 try:return {'status':'READ','value':fn()}
 except (psutil.AccessDenied,psutil.NoSuchProcess,OSError) as e:return {'status':type(e).__name__,'error':str(e)}
git={str(p):{str(a):run(['git',*a],p) for a in [['status','--short'],['branch','--show-current'],['rev-parse','HEAD'],['rev-list','--left-right','--count','HEAD...@{u}']]} for p in [v,Path(r'D:\project\worktrees\blue_apcd_gpu_production_runner_v1'),c]}
assert git[str(v)][str(['rev-parse','HEAD'])]['stdout']=='05fa4f6d51535386635fee0a6b0cedcf496faa49'
ps=r'''$ErrorActionPreference='Stop';[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$procs=@(Get-CimInstance Win32_Process|ForEach-Object{$p=$_;$o=Invoke-CimMethod -InputObject $p -MethodName GetOwner -ErrorAction SilentlyContinue;[pscustomobject]@{PID=$p.ProcessId;PPID=$p.ParentProcessId;CreationDate=if($p.CreationDate){$p.CreationDate.ToUniversalTime().ToString('o')}else{$null};Image=$p.Name;CommandLine=$p.CommandLine;SessionId=$p.SessionId;ExecutablePath=$p.ExecutablePath;Owner=($o.Domain+'\'+$o.User);OwnerReturnValue=$o.ReturnValue}})
$svc=New-Object -ComObject Schedule.Service;$svc.Connect();$running=@($svc.GetRunningTasks(1)|ForEach-Object{[pscustomobject]@{Name=$_.Name;Path=$_.Path;InstanceGuid=$_.InstanceGuid;EnginePID=$_.EnginePID;CurrentAction=$_.CurrentAction;State=$_.State}});$tasks=@($svc.GetFolder('\').GetTasks(1)|Where-Object{$_.Name -match 'APCD'}|ForEach-Object{[pscustomobject]@{Name=$_.Name;Enabled=$_.Enabled;State=$_.State;Xml=$_.Xml;LastRunTime=$_.LastRunTime.ToString('o');LastTaskResult=$_.LastTaskResult}})
$logs=@('Microsoft-Windows-TaskScheduler/Operational','Security','Microsoft-Windows-Sysmon/Operational'|ForEach-Object{ $logName=$_;try{$l=Get-WinEvent -ListLog $logName -ErrorAction Stop;[pscustomobject]@{Name=$logName;Status='READ';Enabled=$l.IsEnabled;RecordCount=$l.RecordCount;LogMode=$l.LogMode.ToString()}}catch{[pscustomobject]@{Name=$logName;Status='ERROR';Error=$_.Exception.Message}}})
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
ConvertTo-Json -InputObject ([pscustomobject]@{HostName=$env:COMPUTERNAME;Identity=[Security.Principal.WindowsIdentity]::GetCurrent().Name;IsAdministrator=$admin;Processes=$procs;RunningTasks=$running;Tasks=$tasks;Logs=$logs}) -Depth 8 -Compress'''
raw=run(['powershell','-NoProfile','-Command',ps]);assert raw['returncode']==0,raw;cim=json.loads(raw['stdout']);assert cim['HostName']=='DESKTOP-NNE313K'
rows=[]
for original in targets:
 row={'original_identity':{'pid':original['pid'],'creation_time':original['create_time'],'command':original.get('cmdline')},'cim':next((x for x in cim['Processes'] if x['PID']==original['pid']),None)}
 try:
  p=psutil.Process(original['pid']);created=p.create_time();row['current_creation_time']=created;row['same_identity']=abs(created-original['create_time'])<0.002
  for name,fn in [('name',p.name),('image',p.exe),('commandline',p.cmdline),('user',p.username),('ppid',p.ppid),('cwd',p.cwd),('status',p.status),('open_files',lambda:[x._asdict() for x in p.open_files()]),('connections',lambda:[{'fd':x.fd,'family':str(x.family),'type':str(x.type),'local':list(x.laddr),'remote':list(x.raddr),'status':x.status} for x in p.net_connections()]),('cpu_times',lambda:p.cpu_times()._asdict()),('memory',lambda:p.memory_info()._asdict()),('threads',p.num_threads),('handles',p.num_handles)]:row[name]=attempt(fn)
  row['ancestors']=attempt(lambda:[{'pid':q.pid,'creation_time':q.create_time(),'name':q.name(),'commandline':q.cmdline()} for q in p.parents()]);row['descendants']=attempt(lambda:[{'pid':q.pid,'creation_time':q.create_time(),'name':q.name(),'commandline':q.cmdline()} for q in p.children(recursive=True)])
  import ctypes
  from ctypes import wintypes
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE;k.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)];k.CloseHandle.argtypes=[wintypes.HANDLE]
  h=k.OpenProcess(0x1000,False,p.pid)
  if not h:row['windows_job_membership']={'status':'ERROR','winerror':ctypes.get_last_error()}
  else:
   try:
    flag=wintypes.BOOL();ok=k.IsProcessInJob(h,None,ctypes.byref(flag));row['windows_job_membership']={'status':'READ' if ok else 'ERROR','in_any_job':bool(flag.value) if ok else None,'winerror':None if ok else ctypes.get_last_error(),'job_owner_identity':'NOT_AVAILABLE_FROM_MEMBERSHIP'}
   finally:k.CloseHandle(h)
  pp=row['ppid'].get('value');row['parent_cim']=next((x for x in cim['Processes'] if x['PID']==pp),None);row['parent_psutil']=attempt(lambda:{'pid':pp,'creation_time':psutil.Process(pp).create_time(),'commandline':psutil.Process(pp).cmdline()})
 except psutil.NoSuchProcess:row['same_identity']=False;row['status']='EXITED'
 except psutil.AccessDenied as e:row['status']='AccessDenied';row['error']=str(e)
 rows.append(row)
markers={str(r/n):{'exists':(r/n).exists(),'sha256':sha(r/n) if (r/n).is_file() else None} for n in ['active_run.json','.runner.lock','scheduler_worker_v1.lock','registry.json']}
requests=[]
for p in (r/'requests/scheduled_run_one_v1').glob('*/request.json'):
 req=json.loads(p.read_text(encoding='utf-8'));requests.append({'path':str(p),'sha256':sha(p),'identity':req.get('identity'),'result_present':(p.parent/'result.json').is_file(),'claim_present':(p.parent/'claim.json').is_file()})
ledger=json.loads((report/'QUEUE_EXECUTION_LEDGER_V1.json').read_text(encoding='utf-8'));dbpath=Path(r'D:\apcd_runtime\global_fdtd_control_v3/control.sqlite3');gate={}
if dbpath.exists():
 db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
 try:gate={'admission':db.execute('SELECT new_entry_hold,control_generation,health_status FROM admission_control WHERE control_id=1').fetchall(),'global_holds':db.execute("SELECT hold_id FROM hold_lifecycle WHERE scope='GLOBAL' AND status='ACTIVE'").fetchall()}
 except Exception as e:gate={'error':repr(e)}
 finally:db.close()
known_g25=r/'runs/K6GDP2_DEV_G025/attempt_001/K6V2_G025_20261008T140327Z_454d6858';g25={str(known_g25/p):sha(known_g25/p) for p in ['run.fsp','run/run_output.h5']}
proof={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'audit_self_pid':os.getpid(),'git':git,'cim':cim,'rows':rows,'markers':markers,'requests':requests,'ledger_counters':{k:x for k,x in ledger.items() if 'count' in k or 'current' in k},'g027_ledger_entries':{k:x for k,x in ledger.items() if 'G027' in str(k)},'controller_status':json.loads((report/'CONTROLLER_STATUS_K6V2SERIAL20261009T112100Z_5F6AEEED.json').read_text(encoding='utf-8')),'global_gate':gate,'g025_truth_hashes':g25,'gpu_query':run(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),'gpu_full':run(['nvidia-smi']),'handle_tool':run(['where.exe','handle.exe']),'scientific_solver_calls':0}
(rt/(label+'.json')).write_text(json.dumps(proof,indent=2,default=str),encoding='utf-8')
print('SNAPSHOT',label,proof['utc'],'same_originals',sum(q.get('same_identity',False) for q in rows),'COUNTERS',proof['ledger_counters'],'GATE',gate)
