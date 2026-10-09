import json,subprocess,sys,hashlib,datetime
from pathlib import Path
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1')
first=runtime/'detached_fixture'
failure={'verdict':'FAIL','scope':'ordinary DETACHED_PROCESS from SSH launcher','evidence':'launcher exited; worker PID no longer present, no started/completed receipt and empty log','root_cause':'Not proven; SSH-associated job lifetime is a candidate','science_entries':0,'original_launch_receipt':json.loads((first/'launch_receipt.json').read_text())}
out=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2/reports/native_acceptance_v1')
(out/'ssh_plain_detach_failed.json').write_text(json.dumps(failure,indent=2),encoding='utf-8')
root=runtime/'detached_fixture_wmi';root.mkdir(exist_ok=True)
body=(first/'worker.py').read_text()
body=body.replace("root=Path(__file__).parent\n", "root=Path(__file__).parent\nsys.stdout=(root/'worker.log').open('a',encoding='utf-8',buffering=1);sys.stderr=sys.stdout\n")
body=body.replace('OFFLINE_SSH_DISCONNECT_ACCEPTANCE','OFFLINE_SSH_DISCONNECT_WMI_ACCEPTANCE')
script=root/'worker.py';assert not script.exists();script.write_text(body,encoding='utf-8',newline='\n')
command='"'+sys.executable+'" "'+str(script)+'"'
ps="$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}; $result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine="+"'"+command.replace("'","''")+"'"+";ProcessStartupInformation=$startup}; $result | Select-Object ReturnValue,ProcessId | ConvertTo-Json -Compress"
x=subprocess.run(['powershell','-NoProfile','-Command',ps],capture_output=True,check=True)
broker=json.loads(x.stdout);assert broker['ReturnValue']==0,broker
receipt={'pid':broker['ProcessId'],'launcher_pid':__import__('os').getpid(),'broker':'Win32_Process.Create via WMI service','broker_result':broker,'worker_path':str(script),'worker_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'creationflags':'WMI broker with ShowWindow=0','stdio':'worker opens durable log; no SSH pipe','scientific_invocations':0,'scheduler_modified':False,'logout_or_reboot_tested':False,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(root/'launch_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WMI_FIXTURE_BROKER',receipt)
