import json,os,psutil,hashlib,datetime,subprocess
from pathlib import Path
runtime=Path(r'D:\apcd_runtime\gpu_platform_v2_native_acceptance_20261009_v1')
out=Path(r'D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1/platform_v2/reports/native_acceptance_v1')
rt=Path(r'D:\apcd_runtime\gpu_production_runner_v1')
proof=json.loads((runtime/'p0_process_full.json').read_text())
rows=proof['rows']
for row in rows:
 p=psutil.Process(row['pid'])
 created_text=row['cim']['CreationDate']
 created=datetime.datetime.strptime(created_text[:26],'%Y-%m-%dT%H:%M:%S.%f').replace(tzinfo=datetime.timezone.utc).timestamp()
 row['cim_psutil_creation_match']=abs(created-row['create_time'])<0.002
 assert row['cim_psutil_creation_match']
 row['parent_identity']='MISSING'
 try:
  pp=psutil.Process(row['ppid']);row['parent_identity']='REUSED_PID' if pp.create_time()>row['create_time'] else 'PRESENT_OLDER_THAN_CHILD'
 except psutil.NoSuchProcess:pass
 # Deleted script bodies and empty native logs do not establish current activity scope.
 if row['classification']=='UNKNOWN':row['reason']='Live process; command/provenance incomplete or source script missing. No active marker/engine does not clear it.'
 for field in ['source_code','ancestors','open_files','connections']:
  if field in row:del row[field]
historical=[]
def walk(value,path,origin):
 if isinstance(value,dict):
  for key,pid in value.items():
   if key.lower() in {'pid','worker_pid','controller_pid','child_pid','owner_pid'} and isinstance(pid,int) and pid>0:
    created=next((value.get(k) for k in ['creation_time','create_time_unix','created_unix','create_time'] if value.get(k) is not None),None)
    status='STALE_INACTIVE'
    try:
     p=psutil.Process(pid)
     try:status='STALE_INACTIVE' if created is not None and abs(float(created)-p.create_time())>0.002 else 'UNKNOWN'
     except (ValueError,TypeError):status='UNKNOWN'
     current={'pid':p.pid,'creation_time':p.create_time(),'command':p.cmdline()}
    except psutil.NoSuchProcess:current=None
    historical.append({'source':str(origin),'json_path':path+'/'+key,'pid':pid,'creation_time':created,'current_identity':current,'classification':status})
   walk(pid,path+'/'+key,origin)
 elif isinstance(value,list):
  for i,x in enumerate(value):walk(x,path+'/'+str(i),origin)
files=list((rt/'runs').glob('*/*/*/status.json'))+list((rt/'requests').glob('*/*/claim.json'))
for p in files:
 if 'CONF' in str(p).upper() or 'SEAL' in str(p).upper():continue
 try:walk(json.loads(p.read_text()),'',p)
 except (ValueError,UnicodeDecodeError):pass
registry=rt/'registry.json'
registry_meta={'path':str(registry),'exists':registry.exists(),'sha256':hashlib.sha256(registry.read_bytes()).hexdigest() if registry.exists() else None}
pending=[]
for p in (rt/'requests/scheduled_run_one_v1').glob('*/request.json'):
 if not (p.parent/'result.json').exists():pending.append(str(p.parent))
targets=[t for t in proof['installed_tasks'] if 'GPU_RUNNER_V1' in t['Name']]
for task in targets:
 task['xml_sha256']=hashlib.sha256(task['Xml'].encode()).hexdigest()
full=runtime/'historical_owner_references.json'
full.write_text(json.dumps(historical,indent=2,default=str),encoding='utf-8')
dedup={}
for entry in historical:
 key=(entry['pid'],str(entry['creation_time']),entry['classification'])
 if key not in dedup:dedup[key]={**entry,'occurrences':0}
 dedup[key]['occurrences']+=1
historical=list(dedup.values())
verdict={'verdict':'BLOCKED','owner_isolation_proven':False,'confirmed_v1_active_count':sum(r['classification']=='CONFIRMED_V1_ACTIVE' for r in rows),'unknown_live_count':sum(r['classification']=='UNKNOWN' for r in rows),'current_processes':rows,'historical_owner_references':historical,'markers':proof['markers'],'registry':registry_meta,'v1_running_tasks':[t for t in proof['running_tasks'] if 'APCD_GPU_RUNNER' in t['Name']],'all_running_task_engine_evidence':proof['running_tasks'],'v1_installed_tasks':targets,'pending_requests':pending,'controller_status':proof['controller_status'],'manual_or_cli_restart_possible':True,'scheduler_modified':False,'locks_deleted':False,'processes_terminated':False,'api_logs':'Eight logs exist but are empty; no start/exit script body proof','historical_launch_inputs':'Missing temp scripts and stdin bodies cannot be reconstructed from process name or empty logs','classification_policy':'UNKNOWN remains blocking; dead or creation-time-mismatched historical PID is STALE_INACTIVE; audit self excluded by exact PID','science_calls_this_task':0}
(out/'p0_owner_isolation.json').write_text(json.dumps(verdict,indent=2,default=str),encoding='utf-8')
print('P0 VERDICT',verdict['verdict'],'LIVE UNKNOWN',verdict['unknown_live_count'],'CONFIRMED V1 ACTIVE',verdict['confirmed_v1_active_count'],'PENDING',pending,'HISTORICAL_REFERENCES',len(historical))
