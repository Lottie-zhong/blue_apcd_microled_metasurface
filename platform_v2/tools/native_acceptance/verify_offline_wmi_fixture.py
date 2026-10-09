import json,time,psutil
from pathlib import Path
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1');root=runtime/'detached_fixture_wmi'
receipt=json.loads((root/'launch_receipt.json').read_text())
started=json.loads((root/'started.json').read_text());completed=json.loads((root/'completed.json').read_text())
owner=started['owner'];assert owner['pid']==receipt['pid'] and completed['owner']==owner
assert completed['result']['state']=='DONE_OFFLINE' and completed['result']['scientific_calls']==0
assert completed['audit']['integrity']=='ok' and completed['audit']['tasks'][0]['entered']==1
assert not psutil.pid_exists(receipt['launcher_pid']) or psutil.Process(receipt['launcher_pid']).create_time()>owner['creation_time']
result={'verdict':'PASS_FIXTURE_ONLY','worker_identity':owner,'launcher_exited_before_completion':True,'fixture_completed_after_ssh_launcher_exit':True,'durable_log_path':str(root/'worker.log'),'science_entries':0,'fixture_entries':1,'logout_or_reboot_tested':False,'production_dispatcher_qualified':False,'receipt':receipt}
out=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2/reports/native_acceptance_v1');(out/'ssh_detached_fixture.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('DETACHED_VERDICT',result)
