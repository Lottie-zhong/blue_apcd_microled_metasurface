import sys,json,os,subprocess,traceback
from pathlib import Path
v=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2');sys.path.insert(0,str(v))
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1');cfg=json.loads((runtime/'acceptance_config.json').read_text())
from apcd_gpu_v2.native_readonly import native_session,pinned_module
from apcd_gpu_v2.processes import identity
from apcd_gpu_v2.artifacts import sha256
sys.path.insert(0,str(Path(cfg['lumapi_path']).parent));os.environ['ANSYS_LICENSING_DESKTOP_PORT_RANGE']='6200:6299';os.environ['TEMP']=str(runtime/'api_temp');os.environ['TMP']=os.environ['TEMP']
lum=pinned_module(cfg['lumapi_path'],cfg['lumapi_sha256'],'lumapi');receipt={'worker_identity':identity(),'guard_source_sha256':sha256(v/'apcd_gpu_v2/native_readonly.py'),'native_session':{}}
try:
 with native_session(lum.FDTD,{cfg['g027_copy']:cfg['g027_source_sha256']},receipt['native_session']) as fd:
  fd.load(cfg['g027_copy'])
  pids=[x['pid'] for x in receipt['native_session']['opened_children']]
  ps="$ids=@("+','.join(map(str,pids+[os.getpid()]))+"); @(Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in $ids} | ForEach-Object {$o=Invoke-CimMethod -InputObject $_ -MethodName GetOwner; [pscustomobject]@{PID=$_.ProcessId;CreationDate=$_.CreationDate.ToUniversalTime().ToString('o');ParentPID=$_.ParentProcessId;CommandLine=$_.CommandLine;SessionId=$_.SessionId;Owner=($o.Domain+'\\'+$o.User)}}) | ConvertTo-Json -Compress"
  x=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,check=True);receipt['actual_cim_identity']=json.loads(x.stdout)
  raise RuntimeError('CONTROLLED_NATIVE_LOAD_ONLY_READ_EXCEPTION')
except RuntimeError as exc:
 assert str(exc)=='CONTROLLED_NATIVE_LOAD_ONLY_READ_EXCEPTION';receipt['expected_error']=str(exc)
assert receipt['native_session']['close_called'] and not receipt['native_session']['after_children']
assert sha256(cfg['g027_copy'])==cfg['g027_source_sha256']==sha256(cfg['g027_source'])
receipt['verdict']='PASS';receipt['native_pair_unchanged']=True;receipt['scientific_solver_invocations']=0
(v/'reports/native_acceptance_v1/real_native_exception_close.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('REAL_EXCEPTION_CLOSE',receipt)
